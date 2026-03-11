import requests

from app.services.config_manager import ConfigManager
from app.tools.log import logger

config = ConfigManager()


def send_message(title, msg, email_address, qw_hook):

    try:
        send_message_by_qw(msg, qw_hook)
    except Exception as e:
        logger.exception(e)


def send_message_by_qw(msg, qw_hook):
    if qw_hook:
        data = {"msgtype": "markdown", "markdown": {"content": msg}}
        requests.post(qw_hook, json=data)


