import os
import random
import string
from datetime import timedelta
from os import mkdir
from os.path import join, exists
from typing import Optional
from threading import Timer
from werkzeug.exceptions import abort

from entity import Item, from_dict
from mapper import MemoryDataBase
from tool4item import where_can_delete, \
    where_update_repeatable_item, update_repeatable_item, where_id_equal, finish_item, \
    undo_item, where_equal, old_item, group_all_item_with, where_select_todo_with, update_note_url, \
    where_select_all_file, where_unreferenced, select_id, select_title
from tool4key import todo_item_key, done_item_key, old_item_key
from tool4log import logger
from tool4time import now
from tool4web import extract_title, download


def generate_token_str():
    return ''.join(random.sample(string.ascii_letters + string.digits, 16))


class TokenManager:
    def __init__(self):
        self.data = {}

    def create_token(self, info: dict) -> str:
        token = generate_token_str()
        self.data[token] = info
        return token

    def query_info(self, token: str) -> Optional[dict]:
        return self.data.get(token)

    def check_token(self, request, role) -> bool:
        token = request.headers.get('token')
        return token in self.data and role in self.data[token].get('role')

    def get_username(self, request) -> Optional[str]:
        token = request.headers.get('token')
        info = self.data.get(token, {})
        return info.get('username')

    def remove_token(self, token: str) -> None:
        if token in self.data:
            del self.data[token]


class TaskManager:
    def __init__(self) -> None:
        self.tasks = [[] for _ in range(24)]
        self.ONE_HOUR = 60 * 60

    def add_task(self, task, hour: int):
        self.tasks[hour].append(task)

    def start(self):
        now_time = now()
        t0 = timedelta(hours=now_time.hour, minutes=now_time.minute, seconds=now_time.second)
        t1 = timedelta(hours=now_time.hour + 1)
        dt = t1 - t0

        logger.info(f"TimeTask: Now is {now_time}. Sleep {dt.seconds} seconds to the hour")
        # 等待到下一个整点时刻再开始执行任务
        Timer(dt.seconds, self.__start0).start()

    def __start0(self):
        now_hour = now().hour
        logger.info(f"TimeTask: Do Task For Hour {now_hour}")

        for task in self.tasks[now_hour]:
            task()

        Timer(self.ONE_HOUR, self.__start0).start()


class TomatoManager:
    def __init__(self):
        self.data = {}
        self.taskName = ""
        self.startTime = now()

    def set_task(self, name: str, owner: str):
        self.data[owner] = {"name": name, "startTime": now().timestamp()}

    def get_task(self, owner: str):
        return self.data[owner]


class Manager:
    def __init__(self):
        database = MemoryDataBase()
        self.database = database
        self.item_manager = ItemManager(database)
        self.file_manager = FileItemManager(database)
        self.note_manager = NoteItemManager(database)
        self.manager = {"single": self.item_manager, "file": self.file_manager, "note": self.note_manager}
        self.task_manager = TaskManager()
        self.tomato_manager = TomatoManager()
        self.__init_task()

    def __init_task(self):
        self.task_manager.add_task(self.__update_state, 1)
        self.task_manager.add_task(self.garbage_collection, 2)
        self.task_manager.start()

    def check_authority(self, xid: int, owner: str):
        # select_by 方法返回一个数组, 因此需要取出其中的值
        expected_owner = self.database.select_by(where_id_equal(xid), lambda it: it['owner'])[0]
        if expected_owner != owner:
            logger.warning(f"{Manager.__name__}: User {owner} dose not have authority For xID {xid}"
                           f"(expected owner : {expected_owner})")
            abort(401)

    def create(self, item: Item):
        self.manager[item.item_type].create(item)

    def create_upload_file(self, f, parent: int, owner: str):
        name, url = self.file_manager.create_upload_file(f)
        item = Item(0, name, 'file', owner, parent=parent)
        item.url = url
        self.item_manager.create(item)

    def select(self):
        pass

    def all_items(self, owner: str, /, parent: int = 0):
        # 可以考虑在前端请求的时候, 返回一个是否需要刷新的标记, 如果检测到变化, 则要求前端刷新, 否则不变
        return self.item_manager.select_all(owner, parent)

    def todo_items(self, owner: str, /, parent: int = 0):
        return self.item_manager.select_todo(owner, parent)

    def files(self):
        return self.item_manager.select_file()

    def remove(self, xid: int, owner: str):
        self.check_authority(xid, owner)
        item = self.item_manager.select(xid)
        self.manager[item.item_type].remove(item)

    def done(self, xid: int, owner: str, parent: int = 0):
        self.database.update_by(where_equal(xid, owner), finish_item)
        return self.todo_items(owner, parent=parent)

    def undo(self, xid: int, owner: str, parent: int = 0):
        self.database.update_by(where_equal(xid, owner), undo_item)
        return self.todo_items(owner, parent=parent)

    def to_old(self, xid: int, owner: str) -> bool:
        return self.database.update_by(where_equal(xid, owner), old_item) == 1

    def get_title(self, xid: int, owner: str) -> str:
        return self.database.select_one(where_equal(xid, owner), select_title)

    def get_note(self, nid: int, owner: str) -> str:
        self.check_authority(nid, owner)
        return self.note_manager.get(nid)

    def update_note(self, nid: int, owner: str, content: str):
        self.check_authority(nid, owner)
        self.note_manager.update(nid, content)

    # 垃圾收集的条件  1. 达到计数次数 2. 零点定时处理
    def garbage_collection(self):
        items = self.database.select_by(where_can_delete)
        for item in items:
            self.manager[item.item_type].remove(item)
            logger.info(f"Garbage Collection(Expired): {item.name}")

        ids = self.database.select_by(select=select_id)
        unreferenced = self.database.select_by(where=where_unreferenced(ids))
        for item in unreferenced:
            self.manager[item.item_type].remove(item)
            logger.info(f"Garbage Collection(Unreferenced): {item.name}")

    def set_tomato_task(self, xid: int, owner: str):
        title = self.get_title(xid, owner)
        self.tomato_manager.set_task(title, owner)

    def get_tomato_task(self, owner: str):
        return self.tomato_manager.get_task(owner)

    def __update_state(self):
        self.database.update_by(where_update_repeatable_item, update_repeatable_item)


class ItemManager:
    def __init__(self, database: MemoryDataBase):
        self.database = database

    def create(self, item: Item) -> int:
        if item.name.startswith("http"):
            title = extract_title(item.name)
            item.url = item.name
            item.name = title
        return self.database.insert(item)

    def select(self, iid: int) -> Item:
        return from_dict(self.database.select(iid))

    def select_all(self, owner: str, parent: int):
        data = {"todo": [], "done": [], "old": [], "delete": []}
        self.database.select_group_by(data, group_all_item_with(owner, parent))

        return {
            "todo": list(map(self.to_dict, sorted(data["todo"], key=todo_item_key, reverse=True))),
            "done": list(map(self.to_dict, sorted(data["done"], key=done_item_key, reverse=True))),
            "old": list(map(self.to_dict, sorted(data["old"], key=old_item_key, reverse=True)))
        }

    def select_todo(self, owner: str, parent: int):
        return list(map(self.to_dict, sorted(self.database.select_by(where_select_todo_with(owner, parent)),
                                             key=todo_item_key, reverse=True)))

    def select_file(self):
        return list(map(self.to_dict, self.database.select_by(where_select_all_file)))

    def remove(self, item: Item):
        self.database.remove(item)

    @staticmethod
    def to_dict(item: Item) -> dict:
        return item.to_dict()


class FileItemManager(ItemManager):
    _USER_FOLDER = "data/database"
    _FILE_FOLDER = "data/filebase"

    def __init__(self, database: MemoryDataBase):
        super().__init__(database)
        self.__init_folder()
        self.database = database

    def __init_folder(self):
        if not exists(self._FILE_FOLDER):
            mkdir(self._FILE_FOLDER)

    def create(self, item: Item):
        """将指定URL对应的文件下载到公共空间"""
        remote_url = item.name
        path = download(remote_url, FileItemManager._FILE_FOLDER)
        item.url = path.replace(FileItemManager._FILE_FOLDER, '/file').replace("\\", "/")
        return self.database.insert(item)

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
            self.database.remove(item)
        except FileNotFoundError:
            # 对于文件没有找到这种情况, 可以删除记录
            logger.exception(f"{FileItemManager.__name__}: File Not Found: {filename}")
            self.database.remove(item)
        except OSError:
            # 其他的异常情况下, 则保留记录
            logger.exception(f"{FileItemManager.__name__}: Fail To Remove the File: {filename}")


class NoteItemManager(ItemManager):
    _NOTE_FOLDER = "data/notebase"

    def __init__(self, database: MemoryDataBase):
        super().__init__(database)
        self.__init_folder()
        self.database = database
        if not exists(NoteItemManager._NOTE_FOLDER):
            mkdir(NoteItemManager._NOTE_FOLDER)

    def __init_folder(self):
        if not exists(self._NOTE_FOLDER):
            mkdir(self._NOTE_FOLDER)

    def create(self, item: Item):
        nid = self.database.insert(item)
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(nid))
        self.__write_init_content(filename, title=item.name)
        self.database.update_by(where_id_equal(item.id), update_note_url)
        return nid

    def remove(self, item: Item):
        nid = item.id
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(nid))
        try:
            os.remove(filename)
            self.database.remove(item)
        except FileNotFoundError:
            self.database.remove(item)
            logger.exception(f"{NoteItemManager.__name__}: Note Not Found: {nid}")
        except OSError:
            logger.exception(f"{NoteItemManager.__name__}: Fail To Remove Note: {nid}")

    @staticmethod
    def get(nid: int) -> str:
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(nid))
        with open(filename, 'r') as f:
            return f.read()

    @staticmethod
    def update(nid: int, content: str):
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(nid))
        with open(filename, "w") as f:
            f.write(content)

    @staticmethod
    def __write_init_content(filename, title):
        with open(filename, "w") as f:
            content = f"<h1>{title}</h1>" \
                      f"<div>====================</div>" \
                      f"<div><br></div><div><br></div><div><br></div><div><br></div>"
            f.write(content)
