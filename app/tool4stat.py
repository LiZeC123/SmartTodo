from collections import namedtuple
from datetime import timedelta
from typing import List

import sqlalchemy as sal

from entity import TomatoTaskRecord, Item, ItemType, TomatoType
from tool4time import last_month, now

Record = namedtuple("Record", ["start", "finish", "title", "extend"])


def load_data(db, owner: str, limit: int = 200) -> List[TomatoTaskRecord]:
    stmt = sal.select(TomatoTaskRecord).where(TomatoTaskRecord.owner == owner,
                                              TomatoTaskRecord.finish_time > last_month()) \
        .order_by(TomatoTaskRecord.id.desc()).limit(limit)
    return db.execute(stmt).scalars().all()


def total_stat(data: List[TomatoTaskRecord]) -> dict:
    count = len(data)
    time = timedelta()
    for record in data:
        start = record.start_time
        finish = record.finish_time
        time += (finish - start)

    first_time = data[-1].start_time
    last_time = data[0].finish_time

    elapsed_day = (last_time - first_time).days + 1
    average_time = time.total_seconds() / elapsed_day

    return {
        "count": count,
        "hour": int(time.total_seconds() / 60 / 60),
        "average": int(average_time / 60)
    }


def today_stat(data: List[TomatoTaskRecord]) -> dict:
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


def week_stat(data: List[TomatoTaskRecord]) -> list:
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


def report(db, owner: str) -> dict:
    d = load_data(db, owner)
    return {"total": total_stat(d), "today": today_stat(d), "week": week_stat(d)}


def done_task_stat(db, owner: str) -> list:
    stmt = sal.select(Item.name).where(Item.owner == owner, Item.expected_tomato == Item.used_tomato)
    return db.execute(stmt).scalars().all()


def undone_task_stat(db, owner: str) -> list:
    stmt = sal.select(Item.name).where(Item.owner == owner, Item.tomato_type == TomatoType.Today,
                                       Item.expected_tomato != Item.used_tomato,
                                       Item.item_type != ItemType.Note)
    return db.execute(stmt).scalars().all()


def local_report(db, owner: str):
    d = report(db, owner)
    print({"总体统计": d['total'], "今日数据": d['today'], "近15日数据": d['week']})
    print(f"已完成任务统计: {done_task_stat(db, owner)}")
    print(f"未完成任务统计: {undone_task_stat(db, owner)}")
