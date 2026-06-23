
import app.tools.time as time
from app.models.item import Item, ItemType, TomatoType
from app.services.checkin_manager import CheckinManager
from app.services.config_manager import ConfigManager
from app.services.event_log_manager import EventManager
from app.services.item_manager import ItemManager
from app.services.weight_manager import WeightManager
from app.tests.services.make_db import make_new_db

config_manager = ConfigManager()
event_manager = EventManager(make_new_db())
item_manager = ItemManager(event_manager)
checkin_manager = CheckinManager(config_manager, item_manager)
weight_manager = WeightManager(event_manager)
owner = "user"


def make_base_item(name):
    return Item(name=name, item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner)


def test_checkin_base():
    itemA = make_base_item("每日早起打卡")
    itemB = make_base_item("每日运动打卡")
    item_manager.create(itemA)
    item_manager.create(itemB)
    item_manager.finish_used_tomato(itemA.id, owner)
    item_manager.finish_used_tomato(itemB.id, owner)
    event_manager.add_event_log(owner, itemB.name)
    weight_manager.add_log(owner, 123.45)

    assert checkin_manager.get_all_data(owner)
    assert checkin_manager.get_month_data(itemA.name, time.now(), owner)

    assert checkin_manager.get_stat(itemB.name, owner)

    checkin_manager.update_all_checkin_state()
    assert checkin_manager.get_stat(itemA.name, owner)
