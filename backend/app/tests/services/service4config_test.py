from app.services.config_manager import *


def test_base():
    manager = ConfigManager()
    assert manager.try_login("admin", "123456") == True
    assert manager.try_login("admin", "") == False

    assert manager.is_admin_user("admin") == True
    assert manager.is_admin_user("user") == False
    assert manager.is_admin_user("sxa") == False

    assert manager.get_users_msg_info() != []

    sender, password = manager.get_mail_info()
    assert sender is not None and password is not None
