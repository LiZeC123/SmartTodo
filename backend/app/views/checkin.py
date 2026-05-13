
from flask import Blueprint, request

from app import checkin_manager
from app.tools.time import get_datetime_from_month_str
from app.views.authority import authority_check

checkin_bp = Blueprint("checkin", __name__)


@checkin_bp.post("/api/checkin/month_record")
@authority_check()
def month_record(owner: str):
    f: dict = request.get_json()
    item_name: str = f.get('item_name', '')
    month: str = f.get('month', '')
    t = get_datetime_from_month_str(month)
    return checkin_manager.get_month_data(item_name, t, owner)


@checkin_bp.post("/api/checkin/stat")
@authority_check()
def stat(owner: str):
    f: dict = request.get_json()
    item_name: str = f.get('item_name', '')
    return checkin_manager.get_stat(item_name, owner)

@checkin_bp.post("/api/checkin/record")
@authority_check()
def record(owner: str):
    return checkin_manager.get_all_data(owner)

