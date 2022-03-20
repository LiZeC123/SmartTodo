import yagmail

from service4config import ConfigManager

config = ConfigManager()


def send_report(title, msg, res):
    sender, password = config.get_mail_info()
    yag = yagmail.SMTP(user=sender, password=password, host='smtp.qq.com', smtp_ssl=True)
    return yag.send(to=res, subject=title, contents=msg)


def send_daily_report(user, email, summary):
    today_stats = summary['stats']['today']
    habits = summary['habit']
    msg = f"<p>亲爱的{user}，以下是您的SmartTodo日报：</p>" + \
          f"<p>今日完成番茄钟数量: {today_stats['count']} 今日累计学习时间: {today_stats['minute']}分钟</p>" + \
          f"<hr/>" + \
          f"<h4>打卡完成情况</h4>"

    for habit in habits:
        if habit['expected_tomato'] == habit['used_tomato']:
            msg += f"<p>(已完成){habit['name']}</p>"
        else:
            msg += f"<p>(尚未打卡){habit['name']}</p>"

    send_report(f"SmartTodo日报", msg, email)


def send_weekly_report():
    pass
