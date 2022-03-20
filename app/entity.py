from typing import Dict, Optional, List

from tool4time import now_str, zero_time


class Item:
    def __init__(self, item_id, name, item_type, owner, /,
                 tomato_type: str = "activate", deadline: Optional[str] = None, repeatable: bool = False,
                 specific: int = 0, url: Optional[str] = None, parent: int = 0):
        self.id: int = item_id
        self.name: str = name

        # single, file, note 三种类型
        self.item_type: str = item_type

        # activate, urgent, today 三种类型
        self.tomato_type: str = tomato_type

        self.create_time: str = now_str()
        self.deadline: Optional[str] = deadline
        self.repeatable: bool = repeatable
        self.specific: int = specific
        self.url: Optional[str] = url

        # 指示此Item是否附属于某个note, 0表示不附属任何note
        self.parent: int = parent

        # 番茄钟相关属性
        self.expected_tomato: int = 1
        self.used_tomato: int = 0

        # 打卡相关属性
        self.habit_done: int = 0
        self.habit_expected: int = 0
        self.last_check_time: str = zero_time()

        self.owner: str = owner

    def to_dict(self) -> Dict:
        return self.__dict__

    def __str__(self) -> str:
        return str(self.to_dict())

    def done_item(self) -> bool:
        return self.expected_tomato == self.used_tomato


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
    if "url" in raw:
        item.url = raw['url']
    if "parent" in raw:
        item.parent = int(raw['parent'])
    if "expected_tomato" in raw:
        item.expected_tomato = int(raw['expected_tomato'])
    if "used_tomato" in raw:
        item.used_tomato = int(raw['used_tomato'])
    if "habit_done" in raw:
        item.habit_done = int(raw['habit_done'])
    if "habit_expected" in raw:
        item.habit_expected = int(raw['habit_expected'])
    if "last_check_time" in raw:
        item.last_check_time = raw['last_check_time']
    return item
