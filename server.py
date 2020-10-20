from typing import Dict

from entity import Item
from mapper import MemoryDataBase
from service4file import FileManager
from service4note import NoteManager
from tool4config import ConfigManager
from tool4item import todo_item_key, done_item_key, old_item_key, map_item, map_file, \
    update_urgent_level, update_repeatable_done_status
from tool4log import logger
from tool4time import now_str
from tool4web import extract_title


class Manager:
    def __init__(self):
        self.database = MemoryDataBase("admin")
        self.fileManager = FileManager()
        self.noteManager = NoteManager()
        self.configManager = ConfigManager()
        self.create_strategy = [
            (lambda it: it.item_type == "file", self.__create_download_file),
            (lambda it: it.item_type == "note", self.__create_note),
            (lambda it: it.name.startswith("http"), self.__create_link_item),
            (lambda it: True, self.__create_item)
        ]

    def __repr__(self):
        return "manager"

    def create(self, it: Item):
        for predict, action in self.create_strategy:
            if predict(it):
                action(it)
                return True
        return False

    def update(self, item_type: str, xid: int, content: str = None):
        if item_type == "item":
            return self.__update(xid)
        elif item_type == "note":
            return self.noteManager.update(xid, content=content)

    def remove(self, iid):
        with self.database.select(iid) as item:
            if item['itemType'] == "file":
                self.fileManager.remove(item['url'])
            if item['itemType'] == "note":
                self.noteManager.remove(int(item['id']))
        self.database.remove(iid)

    def todo(self, parent):
        """获取待办事项的列表"""
        data = {"todo": [], "done": [], "old": [], "delete": [], "miss": []}
        self.__update_state()  # 先更新状态, 然后处理请求
        for item in self.database.items():
            data[map_item(item, parent)].append(item)
        self.__garbage_collection(data)  # 垃圾回收不要求实时处理, 因此最后处理

        return {
            "todo": sorted(data["todo"], key=todo_item_key, reverse=True),
            "done": sorted(data["done"], key=done_item_key, reverse=True),
            "old": sorted(data["old"], key=old_item_key, reverse=True)
        }

    def files(self):
        """获取文件项列表"""
        data = {"todo": [], "done": [], "delete": []}

        for item in self.database.items():
            data[map_file(item)].append(item)

        return {
            "todo": sorted(data["todo"], key=todo_item_key, reverse=True),
            "done": sorted(data["done"], key=done_item_key, reverse=True),
        }

    def item(self, iid: int) -> Dict:
        with self.database.select(iid) as item:
            return item

    def note(self, nid: int):
        return self.noteManager.get(nid=nid)

    def to_old(self, iid):
        with self.database.select(iid) as item:
            item['old'] = True
            logger.info(f"DataManager: Move Item {iid} To Old Space")

    def save_file(self, f):
        """保存用户上传的文件"""
        filename, local_url = self.fileManager.save_upload_file(f)
        item = Item(0, filename, "file")
        item.url = local_url
        self.database.insert(item)

    def try_login(self, username: str, password: str) -> bool:
        users = self.configManager.users()
        return username in users and users[username]['password'] == password

    def back_up(self):
        return self.database.get_filename()

    def version(self):
        return self.configManager.version()

    def __create_download_file(self, item: Item):
        self.fileManager.download_file(item)
        self.database.insert(item)

    def __create_link_item(self, item: Item):
        title = extract_title(item.name)
        item.url = item.name
        item.name = title
        self.database.insert(item)

    def __create_note(self, item: Item):
        item = self.database.insert(item)
        self.noteManager.create(item.id, item.name)
        self.database.update_url(item.id, f"note/{item.id}")

    def __create_item(self, item: Item):
        self.database.insert(item)

    def __update(self, iid):
        with self.database.select(iid) as item:
            if item['finishTime'] is None or item['itemType'] == "specific":
                item['finishTime'] = now_str()
                logger.info(f"DataManager: Move Item {iid} To Done Lists")
            else:
                item['finishTime'] = None
                # 可重复任务重置创建时间, 从而能够正常的进行排序
                if item['itemType'] == "repeatable":
                    item['createTime'] = now_str()
                logger.info(f"DataManager: Move Item {iid} To Todo List")

    def __garbage_collection(self, data):
        for item in data['delete']:
            self.remove(item['id'])
            logger.info(f"Garbage Collection(Expire): {item}")

        ids = list(map(lambda i: i['id'], self.database.items()))
        unreferenced = []
        for item in self.database.items():
            if item['parent'] is not None and int(item['parent']) not in ids:
                unreferenced.append(item)
        for item in unreferenced:
            self.remove(item['id'])
            logger.info(f"Garbage Collection(Unreferenced): {item}")

    def __update_state(self):
        for item in self.database.items():
            # 更新所有需要自动更新的属性
            item['urgent'] = update_urgent_level(item)
            item['finishTime'] = update_repeatable_done_status(item)
