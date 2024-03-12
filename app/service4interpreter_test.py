import pytest

from entity import init_database
from exception import NotUniqueItemException
from server4item_test import make_base_item
from service4interpreter import *
from tool4time import now

db_session = init_database()
owner = "user"
item_manager = ItemManager(db_session)
op = OpInterpreter(item_manager)


def test():
    op.exec_function(command="m", data="-A -B -C", parent=None, owner=owner)
    op.exec_function(command="backup", data="", parent=None, owner=owner)
    op.exec_function(command="gc", data="", parent=None, owner=owner)
    op.exec_function(command="UnKnown", data="Unknown Data", parent=None, owner=owner)


def test_split():
    base_item = make_base_item("split_item")
    item_manager.create(base_item)
    op.exec_function(command="sn", data="split 6 章节", parent=None, owner=owner)
    op.exec_function(command="sx", data="Item -Ta", parent=None, owner=owner)
    op.exec_function(command="sx", data="XX -Ta", parent=None, owner=owner)


def test_renew():
    base_item = make_base_item("base_item")
    deadline_item = make_base_item("deadline_item")
    deadline_item.deadline = the_day_after(now(), 3)

    item_manager.create(base_item)
    item_manager.create(deadline_item)

    op.exec_function_with_exception(command="renew", data="deadline_item 5", parent=None, owner=owner)

    with pytest.raises(IllegalArgumentException):
        op.exec_function_with_exception(command="renew", data="base_item 5", parent=None, owner=owner)

    with pytest.raises(NotUniqueItemException):
        op.exec_function_with_exception(command="renew", data="item 5", parent=None, owner=owner)

    with pytest.raises(IllegalArgumentException):
        op.exec_function_with_exception(command="renew", data=" ", parent=None, owner=owner)


def test_parse_sn_data():
    usages = [
        ("task", ("task", 3, "部分")),
        ("task 4 ", ("task", 4, "部分")),
        ("task 5 suffix", ("task", 5, "suffix")),
    ]

    for (data, (name, count, suffix)) in usages:
        assert parse_sn_data(data) == (name, count, suffix)

    usages = [
        "task 5 suffix ex",
        "task xx",
    ]

    for data in usages:
        with pytest.raises(IllegalArgumentException):
            parse_sn_data(data)


def test_parse_sx_data():
    assert parse_sx_data("task -Ta - Tb -  Tc -Td") == ("task", ["Ta", "Tb", "Tc", "Td"])

    with pytest.raises(IllegalArgumentException):
        parse_sx_data("")

    with pytest.raises(IllegalArgumentException):
        parse_sx_data("task")



def test_parse_renew_data():
    usages = [
        ("X 2", "X", 2),
        ("XX  -1", "XX", -1)
    ]

    for (data, name, count) in usages:
        assert parse_renew_data(data) == (name, count)

    usages = [
        "",
    ]

    for data in usages:
        with pytest.raises(IllegalArgumentException):
            parse_renew_data(data)
