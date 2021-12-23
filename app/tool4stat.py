from collections import defaultdict
from datetime import timedelta
from os.path import join

from tool4time import get_datetime_from_str, now

DATABASE_FOLDER = "data/database"
DATA_FILE = join(DATABASE_FOLDER, "TomatoRecord.dat")


def load_data() -> dict:
    ans = defaultdict(list)
    with open(DATA_FILE, encoding='utf-8') as f:
        for line in f.readlines():
            start, finish, owner, title = line.split(" | ")
            ans[owner].append({
                "start": get_datetime_from_str(start),
                "finish": get_datetime_from_str(finish),
                "title": title.strip()
            })
    return ans


def total_stat(data: list) -> dict:
    count = len(data)
    time = timedelta()
    for record in data:
        start = record['start']
        finish = record['finish']
        time += (finish - start)

    first_time = data[0]['start']
    last_time = data[-1]['finish']

    elapsed_day = (last_time - first_time).days + 1
    average_time = time.total_seconds() / elapsed_day

    return {
        "count": count,
        "hour": int(time.total_seconds() / 60 / 60),
        "average": int(average_time / 60)
    }

    # return f"累计完成番茄钟数量:{count} " \
    #        f"累计学习时间: {int(time.total_seconds() / 60 / 60)}小时 " \
    #        f"日均学习时间: {int(average_time / 60)}分钟 "


def today_stat(data: list) -> dict:
    today = now().date()
    count = 0
    time = timedelta()
    for record in data:
        start = record['start']
        finish = record['finish']
        if start.date() == today:
            count += 1
            time += (finish - start)
    return {
        "count": count,
        "minute": int(time.total_seconds() / 60)
    }

    # return f"今日完成番茄钟数量: {count} " \
    #        f"今日累计学习时间: {int(time.total_seconds() / 60)}分钟 "


def task_sort_key(record) -> float:
    DAY_SECONDS = 24 * 60 * 60
    time = record['lastTime']
    count = record['count']
    return count * DAY_SECONDS + time.timestamp()


def task_stat(data: list) -> str:
    tasks = {}
    for record in data:
        title = record['title']
        finish = record['finish']
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
        return {"total": total_stat(d), "today": today_stat(d)}


if __name__ == '__main__':
    print(report("lizec"))
