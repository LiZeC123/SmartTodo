from entity import init_database
from tool4tomato import *


db = init_database('sqlite://')


item_manager = ItemManager(db=db)
tomato_manager = TomatoManager(db, item_manager)
record_manager = TomatoRecordManager(db, item_manager)

owner = "user"
fake_owner = "fake"

def make_base_item(name, expected_tomato=1):
    return Item(name=name, item_type=ItemType.Single, tomato_type=TomatoType.Today, expected_tomato=expected_tomato,owner=owner)

def test_start_and_query():
    item = make_base_item(name=f"Test")
    item_manager.create(item)

    query = tomato_manager.get_task(owner)
    assert query is None

    tomato_manager.start_task(item.id, owner)
    assert tomato_manager.has_task(owner)

    task = tomato_manager.query_task(owner)
    assert task
    assert task.item_id == item.id

    task = tomato_manager.get_task(owner)
    assert task is not None
    assert task['itemId'] == item.id


def test_finish():
    item = make_base_item(name=f"Test")
    item_manager.create(item)

    tomato_manager.start_task(item.id, owner)
    task = tomato_manager.query_task(owner)
    assert task is not None
    
    # 用户名不匹配, 无法完成
    assert tomato_manager.finish_task(task.item_id, fake_owner) == False
    # ID不匹配
    assert tomato_manager.finish_task(task.item_id+2, owner) == False
    # 正常完成
    assert tomato_manager.finish_task(task.item_id, owner) == True
    # 已完成不可再次完成
    assert tomato_manager.finish_task(task.item_id, owner) == False


def test_clean():
    item = make_base_item(name=f"Test")
    item_manager.create(item)
    reason = "测试"

    tomato_manager.start_task(item.id, owner)
    task = tomato_manager.query_task(owner)
    assert task is not None
    
    # 用户名不匹配, 无法完成
    assert tomato_manager.clear_task(task.item_id, reason=reason, owner=fake_owner) == False
    # ID不匹配
    assert tomato_manager.clear_task(task.item_id+2, reason=reason, owner=owner) == False    
    # 正常完成
    assert tomato_manager.clear_task(task.item_id, reason=reason, owner=owner) == True
    # 已完成不可再次完成
    assert tomato_manager.clear_task(task.item_id, reason=reason, owner=owner) == False


def test_start_twice():
    items = [make_base_item(name=f"Test-{i}") for i in range(2)]
    assert item_manager.create(items[0])
    assert item_manager.create(items[1])

    assert tomato_manager.start_task(items[0].id, owner) == ""
    assert tomato_manager.start_task(items[1].id, owner) == '启动失败: 当前存在正在执行的番茄钟'
    
    assert tomato_manager.finish_task(items[0].id, owner)

    assert tomato_manager.start_task(items[0].id, owner) == '启动失败: 当前任务已完成全部番茄钟'

def test_add_tomato_record():
    assert tomato_manager.add_tomato_record("测试手动添加任务", "10:00", owner=owner)


def test_tomato_record_base():
    itemA = make_base_item(name="ItemA")
    item_manager.create(itemA)

    itemB = make_base_item(name="ItemB")
    itemB.parent = itemA.id
    itemB.used_tomato = 1
    item_manager.create(itemB)

    record_manager.get_time_line_summary(owner)
    record_manager.get_smart_analysis_report(owner)