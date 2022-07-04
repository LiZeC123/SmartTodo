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

    def remove_token(self, token: str) -> None:
        if token in self.data:
            del self.data[token]
