from entity import Item
from tool4time import get_timestamp_from_str, now_stamp, get_datetime_from_str, now


def activate_key(item: Item):
    value = item.create_time.timestamp()
    day_second = 60 * 60 * 24

    # if item.specific != 0:
    #     # 由于特定任务只能在某一天完成, 因此具有最高优先级
    #     value = now_stamp()
    #     value += 100 * day_second
    if item.deadline is not None:
        # deadline属性的任务比较剩余时间
        # 首先消除创建时间的分值, 统一使用当前时间
        # <3天:置顶; <7天,给予一定的权重; > 7天降低权重
        value = now_stamp()
        deadline = item.deadline
        delta = deadline - now()
        value += (56 - 8 * delta.days) * day_second - 8 * delta.seconds
    return value


def create_time_key(item: Item):
    value = item.create_time.timestamp()
    day_second = 60 * 60 * 24

    # 已经完成的任务排到最下方
    if item.used_tomato == item.expected_tomato:
        value += 100 * day_second

    return value
