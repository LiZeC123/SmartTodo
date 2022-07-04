from entity import *

from tool4time import get_datetime_from_str, now_str


def test_class2dict():
    item = Item(name="A", item_type=ItemType.Single, owner="lizec")
    d = class2dict(item)
    assert d['name'] == item.name
    assert d['item_type'] == item.item_type
    assert d['owner'] == item.owner

    now_time = get_datetime_from_str(now_str())
    tomato = TomatoTaskRecord(start_time=now_time, owner="lizec")
    d = class2dict(tomato)
    assert get_datetime_from_str(d['start_time']) == now_time
    assert d['owner'] == tomato.owner
