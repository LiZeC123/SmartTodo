import yagmail
import requests

from app.services.config_manager import ConfigManager
from app.tools.logger import logger

config = ConfigManager()


def send_message(title, msg, email_address, qw_hook):
    try:
        send_message_by_mail(email_address, msg, title)
    except Exception as e:
        logger.exception(e)

    try:
        send_message_by_qw(msg, qw_hook)
    except Exception as e:
        logger.exception(e)


def send_message_by_qw(msg, qw_hook):
    if qw_hook:
        data = {"msgtype": "markdown", "markdown": {"content": msg}}
        requests.post(qw_hook, json=data)


def send_message_by_mail(email_address, msg, title):
    if email_address:
        sender, password = config.get_mail_info()
        yag = yagmail.SMTP(user=sender, password=password, host='smtp.qq.com', smtp_ssl=True)
        yag.send(to=email_address, subject=title, contents=msg)
