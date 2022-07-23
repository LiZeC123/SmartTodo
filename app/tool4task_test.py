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
