import json
import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from datetime import datetime, timedelta

import sqlalchemy as sal
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolUnionParam,
    ChatCompletionUserMessageParam,
)
from sqlalchemy.orm import Session, scoped_session

from app.models.assistant import (
    AssistantModeType,
    AssistantTagType,
    AssistantType,
    History,
    Status,
    assistant_mode_str,
    make_assistant_status,
)
from app.models.item import Item
from app.models.memory import (
    KB,
    MemoryDetail,
    MemoryDetailType,
    MemoryPolicy,
    MinCompressionSize,
    make_memory_detail,
)
from app.services.config_manager import ConfigManager
from app.services.role_manager import RoleConfig, RoleManager
from app.services.tomato_manager import TomatoRecordManager
from app.template.prompt import (
    AnyQueryPrompt,
    AssistantSp,
    InjectRumorPrompt,
    LongTermMemoryPrompt,
    RolePalyingSp,
    RumorMemoryPrompt,
)
from app.template.tools import AnyQueryTool, CreatItemTool, GetDeadlineItemTool
from app.tools.llm import LLMClient
from app.tools.log import logger
from app.tools.time import (
    format_timedelta,
    get_datetime_from_str,
    get_hour_str_from,
    get_str_from_datetime,
    now,
    now_str,
    parse_befeore_time_str,
    the_day_begin,
    today_begin,
)


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
        self.db.commit()

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
        self.db.commit()

    def switch(self, /, role_config: RoleConfig, owner: str):
        status = self.query_or_init_status(owner)
        status.assistant_name = role_config.name

        msg = self.select_last_msg(role_config.name, owner)
        role_mode = msg.assistant_mode if msg else AssistantModeType.RolePlaying
        status.assistant_mode = role_mode

        self.db.flush()
        self.db.commit()

    def change_mode(self, role_mode: int, owner: str):
        status = self.query_or_init_status(owner)
        status.assistant_mode = role_mode
        self.db.flush()
        self.db.commit()

    def remove_last_assistant(self, owner: str) -> bool:
        status = self.query_or_init_status(owner)
        last = self.select_last_msg(status.assistant_name, owner)
        if last is None:
            return False

        if last.role != AssistantType.Assistant:
            return False

        self.db.delete(last)
        self.db.flush()
        self.db.commit()
        return True

    def remove_last_user(self, owner: str) -> bool:
        status = self.query_or_init_status(owner)
        last = self.select_last_msg(status.assistant_name, owner)
        if last is None:
            return False

        if last.role != AssistantType.User:
            return False

        self.db.delete(last)
        self.db.flush()
        self.db.commit()
        return True

    def remove_last_pair(self, owner: str) -> bool:
        status = self.query_or_init_status(owner)
        while True:
            last = self.select_last_msg(status.assistant_name, owner)
            if last is None:
                break

            if last.role == AssistantType.User:
                self.db.delete(last)
                break
            else:
                self.db.delete(last)
        self.db.flush()
        self.db.commit()
        return True

    def query_or_init_status(self, owner: str) -> Status:
        stmt = sal.select(Status).where(Status.owner == owner)
        t = self.db.scalar(stmt)
        if t is None:
            t = make_assistant_status(owner=owner)
            self.db.add(t)
            self.db.flush()
            self.db.commit()
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


class AssistantMemoryManager:
    RUMOR_ROLE_NAME = "公共"
    CACHE_EXPIRE_TIME = 20 * 3600

    def __init__(
        self,
        db: scoped_session[Session],
        role_manager: RoleManager,
        llm_client: LLMClient,
        history_manager: AssistantHistoryManager,
    ) -> None:
        self.db = db
        self.role_manager = role_manager
        self.client = llm_client
        self.history_manager = history_manager

    def query_memory_detail(self, assistant_name: str, owner: str) -> str:
        """基于角色的记忆使用策略, 按照配置加载对应的记忆项, 返回提示词文本"""
        content = ""
        config = self.role_manager.get_role(name=assistant_name)
        policy = MemoryPolicy.get_policy(config.memory_policy)

        if policy.enable_role_setting:
            setting: str = self.query_role_setting(assistant_name, owner)
            content += f"# 角色新增设定\n{setting}\n" if setting else ""

        if policy.enable_preference:
            preference: str = self.query_preference(assistant_name, owner)
            content += f"# 预测用户偏好\n{preference}\n" if preference else ""

        if policy.max_topic_num > 0:
            topic: str = self.query_topic(policy.max_topic_num, assistant_name, owner)
            content += f"# 近期话题\n{topic}\n" if topic else ""

        if policy.max_diary_num > 0:
            # TODO: 日记和里程碑的处理与其他字段不一样, 还需要更细致的操作
            # 原始对话文本的开始时间那一天就是日记的截止时间, 避免加载重复的内容
            end_time = self.query_msg_start_time(assistant_name, owner)
            end_time = the_day_begin(end_time)
            diary: str = self.query_diary(policy.max_diary_num, end_time, assistant_name, owner)
            content += f"# 角色近期日记\n{diary}\n" if diary else ""

        content = content.strip()
        if content:
            return "以下是你与用户之间的已经发生过的事件的总结信息\n" + content
        else:
            return ""

    def dump_memory_detail(self, assistant_name: str, owner: str) -> str:
        content = "当前角色所有生效的记忆项\n\n"
        setting: str = self.query_role_setting(assistant_name, owner)
        content += f"# 角色新增设定\n{setting}\n\n" if setting else ""

        preference: str = self.query_preference(assistant_name, owner)
        content += f"# 预测用户偏好\n{preference}\n\n" if preference else ""

        topic: str = self.query_topic(15, assistant_name, owner)
        content += f"# 近期话题\n{topic}\n\n" if topic else ""

        end_time = now()
        diary: str = self.query_diary(5, end_time, assistant_name, owner)
        content += f"# 角色近期日记\n{diary}\n\n" if diary else ""

        return content

    def query_topic(self, topic_num: int, assistant_name: str, owner: str) -> str:
        if topic_num < 1 or topic_num > 15:
            topic_num = 1

        stmt = (
            sal.select(MemoryDetail)
            .where(
                MemoryDetail.owner == owner,
                MemoryDetail.assistant_name == assistant_name,
                MemoryDetail.tag == MemoryDetailType.RecentTopic,
            )
            .order_by(MemoryDetail.id.desc())
            .limit(topic_num)
        )
        records = self.db.scalars(stmt).all()

        if len(records) == 0:
            return ""

        total_content = "\n".join([r.content for r in records])
        return total_content

    def query_role_setting(self, assistant_name: str, owner: str) -> str:
        min_id, content = self.__query_watermark(assistant_name, owner, MemoryDetailType.FixedSetting)
        stmt = sal.select(MemoryDetail).where(
            MemoryDetail.owner == owner,
            MemoryDetail.assistant_name == assistant_name,
            MemoryDetail.tag == MemoryDetailType.RoleSetting,
            MemoryDetail.id > min_id,
        )

        content.extend([r.content for r in self.db.scalars(stmt)])
        if len(content) == 0:
            return ""

        total = "\n".join(content)
        return total

    def query_preference(self, assistant_name: str, owner: str) -> str:
        min_id, content = self.__query_watermark(assistant_name, owner, MemoryDetailType.FixedPreference)
        stmt = sal.select(MemoryDetail).where(
            MemoryDetail.owner == owner,
            MemoryDetail.assistant_name == assistant_name,
            MemoryDetail.tag == MemoryDetailType.Preference,
            MemoryDetail.id > min_id,
        )

        content.extend([r.content for r in self.db.scalars(stmt)])
        if len(content) == 0:
            return ""

        total = "\n".join(content)
        return total

    def query_diary(self, diary_num: int, end_time: datetime, assistant_name: str, owner: str) -> str:
        if diary_num < 1 or diary_num > 10:
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
        total = "\n".join(content)
        return total

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
            config = self.role_manager.get_role(name=assistant_name)
            policy = MemoryPolicy.get_policy(config.memory_policy)
            start_day = self.history_manager.evalute_first_memory_datetime(
                policy.raw_content_size, assistant_name, owner
            )
            content = get_str_from_datetime(start_day)
            self.set_process_time(content=content, assistant_name=assistant_name, owner=owner, reason="初始化")
            return start_day

        # 否则直接返回记录的时间, 在执行记忆压缩时会重新计算时间
        return get_datetime_from_str(details[0].content)

    # TODO: 二级内容提取, 里程碑等内容
    def update_long_term_memory(self, *, config: RoleConfig, owner: str) -> bool:
        # 判断记忆压缩策略
        if config.memory_policy == "None":
            logger.info(f"[{owner}:{config.name}]: 跳过压缩, 该角色记忆压缩策略为不压缩")
            return False

        # 查询需要压缩的记录, 判断是否满足记忆压缩策略
        start_time = self.get_lastest_diary_day(config.name, owner) + timedelta(days=1)
        records = self.history_manager.select_record_between(config.name, start_time, today_begin(), owner)
        cost = sum(len(s) for r in records if (s := r.to_dump()) is not None)
        if cost < MinCompressionSize:
            logger.info(
                f"[{owner}:{config.name}]: 跳过压缩, 当前待压缩对话长度 {cost / KB:.2f} KB < 最小压缩长度 {MinCompressionSize / KB:.2f} KB"
            )
            return False

        # 执行压缩操作
        new_content = "\n".join([json.dumps(r.to_openai(), ensure_ascii=False) for r in records])
        existing_content = self.query_role_setting(config.name, owner) + self.query_preference(config.name, owner)
        existing_content = "当前没有内容" if not existing_content else existing_content
        prompt = LongTermMemoryPrompt.format(
            role_desc=config.get_self_desc(), existing_content=existing_content, new_content=new_content
        )
        reason, content = self.client.generate_one_shot(prompt)
        if content is None:
            logger.error(f"[{owner}:{config.name}]: 模型返回记忆为空")
            return False

        # 更新记忆
        details = self.split_markdown_by_heading(content)
        items, err = self.parse_markdown_item(details, config.name, owner)
        self.db.add_all(items)
        if err:
            logger.warning(f"记忆项目存在提取失败: {err}\n原始内容:{content}")

        if reason:
            item = make_memory_detail(
                reason,
                assistant_name=config.name,
                owner=owner,
                tag=MemoryDetailType.Thinking,
                content_time=now(),
            )
            self.db.add(item)

        policy = MemoryPolicy.get_policy(config.memory_policy)
        old_start_time = self.query_msg_start_time(config.name, owner)
        new_start_time = self.history_manager.evalute_first_memory_datetime(policy.raw_content_size, config.name, owner)
        if new_start_time > old_start_time:
            self.set_process_time(
                content=get_str_from_datetime(new_start_time),
                assistant_name=config.name,
                owner=owner,
                reason="自动更新",
            )

        self.db.commit()

        logger.info(
            f"[{owner}:{config.name}] 记忆压缩完毕, 新对话起始时间为 {get_str_from_datetime(new_start_time)}, 新增记忆长度为 {len(content) / KB:.2f} KB, 思考长度为 {len(reason) / KB:.2f} KB"
        )
        return True

    def rumor_propagation(self, start_time: datetime, owner: str) -> bool:
        roles = self.history_manager.get_recent_assistant_list(owner)
        if len(roles) == 0:
            return False

        end_time = start_time + timedelta(days=1)
        stmt = sal.select(MemoryDetail).where(
            MemoryDetail.owner == owner,
            MemoryDetail.content_time >= start_time,
            MemoryDetail.content_time <= end_time,
            MemoryDetail.tag == MemoryDetailType.Diary,
            MemoryDetail.assistant_name.in_(roles),
        )

        records = self.db.scalars(stmt).all()
        if len(records) == 0:
            logger.warning(f"[{owner}] 由于没有可用日记, 流言蜚语传播计算取消")
            return False

        diaries = []
        for r in records:
            name = r.assistant_name
            desc = self.role_manager.get_role(name=r.assistant_name).short_desc
            text = r.content
            diaries.append(f"{name}({desc}): {text}")

        diary_text = "\n".join(diaries)
        # 根据所有人的日记获得一个用户全天行为的客观描述
        prompt = RumorMemoryPrompt.format(diary_text=diary_text)
        reason, content = self.client.generate_one_shot(prompt)
        if not content:
            logger.warning(f"{owner}: 流言蜚语计算, 模型返回为空")
            return False

        detail = make_memory_detail(
            content,
            reason=reason,
            assistant_name=self.RUMOR_ROLE_NAME,
            owner=owner,
            tag=MemoryDetailType.Rumor,
            content_time=start_time,
        )
        self.db.add(detail)
        self.db.commit()
        return True

    def query_rumor(self, owner: str) -> MemoryDetail | None:
        records = self.__query_lastest(self.RUMOR_ROLE_NAME, owner, MemoryDetailType.Rumor)
        return records[0] if records else None

    @staticmethod
    def split_markdown_by_heading(content: str) -> dict[str, str]:
        """
        将 Markdown 文件按一级标题（# 开头）切分为字典。
        返回:
            Dict[str, str]: 键为章节标题（去除 '# ' 前缀），值为章节内容（保留原始格式）
        """
        if content == "":
            return {}
        lines = content.splitlines()

        sections = {}
        current_title = None
        current_content = []

        # 正则匹配一级标题行：行首可选空白 + '# ' + 标题内容
        heading_pattern = re.compile(r"^\s*#\s+(.*)$")

        for line in lines:
            match = heading_pattern.match(line)
            if match:
                # 遇到新标题，保存上一个章节
                if current_title is not None:
                    sections[current_title] = "\n".join(current_content).rstrip("\n")
                # 开始新章节
                current_title = match.group(1).strip()  # 标题文本（去除两侧空白）
                current_content = []
            else:
                # 非标题行，添加到当前章节内容
                if current_title is not None:
                    current_content.append(line)

        # 处理最后一个章节
        if current_title is not None:
            sections[current_title] = "\n".join(current_content).rstrip("\n")

        return sections

    def parse_markdown_item(
        self, details: dict[str, str], assistant_name: str, owner: str
    ) -> tuple[Sequence[MemoryDetail], str]:
        content_time = today_begin() - timedelta(days=1)

        ans = []
        err = ""
        configs = {
            "新增设定": (MemoryDetailType.RoleSetting, ),
            "用户偏好": (MemoryDetailType.RoleSetting, ),
            "近期话题": (MemoryDetailType.RecentTopic, ),
            "个人日记": (MemoryDetailType.Diary, ),
        }
        for key, config in configs.items():
            value = details.get(key)
            if not value:
                err += f"{key}提取失败 "
                continue

            value = value.strip()
            if not value:
                # 可能出现这种情况, 先打日志看看表现
                logger.info(f"[{owner}:{assistant_name}] 提取{key}内容为空")
                continue

            item = make_memory_detail(
                value,
                assistant_name=assistant_name,
                owner=owner,
                tag=config[0],
                content_time=content_time,
            )
            ans.append(item)

        return ans, err

    def stabilize_role_setting(self, *, content: str, assistant_name: str, owner: str):
        detail = make_memory_detail(
            content,
            reason="手动设置",
            assistant_name=assistant_name,
            owner=owner,
            tag=MemoryDetailType.FixedSetting,
            content_time=now(),
        )
        self.db.add(detail)
        self.db.commit()

    def stabilize_preference(self, *, content: str, assistant_name: str, owner: str):
        detail = make_memory_detail(
            content,
            reason="手动设置",
            assistant_name=assistant_name,
            owner=owner,
            tag=MemoryDetailType.FixedPreference,
            content_time=now(),
        )
        self.db.add(detail)
        self.db.commit()

    def set_process_time(self, *, content: str, assistant_name: str, owner: str, reason="手动设置"):
        detail = make_memory_detail(
            content,
            reason=reason,
            assistant_name=assistant_name,
            owner=owner,
            tag=MemoryDetailType.StartTime,
            content_time=now(),
        )
        self.db.add(detail)
        self.db.commit()


class AssistantManager:
    def __init__(self, cm: ConfigManager, trm: TomatoRecordManager) -> None:
        self.role_manager = RoleManager()

        self.config_manager = cm
        self.llm_manager = LLMClient(cm)

        self.tomato_record_manager = trm
        self.item_manager = trm.item_manager
        self.history_manager = AssistantHistoryManager(self.item_manager.db)
        self.memory_manager = AssistantMemoryManager(
            self.item_manager.db, self.role_manager, self.llm_manager, self.history_manager
        )
        self.event_manager = self.item_manager.event_manager

        # 执行一些其他初始化逻辑
        self.print_check_info()

    def print_check_info(self):
        logger.info(f"当前是生产环境?: {self.config_manager.is_production()}")

    def make_system_prompt(self, status: Status) -> ChatCompletionSystemMessageParam:
        config = self.role_manager.get_role(name=status.assistant_name)
        desc = config.get_self_desc()
        if status.assistant_mode == AssistantModeType.RolePlaying:
            return ChatCompletionSystemMessageParam(role="system", content=RolePalyingSp.format(role_desc=desc))

        return ChatCompletionSystemMessageParam(role="system", content=AssistantSp.format(role_desc=desc))

    def get_history(self, owner: str) -> list[ChatCompletionMessageParam]:
        status = self.history_manager.query_or_init_status(owner)
        sp = self.make_system_prompt(status)
        memory = self.memory_manager.query_memory_detail(status.assistant_name, owner)
        start_time = self.memory_manager.query_msg_start_time(status.assistant_name, owner)
        records = self.history_manager.select_record_between(status.assistant_name, start_time, now(), owner)

        if not memory:
            return [sp] + [msg.to_openai() for msg in records]

        mp = ChatCompletionUserMessageParam(role="user", content=memory)
        return [sp, mp] + [msg.to_openai() for msg in records]

    def generate(self, owner: str, *, enable_tools=False) -> Iterator[str]:
        """流式生成回复：后台消费 LLM 流并保存，前台推送给客户端"""
        if not enable_tools:
            history = self.get_history(owner)
            stream = self.llm_manager.generate_stream(history)
            yield from self._consume_simple_stream(stream, owner)
        else:
            yield from self._consume_tool_stream(owner)

    def _consume_simple_stream(self, stream: Iterator[str], owner: str) -> Iterator[str]:
        """消费简单模式的流"""
        full_answer = []
        try:
            for token in stream:
                full_answer.append(token)
                yield token
        except GeneratorExit as e:
            logger.error(f"推送LLM模型消息到客户端中断: {e}")
            # 继续消费上游数据, 确保已经生成的内容依然可以落库
            for token in stream:
                full_answer.append(token)
        except Exception as e:
            # 发生其他异常时，先尝试发送错误信息（如果客户端还在）
            logger.error(f"推送LLM模型消息到客户端异常: {e}")
            yield str(e)
        finally:
            content = "".join(full_answer)
            self.history_manager.add_assistant_answer(content, owner)

    def _consume_tool_stream(self, owner: str) -> Iterator[str]:
        tool_desc, tool_map = self.make_tools(owner)

        while True:
            tool_calls_list = []
            full_answer = []
            history = self.get_history(owner)
            stream = self.llm_manager.generate_steam_with_tools(history, tool_desc, tool_calls_list)
            for token in stream:
                full_answer.append(token)
                yield token
            if not full_answer:
                return

            content = "".join(full_answer)
            if tool_calls_list:
                list_josn = json.dumps(tool_calls_list)
                self.history_manager.add_assistant_answer(content, owner, tool_call_list_json=list_josn)
                # 执行工具调用
                for tc in tool_calls_list:
                    name = tc["function"]["name"]
                    if name in tool_map:
                        result = tool_map[name](tc["function"]["arguments"])
                        self.history_manager.add_tool_call_msg(tc["id"], result, owner=owner)
                # 继续循环
            else:
                # 没有工具调用可以结束循环
                self.history_manager.add_assistant_answer(content, owner)
                return

    def make_tools(self, owner: str) -> tuple[Sequence[ChatCompletionToolUnionParam], dict[str, Callable[[str], str]]]:
        def create_f(arg_json: str) -> str:
            try:
                args: dict[str, str] = json.loads(arg_json)
                item = Item(
                    name=args.get("name"),
                    item_type="single",
                    owner=owner,
                    deadline=get_datetime_from_str(args.get("deadline", "")),
                    priority=args.get("priority"),
                )
                self.item_manager.create(item)
                self.item_manager.db.commit()
            except Exception as e:
                logger.exception(e)
                return f"error: {e}"
            return "success"

        def query_f(arg_json: str) -> str:
            try:
                args: dict[str, str] = json.loads(arg_json)
                role_name = args.get("name", "")
                question = args.get("question", "")
                if role_name == "" or question == "":
                    return f"查询信息不完整. name={role_name}, question={question}"
                # TODO: 角色名存在校验
                config = self.role_manager.get_role(name=role_name)
                short_info = f"{config.name}({config.short_desc})"
                prompt = AnyQueryPrompt.format(role_short_info=short_info, question=question)
                content = self.llm_manager.generate_one_shot_with_history(prompt, f"{owner}_AnyQ", simple_client=True)
                logger.info(f"[{config.name}] 提问 [{question}] 获得回答 [{content}]")
                return content or "查询结果为空"
            except Exception as e:
                logger.exception(e)
                return f"error: {e}"

        def get_deadline_f(arg_json: str) -> str:
            try:
                groups = self.item_manager.get_deadline_item(owner)
                if not groups:
                    return "当前没有过期的待办事项。"
                lines = ["以下是所有过期的待办事项（按分组展示）：", ""]
                idx = 1
                for group in groups:
                    parent = group.get("self", {})
                    children = group.get("children", [])
                    group_name = parent.get("name", "全局任务")
                    lines.append(f"【分组: {group_name}】")
                    for d in children:
                        name = d.get("name", "(无名称)")
                        deadline = d.get("deadline", "(无截止时间)")
                        priority = d.get("priority", "(无优先级)")
                        lines.append(f"  {idx}. {name}")
                        lines.append(f"     截止时间: {deadline}")
                        lines.append(f"     优先级: {priority}")
                        idx += 1
                    lines.append("")
                return "\n".join(lines)
            except Exception as e:
                logger.exception(e)
                return f"error: {e}"

        return [CreatItemTool, AnyQueryTool, GetDeadlineItemTool], {
            "create_item": create_f,
            "query_info": query_f,
            "get_deadline_item": get_deadline_f,
        }

    def chat(self, prompt: str, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        config = self.role_manager.get_role(name=status.assistant_name)
        inject_content = self.make_user_inject_content(status, owner)
        self.history_manager.add_user_prompt(prompt, inject_content, owner)
        return self.generate(owner, enable_tools=bool(config.enable_tools))

    def remake(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        config = self.role_manager.get_role(name=status.assistant_name)
        self.history_manager.remove_last_assistant(owner)
        return self.generate(owner, enable_tools=bool(config.enable_tools))

    def delete(self, num: int, owner: str) -> bool:
        if num < 1:
            return False

        for _ in range(num):
            self.history_manager.remove_last_pair(owner)
        return True

    def replace(self, prompt: str, owner: str) -> Iterator[str]:
        self.history_manager.remove_last_pair(owner)
        return self.chat(prompt, owner)

    def auto_switch(self, *, role_keyword: str, owner: str) -> Iterator[str]:
        config = self.role_manager.get_role(keyword=role_keyword)
        self.history_manager.switch(role_config=config, owner=owner)
        yield f"切换到角色: {config.name}"

    def change_mode(self, role_mode: int, owner: str) -> Iterator[str]:
        self.history_manager.change_mode(role_mode, owner)
        yield f"切换到模式: {assistant_mode_str(role_mode)}"

    def make_user_inject_content(self, status: Status, owner: str) -> str:
        # 扮演模式不注入任何系统相关的信息
        if status.assistant_mode == AssistantModeType.RolePlaying:
            return ""

        # 非扮演模式查询具体的状态信息
        # 当前番茄钟状态
        start = self.history_manager.get_last_assistant_mode_time(status)
        state = self.tomato_record_manager.get_tomato_state(owner=owner)
        content = f"番茄钟状态: {state}\n"

        # 事件信息, 可能没有事件
        # 如果已经跨越了1天时间, 则昨天产生的信息不再继续追加到当前会话中
        start = tb if (tb := today_begin()) > start else start
        event_info = self.get_event_info(owner, start)
        if event_info != "":
            content += "用户新增的事件记录:\n" + event_info

        return content

    def get_role_info_list(self) -> Iterator[str]:
        raw_list = self.role_manager.get_role_list()
        for role in raw_list:
            name = role.name
            desc = role.short_desc
            yield f"{name}: {desc}\n"

    def show_cost(self, owner: str) -> Iterator[str]:
        head = "角色: 记忆字符数+对话字符数（轮数）= 总字符数(预计token数)"
        report = [head]
        names = self.history_manager.get_recent_assistant_list(owner)
        for name in names:
            memory_cost = len(self.memory_manager.query_memory_detail(name, owner))
            start_time = self.memory_manager.query_msg_start_time(name, owner)
            records = self.history_manager.select_record_between(name, start_time, now(), owner)
            char_cost = sum(len(s) for r in records if (s := r.to_dump()))
            conv_cnt = len(records) // 2
            all_char_cost = memory_cost + char_cost
            token_cost = (memory_cost + char_cost) * 1.5
            delta_times = format_timedelta(now() - start_time)
            txt = f"{name:>8s}: {memory_cost / 1024:2.1f}KB+{char_cost // 1024:3d}KB({conv_cnt:3d}轮)={all_char_cost // 1024:3d}KB({token_cost / 1024:3.1f}K) / {delta_times} "
            report.append(txt)
        yield "\n".join(report)

        head = "\n\n当前角色成本明细:"
        report = [head]
        state = self.history_manager.query_or_init_status(owner)
        start_day = now() - timedelta(days=14)
        rows = self.history_manager.evalute_day_cost(state.assistant_name, start_day, owner)
        report.extend([f"{d}: {total_cnt / KB:6.2f} KB / {msg_cnt // 2:4d} Msg" for d, total_cnt, msg_cnt in rows])
        yield "\n".join(report)

    def show_memory(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        start_time = self.memory_manager.query_msg_start_time(status.assistant_name, owner)
        content = f"原始对话起始时间: {get_str_from_datetime(start_time)}\n"
        content += self.memory_manager.query_memory_detail(status.assistant_name, owner)
        yield content

    def show_last_reason(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        memory_reason = self.memory_manager.query_last_reason(status.assistant_name, owner)

        rumor_detail = self.memory_manager.query_rumor(owner)
        rumor_reason = rumor_detail.reason if rumor_detail else ""

        content = f"压缩记忆: \n{memory_reason}\n\n流言蜚语: \n {rumor_reason}"
        yield content

    def new_topic(self, owner: str) -> Iterator[str]:
        inject = "你需要根据现有的近期话题主动发起一个新话题"
        self.history_manager.add_user_prompt("", inject, owner, tag=AssistantTagType.NewTopic)
        yield from self.generate(owner)

    def set_memory(self, memory_type: str, content: str, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        if memory_type == "设定":
            self.memory_manager.stabilize_role_setting(
                content=content, assistant_name=status.assistant_name, owner=owner
            )
        elif memory_type == "偏好":
            self.memory_manager.stabilize_preference(content=content, assistant_name=status.assistant_name, owner=owner)

        yield from self.show_memory(owner)

    def set_time(self, time_str: str, owner: str) -> Iterator[str]:
        """设置原始聊天上下文起始时间, 支持待办事项截止日期相同格式的时间, 或者字符串'now'表示设置为当前时间"""
        if time_str == "now":
            content = now_str()
        else:
            t = parse_befeore_time_str(time_str)
            content = get_str_from_datetime(t)
        status = self.history_manager.query_or_init_status(owner)
        self.memory_manager.set_process_time(content=content, assistant_name=status.assistant_name, owner=owner)
        yield from self.show_memory(owner)

    def dump_memory(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        yield self.memory_manager.dump_memory_detail(status.assistant_name, owner)

    def dump_tool(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        msgs = self.history_manager.select_recent_tool_call_msgs(status.assistant_name, 3, owner)
        if not msgs:
            yield "最近没有工具调用记录"
            return

        lines: list[str] = []
        for i, msg in enumerate(msgs):
            lines.append(f"--- 工具调用 #{i + 1} ---")
            lines.append(f"时间: {get_str_from_datetime(msg.create_time)}")
            for tc in json.loads(msg.tool_call_list_json):
                name = tc["function"]["name"]
                args = tc["function"]["arguments"]
                lines.append(f"调用: {name}({args})")
                result = self.history_manager.select_tool_result_msg(tc["id"])
                if result:
                    lines.append(f"返回: {result.content}")
            lines.append("")
        content = "\n".join(lines)
        yield content

    def rumor(self, owner: str) -> Iterator[str]:
        yestoday = today_begin() - timedelta(days=1)
        yield "正在生成流言蜚语\n"
        self.memory_manager.rumor_propagation(yestoday, owner)
        rumor = self.memory_manager.query_rumor(owner)
        yield rumor.content if rumor else ""

    def rumor_propagation(self, target_keyword: str, owner: str) -> Iterator[str]:
        rumor_detail = self.memory_manager.query_rumor(owner)
        if not rumor_detail:
            yield "当前没有流言蜚语"
            return

        target = ""
        if target_keyword:
            target = f"用户要求你关注{target_keyword}相关的流言蜚语."

        inject_content = InjectRumorPrompt.format(target=target, rumor_text=rumor_detail.content)
        self.history_manager.add_user_prompt("", inject_content, owner, tag=AssistantTagType.Rumor)

        status = self.history_manager.query_or_init_status(owner)
        config = self.role_manager.get_role(name=status.assistant_name)
        yield from self.generate(owner, enable_tools=config.enable_tools)

    def inject(self, inject_data: str, user_prompt: str, owner: str) -> Iterator[str]:
        self.history_manager.add_user_prompt(user_prompt, inject_data, owner)
        yield from self.generate(owner)

    def __is_zero_tomoto_task(self, name: str) -> bool:
        # 打卡类任务可瞬间完成无需番茄钟.  午间和晚间任务不占用番茄钟
        keywords = ["打卡", "午间", "晚间"]
        return any(word in name for word in keywords)

    def get_event_info(self, owner: str, begin_time: datetime) -> str:
        content = ""
        # 新增番茄钟记录
        events = self.event_manager.get_event_log_after(begin_time, owner)
        for e in events:
            content += f"{get_hour_str_from(e.create_time)}: {e.msg}\n"

        return content

    def get_web_history(self, owner: str) -> list[dict]:
        status = self.history_manager.query_or_init_status(owner)
        start_time = self.memory_manager.query_msg_start_time(status.assistant_name, owner)
        records = self.history_manager.select_record_between(status.assistant_name, start_time, now(), owner)

        data_after = self.history_manager.to_web_json_list(records)
        div = [{"type": "divider", "label": "以上对话已压缩至记忆"}]

        data_before = self.history_manager.get_more_web_history(start_time, owner)
        if data_before:
            return data_before + div + data_after
        else:
            return data_after

    def get_more_web_history(self, end_time_str: str, owner: str) -> list[dict]:
        if end_time_str == "":
            return []

        end_time = get_datetime_from_str(end_time_str)
        return self.history_manager.get_more_web_history(end_time=end_time, owner=owner)

    def dump_user_prompt(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        mode = assistant_mode_str(status.assistant_mode)
        config = self.role_manager.get_role(name=status.assistant_name)
        content = (
            f"【当前状态信息】\n角色名: {status.assistant_name}\n角色模式: {mode}\n角色描述: {config.short_desc}\n"
        )

        rumor = self.memory_manager.query_rumor(owner)
        rumor_text = rumor.content if rumor else ""
        content += f"\n【流言蜚语】\n{rumor_text}\n"

        records = self.history_manager.select_inject_history(status.assistant_name, 4, owner)
        content += "\n【最近几条注入信息】\n"
        content += "\n".join([r.system_inject_content for r in reversed(records)])

        to_inject_content = self.make_user_inject_content(status, owner)
        content += f"\n\n【即将注入的信息】\n{to_inject_content}\n"

        yield content

    def auto_update_memory(self):
        if not self.config_manager.is_production():
            logger.info("非生产环境, 取消记忆压缩任务执行")
            return

        users = self.config_manager.get_all_users()
        start_time = today_begin() - timedelta(days=1)
        for user in users:
            # 检查该用户所有助理的历史对话长度, 更新满足要求的助理的记忆
            for role in self.history_manager.get_recent_assistant_list(user):
                config = self.role_manager.get_role(name=role)
                self.memory_manager.update_long_term_memory(config=config, owner=user)
            # 基于已经更新的日记, 计算用户行为轨迹, 作为流言蜚语传播的素材
            self.memory_manager.rumor_propagation(start_time, user)

    def debug_update_memory(self) -> Iterator[str]:
        yield "正在执行记忆压缩操作\n"
        self.auto_update_memory()
        yield "记忆压缩完毕\n"
