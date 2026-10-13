import random
from collections.abc import Sequence
from datetime import datetime, timedelta

import sqlalchemy as sal

from app.models.memory import (
    KB,
    MemoryDetail,
    MemoryDetailType,
    make_memory_detail,
)
from app.models.role import RoleConfig
from app.services.assistant_history import AssistantHistoryManager
from app.services.role_manager import RoleManager
from app.template.prompt import DiaryQueryPrompt
from app.tools.llm import LLMClient
from app.tools.log import logger
from app.tools.time import get_datetime_from_str, get_str_from_datetime, now, the_day_begin, today_begin

MinCompressionSize = 2 * KB


class AssistantMemoryManager:
    def __init__(self, rm: RoleManager, lc: LLMClient, hm: AssistantHistoryManager) -> None:
        self.db = hm.db
        self.role_manager = rm
        self.client = lc
        self.history_manager = hm

    def query_memory_detail(self, assistant_name: str, owner: str) -> str:
        """基于角色的记忆使用策略, 按照配置加载对应的记忆项, 返回提示词文本"""
        content = ""
        policy = self.role_manager.get_role(name=assistant_name).get_memory_policy()

        # 日记仅提取当前原始对话中不包含的, 避免重复信息太多
        end_time = the_day_begin(self.query_msg_start_time(assistant_name, owner))
        if policy.max_diary_num > 0:
            diary: str = self.query_diary(policy.max_diary_num, end_time, assistant_name, owner)
            content += f"# 角色近期日记\n{diary}\n" if diary else ""

        content = content.strip()
        if content:
            return "以下是你与用户之间的已经发生过的事件的总结信息\n" + content
        else:
            return ""

    def dump_memory_detail(self, assistant_name: str, owner: str) -> str:
        end_time = now()
        diary: str = self.query_diary(20, end_time, assistant_name, owner)
        content = f"# 角色近期日记\n{diary}\n\n" if diary else ""

        return content

    def query_diary(self, diary_num: int, end_time: datetime, assistant_name: str, owner: str) -> str:
        if diary_num < 1:
            diary_num = 1

        min_id, content = self.__query_watermark(assistant_name, owner, MemoryDetailType.Milestone)
        stmt = (
            sal.select(MemoryDetail)
            .where(
                MemoryDetail.owner == owner,
                MemoryDetail.assistant_name == assistant_name,
                MemoryDetail.tag == MemoryDetailType.Diary,
                MemoryDetail.id > min_id,
                MemoryDetail.content_time < end_time,
            )
            .order_by(MemoryDetail.id.desc())
            .limit(diary_num)
        )

        content.extend([f"{r.content_time.strftime('%Y-%m-%d')}\n{r.content}\n" for r in self.db.scalars(stmt)])
        total = "\n".join(reversed(content))
        return total

    def query_diary_with(self, query: str, assistant_name: str, owner: str) -> str:
        end_time = now()
        diary: str = self.query_diary(30, end_time, assistant_name, owner)
        prompt = DiaryQueryPrompt.format(query=query, diary=diary)
        reason, content = self.client.generate_one_shot(prompt, thinking=True, simple_client=True)
        logger.info(f"{assistant_name}查询{query}得到{content}\n思考过程{reason}")
        return content

    def query_last_reason(self, assistant_name: str, owner: str) -> str:
        _, items = self.__query_watermark(assistant_name, owner, MemoryDetailType.Thinking)
        return items[0] if items else ""

    def __query_watermark(self, assistant_name: str, owner: str, tag: int) -> tuple[int, list[str]]:
        """查询指定tag类型有无水位线, 如果有返回水位线id和内容数组, 如果无返回默认值"""
        watermark = self.__query_lastest(assistant_name, owner, tag)
        if watermark:
            min_id = watermark[0].id
            content = [watermark[0].content]
        else:
            min_id = 0
            content = []
        return min_id, content

    def __query_lastest(self, assistant_name: str, owner: str, tag: int) -> Sequence[MemoryDetail]:
        stmt = (
            sal.select(MemoryDetail)
            .where(
                MemoryDetail.owner == owner,
                MemoryDetail.assistant_name == assistant_name,
                MemoryDetail.tag == tag,
            )
            .order_by(MemoryDetail.id.desc())
            .limit(1)
        )

        return self.db.scalars(stmt).all()

    def get_lastest_diary_day(self, assistant_name: str, owner: str) -> datetime:
        records = self.__query_lastest(assistant_name, owner, tag=MemoryDetailType.Diary)
        if records:
            return records[0].content_time
        else:
            return datetime(year=2026, month=5, day=1)

    def query_msg_start_time(self, assistant_name: str, owner: str) -> datetime:
        """
        查询聊天记录的起始时刻, 起始时刻之前的内容使用记忆代替, 起始时刻之后的内容保留原始文本
        """
        details = self.__query_lastest(assistant_name, owner, MemoryDetailType.StartTime)
        if not details:
            # 没有设置过时间时, 进行初始化计算
            policy = self.role_manager.get_role(name=assistant_name).get_memory_policy()
            start_day = self.history_manager.evalute_first_memory_datetime(
                policy.raw_content_size, assistant_name, owner
            )
            self.set_process_time(start_day, assistant_name=assistant_name, owner=owner, reason="初始化")
            return start_day

        # 否则直接返回记录的时间, 在执行记忆压缩时会重新计算时间
        return get_datetime_from_str(details[0].content)

    def update_memory_item(self, config: RoleConfig, content: str, owner: str):
        content_time = today_begin() - timedelta(days=1)
        item = make_memory_detail(
            content, assistant_name=config.name, owner=owner, tag=MemoryDetailType.Diary, content_time=content_time
        )
        self.db.add(item)

        policy = config.get_memory_policy()
        old_start_time = self.query_msg_start_time(config.name, owner)
        new_start_time = self.history_manager.evalute_first_memory_datetime(policy.raw_content_size, config.name, owner)
        if new_start_time > old_start_time:
            self.set_process_time(new_start_time, assistant_name=config.name, owner=owner, reason="自动更新")
        self.db.flush()

    def query_rumor_diary(self, owner: str) -> MemoryDetail | None:
        stmt = (
            sal.select(MemoryDetail)
            .where(
                MemoryDetail.owner == owner,
                MemoryDetail.tag == MemoryDetailType.Diary,
            )
            .order_by(MemoryDetail.id.desc())
            .limit(10)
        )
        records = self.db.scalars(stmt).all()
        if not records:
            return None
        return random.choice(records)

    def set_process_time(self, process_time: datetime, /, *, assistant_name: str, owner: str, reason="手动设置"):
        detail = make_memory_detail(
            get_str_from_datetime(process_time),
            reason=reason,
            assistant_name=assistant_name,
            owner=owner,
            tag=MemoryDetailType.StartTime,
            content_time=now(),
        )
        self.db.add(detail)
        self.db.flush()
