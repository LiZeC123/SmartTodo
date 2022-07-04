from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base
from server import Manager

from service4interpreter import *

engine = create_engine('sqlite://', echo=True, future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)


def test():
    manager = Manager(db_session)
    op = OpInterpreter(manager)
    op.exec_function(command="m", data="-A -B -C", parent=0, owner="user")
    op.exec_function(command="backup", data="", parent=0, owner="user")
    op.exec_function(command="gc", data="", parent=0, owner="user")
    op.exec_function(command="sn", data="task 6 章节", parent=0, owner="user")
    op.exec_function(command="sx", data="Item -Ta", parent=0, owner="user")
    op.exec_function(command="habit", data="habit 3", parent=0, owner="user")


def test_parse_sn_data():
    usages = [
        ("task", ("task", 3, "部分")),
        ("task 4 ", ("task", 4, "部分")),
        ("task 5 suffix", ("task", 5, "suffix")),
        ("task 5 suffix ex", ("", 0, "")),
        ("task xx", ("", 0, "")),
    ]

    for (data, (name, count, suffix)) in usages:
        assert parse_sn_data(data) == (name, count, suffix)


def test_parse_sx_data():
    assert parse_sx_data("") == ("", [])
    assert parse_sx_data("task") == ("", [])
    assert parse_sx_data("task -Ta - Tb -  Tc -Td") == ("task", ["Ta", "Tb", "Tc", "Td"])


def test_parse_habit_data():
    usages = [
        # 无法解析
        ("", None, -1),
        # 无限任务
        ("habit", "habit", -1),
        ("habit2  ", "habit2", -1),
        ("  habit3  ", "habit3", -1),
        # 正常数据
        ("habit 3", "habit", 3),
        (" habit  3 ", "habit", 3),
        # 错误数据类型
        ("habit x", None, -1),

    ]
    for (data, name, count) in usages:
        assert parse_habit_data(data) == (name, count)
