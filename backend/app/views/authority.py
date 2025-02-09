import functools
import logging

from typing import Any
from flask import jsonify, request, abort, session

from app.tools.exception import UnauthorizedException
from app.tools.log import logger


class authority_check:
    def __init__(self, role='ROLE_USER') -> None:
        self.role = role

    def __call__(self, func) -> Any:
        @functools.wraps(func)
        def wrapped_function(*args, **kwargs):
            owner = session.get("username")
            role_list =  session.get("role")
            if owner is None:
                logging.warning(f"当前用户未登录, 无法请求 {func.__name__} 接口")
                abort(401)
            if self.role not in role_list:
                logger.warning(f"用户 {owner} 缺少 {self.role} 权限")
                abort(401)

            try:
                return jsonify(func(*args, **kwargs, owner=owner))
            except UnauthorizedException as e:
                logger.warning(e)
                abort(401)

        return wrapped_function
