import random
from collections.abc import Sequence
from datetime import date, datetime, timedelta

import sqlalchemy as sal

from app.models.base import Database
from app.models.event import CheckinState, EventLog
from app.services.config_manager import ConfigManager
from app.services.item_manager import ItemManager
from app.tools.log import logger
from app.tools.time import get_month_bounds, now, the_month_begin, today, today_begin

icon_map = {"运动": "🏃🏻‍♀️", "早起": "🛏", "琴": "🎵", "体重": "🏋"}

normal_emoji = ['✅', '⏳', '📅', '⏰', '🔔', '📊', '🏆', '⭐', '❌', '✏️', '🌟', '🎯', '🔄', '📌', '🗓️', '⏲️', '🔥', '💡', '📝', '🧩', '🧘', '🎲', '🧭', '🫧', '🔁']


class CheckinManager:
    def __init__(self, db: Database, config_manager: ConfigManager, item_manager: ItemManager) -> None:
        self.db = db
        self.item_manager = item_manager
        self.config_manager = config_manager

    def get_all_data(self, owner: str):
        names = self.item_manager.select_checkin_item(owner)
        start = the_month_begin()
        end = now()
        return {name: self.get_data(name, start, end, owner) for name in names}

    def get_month_data(self, name: str, month: datetime, owner: str) -> list[str]:
        start, end = get_month_bounds(month)
        record = self.get_checkin_datetime(name, start, end, owner)
        return [r.strftime("%Y-%m-%d %H:%M:%S") for r in record]

    def get_data(self, name: str, start: datetime, end: datetime, owner: str) -> dict:
        record = self.get_checkin_datetime(name, start, end, owner)
        emoji = self.get_emoji(name)
        return {"record": [r.strftime("%Y-%m-%d %H:%M:%S") for r in record], "emoji": emoji}

    def get_checkin_datetime(self, name: str, start: datetime, end: datetime, owner: str) -> Sequence[datetime]:
        stmt = sal.select(EventLog.create_time).where(
            EventLog.owner == owner,
            EventLog.create_time > start,
            EventLog.create_time < end,
            sal.or_(EventLog.msg.like(f"%完成%{name}%"), EventLog.msg.like(f"%补卡%{name}%")),
        )
        return self.db.scalars(stmt).all()

    def today_checked(self, name: str, owner: str) -> bool:
        stmt = sal.select(EventLog.id).where(
            EventLog.owner == owner, EventLog.create_time > today_begin(), EventLog.msg.like(f"%完成%{name}%")
        )
        id = self.db.scalar(stmt)
        return id is not None

    def select_checkin_state(self, name: str, owner: str) -> CheckinState | None:
        stmt = sal.select(CheckinState).where(CheckinState.item_name == name, CheckinState.owner == owner).limit(1)
        return self.db.scalar(stmt)

    def update_all_checkin_state(self):
        users = self.config_manager.get_all_users()
        end_day = today() - timedelta(days=1)
        for user in users:
            names = self.item_manager.select_checkin_item(user)
            for name in names:
                self.update_checkin_state(name=name, end_day=end_day, owner=user)


    def update_checkin_state(self, name: str, end_day: date, owner: str):
        """注意: 不要混用datetime和date类型, 两者具有继承关系, 但无法进行比较"""
        start = datetime(year=2025, month=1, day=1)
        end = today_begin()
        records = self.get_checkin_datetime(name, start, end, owner)

        total_count = len(records)
        checkin_dates: set[date] = set([r.date() for r in records])

        # 连续打卡次数 & 最近未打卡日期
        streak = 0
        cursor = end_day
        while cursor in checkin_dates:
            streak += 1
            cursor -= timedelta(days=1)

        # 更新数据库
        state = self.select_checkin_state(name, owner)
        if state is None:
            state = CheckinState(
                owner=owner,
                item_name=name,
                total_count=total_count,
                consecutive_days=streak,
                start_prg_date=cursor,
                progress=streak,
            )
            self.db.add(state)
            self.db.flush()
            return state

        state.total_count = total_count
        state.consecutive_days = streak
        if state.start_prg_date <= cursor:
            # 上次打卡起始日期位于有效区间内, 因此可以直接计算差值
            state.progress = (end_day - state.start_prg_date).days
        else:
            state.start_prg_date = cursor
            state.progress = streak
        self.db.flush()
        return state

    def get_stat(self, name: str, owner: str) -> dict:
        state = self.select_checkin_state(name, owner)
        if state is None:
            logger.info(f"[{owner}]: {name} 由于没有历史数据开始重新生成")
            end_day = today() - timedelta(days=1)
            state = self.update_checkin_state(name, end_day, owner)
        if self.today_checked(name, owner):
            return {
                "total_count": state.total_count + 1,
                "continuous_count": state.consecutive_days + 1,
                "achievement_count": state.achievement_count,
                "remaining_make_up": state.make_up_count,
                "process": state.progress+1,
            }
        else:
            return {
                "total_count": state.total_count,
                "continuous_count": state.consecutive_days,
                "achievement_count": state.achievement_count,
                "remaining_make_up": state.make_up_count,
                "process": state.progress,
            }

    def get_emoji(self, name: str) -> str:
        for k, v in icon_map.items():
            if k in name:
                return v

        return random.choice(normal_emoji)
