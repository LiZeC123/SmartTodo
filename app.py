# -*- coding: UTF-8 -*-
import functools
import json
import os
from typing import Dict

from flask import Flask, render_template, request, session, make_response, send_file, redirect, abort

from entity import Item
from server import Manager
from tool4log import logger
from tool4time import parse_deadline_str, this_year_str

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = os.urandom(24)

manager = Manager()


def logged(func=None, role='ROLE_USER'):
    if func is None:
        return functools.partial(logged, role=role)

    @functools.wraps(func)  # 设置函数名称，否则由于函数同名导致Flask绑定失败
    def wrapper(*args, **kw):
        if 'username' in session:
            if role in session['role']:
                response = func(*args, **kw)
                return response if response is not None else "Success"
            else:
                # 用户已经登录, 但是没有权限, 所以应该返回401 Unauthorized
                return render_template("401.html"), 401
        else:
            return redirect('/login')

    return wrapper


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if manager.try_login(username, password):
            session['username'] = username
            session['role'] = manager.get_roles(username)
            return redirect('/')
        else:
            real_ip = request.headers.get("X-Real-IP")
            logger.warning(f"已拒绝来自{real_ip}的请求, 此请求尝试以'{password}'为密码登录账号'{username}'")
            return redirect('/login')
    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
@logged
def logout():
    if 'username' in session:
        session.clear()
    return render_template('login.html')


@app.route('/', methods=['GET', 'POST'])
@logged
def index():
    data = {"year": this_year_str(), "version": manager.version(), "username": session['username'],
            'role': session['role']}

    return render_template('index.html', **data)


# ####################### API For File #######################

@app.route('/file')
@logged
def file():
    return render_template("file.html", thisYear=this_year_str(), version=manager.version())


@app.route('/file/list', methods=['POST'])
@logged
def file_list():
    return json.dumps(manager.files())


@app.route("/file/doUpload", methods=["POST"])
@logged
def do_upload():
    f = request.files['myFile']
    manager.save_file(f)


@app.route('/file/toRemote', methods=['POST'])
@logged(role='ROLE_ADMIN')
def to_remote():
    raise NotImplementedError
    # iid = request.form["id"]
    # fileManager.file2remote(iid)


@app.route("/file/<filename>", methods=['GET'])
@logged
def get_file(filename):
    resp = make_response(send_file(f"filebase/{filename}"))
    return resp


# ####################### API For Note #######################

@app.route('/note/<nid>', methods=['GET'])
@logged
def note(nid):
    item_info = manager.item(iid=nid)
    base_info = dict(nid=nid, note=manager.note(nid), year=this_year_str(), version=manager.version())
    item_info.update(base_info)
    return render_template("note.html", **item_info)


@app.route('/note/update', methods=['POST'])
@logged
def note_update():
    nid = request.form["nid"]
    text = request.form["text"]
    manager.update("note", xid=nid, content=text)


# ####################### API For Item #######################

@app.route('/items/todo', methods=['POST'])
@logged
def todo_item():
    f = request.form
    nid = f.get("nid", default=None)
    return json.dumps(manager.todo(nid))


@app.route("/item/delete", methods=["POST"])
@logged
def remove_item():
    iid = check_id(request.form["id"])
    manager.remove(iid)


@app.route("/item/add", methods=["POST"])
@logged
def add_item():
    f: Dict = request.form
    item: Item = Item(0, f['name'], f['itemType'], None)
    item.deadline = parse_deadline_str(f["deadline"]) if "deadline" in f else None

    item.work = False
    if "work" in f:
        item.work = (str(f["work"]).lower() == "true")

    item.repeatable = False
    if "repeatable" in f:
        item.repeatable = (str(f["repeatable"]).lower() == "true")

    item.specific = 0
    if "specific" in f:
        item.specific = int(f["specific"])

    item.parent = None
    if "parent" in f:
        item.parent = int(f["parent"])

    manager.create(item)


@app.route("/item/update", methods=["POST"])
@logged
def update_item():
    iid = check_id(request.form["id"])
    manager.update(item_type="item", xid=iid)


@app.route("/item/old", methods=["POST"])
@logged
def update_item_generation():
    iid = check_id(request.form["id"])
    manager.to_old(iid)


@app.route("/backup", methods=["GET"])
@logged(role='ROLE_ADMIN')
def back_up():
    resp = make_response(send_file(manager.back_up()))
    resp.headers["Content-type"] = "text/plain;charset=UTF-8"
    return resp


@app.route("/log.txt", methods=["GET"])
@logged(role='ROLE_ADMIN')
def update_log():
    # https://blog.csdn.net/weixin_33966095/article/details/94337270
    resp = make_response(send_file("log/log.txt"))
    resp.headers["Content-type"] = "text/plain;charset=UTF-8"
    return resp


@app.route("/op", methods=["POST"])
@logged(role='ROLE_ADMIN')
def do_operation():
    cmd = request.form['cmd']
    manager.exec_cmd(cmd.replace("set", ""))


def check_id(xid: str) -> int:
    return int(xid)


if __name__ == '__main__':
    app.run("0.0.0.0", 4231, threaded=True)
