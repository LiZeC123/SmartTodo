from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base

from tool4tomato import *
from tool4stat import *

engine = create_engine('sqlite://', echo=True, future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)


def test_base():
    m = TomatoManager(db_session)
    assert m.inc() == 1
    owner = "user"

    items = [Item(id=i, name=f"Test-{i}") for i in range(10)]

    tid = m.start_task(items[0], owner)

    assert m.finish_task(tid - 1, items[0].id, owner) == False
    assert m.finish_task(tid, items[0].id, owner) == True

    tid = m.start_task(items[1], owner)
    assert m.clear_task(tid - 1, items[1].id, owner) == False
    assert m.clear_task(tid, items[1].id, owner) == True

    tid = m.start_task(items[2], owner)
    query = m.get_task("user")
    assert query['id'] == items[2].id
    assert m.finish_task(tid, items[2].id, owner) == True

    # Test tool4stat
    for i in range(3, 10):
        tid = m.start_task(items[i], owner)
        m.finish_task(tid, items[i].id, owner)

    print(local_report(db_session, owner))
