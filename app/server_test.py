from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base
from server import *

engine = create_engine('sqlite://', echo=True, future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)
manager = Manager(db_session)


def test():
    owner = "lizec"
    items = [Item(name=f"Item-{i}", item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner) for i in
             range(10)]

    items[0].specific = 2
    items[1].repeatable = True
    items[0].deadline = now() + timedelta(days=3)
    items[2].habit_expected = 1
    items[3].name = "https://lizec.top/"
    items[5].habit_expected = 3

    for item in items:
        manager.create(item)

    for i in range(0, 10, 2):
        manager.increase_used_tomato(items[i].id, owner)

    for i in range(0, 10, 3):
        manager.undo(items[i].id, owner)

    query = manager.all_items("lizec")['todayTask']
    assert len(query) == 6

    item = manager.get_item_by_name("Item-1", parent=None, owner=owner)[0]
    manager.increase_expected_tomato(item.id, owner)
    manager.increase_used_tomato(item.id, owner)
    manager.undo(item.id, owner, parent=None)

    query = manager.activate_items(owner)
    assert len(query) == 5

    manager.to_today_task(item.id, owner)

    manager.garbage_collection()

    manager.get_summary(owner)


def test_note():
    owner = "lizec"
    note = Item(name="Note-A", item_type=ItemType.Note, owner=owner)
    manager.create(note)

    assert manager.get_title(note.id, owner) == "Note-A"

    test_content = "Test For Note."
    manager.update_note(note.id, owner, test_content)
    assert manager.get_note(note.id, owner) == test_content

    manager.remove(note.id, owner)


def test_tomato():
    owner = "lizec"
    item = Item(name=f"Tomato-A", item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner)
    manager.create(item)

    tid = manager.set_tomato_task(item.id, owner)
    query = manager.get_tomato_task(owner)
    assert query['name'] == item.name

    assert manager.finish_tomato_task(tid, item.id, owner)

    manager.undo_tomato_task(tid, item.id, owner)
    query = manager.get_tomato_task(owner)
    assert query['id'] == 0

    manager.increase_expected_tomato(item.id, owner)
    tid = manager.set_tomato_task(item.id, owner)
    query = manager.get_tomato_task(owner)
    assert query['name'] == item.name

    manager.finish_tomato_task_manually(tid, item.id, owner)
    query = manager.get_tomato_task(owner)
    assert query['id'] == 0


def test_mail():
    manager.mail_report(dry_run=True)
