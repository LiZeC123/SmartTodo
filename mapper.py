import json
import os
import threading
from os.path import exists
from typing import List, Optional, Callable, Dict

from entity import Item, from_dict
from tool4log import logger
from tool4time import now_str


def load_data(filename):
    with open(filename, "r", encoding="utf8") as f:
        return json.load(f)


class OpCount:
    def __init__(self, delta: int):
        self.op_count = 0
        self.last_count = 0
        self.delta = delta
        self.lock = threading.Lock()
        self.finish = True
        self.observer_list = []

    def inc(self):
        with self.lock:
            self.op_count += 1
            self.__do_when_need()

    def add_observer(self, f):
        self.observer_list.append(f)

    def __do_when_need(self):
        if not self.finish:
            # 检查是否完成一次调用, 避免递归
            return

        self.finish = False
        if self.op_count - self.last_count >= self.delta:
            for f in self.observer_list:
                f()
            self.last_count = self.op_count
        self.finish = True


class MemoryDataBase:
    _DATABASE_FOLDER = "database"

    def __init__(self):
        self.lock = threading.Lock()
        self.filename = os.path.join(MemoryDataBase._DATABASE_FOLDER, f"data.json")
        self.counter = OpCount(10)
        self.data: List = []
        if exists(self.filename):
            self.data = load_data(self.filename)
            logger.info(f"{MemoryDataBase.__name__}: Load Data From File")
        if self.data:
            self.current_id = max(map(lambda i: i['id'], self.data))
        else:
            self.current_id = 0

    def __next_id(self):
        with self.lock:
            self.current_id = self.current_id + 1
            return self.current_id

    def add_modify_observer(self, f):
        self.counter.add_observer(f)

    def select(self, iid: int) -> Optional[dict]:
        for item in self.data:
            if item['id'] == iid:
                return item
        return None

    def select_by(self, where: Callable[[dict], bool] = lambda _: True,
                  select: Callable[[dict], tuple] = lambda x: from_dict(x)) -> list:
        return list(map(select, filter(where, self.data)))

    def update_by(self, where: Callable[[dict], bool], update: Callable[[dict], None]) -> int:
        ans = len(list(map(update, filter(where, self.data))))
        self.save2file()
        return ans

    def select_group_by(self, ans: Dict[str, List], f: Callable[[dict], str]) -> Dict[str, List]:
        for item in self.data:
            key = f(item)
            if key in ans:
                ans[key].append(from_dict(item))
        return ans

    def insert(self, item: Item) -> int:
        item.id = self.__next_id()
        item.create_time = now_str()
        with self.lock:
            self.data.append(item.to_dict())
        self.save2file()
        return item.id

    def __get_idx(self, item: Item) -> Optional[int]:
        for idx, dic in enumerate(self.data):
            if dic['id'] == item.id:
                return idx
        return None

    def remove(self, item: Item):
        with self.lock:
            idx = self.__get_idx(item)
            if idx:
                self.data.pop(idx)
                self.save2file()

    def save2file(self):
        self.counter.inc()  # 在保存操作之前检查是否达到计数
        json_data = json.dumps(self.data)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(json_data)
        logger.info(f"{MemoryDataBase.__name__}: Success Save Date to File")
