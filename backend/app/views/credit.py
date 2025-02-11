from typing import Dict

from flask import Blueprint, request

from app import db
from app.services.credit_manager import *
from app.views.authority import authority_check

credit_bp = Blueprint("credit", __name__)


@credit_bp.post("/api/credit/get_credit")
@authority_check()
def get_credit(owner: str):
    total = query_credit(db, owner)
    earn, used = query_credit_week(db, owner)
    return {"all": total, "earned": earn, "used": used}


@credit_bp.post("/api/credit/get_detail_list")
@authority_check()
def get_detail_list(owner: str):
    return query_credit_list(db, owner)


@credit_bp.post("/api/credit/add")
@authority_check()
def add_other_credits(owner: str):
    data: Dict = request.get_json()
    credit_type = data.get('type')
    score = data.get('score')
    if credit_type is None or score is None:
        return False

    reason = '完成任务 '
    if credit_type == 'sports':
        reason += '我爱运动'

    return update_credit(db, owner, int(score), reason)