import threading
import time
from collections import defaultdict
from typing import Callable

import schedule

from app.tools.logger import logger


def make_task(name: str, task: Callable) -> Callable:
    def task_func():
        logger.info(f"定时任务管理器: 执行任务: {name}")
        try:
            task()
        except Exception as e:
            logger.exception(e)

    return task_func


class TaskManager(threading.Thread):

    def __init__(self) -> None:
        super().__init__()
        self.tasks = defaultdict(list)
        self.HALF_HOUR_SEC = 30 * 60

    @staticmethod
    def add_daily_task(name: str, task: Callable, hour: str):
        schedule.every().day.at(hour).do(make_task(name, task))

    @staticmethod
    def add_friday_task(name: str, task: Callable, hour: str):
        schedule.every().friday.at(hour).do(make_task(name, task))

    def start(self) -> None:
        self.daemon = True
        super().start()

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(60)
