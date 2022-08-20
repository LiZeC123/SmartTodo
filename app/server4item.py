import os
from collections import defaultdict
from os.path import join
from typing import Optional

import sqlalchemy as sal

from entity import Item, TomatoType, ItemType, class2dict
from tool4key import activate_key, create_time_key
from tool4log import logger
from tool4web import extract_title, download


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

    def select_done_item(self, owner: str) -> list:
        stmt = sal.select(Item.name).where(Item.owner == owner, Item.expected_tomato == Item.used_tomato)
        return self.db.execute(stmt).scalars().all()

    def select_undone_item(self, owner: str) -> list:
        stmt = sal.select(Item.name).where(Item.owner == owner, Item.tomato_type == TomatoType.Today,
                                           Item.expected_tomato != Item.used_tomato,
                                           Item.item_type != ItemType.Note)
        return self.db.execute(stmt).scalars().all()

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
