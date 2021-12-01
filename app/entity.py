from typing import Dict, Optional, List

from tool4time import now_str


class Item:
    def __init__(self, item_id, name, item_type, owner, /,
                 tomato_type: str = "activate", deadline: Optional[str] = None, repeatable: bool = False,
                 specific: int = 0, work: bool = False, url: Optional[str] = None, parent: int = 0):
        self.id: int = item_id
        self.name: str = name
        self.item_type: str = item_type         # single, file, note 三种类型
        self.tomato_type: str = tomato_type     # activate, urgent, today 三种类型
        self.create_time: str = now_str()
        self.deadline: Optional[str] = deadline
        self.repeatable: bool = repeatable
        self.specific: int = specific
        self.work: bool = work
        self.url: Optional[str] = url
        self.parent: int = parent  # 指示此Item是否附属于某个note, 0表示不附属任何note
        self.pTask: int = 0  # 指示此Item是否是某个Item的子任务, 0表示不附属任何Item
        self.expected_tomato: int = 1
        self.used_tomato: int = 0
        self.owner: str = owner

    def to_dict(self) -> Dict:
        # 添加一个字典到对象的方法, 从而便于添加字段
        return self.__dict__

    def __str__(self) -> str:
        return str(self.to_dict())


def from_dict(raw: Dict) -> Item:
    item = Item(int(raw['id']), raw['name'], raw['item_type'], raw['owner'])
    if "tomato_type" in raw:
        item.tomato_type = raw['tomato_type']
    if "create_time" in raw:
        item.create_time = raw['create_time']
    if "deadline" in raw:
        item.deadline = raw['deadline']
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
    if "pTask" in raw:
        item.subTask = int(raw['pTask'])
    if "expected_tomato" in raw:
        item.expected_tomato = int(raw['expected_tomato'])
    if "used_tomato" in raw:
        item.used_tomato = int(raw['used_tomato'])
    return item
