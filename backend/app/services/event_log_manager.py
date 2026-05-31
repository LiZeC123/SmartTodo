from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sal

from app.models.base import Database
from app.models.event import EventLog


class EventManager:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add_event_log(self, owner: str, msg: str) -> bool:
        event = EventLog(owner=owner, msg=msg)
        self.db.add(event)
        self.db.flush()
        return True

    def get_event_log_after(self, time: datetime, owner: str) -> Sequence[EventLog]:
        stmt = sal.select(EventLog).where(EventLog.owner == owner, EventLog.create_time > time)
        return self.db.execute(stmt).scalars().all()
