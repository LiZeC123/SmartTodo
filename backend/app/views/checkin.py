from typing import Dict

from flask import Blueprint, request

from app import db
from app.services.credit_manager import *
from app.views.authority import authority_check

checkin_bp = Blueprint("checkin", __name__)


@checkin_bp.post("/api/checkin/month_record")
@authority_check()
def month_record(owner: str):
    return ['2026-01-01 10:03:01', '2026-01-02 12:02:04']


@checkin_bp.post("/api/checkin/stat")
@authority_check()
def stat(owner: str):
    return {'total_count': 20, 'continuous_count': 2, 'achievement_count': 88, 'remaining_make_up': 2}

@checkin_bp.post("/api/checkin/record")
@authority_check()
def record(owner: str):
    return {'每日早起打卡': {'record': ['2026-05-01 10:03:01', '2026-05-02 12:02:04'], 'process': 8, 'emoji': '📚'}, '每日运动打卡': {'record': ['2026-05-01 12:02:04', '2026-05-03 12:02:04'], 'process': 2, 'emoji': '🏃🏻‍♀️'} }
