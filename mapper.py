import json
import os
from contextlib import contextmanager
from os.path import exists
from typing import List

from entity import Item
from tool4log import logger
from tool4time import now_str

DummyItem = Item(0, "DummyItem", "single", "2020-02-02 22:00:22").to_dict()


def load_data(filename):
    with open(filename, "r", encoding="utf8") as f:
        return json.load(f)


class MemoryDataBase:
    _DATABASE_FOLDER = "database"

    def __repr__(self):
        return "memoryDataBase"

    def __init__(self, username):
        self.username = username
        self.filename = os.path.join(MemoryDataBase._DATABASE_FOLDER, f"{username}.json")
        self.data: List = []
        if exists(self.filename):
            self.data = load_data(self.filename)
            logger.info(f"{MemoryDataBase.__name__}: Load Data From {self.username}")
        self.current_id = max(map(lambda i: i['id'], self.data))

    def __next_id(self):
        self.current_id = self.current_id + 1
        return self.current_id

    @contextmanager
    def select(self, iid):
        item = DummyItem
        for i in self.data:
            if int(i['id']) == int(iid):
                item = i
        # 如果找到就返回相应的数据, 否则返回默认节点
        if item is DummyItem:
            logger.warn(f"{MemoryDataBase.__name__}: Select DummyItem")
        yield item

        # 操作结束保存数据
        self.save2file()

    def insert(self, item: Item):
        item.id = self.__next_id()
        item.create_time = now_str()
        self.data.append(item.to_dict())
        self.save2file()
        return item

    def remove(self, iid: int):
        with self.select(iid) as item:
            self.data.remove(item)

    def items(self):
        return self.data

    def update_url(self, iid: int, url: str):
        with self.select(iid) as item:
            item['url'] = url

    def save2file(self):
        json_data = json.dumps(self.data)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(json_data)
        logger.info(f"{MemoryDataBase.__name__}: Success Save Date to File")

    def get_id_by_name(self, name: str):
        query_id = None
        for item in self.data:
            if name in item["name"]:
                if query_id is None:
                    query_id = item['id']
                else:
                    raise ValueError("More than one item have the same name")
        return query_id

    def exec_set_cmd(self, iid: str, attr: str, value):
        with self.select(iid) as item:
            item[attr] = value
            logger.info(f"{MemoryDataBase.__name__}: Do Command [{iid}] --> [{attr}] = [{value}]")

    def get_filename(self):
        return self.filename
