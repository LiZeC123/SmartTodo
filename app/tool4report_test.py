from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base
from tool4report import *

engine = create_engine('sqlite://', future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)

manager = ReportManager(db_session)
owner = "user"

def test_summary_base():
    # 初始查询今日总结为空
    assert manager.get_today_summary(owner) == ""    

    assert manager.update_summary("Hello", owner)

    assert manager.get_today_summary(owner) == "Hello" 

    assert manager.update_summary("Hello World", owner)
    
    assert manager.get_today_summary(owner) == "Hello World" 

