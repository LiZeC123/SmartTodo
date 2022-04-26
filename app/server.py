import os
from os import mkdir
from os.path import join, exists
from typing import Optional

import sqlalchemy as sal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from werkzeug.exceptions import abort

from entity import Item, Base, TomatoType, ItemType
from service4config import ConfigManager
from service4interpreter import OpInterpreter
from tool4key import activate_key, create_time_key
from tool4log import logger
from tool4mail import send_daily_report
from tool4stat import report
from tool4task import TaskManager
from tool4time import now, today
from tool4tomato import TomatoManager
from tool4web import extract_title, download

config = ConfigManager()


class Manager:
    def __init__(self):
        url = "sqlite:///data/database/data.db?check_same_thread=false"
        self.engine = create_engine(url, echo=True, future=True)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.item_manager = ItemManager(self.session)
        self.file_manager = FileItemManager(self.item_manager)
        self.note_manager = NoteItemManager(self.item_manager)

        self.manager = {
            ItemType.Single: self.item_manager,
            ItemType.File: self.file_manager,
            ItemType.Note: self.note_manager
        }

        # self.op = OpInterpreter(self)
        self.task_manager = TaskManager()
        self.tomato_manager = TomatoManager()
        self.__init_task()

    def __init_task(self):
        self.task_manager.add_task(self.__update_state, 1)
        self.task_manager.add_task(self.garbage_collection, 2)
        self.task_manager.add_task(self.mail_report, 22)
        self.task_manager.start()

    def check_authority(self, xid: int, owner: str):
        with self.session.begin():
            stmt = sal.select(Item.owner).where(Item.id == xid)
            expected_owner = self.session.scalar(stmt)
            if expected_owner != owner:
                logger.warning(f"{Manager.__name__}: User {owner} dose not have authority For xID {xid}")
                abort(401)

    def create(self, item: Item):
        self.manager[item.item_type].create(item)

    def create_upload_file(self, f, parent: int, owner: str):
        name, url = self.file_manager.create_upload_file(f)
        item = Item(0, name, 'file', owner, parent=parent)
        item.url = url
        self.item_manager.create(item)

    def all_items(self, owner: str, /, parent: Optional[int] = None):
        # 可以考虑在前端请求的时候, 返回一个是否需要刷新的标记, 如果检测到变化, 则要求前端刷新, 否则不变
        return self.item_manager.select_all(owner, parent)

    def activate_items(self, owner: str, /, parent: Optional[int] = None):
        return self.item_manager.select_activate(owner, parent)

    def get_summary(self, owner: str):
        return {
            "items": self.item_manager.select_summary(owner),
            "stats": report(owner),
            "habit": self.item_manager.select_habit(owner)
        }

    def remove(self, xid: int, owner: str):
        self.check_authority(xid, owner)
        item = self.item_manager.select(xid)
        self.manager[item.item_type].remove(item)

    def undo(self, xid: int, owner: str, parent: Optional[int] = None):
        with self.session.begin():
            stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
            item = self.session.scalar(stmt)
            item.create_time = now()
            item.tomato_type = TomatoType.Activate
            logger.info(f"回退任务到活动列表: {item.name}")
        return self.activate_items(owner, parent=parent)

    def increase_expected_tomato(self, xid: int, owner: str):
        with self.session.begin():
            stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
            item = self.session.scalar(stmt)
            if item:
                item.expected_tomato += 1
            return item is not None

    def increase_used_tomato(self, xid: int, owner: str):
        with self.session.begin():
            stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
            item = self.session.scalar(stmt)
            if item:
                if item.habit_expected != 0 and item.last_check_time.date() != today():
                    item.habit_done += 1
                if item.used_tomato < item.expected_tomato:
                    item.used_tomato += 1
            return item is not None

    def to_today_task(self, xid: int, owner: str):
        with self.session.begin():
            stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
            item = self.session.scalar(stmt)
            if item:
                item.create_time = now()
                item.tomato_type = TomatoType.Today
        return item is not None

    def get_title(self, xid: int, owner: str) -> str:
        with self.session.begin():
            stmt = sal.select(Item.name).where(Item.id == xid, Item.owner == owner)
            return self.session.scalar(stmt)

    def get_note(self, nid: int, owner: str) -> str:
        self.check_authority(nid, owner)
        return self.note_manager.get(nid)

    def update_note(self, nid: int, owner: str, content: str):
        self.check_authority(nid, owner)
        self.note_manager.update(nid, content)

    def garbage_collection(self):
        # TODO:测试垃圾回收状态
        # 1. 不是不可回收的特殊类型
        # 2. 处于完成状态
        stmt = sal.select(Item).where(Item.repeatable == False, Item.specific == 0,
                                      Item.used_tomato == Item.expected_tomato)
        items = self.session.scalar(stmt)
        for item in items:
            self.manager[item.item_type].remove(item.id)
            logger.info(f"Garbage Collection(Expired): {item.name}")

        stmt = sal.select(Item.id)
        ids = self.session.scalar(stmt)
        ids.append(None)
        stmt = sal.select(Item).where(Item.parent.not_in(ids))
        unreferenced = self.session.scalar(stmt)
        for item in unreferenced:
            self.manager[item.item_type].remove(item)
            logger.info(f"Garbage Collection(Unreferenced): {item.name}")

        self.session.commit()

    def set_tomato_task(self, xid: int, owner: str):
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

    def __update_state(self):
        stmt = sal.select(Item).where(Item.repeatable == True)
        items = self.session.scalar(stmt)
        for item in items:
            item.used_tomato = 0
            logger.info(f"重置可重复任务: {item.name}")

    def exec_function(self, command: str, data: str, parent: int, owner: str):
        pass
        # self.op.exec_function(command, data, parent, owner)

    def mail_report(self):
        for user, email in config.get_mail_users():
            send_daily_report(user, email, self.get_summary(user))


class BaseManager:
    def create(self, item: Item) -> Item:
        raise NotImplementedError()

    def remove(self, item: Item):
        raise NotImplementedError()


class ItemManager(BaseManager):
    def __init__(self, session: Session):
        self.session = session

    def create(self, item: Item) -> Item:
        if item.name.startswith("http"):
            title = extract_title(item.name)
            item.url = item.name
            item.name = title
        self.session.add(item)
        self.session.commit()
        return item

    def select(self, iid: int) -> Item:
        with self.session.begin():
            return self.session.scalar(sal.select(Item).where(Item.id == iid))

    def select_all(self, owner: str, parent: int):
        with self.session.begin():
            stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                          Item.tomato_type == TomatoType.Today)
            todays = self.session.execute(stmt).scalars().all()

            stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                          Item.tomato_type == TomatoType.Activate)
            activates = self.session.execute(stmt).scalars().all()

            return {
                "todayTask": list(map(self.to_dict, sorted(todays, key=create_time_key))),
                "activeTask": list(map(self.to_dict, sorted(activates, key=activate_key, reverse=True)))
            }

    def select_activate(self, owner: str, parent: int):
        with self.session.begin():
            stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                          Item.tomato_type == TomatoType.Activate)
            activates = self.session.execute(stmt).scalars().all()
            return list(map(self.to_dict, sorted(activates, key=activate_key, reverse=True)))

    def select_summary(self, owner: str):
        pass
        # res = defaultdict(list)
        # self.database.select_group_by(res, group_today_task_by_parent(owner), limited=False)
        #
        # if "0" in res:
        #     del res['0']
        #
        # if "miss" in res:
        #     del res['miss']
        #
        # ans = {}
        # for parent, lists in res.items():
        #     lists.insert(0, self.database.select_one(where_id_equal(int(parent))))
        #     ans[parent] = list(map(self.to_dict, lists))
        # return ans

    def select_habit(self, owner: str):
        with self.session.begin():
            stmt = sal.select(Item).where(Item.owner == owner, Item.habit_expected != 0)
            habits = self.session.execute(stmt).scalars().all()
            return list(map(self.to_dict, habits))

    def update_note_url(self, item: Item, url: str) -> Item:
        item.url = url
        self.session.commit()
        return item

    def remove(self, item: Item):
        self.session.delete(item)
        self.session.commit()

    @staticmethod
    def to_dict(item: Item) -> dict:
        return item.to_dict()


class FileItemManager(BaseManager):
    _USER_FOLDER = "data/database"
    _FILE_FOLDER = "data/filebase"

    def __init__(self, m: ItemManager):
        self.manager = m
        self.__init_folder()

    def __init_folder(self):
        if not exists(self._FILE_FOLDER):
            mkdir(self._FILE_FOLDER)

    def create(self, item: Item) -> Item:
        """将指定URL对应的文件下载到公共空间"""
        remote_url = item.name
        path = download(remote_url, FileItemManager._FILE_FOLDER)
        item.url = path.replace(FileItemManager._FILE_FOLDER, '/file').replace("\\", "/")
        return self.manager.create(item)

    @staticmethod
    def create_upload_file(f):
        """将上传的文件保存到私有空间"""
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
        except OSError:
            # 其他的异常情况下, 则保留记录
            logger.exception(f"{FileItemManager.__name__}: Fail To Remove the File: {filename}")


class NoteItemManager(BaseManager):
    _NOTE_FOLDER = "data/notebase"

    def __init__(self, m: ItemManager):
        self.manager = m
        self.__init_folder()
        if not exists(NoteItemManager._NOTE_FOLDER):
            mkdir(NoteItemManager._NOTE_FOLDER)

    def __init_folder(self):
        if not exists(self._NOTE_FOLDER):
            mkdir(self._NOTE_FOLDER)

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
        except OSError:
            logger.exception(f"{NoteItemManager.__name__}: Fail To Remove Note: {nid}")

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


if __name__ == '__main__':
    manager = Manager()
    manager.mail_report()
