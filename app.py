import functools
import json
from typing import Dict

from flask import Flask, request, abort

from entity import Item
from server import Manager, TokenManager
from service4config import ConfigManager
from tool4log import logger
from tool4time import parse_deadline_str

app = Flask(__name__)

manager = Manager()
token = TokenManager()
config = ConfigManager()


def make_success(data=None) -> str:
    return json.dumps({"success": True, "data": data})


def make_fail(data=None) -> str:
    return json.dumps({"success": False, "data": data})


def logged(func=None, role='ROLE_USER'):
    if func is None:
        return functools.partial(logged, role=role)

    @functools.wraps(func)  # 设置函数名称，否则由于函数同名导致Flask绑定失败
    def wrapper(*args, **kw):
        if token.check_token(request, role):
            return make_success(func(*args, **kw))
        else:
            abort(401)

    return wrapper


@app.errorhandler(401)
def handle_401(e):
    return make_fail("未授权操作")


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
        return make_fail()


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
        item.deadline = parse_deadline_str(f["deadline"])

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


def get_xid_from_request() -> int:
    f: Dict = request.get_json()
    xid = int(f.get('id'))
    return xid


def try_get_parent_from_request() -> int:
    f: Dict = request.get_json()
    return int(f.get("parent", "0"))


# ####################### API For Functions #######################
# 使用一个单独的页面来展示这些文本内容, 由于文字量不大, 因此可以直接放入一个textarea中

@app.route("/admin/backup", methods=["GET"])
@logged(role='ROLE_ADMIN')
def back_up():
    pass

    # resp = make_response(send_file(manager.back_up()))
    # resp.headers["Content-type"] = "text/plain;charset=UTF-8"
    # return resp


@app.route("/admin/log.txt", methods=["GET"])
@logged(role='ROLE_ADMIN')
def update_log():
    pass
    # 将文件的内容取出来, 直接返回, 因为log文件长度有限, 因此问题不大
    # https://blog.csdn.net/weixin_33966095/article/details/94337270
    # resp = make_response(send_file("log/log.txt"))
    # resp.headers["Content-type"] = "text/plain;charset=UTF-8"
    # return resp


@app.route("/admin/op", methods=["POST"])
@logged(role='ROLE_ADMIN')
def do_operation():
    pass
    # cmd = request.form['cmd']
    # manager.exec_cmd(cmd.replace("set", ""))


# ####################### API For File #######################

@app.route("/api/file/getAll", methods=["POST"])
@logged
def file_get_all_items():
    return manager.files()


@app.route("/api/file/upload", methods=["POST"])
@logged
def file_do_upload():
    pass


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


if __name__ == '__main__':
    app.run("0.0.0.0", 4231, threaded=True)
