from typing import Optional

from tool4log import logger
from tool4time import now, today, is_work_time, now_stamp, get_timestamp_from_str, \
    get_day_from_str, get_datetime_from_str


def check_specific_item_is_todo(item):
    # 特定任务在每周设定的日期, 如果完成时间没有被更新,则重置到todo列表
    create_day = get_day_from_str(item['createTime'])
    if create_day.weekday() == today().weekday():
        if item['finishTime'] is None:
            # 没有完成时间则必定属于todo列表
            return True
        else:
            # 否则检查完成时间是否小于今天, 是则说明以前完成了, 但今天还需要重复完成
            finish_day = get_day_from_str(item['finishTime'])
            return finish_day < today()


def map_item(item, parent: Optional[int], owner: str):
    if owner != item['owner']:
        return "miss"
    if parent is None and item["parent"] is not None:
        # 如果是全局的请求, 则过滤在Note中创建的Item
        return "miss"
    if parent is not None and (item["parent"] is None or int(item["parent"]) != int(parent)):
        # 如果是Note中的请求, 则过滤全局创建的Item
        return "miss"
    if item['old'] is True:
        return "old"
    if item['finishTime'] is None:
        return "todo"
    if item['specific'] != 0:
        return "todo" if check_specific_item_is_todo(item) else "done"
    if item['repeatable'] is True:
        return "done"
    if item['finishTime'] is not None:
        finish_day = get_day_from_str(item['finishTime'])
        return "done" if finish_day == today() else "delete"
    else:
        return "delete"


def map_file(item):
    if item['itemType'] == "file":
        if item['finishTime'] is None:
            return "todo"
        finish_day = get_day_from_str(item['finishTime'])
        return "done" if finish_day == today() else "delete"
    return "delete"


def todo_item_key(item):
    value = get_timestamp_from_str(item['createTime'])
    day_second = 60 * 60 * 24
    if item['work']:
        # 如果处于工作时间段, 则相应时间段的任务相当于30天后提交的任务
        # 否则相当于30天以前提交的任务
        if is_work_time():
            value = value + 30 * day_second
        else:
            value = value - 30 * day_second
    if item['specific'] != 0:
        # 由于特定任务只能在某一天完成, 因此具有最高优先级
        value = now_stamp()
        value = value + 100 * day_second
    if item['deadline'] is not None:
        # deadline属性的任务比较剩余时间
        # 首先消除创建时间的分值, 统一使用当前时间
        # <3天:置顶; <7天,给予一定的权重; > 7天降低权重
        value = now_stamp()
        deadline = get_datetime_from_str(item['deadline'])
        delta = deadline - now()
        value = value + (56 - 8 * delta.days) * day_second - 8 * delta.seconds
    return value


def done_item_key(item):
    return get_datetime_from_str(item['finishTime'])


def old_item_key(item):
    return get_datetime_from_str(item['createTime'])


def update_urgent_level(item):
    if item['deadline'] is not None:
        deadline = get_datetime_from_str(item['deadline'])
        # 时间相减后的形式是 xx days, xx:xx:xx, 直接忽略不足一天的部分
        delta = (deadline - now()).days
        return delta

    return -1


def update_repeatable_done_status(item):
    if item['repeatable'] is True and item['finishTime'] is not None:
        finish_day = get_day_from_str(item['finishTime'])
        # 如果小于当前日期, 则重置
        if finish_day < today():
            logger.info(f"DataManager: Reset Repeatable Item {item['name']} To Todo")
            return None
    # 其他情况都不变
    return item['finishTime']
