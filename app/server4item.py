import os
from collections import defaultdict
from os.path import join
from typing import Optional, Dict, List

import sqlalchemy as sal

from entity import Item, TomatoType, ItemType, class2dict
from exception import UnauthorizedException, NotUniqueItemException, UnmatchedException
from tool4event import EventManager
from tool4key import activate_key, create_time_key
from tool4log import logger
from tool4time import now, today
from tool4web import extract_title, download


class BaseManager:
    def create(self, item: Item) -> Item:
        raise NotImplementedError()

    def update(self, item: Item) -> Item:
        raise NotImplementedError

    def remove(self, item: Item):
        raise NotImplementedError()


class ItemManager(BaseManager):
    def __init__(self, db):
        self.db = db
        self.base_manager = SingleItemManager(db)
        self.file_manager = FileItemManager(self.base_manager)
        self.note_manager = NoteItemManager(self.base_manager)
        self.event_manager = EventManager(db)

        self.manager: Dict[str, BaseManager] = {
            ItemType.Single: self.base_manager,
            ItemType.File: self.file_manager,
            ItemType.Note: self.note_manager
        }

    def check_authority(self, xid: int, owner: str):
        stmt = sal.select(Item.owner).where(Item.id == xid)
        expected_owner = self.db.scalar(stmt)
        if expected_owner is None:
            raise UnmatchedException(f"No Item matched xId {xid}")
        if expected_owner != owner:
            raise UnauthorizedException(f"User {owner} dose not have authority For xID {xid}")

    def create(self, item: Item) -> Item:
        return self.manager[item.item_type].create(item)

    def create_upload_file(self, f, parent: Optional[int], owner: str) -> Item:
        name, url = self.file_manager.create_upload_file(f)
        item = Item(name=name, item_type=ItemType.File, owner=owner, parent=parent, url=url)
        return self.base_manager.create(item)

    def select(self, iid: int) -> Item:
        return self.db.scalar(sal.select(Item).where(Item.id == iid))

    def select_all(self, owner: str, parent: Optional[int]):
        return {
            "todayTask": self.select_today(owner, parent),
            "activeTask": self.select_activate(owner, parent)
        }

    def select_today(self, owner: str, parent: Optional[int]) -> List:
        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Today)
        today_items = self.db.execute(stmt).scalars().all()
        return list(map(class2dict, sorted(today_items, key=create_time_key)))

    def select_activate(self, owner: str, parent: Optional[int]) -> List:
        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Activate)
        activates = self.db.execute(stmt).scalars().all()
        return list(map(class2dict, sorted(activates, key=activate_key, reverse=True)))

    def get_item_by_name(self, name: str, parent: Optional[int], owner: str) -> List[Item]:
        stmt = sal.select(Item).where(Item.name.like(f"%{name}%"), Item.parent == parent, Item.owner == owner)
        return self.db.execute(stmt).scalars().all()

    def get_unique_item_by_name(self, name: str, parent: Optional[int], owner: str) -> Item:
        items = self.get_item_by_name(name, parent, owner)
        if len(items) == 1:
            return items[0]

        item_str = ' '.join(map(str, items))
        raise NotUniqueItemException(f"[{item_str}]均查询条件(name={name}, parent={parent}, owner={owner})")

    def get_unique_or_null_item_by_name(self, name: str, parent: Optional[int], owner: str) -> Optional[Item]:
        items = self.get_item_by_name(name, parent, owner)
        if len(items) == 0:
            return None
        elif len(items) == 1:
            return items[0]

        item_str = ' '.join(map(str, items))
        raise NotUniqueItemException(f"[{item_str}]均查询条件(name={name}, parent={parent}, owner={owner})")

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

    def undo(self, xid: int, owner: str, parent: Optional[int] = None):
        stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
        item:Item = self.db.scalar(stmt)
        self._undo(item)
        self.event_manager.add_event(f"回退任务到活动任务列表: {item.name}", owner)
        return self.select_activate(owner, parent=parent)

    def _undo(self, item: Item):
        item.create_time = now()
        item.tomato_type = TomatoType.Activate
        self.db.commit()

    def increase_expected_tomato(self, xid: int, owner: str):
        stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
        item = self.db.scalar(stmt)
        if item:
            item.expected_tomato += 1
            self.event_manager.add_event(f"增加预计的番茄钟时间: {item.name}", owner)
        self.db.commit()
        return item is not None

    def increase_used_tomato(self, xid: int, owner: str):
        stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
        item = self.db.scalar(stmt)
        if item:
            if item.habit_expected != 0 and item.last_check_time.date() != today():
                item.habit_done += 1
                item.last_check_time = now()
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
    
    def get_tomato_item(self, owner: str)-> List[Item]:
        stmt = sal.select(Item).where(Item.owner == owner, Item.tomato_type == TomatoType.Today, Item.item_type == ItemType.Single)
        items = self.db.execute(stmt).scalars().all()
        return list(map(class2dict, sorted(items, key=create_time_key)))

    def get_title(self, xid: int, owner: str) -> str:
        stmt = sal.select(Item.name).where(Item.id == xid, Item.owner == owner)
        return self.db.scalar(stmt)

    def get_note(self, nid: int, owner: str) -> str:
        self.check_authority(nid, owner)
        return self.note_manager.get_note(nid)

    def update_note(self, nid: int, owner: str, content: str):
        item = self.select(nid)
        if not item or item.owner != owner:
            raise UnauthorizedException(f"User {owner} dose not have authority For nID {nid}")

        if item.item_type != ItemType.Note:
            raise UnauthorizedException(f"Item {nid} isn't a note, and can't be updated")

        self.note_manager.update_note(nid, content)

    def update(self, item: Item) -> Item:
        return self.manager[item.item_type].update(item)

    def remove(self, item: Item):
        return self.manager[item.item_type].remove(item)

    def remove_by_id(self, xid: int, owner: str) -> bool:
        try:
            self.check_authority(xid, owner)
        except UnmatchedException:
            return False
        
        item = self.select(xid)
        self.manager[item.item_type].remove(item)
        return True

    def garbage_collection(self):
        # 1. 不是不可回收的特殊类型
        # 2. 处于完成状态
        stmt = sal.select(Item).where(Item.repeatable == False, Item.specific == 0,
                                      Item.used_tomato == Item.expected_tomato)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            self.manager[item.item_type].remove(item)
            logger.info(f"垃圾回收(已过期的任务): {item.name}")

        stmt = sal.select(Item.id)
        ids = self.db.execute(stmt).scalars().all()
        stmt = sal.select(Item).where(Item.parent.not_in(ids))
        unreferenced = self.db.execute(stmt).scalars().all()
        for item in unreferenced:
            self.manager[item.item_type].remove(item)
            logger.info(f"垃圾回收(无引用的任务): {item.name}")

        self.db.commit()

    def reset_daily_task(self):
        stmt = sal.select(Item).where(Item.repeatable == True)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            item.used_tomato = 0
            item.tomato_type = TomatoType.Today
            item.create_time = now()
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


class SingleItemManager(BaseManager):
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

    def update(self, item: Item) -> Item:
        self.db.commit()
        return item

    def remove(self, item: Item):
        self.db.delete(item)
        self.db.commit()


class FileItemManager(BaseManager):
    _FILE_FOLDER = "data/filebase"

    def __init__(self, m: BaseManager):
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

    def update(self, item: Item) -> Item:
        return self.manager.update(item)

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

    def __init__(self, m: BaseManager):
        self.manager = m

    def create(self, item: Item) -> Item:
        item = self.manager.create(item)
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(item.id))
        self.__write_init_content(filename, title=item.name)
        item.url = f"note/{item.id}"
        return self.manager.update(item)

    def update(self, item: Item) -> Item:
        return self.manager.update(item)

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
    def get_note(nid: int) -> str:
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(nid))
        with open(filename, 'r', encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def update_note(nid: int, content: str):
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
