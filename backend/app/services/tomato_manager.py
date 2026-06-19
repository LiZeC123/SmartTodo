from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from itertools import groupby

import sqlalchemy as sal

from app.models.item import Item, ItemType, TomatoType
from app.models.tomato import TomatoStatus, TomatoTaskRecord
from app.services.item_manager import ItemManager
from app.tools.log import logger
from app.tools.time import get_hour_str_from, last_month, now, parse_time, today_begin

# 定义番茄钟完成事件, 入参为当前完成的番茄钟对象和完成类型
# 其中完成类型可选值: auto 自动完成;
OnTomatoFinished = Callable[[TomatoStatus, str], None]

WorkTimeSecond = 25 * 60
RestTimeSecond = 5 * 60


class TomatoManager:
    def __init__(self, item_manager: ItemManager):
        self.db = item_manager.db
        self.item_manager = item_manager
        self.event_manager = item_manager.event_manager
        self.tomato_finished_event: list[OnTomatoFinished] = []

    def on_tomato_finished(self, callback: OnTomatoFinished):
        self.tomato_finished_event.append(callback)

    def start_task(self, xid: int, owner: str) -> tuple[TomatoStatus | None, str]:
        # 检查当前用户是否已经开启其他番茄钟
        status = self.query_task(owner)
        if status:
            return status, "启动失败: 当前存在正在执行的番茄钟"

        # 查询Item状态是否符合预期
        item = self.item_manager.select_with_authority(xid, owner)
        if item.used_tomato >= item.expected_tomato:
            return None, "启动失败: 当前任务已完成全部番茄钟"

        # 针对owner字段设置了唯一索引, 避免一个用户同时提交多个番茄钟请求, 导致状态异常
        status = TomatoStatus(item_id=item.id, name=item.name, owner=owner)
        self.db.add(status)
        self.db.flush()
        return status, ""

    def finish_task(self, xid: int, owner: str) -> bool:
        status = self.query_task_for_update(owner)
        if status is None:
            return False

        if status.item_id != xid:
            logger.error(f"完成番茄钟失败: 用户{owner}当前任务的Id不匹配, 期望为 {status.item_id} 实际为 {xid}")
            return False

        self.db.delete(status)
        # 浏览器端由于内存回收等原因, 可能在番茄钟完成时触发两次完成操作
        # 当前无法有效区分此情况, 仅通过剩余番茄钟时间进行判断
        # 如果增加番茄钟操作失败, 则不进行后续操作
        if self.item_manager.increase_used_tomato(xid, owner):
            self.__insert_record(status)
            return True
        return False

    def clear_task(self, xid: int, reason: str, owner: str) -> bool:
        status = self.query_task(owner)
        if status is None:
            return False

        if status.item_id != xid:
            logger.error(f"清除番茄钟失败: 用户{owner}当前任务的Id不匹配, 期望为 {status.item_id} 实际为 {xid}")
            return False

        elapsed_minutes = (now() - status.start_time).total_seconds() / 60
        self.event_manager.add_event_log(
            owner,
            f"用户取消番茄钟任务[{status.name}]的执行, 取消原因是{reason}. 该任务在取消前已经执行{elapsed_minutes:.2f}分钟.",
        )
        self.db.delete(instance=status)
        self.db.flush()
        return True

    def query_task(self, owner: str) -> TomatoStatus | None:
        stmt = sal.select(TomatoStatus).where(TomatoStatus.owner == owner)
        return self.db.scalar(stmt)

    def query_task_for_update(self, owner: str) -> TomatoStatus | None:
        # 查询番茄钟时增加for update标记, 如果后续要更新该条目, 可以保证操作互斥, 不会同时更新触发多次业务逻辑的执行
        stmt = sal.select(TomatoStatus).where(TomatoStatus.owner == owner).with_for_update()
        return self.db.scalar(stmt)

    def get_task(self, owner: str) -> dict | None:
        status = self.query_task(owner)
        if not status:
            return None

        # 处于正常番茄钟范围内, 直接返回
        delta_time = now() - status.start_time
        if delta_time.total_seconds() < (WorkTimeSecond + RestTimeSecond):
            return status.to_dict()

        # 否则需要结束番茄钟
        if self.finish_task(status.item_id, status.owner):
            # 可以直接启动番茄钟, 如果没有配额了等于无事发生
            status, _ = self.start_task(status.item_id, status.owner)
            return status.to_dict() if status else None

    def has_task(self, owner) -> bool:
        return self.query_task(owner) is not None

    def add_tomato_record(self, name: str, start_time: str, owner: str) -> bool:
        item = Item(name=name, item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner)
        item.used_tomato = 1
        self.item_manager.create(item)

        record = TomatoTaskRecord(name=name, owner=owner, start_time=parse_time(start_time), finish_time=now())
        self.db.add(record)
        self.db.flush()
        return True

    def __insert_record(self, task: TomatoStatus):
        record = TomatoTaskRecord(start_time=task.start_time, finish_time=now(), owner=task.owner, name=task.name)
        self.db.add(record)


class TomatoRecordManager:
    def __init__(self, tomato_manager: TomatoManager):
        self.tomato_manager = tomato_manager
        self.item_manager = tomato_manager.item_manager
        self.db = self.item_manager.db

    def get_time_line_summary(self, owner: str):
        """获取今日番茄钟统计信息以及具体的时间轴"""
        record = self.select_record_after(owner, today_begin())
        items = [
            {"start": get_hour_str_from(r.start_time), "finish": get_hour_str_from(r.finish_time), "title": r.name}
            for r in record
        ]
        return {"counter": self.__time_line_stat(record), "items": items}

    def get_smart_analysis_report(self, owner: str):
        items = self.item_manager.select_done_item(owner)
        groups = []
        for iid, g in groupby(
            sorted(items, key=lambda x: x.parent if x.parent is not None else 0), key=lambda x: x.parent
        ):
            item = None
            if iid is not None:
                item = self.item_manager.select(iid)
            pname = "全局任务" if item is None else item.name
            groups.append({"name": pname, "items": [i.to_dict() for i in g]})

        return {"count": len(items), "groups": groups}

    def get_tomato_stat(self, owner):
        d = self.__load_data(owner)
        return {"total": self.__total_stat(d), "today": self.__today_stat(d), "week": self.__week_chart_stat(d)}

    # def get_daily_stat(self, owner):
    #     d = self.__load_data(owner)
    #     return self.__today_stat(d)

    # def select_today_tomato(self, owner: str) -> list:
    #     return self.__select_tomato_before(owner, today_begin())

    # def select_week_tomato(self, owner: str) -> list:
    #     return self.__select_tomato_before(owner, this_week_begin())

    # def get_tomato_log(self, owner: str) -> str:
    #     return "\n".join(map(str, self.__load_data(owner=owner, limit=20)))

    # def __select_tomato_before(self, owner: str, time):
    #     stmt = sal.select(TomatoTaskRecord.name, func.count()) \
    #         .where(TomatoTaskRecord.owner == owner, TomatoTaskRecord.start_time > time) \
    #         .group_by(TomatoTaskRecord.name)

    #     items = self.db.execute(stmt).all()
    #     return list(sorted(items, key=lambda x: x[1], reverse=True))

    def select_record_after(self, owner: str, time: datetime) -> Sequence[TomatoTaskRecord]:
        stmt = (
            sal.select(TomatoTaskRecord)
            .where(TomatoTaskRecord.owner == owner, TomatoTaskRecord.finish_time > time)
            .order_by(TomatoTaskRecord.id.asc())
        )
        return self.db.execute(stmt).scalars().all()

    def __load_data(self, owner: str, limit: int = 200) -> Sequence[TomatoTaskRecord]:
        stmt = (
            sal.select(TomatoTaskRecord)
            .where(TomatoTaskRecord.owner == owner, TomatoTaskRecord.finish_time > last_month())
            .order_by(TomatoTaskRecord.id.desc())
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    @staticmethod
    def __time_line_stat(data: Sequence[TomatoTaskRecord]) -> dict:
        time = timedelta()
        for record in data:
            time += record.finish_time - record.start_time
        count = len(data)
        return {"tomatoCounts": count, "totalMinutes": int(time.total_seconds() / 60)}

    @staticmethod
    def __total_stat(data: Sequence[TomatoTaskRecord]) -> dict:
        time = timedelta()
        for record in data:
            time += record.finish_time - record.start_time

        elapsed_day = 1
        count = len(data)
        if count >= 2:
            first_time = data[-1].start_time
            last_time = data[0].finish_time
            elapsed_day = (last_time - first_time).days + 1

        average_time = time.total_seconds() / elapsed_day

        return {"count": count, "hour": int(time.total_seconds() / 60 / 60), "average": int(average_time / 60)}

    @staticmethod
    def __today_stat(data: Sequence[TomatoTaskRecord]) -> dict:
        today = now().date()
        count = 0
        time = timedelta()
        for record in data:
            start = record.start_time
            finish = record.finish_time
            if start.date() == today:
                count += 1
                time += finish - start
        return {"count": count, "minute": int(time.total_seconds() / 60)}

    @staticmethod
    def __week_chart_stat(data: Sequence[TomatoTaskRecord]) -> list:
        WEEK_LENGTH = 15
        today = now().date()
        counts = [timedelta() for _ in range(WEEK_LENGTH)]
        for record in data:
            start = record.start_time
            finish = record.finish_time
            delta = (today - start.date()).days
            if delta < WEEK_LENGTH:
                counts[delta] += finish - start

        return list(map(lambda time: int(time.total_seconds() / 60), counts))

    def get_tomato_state_begin_time(self) -> tuple[datetime, str]:
        now_time = now()
        today_morning_start = datetime(now_time.year, now_time.month, now_time.day, 8, 0, 0)
        today_morning_end = datetime(now_time.year, now_time.month, now_time.day, 12, 0, 0)
        today_afternoon_end = datetime(now_time.year, now_time.month, now_time.day, 18, 0, 0)

        if now_time < today_morning_end:
            return today_morning_start, "上午"

        if now_time < today_afternoon_end:
            return today_morning_end, "下午"

        return today_afternoon_end, "晚上"

    def check_rest_time(self) -> str:
        now_time = now()
        noon_rest_start = datetime(now_time.year, now_time.month, now_time.day, 11, 30, 0)
        noon_rest_end = datetime(now_time.year, now_time.month, now_time.day, 14, 30, 0)

        evening_start = datetime(now_time.year, now_time.month, now_time.day, 17, 30, 0)
        evening_end = datetime(now_time.year, now_time.month, now_time.day, 19, 00, 0)

        night_start = datetime(now_time.year, now_time.month, now_time.day, 21, 00, 0)

        if noon_rest_start < now_time < noon_rest_end:
            return "午间休息时间"

        if evening_start < now_time < evening_end:
            return "晚间休息时间"

        if now_time > night_start:
            return "深夜休息时间"

        return ""

    def get_tomato_state(self, owner: str) -> str:
        begin_time, begin_state = self.get_tomato_state_begin_time()
        # 首先检查是否是番茄钟工作状态, 该状态优先级最高, 因此用户实际上可以在任意时间开始番茄钟
        state = self.tomato_manager.query_task(owner=owner)
        if state:
            last_group_cnt, last_tomato_cnt, _ = self.get_tomoto_record_info(owner=owner, begin_time=begin_time)
            work_finish_time = state.start_time + timedelta(minutes=25)
            rest_finish_time = work_finish_time + timedelta(minutes=5)
            now_time = now()
            if now_time < work_finish_time:
                remain_minutes = (work_finish_time - now_time).total_seconds() / 60
                return f"正在进行{begin_state}第{last_group_cnt + 1}组番茄钟内的第{last_tomato_cnt + 1}个番茄钟, 当前为工作状态, 番茄钟任务为[{state.name}], 工作时间剩余{remain_minutes:.1f}分钟\n"
            elif now_time < rest_finish_time:
                remain_minutes = (rest_finish_time - now_time).total_seconds() / 60
                return f"正在进行{begin_state}第{last_group_cnt + 1}组番茄钟内的第{last_tomato_cnt + 1}个番茄钟, 当前为休息状态, 番茄钟任务为[{state.name}], 休息时间剩余{remain_minutes:.1f}分钟\n"

        # 其次检查是否为休息时间, 相当于可以覆盖番茄钟的休息和规划状态
        reset_time = self.check_rest_time()
        if reset_time != "":
            return reset_time

        # 当前不是番茄钟状态, 先检查是否为初始状态
        last_group_cnt, last_tomato_cnt, last_record = self.get_tomoto_record_info(owner=owner, begin_time=begin_time)
        if last_record is None:
            # 没有开始任何番茄钟
            return "还未开始任何番茄钟\n"

        # 不是初始状态, 再检查休息和规划状态
        elapsed_minutes = (now() - last_record.finish_time).total_seconds() / 60
        # 如果上一个番茄钟是一组里的最后一个番茄钟, 则需要进行组之间的休息时间判断,
        if last_tomato_cnt == 0:
            if elapsed_minutes < 20:
                # 最后一个番茄钟会让cnt+1所以输出时无需+1了
                return f"已完成{begin_state}第{last_group_cnt}组番茄钟, 当前为大组之间的休息时间, 剩余{20 - elapsed_minutes:.1f}分钟\n"
            else:
                return f"已完成{begin_state}第{last_group_cnt}组番茄钟, 已完成大组之间的休息, 当前进入规划状态, 已持续{elapsed_minutes - 20:.1f}分钟\n"

        # 如果不是最后一个番茄钟
        return f"已完成{begin_state}第{last_group_cnt + 1}组番茄钟内的第{last_tomato_cnt}个番茄钟, 当前进入规划状态, 已持续{elapsed_minutes:.1f}分钟\n"

    def get_tomoto_record_info(self, owner: str, begin_time: datetime) -> tuple[int, int, TomatoTaskRecord | None]:
        tomato_records = self.select_record_after(owner=owner, time=begin_time)
        record_cnt = len(tomato_records)

        if record_cnt == 0:
            return 0, 0, None

        last_group_cnt = record_cnt // 4
        last_tomato_cnt = record_cnt % 4
        return last_group_cnt, last_tomato_cnt, tomato_records[-1]


# import datetime
# from typing import Sequence
# import sqlalchemy as sal
# from sqlalchemy.orm import scoped_session, Session
#
# from entity import Summary
# from tool4time import today_str
#
#
# class ReportManager:
#     def __init__(self, db: scoped_session[Session]) -> None:
#         self.db = db
#
#     def update_summary(self, content:str, owner: str)-> bool:
#         # day = today_str()
#         # stmt = sal.select(Summary).where(Summary.owner == owner, Summary.create_time == day)
#         # summary = self.db.scalar(stmt)
#         # if summary is None:
#         #     summary = Summary(create_time=day, content=content, owner=owner)
#         # else:
#         #     summary.content = content
#         # self.db.add(summary)
#         # self.db.flush()
#         return True
#
#     def get_today_summary(self, owner: str)-> str:
#         day = today_str()
#         stmt = sal.select(Summary.content).where(Summary.create_time == day, Summary.owner == owner)
#         content =  self.db.scalar(stmt)
#         if content is None:
#             return ""
#         return content
#
#     def get_summary_from(self, date: datetime.datetime) -> Sequence[Summary]:
#         stmt = sal.select(Summary).where(Summary.create_time > date)
#         return self.db.execute(stmt).scalars().all()
