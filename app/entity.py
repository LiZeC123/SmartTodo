from datetime import datetime
from typing import Dict
from tool4time import zero_time, now
from sqlalchemy import create_engine, Column, DateTime, Integer, String, Text, SmallInteger, ForeignKey
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

engine = create_engine('sqlite:///data/database/data.db', echo=True, future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
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
    tomato_type = Column(String(10), nullable=False, default=TomatoType.Activate)
    expected_tomato = Column(SmallInteger, nullable=False, default=1)
    used_tomato = Column(SmallInteger, nullable=False, default=0)

    # 打卡相关属性
    habit_done = Column(SmallInteger, nullable=False, default=0)
    habit_expected = Column(SmallInteger, nullable=False, default=0)
    last_check_time = Column(DateTime, nullable=False, default=zero_time)

    def to_dict(self) -> Dict:
        d = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name, None)
            if type(v) == datetime:
                d[c.name] = v.strftime("%Y-%m-%d %H:%M:%S")
            else:
                d[c.name] = v
        return d

    def __str__(self) -> str:
        return str(self.to_dict())


class TomatoTaskRecord(Base):
    __tablename__ = "tomato_task_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False)
    finish_time = Column(DateTime, nullable=False)
    owner = Column(String(15), nullable=False)
    name = Column(Text, nullable=False)

    def to_dict(self) -> Dict:
        d = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name, None)
            if type(v) == datetime:
                d[c.name] = v.strftime("%Y-%m-%d %H:%M:%S")
            else:
                d[c.name] = v
        return d

    def __str__(self) -> str:
        return str(self.to_dict())

# 初始化所有的表
Base.metadata.create_all(engine)

if __name__ == '__main__':
    # 使用SQLite内存数据库测试对象构建是否正常
    import sqlalchemy as sal
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine("sqlite://", echo=True, future=True)
    Base.metadata.create_all(engine)
    session = Session(engine)
    with session.begin():
        item = Item(name="A", item_type=ItemType.Single, owner="lizec")
        session.add(item)
        session.commit()

    with session.begin():
        stmt = sal.select(Item).where(Item.name == "A", Item.owner == "lizec")
        item = session.scalar(stmt)
        item.deadline = now()
        print(item.to_dict())
