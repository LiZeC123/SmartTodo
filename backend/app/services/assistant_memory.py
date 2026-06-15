import json
import random
import re
from collections.abc import Sequence
from datetime import datetime, timedelta

import sqlalchemy as sal
from sqlalchemy.orm import Session, scoped_session

from app.models.memory import KB, MemoryDetail, MemoryDetailType, MemoryPolicy, MinCompressionSize, make_memory_detail
from app.services.assistant_history import AssistantHistoryManager
from app.services.role_manager import RoleConfig, RoleManager
from app.template.prompt import LongTermMemoryPrompt, RumorMemoryPrompt
from app.tools.llm import LLMClient
from app.tools.log import logger
from app.tools.time import get_datetime_from_str, get_str_from_datetime, now, the_day_begin, today_begin


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

        # 话题和日记仅提取当前原始对话中不包含的, 避免重复信息太多
        end_time = the_day_begin(self.query_msg_start_time(assistant_name, owner))
        if policy.max_topic_num > 0:
            topic: str = self.query_topic(policy.max_topic_num, end_time, assistant_name, owner)
            content += f"# 近期话题\n{topic}\n" if topic else ""

        if policy.max_diary_num > 0:
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

        end_time = now()
        topic: str = self.query_topic(15, end_time, assistant_name, owner)
        content += f"# 近期话题\n{topic}\n\n" if topic else ""

        diary: str = self.query_diary(5, end_time, assistant_name, owner)
        content += f"# 角色近期日记\n{diary}\n\n" if diary else ""

        return content

    def query_topic(self, topic_num: int, end_time: datetime, assistant_name: str, owner: str) -> str:
        if topic_num < 1 or topic_num > 15:
            topic_num = 1

        stmt = (
            sal.select(MemoryDetail)
            .where(
                MemoryDetail.owner == owner,
                MemoryDetail.assistant_name == assistant_name,
                MemoryDetail.tag == MemoryDetailType.RecentTopic,
                MemoryDetail.content_time < end_time,
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

        self.db.flush()

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
        self.db.flush()
        return True

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
            "新增设定": (MemoryDetailType.RoleSetting,),
            "用户偏好": (MemoryDetailType.Preference,),
            "近期话题": (MemoryDetailType.RecentTopic,),
            "个人日记": (MemoryDetailType.Diary,),
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
        self.db.flush()

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
        self.db.flush()

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
        self.db.flush()
