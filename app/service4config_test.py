from service4config import *


def test_base():
    manager = ConfigManager()
    assert manager.try_login("admin", "123456") == True
    assert manager.try_login("admin", "") == False

    assert manager.is_admin_user("admin") == True
    assert manager.is_admin_user("user") == False
    assert manager.is_admin_user("sxa") == False

    assert manager.get_mail_users() != []
