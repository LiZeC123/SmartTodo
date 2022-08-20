from server4item import ItemManager
from tool4mail import send_mail
from tool4time import now
from tool4tomato import TomatoRecordManager


class ReportSummary:
    def __init__(self, username, title):
        self.username = username
        self.title = title
        self.today_tomato_count = 0
        self.today_cost_time = 0
        self.undone_habit = []
        self.undone_task = []
        self.done_task = []
        self.tomato_task = []

    def set_tomato_stat(self, today_tomato_count: int, today_cost_time: int):
        self.today_tomato_count = today_tomato_count
        self.today_cost_time = today_cost_time

    def set_habit(self, undone_habit):
        self.undone_habit = undone_habit

    def set_task(self, undone_task, done_task):
        self.undone_task = undone_task
        self.done_task = done_task

    def set_tomato_task(self, tomato_task):
        self.tomato_task = tomato_task


def render_daily_mail_message(summary: ReportSummary) -> str:
    msg = f"<p>亲爱的{summary.username}，以下是您的{summary.title}：</p>"
    msg += "<h4>总体情况统计</h4>"
    msg += f"<ul><li>今日完成番茄钟数量: {summary.today_tomato_count}个</li>"
    msg += f"<li>今日累计学习时间: {summary.today_cost_time}分钟</li>"
    msg += "</ul>"

    if len(summary.undone_habit) != 0:
        msg += "<hr/><h4>尚未打卡的记录</h4><ul>"
        for habit in summary.undone_habit:
            msg += f"<li>{habit['name']}</li>"
        msg += "</ul>"

    if len(summary.undone_task) != 0:
        msg += "<hr/><h4>尚未完成的代办事项</h4><ul>"
        for task in summary.undone_task:
            msg += f"<li>{task}</li>"
        msg += "</ul>"

    if len(summary.done_task) != 0:
        msg += "<hr/><h4>今日完成的代办事项</h4><ul>"
        for task in summary.done_task:
            msg += f"<li>{task}</li>"
        msg += "</ul>"

    if len(summary.tomato_task) != 0:
        msg += "<hr/><h4>番茄钟消耗统计</h4><ul>"
        for task in summary.tomato_task:
            msg += f"<li>{task[0]}(消耗{task[1]}个番茄钟)</li>"
        msg += "</ul>"

    msg += "<hr/><h4>其他事项</h4>"
    msg += "<p>请在规定的时间内完成今日的工作与思考总结, 并整理为文字资料.</p>"

    return msg


def render_weekly_mail_report(summary: ReportSummary) -> str:
    msg = f"<p>亲爱的{summary.username}，以下是您的{summary.title}：</p>"

    if len(summary.tomato_task) != 0:
        msg += "<hr/><h4>本周番茄钟消耗统计</h4><ul>"
        for task in summary.tomato_task:
            msg += f"<li>{task[0]}(消耗{task[1]}个番茄钟)</li>"
        msg += "</ul>"

    msg += "<hr/><h4>其他事项</h4>"
    msg += "<p>请在规定的时间内完成本周的工作与思考总结, 并整理为文字资料.</p>"

    return msg


def render_daily_report(summary: ReportSummary) -> str:
    msg = f"{now().strftime('%Y/%m/%d')} 日报\n"
    msg += "------------------\n"
    msg += "\n"
    msg += "### 今日主要工作\n"
    for item in summary.tomato_task:
        msg += f"- {item[0]}\n"

    msg += "\n"
    msg += "### 明日规划\n"
    for item in summary.undone_task:
        msg += f"- {item}\n"
    msg += "\n"

    return msg


class ReportManager:
    def __init__(self, item_manager: ItemManager, tomato_record_manager: TomatoRecordManager, send_mail_func=None):
        self.item_manager = item_manager
        self.tomato_record_manager = tomato_record_manager

        if send_mail_func is None:
            self.send_mail = send_mail
        else:
            self.send_mail = send_mail_func

    def get_daily_report(self, owner: str):
        summary = ReportSummary(owner, "")
        summary.set_tomato_task(self.tomato_record_manager.select_today_tomato(owner))
        summary.set_task(self.item_manager.select_undone_item(owner), None)
        return render_daily_report(summary)

    def get_summary(self, owner: str):
        return {
            "items": self.item_manager.select_summary(owner),
            "stats": self.tomato_record_manager.get_tomato_stat(owner),
            "habit": self.item_manager.select_habit(owner)
        }

    def send_daily_report(self, owner: str, email_address: str):
        stat = self.tomato_record_manager.get_daily_stat(owner)
        summary = ReportSummary(owner, "SmartTodo日报")
        summary.set_tomato_stat(stat['count'], stat['minute'])
        summary.set_task(self.item_manager.select_undone_item(owner), self.item_manager.select_done_item(owner))
        summary.set_habit(self.item_manager.select_habit(owner))
        summary.set_tomato_task(self.tomato_record_manager.select_today_tomato(owner))

        message = render_daily_mail_message(summary)
        self.send_mail(summary.title, message, email_address)

    def send_weekly_report(self, owner: str, email_address: str):
        summary = ReportSummary(owner, "SmartTodo周报")
        summary.set_tomato_task(self.tomato_record_manager.select_week_tomato(owner))

        message = render_weekly_mail_report(summary)
        self.send_mail(summary.title, message, email_address)
