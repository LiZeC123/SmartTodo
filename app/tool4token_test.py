import pytest
from tool4token import *

info = {"username": "user", "role": "admin"}
fake_token = "fake_token_abcdedf"

def test_base():
    token_manager = TokenManager()
    token = token_manager.create_token(info)

    assert token_manager.query_info(token) == info

    token_manager.remove_token(token)
    assert token_manager.query_info(token) is None

def test_role():
    token_manager = TokenManager()
    token = token_manager.create_token(info)  

    assert token_manager.valid_token(token, 'admin') is True
    assert token_manager.valid_token(token, 'user') is False
    assert token_manager.valid_token(fake_token, 'admin') is False

def test_get_username():
    token_manager = TokenManager()
    token = token_manager.create_token(info) 

    assert token_manager.get_username_from(token) == 'user'
    with pytest.raises(UnauthorizedException):
         token_manager.get_username_from(fake_token)
