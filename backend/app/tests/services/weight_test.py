from datetime import timedelta

import pytest

from app.models.exception import IllegalArgumentException, UnauthorizedException
from app.models.weight import WeightLog
from app.services.event_log_manager import EventManager
from app.services.weight_manager import WeightManager
from app.tests.services.make_db import make_new_db

db = make_new_db()
event_manager = EventManager(db)
weight_manager = WeightManager(event_manager)

owner = "user"
fake_owner = "fake"


def test_add_log():
    assert weight_manager.add_log(owner=owner, weight=100.02)

    rst = weight_manager.query_log(owner=owner)
    assert len(rst) == 1

    i = int(rst[0].id)
    with pytest.raises(UnauthorizedException):
        rst = weight_manager.remove_log(owner=fake_owner, id=i)

    rst = weight_manager.remove_log(owner=owner, id=i)
    assert rst is True


def test_plan():
    # 还未初始化时无法获得计划详情
    with pytest.raises(IllegalArgumentException):
        weight_manager.get_plan_detail(owner)

    assert weight_manager.add_log(owner, 123.45)
    assert weight_manager.init_plan(115.00, owner)
    logs = weight_manager.query_log(owner)
    assert len(logs) > 0

    # 检查详细数据
    detail = weight_manager.get_plan_detail(owner)
    assert detail.get("target_weight", 0)
    assert not detail.get("fit_line")

    # 手动插入一条新数据
    last_log = logs[0]
    new_log = WeightLog(owner=owner, weight=last_log.weight + 2, create_time=last_log.create_time + timedelta(days=1))
    weight_manager.db.add(new_log)
    weight_manager.db.flush()

    # 检查详细数据
    detail = weight_manager.get_plan_detail(owner)
    assert detail.get("target_weight", 0)
    assert detail.get("fit_line")

    # 已经有计划再次添加体重数据
    assert weight_manager.add_log(owner, 123.43)
