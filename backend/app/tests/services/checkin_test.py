from app.services.checkin_manager import CheckinManager
from app.services.config_manager import ConfigManager
from app.services.event_log_manager import EventManager
from app.services.item_manager import ItemManager
from app.tests.services.make_db import make_new_db
from app.tools.time import now

config_manager = ConfigManager()
event_manager = EventManager(make_new_db())
item_manager = ItemManager(event_manager)
checkin_manager = CheckinManager(config_manager, item_manager)
owner = "user"


def test_checkin_base():
    checkin_manager.get_all_data(owner=owner)
    checkin_manager.get_month_data("", now(), owner=owner)
