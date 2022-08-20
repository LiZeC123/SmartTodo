import threading
from collections import defaultdict, namedtuple

from entity import Item, TomatoTaskRecord
from tool4time import now, parse_timestamp

Task = namedtuple("Task", ["tid", "id", "name", "start", "finished"])


def make_task(tid=0, xid=0, name="当前无任务", start_time=0.0, finished=True):
    return Task(tid, xid, name, start_time, finished)


class TomatoManager:
    def __init__(self, db):
        self.db = db
        self.state = defaultdict(make_task)
        self.taskName = ""
        self.startTime = 0
        self.tid = 0
        self.lock = threading.Lock()

    def start_task(self, item: Item, owner: str):
        with self.lock:
            tid = self.__inc()
            current_task = self.state[owner]
            if current_task.tid != 0:
                if not current_task.finished:
                    self.__finish_task(current_task.tid, current_task.id, owner)
                else:
                    self.__clean_task(current_task.tid, current_task.id, owner)

            self.state[owner] = make_task(tid=tid, xid=item.id, name=item.name, start_time=now().timestamp(),
                                          finished=False)
            return tid

    def __inc(self):
        self.tid += 1
        return self.tid

    def finish_task(self, tid: int, xid: int, owner: str) -> bool:
        with self.lock:
            return self.__finish_task(tid, xid, owner)

    def __finish_task(self, tid: int, xid: int, owner: str) -> bool:
        if self.match(tid, xid, owner):
            if not self.state[owner].finished:
                self.__insert_record(owner)
                self.state[owner] = self.state[owner]._replace(finished=True)
                return True
        return False

    def clear_task(self, tid: int, xid: int, owner: str) -> bool:
        with self.lock:
            return self.__clean_task(tid, xid, owner)

    def __clean_task(self, tid: int, xid: int, owner: str) -> bool:
        if self.match(tid, xid, owner):
            self.state.pop(owner)
            return True
        return False

    def get_task(self, owner: str):
        return self.state[owner]._asdict()

    def match(self, tid: int, xid: int, owner: str):
        return self.state[owner].id == xid and self.state[owner].tid == tid

    def __insert_record(self, owner: str):
        state = self.state[owner]
        record = TomatoTaskRecord(start_time=parse_timestamp(state.start), finish_time=now(),
                                  owner=owner, name=state.name)
        self.db.add(record)
        self.db.commit()
