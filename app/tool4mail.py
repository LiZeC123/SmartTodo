import yagmail

from service4config import ConfigManager

config = ConfigManager()


def send_report(title, msg, res):
    sender, password = config.get_mail_info()
    yag = yagmail.SMTP(user=sender, password=password, host='smtp.qq.com', smtp_ssl=True)
    return yag.send(to=res, subject=title, contents=msg)


def send_daily_report():
    for user, email in config.get_mail_users():
        msg = """<h2>统计信息</h2>
    <p>累计完成番茄钟数量: {{ stats.total.count }} 累计学习时间: {{ stats.total.hour }}小时 日均学习时间: {{ stats.total.average }}分钟</p>
    <p>今日完成番茄钟数量: {{ stats.today.count }} 今日累计学习时间: {{ stats.today.minute }}分钟</p>"""
        send_report(f"用户{user}的Todo日报", msg, email)


def send_weekly_report():
    pass


if __name__ == '__main__':
    send_daily_report()
