from entity import Item
from tool4time import get_timestamp_from_str, is_work_time, now_stamp, get_datetime_from_str, now


def todo_item_key(item: Item):
    value = get_timestamp_from_str(item.create_time)
    day_second = 60 * 60 * 24
    if item.work:
        # 如果处于工作时间段, 则相应时间段的任务相当于30天后提交的任务
        # 否则相当于30天以前提交的任务
        if is_work_time():
            value = value + 30 * day_second
        else:
            value = value - 30 * day_second
    if item.specific != 0:
        # 由于特定任务只能在某一天完成, 因此具有最高优先级
        value = now_stamp()
        value = value + 100 * day_second
    if item.deadline is not None:
        # deadline属性的任务比较剩余时间
        # 首先消除创建时间的分值, 统一使用当前时间
        # <3天:置顶; <7天,给予一定的权重; > 7天降低权重
        value = now_stamp()
        deadline = get_datetime_from_str(item.deadline)
        delta = deadline - now()
        value = value + (56 - 8 * delta.days) * day_second - 8 * delta.seconds
    return value


def done_item_key(item: Item):
    return get_datetime_from_str(item.finish_time)


def old_item_key(item: Item):
    return get_datetime_from_str(item.create_time)
