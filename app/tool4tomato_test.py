import random
import time

from tool4tomato import *


class DaoMock:
    def add(self, record):
        pass

    def commit(self):
        pass


mock = DaoMock()
owner = "user"


def test_start_and_query():
    m = TomatoManager(mock)
    items = [Item(id=i, name=f"Test-{i}") for i in range(2)]

    query = m.get_task(owner)
    assert query['id'] == 0
    assert query['tid'] == 0

    tid = m.start_task(items[0], owner)
    assert m.has_task(owner)
    assert m.get_task_tid(owner) == tid
    assert m.get_task_xid(owner) == items[0].id

    tid = m.start_task(items[1], owner)
    query = m.get_task(owner)
    assert query['id'] == items[1].id
    assert query['tid'] == tid

    m.finish_task(tid, items[1].id, owner)
    tid = m.start_task(items[0], owner)
    query = m.get_task(owner)
    assert query['id'] == items[0].id
    assert query['tid'] == tid


def test_finish():
    m = TomatoManager(mock)
    items = [Item(id=i, name=f"Test-{i}") for i in range(2)]

    tid = m.start_task(items[0], owner)
    assert m.finish_task(tid - 1, items[0].id, owner) == False
    assert m.finish_task(tid, items[0].id, owner) == True


def test_clean():
    m = TomatoManager(mock)
    items = [Item(id=i, name=f"Test-{i}") for i in range(2)]

    tid = m.start_task(items[0], owner)
    assert m.clear_task(tid - 1, items[0].id, owner) == False
    assert m.clear_task(tid, items[0].id, owner) == True


def try_finish(m: TomatoManager, tid: int, xid: int, lst: list):
    time.sleep(0.05 * random.random())
    lst.append(m.finish_task(tid, xid, owner))
    time.sleep(0.05 * random.random())
    lst.append(m.clear_task(tid, xid, owner))


def test_thread_finish_and_clean():
    m = TomatoManager(mock)
    items = [Item(id=i, name=f"Test-{i}") for i in range(2)]

    tid = m.start_task(items[1], owner)
    lst = []
    THREAD_COUNT = 15
    threads = [threading.Thread(target=try_finish, args=(m, tid, items[1].id, lst)) for _ in range(THREAD_COUNT)]
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    print(lst)
    assert lst.count(True) == 2
    assert lst.count(False) == 2 * (THREAD_COUNT - 1)
