from flask import Blueprint, request, jsonify

from app import config_manager, token_manager
from app.tools.logger import logger
from app.views.authority import authority_check


login_bp = Blueprint('login', __name__)


@login_bp.post('/api/login')
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



@login_bp.post('/api/logout')
@authority_check()
def logout():
    token = request.form.get('token')
    if token is None:
        return jsonify(False)
    token_manager.remove_token(token)
    return jsonify(True)