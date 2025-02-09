from flask import Blueprint

from app.views.authority import authority_check

credit_bp = Blueprint("credit", __name__)


@credit_bp.post("/api/credit/get_credit")
@authority_check()
def get_credit():
    pass


@credit_bp.post("/api/credit/get_week_count")
@authority_check()
def get_week_count():
    pass


@credit_bp.post("/api/credit/get_detail_list")
@authority_check()
def get_detail_list():
    pass