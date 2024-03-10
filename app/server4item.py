import os
from collections import defaultdict
from os.path import join
from typing import Optional, Dict, List, Sequence

import sqlalchemy as sal
from sqlalchemy.orm import scoped_session, Session

from entity import Item, TomatoType, ItemType, Note, class2dict
from exception import UnauthorizedException, NotUniqueItemException, UnmatchedException
from tool4event import EventManager
from tool4log import logger
from tool4time import now, today
from tool4web import extract_title, download


class BaseManager:
    def create(self, item: Item) -> Item:
        raise NotImplementedError()

    def update(self, item: Item) -> Item:
        raise NotImplementedError

    def remove(self, item: Item) -> bool:
        raise NotImplementedError()


class ItemManager(BaseManager):
    def __init__(self, db: scoped_session[Session]):
        self.db = db
        self.base_manager = SingleItemManager(db)
        self.file_manager = FileItemManager(self.base_manager)
        self.note_manager = NoteItemManager(self.base_manager, db=db)
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

    def select(self, iid: int) -> Optional[Item]:
        return self.db.scalar(sal.select(Item).where(Item.id == iid))
    
    def select_with_authority(self, xid: int, owner:str) -> Item:
        stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
        item = self.db.scalar(stmt)
        if item is None:
            raise UnauthorizedException(f"User {owner} dose not have authority For xID {xid}")

        return item

    def select_all(self, owner: str, parent: Optional[int]):
        return {
            "todayTask": self.select_today(owner, parent),
            "activeTask": self.select_activate(owner, parent)
        }

    def select_today(self, owner: str, parent: Optional[int]) -> List:
        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Today)
        today_items = self.db.execute(stmt).scalars().all()
        return list(map(class2dict, today_items))

    def select_activate(self, owner: str, parent: Optional[int]) -> List:
        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Activate)
        activates = self.db.execute(stmt).scalars().all()
        return list(map(class2dict, activates))

    def get_item_by_name(self, name: str, parent: Optional[int], owner: str) -> Sequence[Item]:
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


    def select_done_item(self, owner: str) -> Sequence[Item]:
        stmt = sal.select(Item).where(Item.owner == owner, Item.expected_tomato == Item.used_tomato)
        return self.db.execute(stmt).scalars().all()

    def select_undone_item(self, owner: str) -> Sequence[str]:
        stmt = sal.select(Item.name).where(Item.owner == owner, Item.tomato_type == TomatoType.Today,
                                           Item.expected_tomato != Item.used_tomato,
                                           Item.item_type != ItemType.Note)
        return self.db.execute(stmt).scalars().all()

    def undo(self, xid: int, owner: str, parent: Optional[int] = None):
        item = self.select_with_authority(xid=xid, owner=owner)
        self._undo(item)
        self.event_manager.add_event(f"回退任务到列表: {item.name}", owner)
        return True
        # return self.select_activate(owner, parent=parent)

    def _undo(self, item: Item):
        item.create_time = now()
        item.tomato_type = TomatoType.Activate
        self.db.flush()

    def increase_expected_tomato(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        item.expected_tomato += 1
        self.event_manager.add_event(f"增加预计的时间: {item.name}", owner)
        self.db.flush()
        return item is not None

    def increase_used_tomato(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        if item.used_tomato < item.expected_tomato:
            item.used_tomato += 1
            logger.info(f"手动完成任务: {item.name}")
        self.db.flush()
        return item is not None

    def to_today_task(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        item.create_time = now()
        item.tomato_type = TomatoType.Today
        logger.info(f"添加任务到今日任务列表: {item.name}")
        self.db.flush()
        return item is not None
    
    def get_tomato_item(self, owner: str)-> List[Dict]:
        stmt = sal.select(Item).where(Item.owner == owner, Item.tomato_type == TomatoType.Today, Item.item_type == ItemType.Single)
        items = self.db.execute(stmt).scalars().all()
        return list(map(class2dict, items))

    def get_title(self, xid: int, owner: str) -> str:
        stmt = sal.select(Item.name).where(Item.id == xid, Item.owner == owner)
        title =  self.db.scalar(stmt)
        if title is None:
            raise UnauthorizedException("")
        return title

    def get_note(self, nid: int, owner: str) -> str:
        self.check_authority(nid, owner)
        return self.note_manager.get_note(nid)

    def update_note(self, nid: int, owner: str, content: str):
        item = self.select(nid)
        if not item or item.owner != owner:
            raise UnauthorizedException(f"User {owner} dose not have authority For nID {nid}")

        if item.item_type != ItemType.Note:
            raise UnauthorizedException(f"Item {nid} isn't a note, and can't be updated")

        self.note_manager.update_note(nid, content, owner)

    def update(self, item: Item) -> Item:
        return self.manager[item.item_type].update(item)

    def remove(self, item: Item):
        return self.manager[item.item_type].remove(item)

    def remove_by_id(self, xid: int, owner: str) -> bool:
        item = self.select_with_authority(xid, owner)
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

        self.db.flush()

    def reset_daily_task(self):
        stmt = sal.select(Item).where(Item.repeatable == True)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            item.used_tomato = 0
            item.tomato_type = TomatoType.Today
            item.create_time = now()
            logger.info(f"重置可重复任务: {item.name}")
        self.db.flush()

    def reset_today_task(self):
        stmt = sal.select(Item).where(Item.tomato_type == TomatoType.Today, Item.repeatable == False,
                                      Item.item_type != ItemType.Note)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            # 使用逻辑回退, 从而保证回退操作的逻辑是一致的
            self._undo(item)
        self.db.flush()


class SingleItemManager(BaseManager):
    def __init__(self, db):
        self.db = db

    def create(self, item: Item) -> Item:
        if item.name.startswith("http") and item.item_type == ItemType.Single:
            title = extract_title(item.name)
            item.url = item.name
            item.name = title
        self.db.add(item)
        self.db.flush()
        return item

    def update(self, item: Item) -> Item:
        self.db.flush()
        return item

    def remove(self, item: Item):
        self.db.delete(item)
        self.db.flush()
        return True


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
        if item.url is None:
            return False
        
        filename = item.url.replace("/file", FileItemManager._FILE_FOLDER)
        try:
            os.remove(filename)
            return self.manager.remove(item)
        except FileNotFoundError:
            # 对于文件没有找到这种情况, 可以删除记录
            logger.warning(f"{FileItemManager.__name__}: File Not Found: {filename}")
            return self.manager.remove(item)


class NoteItemManager(BaseManager):
    _NOTE_FOLDER = "data/notebase"

    def __init__(self, m: BaseManager, db):
        self.manager = m
        self.db = db

    def create(self, item: Item) -> Item:
        item = self.manager.create(item)
        self.__write_init_content(item)
        item.url = f"note/{item.id}"
        return self.manager.update(item)

    def update(self, item: Item) -> Item:
        return self.manager.update(item)

    def remove(self, item: Item):
        nid = item.id
        stmt = sal.select(Note).where(Note.id == nid)
        note: Note = self.db.scalar(stmt)
        if note is None:
            logger.warning(f"{NoteItemManager.__name__}: Note Not Found: {nid}")
            return False
        
        self.db.delete(note)
        self.db.flush()
        return self.manager.remove(item)

    def get_note(self, nid: int) -> str:
        # 首先尝试从数据库加载
        stmt = sal.select(Note).where(Note.id == nid)
        note: Note = self.db.scalar(stmt)
        if note is not None:
            logger.info(f"从数据库加载Note: {nid}")
            return note.content
        
        # 如果数据库加载失败, 在尝试从文件加载
        filename = os.path.join(NoteItemManager._NOTE_FOLDER, str(nid))
        with open(filename, 'r', encoding="utf-8") as f:
            logger.info(f"从文件库加载Note: {nid}")
            return f.read()

    def update_note(self, nid: int, content: str, owner:str) -> bool:
        stmt = sal.select(Note).where(Note.id == nid)
        note = self.db.scalar(stmt)
        if note is None:
            note = Note(id=nid, content=content, owner=owner)
        else:
            note.content = content
        
        self.db.add(note)
        self.db.flush()
        return True

    def __write_init_content(self, item:Item):
        content = f"<h1>{item.name}</h1>" \
            f"<div>====================</div>" \
            f"<div><br></div><div><br></div><div><br></div><div><br></div>"
        note = Note(id=item.id, content=content, owner=item.owner)
        self.db.add(note)
        self.db.flush()

