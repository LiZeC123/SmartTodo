from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base
from tool4event import EventManager

engine = create_engine('sqlite://', future=True)
db = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)
owner = "user"

def test_base():
    m = EventManager(db)
    m.add_event("Test Content", owner)
    items = m.get_today_event(owner)
    assert len(items) == 1