import json
from os.path import exists, join

from tool4log import logger


class ConfigManager:
    __CONFIG_FOLDER = "config"

    def __init__(self):
        user_config = join(ConfigManager.__CONFIG_FOLDER, "config.json")
        default_config = join(ConfigManager.__CONFIG_FOLDER, "default.json")
        if exists(user_config):
            self.config = json.load(open(user_config))
        else:
            logger.warn("Load Default Config")
            self.config = json.load(open(default_config))

    def try_login(self, username: str, password: str) -> bool:
        users = self.config['USER_INFO']
        return username in users and users[username]['password'] == password

    def get_roles(self, username: str):
        users: dict = self.config['USER_INFO']
        if username in users:
            return users[username]['role']
        else:
            return None

    def is_admin_user(self, username: str):
        return "ROLE_ADMIN" in self.get_roles(username)
