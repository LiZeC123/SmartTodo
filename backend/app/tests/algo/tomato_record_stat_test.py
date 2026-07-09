from datetime import datetime, timedelta

from app.algo.tomato_record_stat import calculate_metrics
from app.models.tomato import TomatoTaskRecord

owner = "user"
name = "MockItem"


def test_calculate_metrics():
    start_time = datetime(year=2026, month=1, day=1, hour=8)
    finish_time = datetime(year=2026, month=1, day=1, hour=8, minute=30)
    delta = timedelta(hours=7)

    records = []
    for i in range(1, 100):
        records.append(TomatoTaskRecord(id=i, start_time=start_time, finish_time=finish_time, owner=owner, name=name))
        start_time += delta
        finish_time += delta

    stat = calculate_metrics(records)
    assert stat is not None
