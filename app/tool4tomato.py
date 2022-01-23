import threading
from collections import defaultdict, namedtuple
from os.path import join

from entity import Item
from tool4time import now, now_str, parse_timestamp

Task = namedtuple("Task", ["tid", "id", "name", "habit", "start", "finished"])


def make_task(tid=0, xid=0, name="当前无任务", habit=False, start_time=0.0, finished=True):
    return Task(tid, xid, name, habit, start_time, finished)


class TomatoManager:
    DATABASE_FOLDER = "data/database"
    DATA_FILE = join(DATABASE_FOLDER, "TomatoRecord.dat")

    def __init__(self):
        self.data = defaultdict(make_task)
        self.taskName = ""
        self.startTime = 0
        self.tid = 0
        self.lock = threading.Lock()

    def inc(self):
        with self.lock:
            self.tid += 1
            return self.tid

    def start_task(self, item: Item, owner: str):
        tid = self.inc()
        self.data[owner] = make_task(tid=tid, xid=item.id, name=item.name, habit=item.habit,
                                     start_time=now().timestamp(), finished=False)
        return tid

    def finish_task(self, tid: int, xid: int, owner: str) -> bool:
        with self.lock:
            if self.match(tid, xid, owner):
                if not self.data[owner].finished:
                    self.__insert_record(owner)
                    self.data[owner] = self.data[owner]._replace(finished=True)
                    return True
            return False

    def clear_task(self, tid: int, xid: int, owner: str) -> bool:
        with self.lock:
            if self.match(tid, xid, owner):
                self.data.pop(owner)
                return True
            return False

    def get_task(self, owner: str):
        return self.data[owner]._asdict()

    def match(self, tid: int, xid: int, owner: str):
        return owner in self.data and self.data[owner].id == xid and self.data[owner].tid == tid

    def __insert_record(self, owner: str):
        record = self.data[owner]
        start_time = parse_timestamp(record.start)
        name = record.name

        with open(TomatoManager.DATA_FILE, "a", encoding="utf-8") as f:
            values = [start_time, now_str(), owner, name]
            if record.habit:
                values.append("hb")

            f.write(" | ".join(values))
            f.write("\n")
