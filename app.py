# -*- coding: UTF-8 -*-
import json
import os
from typing import Dict

from flask import Flask, render_template, request, session, make_response, send_file, redirect

from entity import Item
from server import Manager
from tool4log import logger
from tool4time import parse_deadline_str, this_year_str

app = Flask(__name__, static_url_path='/smart-todo/static')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = os.urandom(24)

manager = Manager()


def logined(func):
    def wrapper(*args, **kw):
        if 'username' in session:
            response = func(*args, **kw)
            if response is None:
                return "Success"
            else:
                return response
        else:
            return render_template('login.html')

    # 设置函数名称，否则由于函数同名导致Flask绑定失败
    wrapper.__name__ = func.__name__
    return wrapper


@app.route('/smart-todo/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if manager.try_login(username, password):
            session['username'] = username
            # session['password'] = password
            resp = make_response(render_template('index.html', name=username))
            resp.set_cookie('username', username)
            return redirect('/smart-todo/')
        else:
            real_ip = request.headers.get("X-Real-IP")
            logger.warn(f"已拒绝来自{real_ip}的请求, 此请求尝试以'{password}'为密码登录账号'{username}'")
            return redirect('/login')
    return render_template('login.html')


@app.route('/smart-todo/logout', methods=['GET', 'POST'])
@logined
def logout():
    if 'username' in session:
        session.clear()
        return render_template('login.html')
    # if request.method == 'POST' and session['username'] == request.form['username']:
    #     session.clear()
    #     return render_template('login.html')
    return False


@app.route('/smart-todo/', methods=['GET', 'POST'])
@logined
def index():
    if session['username'] == 'guest':
        return render_template("file.html", year=this_year_str(), version=manager.version())
    else:
        return render_template("index.html", year=this_year_str(), version=manager.version())


# ####################### API For File #######################

@app.route('/smart-todo/file')
@logined
def file():
    return render_template("file.html", thisYear=this_year_str(), version=manager.version())


@app.route('/smart-todo/file/list', methods=['POST'])
@logined
def file_list():
    return json.dumps(manager.files())


@app.route("/smart-todo/file/doUpload", methods=["POST"])
@logined
def do_upload():
    f = request.files['myFile']
    manager.save_file(f)


@app.route('/smart-todo/file/toRemote', methods=['POST'])
@logined
def to_remote():
    raise NotImplementedError
    # iid = request.form["id"]
    # fileManager.file2remote(iid)


@app.route("/smart-todo/file/<filename>", methods=['GET'])
@logined
def get_file(filename):
    resp = make_response(send_file(f"filebase/{filename}"))
    return resp


# ####################### API For Note #######################

@app.route('/smart-todo/note/<nid>', methods=['GET'])
@logined
def note(nid):
    item_info = manager.item(iid=nid)
    base_info = dict(nid=nid, note=manager.note(nid), year=this_year_str(), version=manager.version())
    item_info.update(base_info)
    return render_template("note.html", **item_info)


@app.route('/smart-todo/note/update', methods=['POST'])
@logined
def note_update():
    nid = request.form["nid"]
    text = request.form["text"]
    manager.update("note", xid=nid, content=text)


# ####################### API For Item #######################

@app.route('/smart-todo/items/todo', methods=['POST'])
@logined
def todo_item():
    f = request.form
    nid = f.get("nid", default=None)
    return json.dumps(manager.todo(nid))


@app.route("/smart-todo/item/delete", methods=["POST"])
@logined
def remove_item():
    iid = check_id(request.form["id"])
    manager.remove(iid)


@app.route("/smart-todo/item/add", methods=["POST"])
@logined
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


@app.route("/smart-todo/item/update", methods=["POST"])
@logined
def update_item():
    iid = check_id(request.form["id"])
    manager.update(item_type="item", xid=iid)


@app.route("/smart-todo/item/old", methods=["POST"])
@logined
def update_item_generation():
    iid = check_id(request.form["id"])
    manager.to_old(iid)


@app.route("/smart-todo/backup", methods=["GET"])
@logined
def back_up():
    resp = make_response(send_file(manager.back_up()))
    resp.headers["Content-type"] = "text/plain;charset=UTF-8"
    return resp


@app.route("/smart-todo/log.txt", methods=["GET"])
@logined
def update_log():
    # https://blog.csdn.net/weixin_33966095/article/details/94337270
    resp = make_response(send_file("log/log.txt"))
    resp.headers["Content-type"] = "text/plain;charset=UTF-8"
    return resp


@app.route("/smart-todo/op", methods=["POST"])
@logined
def do_operation():
    cmd = request.form['cmd']
    manager.exec_cmd(cmd.replace("set", ""))


def check_id(xid: str) -> int:
    return int(xid)


if __name__ == '__main__':
    app.run("0.0.0.0", 4231, threaded=True)
