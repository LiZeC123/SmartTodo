from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, SmallInteger, ForeignKey
from sqlalchemy.orm import declarative_base

from tool4time import zero_time, now

Base = declarative_base()


class ItemType:
    Single = "single"
    File = "file"
    Note = "note"


class TomatoType:
    Activate = "activate"
    Today = "today"


class Item(Base):
    __tablename__ = "item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    # Item类型，具体取值见 ItemType 类
    item_type = Column(String(10), nullable=False)
    owner = Column(String(15), nullable=False)

    create_time = Column(DateTime, nullable=False, default=now)
    deadline = Column(DateTime, default=None)
    url = Column(Text, default=None)

    repeatable = Column(SmallInteger, nullable=False, default=False)
    specific = Column(SmallInteger, nullable=False, default=0)
    # 指示此Item是否附属于某个note, None表示不属于任何note
    parent = Column(Integer, ForeignKey("item.id"), default=None)

    # 番茄钟相关属性
    # 番茄钟类型，具体取值见 TomatoType 类
    tomato_type = Column(String(10), nullable=False, default=TomatoType.Today)
    expected_tomato = Column(SmallInteger, nullable=False, default=1)
    used_tomato = Column(SmallInteger, nullable=False, default=0)

    # 打卡相关属性
    habit_done = Column(SmallInteger, nullable=False, default=0)
    habit_expected = Column(SmallInteger, nullable=False, default=0)
    last_check_time = Column(DateTime, nullable=False, default=zero_time)

    def __str__(self) -> str:
        # noinspection PyTypeChecker
        return str(class2dict(self))


class TomatoTaskRecord(Base):
    __tablename__ = "tomato_task_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False)
    finish_time = Column(DateTime, nullable=False)
    owner = Column(String(15), nullable=False)
    name = Column(Text, nullable=False)

    def __str__(self) -> str:
        # noinspection PyTypeChecker
        return str(class2dict(self))


def class2dict(obj):
    d = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name, None)
        if type(v) == datetime:
            d[c.name] = v.strftime("%Y-%m-%d %H:%M:%S")
        else:
            d[c.name] = v
    return d
