from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.tools.time import now


class TomatoStatus(Base):
    __tablename__ = "tomato_status"

    item_id: Mapped[int]            = mapped_column(Integer, primary_key=True)
    name: Mapped[str]               = mapped_column(Text, nullable=False)
    start_time: Mapped[datetime]    = mapped_column(DateTime, nullable=False, default=now)
    owner: Mapped[str]              = mapped_column(String(15), nullable=False, unique=True)

    def to_dict(self):
        return {"itemId": self.item_id, "taskName": self.name, "startTime": self.start_time.strftime("%Y-%m-%d %H:%M:%S"), "finished": False}

class TomatoTaskRecord(Base):
    __tablename__ = "tomato_task_record"

    id: Mapped[int]                 = mapped_column(Integer, primary_key=True, autoincrement=True)
    start_time: Mapped[datetime]    = mapped_column(DateTime, nullable=False)
    finish_time: Mapped[datetime]   = mapped_column(DateTime, nullable=False)
    owner: Mapped[str]              = mapped_column(String(15), nullable=False)
    name: Mapped[str]               = mapped_column(Text, nullable=False)