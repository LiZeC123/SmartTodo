from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.tools.time import now


class Credit(Base):
    """积分数据表, 记录用户的积分状态"""
    __tablename__ = "credit"

    owner: Mapped[str]    = mapped_column(String(15), primary_key=True)
    credit: Mapped[int]   = mapped_column(Integer, nullable=False)



class CreditLog(Base):
    """积分记录表, 记录所有积分变动明细"""
    __tablename__ = "credit_log"

    id: Mapped[int]               = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]            = mapped_column(String(15), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)
    reason: Mapped[str]           = mapped_column(Text, nullable=False)
    credit: Mapped[int]           = mapped_column(Integer, nullable=False)
    balance: Mapped[int]          = mapped_column(Integer, nullable=False)

    # 定义联合索引
    __table_args__ = (
        # 查询单个用户的积分变更记录
        Index('idx_owner_time', "owner", "create_time"),
    )