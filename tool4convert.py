# -*- coding: UTF-8 -*-
import getopt
import sys
from contextlib import contextmanager

from entity import from_dict
from mapper import MemoryDataBase


@contextmanager
def open_database():
    mapper = MemoryDataBase()

    yield mapper

    mapper.save2file()


def update_data_structure():
    """通过加载数据为标准的Item结构, 然后还原为字典的方式实现数据结构更新"""
    with open_database() as mapper:
        mapper.data = [from_dict(d).to_dict() for d in mapper.items()]


def reset_owner(owner: str) -> None:
    with open_database() as mapper:
        for d in mapper.data:
            d['owner'] = owner


def print_help():
    print("tool4convert: 数据转换工具. 安全的初始化和转换项目的数据")
    print("-h   显示此帮助信息")
    print("-c   更新存储数据结构")
    print("-r   重置所有数据的拥有者")


if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], 'hcr:')
    for opt_name, opt_value in opts:
        if opt_name in ('-h',):
            print_help()
            exit()
        if opt_name in ('-c',):
            update_data_structure()
            exit()
        if opt_name in ("-r",):
            reset_owner(opt_value)
            # create_init_database()
            exit()

        if opt_name in ('-b', '--backup'):
            # backup()
            exit()

    # 如果没有执行以上的任何一个分支, 则输入帮助信息
    print_help()
