import sqlalchemy as sal

from app.models.exception import UnauthorizedException
from app.models.weight import WeightLog
from app.services.event_log_manager import EventManager


class WeightManager:
    def __init__(self, em: EventManager) -> None:
        self.db = em.db
        self.event_manager = em

    def query_log(self, owner: str) -> list[dict]:
        stmt = sal.select(WeightLog).where(WeightLog.owner == owner).order_by(WeightLog.id.desc()).limit(30)
        logs = self.db.execute(stmt).scalars().all()
        return [log.to_dict() for log in logs]

    def add_log(self, owner: str, weight: float) -> bool:
        log = WeightLog(owner=owner, weight=weight)
        self.db.add(log)
        self.event_manager.add_event_log(owner, f"用户更新当前体重为 {weight:.1f} 斤")
        # 两个插入操作一起flush, 因此无需再手动flush
        return True

    def remove_log(self, owner: str, id: int) -> bool:
        stmt = sal.select(WeightLog).where(WeightLog.owner == owner, WeightLog.id == id)
        log = self.db.scalar(stmt)
        if log is None:
            raise UnauthorizedException(f"User {owner} dose not have authority for weight log id {id}")
        self.db.delete(log)
        self.db.flush()
        return True
