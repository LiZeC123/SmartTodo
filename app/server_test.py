from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base
from server import *
from tool4stat import local_report

engine = create_engine('sqlite://', echo=True, future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)
manager = Manager(db_session)

owner = "user"


def make_base_item(name):
    return Item(name=name, item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner)


def init_database():
    db_session.query(Item).delete()
    db_session.commit()

    base_item = make_base_item("base_item")

    deadline_item = make_base_item("deadline_item")
    deadline_item.deadline = now() + timedelta(days=3)

    url_item = make_base_item("url_item")
    url_item.url = "https://lizec.top"

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

    items = [base_item, deadline_item, url_item, repeatable_item, specific_item, activate_item, multi_tomato_item,
             habit_item, inf_habit_item]

    # Test Base Insert
    for item in items:
        manager.create(item)

    # Create Parent Item
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


def test_create():
    init_database()

    url_item = make_base_item("https://lizec.top")
    manager.item_manager.create(url_item)


def test_get_item_by_name():
    init_database()
    base_item = manager.get_item_by_name("url_item", None, owner)[0]
    assert base_item.url == "https://lizec.top"

    parent_item = manager.get_item_by_name("parent_item", None, owner)[0]
    assert len(manager.get_item_by_name("sub_item1", None, owner)) == 0

    sub_item1 = manager.get_item_by_name("sub_item1", parent_item.id, owner)[0]
    assert sub_item1 is not None


def test_check_authority():
    init_database()
    item = manager.get_item_by_name("repeatable_item", None, owner)[0]
    with pytest.raises(UnauthorizedException):
        manager.check_authority(item.id, "others")


def test_all_items():
    init_database()
    items = manager.all_items(owner)
    assert len(items['todayTask']) == 9
    assert len(items['activeTask']) == 1

    parent_item = manager.get_item_by_name("parent_item", None, owner)[0]
    items = manager.all_items(owner, parent_item.id)
    assert len(items['todayTask']) == 1
    assert len(items['activeTask']) == 1


def test_activate_items():
    init_database()
    items = manager.activate_items(owner)
    assert len(items) == 1

    parent_item = manager.get_item_by_name("parent_item", None, owner)[0]
    items = manager.activate_items(owner, parent_item.id)
    assert len(items) == 1


def test_increase_expected_tomato():
    init_database()
    items = manager.all_items(owner)['todayTask']
    for item in items:
        manager.increase_expected_tomato(item['id'], owner)


def test_increase_used_tomato():
    init_database()
    items = manager.all_items(owner)['todayTask']
    for item in items:
        manager.increase_used_tomato(item['id'], owner)
        manager.increase_used_tomato(item['id'], owner)

    # 经过上述操作后, 大部分Item都进入完成状态, 可以直接尝试进行垃圾回收等操作
    manager.garbage_collection()
    manager.reset_today_task()
    manager.reset_daily_task()


def test_undo():
    init_database()
    items = manager.all_items(owner)['todayTask']
    for item in items:
        manager.undo(item['id'], owner)


def test_to_today_task():
    init_database()
    items = manager.all_items(owner)
    for item in items['todayTask']:
        manager.to_today_task(item['id'], owner)

    for item in items["activeTask"]:
        manager.to_today_task(item['id'], owner)


def test_remove():
    init_database()
    items = manager.all_items(owner)
    for item in items['todayTask']:
        manager.remove(item['id'], owner)

    for item in items["activeTask"]:
        manager.remove(item['id'], owner)


def test_get_summary():
    init_database()
    manager.get_summary(owner)


def test_local_report():
    init_database()
    local_report(db_session, owner)

    items = manager.all_items(owner)['todayTask']
    count = 0
    for item in items:
        if count % 2 == 0:
            manager.increase_used_tomato(item['id'], owner)
        count += 1

    daily_report = gen_daily_report(db_session, owner)
    print(daily_report)


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

    manager.file_manager.remove(item)

    # 再次尝试删除, 内部触发FileNotFoundError
    manager.file_manager.remove(item)


def test_download():
    item = make_base_item("https://lizec.top/images/logo.png")
    item.item_type = ItemType.File
    item = manager.create(item)
    manager.remove(item.id, owner)


def test_note():
    note = make_base_item("Note-A")
    manager.create(note)

    assert manager.get_title(note.id, owner) == "Note-A"

    test_content = "Test For Note."
    manager.update_note(note.id, owner, test_content)
    assert manager.get_note(note.id, owner) == test_content

    manager.remove(note.id, owner)

    # 再次尝试删除, 内部触发FileNotFoundError
    manager.note_manager.remove(note)


def test_tomato():
    init_database()

    item = manager.get_item_by_name("base_item", None, owner)[0]
    # manager.create(item)

    # 设置和查询
    tid = manager.set_tomato_task(item.id, owner)
    query = manager.get_tomato_task(owner)
    assert query['name'] == item.name
    assert manager.finish_tomato_task(tid - 1, item.id, owner) == False
    assert manager.finish_tomato_task(tid, item.id, owner)

    # 如果预计的已经消耗的番茄钟数量相等, 则自动增加预计的番茄钟
    tid = manager.set_tomato_task(item.id, owner)
    query = manager.get_tomato_task(owner)
    assert query['name'] == item.name
    assert manager.finish_tomato_task(tid, item.id, owner)

    item = manager.get_item_by_name("base_item", None, owner)[0]
    assert item.expected_tomato == 2

    # 尝试取消任务
    tid = manager.set_tomato_task(item.id, owner)
    manager.undo_tomato_task(tid, item.id, owner)
    query = manager.get_tomato_task(owner)
    assert query['id'] == 0
    item = manager.get_item_by_name("base_item", None, owner)[0]
    # set操作自动增加expected_tomato
    assert item.expected_tomato == 3

    # 执行手动完成操作
    tid = manager.set_tomato_task(item.id, owner)
    query = manager.get_tomato_task(owner)
    assert query['name'] == item.name
    manager.finish_tomato_task_manually(tid, item.id, owner)
    query = manager.get_tomato_task(owner)
    assert query['id'] == 0

    # 利用上述数据测试报告生成功能
    manager.mail_report(dry_run=True)


def test_exec_function():
    manager.exec_function("gc", "now", None, owner)


def test_base_manager():
    m = BaseManager()

    with pytest.raises(NotImplementedError):
        m.create(Item())

    with pytest.raises(NotImplementedError):
        m.remove(Item())
