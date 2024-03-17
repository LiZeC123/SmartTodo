import functools
from typing import Any, Dict, Optional, Sequence

from flask import Flask, jsonify, request, abort


from entity import Item, init_database
from exception import IllegalArgumentException, UnauthorizedException
from service4config import ConfigManager
from service4interpreter import OpInterpreter
from tool4log import Log_File
from tool4event import EventManager
from tool4report import ReportManager
from server4item import ItemManager
from tool4task import TaskManager
from tool4token import TokenManager
from tool4tomato import TomatoManager, TomatoRecordManager
from tool4log import logger
from tool4time import parse_deadline_timestamp

app = Flask(__name__)


db_session = init_database()
config_manager = ConfigManager()
event_manager = EventManager(db_session)
report_manager = ReportManager(db_session)
item_manager = ItemManager(db_session)
task_manager = TaskManager()
token_manager = TokenManager()
tomato_manager = TomatoManager(db_session, item_manager=item_manager)
tomato_record_manager = TomatoRecordManager(db_session, item_manager=item_manager)
op_interpreter = OpInterpreter(item_manager)


class authority_check:
    def __init__(self, role='ROLE_USER') -> None:
        self.role = role

    def __call__(self, func) -> Any:
        @functools.wraps(func)
        def wrapped_function(*args, **kwargs):
            token = request.headers.get('token')
            if token is None or not token_manager.valid_token(token, self.role):
                abort(401)

            try:
                owner = token_manager.get_username_from(token)
                return jsonify(func(*args, **kwargs, owner=owner))
            except UnauthorizedException as e:
                logger.warning(e)
                abort(401)  

        return wrapped_function

@app.post('/api/login')
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if config_manager.try_login(username, password):
        return token_manager.create_token({"username": username, "role": config_manager.get_roles(username)})
    else:
        real_ip = request.headers.get("X-Real-IP")
        logger.warning(f"已拒绝来自{real_ip}的请求, 此请求尝试以'{password}'为密码登录账号'{username}'")
        return ""



@app.post('/api/logout')
@authority_check()
def logout():
    token = request.form.get('token')
    if token is None:
        return jsonify(False)
    token_manager.remove_token(token)
    return jsonify(True)


# ####################### API For Item #######################
@app.post("/api/item/create")
@authority_check()
def create_item(owner:str):
    f: Dict = request.get_json()
    item = Item(name=f['name'], item_type=f['itemType'], owner=owner)

    if "deadline" in f:
        item.deadline = parse_deadline_timestamp(f["deadline"])

    if "repeatable" in f:
        item.repeatable = bool(f["repeatable"])

    if "specific" in f:
        item.specific = int(f["specific"])

    if "parent" in f:
        item.parent = int(f["parent"])

    item_manager.create(item)


@app.post('/api/item/getAll')
@authority_check()
def get_all_item(owner:str):
    parent = try_get_parent_from_request()
    return item_manager.select_all(owner=owner, parent=parent)


@app.post('/api/item/getActivate')
@authority_check()
def get_activate_item(owner:str):
    parent = try_get_parent_from_request()
    return item_manager.select_activate(owner, parent=parent)


@app.post('/api/item/back')
@authority_check()
def back_item(owner:str) -> bool:
    xid = get_xid_from_request()
    parent = try_get_parent_from_request()
    return item_manager.undo(xid=xid, owner=owner, parent=parent)


@app.post("/api/item/remove")
@authority_check()
def remove_item(owner:str):
    iid = get_xid_from_request()
    return item_manager.remove_by_id(xid=iid, owner=owner)


@app.post('/api/item/incExpTime')
@authority_check()
def increase_expected_tomato(owner:str) -> bool:
    xid = get_xid_from_request()
    return item_manager.increase_expected_tomato(xid=xid, owner=owner)


@app.post('/api/item/incUsedTime')
@authority_check()
def increase_used_tomato(owner:str) -> bool:
    xid = get_xid_from_request()
    return item_manager.increase_used_tomato(xid=xid, owner=owner)


@app.post('/api/item/toTodayTask')
@authority_check()
def to_today_task(owner:str) -> bool:
    xid = get_xid_from_request()
    return item_manager.to_today_task(xid=xid, owner=owner)


@app.post("/api/item/getTitle")
@authority_check()
def get_title(owner:str):
    iid = get_xid_from_request()
    return item_manager.get_title(iid, owner)

@app.post("/api/item/getTomato")
@authority_check()
def get_tomato_item(owner:str):
    return item_manager.get_tomato_item(owner)

@app.post("/api/item/getItemWithSubTask")
@authority_check()
def get_item_with_sub_task(owner:str):
    return item_manager.get_item_with_sub_task(owner)




def get_xid_from_request() -> int:
    f: Dict = request.get_json()
    xid = f.get('id')
    if xid is None:
        raise IllegalArgumentException("fail to get xid")
    return int(xid)


def get_required_value_from_request(f:Dict, names: Sequence[str]) -> tuple:
    rst = []
    for name in names:
        v = f.get(name)
        if v is None:
            raise IllegalArgumentException(f"fail to get {name} from request")
        rst.append(v)
    return tuple(rst)


def try_get_parent_from_request() -> Optional[int]:
    f: Dict = request.get_json()
    parent = f.get("parent")
    if parent is None:
        return None

    return int(parent)

# ####################### API For File #######################

@app.post("/api/file/upload")
@authority_check()
def file_do_upload(owner:str):
    file = request.files['myFile']
    parent = int(request.form.get('parent', '0'))

    # 0表示不属于任何类型，转换为None类型进行存储
    if parent == 0:
        parent = None

    item_manager.create_upload_file(file, parent, owner)
    return True


# ####################### API For Note #######################

@app.post('/api/note/content')
@authority_check()
def note_content(owner:str):
    nid = get_xid_from_request()
    return item_manager.get_note(nid, owner=owner)


@app.post('/api/note/update')
@authority_check()
def note_update(owner:str):
    nid = get_xid_from_request()
    content = request.get_json().get("content")
    item_manager.update_note(nid, owner=owner, content=content)


# ####################### API For Tomato #########################
@app.post('/api/tomato/setTask')
@authority_check()
def set_tomato_task(owner:str):
    iid = get_xid_from_request()
    return tomato_manager.start_task(iid, owner)


@app.get('/api/tomato/getTask')
@authority_check()
def get_tomato_task(owner:str):
    return tomato_manager.get_task(owner)


@app.post('/api/tomato/undoTask')
@authority_check()
def undo_tomato_task(owner:str):
    iid = get_xid_from_request()
    f: Dict = request.get_json()
    reason = f['reason']
    return tomato_manager.clear_task( iid, reason, owner)


@app.post('/api/tomato/finishTask')
@authority_check()
def finish_tomato_task(owner:str):
    iid = get_xid_from_request()
    return tomato_manager.finish_task(iid, owner)


@app.post('/api/tomato/addRecord')
@authority_check()
def add_record(owner:str):
    f: Dict = request.get_json()
    name = f['name']
    start_time = f['startTime']
    return tomato_manager.add_tomato_record(name, start_time, owner)


# ####################### API For Summary #######################

@app.post('/api/summary/getReport')
@authority_check()
def get_summary_items(owner:str):
    return tomato_record_manager.get_time_line_summary(owner)

@app.post('/api/summary/getEventLine')
@authority_check()
def get_summary_event_line(owner:str):
    rst = event_manager.get_today_event(owner)
    return [i.to_dict() for i in rst]


@app.post('/api/summary/getNote')
@authority_check()
def get_summary_note(owner:str):
    return report_manager.get_today_summary(owner)

@app.post('/api/summary/updateNode')
@authority_check()
def update_summary_note(owner:str):
    content = request.get_json().get("content")
    return report_manager.update_summary(content, owner)

@app.post('/api/summary/getSmartReport')
@authority_check()
def get_smart_analysis_report(owner:str):
    return tomato_record_manager.get_smart_analysis_report(owner)


# ####################### API For Functions #######################

@app.get("/api/meta/isAdmin")
@authority_check()
def is_admin(owner:str):
    return config_manager.is_admin_user(owner)


@app.get("/api/log/log")
@authority_check("ROLE_ADMIN")
def get_log(owner:str):
    with open(Log_File, encoding='utf-8') as f:
        return "".join(f.readlines())



@app.post("/api/admin/func")
@authority_check("ROLE_ADMIN")
def exec_function(owner:str):
    f: Dict = request.get_json()
    command: str = f.get("cmd", "<undefined>")
    data: str = f.get("data", "")
    parent = try_get_parent_from_request()
    op_interpreter.exec_function(command, data, parent, owner)
    return True


@app.teardown_appcontext
def remove_session(exception=None):
    db_session.commit()
    db_session.remove()
    if exception:
        logger.exception(f"清理Session: 此Session中存在异常 {exception}")

def init_task_manager():
    task_manager.add_daily_task("垃圾回收", item_manager.garbage_collection, "01:00")
    task_manager.add_daily_task("重置可重复任务", item_manager.reset_daily_task, "01:10")
    task_manager.add_daily_task("重置未完成的今日任务", item_manager.reset_today_task, "01:20")
    task_manager.start()


if __name__ == '__main__':
    init_task_manager()
    app.run("localhost", 4231, threaded=True)
