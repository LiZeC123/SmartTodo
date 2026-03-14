import pytest

from app.services.tomato_manager import *
from app.services.weight_manager import add_log, query_log, remove_log
from app.tests.services.make_db import make_new_db
from app.tools.exception import UnauthorizedException

db = make_new_db()



owner = "user"
fake_owner = "fake"


def test_add_log():
    rst = add_log(db, owner=owner, weight=100.02)
    assert rst is True

    rst = query_log(db, owner=owner)
    assert len(rst) > 0

    i = int(rst[0]["id"])
    with pytest.raises(UnauthorizedException):
        rst = remove_log(db,owner=fake_owner,id=i)

    rst = remove_log(db,owner=owner,id=i)
    assert rst is True


