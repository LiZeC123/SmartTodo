import threading
from collections import defaultdict
from os.path import join

from tool4time import now, now_str, parse_timestamp


def make_task(xid=0, name="当前无任务", start_time=0.0, finished=True):
    return {"id": xid, "name": name, "startTime": start_time, "finished": finished}


class TomatoManager:
    DATABASE_FOLDER = "data/database"
    DATA_FILE = join(DATABASE_FOLDER, "TomatoRecord.dat")

    def __init__(self):
        self.data = defaultdict(make_task)
        self.taskName = ""
        self.startTime = 0
        self.lock = threading.Lock()

    def start_task(self, xid: int, name: str, owner: str):
        self.data[owner] = make_task(xid=xid, name=name, start_time=now().timestamp(), finished=False)

    def finish_task(self, xid: int, owner: str) -> bool:
        with self.lock:
            if self.match(xid, owner):
                if not self.data[owner]['finished']:
                    self.__insert_record(owner)
                    self.data[owner]['finished'] = True
                    return True
            return False

    def clear_task(self, xid: int, owner: str) -> bool:
        with self.lock:
            if self.match(xid, owner):
                self.data.pop(owner)
                return True
            return False

    def get_task(self, owner: str):
        return self.data[owner]

    def match(self, xid: int, owner: str):
        return owner in self.data and self.data[owner]['id'] == xid

    def __insert_record(self, owner: str):
        record = self.data[owner]
        start_time = parse_timestamp(record['startTime'])
        name = record['name']

        with open(TomatoManager.DATA_FILE, "a", encoding="utf-8") as f:
            f.write(f"{start_time} | {now_str()} | {owner} | {name}\n")
