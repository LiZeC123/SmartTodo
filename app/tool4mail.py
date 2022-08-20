import yagmail

from service4config import ConfigManager

config = ConfigManager()


def send_mail(title, msg, res):
    sender, password = config.get_mail_info()
    yag = yagmail.SMTP(user=sender, password=password, host='smtp.qq.com', smtp_ssl=True)
    return yag.send(to=res, subject=title, contents=msg)
