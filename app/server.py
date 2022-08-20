from typing import Optional, List

import sqlalchemy as sal

from entity import Item, TomatoType, ItemType
from exception import UnauthorizedException
from server4item import ItemManager, FileItemManager, NoteItemManager
from service4config import ConfigManager
from service4interpreter import OpInterpreter
from tool4log import logger
from tool4report import ReportManager
from tool4task import TaskManager
from tool4time import now, today
from tool4tomato import TomatoManager, TomatoRecordManager

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
        self.tomato_record_manager = TomatoRecordManager(self.db)
        self.report_manager = ReportManager(self.item_manager, self.tomato_record_manager)
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
        return self.report_manager.get_summary(owner)

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

    def mail_report(self):
        for owner, email in config.get_mail_users():
            self.report_manager.send_daily_report(owner, email)

    def get_daily_report(self, owner):
        return self.report_manager.get_daily_report(owner)
