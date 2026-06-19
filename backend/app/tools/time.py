import calendar
from datetime import date, datetime, timedelta


def now() -> datetime:
    return datetime.now()


def now_str() -> str:
    return now().strftime("%Y-%m-%d %H:%M:%S")


def now_str_fn() -> str:
    return now().strftime("%Y%m%d_%H%M%S")


def today() -> date:
    return now().date()


def today_begin() -> datetime:
    return the_day_begin(now())


def the_day_begin(t: datetime):
    return t - timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond)


def the_month_begin() -> datetime:
    t = now()
    return datetime(year=t.year, month=t.month, day=1)


def this_week_begin() -> datetime:
    now_time = now()
    # 按照周统计的指标粒度可以粗一点， 大致对应7天之前即可
    return now_time - timedelta(days=7)


def get_month_bounds(t: datetime):
    # 当月第一天 00:00:00
    first_day = datetime(t.year, t.month, 1, 0, 0, 0)

    # 当月最后一天 23:59:59
    # 使用 calendar 获取当月天数
    last_day_num = calendar.monthrange(t.year, t.month)[1]  # 当月最后一天的日期数字
    last_day = datetime(t.year, t.month, last_day_num, 23, 59, 59)

    return first_day, last_day


def this_year_str() -> str:
    return now().strftime("%Y")


def get_datetime_from_str(t: str) -> datetime:
    return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")


def get_str_from_datetime(t: datetime):
    return t.strftime("%Y-%m-%d %H:%M:%S")


def get_datetime_from_month_str(t: str):
    return datetime.strptime(t, "%Y-%m")


def get_day_from_str(t: str) -> date:
    return get_datetime_from_str(t).date()


def get_timestamp_from_str(t: str) -> float:
    return datetime.timestamp(get_datetime_from_str(t))


def last_month() -> datetime:
    return now() - timedelta(days=30)


def the_day_after(day: datetime, after_day: int):
    return day + timedelta(days=after_day)


def get_hour_str_from(t: datetime) -> str:
    return datetime.strftime(t, "%H:%M")


def format_timedelta(delta: timedelta) -> str:
    days = delta.days
    secs = delta.seconds
    hours = secs // 3600
    mins = (secs % 3600) // 60
    sec = secs % 60

    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if mins > 0:
        parts.append(f"{mins}分钟")
    if sec > 0:
        parts.append(f"{sec}秒")

    return "".join(parts) or "0秒"


# ################################# API For Server ################################# #


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


def parse_befeore_time_str(date_str: str) -> datetime:
    """解析日期字符串, 与parse_deadline_str逻辑正好相反, 始终返回过去的时间"""
    if ":" in date_str:
        time_pattern = "%Y.%m.%d:%H"
    else:
        time_pattern = "%Y.%m.%d"
    this_year = datetime.strptime(f"{now().year}.{date_str}", time_pattern)
    last_year = datetime.strptime(f"{now().year - 1}.{date_str}", time_pattern)
    if now() > this_year:
        return this_year
    else:
        return last_year


def parse_time(time_str: str) -> datetime:
    t = today()
    pt = datetime.strptime(time_str, "%H:%M")
    return datetime(t.year, t.month, t.day, pt.hour, pt.minute, 0)


def is_work_time():
    # weekday返回的范围是0~6, 且周一返回0
    return 9 <= now().hour < 18 and 0 <= now().weekday() <= 4
