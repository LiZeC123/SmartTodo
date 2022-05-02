from collections import namedtuple, defaultdict
from datetime import timedelta
from threading import Timer

from tool4log import logger
from tool4time import now

TimedTask = namedtuple("TimedTask", ["name", "task", "hour", "half"])


class TaskManager:
    def __init__(self) -> None:
        self.tasks = defaultdict(list)
        self.HALF_HOUR_SEC = 30 * 60

    def add_task(self, name, task, hour: int, half=False):
        self.tasks[hour + half].append(TimedTask(name=name, task=task, hour=hour, half=half))

    def start(self):
        now_time = now()
        t0 = timedelta(hours=now_time.hour, minutes=now_time.minute, seconds=now_time.second)
        t1 = timedelta(hours=now_time.hour + 1)
        dt = t1 - t0

        logger.info(f"定时任务管理器:现在是{now_time}. 休眠{dt.seconds}秒后调度下一个整点时刻任务")
        # 等待到下一个整点时刻再开始执行任务
        T = Timer(dt.seconds, self.__start0)
        T.daemon = True
        T.start()

    def __start0(self):
        now_time = now()
        if now_time.minute < 15:
            hour = now_time.hour
            half = False
        elif now_time.minute < 45:
            hour = now_time.hour
            half = True
        else:
            hour = now_time.hour + 1
            half = False

        logger.info(f"now = {now_time}, hour = {hour}, half = {half}, tasks = {self.tasks[hour + half]}")
        for t in self.tasks[hour + half]:
            logger.info(f"定时任务管理器: 执行任务: {t.name}")
            t.task()

        T = Timer(self.HALF_HOUR_SEC, self.__start0)
        T.daemon = True
        T.start()
