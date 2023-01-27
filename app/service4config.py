import json
from os.path import exists, join

from tool4log import logger


class ConfigManager:
    __CONFIG_FOLDER = "config"

    def __init__(self):
        config_file = join(ConfigManager.__CONFIG_FOLDER, "config.json")
        if not exists(config_file):
            config_file = join(ConfigManager.__CONFIG_FOLDER, "default.json")
            logger.warning("Load Default Config")

        with open(config_file) as f:
            self.config = json.load(f)

    def try_login(self, username: str, password: str) -> bool:
        users = self.config['USER_INFO']
        return username in users and users[username]['password'] == password

    def get_roles(self, username: str):
        users: dict = self.config['USER_INFO']
        if username in users:
            return users[username]['role']
        else:
            return []

    def is_admin_user(self, username: str):
        return "ROLE_ADMIN" in self.get_roles(username)

    def get_mail_info(self):
        info = self.config['MAIL_INFO']
        return info["SENDER"], info["PASSWORD"]

    def get_users_msg_info(self):
        ans = []
        for username, user_config in self.config["USER_INFO"].items():
            email = user_config.get("email")
            qw_hook = user_config.get("qw_hook")
            ans.append((username, email, qw_hook))
        return ans
