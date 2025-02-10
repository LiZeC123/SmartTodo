from typing import Dict

from flask import Blueprint, request

from app import db
from app.services.weight_manager import *
from app.tools.log import Log_File
from app.views.authority import authority_check
from app.views.tool import try_get_parent_from_request

weight_bp = Blueprint('weight', __name__)


@weight_bp.post("/api/me/weight/query")
@authority_check()
def query(owner: str):
    return query_log(db, owner)


@weight_bp.post("/api/me/weight/add")
@authority_check()
def add(owner: str):
    data: Dict = request.get_json()
    weight = float(data.get('weight'))
    return add_log(db, owner, weight)


@weight_bp.post("/api/me/weight/remove")
@authority_check()
def remove(owner: str):
    data = request.get_json()
    id = int(data.get('id'))
    return remove_log(db, owner, id)


