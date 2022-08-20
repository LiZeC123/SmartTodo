import os
from collections import defaultdict
from os.path import join
from typing import Optional, List

import sqlalchemy as sal

from entity import Item, TomatoType, ItemType, class2dict
from exception import UnauthorizedException
from service4config import ConfigManager
from service4interpreter import OpInterpreter
from tool4key import activate_key, create_time_key
from tool4log import logger
from tool4mail import send_daily_report
from tool4stat import report, done_task_stat, undone_task_stat, tomato_stat, gen_daily_report
from tool4task import TaskManager
from tool4time import now, today
from tool4tomato import TomatoManager
from tool4web import extract_title, download

config = ConfigManager()


class Manager:
    def __init__(self, db):
        self.db = db
        self.item_manager = ItemManager(db)
        self.file_manager = FileItemManager(self.item_manager)
        self.note_manager = NoteItemManager(self.item_manager)

        self.manager = {
            ItemType.Single: self.item_manager,
            ItemType.File: self.file_manager,
            ItemType.Note: self.note_manager
        }

        self.op = OpInterpreter(self)
        self.task_manager = TaskManager()
        self.tomato_manager = TomatoManager(self.db)
        self.__init_task()

    def __init_task(self):
        self.task_manager.add_task("垃圾回收", self.garbage_collection, "01:00")
        self.task_manager.add_task("重置可重复任务", self.reset_daily_task, "01:30")
        self.task_manager.add_task("重置未完成的今日任务", self.reset_today_task, "01:35")
        self.task_manager.add_task("发送每日总结邮件", self.mail_report, "22:30")
        self.task_manager.start()

    def check_authority(self, xid: int, owner: str):
        stmt = sal.select(Item.owner).where(Item.id == xid)
        expected_owner = self.db.scalar(stmt)
        if expected_owner != owner:
            msg = f"{Manager.__name__}: User {owner} dose not have authority For xID {xid}"
            logger.warning(msg)
            raise UnauthorizedException(msg)

    def create(self, item: Item) -> Item:
        return self.manager[item.item_type].create(item)

    def create_upload_file(self, f, parent: Optional[int], owner: str) -> Item:
        name, url = self.file_manager.create_upload_file(f)
        item = Item(name=name, item_type=ItemType.File, owner=owner, parent=parent, url=url)
        return self.item_manager.create(item)

    def all_items(self, owner: str, /, parent: Optional[int] = None):
        # 可以考虑在前端请求的时候, 返回一个是否需要刷新的标记, 如果检测到变化, 则要求前端刷新, 否则不变
        return self.item_manager.select_all(owner, parent)

    def activate_items(self, owner: str, /, parent: Optional[int] = None):
        return self.item_manager.select_activate(owner, parent)

    def get_summary(self, owner: str):
        return {
            "items": self.item_manager.select_summary(owner),
            "stats": report(self.db, owner),
            "habit": self.item_manager.select_habit(owner)
        }

    def get_item_by_name(self, name: str, parent: Optional[int], owner: str) -> List[Item]:
        stmt = sal.select(Item).where(Item.name.like(f"%{name}%"), Item.parent == parent, Item.owner == owner)
        return self.db.execute(stmt).scalars().all()

    def remove(self, xid: int, owner: str):
        self.check_authority(xid, owner)
        item = self.item_manager.select(xid)
        self.manager[item.item_type].remove(item)

    def undo(self, xid: int, owner: str, parent: Optional[int] = None):
        stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
        item = self.db.scalar(stmt)
        self._undo(item)
        return self.activate_items(owner, parent=parent)

    def _undo(self, item: Item):
        item.create_time = now()
        item.tomato_type = TomatoType.Activate
        logger.info(f"回退任务到活动任务列表: {item.name}")
        self.db.commit()

    def increase_expected_tomato(self, xid: int, owner: str):
        stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
        item = self.db.scalar(stmt)
        if item:
            item.expected_tomato += 1
        self.db.commit()
        return item is not None

    def increase_used_tomato(self, xid: int, owner: str):
        stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
        item = self.db.scalar(stmt)
        if item:
            if item.habit_expected != 0 and item.last_check_time.date() != today():
                item.habit_done += 1
                logger.info(f"完成打卡任务: {item.name}")
            if item.used_tomato < item.expected_tomato:
                item.used_tomato += 1
                logger.info(f"手动完成任务: {item.name}")
        self.db.commit()
        return item is not None

    def to_today_task(self, xid: int, owner: str):
        stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
        item = self.db.scalar(stmt)
        if item:
            item.create_time = now()
            item.tomato_type = TomatoType.Today
            logger.info(f"添加任务到今日任务列表: {item.name}")
        self.db.commit()
        return item is not None

    def get_title(self, xid: int, owner: str) -> str:
        stmt = sal.select(Item.name).where(Item.id == xid, Item.owner == owner)
        return self.db.scalar(stmt)

    def get_note(self, nid: int, owner: str) -> str:
        self.check_authority(nid, owner)
        return self.note_manager.get(nid)

    def update_note(self, nid: int, owner: str, content: str):
        self.check_authority(nid, owner)
        self.note_manager.update(nid, content)

    def garbage_collection(self):
        # 1. 不是不可回收的特殊类型
        # 2. 处于完成状态
        stmt = sal.select(Item).where(Item.repeatable == False, Item.specific == 0,
                                      Item.used_tomato == Item.expected_tomato)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            self.manager[item.item_type].remove(item)
            logger.info(f"Garbage Collection(Expired): {item.name}")

        stmt = sal.select(Item.id)
        ids = self.db.execute(stmt).scalars().all()
        stmt = sal.select(Item).where(Item.parent.not_in(ids))
        unreferenced = self.db.execute(stmt).scalars().all()
        for item in unreferenced:
            self.manager[item.item_type].remove(item)
            logger.info(f"Garbage Collection(Unreferenced): {item.name}")

        self.db.commit()

    def set_tomato_task(self, xid: int, owner: str) -> int:
        item = self.item_manager.select(xid)

        if item.used_tomato == item.expected_tomato:
            self.increase_expected_tomato(xid, owner)

        return self.tomato_manager.start_task(item, owner)

    def get_tomato_task(self, owner: str):
        return self.tomato_manager.get_task(owner)

    def undo_tomato_task(self, tid: int, xid: int, owner: str) -> bool:
        return self.clear_tomato_task(tid, xid, owner)

    def finish_tomato_task(self, tid: int, xid: int, owner: str):
        if self.tomato_manager.finish_task(tid, xid, owner):
            self.increase_used_tomato(xid, owner)
            return True
        return False

    def clear_tomato_task(self, tid: int, xid: int, owner: str):
        return self.tomato_manager.clear_task(tid, xid, owner)

    def finish_tomato_task_manually(self, tid: int, xid: int, owner: str):
        return self.finish_tomato_task(tid, xid, owner) and self.clear_tomato_task(tid, xid, owner)

    def reset_daily_task(self):
        stmt = sal.select(Item).where(Item.repeatable == True)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            item.used_tomato = 0
            item.tomato_type = TomatoType.Today
            logger.info(f"重置可重复任务: {item.name}")
        self.db.commit()

    def reset_today_task(self):
        stmt = sal.select(Item).where(Item.tomato_type == TomatoType.Today, Item.repeatable == False,
                                      Item.item_type != ItemType.Note)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            # 使用逻辑回退, 从而保证回退操作的逻辑是一致的
            self._undo(item)
        self.db.commit()

    def exec_function(self, command: str, data: str, parent: Optional[int], owner: str):
        self.op.exec_function(command, data, parent, owner)

    def get_mail_report_data(self, owner: str):
        summary = report(self.db, owner)
        habits = self.item_manager.select_habit(owner)
        return {
            "user": owner,
            "today_stat": summary['today']['count'],
            "total_stat": summary['today']['minute'],
            "done_task": done_task_stat(self.db, owner),
            "undone_task": undone_task_stat(self.db, owner),
            "undone_habit": [habit for habit in habits if habit['expected_tomato'] != habit['used_tomato']],
            "tomato_task": tomato_stat(self.db, owner)
        }

    def mail_report(self, dry_run=False):
        for user, email in config.get_mail_users():
            send_daily_report(email, self.get_mail_report_data(user), dry_run)

    def get_daily_report(self, owner):
        return gen_daily_report(self.db, owner)


class BaseManager:
    def create(self, item: Item) -> Item:
        raise NotImplementedError()

    def remove(self, item: Item):
        raise NotImplementedError()


class ItemManager(BaseManager):
    def __init__(self, db):
        self.db = db

    def create(self, item: Item) -> Item:
        if item.name.startswith("http") and item.item_type == ItemType.Single:
            title = extract_title(item.name)
            item.url = item.name
            item.name = title
        self.db.add(item)
        self.db.commit()
        return item

    def select(self, iid: int) -> Item:
        return self.db.scalar(sal.select(Item).where(Item.id == iid))

    def select_all(self, owner: str, parent: Optional[int]):
        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Today)
        todays = self.db.execute(stmt).scalars().all()

        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Activate)
        activates = self.db.execute(stmt).scalars().all()

        return {
            "todayTask": list(map(class2dict, sorted(todays, key=create_time_key))),
            "activeTask": list(map(class2dict, sorted(activates, key=activate_key, reverse=True)))
        }

    def select_activate(self, owner: str, parent: Optional[int]):
        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Activate)
        activates = self.db.execute(stmt).scalars().all()
        return list(map(class2dict, sorted(activates, key=activate_key, reverse=True)))

    def select_summary(self, owner: str):
        stmt = sal.select(Item).where(Item.owner == owner, Item.tomato_type == TomatoType.Today)
        items = self.db.execute(stmt).scalars().all()
        res = defaultdict(list)
        for item in items:
            res[item.parent].append(item)

        ans = {}
        for parent, lists in res.items():
            if parent is None:
                # 汇总页面上仅显示各个Note之中的任务
                continue
            lists.insert(0, self.select(parent))
            ans[parent] = list(map(class2dict, lists))
        return ans

    def select_habit(self, owner: str):
        stmt = sal.select(Item).where(Item.owner == owner, Item.habit_expected != 0)
        habits = self.db.execute(stmt).scalars().all()
        return list(map(class2dict, habits))

    def update_note_url(self, item: Item, url: str) -> Item:
        item.url = url
        self.db.commit()
        return item

    def remove(self, item: Item):
        self.db.delete(item)
        self.db.commit()


class FileItemManager(BaseManager):
    _FILE_FOLDER = "data/filebase"

    def __init__(self, m: ItemManager):
        self.manager = m

    def create(self, item: Item) -> Item:
        """从指定的URL下载文件到服务器"""
        remote_url = item.name
        path = download(remote_url, FileItemManager._FILE_FOLDER)
        item.url = path.replace(FileItemManager._FILE_FOLDER, '/file').replace("\\", "/")
        return self.manager.create(item)

    @staticmethod
    def create_upload_file(f):
        """将上传的文件保存到服务器"""
        path = join(FileItemManager._FILE_FOLDER, f.filename)
        f.save(path)
        url = path.replace("\\", "/").replace(FileItemManager._FILE_FOLDER, '/file')
        return f.filename, url

    def remove(self, item: Item):
        filename = item.url.replace("/file", FileItemManager._FILE_FOLDER)
        try:
            os.remove(filename)
            self.manager.remove(item)
        except FileNotFoundError:
            # 对于文件没有找到这种情况, 可以删除记录
            logger.warning(f"{FileItemManager.__name__}: File Not Found: {filename}")
            self.manager.remove(item)


class NoteItemManager(BaseManager):
    _NOTE_FOLDER = "data/notebase"

    def __init__(self, m: ItemManager):
        self.manager = m

    def create(self, item: Item) -> Item:
        item = self.manager.create(item)
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(item.id))
        self.__write_init_content(filename, title=item.name)
        return self.manager.update_note_url(item, f"note/{item.id}")

    def remove(self, item: Item):
        nid = item.id
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(nid))
        try:
            os.remove(filename)
            self.manager.remove(item)
        except FileNotFoundError:
            logger.warning(f"{NoteItemManager.__name__}: Note Not Found: {nid}")
            self.manager.remove(item)

    @staticmethod
    def get(nid: int) -> str:
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(nid))
        with open(filename, 'r', encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def update(nid: int, content: str):
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(nid))
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def __write_init_content(filename, title):
        with open(filename, "w", encoding="utf-8") as f:
            content = f"<h1>{title}</h1>" \
                      f"<div>====================</div>" \
                      f"<div><br></div><div><br></div><div><br></div><div><br></div>"
            f.write(content)
