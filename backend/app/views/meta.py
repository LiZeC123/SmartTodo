from flask import Blueprint, request

from app import config_manager, event_manager, op_interpreter
from app.tools.log import Log_File
from app.tools.time import get_hour_str_from, today_begin
from app.views.authority import authority_check
from app.views.tool import try_get_parent_from_request

meta_bp = Blueprint("meta", __name__)


@meta_bp.get("/api/meta/isAdmin")
@authority_check()
def is_admin(owner: str):
    return config_manager.is_admin_user(owner)


@meta_bp.get("/api/log/log")
@authority_check("ROLE_ADMIN")
def get_log(owner: str):
    with open(Log_File, encoding="utf-8") as f:
        return f.read()


@meta_bp.get("/api/log/event")
@authority_check("ROLE_ADMIN")
def get_event_log(owner: str):
    logs = event_manager.get_event_log_after(today_begin(), owner)
    lines = [f"{get_hour_str_from(log.create_time)}: {log.msg}" for log in logs]
    return "\n".join(lines)


@meta_bp.post("/api/admin/func")
@authority_check("ROLE_ADMIN")
def exec_function(owner: str):
    f: dict = request.get_json()
    command: str = f.get("cmd", "<undefined>")
    data: str = f.get("data", "")
    parent = try_get_parent_from_request()
    op_interpreter.exec_function(command, data, parent, owner)
    return True
