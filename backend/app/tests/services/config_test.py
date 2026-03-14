from app.services.config_manager import *


def test_base():
    manager = ConfigManager()
    assert manager.try_login("admin", "123456") == True
    assert manager.try_login("admin", "") == False

    assert manager.is_admin_user("admin") == True
    assert manager.is_admin_user("user") == False
    assert manager.is_admin_user("sxa") == False

    assert manager.get_users_msg_info() != []

    base_url, api_key = manager.get_llm_info()
    assert base_url is not None and api_key is not None
