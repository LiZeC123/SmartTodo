import functools
import json
from typing import Dict

from flask import Flask, request, abort

from entity import Item
from server import Manager
from service4config import ConfigManager
from tool4log import logger, Log_File
from tool4time import parse_deadline_timestamp
from tool4token import TokenManager

app = Flask(__name__)

manager = Manager()
token = TokenManager()
config = ConfigManager()


def make_result(data) -> str:
    return json.dumps(data)


def logged(func=None, role='ROLE_USER', wrap=True):
    if func is None:
        return functools.partial(logged, role=role)

    @functools.wraps(func)  # 设置函数名称，否则由于函数同名导致Flask绑定失败
    def wrapper(*args, **kw):
        if not wrap:
            return func(*args, **kw)
        elif token.check_token(request, role):
            return make_result(func(*args, **kw))
        else:
            abort(401)

    return wrapper


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if config.try_login(username, password):
        return token.create_token({"username": username, "role": config.get_roles(username)})
    else:
        real_ip = request.headers.get("X-Real-IP")
        logger.warning(f"已拒绝来自{real_ip}的请求, 此请求尝试以'{password}'为密码登录账号'{username}'")
        return abort(401)


@app.route('/api/logout', methods=['POST'])
@logged
def logout():
    token.remove_token(request.form.get('token'))


# ####################### API For Item #######################
@app.route("/api/item/create", methods=["POST"])
@logged
def create_item():
    f: Dict = request.get_json()
    item: Item = Item(0, f['name'], f['itemType'], token.get_username(request))

    if "deadline" in f:
        item.deadline = parse_deadline_timestamp(f["deadline"])

    if "repeatable" in f:
        item.repeatable = bool(f["repeatable"])

    if "specific" in f:
        item.specific = int(f["specific"])

    if "parent" in f:
        item.parent = int(f["parent"])

    if "today" in f:
        item.tomato_type = "today"

    if "exp" in f:
        item.expected_tomato = int(f["exp"])

    manager.create(item)


@app.route('/api/item/getAll', methods=['POST'])
@logged
def get_all_item():
    owner: str = token.get_username(request)
    parent = try_get_parent_from_request()
    return manager.all_items(owner, parent=parent)


@app.route('/api/item/getActivate', methods=['POST'])
@logged
def get_activate_item():
    # Deprecated
    owner: str = token.get_username(request)
    parent = try_get_parent_from_request()
    return manager.activate_items(owner, parent=parent)


@app.route('/api/item/getSummary', methods=['POST'])
@logged
def get_summary():
    owner: str = token.get_username(request)
    return manager.get_summary(owner)


@app.route('/api/item/back', methods=['POST'])
@logged
def back_item() -> bool:
    xid = get_xid_from_request()
    owner = token.get_username(request)
    parent = try_get_parent_from_request()
    return manager.undo(xid=xid, owner=owner, parent=parent)


@app.route("/api/item/remove", methods=["POST"])
@logged
def remove_item():
    iid = get_xid_from_request()
    owner = token.get_username(request)
    manager.remove(iid, owner)


@app.route('/api/item/increaseExpectedTomatoTime', methods=['POST'])
@logged
def increase_expected_tomato() -> bool:
    xid = get_xid_from_request()
    owner = token.get_username(request)
    return manager.increase_expected_tomato(xid=xid, owner=owner)


@app.route('/api/item/increaseUsedTomatoTime', methods=['POST'])
@logged
def increase_used_tomato() -> bool:
    xid = get_xid_from_request()
    owner = token.get_username(request)
    return manager.increase_used_tomato(xid=xid, owner=owner)


@app.route('/api/item/toUrgentTask', methods=['POST'])
@logged
def to_urgent_task() -> bool:
    xid = get_xid_from_request()
    owner = token.get_username(request)
    return manager.to_urgent_task(xid=xid, owner=owner)


@app.route('/api/item/toTodayTask', methods=['POST'])
@logged
def to_today_task() -> bool:
    xid = get_xid_from_request()
    owner = token.get_username(request)
    return manager.to_today_task(xid=xid, owner=owner)


@app.route("/api/item/getTitle", methods=["POST"])
@logged
def get_title():
    iid = get_xid_from_request()
    owner = token.get_username(request)
    title = manager.get_title(iid, owner)
    return title


def get_xid_from_request() -> int:
    f: Dict = request.get_json()
    xid = int(f.get('id'))
    return xid


def get_tid_from_request() -> int:
    f: Dict = request.get_json()
    tid = int(f.get('tid'))
    return tid


def try_get_parent_from_request() -> int:
    f: Dict = request.get_json()
    if f is not None:
        return int(f.get("parent", "0"))
    else:
        return 0


# ####################### API For File #######################

@app.route("/api/file/upload", methods=["POST"])
@logged
def file_do_upload():
    file = request.files['myFile']
    parent = int(request.form['parent'])
    owner = token.get_username(request)
    return manager.create_upload_file(file, parent, owner)


# ####################### API For Note #######################

@app.route('/api/note/content', methods=['POST'])
@logged
def note_content():
    nid = get_xid_from_request()
    return manager.get_note(nid, owner=token.get_username(request))


@app.route('/api/note/update', methods=['POST'])
@logged
def note_update():
    nid = get_xid_from_request()
    content = request.get_json().get("content")
    manager.update_note(nid, owner=token.get_username(request), content=content)


@app.route('/api/note/getAll', methods=['POST'])
@logged
def note_get_all_item():
    owner: str = token.get_username(request)
    nid = get_xid_from_request()
    return manager.all_items(owner, parent=nid)


@app.route('/api/note/getTodo', methods=['POST'])
@logged
def note_get_todo_item():
    owner: str = token.get_username(request)
    nid = get_xid_from_request()
    return manager.activate_items(owner, parent=nid)


# ####################### API For SubTasks #######################

def sub_task_items():
    pass


# 1. 根据文本创建 / 查询已有记录 / 修改记录状态 / 记录转文本 / 根据文本更新记录

# ####################### API For Tomato #########################
@app.route('/api/tomato/setTask', methods=['POST'])
@logged
def set_tomato_task():
    iid = get_xid_from_request()
    owner = token.get_username(request)
    return manager.set_tomato_task(iid, owner)


@app.route('/api/tomato/getTask', methods=['GET'])
@logged
def get_tomato_task():
    owner = token.get_username(request)
    return manager.get_tomato_task(owner)


@app.route('/api/tomato/undoTask', methods=['POST'])
@logged
def undo_tomato_task():
    tid = get_tid_from_request()
    iid = get_xid_from_request()
    owner = token.get_username(request)
    return manager.undo_tomato_task(tid, iid, owner)


@app.route('/api/tomato/finishTask', methods=['POST'])
@logged
def finish_tomato_task():
    tid = get_tid_from_request()
    iid = get_xid_from_request()
    owner = token.get_username(request)
    return manager.finish_tomato_task(tid, iid, owner)


@app.route('/api/tomato/finishTaskManually', methods=['POST'])
@logged
def finish_tomato_task_manually():
    tid = get_tid_from_request()
    iid = get_xid_from_request()
    owner = token.get_username(request)
    return manager.finish_tomato_task_manually(tid, iid, owner)


@app.route('/api/tomato/clearTask', methods=['POST'])
@logged
def clear_tomato_task():
    tid = get_tid_from_request()
    iid = get_xid_from_request()
    owner = token.get_username(request)
    return manager.clear_tomato_task(tid, iid, owner)


# ####################### API For Functions #######################

@app.route("/api/meta/isAdmin", methods=["GET"])
@logged
def is_admin():
    username = token.get_username(request)
    return config.is_admin_user(username)


@app.route("/api/log/tomato", methods=["GET"])
@logged(role='ROLE_ADMIN')
def back_up():
    with open(manager.tomato_manager.DATA_FILE, encoding='utf-8') as f:
        return "".join(f.readlines())


@app.route("/api/log/log", methods=["GET"])
@logged(role='ROLE_ADMIN')
def get_log():
    # 文本中可能包含中文字符, 因此需要指定合适的编码
    with open(Log_File, encoding='utf-8') as f:
        return "".join(f.readlines())


@app.route("/api/admin/gc", methods=["POST"])
@logged(role='ROLE_ADMIN')
def gc():
    """手动触发垃圾回收操作"""
    manager.garbage_collection()


@app.route("/api/admin/func", methods=["POST"])
@logged(role='ROLE_ADMIN')
def exec_function():
    f: Dict = request.get_json()
    command: str = f.get("cmd", "<undefined>")
    data: str = f.get("data", "")
    owner = token.get_username(request)
    parent = try_get_parent_from_request()
    manager.exec_function(command, data, parent, owner)


if __name__ == '__main__':
    app.run("localhost", 4231, threaded=True)
