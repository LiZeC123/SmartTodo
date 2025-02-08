from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, SmallInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TomatoType
from app.tools.time import now


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str]   = mapped_column(Text, nullable=False)
    # Item类型，具体取值见 ItemType 类
    item_type: Mapped[str]  = mapped_column(String(10), nullable=False)

    create_time: Mapped[datetime]           = mapped_column(DateTime, nullable=False, default=now)
    update_time: Mapped[datetime]           = mapped_column(DateTime, nullable=False, default=now)
    deadline: Mapped[Optional[datetime]]    = mapped_column(DateTime, default=None)

    url: Mapped[Optional[str]]      = mapped_column(Text, default=None)
    repeatable: Mapped[int]         = mapped_column(SmallInteger, nullable=False, default=False)
    specific: Mapped[int]           = mapped_column(SmallInteger, nullable=False, default=0)
    priority: Mapped[str]           = mapped_column(SmallInteger, nullable=False, default='p2')
    tags: Mapped[str]               = mapped_column(SmallInteger, nullable=False, default='')

    owner: Mapped[str] = mapped_column(String(15), nullable=False)
    # 指示此Item是否附属于某个note, None表示不属于任何note
    parent: Mapped[Optional[int]]   = mapped_column(Integer, ForeignKey("item.id"), default=None)

    # 番茄钟类型，具体取值见 TomatoType 类
    tomato_type: Mapped[str]        = mapped_column(String(10), nullable=False, default=TomatoType.Activate)
    expected_tomato: Mapped[int]    = mapped_column(SmallInteger, nullable=False, default=1)
    used_tomato: Mapped[int]        = mapped_column(SmallInteger, nullable=False, default=0)    