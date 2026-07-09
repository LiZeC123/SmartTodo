
from app.services.event_log_manager import EventManager
from app.services.exercise_manager import ExerciseManager
from app.tests.services.make_db import make_new_db

db = make_new_db()
event_manager = EventManager(db)
exercise_manager = ExerciseManager(event_manager)

owner = "user"
fake_owner = "fake"


def test_add_record():
    assert exercise_manager.add_record("RowingMachine", 1200, {"stroke_count": 120}, owner)


def test_plan_rowing():
    # 由于具有一定的随机性, 因此可以多执行几次, 覆盖更多情况
    for _ in range(10):
        rst = exercise_manager.plan_rowing(owner)
        assert len(rst["frequency"]) > 0
        assert len(rst["resistance"]) > 0
