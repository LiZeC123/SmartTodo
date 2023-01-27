import yagmail
import requests
import json

from service4config import ConfigManager

config = ConfigManager()


def send_message(title, msg, email_address, qw_hook):
    if email_address:
        sender, password = config.get_mail_info()
        yag = yagmail.SMTP(user=sender, password=password, host='smtp.qq.com', smtp_ssl=True)
        yag.send(to=email_address, subject=title, contents=msg)
    
    if qw_hook:
        data =  {"msgtype" : "markdown", "markdown": {"content": msg}}
        requests.post(qw_hook, json=data)
