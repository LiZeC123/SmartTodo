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

    def users(self):
        return self.config['USER_INFO']

    def mails(self):
        return self.config['MAIL_INFO']

    def version(self):
        return self.config['VERSION']
