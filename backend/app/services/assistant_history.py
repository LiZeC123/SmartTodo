from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta

import sqlalchemy as sal
from sqlalchemy.orm import Session, scoped_session

from app.models.assistant import AssistantModeType, AssistantType, History, Status, make_assistant_status
from app.models.exception import LLMIllegalStatusException
from app.services.role_manager import RoleConfig
from app.tools.log import logger
from app.tools.time import now, today_begin


class AssistantHistoryManager:
    def __init__(self, db: scoped_session[Session]) -> None:
        self.db = db

    def add_user_prompt(self, prompt: str, inject: str, owner: str, *, tag: int = 0):
        status = self.query_or_init_status(owner)
        msg = History(
            role="user",
            content=prompt,
            system_inject_content=inject,
            owner=owner,
            assistant_name=status.assistant_name,
            assistant_mode=status.assistant_mode,
            tag=tag,
        )
        self.db.add(msg)
        self.db.flush()

    def add_assistant_answer(self, content: str, owner: str, *, tool_call_list_json="", tag: int = 0):
        status = self.query_or_init_status(owner)
        msg = History(
            role="assistant",
            content=content,
            owner=owner,
            assistant_name=status.assistant_name,
            assistant_mode=status.assistant_mode,
            tool_call_list_json=tool_call_list_json,
            tag=tag,
        )
        self.db.add(msg)
        self.db.flush()
        # 由于助手消息需要等待流式输出完毕才能添加, 因此通常会滞后插入数据, 为了避免长时间持有锁, 插入完毕立即提交
        self.db.commit()

    def add_tool_call_msg(self, tool_call_id: str, content: str, *, owner: str, tag: int = 0):
        status = self.query_or_init_status(owner)
        msg = History(
            role="tool",
            tool_call_id=tool_call_id,
            content=content,
            owner=owner,
            assistant_name=status.assistant_name,
            assistant_mode=status.assistant_mode,
            tag=tag,
        )
        self.db.add(msg)
        self.db.flush()

    def switch(self, /, role_config: RoleConfig, owner: str):
        status = self.query_or_init_status(owner)
        status.assistant_name = role_config.name

        msg = self.select_last_msg(role_config.name, owner)
        role_mode = msg.assistant_mode if msg else AssistantModeType.RolePlaying
        status.assistant_mode = role_mode

        self.db.flush()

    def change_mode(self, role_mode: int, owner: str):
        status = self.query_or_init_status(owner)
        status.assistant_mode = role_mode
        self.db.flush()

    def set_auto_continue(self, min_char_num: int, owner: str):
        if min_char_num < 0:
            min_char_num = 0

        status = self.query_or_init_status(owner)
        status.auto_continue = min_char_num
        self.db.flush()

    def merge_assistant_msg(self, owner: str):
        assistant_msg_0 = self.remove_last_assistant(owner)
        if not assistant_msg_0:
            raise LLMIllegalStatusException(f"[{owner}]: 获取最后一条助手消息失败")

        user_msg_0 = self.remove_last_user(owner)
        if not user_msg_0:
            raise LLMIllegalStatusException(f"[{owner}]: 获取最后一条用户消息失败")

        assistant_msg_1 = self.remove_last_assistant(owner)
        if not assistant_msg_1:
            raise LLMIllegalStatusException(f"[{owner}]: 获取倒数第二条助手消息失败")

        content = assistant_msg_1.content + assistant_msg_0.content
        self.add_assistant_answer(content, owner)

    def remove_anto_answer_msg(self, owner: str) -> str:
        auto_answer = self.remove_last_assistant(owner)
        if not auto_answer:
            raise LLMIllegalStatusException(f"[{owner}]: 获取自动回答消息失败")

        prompt = self.remove_last_user(owner)
        if not prompt:
            raise LLMIllegalStatusException(f"[{owner}]: 获取自动回答的用户提示词消息失败")

        return auto_answer.content

    def remove_last_assistant(self, owner: str) -> History | None:
        """移除最后一个助手回复及其关联的工具调用/返回结果消息。

        一次助手回复可能因工具调用产生多条 DB 消息：
            assistant (tool_calls) → tool (结果) → assistant (最终回复)
        此方法从末尾向前扫描，删除所有非 user 消息，合并其内容后返回；
        遇到 user 消息或没有更多消息时停止。
        """
        status = self.query_or_init_status(owner)

        last = self.select_last_msg(status.assistant_name, owner)
        if last is None:
            return None
        if last.role == AssistantType.User:
            return None

        # 从后向前扫描，收集并删除所有属于该助手回复的消息
        content_parts: list[str] = []
        tool_call_json = ""
        # 记录最早（时序上最靠前）消息的元信息
        first_create_time = last.create_time
        first_assistant_name = last.assistant_name
        first_assistant_mode = last.assistant_mode

        while True:
            last = self.select_last_msg(status.assistant_name, owner)
            if last is None:
                break
            if last.role == AssistantType.User:
                break  # 遇到用户消息，停止

            if last.content:
                content_parts.append(last.content)
            if last.tool_call_list_json:
                tool_call_json = last.tool_call_list_json

            # 持续更新为更早消息的元信息
            first_create_time = last.create_time
            first_assistant_name = last.assistant_name
            first_assistant_mode = last.assistant_mode

            self.db.delete(last)
            self.db.flush()

        if not content_parts:
            return None

        self.db.flush()

        # content_parts 是反向收集的（从晚到早），反转后拼接
        content_parts.reverse()
        merged_content = "".join(content_parts)

        return History(
            role=AssistantType.Assistant,
            content=merged_content,
            tool_call_list_json=tool_call_json,
            create_time=first_create_time,
            owner=status.owner,
            assistant_name=first_assistant_name,
            assistant_mode=first_assistant_mode,
        )

    def remove_last_user(self, owner: str) -> History | None:
        status = self.query_or_init_status(owner)
        last = self.select_last_msg(status.assistant_name, owner)
        if last is None:
            return None

        if last.role != AssistantType.User:
            return None

        self.db.delete(last)
        self.db.flush()
        return last

    def remove_last_pair(self, owner: str) -> bool:
        status = self.query_or_init_status(owner)
        while True:
            last = self.select_last_msg(status.assistant_name, owner)
            if last is None:
                break

            if last.role == AssistantType.User:
                self.db.delete(last)
                self.db.flush()
                break
            else:
                self.db.delete(last)
                self.db.flush()
        return True

    def query_or_init_status(self, owner: str) -> Status:
        stmt = sal.select(Status).where(Status.owner == owner)
        t = self.db.scalar(stmt)
        if t is None:
            t = make_assistant_status(owner=owner)
            self.db.add(t)
            self.db.flush()
        return t

    def select_last_msg(self, assistant_name: str, owner: str) -> History | None:
        """查询指定角色最后一条消息"""
        stmt = (
            sal.select(History)
            .where(History.owner == owner, History.assistant_name == assistant_name)
            .order_by(History.id.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def query_last_assistant_msg_length(self, owner: str) -> int:
        status = self.query_or_init_status(owner)
        last = self.select_last_msg(status.assistant_name, owner)
        if last is None:
            raise LLMIllegalStatusException(f"[{owner}: {status.assistant_name}] 当前没有助手消息")
        if last.role != AssistantType.Assistant:
            raise LLMIllegalStatusException(f"[{owner}: {status.assistant_name}] 最后一条消息不是助手消息")

        return len(last.content)

    def get_last_assistant_mode_time(self, status: Status) -> datetime:
        # 查询当前助手上一次助手模式的记录时间, 在非助手模式或者其他助手对话过程中产生的记录对当前助手来说是没有见过的
        stmt = (
            sal.select(History)
            .where(
                History.owner == status.owner,
                History.assistant_mode == AssistantModeType.Assistant,
                History.assistant_name == status.assistant_name,
            )
            .order_by(History.id.desc())
            .limit(1)
        )
        last = self.db.scalar(stmt)
        if last is None:
            return today_begin()
        else:
            return last.create_time

    def get_recent_assistant_list(self, owner: str) -> Sequence[str]:
        """按照最后活动顺序获得所有交互过的助理列表"""
        sql = sal.text("""
            SELECT assistant_name
            FROM (
                SELECT assistant_name, MAX(id) as last_id
                FROM assistant_history
                WHERE owner = :owner
                GROUP BY assistant_name
            ) t
            ORDER BY last_id DESC
        """)

        result = self.db.execute(sql, {"owner": owner})
        names = result.scalars().all()  # 获得按照最近聊天顺序的列表
        return names

    def select_record_between(
        self, role_name: str, start_time: datetime, end_time: datetime, owner: str
    ) -> Sequence[History]:
        if start_time >= end_time:
            logger.warning(f"[{owner}:{role_name}]: 查询记录的时间范围异常. {start_time} > {end_time} ")
            return []

        stmt = sal.select(History).where(
            History.owner == owner,
            History.assistant_name == role_name,
            History.create_time > start_time,
            History.create_time < end_time,
        )
        return self.db.scalars(stmt).all()

    def select_inject_history(self, role_name: str, limit: int, owner: str) -> Sequence[History]:
        if limit < 1:
            limit = 1

        stmt = (
            sal.select(History)
            .where(History.owner == owner, History.assistant_name == role_name, History.system_inject_content != "")
            .order_by(History.id.desc())
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def get_more_web_history(self, end_time: datetime, owner: str) -> list[dict]:
        status = self.query_or_init_status(owner)
        stmt = (
            sal.select(History)
            .where(
                History.owner == owner, History.create_time < end_time, History.assistant_name == status.assistant_name
            )
            .order_by(History.id.desc())
            .limit(20)
        )
        records = reversed(self.db.scalars(stmt).all())
        return self.to_web_json_list(records)

    def to_web_json_list(self, records: Iterable[History]):
        return self.post_merging(
            [msg.to_web_json() for msg in records if msg.role in [AssistantType.User, AssistantType.Assistant]]
        )

    def post_merging(self, records: list[dict]):
        if len(records) == 0:
            return records

        last = records[0]
        rst = [last]
        for rec in records[1:]:
            this_role = rec.get("role")
            if this_role == AssistantType.Assistant and last.get("role") == AssistantType.Assistant:
                last["content"] += rec.get("content")
            else:
                rst.append(rec)
                last = rec
        return rst

    def evalute_day_cost(self, role_name: str, start_day: datetime, owner: str) -> list[tuple[str, int, int]]:
        """
        按天统计指定角色的每日成本, 返回三元组(统计日期, 总字符数, 消息数)
        """

        stmt = (
            sal.select(
                sal.func.date(History.create_time).label("stat_date"),
                sal.func.sum(sal.func.length(History.content) + sal.func.length(History.system_inject_content)).label(
                    "total_chars"
                ),
                sal.func.count().label("msg_count"),
            )
            .where(History.owner == owner, History.assistant_name == role_name, History.create_time > start_day)
            .group_by(sal.func.date(History.create_time))
            .order_by(sal.desc("stat_date"))
        )
        records = self.db.execute(stmt)
        return [(r.stat_date, r.total_chars, r.msg_count) for r in records]

    def evalute_first_memory_datetime(self, min_size: int, role_name: str, owner: str) -> datetime:
        start_day = now() - timedelta(14)
        acc = 0
        for day, total_chars, _ in self.evalute_day_cost(role_name, start_day, owner):
            acc += total_chars
            if acc > min_size:
                return datetime.strptime(day, "%Y-%m-%d")
        return start_day

    def select_recent_tool_call_msgs(self, assistant_name: str, limit: int, owner: str) -> Sequence[History]:
        stmt = (
            sal.select(History)
            .where(
                History.owner == owner,
                History.assistant_name == assistant_name,
                History.role == "assistant",
                History.tool_call_list_json != "",
            )
            .order_by(History.id.desc())
            .limit(limit)
        )
        return list(reversed(self.db.scalars(stmt).all()))

    def select_tool_result_msg(self, tool_call_id: str) -> History | None:
        return self.db.scalar(sal.select(History).where(History.tool_call_id == tool_call_id, History.role == "tool"))
