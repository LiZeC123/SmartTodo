import threading
from time import sleep

from app.services.event_log_manager import EventManager
from app.services.task_manager import TaskManager, make_task
from app.tests.services.make_db import make_new_file_db

db = make_new_file_db()
event_manager = EventManager(db)
owner = "lizec"


def task1():
    print("Hello")


def task2():
    raise Exception("Exception in task")


def test_make_task():
    task_func = make_task("make_task Test", db, task1)
    task_func()

    task_func = make_task("make_task Test", db, task2)
    task_func()


def test_task_manager():
    manager = TaskManager(db)
    manager.add_daily_task("测试日常任务", lambda: print("x"), "00:00")
    manager.add_friday_task("测试周五任务", lambda: print("x"), "00:00")
    manager.start()
    sleep(0.02)


def task_with_db_update():
    event_manager.add_event_log(owner, "测试更新")


def test_task_db_commited():
    # 两个线程同时写入DB, 只有各自均正常commit才能正常执行, 否则将产生异常并回滚
    thread1 = threading.Thread(target=make_task("测试任务1", db, task_with_db_update))
    thread2 = threading.Thread(target=make_task("测试任务1", db, task_with_db_update))

    # 启动线程
    thread1.start()
    thread2.start()

    # 等待两个线程执行完毕
    thread1.join()
    thread2.join()
