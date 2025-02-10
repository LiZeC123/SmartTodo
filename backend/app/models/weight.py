from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.tools.time import now


class WeightLog(Base):
    """体重数据表, 记录用户的体重变化状态"""
    __tablename__ = "weight_log"

    id: Mapped[int]               = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]            = mapped_column(String(15), nullable=False, index=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)
    weight: Mapped[int]           = mapped_column(Integer, nullable=False)


