import datetime

import tool4time

from tool4time import *

tool4time.is_time_debug = True
tool4time.debug_time = get_datetime_from_str("2022-7-5 15:00:00")


def test_base():
    assert is_work_time()
    assert get_datetime_from_str("2022-07-15 00:00:00") == datetime(2022, 7, 15, 0, 0, 0)
    assert get_day_from_str("2022-07-15 12:00:00") == datetime(2022, 7, 15, 0, 0, 0).date()
    assert this_year_str() == "2022"
    assert parse_deadline_timestamp(get_timestamp_from_str(now_str()) * 1000).date() == today()


def test_parse_deadline_str():
    assert parse_deadline_str("7.15") == "2022-07-15 00:00:00"
    assert parse_deadline_str("6.15") == "2023-06-15 00:00:00"

    assert parse_deadline_str("7.14:12") == "2022-07-14 12:00:00"
    assert parse_deadline_str("6.15:12") == "2023-06-15 12:00:00"
