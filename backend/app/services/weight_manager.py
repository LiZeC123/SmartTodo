import sqlalchemy as sal
from sqlalchemy.orm import scoped_session, Session

from app.models.weight import WeightLog
from app.tools.exception import UnauthorizedException


Database = scoped_session[Session]

def query_log(db :Database, owner:str):
    stmt = sal.select(WeightLog).where(WeightLog.owner == owner).limit(60)
    logs = sal.execute(stmt).scalars().all()
    return logs


def add_log(db :Database, owner:str, weight:float) -> bool:
    log = WeightLog(owner=owner, weight=weight)
    db.add(log)
    return True


def remove_log(db :Database, owner:str, id: int)->bool:
    stmt = sal.select(WeightLog).where(WeightLog.owner == owner, WeightLog.id == id)
    log = sal.scalar(stmt)
    if log is None:
        raise UnauthorizedException('')
    db.delete(log)
    return True


