from collections import defaultdict, namedtuple
from datetime import timedelta
from os.path import join
from typing import List

from tool4time import get_datetime_from_str, now

DATABASE_FOLDER = "data/database"
DATA_FILE = join(DATABASE_FOLDER, "TomatoRecord.dat")

Record = namedtuple("Record", ["start", "finish", "title", "extend"])


def load_data() -> dict:
    ans = defaultdict(list)
    with open(DATA_FILE, encoding='utf-8') as f:
        for line in f.readlines():
            start, finish, owner, title, *extend = line.split(" | ")
            ans[owner].append(Record(
                start=get_datetime_from_str(start),
                finish=get_datetime_from_str(finish),
                title=title.strip(),
                extend=extend
            ))
    return ans


def total_stat(data: List[Record]) -> dict:
    count = len(data)
    time = timedelta()
    for record in data:
        start = record.start
        finish = record.finish
        time += (finish - start)

    first_time = data[0].start
    last_time = data[-1].finish

    elapsed_day = (last_time - first_time).days + 1
    average_time = time.total_seconds() / elapsed_day

    return {
        "count": count,
        "hour": int(time.total_seconds() / 60 / 60),
        "average": int(average_time / 60)
    }


def today_stat(data: List[Record]) -> dict:
    today = now().date()
    count = 0
    time = timedelta()
    for record in data:
        start = record.start
        finish = record.finish
        if start.date() == today:
            count += 1
            time += (finish - start)
    return {
        "count": count,
        "minute": int(time.total_seconds() / 60)
    }


def week_stat(data: List[Record]) -> list:
    WEEK_LENGTH = 7
    today = now().date()
    counts = [timedelta() for _ in range(WEEK_LENGTH)]
    for record in data:
        start = record.start
        finish = record.finish
        delta = (today - start.date()).days
        if delta < WEEK_LENGTH:
            counts[delta] += (finish - start)

    return list(map(lambda time: int(time.total_seconds() / 60), counts))


def task_sort_key(task) -> float:
    DAY_SECONDS = 24 * 60 * 60
    time = task['lastTime']
    count = task['count']
    return count * DAY_SECONDS + time.timestamp()


def task_stat(data: List[Record]) -> str:
    tasks = {}
    for record in data:
        title = record.title
        finish = record.finish
        if title not in tasks:
            tasks[title] = {"name": title, "lastTime": finish, "count": 1}
        else:
            tasks[title]['lastTime'] = finish
            tasks[title]['count'] += 1
    leader_board = list(sorted(tasks.values(), key=task_sort_key, reverse=True))

    # 至多显示最近的10条记录
    content = list(map(lambda x: f"{x['name']:<8s}(x{x['count']})", leader_board[:10]))
    return "最近项目完成情况: \n" + " ".join(content[:5]) + "\n" + " ".join(content[5:10])


def report(owner: str) -> dict:
    dataset = load_data()
    if owner is None or owner not in dataset:
        return {}
    else:
        d = dataset[owner]
        return {"total": total_stat(d), "today": today_stat(d), "week": week_stat(d)}


def local_report(owner: str) -> dict:
    dataset = load_data()
    if owner is None or owner not in dataset:
        return {}
    else:
        d = dataset[owner]
        print({"total": total_stat(d), "today": today_stat(d), "week": week_stat(d)})
        print(task_stat(d))


if __name__ == '__main__':
    local_report("lizec")
