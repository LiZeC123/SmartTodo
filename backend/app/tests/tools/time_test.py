from datetime import datetime

import app.tools.time as time


def test_base():
    _now = time.now
    time.now = lambda: time.get_datetime_from_str("2022-7-5 15:00:00")
    assert time.is_work_time()
    assert time.get_datetime_from_str("2022-07-15 00:00:00") == datetime(2022, 7, 15, 0, 0, 0)
    assert time.get_day_from_str("2022-07-15 12:00:00") == datetime(2022, 7, 15, 0, 0, 0).date()
    assert time.this_year_str() == "2022"
    assert time.parse_deadline_timestamp(time.get_timestamp_from_str(time.now_str()) * 1000).date() == time.today()
    time.now = _now


def test_begin():
    assert time.get_hour_str_from(time.get_datetime_from_str("2024-2-26 22:00:00")) == "22:00"
    time.this_week_begin()
    time.last_month()


def test_parse_deadline_str():
    _now = time.now
    time.now = lambda: time.get_datetime_from_str("2022-7-5 15:00:00")
    assert time.parse_deadline_str("7.15") == "2022-07-15 00:00:00"
    assert time.parse_deadline_str("6.15") == "2023-06-15 00:00:00"

    assert time.parse_deadline_str("7.14:12") == "2022-07-14 12:00:00"
    assert time.parse_deadline_str("6.15:12") == "2023-06-15 12:00:00"
    time.now = _now


def test_parse_time_str():
    time.parse_time("10:15")
