from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.tools.time import now


class EventLog(Base):
    """事件记录表, 记录任务完成/任务回退/修改任务预期时间等进度相关的事件"""
    __tablename__ = "event_log"

    id: Mapped[int]               = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]            = mapped_column(String(15), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)
    msg: Mapped[str]              = mapped_column(Text, nullable=False)


class CheckinState(Base):
    """用户打卡相关状态表"""
    __tablename__ = 'checkin_state'

    id: Mapped[int]                 = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]              = mapped_column(String(15), nullable=False)
    item_name: Mapped[str]          = mapped_column(String(64), nullable=False)
    total_count: Mapped[int]        = mapped_column(Integer, nullable=False, default=0) # 总完成次数, 截止昨天24点
    consecutive_days: Mapped[int]   = mapped_column(Integer, nullable=False, default=0) # 连续打卡次数, 截止昨天24点
    achievement_count: Mapped[int]  = mapped_column(Integer, nullable=False, default=0) # 获得成就数, 实时值
    make_up_count: Mapped[int]      = mapped_column(Integer, nullable=False, default=0) # 补卡次数, 实时值
    start_prg_date: Mapped[date]    = mapped_column(Date, nullable=False, default=now) # 新一轮21天打卡挑战起始日期, 截止昨天24点
    progress: Mapped[int]           = mapped_column(Integer, nullable=False, default=0) # 新一轮21天打卡挑战进度值, 截止昨天24点
