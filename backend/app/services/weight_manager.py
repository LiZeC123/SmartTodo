from typing import List

import sqlalchemy as sal
from sqlalchemy.orm import scoped_session, Session

from app.models.weight import WeightLog
from app.tools.exception import UnauthorizedException

Database = scoped_session[Session]


def query_log(db: Database, owner: str) -> List:
    stmt = sal.select(WeightLog).where(WeightLog.owner == owner).order_by(WeightLog.id.desc()).limit(30)
    logs = db.execute(stmt).scalars().all()
    return [log.to_dict() for log in logs]


def add_log(db: Database, owner: str, weight: float) -> bool:
    log = WeightLog(owner=owner, weight=weight)
    db.add(log)
    return True


def remove_log(db: Database, owner: str, id: int) -> bool:
    stmt = sal.select(WeightLog).where(WeightLog.owner == owner, WeightLog.id == id)
    log = db.scalar(stmt)
    if log is None:
        raise UnauthorizedException(f'User {owner} dose not have authority for weight log id {id}')
    db.delete(log)
    return True
