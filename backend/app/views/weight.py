from flask import Blueprint, request

from app import weight_manager
from app.views.authority import authority_check

weight_bp = Blueprint("weight", __name__)


@weight_bp.post("/api/me/weight/query")
@authority_check()
def query(owner: str):
    return weight_manager.query_log(owner)


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
