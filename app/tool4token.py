import string
import random
from typing import List, Optional

from exception import UnauthorizedException

def generate_token_str():
    return ''.join(random.sample(string.ascii_letters + string.digits, 16))


class TokenManager:
    def __init__(self):
        self.data = {}

    def create_token(self, info: dict) -> str:
        token = generate_token_str()
        self.data[token] = info
        return token

    def remove_token(self, token: str) -> None:
        if token in self.data:
            del self.data[token]

    def valid_token(self, token: str, role: str) -> bool:
        info = self.query_info(token)
        if info is None:
            return False
        role_list: List[str] = info.get('role', [])
        return role in role_list
    
    def get_username_from(self, token: str) -> str:
        if token in self.data:
            return self.data[token].get('username')
        raise UnauthorizedException("Token is not valid.")   

    def query_info(self, token: str) -> Optional[dict]:
        return self.data.get(token)