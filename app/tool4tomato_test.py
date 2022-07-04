from tool4tomato import *


def test_base():
    m = TomatoManager()
    assert m.inc() == 1
    xid = 1
    owner = "user"
    item = Item(id=xid, name="TestItem")

    tid = m.start_task(item, owner)

    assert m.finish_task(tid - 1, xid, owner) == False
    assert m.finish_task(tid, xid, owner) == True

    tid = m.start_task(item, owner)
    assert m.clear_task(tid - 1, xid, owner) == False
    assert m.clear_task(tid, xid, owner) == True

    item.id = 233
    m.start_task(item, owner)
    query = m.get_task("user")
    assert query['id'] == item.id
