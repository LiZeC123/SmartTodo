import threading
from collections import defaultdict, namedtuple
from datetime import timedelta
from typing import List

import sqlalchemy as sal
from sqlalchemy import func

from entity import Item, TomatoTaskRecord
from tool4time import now, parse_timestamp, last_month, today_begin, this_week_begin

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

    def has_task(self, owner) -> bool:
        current_task = self.state[owner]
        return current_task.tid != 0

    def get_task_tid(self, owner: str) -> int:
        return self.state[owner].tid

    def get_task_xid(self, owner: str) -> int:
        return self.state[owner].id

    def match(self, tid: int, xid: int, owner: str):
        return self.state[owner].id == xid and self.state[owner].tid == tid

    def __insert_record(self, owner: str):
        state = self.state[owner]
        record = TomatoTaskRecord(start_time=parse_timestamp(state.start), finish_time=now(),
                                  owner=owner, name=state.name)
        self.db.add(record)
        self.db.commit()


Record = namedtuple("Record", ["start", "finish", "title", "extend"])


class TomatoRecordManager:
    def __init__(self, db):
        self.db = db

    def get_tomato_stat(self, owner):
        d = self.__load_data(self.db, owner)
        return {"total": self.__total_stat(d), "today": self.__today_stat(d), "week": self.__week_chat_stat(d)}

    def get_daily_stat(self, owner):
        d = self.__load_data(self.db, owner)
        return self.__today_stat(d)

    def select_today_tomato(self, owner: str) -> list:
        return self.__select_tomato_before(owner, today_begin())

    def select_week_tomato(self, owner: str) -> list:
        return self.__select_tomato_before(owner, this_week_begin())

    def __select_tomato_before(self, owner: str, time):
        stmt = sal.select(TomatoTaskRecord.name, func.count()) \
            .where(TomatoTaskRecord.owner == owner, TomatoTaskRecord.start_time > time) \
            .group_by(TomatoTaskRecord.name)

        items = self.db.execute(stmt).all()
        return list(sorted(items, key=lambda x: x[1], reverse=True))

    @staticmethod
    def __load_data(db, owner: str, limit: int = 200) -> List[TomatoTaskRecord]:
        stmt = sal.select(TomatoTaskRecord).where(TomatoTaskRecord.owner == owner,
                                                  TomatoTaskRecord.finish_time > last_month()) \
            .order_by(TomatoTaskRecord.id.desc()).limit(limit)
        return db.execute(stmt).scalars().all()

    @staticmethod
    def __total_stat(data: List[TomatoTaskRecord]) -> dict:
        time = timedelta()
        for record in data:
            time += (record.finish_time - record.start_time)

        elapsed_day = 1
        count = len(data)
        if count >= 2:
            first_time = data[-1].start_time
            last_time = data[0].finish_time
            elapsed_day = (last_time - first_time).days + 1

        average_time = time.total_seconds() / elapsed_day

        return {
            "count": count,
            "hour": int(time.total_seconds() / 60 / 60),
            "average": int(average_time / 60)
        }

    @staticmethod
    def __today_stat(data: List[TomatoTaskRecord]) -> dict:
        today = now().date()
        count = 0
        time = timedelta()
        for record in data:
            start = record.start_time
            finish = record.finish_time
            if start.date() == today:
                count += 1
                time += (finish - start)
        return {
            "count": count,
            "minute": int(time.total_seconds() / 60)
        }

    @staticmethod
    def __week_chat_stat(data: List[TomatoTaskRecord]) -> list:
        WEEK_LENGTH = 15
        today = now().date()
        counts = [timedelta() for _ in range(WEEK_LENGTH)]
        for record in data:
            start = record.start_time
            finish = record.finish_time
            delta = (today - start.date()).days
            if delta < WEEK_LENGTH:
                counts[delta] += (finish - start)

        return list(map(lambda time: int(time.total_seconds() / 60), counts))
