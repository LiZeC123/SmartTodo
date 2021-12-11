from datetime import timedelta
from threading import Timer

from tool4log import logger
from tool4time import now


class TaskManager:
    def __init__(self) -> None:
        self.tasks = [[] for _ in range(24)]
        self.ONE_HOUR = 60 * 60

    def add_task(self, task, hour: int):
        self.tasks[hour].append(task)

    def start(self):
        now_time = now()
        t0 = timedelta(hours=now_time.hour, minutes=now_time.minute, seconds=now_time.second)
        t1 = timedelta(hours=now_time.hour + 1)
        dt = t1 - t0

        logger.info(f"TimeTask: Now is {now_time}. Sleep {dt.seconds} seconds to the hour")
        # 等待到下一个整点时刻再开始执行任务
        Timer(dt.seconds, self.__start0).start()

    def __start0(self):
        now_hour = now().hour
        logger.info(f"TimeTask: Do Task For Hour {now_hour}")

        for task in self.tasks[now_hour]:
            task()

        Timer(self.ONE_HOUR, self.__start0).start()
