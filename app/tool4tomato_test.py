import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import random
import time

from entity import Base
from tool4tomato import *


engine = create_engine('sqlite://', echo=True, future=True)
db= scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)


item_manager = ItemManager(db=db)
tomato_manager = TomatoManager(db, item_manager)

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
    assert task['item_id'] == item.id


def test_finish():
    item = make_base_item(name=f"Test")
    item_manager.create(item)

    tomato_manager.start_task(item.id, owner)
    task = tomato_manager.query_task(owner)
    assert task is not None
    
    # 用户名不匹配, 无法完成
    assert tomato_manager.finish_task(task.item_id, fake_owner) == False
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