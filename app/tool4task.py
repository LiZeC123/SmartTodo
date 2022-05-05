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
        idx = 2 * hour + half
        self.tasks[idx].append(TimedTask(name=name, task=task, hour=hour, half=half))

    def start(self):
        now_time = now()
        t0 = timedelta(hours=now_time.hour, minutes=now_time.minute, seconds=now_time.second)
        t1 = timedelta(hours=now_time.hour + 1)
        dt = t1 - t0

        logger.info(f"定时任务管理器:现在是{now_time}. 休眠{dt.seconds}秒后调度下一个整点时刻任务")
        logger.info(f"当前已注册任务列表: {self}")
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

        idx = 2 * hour + half
        logger.info(f"定时任务管理器:当前时刻索引为:{idx} 任务列表为:{self.tasks[idx]}")
        for t in self.tasks[idx]:
            logger.info(f"定时任务管理器: 执行任务: {t.name}")
            try:
                t.task()
            except Exception as e:
                logger.exception(e)

        T = Timer(self.HALF_HOUR_SEC, self.__start0)
        T.daemon = True
        T.start()

    def __str__(self):
        ans = []
        for hour in range(24):
            for half in [False, True]:
                for task in self.tasks[2 * hour + half]:
                    ans.append(f"<{task.name}@{task.hour}:{'30' if task.half else '00'}>")
        return "".join(ans)
