from typing import Dict

from flask import Blueprint, request

from app import db
from app.services.item_manager import ItemManager
from app.services.tomato_manager import TomatoManager
from app.views.authority import authority_check
from app.views.tool import get_xid_from_request

tomato_bp = Blueprint('tomato', __name__)

item_manager = ItemManager(db)
tomato_manager = TomatoManager(db, item_manager)


@tomato_bp.post('/api/tomato/setTask')
@authority_check()
def set_tomato_task(owner: str):
    iid = get_xid_from_request()
    return tomato_manager.start_task(iid, owner)


@tomato_bp.get('/api/tomato/getTask')
@authority_check()
def get_tomato_task(owner: str):
    return tomato_manager.get_task(owner)


@tomato_bp.post('/api/tomato/undoTask')
@authority_check()
def undo_tomato_task(owner: str):
    iid = get_xid_from_request()
    f: Dict = request.get_json()
    reason = f['reason']
    return tomato_manager.clear_task(iid, reason, owner)


@tomato_bp.post('/api/tomato/finishTask')
@authority_check()
def finish_tomato_task(owner: str):
    iid = get_xid_from_request()
    return tomato_manager.finish_task(iid, owner)


@tomato_bp.post('/api/tomato/addRecord')
@authority_check()
def add_record(owner: str):
    f: Dict = request.get_json()
    name = f['name']
    start_time = f['startTime']
    return tomato_manager.add_tomato_record(name, start_time, owner)
