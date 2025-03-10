from app.models.base import ItemType
from app.models.item import Item
from app.tools.time import get_datetime_from_str, now_str


def test_to_dict():
    item = Item(name="A", item_type=ItemType.Single, owner="lizec")
    d = item.to_dict()
    assert d['name'] == item.name
    assert d['item_type'] == item.item_type
    assert d['owner'] == item.owner