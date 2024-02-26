import threading
from collections import namedtuple
from datetime import timedelta
from typing import Dict, List

import sqlalchemy as sal
from sqlalchemy import func

from entity import Item, TomatoTaskRecord
from tool4event import EventManager
from tool4time import get_hour_str_from, now, parse_timestamp, last_month, today_begin, this_week_begin

Task = namedtuple("Task", ["taskId", "itemId", "taskName", "startTime"])


class TomatoManager:
    def __init__(self, db):
        self.db = db
        self.state: Dict[str, Task] = {}
        self.tid = 1025
        self.lock = threading.Lock()
        self.event_manager = EventManager(db)

    def start_task(self, item: Item, owner: str):
        with self.lock:
            tid = self.__inc()
            self.state[owner] = Task(tid, item.id, item.name, now().timestamp()*1000)
            return tid

    def __inc(self):
        self.tid += 1
        return self.tid

    def finish_task(self, tid: int, xid: int, owner: str) -> bool:
        with self.lock:
            if self.match(tid, xid, owner):
                self.__insert_record(owner)
                self.state.pop(owner)
                return True
            return False

    def clear_task(self, tid: int, xid: int, reason: str, owner: str) -> bool:
        with self.lock:
            if self.match(tid, xid, owner):
                task = self.state.pop(owner)
                self.event_manager.add_event(f"由于 {reason} 中断番茄钟 {task.taskName}", owner)
                return True
            return False

    def get_task(self, owner: str)-> Dict | None:
        t = self.state.get(owner)
        if t:
            return t._asdict()


    def has_task(self, owner) -> bool:
        return self.state.get(owner) is not None

    def match(self, tid: int, xid: int, owner: str):
        t = self.state.get(owner)
        if t:
            return t.itemId == xid and t.taskId == tid        
        return False

    def create_record(self, record:TomatoTaskRecord):
        self.db.add(record)
        self.db.commit()

    def __insert_record(self, owner: str):
        task = self.state[owner]
        record = TomatoTaskRecord(start_time=parse_timestamp(task.startTime / 1000), finish_time=now(),
                                  owner=owner, name=task.taskName)
        self.create_record(record)


Record = namedtuple("Record", ["start", "finish", "title", "extend"])


class TomatoRecordManager:
    def __init__(self, db):
        self.db = db

    def get_time_line_summary(self, owner:str):
        record = self.__select_record_before(owner, today_begin())
        return {"counter": self.__time_line_stat(record), "items": [{"start": get_hour_str_from(r.start_time), "finish": get_hour_str_from(r.finish_time), "title": r.name} for r in record]}

    # def get_tomato_stat(self, owner):
    #     d = self.__load_data(owner)
    #     return {"total": self.__total_stat(d), "today": self.__today_stat(d), "week": self.__week_chart_stat(d)}

    # def get_daily_stat(self, owner):
    #     d = self.__load_data(owner)
    #     return self.__today_stat(d)

    # def select_today_tomato(self, owner: str) -> list:
    #     return self.__select_tomato_before(owner, today_begin())

    # def select_week_tomato(self, owner: str) -> list:
    #     return self.__select_tomato_before(owner, this_week_begin())

    # def get_tomato_log(self, owner: str) -> str:
    #     return "\n".join(map(str, self.__load_data(owner=owner, limit=20)))

    # def __select_tomato_before(self, owner: str, time):
    #     stmt = sal.select(TomatoTaskRecord.name, func.count()) \
    #         .where(TomatoTaskRecord.owner == owner, TomatoTaskRecord.start_time > time) \
    #         .group_by(TomatoTaskRecord.name)

    #     items = self.db.execute(stmt).all()
    #     return list(sorted(items, key=lambda x: x[1], reverse=True))
    
    def __select_record_before(self, owner:str, time) -> List[TomatoTaskRecord]:
        stmt = sal.select(TomatoTaskRecord) \
            .where(TomatoTaskRecord.owner == owner, TomatoTaskRecord.finish_time > time) \
            .order_by(TomatoTaskRecord.id.asc())
        return self.db.execute(stmt).scalars().all()

    # def __load_data(self, owner: str, limit: int = 200) -> List[TomatoTaskRecord]:
    #     stmt = sal.select(TomatoTaskRecord).where(TomatoTaskRecord.owner == owner,
    #                                               TomatoTaskRecord.finish_time > last_month()) \
    #         .order_by(TomatoTaskRecord.id.desc()).limit(limit)
    #     return self.db.execute(stmt).scalars().all()

    @staticmethod
    def __time_line_stat(data: List[TomatoTaskRecord]) -> dict:
        time = timedelta()
        for record in data:
            time += (record.finish_time - record.start_time)
        count = len(data)
        return {"tomatoCounts": count, "totalMinutes": int(time.total_seconds() / 60)}


    # @staticmethod
    # def __total_stat(data: List[TomatoTaskRecord]) -> dict:
    #     time = timedelta()
    #     for record in data:
    #         time += (record.finish_time - record.start_time)

    #     elapsed_day = 1
    #     count = len(data)
    #     if count >= 2:
    #         first_time = data[-1].start_time
    #         last_time = data[0].finish_time
    #         elapsed_day = (last_time - first_time).days + 1

    #     average_time = time.total_seconds() / elapsed_day

    #     return {
    #         "count": count,
    #         "hour": int(time.total_seconds() / 60 / 60),
    #         "average": int(average_time / 60)
    #     }

    # @staticmethod
    # def __today_stat(data: List[TomatoTaskRecord]) -> dict:
    #     today = now().date()
    #     count = 0
    #     time = timedelta()
    #     for record in data:
    #         start = record.start_time
    #         finish = record.finish_time
    #         if start.date() == today:
    #             count += 1
    #             time += (finish - start)
    #     return {
    #         "count": count,
    #         "minute": int(time.total_seconds() / 60)
    #     }

    # @staticmethod
    # def __week_chart_stat(data: List[TomatoTaskRecord]) -> list:
    #     WEEK_LENGTH = 15
    #     today = now().date()
    #     counts = [timedelta() for _ in range(WEEK_LENGTH)]
    #     for record in data:
    #         start = record.start_time
    #         finish = record.finish_time
    #         delta = (today - start.date()).days
    #         if delta < WEEK_LENGTH:
    #             counts[delta] += (finish - start)

    #     return list(map(lambda time: int(time.total_seconds() / 60), counts))
