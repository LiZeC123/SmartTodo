from app.services.config_manager import ConfigManager


def test_base():
    manager = ConfigManager()
    assert manager.try_login("admin", "123456")
    assert not manager.try_login("admin", "")

    assert manager.is_admin_user("admin")
    assert not manager.is_admin_user("user")
    assert not manager.is_admin_user("sxa")

    assert manager.get_users_msg_info() != []

    base_url, api_key, model_name = manager.get_llm_info()
    assert base_url is not None and api_key is not None and model_name is not None

    users = manager.get_all_users()
    assert len(list(users)) != 0
