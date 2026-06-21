from flask import Blueprint, request

from app import weight_manager
from app.views.authority import authority_check

weight_bp = Blueprint("weight", __name__)


@weight_bp.post("/api/me/weight/query")
@authority_check()
def query(owner: str):
    logs = weight_manager.query_log(owner)
    return [log.to_dict() for log in logs]


@weight_bp.post("/api/me/weight/add")
@authority_check()
def add(owner: str):
    data: dict = request.get_json()
    weight = float(data.get("weight", 0))
    return weight_manager.add_log(owner, weight)


@weight_bp.post("/api/me/weight/remove")
@authority_check()
def remove(owner: str):
    data = request.get_json()
    id = int(data.get("id"))
    return weight_manager.remove_log(owner, id)


@weight_bp.get("/api/weight/plan/init")
@authority_check()
def is_plan_inited(owner: str):
    plan = weight_manager.query_plan(owner)
    return plan is not None


@weight_bp.post("/api/weight/plan/init")
@authority_check()
def init_plan(owner: str):
    data = request.get_json()
    target_weight = float(data.get("target_weight", 0))
    return weight_manager.init_plan(target_weight, owner)


@weight_bp.get("/api/weight/plan/detail")
@authority_check()
def get_plan_detail(owner: str):
    return weight_manager.get_plan_detail(owner)
