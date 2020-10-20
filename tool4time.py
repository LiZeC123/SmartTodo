import datetime
import os

from tool4log import logger


def is_time_debug() -> bool:
    return os.path.exists("database/time.debug")


def debug_time() -> str:
    with open("database/time.debug") as f:
        return f.readline()


def now() -> datetime.datetime:
    if is_time_debug():
        r = datetime.datetime.strptime(debug_time(), "%Y-%m-%d %H:%M:%S")
        logger.warning(f" now() is in DEBUG mode and now is {r}")
        return r
    else:
        return datetime.datetime.now()


def now_str() -> str:
    return now().strftime("%Y-%m-%d %H:%M:%S")


def now_stamp() -> float:
    return now().timestamp()


def today() -> datetime.date:
    if is_time_debug():
        r = datetime.datetime.strptime(debug_time(), "%Y-%m-%d %H:%M:%S").date()
        logger.warning(f" today() is in DEBUG mode and today is {r}")
        return r
    else:
        return datetime.date.today()


def this_year_str() -> str:
    return now().strftime("%Y")


def get_datetime_from_str(time: str) -> datetime.datetime:
    return datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')


def get_day_from_str(time: str) -> datetime.date:
    return get_datetime_from_str(time).date()


def get_timestamp_from_str(time: str) -> float:
    return datetime.datetime.timestamp(get_datetime_from_str(time))


# ################################# API For Server ################################# #


def parse_deadline_str(date_str: str) -> str:
    """解析截止日期的字符串, 将其转化为时间类型"""
    if ":" in date_str:
        time_pattern = "%Y.%m.%d:%H"
    else:
        time_pattern = "%Y.%m.%d"
    this_year = datetime.datetime.strptime(f"{now().year}.{date_str}", time_pattern)
    next_year = datetime.datetime.strptime(f"{now().year + 1}.{date_str}", time_pattern)
    if now() < this_year:
        return this_year.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return next_year.strftime("%Y-%m-%d %H:%M:%S")


def is_work_time():
    # weekday返回的范围是0~6, 且周一返回0
    return 9 <= now().hour < 18 and 0 <= now().weekday() <= 4


if __name__ == '__main__':
    delta = get_datetime_from_str("2020-2-13 12:00:00") - get_datetime_from_str("2020-2-14 12:00:00")
    print(delta.total_seconds())
