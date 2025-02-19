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


@credit_bp.post("/api/credit/get_exchange_list")
@authority_check()
def get_exchange_list(owner: str):
    return query_exchange_item_list(db, owner)

@credit_bp.post("/api/credit/get_welfare_list")
@authority_check()
def get_welfare_list(owner: str):
    return query_welfare_item_list(db, owner)


@credit_bp.post("/api/credit/exchange_item")
@authority_check()
def exchange_item(owner: str):
    data: Dict = request.get_json()
    item_id = int(data.get('item_id', 0))
    return exchange(db, item_id, owner)

@credit_bp.post("/api/credit/add_exchange_item")
@authority_check(role='ROLE_ADMIN')
def admin_add_exchange_item(owner: str):
    data: Dict = request.get_json()
    name = data.get("name", "")
    price = float(data.get("price", 0.0))
    cycle = int(data.get("cycle", 0))
    factor = float(data.get("factor", 0.0))

    if name== "" or price == 0.0 or cycle == 0 or factor == 0.0:
        return False

    return add_exchange_item(db, name, price, cycle, factor)


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


@credit_bp.post("/api/credit/remove_exchange_item")
@authority_check(role='ROLE_ADMIN')
def admin_remove_exchange_item(owner: str):
    data: Dict = request.get_json()
    item_id = int(data.get('item_id', 0))
    return remove_exchange_item(db, item_id)
