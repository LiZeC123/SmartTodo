import json
import math
from collections.abc import Sequence
from datetime import datetime, timedelta

import sqlalchemy as sal

from app.models.exception import IllegalArgumentException, UnauthorizedException
from app.models.weight import WeightLog, WeightPlan
from app.services.event_log_manager import EventManager
from app.tools.time import now, the_day_begin, the_day_str


class WeightManager:
    def __init__(self, em: EventManager) -> None:
        self.db = em.db
        self.event_manager = em

    def query_log(self, owner: str, limit: int = 30) -> Sequence[WeightLog]:
        stmt = sal.select(WeightLog).where(WeightLog.owner == owner).order_by(WeightLog.id.desc()).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def query_log_between(self, owner: str, start: datetime, end: datetime) -> Sequence[WeightLog]:
        stmt = sal.select(WeightLog).where(
            WeightLog.owner == owner, WeightLog.create_time >= start, WeightLog.create_time <= end
        )
        return self.db.execute(stmt).scalars().all()

    def add_log(self, owner: str, weight: float) -> bool:
        log = WeightLog(owner=owner, weight=weight)
        self.db.add(log)
        plan = self.query_plan(owner)
        if plan:
            target_weight = self.__fast_get_target_weight(plan)
            self.event_manager.add_event_log(
                owner, f"用户更新当前体重为 {weight:.1f} 斤, 当前目标体重为 {target_weight:.1f} 斤"
            )
        else:
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

    def query_plan(self, owner: str) -> WeightPlan | None:
        stmt = sal.select(WeightPlan).where(WeightPlan.owner == owner).order_by(WeightPlan.id.desc()).limit(1)
        return self.db.scalar(stmt)

    def init_plan(self, target_weight: float, owner: str) -> bool:
        if target_weight <= 0:
            return False

        weight_logs = self.query_log(owner, limit=1)
        if len(weight_logs) != 1:
            return False

        current = weight_logs[0]
        C = current.weight - target_weight
        days = 90
        a = -math.log(C) / days
        args = {"C": C, "a": a}

        plan = WeightPlan(
            owner=owner,
            target_weight=target_weight,
            start_day=the_day_begin(current.create_time),
            end_day=now() + timedelta(days=days),
            mode=1,
            args=json.dumps(args),
        )
        self.db.add(plan)
        self.db.flush()
        return True

    def get_plan_detail(self, owner: str) -> dict:
        plan = self.query_plan(owner)
        if not plan:
            raise IllegalArgumentException(f"{owner}: 还未初始化体重计划")

        logs = self.query_log_between(owner, plan.start_day, plan.end_day)

        return {
            "target_weight": plan.target_weight,
            "delta_weight": 1.23,
            "BMI": 22,
            "target_line": self.__gen_target_line(plan),
            "user_line": {the_day_str(log.create_time): log.weight for log in logs},
        }

    def __gen_target_line(self, plan: WeightPlan) -> dict:
        args = json.loads(plan.args)
        line = {}
        days = (plan.end_day - plan.start_day).days
        for i in range(days):
            the_day = the_day_str(plan.start_day + timedelta(days=i))
            value = plan.target_weight + args["C"] * math.exp(args["a"] * i)
            line[the_day] = value
        return line

    def __fast_get_target_weight(self, plan: WeightPlan) -> float:
        args = json.loads(plan.args)
        i = (now() - plan.start_day).days
        return plan.target_weight + args["C"] * math.exp(args["a"] * i)
