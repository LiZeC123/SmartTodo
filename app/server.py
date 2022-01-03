import os
from collections import defaultdict
from os import mkdir
from os.path import join, exists

from werkzeug.exceptions import abort

from entity import Item, from_dict
from mapper import MemoryDataBase
from service4interpreter import OpInterpreter
from tool4item import where_can_delete, \
    where_update_repeatable_item, update_repeatable_item, where_id_equal, \
    undo_item, where_equal, group_all_item_with, where_select_activate_with, update_note_url, \
    where_unreferenced, select_id, select_title, inc_expected_tomato, inc_used_tomato, \
    urgent_task, today_task, group_today_task_by_parent, shrink_item, where_same_parent
from tool4key import activate_key, create_time_key
from tool4log import logger
from tool4stat import report
from tool4task import TaskManager
from tool4tomato import TomatoManager
from tool4web import extract_title, download


class Manager:
    def __init__(self):
        self.database: MemoryDataBase = MemoryDataBase()
        self.item_manager = ItemManager(self.database)
        self.file_manager = FileItemManager(self.database)
        self.note_manager = NoteItemManager(self.database)
        self.manager = {"single": self.item_manager, "file": self.file_manager, "note": self.note_manager}
        self.op = OpInterpreter(self)
        self.task_manager = TaskManager()
        self.tomato_manager = TomatoManager()
        self.__init_task()

    def __init_task(self):
        self.task_manager.add_task(self.__update_state, 1)
        self.task_manager.add_task(self.garbage_collection, 2)
        self.task_manager.start()

    def check_authority(self, xid: int, owner: str):
        # select_by 方法返回一个数组, 因此需要取出其中的值
        owners = self.database.select_by(where_id_equal(xid), lambda it: it['owner'])
        if len(owners) > 0:
            expected_owner = self.database.select_by(where_id_equal(xid), lambda it: it['owner'])[0]
            if expected_owner == owner:
                return

        logger.warning(f"{Manager.__name__}: User {owner} dose not have authority For xID {xid}")
        abort(401)

    def create(self, item: Item):
        self.manager[item.item_type].create(item)

    def create_upload_file(self, f, parent: int, owner: str):
        name, url = self.file_manager.create_upload_file(f)
        item = Item(0, name, 'file', owner, parent=parent)
        item.url = url
        self.item_manager.create(item)

    def all_items(self, owner: str, /, parent: int = 0):
        # 可以考虑在前端请求的时候, 返回一个是否需要刷新的标记, 如果检测到变化, 则要求前端刷新, 否则不变
        return self.item_manager.select_all(owner, parent)

    def activate_items(self, owner: str, /, parent: int = 0):
        return self.item_manager.select_activate(owner, parent)

    def get_summary(self, owner: str):
        return {
            "items": self.item_manager.select_summary(owner),
            "stats": report(owner)
        }

    def remove(self, xid: int, owner: str):
        self.check_authority(xid, owner)
        item = self.item_manager.select(xid)
        self.manager[item.item_type].remove(item)

    def undo(self, xid: int, owner: str, parent: int = 0):
        self.database.update_by(where_equal(xid, owner), undo_item)
        return self.activate_items(owner, parent=parent)

    def increase_expected_tomato(self, xid: int, owner: str):
        return self.database.update_by(where_equal(xid, owner), inc_expected_tomato) == 1

    def increase_used_tomato(self, xid: int, owner: str):
        return self.database.update_by(where_equal(xid, owner), inc_used_tomato) == 1

    def to_urgent_task(self, xid: int, owner: str):
        return self.database.update_by(where_equal(xid, owner), urgent_task) == 1

    def to_today_task(self, xid: int, owner: str):
        return self.database.update_by(where_equal(xid, owner), today_task) == 1

    def get_title(self, xid: int, owner: str) -> str:
        return self.database.select_one(where_equal(xid, owner), select_title)

    def shrink(self, parent: int, owner: str):
        return self.database.update_by(where_same_parent(parent, owner), shrink_item)

    def get_note(self, nid: int, owner: str) -> str:
        self.check_authority(nid, owner)
        return self.note_manager.get(nid)

    def update_note(self, nid: int, owner: str, content: str):
        self.check_authority(nid, owner)
        self.note_manager.update(nid, content)

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
        return self.tomato_manager.start_task(xid, title, owner)

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
        self.database.update_by(where_update_repeatable_item, update_repeatable_item)

    def exec_function(self, command: str, data: str, parent: int, owner: str):
        self.op.exec_function(command, data, parent, owner)


class ItemManager:
    def __init__(self, database: MemoryDataBase):
        self.database: MemoryDataBase = database

    def create(self, item: Item) -> int:
        if item.name.startswith("http"):
            title = extract_title(item.name)
            item.url = item.name
            item.name = title
        return self.database.insert(item)

    def select(self, iid: int) -> Item:
        return from_dict(self.database.select(iid))

    def select_all(self, owner: str, parent: int):
        data = {"activate": [], "urgent": [], "today": [], "delete": []}
        self.database.select_group_by(data, group_all_item_with(owner, parent))

        return {
            "todayTask": list(map(self.to_dict, sorted(data["today"], key=create_time_key))),
            "urgentTask": list(map(self.to_dict, sorted(data["urgent"], key=create_time_key))),
            "activeTask": list(map(self.to_dict, sorted(data["activate"], key=activate_key, reverse=True)))
        }

    def select_activate(self, owner: str, parent: int):
        return list(map(self.to_dict, sorted(self.database.select_by(where_select_activate_with(owner, parent)),
                                             key=activate_key, reverse=True)))

    def select_summary(self, owner: str):
        res = defaultdict(list)
        self.database.select_group_by(res, group_today_task_by_parent(owner), limited=False)

        del res['0']
        del res['miss']

        ans = {}
        for parent, lists in res.items():
            lists.insert(0, self.database.select_one(where_id_equal(int(parent))))
            ans[parent] = list(map(self.to_dict, lists))
        return ans

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
        self.database: MemoryDataBase = database

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
        self.database: MemoryDataBase = database
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
