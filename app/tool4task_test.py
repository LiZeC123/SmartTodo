from time import sleep
from tool4task import *


def task1():
    print("Hello")


def task2():
    raise Exception("Exception in task")


def test_make_task():
    task_func = make_task("make_task Test", task1)
    task_func()

    task_func = make_task("make_task Test", task2)
    task_func()


def test_task_manager():
    manager = TaskManager()
    manager.add_daily_task("测试日常任务", lambda : print('x'), '00:00')
    manager.add_friday_task("测试周五任务", lambda : print('x'), '00:00')
    manager.start()
    sleep(0.02)