from collections.abc import Sequence
from datetime import datetime

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

def get_checkin_datetime(db: Database, name: str, start: datetime, end:datetime, owner: str)-> Sequence[datetime]:
    stmt = sal.select(EventLog.create_time) \
              .where(EventLog.owner == owner,
                     EventLog.create_time > start, EventLog.create_time < end,
                     EventLog.msg.like(f"%完成%{name}%"))
    return db.scalars(stmt).all()
