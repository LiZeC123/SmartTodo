import threading
import time
from collections import defaultdict
from collections.abc import Callable

import schedule

from app.models.base import Database
from app.tools.log import logger


def make_task(name: str, db: Database, task: Callable) -> Callable:
    def task_func():
        logger.info(f"定时任务管理器: 执行任务: {name}")
        try:
            task()
            db.commit()
        except Exception as e:
            logger.exception(e)
            db.rollback()

    return task_func


class TaskManager(threading.Thread):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.tasks = defaultdict(list)
        self.HALF_HOUR_SEC = 30 * 60

    def add_daily_task(self, name: str, task: Callable, hour: str):
        schedule.every().day.at(hour).do(make_task(name, self.db, task))

    def add_friday_task(self, name: str, task: Callable, hour: str):
        schedule.every().friday.at(hour).do(make_task(name, self.db, task))

    def start(self) -> None:
        self.daemon = True
        super().start()

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(60)
