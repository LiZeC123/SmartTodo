# -*- coding: UTF-8 -*-
import getopt
import sys
from collections import namedtuple, defaultdict
from os.path import join

from entity import TomatoTaskRecord, db_session
from tool4time import get_datetime_from_str


def print_help():
    print("tool4convert: 数据转换工具. 安全的初始化和转换项目的数据")
    print("-u   迁移数据到4.0+版本")


def move_user_data():
    pass


DATABASE_FOLDER = "data/database"
DATA_FILE = join(DATABASE_FOLDER, "TomatoRecord.dat")

Record = namedtuple("Record", ["start", "finish", "title", "extend"])


def load_record_data() -> dict:
    ans = defaultdict(list)
    with open(DATA_FILE, encoding='utf-8') as f:
        for line in f.readlines():
            start, finish, owner, title, *extend = line.split(" | ")
            ans[owner].append(Record(
                start=get_datetime_from_str(start),
                finish=get_datetime_from_str(finish),
                title=title.strip(),
                extend=[ex.strip() for ex in extend]
            ))
    return ans


def move_record_data():
    records = load_record_data()
    for owner, record in records.items():
        for r in record:
            nr = TomatoTaskRecord(start_time=r.start, finish_time=r.finish, owner=owner, name=r.title)
            db_session.add(nr)
    db_session.commit()


if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], 'hcur:', ["test", ])
    for opt_name, opt_value in opts:
        if opt_name in ('-h',):
            print_help()
            exit()
        if opt_name in ('-u',):
            move_user_data()
            move_record_data()
            exit()
        if opt_name in ("--test",):
            exit()
    # 如果没有执行以上的任何一个分支, 则输入帮助信息
    print_help()
