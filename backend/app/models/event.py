from datetime import datetime


from sqlalchemy import DateTime, Integer, String, Text
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
    

# class CheckinLog(Base):
#     '''打卡记录表, 记录名称中包含 打卡 文字的代办事项的完成记录'''
#     __tablename__ = "checkin_log"
    
#     id: Mapped[int]               = mapped_column(Integer, primary_key=True, autoincrement=True)
#     owner: Mapped[str]            = mapped_column(String(15), nullable=False)
#     create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)
#     name: Mapped[str]             = mapped_column(Text, nullable=False)