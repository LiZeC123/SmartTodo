import functools

from typing import Any
from flask import jsonify, request, abort

from app.services.token_manager import TokenManager
from app.tools.exception import UnauthorizedException
from app.tools.logger import logger

token_manager = TokenManager()

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