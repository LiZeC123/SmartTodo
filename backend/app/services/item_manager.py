from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime
from itertools import groupby

import sqlalchemy as sal
from sqlalchemy.orm import Session, scoped_session

from app.models.item import Item, ItemType, TomatoType
from app.models.note import Note
from app.services.credit_manager import update_credit
from app.services.event_log_manager import add_event_log
from app.tools.exception import NotUniqueItemException, UnauthorizedException, UnmatchedException
from app.tools.file import create_download_file, create_upload_file, delete_file_from_url
from app.tools.log import logger
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
    # 区分文件上传和文件下载场景, 上传文件时有URL, 而指定下载时无URL
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


def done_item_handler(db: DataBase, item: Item):
    if item.repeatable or item.url is None:
        update_credit(db, item.owner, 1, f"完成任务 {item.name}")

class ItemManager:
    def __init__(self, db: scoped_session[Session]):
        self.db = db

        self.before_create_event: list[ItemEvent] = [http_url_handler, download_file_handler]
        self.after_create_event: list[ItemEvent] = [create_note_handler]
        self.on_done_event: list[ItemEvent] = [done_item_handler]
        self.on_delete_event: list[ItemEvent] = [remove_file_handler, remove_note_handler]

    def create(self, item: Item) -> Item:
        for f in self.before_create_event:
            f(self.db, item)

        self.db.add(item)
        self.db.flush()

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
        logger.info(f"删除任务: {item.name}")


    def create_upload_file(self, f, parent: int | None, owner: str) -> Item:
        name, url = create_upload_file(f)
        item = Item(name=name, item_type=ItemType.File, owner=owner, parent=parent, url=url)
        return self.create(item)

    def select(self, iid: int) -> Item | None:
        return self.db.scalar(sal.select(Item).where(Item.id == iid))

    def select_with_authority(self, xid: int, owner: str) -> Item:
        """查询指定Item并检查用户信息是否匹配, 不匹配时抛出异常"""
        stmt = sal.select(Item).where(Item.id == xid, Item.owner == owner)
        item = self.db.scalar(stmt)
        if item is None:
            raise UnauthorizedException(f"User {owner} dose not have authority For xID {xid}")

        return item

    def select_all(self, owner: str, parent: int | None):
        return {
            "todayTask": self.select_today(owner, parent),
            "activeTask": self.select_activate(owner, parent)
        }

    def select_today(self, owner: str, parent: int | None) -> list:
        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Today)
        today_items = self.db.execute(stmt).scalars().all()
        return [i.to_dict() for i in today_items]

    def select_activate(self, owner: str, parent: int | None) -> list:
        stmt = sal.select(Item).where(Item.owner == owner, Item.parent == parent,
                                      Item.tomato_type == TomatoType.Activate)
        activates = self.db.execute(stmt).scalars().all()
        return [i.to_dict() for i in activates]

    def get_item_by_name(self, name: str, parent: int | None, owner: str) -> Sequence[Item]:
        stmt = sal.select(Item).where(Item.name.like(f"%{name}%"), Item.parent == parent, Item.owner == owner)
        return self.db.execute(stmt).scalars().all()

    def get_unique_item_by_name(self, name: str, parent: int | None, owner: str) -> Item:
        items = self.get_item_by_name(name, parent, owner)
        if len(items) == 1:
            return items[0]

        item_str = ' '.join([item.name for item in items])
        raise NotUniqueItemException(f"[{item_str}]均查询条件(name={name}, parent={parent}, owner={owner})")

    def get_unique_or_null_item_by_name(self, name: str, parent: int | None, owner: str) -> Item | None:
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

    def select_done_itme_after(self, owner: str, after: datetime) -> Sequence[Item]:
        stmt = sal.select(Item).where(Item.owner == owner, Item.expected_tomato == Item.used_tomato, Item.update_time > after).order_by(Item.update_time.asc())
        return self.db.execute(stmt).scalars().all()

    def select_undone_item(self, owner: str) -> Sequence[str]:
        stmt = sal.select(Item.name).where(Item.owner == owner, Item.tomato_type == TomatoType.Today,
                                           Item.expected_tomato != Item.used_tomato,
                                           Item.item_type != ItemType.Note)
        return self.db.execute(stmt).scalars().all()

    def select_checkin_item(self, owner: str) -> Sequence[str]:
        stmt = sal.select(Item.name).where(Item.owner == owner, Item.name.like("每日%"))
        return self.db.scalars(stmt).all()

    def select_recent_note_config(self, owner: str) -> list[dict]:
        # 生成一个标量子查询, 可以用于in等条件中. 默认的字查询仅可用于FROM语句中
        sub = sal.select(Item.parent.distinct()).where(Item.owner==owner, Item.parent.is_not(None)).order_by(Item.id.desc()).limit(4).scalar_subquery()
        stmt = sal.select(Item).where(Item.id.in_(sub))
        items = self.db.scalars(stmt).all()
        return [{'title': item.name, 'path': f"note/{item.id}"} for item in items ]

    def undo(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        self._undo(item)
        add_event_log(self.db, owner, f'用户回退任务[{item.name}]到待执行列表')
        return True

    def _undo(self, item: Item):
        item.update_time = now()
        item.tomato_type = TomatoType.Activate
        self.db.flush()

    def increase_expected_tomato(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        item.expected_tomato += 1
        if item.used_tomato > 0:
            add_event_log(self.db, owner, f'用户增加任务[{item.name}]的预计番茄钟数量, 该任务预计需要{item.expected_tomato}个番茄钟, 已完成{item.used_tomato}个番茄钟')
        self.db.flush()
        return item is not None

    def increase_used_tomato(self, xid: int, owner: str):
        """已使用番茄钟计数增加1, 用于番茄钟完成后更新状态场景"""
        item = self.select_with_authority(xid=xid, owner=owner)
        if item.used_tomato >= item.expected_tomato:
            return False

        item.used_tomato += 1
        item.update_time = now()
        self.db.flush()

        add_event_log(self.db, owner, f'用户完成番茄钟任务[{item.name}], 该任务预计需要{item.expected_tomato}个番茄钟, 已完成{item.used_tomato}个番茄钟')
        return True

    def finish_used_tomato(self, xid: int, owner: str):
        """手动结束一个任务, 用于在界面上手动点击完成的场景"""
        item = self.select_with_authority(xid=xid, owner=owner)
        if item.used_tomato >= item.expected_tomato:
            return False

        if item.expected_tomato == 1:
            # 如果当前是一个普通的任务, 即不需要消耗多个番茄钟, 则设置为完成状态
            item.used_tomato = 1
            item.update_time = now()
            add_event_log(self.db, owner, f'用户标记完成任务[{item.name}]')
        elif item.used_tomato == 0:
            # 直接手动完成了一个预计需要多个番茄钟的任务
            delta = item.expected_tomato
            item.used_tomato = 1
            item.expected_tomato = 1
            add_event_log(self.db, owner, f'用户标记提前完成任务[{item.name}]并废弃{delta}个预计的番茄钟')
        else:
            # 当前任务规划需要多个番茄钟, 并且已经完成了一部分番茄钟
            # 此时手动点击完成, 则视为放弃原本预计需要的番茄钟, 直接调整为完成状态
            # 例如原本预计4个番茄钟, 已经使用了两个番茄钟, 则直接将预期番茄钟数量调整为2并将任务设置为完成
            delta = item.expected_tomato - item.used_tomato
            item.expected_tomato = item.used_tomato
            add_event_log(self.db, owner, f'用户标记提前完成任务[{item.name}]并废弃{delta}个预计的番茄钟')
        self.db.flush()

        for f in self.on_done_event:
            f(self.db, item)

        logger.info(f"完成任务: {item.name}")
        return True

    def to_today_task(self, xid: int, owner: str):
        item = self.select_with_authority(xid=xid, owner=owner)
        item.update_time = now()
        item.tomato_type = TomatoType.Today
        deadline = item.deadline.strftime("%Y-%m-%d %H:%M:%S") if item.deadline is not None else "未指定"
        add_event_log(self.db, owner, f'用户添加任务[{item.name}]到今日任务列表, 该任务预计需要{item.expected_tomato}个番茄钟, 已完成{item.used_tomato}个番茄钟, 截止日期为{deadline}, 优先级为{item.priority}')
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

    def get_tomato_item(self, owner: str) -> list[dict]:
        stmt = sal.select(Item).where(Item.owner == owner, Item.tomato_type == TomatoType.Today,
                                      Item.item_type == ItemType.Single)
        items = self.db.execute(stmt).scalars().all()
        return self.__group_sub_task(items, owner)

    def get_item_with_sub_task(self, owner: str) -> list[dict]:
        stmt = sal.select(Item).where(Item.owner == owner, Item.tomato_type == TomatoType.Today,
                                      Item.item_type == ItemType.Single)
        items = self.db.execute(stmt).scalars().all()
        return self.__group_sub_task(items, owner)

    def __group_sub_task(self, items: Sequence[Item], owner):
        groups = []
        globalItem = Item(id=0, name="全局任务", item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner)
        for parent_id, g in groupby(sorted(items, key=lambda x: x.parent if x.parent is not None else 0),
                              key=lambda x: x.parent):

            parent_item = self.select(parent_id) if parent_id is not None else None
            if parent_item is not None:
                groups.append({"self": parent_item.to_dict(), "children": [i.to_dict() for i in g]})
            else:
                groups.append({"self": globalItem.to_dict(), "children": [i.to_dict() for i in g]})

        return groups

    def get_deadline_item(self, owner: str) -> Sequence[dict]:
        next_week = the_day_after(now(), 7)
        stmt = sal.select(Item).where(Item.owner == owner, Item.expected_tomato > Item.used_tomato,
                                      Item.deadline != None)  # noqa: E711
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
        add_event_log(self.db, owner, f'用户手动删除任务[{item.name}]')
        return True

    def garbage_collection(self):
        # 1. 不是不可回收的特殊类型
        # 2. 处于完成状态
        stmt = sal.select(Item).where(Item.repeatable == False, Item.specific == 0,  # noqa: E712
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
        stmt = sal.select(Item).where(Item.repeatable == True)  # noqa: E712
        items = self.db.execute(stmt).scalars().all()
        for item in items:
            item.used_tomato = 0
            item.tomato_type = TomatoType.Today
            item.update_time = now()
            add_event_log(self.db, item.owner, f'系统自动重置可重复任务[{item.name}]为未完成状态')
            logger.info(f"重置可重复任务: {item.name}")
        self.db.commit()  # 定时器触发任务, 必须commit, 否则操作会被回滚

    def reset_today_task(self):
        stmt = sal.select(Item).where(Item.tomato_type == TomatoType.Today, Item.repeatable == False,  # noqa: E712
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


