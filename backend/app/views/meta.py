from typing import Dict

from flask import Blueprint, request

from app import db, config_manager
from app.services.interpreter import OpInterpreter
from app.services.item_manager import ItemManager
from app.tools.log import Log_File
from app.views.authority import authority_check
from app.views.tool import try_get_parent_from_request

meta_bp = Blueprint('meta', __name__)

item_manager = ItemManager(db)
op_interpreter = OpInterpreter(item_manager)


# ####################### API For Functions #######################

@meta_bp.get("/api/meta/isAdmin")
@authority_check()
def is_admin(owner: str):
    return config_manager.is_admin_user(owner)


@meta_bp.get("/api/log/log")
@authority_check("ROLE_ADMIN")
def get_log(owner: str):
    with open(Log_File, encoding='utf-8') as f:
        return "".join(f.readlines())


@meta_bp.post("/api/admin/func")
@authority_check("ROLE_ADMIN")
def exec_function(owner: str):
    f: Dict = request.get_json()
    command: str = f.get("cmd", "<undefined>")
    data: str = f.get("data", "")
    parent = try_get_parent_from_request()
    op_interpreter.exec_function(command, data, parent, owner)
    return True
