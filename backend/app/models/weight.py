from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.tools.time import now


class WeightLog(Base):
    """体重数据表, 记录用户的体重变化状态"""
    __tablename__ = "weight_log"

    id: Mapped[int]               = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]            = mapped_column(String(15), nullable=False, index=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)
    weight: Mapped[float]         = mapped_column(Float, nullable=False)


class WeightPlan(Base):
    """体重计划表, 记录用户当前的体重计划数据"""
    __tablename__ = "weight_plan"

    id: Mapped[int]               = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]            = mapped_column(String(15), nullable=False, index=True)
    target_weight: Mapped[float]  = mapped_column(Float, nullable=False)                # 目标体重
    start_day:  Mapped[datetime]  = mapped_column(DateTime, nullable=False)             # 计划开始时间
    end_day: Mapped[datetime]     = mapped_column(DateTime, nullable=False)             # 计划结束日期
    mode: Mapped[int]             = mapped_column(Integer, nullable=False)              # 计划模式: 1. 指数衰减模式
    args:  Mapped[str]            = mapped_column(Text, nullable=False, default="{}")   # 计划的推测曲线参数

