from datetime import timedelta
import os
from unittest.mock import patch

import pytest

from app.models.item import Item, ItemType, TomatoType
from app.services.event_log_manager import EventManager
from app.services.item_manager import ItemManager
from app.tests.services.make_db import make_new_db
from app.tools.exception import UnauthorizedException, UnmatchedException
from app.tools.file import FILE_FOLDER
from app.tools.time import now, the_day_after

event_manager = EventManager(make_new_db())
manager = ItemManager(event_manager)
owner = "user"


def make_base_item(name):
    return Item(name=name, item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner)


def make_note_item(name):
    return Item(name=name, item_type=ItemType.Note, tomato_type=TomatoType.Today, owner=owner)


def test_base_create():
    item = make_base_item("test_create")
    manager.create(item)
    manager.remove(item)


def test_url_item_create():
    with patch("app.services.item_manager.extract_title") as extract_title:
        mock_title = "Mock-Title"
        extract_title.return_value = mock_title
        item = make_base_item("https://not_a_web.abcd.def/")
        manager.create(item)

        assert item.name == mock_title
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

    items = [deadline_item, repeatable_item, specific_item, activate_item, multi_tomato_item]

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


# 先禁用依赖网络的测试用例, 后续将网络能力Mock
def test_file_create():
    with patch("app.tools.file.download") as mock_download:
        mock_file_name = os.path.join(FILE_FOLDER, "mock_download.txt")
        mock_url = "https://mock.test.com/w.png"
        mock_download.return_value = mock_file_name
        item = make_base_item(mock_url)
        item.item_type = ItemType.File
        item = manager.create(item)
        assert item.name == mock_url
        assert item.url == os.path.join("/file", "mock_download.txt")
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

    manager.remove(item)
    # 再次删除, 触发异常分支
    manager.remove(item)


def test_file_no_url():
    item = make_base_item("file_no_url")
    manager.create(item)

    item.item_type = ItemType.File
    manager.update(item)

    manager.remove(item)


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


def test_note_no_exists():
    fake_id = 65535
    with pytest.raises(UnmatchedException):
        manager.must_get_note(fake_id)


def test_update_not_note():
    test_content = "Test For Note."
    item = make_base_item("test_update_not_note")
    manager.create(item)
    with pytest.raises(UnmatchedException):
        manager.update_note(item.id, owner, test_content)
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
    assert len(query["todayTask"]) == 1
    assert len(query["activeTask"]) == 1

    sub_base_item = make_base_item("test_all_items_sub_base_item")
    sub_base_item.parent = base_note_item.id
    sub_base_item.tomato_type = TomatoType.Activate
    sub_today_item = make_base_item("test_all_items_sub_today_item")
    sub_today_item.parent = base_note_item.id
    manager.create(sub_base_item)
    manager.create(sub_today_item)

    query = manager.select_all(owner, base_note_item.id)
    assert len(query["todayTask"]) == 1
    assert len(query["activeTask"]) == 1

    manager.remove(base_note_item)
    manager.remove(today_item)
    manager.remove(sub_base_item)
    manager.remove(sub_today_item)


def test_select():
    item = make_base_item("test_select")
    item.url = "Test Data"
    manager.create(item)

    t = manager.select(item.id)
    assert t is not None and t.url == item.url

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

    manager.undo(item.id, owner)
    assert item.tomato_type == TomatoType.Activate

    manager.remove(item)


def test_increase_expected_tomato():
    item = make_base_item("test_increase_expected_tomato")
    manager.create(item)

    # 直接增加预期时间
    assert manager.increase_expected_tomato(item.id, owner)

    # 完成一次后再次增加预期时间
    assert manager.increase_used_tomato(item.id, owner)
    assert manager.increase_expected_tomato(item.id, owner)

    with pytest.raises(UnauthorizedException):
        manager.increase_expected_tomato(item.id + 999, owner)

    # 最多设置四个番茄钟
    assert manager.increase_used_tomato(item.id, owner)
    assert manager.increase_used_tomato(item.id, owner)

    # 继续增加番茄钟数量会失败
    assert not manager.increase_used_tomato(item.id, owner)

    manager.remove(item)


def test_increase_used_tomato():
    item = make_base_item("test_increase_used_tomato")
    manager.create(item)

    manager.increase_used_tomato(item.id, owner)
    assert item.used_tomato == 1

    # 测试重复提交不更新数据
    manager.increase_used_tomato(item.id, owner)
    assert item.used_tomato == 1

    manager.remove(item)


def test_finish_used_tomato():
    item = make_base_item("test_finish_used_tomato")

    # 完成单个任务
    manager.create(item)
    assert manager.finish_used_tomato(item.id, owner)
    assert item.expected_tomato == item.used_tomato

    # 完成有有多个番茄钟, 且已经完成部分番茄种的任务
    manager.increase_expected_tomato(item.id, owner)
    manager.increase_expected_tomato(item.id, owner)
    assert manager.finish_used_tomato(item.id, owner)
    assert item.expected_tomato == item.used_tomato
    manager.remove(item)

    # 完成一个具有多个番茄钟, 且当前未开始任何番茄钟的任务
    item = make_base_item("test_finish_used_tomato2")
    item.expected_tomato = 3
    manager.create(item)
    assert manager.finish_used_tomato(item.id, owner)
    assert item.expected_tomato == item.used_tomato
    manager.remove(item)


def test_to_today_task():
    item = make_base_item("test_to_today_task")
    item.tomato_type = TomatoType.Activate
    manager.create(item)

    assert manager.to_today_task(item.id, owner)
    with pytest.raises(UnauthorizedException):
        manager.to_today_task(item.id + 999, owner)

    t = manager.select(item.id)
    assert t is not None and t.tomato_type == TomatoType.Today

    manager.remove(item)


def test_get_tomato_item():
    item1 = make_base_item("test_get_tomato_item1")
    item2 = make_base_item("test_get_tomato_item2")
    item2.tomato_type = TomatoType.Activate
    manager.create(item1)
    manager.create(item2)
    lst = manager.get_tomato_item(owner)
    assert len(lst) == 1

    manager.remove(item1)
    manager.remove(item2)


def test_sub_task():
    item1 = make_base_item("test_sub_task_g")
    manager.create(item1)
    item2 = make_note_item("test_sub_task_note")
    manager.create(item2)

    item3 = make_base_item("test_sub_task_note_sub")
    item3.parent = item2.id
    manager.create(item3)

    assert manager.get_item_with_sub_task(owner)

    manager.remove(item1)
    manager.remove(item2)
    manager.remove(item3)


def test_get_deadline_item():
    item1 = make_base_item("test_make_deadline")
    item1.deadline = the_day_after(now(), -1)
    manager.create(item1)

    item2 = make_base_item("test_make_deadline2")
    item2.deadline = the_day_after(now(), 2)
    manager.create(item2)

    # 预期只有一个分组, 即全局任务分组
    # 该分组中只包含1个过期的任务
    groups = manager.get_deadline_item(owner)
    assert len(groups) == 1
    assert len(groups[0].get("children", [])) == 1

    manager.remove(item1)
    manager.remove(item2)


def test_remove_by_id():
    item = make_base_item("test_remove_by_id")
    manager.create(item)

    manager.remove_by_id(item.id, owner)
    assert len(manager.select_all(owner, None)["todayTask"]) == 0

    with pytest.raises(UnauthorizedException):
        manager.remove_by_id(item.id, owner)


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


def test_renew_sp_task():
    sp_item1 = make_base_item("test_sp_task01")
    sp_item1.specific = 7
    sp_item1.used_tomato = 1
    manager.create(sp_item1)

    # 已完成任务正常续期
    manager.renew_sp_task()

    item = manager.select(sp_item1.id)
    assert item is not None
    assert item.deadline is not None
    assert item.used_tomato == 0

    deadline = item.deadline

    # 未完成任务不会续期
    manager.renew_sp_task()
    item = manager.select(sp_item1.id)
    assert item is not None
    assert deadline == item.deadline
