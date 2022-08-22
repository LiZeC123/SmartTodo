from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base, Item, TomatoType
from server4item_test import make_base_item, make_note_item
from tool4report import *
from tool4tomato import TomatoManager

engine = create_engine('sqlite://', future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)

item_manager = ItemManager(db_session)
tomato_record_manager = TomatoRecordManager(db_session)
tomato_manager = TomatoManager(db_session)


def mock_send_mail(title, msg, res):
    print(f"MockSendMail: title: {title} msg: {msg} res: {res}")


manager = ReportManager(item_manager, tomato_record_manager, send_mail_func=mock_send_mail)
owner = "user"


def create_summary():
    noteA = make_note_item("test_select_summary_noteA")
    noteA.tomato_type = TomatoType.Today
    item_manager.create(noteA)
    sub_itemA = make_base_item("test_select_summary_A")
    sub_itemA.parent = noteA.id
    sub_itemA.used_tomato = 1

    items = [sub_itemA, ]
    for item in items:
        item.tomato_type = TomatoType.Today
        item_manager.create(item)


def test_report_manager():
    items = [Item(id=i, name=f"Test-{i}") for i in range(5)]
    for item in items:
        tid = tomato_manager.start_task(item, owner)
        tomato_manager.finish_task(tid, item.id, owner)

    habit_item = make_base_item("habit_item")
    habit_item.habit_done = 2
    habit_item.habit_expected = 5

    inf_habit_item = make_base_item("inf_habit_item")
    inf_habit_item.habit_done = 3
    habit_item.habit_expected = -1

    item_manager.create(habit_item)
    item_manager.create(inf_habit_item)

    create_summary()

    manager.get_daily_report(owner)
    manager.get_summary(owner)
    manager.send_daily_report(owner, "")
    manager.send_weekly_report(owner, "")

    tomato_record_manager.get_tomato_log(owner)
