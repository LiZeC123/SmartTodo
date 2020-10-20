# -*- coding: UTF-8 -*-
from typing import Dict


class AttrDisplayMixIn:
    def gather_attrs(self):
        return ",".join("{}={}".format(k, getattr(self, k)) for k in self.__dict__.keys())

    def __str__(self):
        return "[{}:{}]".format(self.__class__.__name__, self.gather_attrs())

    def __repr__(self):
        return "[{}:{}]".format(self.__class__.__name__, self.gather_attrs())


class Item(AttrDisplayMixIn):
    def __init__(self, item_id, name, item_type, create_time=None, deadline=None, old=False,
                 repeatable=False, specific=0, work=False, url=None, parent=None):
        self.id = item_id
        self.name = name
        self.item_type = item_type
        self.create_time = create_time
        self.finish_time = None
        self.auto_priority = None
        self.urgent = -1  # 表示紧急程度的等级,一共0~3四个等级
        self.deadline = deadline
        self.old = old
        self.repeatable = repeatable
        self.specific = specific
        self.work = work
        self.url = url
        self.parent = parent

    def to_dict(self) -> Dict:
        # 添加一个字典到对象的方法, 从而便于添加字段
        return {
            "id": self.id,
            "name": self.name,
            "itemType": self.item_type,
            "createTime": self.create_time,
            "finishTime": self.finish_time,
            "autoPriority": self.auto_priority,
            "urgent": self.urgent,
            "deadline": self.deadline,
            "old": self.old,
            "repeatable": self.repeatable,
            "specific": self.specific,
            "work": self.work,
            "url": self.url,
            "parent": self.parent
        }

    def __str__(self) -> str:
        return str(self.to_dict())


def from_dict(raw: Dict) -> Item:
    item = Item(raw['id'], raw['name'], raw['itemType'], None)
    if "createTime" in raw:
        item.create_time = raw['createTime']
    if "finishTime" in raw:
        item.finish_time = raw['finishTime']
    if "autoPriority" in raw:
        item.auto_priority = raw['autoPriority']
    if "urgent" in raw:
        item.urgent = raw['urgent']
    if "deadline" in raw:
        item.deadline = raw['deadline']
    if "old" in raw:
        item.old = raw['old']
    if "repeatable" in raw:
        item.repeatable = raw['repeatable']
    if "specific" in raw:
        item.specific = raw['specific']
    if "work" in raw:
        item.work = raw["work"]
    if "url" in raw:
        item.url = raw['url']
    if "parent" in raw:
        item.parent = raw['parent']
    return item
