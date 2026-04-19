from datetime import datetime
from typing import Sequence

import sqlalchemy as sal
from sqlalchemy.orm import Session, scoped_session

from app.models.event import EventLog

Database = scoped_session[Session]


def add_event_log(db: Database, owner: str, msg: str) -> bool:
    event = EventLog(owner=owner, msg=msg)
    db.add(event)
    db.flush()
    return True


def get_event_log_after(db: Database, time: datetime, owner: str) -> Sequence[EventLog]:
    stmt = sal.select(EventLog).where(EventLog.owner == owner, EventLog.create_time > time)
    return db.execute(stmt).scalars().all()
