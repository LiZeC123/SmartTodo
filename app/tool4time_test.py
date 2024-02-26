import datetime

import tool4time

from tool4time import *


def test_base():
    _now = tool4time.now
    tool4time.now = lambda: get_datetime_from_str("2022-7-5 15:00:00")
    assert is_work_time()
    assert get_datetime_from_str("2022-07-15 00:00:00") == datetime(2022, 7, 15, 0, 0, 0)
    assert get_day_from_str("2022-07-15 12:00:00") == datetime(2022, 7, 15, 0, 0, 0).date()
    assert this_year_str() == "2022"
    assert parse_deadline_timestamp(get_timestamp_from_str(now_str()) * 1000).date() == today()
    tool4time.now = _now

def test_begin():
    assert get_hour_str_from(get_datetime_from_str("2024-2-26 22:00:00")) == '22:00'
    this_week_begin()
    last_month()


def test_parse_deadline_str():
    _now = tool4time.now
    tool4time.now = lambda: get_datetime_from_str("2022-7-5 15:00:00")
    assert parse_deadline_str("7.15") == "2022-07-15 00:00:00"
    assert parse_deadline_str("6.15") == "2023-06-15 00:00:00"

    assert parse_deadline_str("7.14:12") == "2022-07-14 12:00:00"
    assert parse_deadline_str("6.15:12") == "2023-06-15 12:00:00"
    tool4time.now = _now


def test_parse_time_str():
    parse_time("10:15")
