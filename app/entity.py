from typing import Dict, Optional

from tool4time import now_str


class Item:
    def __init__(self, item_id, name, item_type, owner, /,
                 deadline: Optional[str] = None, old: bool = False, repeatable: bool = False, specific: int = 0,
                 work: bool = False, url: Optional[str] = None, parent: int = 0):
        self.id: int = item_id
        self.name: str = name
        self.item_type: str = item_type  # single, file, note 共三种类型
        self.create_time: str = now_str()
        self.finish_time: Optional[str] = None
        self.deadline: Optional[str] = deadline
        self.old: bool = old
        self.repeatable: bool = repeatable
        self.specific: int = specific
        self.work: bool = work
        self.url: Optional[str] = url
        self.parent: int = parent  # 指示此Item是否附属于某个note, 0表示不附属任何note
        self.owner: str = owner

    def to_dict(self) -> Dict:
        # 添加一个字典到对象的方法, 从而便于添加字段
        return self.__dict__

    def __str__(self) -> str:
        return str(self.to_dict())


def from_dict(raw: Dict) -> Item:
    item = Item(int(raw['id']), raw['name'], raw['item_type'], raw['owner'])
    if "create_time" in raw:
        item.create_time = raw['create_time']
    if "finish_time" in raw:
        item.finish_time = raw['finish_time']
    if "deadline" in raw:
        item.deadline = raw['deadline']
    if "old" in raw:
        item.old = bool(raw['old'])
    if "repeatable" in raw:
        item.repeatable = bool(raw['repeatable'])
    if "specific" in raw:
        item.specific = int(raw['specific'])
    if "work" in raw:
        item.work = bool(raw["work"])
    if "url" in raw:
        item.url = raw['url']
    if "parent" in raw:
        item.parent = int(raw['parent'])
    return item
