from typing import Dict

from flask import Blueprint, request

from app import tomato_manager, tomato_record_manager
from app.views.authority import authority_check
from app.views.tool import get_xid_from_request

tomato_bp = Blueprint('tomato', __name__)


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



@tomato_bp.post('/api/summary/getReport')
@authority_check()
def get_summary_items(owner:str):
    return tomato_record_manager.get_time_line_summary(owner)
#
# @app.post('/api/summary/getEventLine')
# @authority_check()
# def get_summary_event_line(owner:str):
#     rst = event_manager.get_today_event(owner)
#     return [i.to_dict() for i in rst]
#
#
# @app.post('/api/summary/getNote')
# @authority_check()
# def get_summary_note(owner:str):
#     return report_manager.get_today_summary(owner)
#
# @app.post('/api/summary/updateNode')
# @authority_check()
# def update_summary_note(owner:str):
#     content = request.get_json().get("content")
#     return report_manager.update_summary(content, owner)
#
# @app.get("/api/summary/getWeeklySummary")
# @authority_check()
# def get_report(owner:str):
#     summarys = report_manager.get_summary_from(this_week_begin())
#     return [s.to_dict() for s in summarys]

@tomato_bp.post('/api/summary/getSmartReport')
@authority_check()
def get_smart_analysis_report(owner:str):
    return tomato_record_manager.get_smart_analysis_report(owner)