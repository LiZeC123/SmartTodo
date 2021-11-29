import functools
import json
from typing import Dict

from flask import Flask, request, abort

from entity import Item
from server import Manager, TokenManager
from service4config import ConfigManager
from tool4log import logger, Log_File
from tool4time import parse_deadline_timestamp

app = Flask(__name__)

manager = Manager()
token = TokenManager()
config = ConfigManager()


def make_success(data=None) -> str:
    return json.dumps({"success": True, "data": data})


def logged(func=None, role='ROLE_USER', wrap=True):
    if func is None:
        return functools.partial(logged, role=role)

    @functools.wraps(func)  # 设置函数名称，否则由于函数同名导致Flask绑定失败
    def wrapper(*args, **kw):
        if not wrap:
            return func(*args, **kw)
        elif token.check_token(request, role):
            return make_success(func(*args, **kw))
        else:
            abort(401)

    return wrapper


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if config.try_login(username, password):
        return make_success(token.create_token({"username": username, "role": config.get_roles(username)}))
    else:
        real_ip = request.headers.get("X-Real-IP")
        logger.warning(f"已拒绝来自{real_ip}的请求, 此请求尝试以'{password}'为密码登录账号'{username}'")
        return abort(401)


@app.route('/api/logout', methods=['POST'])
@logged
def logout():
    token.remove_token(request.form.get('token'))


# ####################### API For Item #######################
@app.route('/api/item/getAll', methods=['POST'])
@logged
def get_all_item():
    owner: str = token.get_username(request)
    return manager.all_items(owner, parent=0)


@app.route('/api/item/getTodo', methods=['POST'])
@logged
def get_todo_item():
    owner: str = token.get_username(request)
    return manager.todo_items(owner, parent=0)


@app.route('/api/item/done', methods=['POST'])
@logged
def done_item() -> bool:
    xid = get_xid_from_request()
    owner = token.get_username(request)
    parent = try_get_parent_from_request()
    return manager.done(xid=xid, owner=owner, parent=parent)


@app.route('/api/item/undone', methods=['POST'])
@logged
def undone_item() -> bool:
    xid = get_xid_from_request()
    owner = token.get_username(request)
    parent = try_get_parent_from_request()
    return manager.undo(xid=xid, owner=owner, parent=parent)


@app.route('/api/item/toOld', methods=['POST'])
@logged
def to_old():
    xid = get_xid_from_request()
    return manager.to_old(xid=xid, owner=token.get_username(request))


@app.route("/api/item/create", methods=["POST"])
@logged
def create_item():
    f: Dict = request.get_json()
    item: Item = Item(0, f['name'], f['itemType'], token.get_username(request))

    if "deadline" in f:
        item.deadline = parse_deadline_timestamp(f["deadline"])

    if "work" in f:
        item.work = bool(f["work"])

    if "repeatable" in f:
        item.repeatable = bool(f["repeatable"])

    if "specific" in f:
        item.specific = int(f["specific"])

    if "parent" in f:
        item.parent = int(f["parent"])

    manager.create(item)


@app.route("/api/item/remove", methods=["POST"])
@logged
def remove_item():
    iid = get_xid_from_request()
    owner = token.get_username(request)
    manager.remove(iid, owner)


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


def try_get_parent_from_request() -> int:
    f: Dict = request.get_json()
    return int(f.get("parent", "0"))


# ####################### API For File #######################

@app.route("/api/file/getAll", methods=["POST"])
@logged
def file_get_all_items():
    return manager.files()


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
    return manager.todo_items(owner, parent=nid)


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
    return manager.get_tomato_task()


# ####################### API For Functions #######################

@app.route("/api/meta/isAdmin", methods=["GET"])
@logged
def is_admin():
    username = token.get_username(request)
    return config.get_roles(username)


@app.route("/api/log/data", methods=["GET"])
@logged(role='ROLE_ADMIN')
def back_up():
    with open(manager.database.DATA_FILE) as f:
        # data数据是不换行存储的JSON数据, 因此只需要取值第一行
        return f.readline()


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


@app.route("/admin/op", methods=["POST"])
@logged(role='ROLE_ADMIN')
def do_operation():
    pass


if __name__ == '__main__':
    app.run("0.0.0.0", 4231, threaded=True)
