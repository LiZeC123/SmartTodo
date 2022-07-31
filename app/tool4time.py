from datetime import datetime, date, timedelta


def now() -> datetime:
    return datetime.now()


def now_str() -> str:
    return now().strftime("%Y-%m-%d %H:%M:%S")


def now_str_fn() -> str:
    return now().strftime("%Y%m%d_%H%M%S")


def now_stamp() -> float:
    return now().timestamp()


def today() -> date:
    return now().date()


def today_begin() -> datetime:
    now_time = now()
    return now_time - timedelta(hours=now_time.hour, minutes=now_time.minute, seconds=now_time.second,
                                microseconds=now_time.microsecond)


def this_year_str() -> str:
    return now().strftime("%Y")


def get_datetime_from_str(t: str) -> datetime:
    return datetime.strptime(t, '%Y-%m-%d %H:%M:%S')


def get_day_from_str(t: str) -> date:
    return get_datetime_from_str(t).date()


def get_timestamp_from_str(t: str) -> float:
    return datetime.timestamp(get_datetime_from_str(t))


def last_month() -> datetime:
    return now() - timedelta(days=30)


# ################################# API For Server ################################# #

def parse_timestamp(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp)


def parse_deadline_timestamp(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp / 1000)


def parse_deadline_str(date_str: str) -> str:
    """解析截止日期的字符串, 将其转化为时间类型"""
    if ":" in date_str:
        time_pattern = "%Y.%m.%d:%H"
    else:
        time_pattern = "%Y.%m.%d"
    this_year = datetime.strptime(f"{now().year}.{date_str}", time_pattern)
    next_year = datetime.strptime(f"{now().year + 1}.{date_str}", time_pattern)
    if now() < this_year:
        return this_year.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return next_year.strftime("%Y-%m-%d %H:%M:%S")


def is_work_time():
    # weekday返回的范围是0~6, 且周一返回0
    return 9 <= now().hour < 18 and 0 <= now().weekday() <= 4


def zero_time() -> datetime:
    return datetime(2022, 2, 2, 2, 2)
