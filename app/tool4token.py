import string
import random
from typing import Optional


def generate_token_str():
    return ''.join(random.sample(string.ascii_letters + string.digits, 16))


class TokenManager:
    def __init__(self):
        self.data = {}

    def create_token(self, info: dict) -> str:
        token = generate_token_str()
        self.data[token] = info
        return token

    def query_info(self, token: str) -> Optional[dict]:
        return self.data.get(token)

    def check_token(self, request, role) -> bool:
        token = request.headers.get('token')
        return token in self.data and role in self.data[token].get('role')

    def get_username(self, request) -> Optional[str]:
        token = request.headers.get('token')
        info = self.data.get(token, {})
        return info.get('username')

    def remove_token(self, token: str) -> None:
        if token in self.data:
            del self.data[token]
