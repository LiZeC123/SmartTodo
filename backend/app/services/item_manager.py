from collections import defaultdict
from itertools import groupby
from typing import Optional, Dict, List, Sequence, Callable

import sqlalchemy as sal
from sqlalchemy.orm import scoped_session, Session

from app.models.base import ItemType, TomatoType
from app.models.item import Item
from app.models.note import Note
from app.tools.exception import UnauthorizedException, NotUniqueItemException, UnmatchedException
from app.tools.file import create_download_file, delete_file_from_url, create_upload_file
from app.tools.logger import logger
from app.tools.time import now, the_day_after, today_begin
from app.tools.web import extract_title

DataBase = scoped_session[Session]

ItemEvent = Callable[[DataBase, Item], None]


def http_url_handler(_: DataBase, item: Item):
    if item.name.startswith("http") and item.item_type == ItemType.Single:
        title = extract_title(item.name)
        item.url = item.name
        item.name = title


def download_file_handler(_: DataBase,item: Item):
    # 区分文件上传的场景, 上传文件时有URL, 而指定下载时无URL
    if item.item_type == ItemType.File and item.url is None:
        item.url = create_download_file(item.name)


def remove_file_handler(_: DataBase,item: Item):
    if item.item_type == ItemType.File and item.url is not None:
        delete_file_from_url(item.url)


def create_note_handler(db: DataBase, item: Item):
    if item.item_type == ItemType.Note:
        content = f"<h1>{item.name}</h1>" \
                  f"<div>====================</div>" \
                  f"<div><br></div><div><br></div><div><br></div><div><br></div>"
        note = Note(id=item.id, content=content, owner=item.owner)
        db.add(note)
        item.url = f"note/{item.id}"

def remove_note_handler(db: DataBase, item: Item):
    if item.item_type == ItemType.Note:
        stmt = sal.delete(Note).where(Note.id == item.id)
        db.execute(stmt)

class ItemManager:
    def __init__(self, db: scoped_session[Session]):
        self.db = db

        self.before_create_event: List[ItemEvent] = [http_url_handler, download_file_handler]
        self.after_create_event: List[ItemEvent] = [create_note_handler]
        self.on_done_event: List[ItemEvent] = []
        self.on_delete_event: List[ItemEvent] = [remove_file_handler, remove_note_handler]

    def create(self, item: Item) -> Item:
        for f in self.before_create_event:
            f(self.db, item)

        self.db.add(item)

        for g in self.after_create_event:
            g(self.db, item)

        self.db.flush()

        return item

    def update(self, item: Item) -> Item:
        self.db.flush()
        return item

    def remove(self, item: Item):
        self.db.delete(item)

        for f in self.on_delete_event:
            f(self.db, item)

        self.db.flush()


    def create_upload_file(self, f, parent: Optional[int], owner: str) -> Item:
        name, url = create_upload_file(f)
        item = Item(name=name, item_type=ItemType.File, owner=owner, parent=parent, url=url)
        return self.create(item)

    def select(self, iid: int) -> Optional[Item]:
        return self.db.scalar(sal.select(Item).where(Item.id == iid))

    def select_with_authority(self, xid: int, owner: str) -> Item:
        """查询指定Item并检查用户信息是否匹配, 不匹配时抛出异常"""
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
        return [i.to_dict() for i in today_items]

    def select_activate(self, owner: str, parent: Optional[int]) -> List:
        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Activate)
        activates = self.db.execute(stmt).scalars().all()
        return [i.to_dict() for i in activates]

    def get_item_by_name(self, name: str, parent: Optional[int], owner: str) -> Sequence[Item]:
        stmt = sal.select(Item).where(Item.name.like(f"%{name}%"), Item.parent == parent, Item.owner == owner)
        return self.db.execute(stmt).scalars().all()

    def get_unique_item_by_name(self, name: str, parent: Optional[int], owner: str) -> Item:
        items = self.get_item_by_name(name, parent, owner)
        if len(items) == 1:
            return items[0]

        item_str = ' '.join([item.name for item in items])
        raise NotUniqueItemException(f"[{item_str}]均查询条件(name={name}, parent={parent}, owner={owner})")

    def get_unique_or_null_item_by_name(self, name: str, parent: Optional[int], owner: str) -> Optional[Item]:
        items = self.get_item_by_name(name, parent, owner)
        if len(items) == 0:
            return None
        if len(items) == 1:
            return items[0]

        # 如果一个任务已经执行了拆分, 那么按照原始的字符串匹配, 就会有多个命中, 导致无法追加新任务
        # 因此需要特殊处理这种情况
        kernel_items = [item for item in items if "：" not in item.name]
        if len(kernel_items) == 1:
            return kernel_items[0]

        item_str = ' '.join([item.name for item in items])
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
            ans[parent] = [i.to_dict() for i in lists]
        return ans

    def select_done_item(self, owner: str) -> Sequence[Item]:
        stmt = sal.select(Item).where(Item.owner == owner, Item.expected_tomato == Item.used_tomato)
        return self.db.execute(stmt).scalars().all()

    def select_undone_item(self, owner: str) -> Sequence[str]:
        stmt = sal.select(Item.name).where(Item.owner == owner, Item.tomato_type == TomatoType.Today,
                                           Item.expected_tomato != Item.used_tomato,
                                           Item.item_type != ItemType.Note)
        return self.db.execute(stmt).scalars().all()

    def undo(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        self._undo(item)
        # self.event_manager.add_event(f"回退任务到列表: {item.name}", owner)
        return True
        # return self.select_activate(owner, parent=parent)

    def _undo(self, item: Item):
        item.update_time = now()
        item.tomato_type = TomatoType.Activate
        self.db.flush()

    def increase_expected_tomato(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        item.expected_tomato += 1
        # self.event_manager.add_event(f"增加预计的时间: {item.name}", owner)
        self.db.flush()
        return item is not None

    def increase_used_tomato(self, xid: int, owner: str):
        """已使用番茄钟计数增加1, 用于番茄钟完成后更新状态场景"""
        item = self.select_with_authority(xid=xid, owner=owner)
        if item.used_tomato >= item.expected_tomato:
            return False

        item.used_tomato += 1
        self.db.flush()
        logger.info(f"完成任务: {item.name}")
        return True

    def finish_used_tomato(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        if item.used_tomato >= item.expected_tomato:
            return False

        if item.expected_tomato == 1:
            # 如果当前是一个普通的任务, 即不需要消耗多个番茄钟, 则设置为完成状态
            item.used_tomato = 1
        else:
            # 否则收缩预期的番茄钟数量为当前值, 例如已经消耗2个番茄钟, 而预期消耗4个番茄钟
            # 此时完成任务, 则将预期番茄钟数量调整为2
            item.expected_tomato = item.used_tomato
        self.db.flush()
        logger.info(f"全部完成任务: {item.name}")
        return True

    def to_today_task(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        item.update_time = now()
        item.tomato_type = TomatoType.Today
        logger.info(f"添加任务到今日任务列表: {item.name}")
        self.db.flush()
        return item is not None

    def renew(self, xid: int, owner: str, renew_day: int):
        """将给定任务的截止日期续期指定天数"""
        item = self.select_with_authority(xid, owner)
        if item.deadline is None:
            item.deadline = today_begin()
        item.used_tomato = 0
        item.deadline = the_day_after(item.deadline, renew_day)
        self.update(item)

    def get_tomato_item(self, owner: str) -> List[Dict]:
        stmt = sal.select(Item).where(Item.owner == owner, Item.tomato_type == TomatoType.Today,
                                      Item.item_type == ItemType.Single, Item.expected_tomato > Item.used_tomato)
        items = self.db.execute(stmt).scalars().all()
        return self.__group_sub_task(items, owner)

    def get_item_with_sub_task(self, owner: str) -> List[Dict]:
        stmt = sal.select(Item).where(Item.owner == owner, Item.tomato_type == TomatoType.Today,
                                      Item.item_type == ItemType.Single)
        items = self.db.execute(stmt).scalars().all()
        return self.__group_sub_task(items, owner)

    def __group_sub_task(self, items: Sequence[Item], owner):
        groups = []
        globalItem = Item(id=0, name="全局任务", item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner)
        for iid, g in groupby(sorted(items, key=lambda x: x.parent if x.parent is not None else 0),
                              key=lambda x: x.parent):
            item = None
            if iid is not None:
                item = self.select(iid)
            if item is not None:
                groups.append({"self": item.to_dict(), "children": [i.to_dict() for i in g]})
            else:
                groups.append({"self": globalItem.to_dict(), "children": [i.to_dict() for i in g]})

        return groups

    def get_deadline_item(self, owner: str) -> Sequence[Dict]:
        next_week = the_day_after(now(), 7)
        stmt = sal.select(Item).where(Item.owner == owner, Item.expected_tomato > Item.used_tomato,
                                      Item.deadline != None)
        items = self.db.execute(stmt).scalars().all()
        return [i.to_dict() for i in items if i.deadline and i.deadline < next_week]

    def get_title(self, xid: int, owner: str) -> str:
        item = self.select_with_authority(xid, owner)
        return item.name

    def must_get_note(self, nid: int) -> Note:
        stmt = sal.select(Note).where(Note.id == nid)
        note = self.db.scalar(stmt)
        if note is None:
            raise UnmatchedException(f"Note Not Found: {nid}")
        return note


    def get_note(self, nid: int, owner: str) -> str:
        self.select_with_authority(nid, owner)
        note = self.must_get_note(nid)
        return note.content

    def update_note(self, nid: int, owner: str, content: str):
        self.select_with_authority(nid, owner)
        note = self.must_get_note(nid)
        note.content = content
        self.db.flush()


    def remove_by_id(self, xid: int, owner: str) -> bool:
        item = self.select_with_authority(xid, owner)
        self.remove(item)
        return True

    def garbage_collection(self):
        # 1. 不是不可回收的特殊类型
        # 2. 处于完成状态
        stmt = sal.select(Item).where(Item.repeatable == False, Item.specific == 0,
                                      Item.used_tomato == Item.expected_tomato)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            self.remove(item)
            logger.info(f"垃圾回收(已过期的任务): {item.name}")

        stmt = sal.select(Item.id)
        ids = self.db.execute(stmt).scalars().all()
        stmt = sal.select(Item).where(Item.parent.not_in(ids))
        unreferenced = self.db.execute(stmt).scalars().all()
        for item in unreferenced:
            self.remove(item)
            logger.info(f"垃圾回收(无引用的任务): {item.name}")

        self.db.commit()  # 定时器触发任务, 必须commit, 否则操作会被回滚

    def reset_daily_task(self):
        stmt = sal.select(Item).where(Item.repeatable == True)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            item.used_tomato = 0
            item.tomato_type = TomatoType.Today
            item.update_time = now()
            logger.info(f"重置可重复任务: {item.name}")
        self.db.commit()  # 定时器触发任务, 必须commit, 否则操作会被回滚

    def reset_today_task(self):
        stmt = sal.select(Item).where(Item.tomato_type == TomatoType.Today, Item.repeatable == False,
                                      Item.item_type != ItemType.Note)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            # 使用逻辑回退, 从而保证回退操作的逻辑是一致的
            self._undo(item)
        self.db.commit()  # 定时器触发任务, 必须commit, 否则操作会被回滚

    def renew_sp_task(self):
        stmt = sal.select(Item).where(Item.specific > 0, Item.item_type != ItemType.Note,
                                      Item.used_tomato == Item.expected_tomato)
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            self.renew(item.id, item.owner, item.specific)
            logger.info(f'续期周期性任务: {item.name} 续期 {item.specific} 天')
        self.db.commit()  # 定时器触发任务, 必须commit, 否则操作会被回滚


