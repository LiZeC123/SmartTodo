from datetime import timedelta
from itertools import groupby
from typing import Dict, Optional, Sequence

import sqlalchemy as sal
from sqlalchemy.orm import scoped_session, Session

from app.models.base import ItemType, TomatoType
from app.models.item import Item
from app.models.tomato import TomatoStatus, TomatoTaskRecord
from app.services.item_manager import ItemManager
from app.tools.logger import logger
from app.tools.time import get_hour_str_from, now, parse_time, today_begin


class TomatoManager:
    def __init__(self, db: scoped_session[Session], item_manager: ItemManager):
        self.db = db
        self.item_manager = item_manager
        # self.event_manager = EventManager(db)

    def start_task(self, xid: int, owner: str) -> str:
        # 检查当前用户是否已经开启其他番茄钟
        status = self.query_task(owner)
        if status:
            return '启动失败: 当前存在正在执行的番茄钟'

        # 查询Item状态是否符合预期
        item = self.item_manager.select_with_authority(xid, owner)
        if item.used_tomato == item.expected_tomato:
            # 如果当前已完成全部番茄钟, 则自动增加一个预期番茄钟
            # TODO: 预期时间变更操作落库, 后续进行分析
            self.item_manager.increase_expected_tomato(xid, owner)

        # 针对owner字段设置了唯一索引, 避免一个用户同时提交多个番茄钟请求, 导致状态异常
        status = TomatoStatus(item_id=item.id, name=item.name, owner=owner)
        self.db.add(status)
        self.db.flush()
        return ""

    def finish_task(self, xid: int, owner: str) -> bool:
        status = self.query_task(owner)
        if status is None:
            return False

        if status.item_id != xid:
            logger.error(f"完成番茄钟失败: 用户{owner}当前任务的Id不匹配, 期望为 {status.item_id} 实际为 {xid}")
            return False

        with self.db.begin(nested=True):
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

        # self.event_manager.add_event(f"由于 {reason} 取消番茄钟 {status.name}", owner)
        self.db.delete(instance=status)
        self.db.flush()
        return True

    def query_task(self, owner: str) -> Optional[TomatoStatus]:
        stmt = sal.select(TomatoStatus).where(TomatoStatus.owner == owner)
        return self.db.scalar(stmt)

    def get_task(self, owner: str) -> Dict | None:
        status = self.query_task(owner)
        if status:
            return status.to_dict()

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
        record = TomatoTaskRecord(start_time=task.start_time, finish_time=now(),
                                  owner=task.owner, name=task.name)
        self.db.add(record)


class TomatoRecordManager:
    def __init__(self, db: scoped_session[Session], item_manager: ItemManager):
        self.db = db
        self.item_manager = item_manager

    def get_time_line_summary(self, owner: str):
        record = self.__select_record_before(owner, today_begin())
        return {"counter": self.__time_line_stat(record), "items": [
            {"start": get_hour_str_from(r.start_time), "finish": get_hour_str_from(r.finish_time), "title": r.name} for
            r in record]}

    def get_smart_analysis_report(self, owner: str):
        items = self.item_manager.select_done_item(owner)
        groups = []
        for iid, g in groupby(sorted(items, key=lambda x: x.parent if x.parent is not None else 0),
                              key=lambda x: x.parent):
            item = None
            if iid is not None:
                item = self.item_manager.select(iid)
            pname = '全局任务' if item is None else item.name
            groups.append({"name": pname, "items": [i.to_dict() for i in g]})

        return {"count": len(items), "groups": groups}

    # def get_tomato_stat(self, owner):
    #     d = self.__load_data(owner)
    #     return {"total": self.__total_stat(d), "today": self.__today_stat(d), "week": self.__week_chart_stat(d)}

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

    def __select_record_before(self, owner: str, time) -> Sequence[TomatoTaskRecord]:
        stmt = sal.select(TomatoTaskRecord) \
            .where(TomatoTaskRecord.owner == owner, TomatoTaskRecord.finish_time > time) \
            .order_by(TomatoTaskRecord.id.asc())
        return self.db.execute(stmt).scalars().all()

    # def __load_data(self, owner: str, limit: int = 200) -> List[TomatoTaskRecord]:
    #     stmt = sal.select(TomatoTaskRecord).where(TomatoTaskRecord.owner == owner,
    #                                               TomatoTaskRecord.finish_time > last_month()) \
    #         .order_by(TomatoTaskRecord.id.desc()).limit(limit)
    #     return self.db.execute(stmt).scalars().all()

    @staticmethod
    def __time_line_stat(data: Sequence[TomatoTaskRecord]) -> dict:
        time = timedelta()
        for record in data:
            time += (record.finish_time - record.start_time)
        count = len(data)
        return {"tomatoCounts": count, "totalMinutes": int(time.total_seconds() / 60)}

    # @staticmethod
    # def __total_stat(data: List[TomatoTaskRecord]) -> dict:
    #     time = timedelta()
    #     for record in data:
    #         time += (record.finish_time - record.start_time)

    #     elapsed_day = 1
    #     count = len(data)
    #     if count >= 2:
    #         first_time = data[-1].start_time
    #         last_time = data[0].finish_time
    #         elapsed_day = (last_time - first_time).days + 1

    #     average_time = time.total_seconds() / elapsed_day

    #     return {
    #         "count": count,
    #         "hour": int(time.total_seconds() / 60 / 60),
    #         "average": int(average_time / 60)
    #     }

    # @staticmethod
    # def __today_stat(data: List[TomatoTaskRecord]) -> dict:
    #     today = now().date()
    #     count = 0
    #     time = timedelta()
    #     for record in data:
    #         start = record.start_time
    #         finish = record.finish_time
    #         if start.date() == today:
    #             count += 1
    #             time += (finish - start)
    #     return {
    #         "count": count,
    #         "minute": int(time.total_seconds() / 60)
    #     }

    # @staticmethod
    # def __week_chart_stat(data: List[TomatoTaskRecord]) -> list:
    #     WEEK_LENGTH = 15
    #     today = now().date()
    #     counts = [timedelta() for _ in range(WEEK_LENGTH)]
    #     for record in data:
    #         start = record.start_time
    #         finish = record.finish_time
    #         delta = (today - start.date()).days
    #         if delta < WEEK_LENGTH:
    #             counts[delta] += (finish - start)

    #     return list(map(lambda time: int(time.total_seconds() / 60), counts))
