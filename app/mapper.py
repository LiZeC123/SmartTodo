import json
import os
import threading
from os.path import exists, join
from typing import List, Optional, Callable, Dict

from entity import Item, from_dict
from tool4log import logger
from tool4time import now_str


def load_data(filename):
    with open(filename, "r", encoding="utf8") as f:
        return json.load(f)


class MemoryDataBase:
    DATABASE_FOLDER = "data/database"
    DATA_FILE = join(DATABASE_FOLDER, "data.json")

    def __init__(self):
        self.lock = threading.Lock()
        self.__init_folder()
        self.filename = MemoryDataBase.DATA_FILE
        self.data: List = []
        if exists(self.filename):
            self.data = load_data(self.filename)
            logger.info(f"{MemoryDataBase.__name__}: Load Data From File")
        if self.data:
            self.current_id = max(map(lambda i: i['id'], self.data))
        else:
            # 默认从1开始, 避免0值产生问题
            self.current_id = 1

    def __init_folder(self):
        if not exists(self.DATABASE_FOLDER):
            os.mkdir(self.DATABASE_FOLDER)

    def __next_id(self):
        with self.lock:
            self.current_id = self.current_id + 1
            return self.current_id

    def select(self, iid: int) -> Optional[dict]:
        for item in self.data:
            if item['id'] == iid:
                return item
        return None

    def select_by(self, where: Callable[[dict], bool] = lambda _: True,
                  select: Callable[[dict], tuple] = lambda x: from_dict(x)) -> list:
        return list(map(select, filter(where, self.data)))

    def select_one(self, where: Callable[[dict], bool] = lambda _: True,
                   select: Callable[[dict], tuple] = lambda x: from_dict(x)):
        return self.select_by(where, select)[0]

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
            # 判断None和直接判断大部分时候都是一致的, 但当idx等于0时会产生错误
            if idx is not None:
                self.data.pop(idx)
                self.save2file()

    def save2file(self):
        json_data = json.dumps(self.data)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(json_data)
        logger.info(f"{MemoryDataBase.__name__}: Success Save Date to File")
