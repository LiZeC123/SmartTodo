from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base
from server4item import *

engine = create_engine('sqlite://', future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)
manager = ItemManager(db_session)
owner = "user"


def test_base_manager():
    m = BaseManager()

    with pytest.raises(NotImplementedError):
        m.create(Item())

    with pytest.raises(NotImplementedError):
        m.update(Item())

    with pytest.raises(NotImplementedError):
        m.remove(Item())


def make_base_item(name):
    return Item(name=name, item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner)


def make_note_item(name):
    return Item(name=name, item_type=ItemType.Note, tomato_type=TomatoType.Today, owner=owner)


def test_base_create():
    item = make_base_item("test_create")
    manager.create(item)
    manager.remove(item)


def test_url_item_create():
    item = make_base_item("https://blog.csdn.net/")
    manager.create(item)
    manager.remove(item)


def test_create_item_with_attr():
    deadline_item = make_base_item("deadline_item")
    deadline_item.deadline = now() + timedelta(days=3)

    repeatable_item = make_base_item("repeatable_item")
    repeatable_item.repeatable = True

    specific_item = make_base_item("specific_item")
    specific_item.specific = 3

    activate_item = make_base_item("activate_item")
    activate_item.tomato_type = TomatoType.Activate

    multi_tomato_item = make_base_item("multi_tomato_item")
    multi_tomato_item.expected_tomato = 3

    habit_item = make_base_item("habit_item")
    habit_item.habit_done = 2
    habit_item.habit_expected = 5

    inf_habit_item = make_base_item("inf_habit_item")
    inf_habit_item.habit_done = 3
    habit_item.habit_expected = -1

    items = [deadline_item, repeatable_item, specific_item, activate_item, multi_tomato_item, habit_item,
             inf_habit_item]

    # Test Base Insert
    for item in items:
        manager.create(item)

    for item in items:
        manager.remove(item)


def test_parent_item():
    parent_item = make_base_item("parent_item")
    parent_item.item_type = ItemType.Note
    manager.create(parent_item)

    pid = parent_item.id
    sub_item1 = make_base_item("sub_item1")
    sub_item1.parent = pid

    sub_item2 = make_base_item("sub_item2")
    sub_item2.parent = pid
    sub_item2.tomato_type = TomatoType.Activate

    manager.create(sub_item1)
    manager.create(sub_item2)

    manager.remove(parent_item)
    manager.remove(sub_item1)
    manager.remove(sub_item2)


def test_file_create():
    item = make_base_item("https://pic2.zhimg.com/80/v2-f6b1f64a098b891b4ea1e3104b5b71f6_720w.png")
    item.item_type = ItemType.File
    item = manager.create(item)
    manager.remove(item)


class MockFile:
    def __init__(self, filename):
        self.filename = filename

    def save(self, path):
        with open(path, "w") as f:
            f.write(f"MockFile {self.filename} writes content to this file.")


def test_file():
    file = MockFile("MockFile.txt")
    item = manager.create_upload_file(file, None, owner)

    assert len(manager.get_item_by_name("MockFile.txt", parent=None, owner=owner)) == 1

    item.repeatable = True
    manager.update(item)

    manager.file_manager.remove(item)

    # 再次尝试删除, 内部触发FileNotFoundError
    manager.file_manager.remove(item)


def test_note():
    note = make_note_item("test_note")
    manager.create(note)

    note.repeatable = True
    manager.update(note)

    assert manager.get_title(note.id, owner) == "test_note"

    test_content = "Test For Note."
    manager.update_note(note.id, owner, test_content)
    assert manager.get_note(note.id, owner) == test_content

    with pytest.raises(UnauthorizedException):
        manager.update_note(note.id + 10000, owner, test_content)

    manager.remove(note)
    # 再次尝试删除, 内部触发FileNotFoundError
    manager.remove(note)


def test_update_not_note():
    test_content = "Test For Note."
    item = make_base_item("test_update_not_note")
    manager.create(item)
    with pytest.raises(UnauthorizedException):
        manager.update_note(item.id, owner, test_content)
    manager.remove(item)


def test_check_authority():
    item = make_base_item("test_check_authority")
    manager.create(item)
    manager.check_authority(item.id, owner)
    with pytest.raises(UnauthorizedException):
        manager.check_authority(item.id, "others")
    manager.remove(item)


def test_get_item_by_name():
    items = [make_base_item("test_get_item_by_name"), make_base_item("ABC"), make_base_item("BCD")]
    for item in items:
        manager.create(item)

    assert len(manager.get_item_by_name("test_get_item_by_name", None, owner)) == 1
    assert len(manager.get_item_by_name("BC", None, owner)) == 2
    assert len(manager.get_item_by_name("CD", None, owner)) == 1

    for item in items:
        manager.remove(item)


def test_all_items():
    base_note_item = make_note_item("test_all_items_base")
    today_item = make_base_item("test_all_items_today")
    base_note_item.tomato_type = TomatoType.Activate
    base_note_item.deadline = now()
    manager.create(base_note_item)
    manager.create(today_item)

    query = manager.select_all(owner, None)
    assert len(query['todayTask']) == 1
    assert len(query['activeTask']) == 1

    sub_base_item = make_base_item("test_all_items_sub_base_item")
    sub_base_item.parent = base_note_item.id
    sub_base_item.tomato_type = TomatoType.Activate
    sub_today_item = make_base_item("test_all_items_sub_today_item")
    sub_today_item.parent = base_note_item.id
    manager.create(sub_base_item)
    manager.create(sub_today_item)

    query = manager.select_all(owner, base_note_item.id)
    assert len(query['todayTask']) == 1
    assert len(query['activeTask']) == 1

    manager.remove(base_note_item)
    manager.remove(today_item)
    manager.remove(sub_base_item)
    manager.remove(sub_today_item)


def test_select():
    item = make_base_item("test_select")
    item.url = "Test Data"
    manager.create(item)

    assert manager.select(item.id).url == item.url

    manager.remove(item)


def test_select_summary():
    noteA = make_note_item("test_select_summary_noteA")
    noteA.tomato_type = TomatoType.Today
    noteB = make_note_item("test_select_summary_noteB")
    noteB.tomato_type = TomatoType.Today
    manager.create(noteA)
    manager.create(noteB)

    sub_itemA = make_base_item("test_select_summary_A")
    sub_itemB = make_base_item("test_select_summary_B")
    sub_itemC = make_base_item("test_select_summary_C")
    sub_itemA.parent = noteA.id
    sub_itemB.parent = noteA.id
    sub_itemC.parent = noteB.id

    items = [sub_itemA, sub_itemB, sub_itemC]
    for item in items:
        item.tomato_type = TomatoType.Today
        manager.create(item)

    manager.select_summary(owner)

    items = [noteA, noteB, sub_itemA, sub_itemB, sub_itemC]
    for item in items:
        manager.remove(item)


def test_select_habit():
    item = make_base_item("test_select_habit")
    item.habit_expected = -1
    manager.create(item)
    manager.select_habit(owner)
    manager.remove(item)


def test_select_done_item():
    done_item = make_base_item("test_select_done_item")
    done_item.expected_tomato = 2
    done_item.used_tomato = 2

    undone_item = make_base_item("test_select_undone_item")
    undone_item.expected_tomato = 2
    undone_item.used_tomato = 1

    note = make_note_item("test_select_done_item_note")

    items = [done_item, undone_item, note]
    for item in items:
        manager.create(item)

    assert len(manager.select_done_item(owner)) == 1
    assert len(manager.select_undone_item(owner)) == 1

    for item in items:
        manager.remove(item)


def test_undo():
    item = make_base_item("test_undo")
    manager.create(item)

    manager.to_today_task(item.id, owner)
    assert item.tomato_type == TomatoType.Today

    manager.undo(item.id, owner, None)
    assert item.tomato_type == TomatoType.Activate

    manager.remove(item)


def test_increase_expected_tomato():
    item = make_base_item("test_increase_expected_tomato")
    manager.create(item)

    assert manager.increase_expected_tomato(item.id, owner)
    assert manager.increase_expected_tomato(item.id + 999, owner) == False

    manager.remove(item)


def test_increase_used_tomato():
    item = make_base_item("test_increase_used_tomato")
    item.habit_expected = -1
    manager.create(item)

    manager.increase_used_tomato(item.id, owner)
    assert item.habit_done == 1
    assert item.used_tomato == 1

    # 测试重复提交不更新数据
    manager.increase_used_tomato(item.id, owner)
    assert item.habit_done == 1
    assert item.used_tomato == 1

    manager.remove(item)


def test_to_today_task():
    item = make_base_item("test_to_today_task")
    manager.create(item)

    assert manager.to_today_task(item.id, owner)
    assert manager.to_today_task(item.id + 999, owner) == False

    manager.remove(item)


def test_remove_by_id():
    item = make_base_item("test_remove_by_id")
    manager.create(item)

    manager.remove_by_id(item.id, owner)
    assert len(manager.select_all(owner, None)['todayTask']) == 0

    # 删除不存在的项目时返回False，不抛出异常
    assert manager.remove_by_id(item.id, owner) == False


def test_garbage_collection():
    note_item = make_note_item("test_garbage_collection")
    manager.create(note_item)

    re_item = make_base_item("test_reset_daily_task")
    re_item.repeatable = True

    sub_item = make_base_item("GCSubItem")
    sub_item.parent = note_item.id

    base_item = make_base_item("GCBaseItem")

    items = [re_item, sub_item, base_item]
    for item in items:
        manager.create(item)

    manager.increase_used_tomato(note_item.id, owner)
    manager.increase_used_tomato(re_item.id, owner)

    manager.garbage_collection()
    print(manager.select_all(owner, None))
    assert len(manager.select_today(owner, None)) == 2

    manager.reset_daily_task()
    assert re_item.used_tomato == 0
    assert re_item.tomato_type == TomatoType.Today

    manager.reset_today_task()
    assert base_item.tomato_type == TomatoType.Activate

    manager.remove(re_item)
    manager.remove(base_item)
