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


class MemoryDataBase:
    _DATABASE_FOLDER = "database"

    def __init__(self):
        self.lock = threading.Lock()
        self.filename = os.path.join(MemoryDataBase._DATABASE_FOLDER, f"data.json")
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

    def select(self, iid: int) -> Optional[dict]:
        for item in self.data:
            if item['id'] == iid:
                return item
        return None

    def select_by(self, where: Callable[[dict], bool] = lambda _: True,
                  select: Callable[[dict], tuple] = lambda x: from_dict(x)) -> list:
        return list(map(select, filter(where, self.data)))

    def update_by(self, where: Callable[[dict], bool], update: Callable[[dict], None]) -> int:
        return len(list(map(update, filter(where, self.data))))

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
        json_data = json.dumps(self.data)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(json_data)
        logger.info(f"{MemoryDataBase.__name__}: Success Save Date to File")

    def get_id_by_name(self, name: str):
        pass
        # query_id = None
        # for item in self.data:
        #     if name in item["name"]:
        #         if query_id is None:
        #             query_id = item['id']
        #         else:
        #             raise ValueError("More than one item have the same name")
        # return query_id

    def exec_set_cmd(self, iid: str, attr: str, value):
        pass
        # with self.select(iid) as item:
        #     item[attr] = value
        #     logger.info(f"{MemoryDataBase.__name__}: Do Command [{iid}] --> [{attr}] = [{value}]")
