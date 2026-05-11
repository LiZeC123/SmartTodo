import random
from datetime import datetime

from sqlalchemy.orm import Session, scoped_session

from app.services.event_log_manager import get_checkin_datetime
from app.services.item_manager import ItemManager
from app.tools.time import get_month_bounds, now, the_month_begin

Database = scoped_session[Session]


icon_map = {"运动": "🏃🏻‍♀️", "早起": "🛏", "琴": "🎵", "体重": "🏋"}

normal_emoji = ["🎯", "📅", "✏️"]


class CheckinManager:
    def __init__(self, db: Database, item_manager: ItemManager) -> None:
        self.db = db
        self.item_manager = item_manager

    def get_all_data(self, owner: str):
        names = self.item_manager.select_checkin_item(owner)
        start = the_month_begin()
        end = now()
        return {name: self.get_data(name, start, end, owner) for name in names}


    def get_month_data(self, name: str, month: datetime, owner: str):
        start, end = get_month_bounds(month)
        record = get_checkin_datetime(self.db, name, start, end, owner)
        return [r.strftime("%Y-%m-%d %H:%M:%S") for r in record]

    def get_data(self, name: str, start: datetime, end: datetime, owner: str):
        record = get_checkin_datetime(self.db, name, start, end, owner)
        emoji = self.get_emoji(name)
        return {'record': [r.strftime("%Y-%m-%d %H:%M:%S") for r in record], 'emoji': emoji, 'process': 3}

    def get_emoji(self, name: str) -> str:
        for k, v in icon_map.items():
            if k in name:
                return v

        return random.choice(normal_emoji)
