from flask import Blueprint, request

from app import exercise_manager
from app.views.authority import authority_check

exercise_bp = Blueprint("exercise", __name__)


@exercise_bp.post("/api/exercise/record")
@authority_check()
def add_exercise_record(owner: str):
    data: dict = request.get_json()
    exercise_type = data.get("type", "")
    time = int(data.get("time", 0))
    extra: dict = data.get("extra", {})
    return exercise_manager.add_record(exercise_type, time, extra, owner)


@exercise_bp.get("/api/exercise/plan/rowing")
@authority_check()
def plan_rowing(owner: str):
    return exercise_manager.plan_rowing(owner)


@exercise_bp.get("/api/exercise/plan/running")
@authority_check()
def plan_running(owner: str):
    pass


@exercise_bp.get("/api/exercise/plan/walking")
@authority_check()
def plan_walking(owner: str):
    pass
