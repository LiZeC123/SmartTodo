import pytest

from app.models.exception import UnauthorizedException
from app.services.event_log_manager import EventManager
from app.services.weight_manager import WeightManager
from app.tests.services.make_db import make_new_db

db = make_new_db()
event_manager = EventManager(db)
weight_manager = WeightManager(event_manager)

owner = "user"
fake_owner = "fake"


def test_add_log():
    rst = weight_manager.add_log(owner=owner, weight=100.02)
    assert rst is True

    rst = weight_manager.query_log(owner=owner)
    assert len(rst) == 1

    i = int(rst[0].id)
    with pytest.raises(UnauthorizedException):
        rst = weight_manager.remove_log(owner=fake_owner, id=i)

    rst = weight_manager.remove_log(owner=owner, id=i)
    assert rst is True
