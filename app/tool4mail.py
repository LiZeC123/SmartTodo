import yagmail

from service4config import ConfigManager

config = ConfigManager()


def send_report(title, msg, res):
    sender, password = config.get_mail_info()
    yag = yagmail.SMTP(user=sender, password=password, host='smtp.qq.com', smtp_ssl=True)
    return yag.send(to=res, subject=title, contents=msg)


def send_daily_report(email, summary, dry_run=False):
    msg = f"<p>亲爱的{summary['user']}，以下是您的SmartTodo日报：</p>"
    msg += "<h4>总体情况统计</h4>"
    msg += f"<ul><li>今日完成番茄钟数量: {summary['today_stat']}个</li>"
    msg += f"<li>今日累计学习时间: {summary['total_stat']}分钟</li>"
    msg += "</ul>"

    if len(summary['undone_habit']) != 0:
        msg += "<hr/><h4>尚未打卡的记录</h4><ul>"
        for habit in summary['undone_habit']:
            msg += f"<li>{habit['name']}</li>"
        msg += "</ul>"

    if len(summary['undone_task']) != 0:
        msg += "<hr/><h4>尚未完成的代办事项</h4><ul>"
        for task in summary['undone_task']:
            msg += f"<li>{task}</li>"
        msg += "</ul>"

    if len(summary['done_task']) != 0:
        msg += "<hr/><h4>今日完成的代办事项</h4><ul>"
        for task in summary['done_task']:
            msg += f"<li>{task}</li>"
        msg += "</ul>"

    msg += "<hr/><h4>其他事项</h4>"
    msg += "<p>请在规定的时间内完成今日的工作与思考总结, 并整理为文字资料.</p>"

    if dry_run:
        print(msg)
    else:
        send_report(f"SmartTodo日报", msg, email)


def send_weekly_report():
    pass
