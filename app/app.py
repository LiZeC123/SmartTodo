import functools
import json
from typing import Dict, Optional

from flask import Flask, request, abort
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Item, Base
from exception import UnauthorizedException
from server import Manager
from service4config import ConfigManager
from tool4log import logger, Log_File
from tool4stat import load_data
from tool4time import parse_deadline_timestamp
from tool4token import TokenManager

app = Flask(__name__)

engine = create_engine('sqlite:///data/database/data.db', echo=True, future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
# 初始化所有的表
Base.metadata.create_all(engine)

manager = Manager(db_session)
token_manager = TokenManager()
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

        token = request.headers.get('token')
        info = token_manager.query_info(token)
        if info is None or role not in info.get('role'):
            abort(401)

        try:
            return make_result(func(*args, **kw))
        except UnauthorizedException:
            abort(401)

    return wrapper


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if config.try_login(username, password):
        return token_manager.create_token({"username": username, "role": config.get_roles(username)})
    else:
        real_ip = request.headers.get("X-Real-IP")
        logger.warning(f"已拒绝来自{real_ip}的请求, 此请求尝试以'{password}'为密码登录账号'{username}'")
        return ""


@app.route('/api/logout', methods=['POST'])
@logged
def logout():
    token_manager.remove_token(request.form.get('token'))


# ####################### API For Item #######################
@app.route("/api/item/create", methods=["POST"])
@logged
def create_item():
    f: Dict = request.get_json()
    item = Item(name=f['name'], item_type=f['itemType'], owner=get_owner_from_request())

    if "deadline" in f:
        item.deadline = parse_deadline_timestamp(f["deadline"])

    if "repeatable" in f:
        item.repeatable = bool(f["repeatable"])

    if "specific" in f:
        item.specific = int(f["specific"])

    if "parent" in f:
        item.parent = int(f["parent"])

    if "habit" in f:
        item.habit = True

    manager.create(item)


@app.route('/api/item/getAll', methods=['POST'])
@logged
def get_all_item():
    owner: str = get_owner_from_request()
    parent = try_get_parent_from_request()
    return manager.all_items(owner, parent=parent)


@app.route('/api/item/getActivate', methods=['POST'])
@logged
def get_activate_item():
    # Deprecated
    owner: str = get_owner_from_request()
    parent = try_get_parent_from_request()
    return manager.activate_items(owner, parent=parent)


@app.route('/api/item/getSummary', methods=['POST'])
@logged
def get_summary():
    owner: str = get_owner_from_request()
    return manager.get_summary(owner)


@app.route('/api/item/back', methods=['POST'])
@logged
def back_item() -> bool:
    xid = get_xid_from_request()
    owner = get_owner_from_request()
    parent = try_get_parent_from_request()
    return manager.undo(xid=xid, owner=owner, parent=parent)


@app.route("/api/item/remove", methods=["POST"])
@logged
def remove_item():
    iid = get_xid_from_request()
    owner = get_owner_from_request()
    manager.remove(iid, owner)


@app.route('/api/item/increaseExpectedTomatoTime', methods=['POST'])
@logged
def increase_expected_tomato() -> bool:
    xid = get_xid_from_request()
    owner = get_owner_from_request()
    return manager.increase_expected_tomato(xid=xid, owner=owner)


@app.route('/api/item/increaseUsedTomatoTime', methods=['POST'])
@logged
def increase_used_tomato() -> bool:
    xid = get_xid_from_request()
    owner = get_owner_from_request()
    return manager.increase_used_tomato(xid=xid, owner=owner)


@app.route('/api/item/toTodayTask', methods=['POST'])
@logged
def to_today_task() -> bool:
    xid = get_xid_from_request()
    owner = get_owner_from_request()
    return manager.to_today_task(xid=xid, owner=owner)


@app.route("/api/item/getTitle", methods=["POST"])
@logged
def get_title():
    iid = get_xid_from_request()
    owner = get_owner_from_request()
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


def get_owner_from_request() -> str:
    token = request.headers.get('token')
    info = token_manager.data.get(token, {})
    return info.get('username')


def try_get_parent_from_request() -> Optional[int]:
    f: Dict = request.get_json()
    if f is not None and "parent" in f:
        return int(f.get("parent"))
    else:
        return None


# ####################### API For File #######################

@app.route("/api/file/upload", methods=["POST"])
@logged
def file_do_upload():
    file = request.files['myFile']
    parent = int(request.form['parent'])

    # 0表示不属于任何类型，转换为None类型进行存储
    if parent == 0:
        parent = None

    owner = get_owner_from_request()
    return manager.create_upload_file(file, parent, owner)


# ####################### API For Note #######################

@app.route('/api/note/content', methods=['POST'])
@logged
def note_content():
    nid = get_xid_from_request()
    return manager.get_note(nid, owner=get_owner_from_request())


@app.route('/api/note/update', methods=['POST'])
@logged
def note_update():
    nid = get_xid_from_request()
    content = request.get_json().get("content")
    manager.update_note(nid, owner=get_owner_from_request(), content=content)


@app.route('/api/note/getAll', methods=['POST'])
@logged
def note_get_all_item():
    owner: str = get_owner_from_request()
    nid = get_xid_from_request()
    return manager.all_items(owner, parent=nid)


@app.route('/api/note/getTodo', methods=['POST'])
@logged
def note_get_todo_item():
    owner: str = get_owner_from_request()
    nid = get_xid_from_request()
    return manager.activate_items(owner, parent=nid)


# ####################### API For Tomato #########################
@app.route('/api/tomato/setTask', methods=['POST'])
@logged
def set_tomato_task():
    iid = get_xid_from_request()
    owner = get_owner_from_request()
    return manager.set_tomato_task(iid, owner)


@app.route('/api/tomato/getTask', methods=['GET'])
@logged
def get_tomato_task():
    owner = get_owner_from_request()
    return manager.get_tomato_task(owner)


@app.route('/api/tomato/undoTask', methods=['POST'])
@logged
def undo_tomato_task():
    tid = get_tid_from_request()
    iid = get_xid_from_request()
    owner = get_owner_from_request()
    return manager.undo_tomato_task(tid, iid, owner)


@app.route('/api/tomato/finishTask', methods=['POST'])
@logged
def finish_tomato_task():
    tid = get_tid_from_request()
    iid = get_xid_from_request()
    owner = get_owner_from_request()
    return manager.finish_tomato_task(tid, iid, owner)


@app.route('/api/tomato/finishTaskManually', methods=['POST'])
@logged
def finish_tomato_task_manually():
    tid = get_tid_from_request()
    iid = get_xid_from_request()
    owner = get_owner_from_request()
    return manager.finish_tomato_task_manually(tid, iid, owner)


@app.route('/api/tomato/clearTask', methods=['POST'])
@logged
def clear_tomato_task():
    tid = get_tid_from_request()
    iid = get_xid_from_request()
    owner = get_owner_from_request()
    return manager.clear_tomato_task(tid, iid, owner)


# ####################### API For Functions #######################

@app.route("/api/meta/isAdmin", methods=["GET"])
@logged
def is_admin():
    username = get_owner_from_request()
    return config.is_admin_user(username)


@app.route("/api/log/tomato", methods=["GET"])
@logged(role='ROLE_ADMIN')
def get_tomato_log():
    owner = get_owner_from_request()
    return "\n".join(map(str, load_data(db_session, owner=owner, limit=20)))


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
    owner = get_owner_from_request()
    parent = try_get_parent_from_request()
    manager.exec_function(command, data, parent, owner)


@app.teardown_appcontext
def remove_session(exception=None):
    db_session.remove()
    if exception:
        logger.exception(f"清理Session: 此Session中存在异常 {exception}")


if __name__ == '__main__':
    app.run("localhost", 4231, threaded=True)
