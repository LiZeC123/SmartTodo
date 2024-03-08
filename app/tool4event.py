from typing import List

import sqlalchemy as sal
from sqlalchemy.orm import Session

from entity import TomatoEvent
from tool4time import now, today_begin



class EventManager:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_event(self, content: str, owner: str):
        e = TomatoEvent(time = now(), content=content, owner=owner)
        self.db.add(e)
        self.db.commit()

    def get_today_event(self, owner: str) -> List[TomatoEvent]:
        stmt = sal.select(TomatoEvent).where(TomatoEvent.owner == owner, TomatoEvent.time > today_begin()) \
                .order_by(TomatoEvent.id.asc())
        return self.db.execute(stmt).scalars().all()