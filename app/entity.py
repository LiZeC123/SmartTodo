from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, SmallInteger, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from tool4time import now

class Base(DeclarativeBase):
    pass


class ItemType:
    Single = "single"
    File = "file"
    Note = "note"


class TomatoType:
    Activate = "activate"
    Today = "today"


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str]   = mapped_column(Text, nullable=False)

    # Item类型，具体取值见 ItemType 类
    item_type: Mapped[str]  = mapped_column(String(10), nullable=False)
    owner: Mapped[str]      = mapped_column(String(15), nullable=False)

    create_time: Mapped[datetime]           = mapped_column(DateTime, nullable=False, default=now)
    deadline: Mapped[Optional[datetime]]    = mapped_column(DateTime, default=None)
    url: Mapped[Optional[str]]              = mapped_column(Text, default=None)

    repeatable: Mapped[int]         = mapped_column(SmallInteger, nullable=False, default=False)
    specific: Mapped[int]           = mapped_column(SmallInteger, nullable=False, default=0)
    # 指示此Item是否附属于某个note, None表示不属于任何note
    parent: Mapped[Optional[int]]   = mapped_column(Integer, ForeignKey("item.id"), default=None)

    # 番茄钟相关属性
    # 番茄钟类型，具体取值见 TomatoType 类
    tomato_type: Mapped[str]        = mapped_column(String(10), nullable=False, default=TomatoType.Activate)
    expected_tomato: Mapped[int]    = mapped_column(SmallInteger, nullable=False, default=1)
    used_tomato: Mapped[int]        = mapped_column(SmallInteger, nullable=False, default=0)


    def __str__(self) -> str:
        # noinspection PyTypeChecker
        return str(class2dict(self))


class TomatoTaskRecord(Base):
    __tablename__ = "tomato_task_record"

    id: Mapped[int]                 = mapped_column(Integer, primary_key=True, autoincrement=True)
    start_time: Mapped[datetime]    = mapped_column(DateTime, nullable=False)
    finish_time: Mapped[datetime]   = mapped_column(DateTime, nullable=False)
    owner: Mapped[str]              = mapped_column(String(15), nullable=False)
    name: Mapped[str]               = mapped_column(Text, nullable=False)

class TomatoEvent(Base):
    """番茄任务事件库: 记录番茄任务相关的事件, 例如任务取消, 任务预计时间变更等"""
    __tablename__ = "tomato_event"

    id: Mapped[int]         = mapped_column(Integer, primary_key=True, autoincrement=True)
    time: Mapped[datetime]  = mapped_column(DateTime, nullable=False)
    content: Mapped[str]    = mapped_column(Text, nullable=False)
    owner: Mapped[str]      = mapped_column(String(15), nullable=False)
    

class Note(Base):
    """便签数据库: 存储创建的便签文本"""
    __tablename__ = "note"

    id: Mapped[int]         = mapped_column(Integer, primary_key=True)
    content: Mapped[str]    = mapped_column(Text, nullable=False)
    owner: Mapped[str]      = mapped_column(String(15), nullable=False)

class Summary(Base):
    """总结记录库: 存储每日总结的文本"""
    __tablename__ = "summary"

    id: Mapped[int]               = mapped_column(Integer, primary_key=True, autoincrement=True)
    create_time: Mapped[datetime] = mapped_column(String(10), nullable=False)
    content: Mapped[str]          = mapped_column(Text, nullable=False)
    owner: Mapped[str]            = mapped_column(String(15), nullable=False)


def class2dict(obj):
    d = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name, None)
        if type(v) == datetime:
            d[c.name] = v.strftime("%Y-%m-%d %H:%M:%S")
        else:
            d[c.name] = v
    return d
