
import sqlalchemy as sal
from sqlalchemy.orm import Session, scoped_session

from app.models.weight import WeightLog
from app.tools.exception import UnauthorizedException

Database = scoped_session[Session]


def query_log(db: Database, owner: str) -> list[dict]:
    stmt = sal.select(WeightLog).where(WeightLog.owner == owner).order_by(WeightLog.id.desc()).limit(30)
    logs = db.execute(stmt).scalars().all()
    return [log.to_dict() for log in logs]


def add_log(db: Database, owner: str, weight: float) -> bool:
    log = WeightLog(owner=owner, weight=weight)
    db.add(log)
    db.flush()
    return True


def remove_log(db: Database, owner: str, id: int) -> bool:
    stmt = sal.select(WeightLog).where(WeightLog.owner == owner, WeightLog.id == id)
    log = db.scalar(stmt)
    if log is None:
        raise UnauthorizedException(f'User {owner} dose not have authority for weight log id {id}')
    db.delete(log)
    db.flush()
    return True
