from tool4token import *


def test_base():
    token = TokenManager()
    info = {"username": "user", "role": "admin"}
    t = token.create_token(info)

    assert token.query_info(t) == info

    token.remove_token(t)
    assert token.query_info(t) is None
