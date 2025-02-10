from flask import Blueprint, request, jsonify, session

from app import config_manager
from app.tools.log import logger

login_bp = Blueprint('login', __name__)


@login_bp.post('/api/login')
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if config_manager.try_login(username, password):
        # 启用持久化存储, 默认情况保存31天
        session.permanent = True
        session["username"] = username
        session["role"] = config_manager.get_roles(username)
        return "True"
    else:
        real_ip = request.headers.get("X-Real-IP")
        logger.warning(f"已拒绝来自{real_ip}的请求, 此请求尝试以'{password}'为密码登录账号'{username}'")
        return "False"


@login_bp.post('/api/logout')
def logout():
    session.clear()
    return jsonify(True)
