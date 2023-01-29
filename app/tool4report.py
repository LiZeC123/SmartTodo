from typing import List, Callable

from server4item import ItemManager
from tool4mail import send_message
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


def render_daily_report(summary: ReportSummary) -> str:
    msg = list()
    msg.append(f"亲爱的{summary.username}，以下是您的{summary.title}日报")
    msg.append("总体情况统计")
    msg.append("--------------------")
    msg.append(f"今日完成番茄钟数量: {summary.today_tomato_count}个")
    msg.append(f"今日累计学习时间: {summary.today_cost_time}分钟")
    msg.append("")

    render_list(msg, "尚未打卡的记录", summary.undone_habit, lambda habit: habit['name'])
    render_list(msg, "尚未完成的代办事项", summary.undone_task, lambda x: x)
    render_list(msg, "番茄钟消耗统计", summary.tomato_task, lambda task: f"{task[0]}(消耗{task[1]}个番茄钟)")
    render_list(msg, "今日完成的代办事项", summary.done_task, lambda x: x)

    msg.append("请在规定的时间内完成今日的工作与思考总结, 并整理为文字资料.")

    return "\n".join(msg)


def render_weekly_report(summary: ReportSummary) -> str:
    msg = [f"亲爱的{summary.username}，以下是您的{summary.title}周报"]
    render_list(msg, "本周番茄钟消耗统计", summary.tomato_task, lambda task: f"{task[0]}(消耗{task[1]}个番茄钟)")

    msg.append("请在规定的时间内完成今日的工作与思考总结, 并整理为文字资料.")

    return "\n".join(msg)


def render_list(msg: List[str], title: str, data: List, fn_get: Callable[[List], str]):
    if data and len(data) > 0:
        msg.append(title)
        msg.append("--------------------")
        for item in data:
            msg.append(f"- {fn_get(item)}")
        msg.append("")


class ReportManager:
    def __init__(self, item_manager: ItemManager, tomato_record_manager: TomatoRecordManager, send_message_func=None):
        self.item_manager = item_manager
        self.tomato_record_manager = tomato_record_manager

        if send_message_func is None:
            self.send_message = send_message
        else:
            self.send_message = send_message_func

    def get_daily_report(self, owner: str):
        summary = ReportSummary(owner, "实时")
        summary.set_tomato_task(self.tomato_record_manager.select_today_tomato(owner))
        summary.set_task(self.item_manager.select_undone_item(owner), None)
        return render_daily_report(summary)

    def get_summary(self, owner: str):
        return {
            "items": self.item_manager.select_summary(owner),
            "stats": self.tomato_record_manager.get_tomato_stat(owner),
            "habit": self.item_manager.select_habit(owner)
        }

    def send_daily_report(self, user):
        owner, email_address, qw_hook = user
        stat = self.tomato_record_manager.get_daily_stat(owner)
        summary = ReportSummary(owner, "SmartTodo")
        summary.set_tomato_stat(stat['count'], stat['minute'])
        summary.set_task(self.item_manager.select_undone_item(owner), self.item_manager.select_done_item(owner))
        summary.set_habit(self.item_manager.select_habit(owner))
        summary.set_tomato_task(self.tomato_record_manager.select_today_tomato(owner))

        message = render_daily_report(summary)
        self.send_message(summary.title, message, email_address, qw_hook)

    def send_weekly_report(self, user):
        owner, email_address, qw_hook = user
        summary = ReportSummary(owner, "SmartTodo")
        summary.set_tomato_task(self.tomato_record_manager.select_week_tomato(owner))

        message = render_weekly_report(summary)
        self.send_message(summary.title, message, email_address, qw_hook)
