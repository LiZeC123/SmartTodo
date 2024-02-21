from typing import Optional

from entity import Item, ItemType, TomatoTaskRecord, TomatoType, class2dict
from exception import UnauthorizedException
from server4item import ItemManager
from service4config import ConfigManager
from service4interpreter import OpInterpreter
from tool4log import Log_File
from tool4event import EventManager
from tool4report import ReportManager
from tool4task import TaskManager
from tool4token import TokenManager
from tool4tomato import TomatoManager, TomatoRecordManager
from tool4time import parse_time, now

class Manager:
    def __init__(self, db):
        self.config = ConfigManager()
        self.token_manager = TokenManager()

        self.item_manager = ItemManager(db)

        self.task_manager = TaskManager()

        self.tomato_manager = TomatoManager(db)
        self.tomato_record_manager = TomatoRecordManager(db)

        self.op = OpInterpreter(self.item_manager, self.tomato_manager)
        self.report_manager = ReportManager(self.item_manager, self.tomato_record_manager)
        self.event_manager = EventManager(db)

        self.__init_task()

    def __init_task(self):
        self.task_manager.add_daily_task("垃圾回收", self.garbage_collection, "01:00")
        self.task_manager.add_daily_task("重置可重复任务", self.reset_daily_task, "01:30")
        self.task_manager.add_daily_task("重置未完成的今日任务", self.reset_today_task, "01:35")
        # self.task_manager.add_daily_task("发送每日总结邮件", self.send_daily_report, "19:45")
        # self.task_manager.add_friday_task("发送每周总结邮件", self.send_weekly_report, "19:45")
        self.task_manager.start()

    def valid_token(self, token: str, role: str):
        info = self.token_manager.query_info(token)
        return info is not None and role in info.get('role')

    def is_admin_user(self, username):
        return self.config.is_admin_user(username)

    def try_login(self, username, password):
        if self.config.try_login(username, password):
            return self.token_manager.create_token({"username": username, "role": self.config.get_roles(username)})
        return None

    def get_username_by_token(self, token: str):
        if token in self.token_manager.data:
            return self.token_manager.data[token].get('username')
        raise UnauthorizedException("Token is not valid.")

    def logout(self, token: str):
        self.token_manager.remove_token(token)

    def create(self, item: Item) -> Item:
        return self.item_manager.create(item)

    def create_upload_file(self, f, parent: Optional[int], owner: str) -> Item:
        return self.item_manager.create_upload_file(f, parent, owner)

    def all_items(self, owner: str, /, parent: Optional[int] = None):
        # 可以考虑在前端请求的时候, 返回一个是否需要刷新的标记, 如果检测到变化, 则要求前端刷新, 否则不变
        return self.item_manager.select_all(owner, parent)

    def activate_items(self, owner: str, /, parent: Optional[int] = None):
        return self.item_manager.select_activate(owner, parent)

    def get_summary(self, owner: str):
        return self.report_manager.get_summary(owner)

    def remove(self, xid: int, owner: str):
        self.item_manager.remove_by_id(xid, owner)

    def undo(self, xid: int, owner: str, parent: Optional[int] = None):
        return self.item_manager.undo(xid, owner, parent)

    def increase_expected_tomato(self, xid: int, owner: str):
        return self.item_manager.increase_expected_tomato(xid, owner)

    def increase_used_tomato(self, xid: int, owner: str):
        return self.item_manager.increase_used_tomato(xid, owner)

    def to_today_task(self, xid: int, owner: str):
        return self.item_manager.to_today_task(xid, owner)
    
    def get_tomato_item(self, owner:str):
        return self.item_manager.get_tomato_item(owner)

    def get_title(self, xid: int, owner: str) -> str:
        return self.item_manager.get_title(xid, owner)

    def get_note(self, nid: int, owner: str) -> str:
        return self.item_manager.get_note(nid, owner)

    def update_note(self, nid: int, owner: str, content: str):
        return self.item_manager.update_note(nid, owner, content)

    def set_tomato_task(self, xid: int, owner: str) -> str:
        item = self.item_manager.select(xid)

        if item.used_tomato == item.expected_tomato:
            return '启动失败: 当前任务已完成全部番茄钟'

        if self.tomato_manager.has_task(owner):
            return '启动失败: 当前存在正在执行的番茄钟'

        return self.tomato_manager.start_task(item, owner)

    def get_tomato_task(self, owner: str):
        return self.tomato_manager.get_task(owner)

    def undo_tomato_task(self, tid: int, xid: int, reason: str, owner: str) -> bool:
        return self.tomato_manager.clear_task(tid, xid, reason, owner)

    def finish_tomato_task(self, tid: int, xid: int, owner: str):
        if self.tomato_manager.finish_task(tid, xid, owner):
            self.increase_used_tomato(xid, owner)
            return True
        return False


    def add_tomato_record(self, name:str, start_time:str, owner: str):
        item = Item(name=name, item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner)
        item.used_tomato = 1
        self.item_manager.create(item)

        record = TomatoTaskRecord(name=name, owner=owner, start_time=parse_time(start_time), finish_time=now())
        self.tomato_manager.create_record(record)

    def get_summary_report(self, owner: str):
        return self.tomato_record_manager.get_time_line_summary(owner)
    
    def get_summary_event_line(self, owner:str):
        l = self.event_manager.get_today_event(owner)
        return [class2dict(i) for i in l]

    def get_event_line(self, owner:str):
        l =  self.event_manager.get_today_event(owner)
        return [class2dict(i) for i in l]

    def garbage_collection(self):
        return self.item_manager.garbage_collection()

    def reset_daily_task(self):
        return self.item_manager.reset_daily_task()

    def reset_today_task(self):
        return self.item_manager.reset_today_task()

    def exec_function(self, command: str, data: str, parent: Optional[int], owner: str):
        self.op.exec_function(command, data, parent, owner)

    def send_daily_report(self):
        for user in self.config.get_users_msg_info():
            self.report_manager.send_daily_report(user)

    def send_weekly_report(self):
        for user in self.config.get_users_msg_info():
            self.report_manager.send_weekly_report(user)

    def get_daily_report(self, owner):
        return self.report_manager.get_daily_report(owner)

    @staticmethod
    def get_log():
        with open(Log_File, encoding='utf-8') as f:
            return "".join(f.readlines())

    def get_tomato_log(self, owner: str):
        return self.tomato_record_manager.get_tomato_log(owner)
