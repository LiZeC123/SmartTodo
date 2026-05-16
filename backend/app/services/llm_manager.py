import json
import random
import re
from collections.abc import Callable, Generator, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

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
    AssistantType,
    History,
    Memory,
    Status,
    assistant_mode_str,
    make_assistant_status,
)
from app.models.item import Item
from app.models.tomato import TomatoTaskRecord
from app.services.config_manager import ConfigManager
from app.services.event_log_manager import get_event_log_after
from app.services.item_manager import ItemManager
from app.services.tomato_manager import TomatoManager, TomatoRecordManager
from app.template.prompt import (
    AnyQueryPrompt,
    AssistantSp,
    LongTermMemoryPrompt,
    RolePalyingSp,
    RumorMemoryPrompt,
    RumorMillPrompt,
)
from app.template.tools import AnyQueryTool, CreatItemTool
from app.tools.llm import LLMClient
from app.tools.log import logger
from app.tools.time import (
    format_timedelta,
    get_datetime_from_str,
    get_hour_str_from,
    now,
    parse_befeore_time_str,
    today_begin,
)


@dataclass
class RoleConfig:
    name: str               # 角色姓名
    enable_tools: bool      # 是否允许调用工具
    memory_compress: str    # 记忆压缩策略
    enable_rumor: bool      # 是否启用流言蜚语系统(获得流言蜚语信息)
    visible_in_rumor: bool  # 是否在流言蜚语系统中可见(可以产生传闻并被其他角色获知)
    short_desc: str         # 角色的简短描述
    long_desc: str          # 角色的详细设定

    def get_desc(self):
        return f"你是一位{self.short_desc}, 名叫{self.name}. {self.long_desc}"

@dataclass
class CompressionPolicy:
    day_delta: int
    char_cost: int

KB = 1024

AggressivePolicy = CompressionPolicy(day_delta=1, char_cost=3*KB)
ModeratePolicy = CompressionPolicy(day_delta=1, char_cost=6*KB)
LazyPolicy = CompressionPolicy(day_delta=1, char_cost=10*KB)

MinCompressionSize = 5*KB


class RoleManager:
    def __init__(self) -> None:
        pass

    def __load_file(self) -> list[RoleConfig]:
        with open("config/role/Assistant.jsonl") as f:
            return [RoleConfig(**json.loads(s)) for role in f if (s:=role.strip()) != "" and not s.startswith("//")]

    def get_role_list(self) -> list[RoleConfig]:
        try:
            return self.__load_file()
        except OSError:
            # 文件不存在时, 直接返回空即可, 相当于没有额外的角色设定
            return []

    def get_role_map(self) -> dict[str, RoleConfig]:
        return {item.name: item for item in self.get_role_list()}

    def get_role(self, role_keyword: str) -> RoleConfig:
        roles =self.get_role_list()
        if len(roles) == 0:
            logger.warning('角色列表为空, 加载默认角色')
            return RoleConfig(name='默认助手', enable_tools=False, memory_compress='No', enable_rumor=False, visible_in_rumor=False, short_desc='有用的助手.', long_desc='')

        random_role = random.choice(roles)
        if role_keyword == "":
            return random_role

        it = (role for role in roles if role_keyword in role.get_desc())
        return next(it, random_role)

    def get_compression_policy(self, policy: str) -> CompressionPolicy:
        if policy == 'Aggressive':
            return AggressivePolicy
        if policy == 'Lazy':
            return LazyPolicy

        return ModeratePolicy



class AssistantHistoryManager:
    def __init__(self, db: scoped_session[Session]) -> None:
        self.db = db

    def add_user_prompt(self, prompt: str, inject: str, owner:str, *, tag:int=0):
        status = self.query_or_init_status(owner)
        msg = History(role='user', content=prompt, system_inject_content=inject, owner=owner,
                               assistant_name=status.assistant_name, assistant_mode=status.assistant_mode, tag=tag)
        self.db.add(msg)
        self.db.flush()
        self.db.commit()

    def add_assistant_answer(self, content: str,owner:str, *, tool_call_list_json='', tag:int=0):
        status = self.query_or_init_status(owner)
        msg = History(role='assistant', content=content, owner=owner,
                               assistant_name=status.assistant_name, assistant_mode=status.assistant_mode,
                               tool_call_list_json=tool_call_list_json, tag=tag)
        self.db.add(msg)
        self.db.flush()
        self.db.commit()

    def add_tool_call_msg(self, tool_call_id: str, content: str, *, owner: str, tag:int=0):
        status = self.query_or_init_status(owner)
        msg = History(role='tool', tool_call_id=tool_call_id, content=content, owner=owner,
                               assistant_name=status.assistant_name, assistant_mode=status.assistant_mode,
                               tag=tag)
        self.db.add(msg)
        self.db.flush()
        self.db.commit()

    def switch(self, /, role_config: RoleConfig, owner:str):
        status = self.query_or_init_status(owner)
        status.assistant_name = role_config.name
        status.assistant_desc = role_config.get_desc()
        status.enable_tools = role_config.enable_tools

        msg = self.select_last_msg(role_config.name, owner)
        role_mode = msg.assistant_mode if msg  else AssistantModeType.RolePlaying
        status.assistant_mode = role_mode

        self.db.flush()
        self.db.commit()

    def change_mode(self, role_mode: int, owner: str):
        status = self.query_or_init_status(owner)
        status.assistant_mode = role_mode
        self.db.flush()
        self.db.commit()

    def add_user_inject(self, content: str, role_name: str, owner: str):
        last_msg = self.select_last_msg(role_name, owner)
        role_mode = last_msg.assistant_mode if last_msg  else AssistantModeType.RolePlaying

        msg = History(role='user', content='', system_inject_content=content, owner=owner,
                               assistant_name=role_name, assistant_mode=role_mode, tag=1)
        self.db.add(msg)
        self.db.flush()
        self.db.commit()

    def remove_last_assistant(self, owner: str) -> bool:
        status = self.query_or_init_status(owner)
        last =  self.select_last_msg(status.assistant_name, owner)
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
        last =  self.select_last_msg(status.assistant_name, owner)
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
            last =  self.select_last_msg(status.assistant_name, owner)
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


    def select_last_msg(self, assistant_name: str,  owner: str) -> History | None:
        """查询指定角色最后一条消息"""
        stmt = sal.select(History).where(History.owner==owner, History.assistant_name==assistant_name).order_by(History.id.desc()).limit(1)
        return self.db.scalar(stmt)

    def get_last_assistant_mode_time(self, status:Status) -> datetime:
        # 查询当前助手上一次助手模式的记录时间, 在非助手模式或者其他助手对话过程中产生的记录对当前助手来说是没有见过的
        stmt = sal.select(History).where(History.owner==status.owner,
                                                  History.assistant_mode==AssistantModeType.Assistant,
                                                  History.assistant_name==status.assistant_name).order_by(History.id.desc()).limit(1)
        last = self.db.scalar(stmt)
        if last is None:
            return today_begin()
        else:
            return last.create_time

    def select_record(self, owner:str) -> tuple[Status, Memory | None, Iterable[History]]:
        # 查询当前角色自从上次记忆压缩后的聊天记录
        status = self.query_or_init_status(owner)

        stmt = sal.select(Memory).where(Memory.assistant_name==status.assistant_name,Memory.owner==owner).order_by(Memory.id.desc()).limit(1)
        memory = self.db.scalar(stmt)

        if memory is not None:
            start_time = memory.processed_time
        else:
            start_time = today_begin() - timedelta(days=2)
        stmt = sal.select(History) \
                  .where(History.owner == owner, History.create_time > start_time,
                         History.assistant_name == status.assistant_name)
        return (status, memory, self.db.scalars(stmt))

    def select_record_after(self, role_name: str, start_time:datetime, owner: str) -> Iterable[History]:
        stmt = sal.select(History)\
                  .where(History.owner == owner, History.create_time > start_time,
                         History.assistant_name == role_name)
        return self.db.scalars(stmt)

    def select_record_between(self, role_name: str, start_time:datetime, end_time:datetime, owner: str) -> Sequence[History]:
        stmt = sal.select(History)\
                  .where(History.owner == owner, History.assistant_name == role_name,
                         History.create_time > start_time, History.create_time < end_time)
        return self.db.scalars(stmt).all()

    def get_history(self, owner:str)-> list[ChatCompletionMessageParam]:
        status, memory, records = self.select_record(owner)
        sp = self.make_system_prompt(status)

        if memory is None:
            return [sp] + [msg.to_openai() for msg in records]

        mp = ChatCompletionUserMessageParam(role='user',content=memory.to_assistant())
        return [sp, mp] + [msg.to_openai() for msg in records]

    def get_web_history(self, owner: str) -> list[dict]:
        status, memory, records = self.select_record(owner)
        if memory is None:
            return self.to_web_json_list(records)

        start = memory.processed_time - timedelta(days=1)
        records_before = self.select_record_between(status.assistant_name, start, memory.processed_time, owner)
        data_before = self.to_web_json_list(records_before)
        data_after = self.to_web_json_list(records)
        div = [{'type': 'divider', 'label': '以上对话已压缩至记忆'}]

        if data_before:
            return data_before + div + data_after
        else:
            return data_after

    def get_more_web_history(self, end_time: datetime,  owner: str) -> list[dict]:
        status = self.query_or_init_status(owner)
        stmt = sal.select(History)\
                  .where(History.owner == owner, History.create_time < end_time,
                         History.assistant_name == status.assistant_name).order_by(History.id.desc()).limit(20)
        records = reversed(self.db.scalars(stmt).all())
        return self.to_web_json_list(records)

    @staticmethod
    def to_web_json(msg: History):
        return {'role': msg.role, 'content': msg.to_web(), 'createTime': msg.create_time.strftime("%Y-%m-%d %H:%M:%S")}

    def to_web_json_list(self, records: Iterable[History]):
        return self.post_merging([self.to_web_json(msg) for msg in records if msg.role in [AssistantType.User, AssistantType.Assistant]])

    def post_merging(self, records: list[dict]):
        if len(records) == 0:
            return records

        last = records[0]
        rst = [last]
        for rec in records[1:]:
            this_role = rec.get('role')
            if this_role == AssistantType.Assistant and last.get('role') == AssistantType.Assistant:
                last['content'] += rec.get('content')
            else:
                rst.append(rec)
                last = rec
        return rst

    def evalute_day_cost(self, role_name: str, start_day: datetime, owner: str) -> list[tuple[str, int, int]]:
        stmt = sal.select(sal.func.date(History.create_time).label("stat_date"),
                          sal.func.sum(sal.func.length(History.content) +sal.func.length(History.system_inject_content)).label("total_chars"),
                          sal.func.count().label('msg_count')) \
                  .where(History.owner == owner,History.assistant_name == role_name, History.create_time > start_day) \
                  .group_by(sal.func.date(History.create_time)) \
                  .order_by(sal.desc("stat_date"))
        records = self.db.execute(stmt)
        return [(r.stat_date, r.total_chars, r.msg_count) for r in records]


    def day_cost_report(self, role: str,  owner: str) -> str:
        start_day = now() - timedelta(days=14)
        rows = self.evalute_day_cost(role, start_day, owner)
        return "\n".join([f"{d}: {total_cnt / KB:6.2f} KB / {msg_cnt // 2:4d} Msg" for d, total_cnt, msg_cnt in rows])

    def make_system_prompt(self, status: Status) -> ChatCompletionSystemMessageParam:
        if status.assistant_mode == AssistantModeType.RolePlaying:
            return ChatCompletionSystemMessageParam(role="system", content=RolePalyingSp.format(role_desc=status.assistant_desc))

        return ChatCompletionSystemMessageParam(
            role="system",
            content=AssistantSp.format(role_desc=status.assistant_desc)
        )



class AssistantMemoryManager:
    def __init__(self, db: scoped_session[Session], llm_client: LLMClient, history_manager: AssistantHistoryManager) -> None:
        self.db = db
        self.config_manager = ConfigManager()
        self.role_manager = RoleManager()
        self.cliet = llm_client
        self.history_manager = history_manager

    def query_or_init_memory(self, role_name:str, owner:str) -> Memory:
        stmt = sal.select(Memory).where(Memory.assistant_name==role_name,Memory.owner==owner).order_by(Memory.id.desc()).limit(1)
        t = self.db.scalar(stmt)
        if t is None:
            t = Memory(assistant_name=role_name, owner=owner)
            self.db.add(t)
            self.db.flush()
            self.db.commit()
        return t

    def update_long_term_memory(self, *, config: RoleConfig, owner: str) -> bool:
        policy = self.role_manager.get_compression_policy(config.memory_compress)
        memory = self.query_or_init_memory(config.name, owner)

        # 获取当前角色按照天统计的成本, 计算累计值达到阈值的日期
        acc_count = 0
        end_time = None
        cost_records = self.history_manager.evalute_day_cost(config.name, memory.processed_time, owner)
        for day, day_cost, _ in cost_records:
            acc_count += day_cost
            if acc_count > policy.char_cost:
                t = datetime.strptime(day, '%Y-%m-%d')
                end_time = datetime(year=t.year, month=t.month, day=t.day)
                break
        if end_time is None:
            logger.info(f"[{owner}:{config.name}]: 跳过压缩, 当前角色剩余对话长度 {acc_count / KB:.2f} KB < 目标阈值 {policy.char_cost / KB:.2f} KB")
            return False

        # 查询需要压缩的记录, 判断是否满足记忆压缩策略
        records = self.history_manager.select_record_between(config.name, memory.processed_time, end_time, owner)
        cost = sum(len(s) for r in records if (s := r.to_dump()) is not None)
        if cost < MinCompressionSize:
            logger.info(f"[{owner}:{config.name}]: 跳过压缩, 当前待压缩对话长度 {cost / KB:.2f} KB < 最小压缩长度 {MinCompressionSize / KB:.2f} KB")
            return False

        # 执行压缩操作
        logger.info(f"[{owner}:{config.name}]: 执行压缩, 当前角色剩余对话长度 {acc_count / KB:.2f} KB , 待压缩对话长度 {cost / KB:.2f} KB")
        new_content = "\n".join([json.dumps(r.to_openai(), ensure_ascii=False) for r in records])
        prompt = LongTermMemoryPrompt.format(role_desc=config.get_desc(), old_memory=memory.long_term_memory, new_content=new_content)
        reason, content = self.cliet.generate_one_shot(prompt)

        # 更新记忆
        new_memory = memory.deep_copy(processed_time=end_time)
        new_memory.compression_reason = reason if reason else ''
        if content is not None:
            new_memory.long_term_memory = content
            self.db.add(new_memory)
            self.db.commit()
            logger.info(f"[{owner}:{config.name}] 记忆压缩完毕, 新记忆长度为 {len(content)/KB:.2f} KB, 思考长度为 {len(new_memory.compression_reason) / KB:.2f} KB")
            return True
        else:
            logger.warning(f'[{owner}:{config.name}]: 模型返回记忆为空')
            return False

    def auto_update_memory(self):
        users = self.config_manager.get_all_users()
        for user in users:
            # 检查该用户所有助理的历史对话长度, 更新满足要求的助理的记忆
            for role in self.get_recent_assistant_list(user):
                config = self.role_manager.get_role(role)
                self.update_long_term_memory(config=config, owner=user)
            # 基于已经更新的记忆和最近的活跃助理, 传播流言蜚语
            self.rumor_propagation(owner=user)

    def rumor_propagation(self, owner: str):
        roles = self.get_recent_assistant_list(owner)
        if len(roles) == 0:
            return

        configs = self.role_manager.get_role_map()

        # 第一轮提取公共池数据
        names = []
        for role in roles:
            config = configs.get(role)
            if config is None:
                logger.warning(f'[{owner}:{role}] 无法获取角色配置')
                continue
            if not config.visible_in_rumor:
                logger.info(f'[{owner}:{role}] 当前角色不产生流言蜚语')
                continue
            names.append(role)

        idea_pool = self.get_memory_pool(names, configs, owner)
        if len(idea_pool) == 0:
            logger.warning(f"[{owner}] 由于没有公共记忆, 流言蜚语传播计算取消")
            return False

        # 第二轮计算昨日活跃角色扩散的流言蜚语
        roles = self.get_activate_assistant_names(owner)
        for role in roles:
            config = configs.get(role)
            if config is None:
                logger.warning(f'[{owner}:{role}] 无法获取角色配置')
                continue
            if not config.enable_rumor:
                logger.info(f'[{owner}:{role}] 当前角色不接受流言蜚语')
                continue

            prompt = RumorMemoryPrompt.format(idea_pool=idea_pool, role_desc=config.get_desc())
            reason, content = self.cliet.generate_one_shot(prompt)

            memory = self.query_or_init_memory(config.name, owner)
            memory.rumor_reason = reason if reason else ''
            if content:
                # 流言蜚语存储到短期记忆字段中, 默认不注入到对话之中
                # 还需要实验合理的触发时机
                memory.short_term_memory = content
                logger.info(f'[{owner}:{role}] 流言蜚语计算完毕, 长度为{len(memory.short_term_memory) / KB:.2f} KB, 思考长度为 {len(memory.rumor_reason) / KB:.2f} KB')
            else:
                logger.warning(f'[{owner}:{role}] 流言蜚语计算返回为空, 思考长度为 {len(memory.rumor_reason) / KB:.2f} KB')
            self.db.flush()
            self.db.commit()

    def get_memory_pool(self, role_names: list[str], configs: dict[str, RoleConfig], owner: str) -> str:
        # 子查询：按 assistant_name 分组，取每组最大 id
        sub =  sal.select(Memory.assistant_name, sal.func.max(Memory.id).label("max_id")) \
                  .where(Memory.assistant_name.in_(role_names), Memory.owner==owner) \
                  .group_by(Memory.assistant_name).subquery()

        stmt = sal.select(Memory).where(Memory.id == sub.c.max_id)

        lines = []
        for memory in self.db.scalars(stmt):
            config =configs.get(memory.assistant_name)
            if config is None:
                continue

            idea = self.extract_inner_thoughts(memory.long_term_memory)
            if idea == '':
                continue
            lines.append(f"{config.name}({config.short_desc}): {idea}")


        return "\n".join(lines)


    @staticmethod
    def extract_inner_thoughts(text: str) -> str:
        """
        从包含 '# 助手内心想法' 和 '# 新增设定' 的文本中提取中间内容。
        """
        # 非贪婪匹配两个标题之间的任意字符（包括换行）
        pattern = r'#\s*助手内心想法\s*(.*?)\s*#\s*新增设定'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            return content
        return ""



    # TODO: 实现
    def rollback_long_term_memory(self, *, role_name: str, owner: str) -> bool:
        return False

    # TODO: 实现
    def redo_long_term_memory(self, *, role_name: str, role_desc:str, end_time:datetime, owner: str) -> str:
        return ""

    # TODO: 实现
    def reset_long_term_memory(self, *, role_name: str, owner: str) -> bool:
        return False

    def inject_long_term_memory(self, *, memory_content: str,  role_name: str, owner: str):
        """从外部直接注入记忆"""
        memory = self.query_or_init_memory(role_name, owner)
        new_memory = memory.deep_copy(memory.processed_time)
        new_memory.long_term_memory = memory_content
        new_memory.compression_reason = '手动注入记忆'
        self.db.add(new_memory)
        self.db.commit()

    def reset_process_time(self, new_time: datetime,  role_name:str, owner:str) -> bool:
        # 修改处理时间未改动内容, 为了减少冗余直接修改当前记录
        # 因此无法直接回滚对时间的修改操作, 但是可以手动再次修改时间来恢复
        memory = self.query_or_init_memory(role_name, owner)
        memory.processed_time = new_time
        self.db.flush()
        self.db.commit()
        return True

    def get_activate_assistant_names(self, owner: str) -> Iterable[str]:
        """最近一天活跃的助理列表, 可能存在用户单方面插入的信息, 如果助手还未回复则不视为活跃"""
        start = now() - timedelta(days=1)
        stmt = sal.select(History.assistant_name.distinct()).where(History.owner==owner, History.create_time > start, History.role=='assistant')
        return self.db.scalars(stmt)

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
        names = result.scalars().all()   # 获得按照最近聊天顺序的列表
        return names

    def evaluate_cost(self, owner: str) -> str:
        names = self.get_recent_assistant_list(owner)
        head = "角色: 记忆字符数+对话字符数（轮数）= 总字符数(预计token数) / 对话累计时间\n"
        return head+"\n".join([self.evaluate_one_role_cost(name, owner) for name in names])

    def evaluate_one_role_cost(self, role_name: str, owner: str) -> str:
        memory = self.query_or_init_memory(role_name, owner)
        stmt = sal.select(History).where(History.owner == owner,
                                                  History.create_time > memory.processed_time,
                                                  History.assistant_name == role_name)
        records = self.db.scalars(stmt).all()

        memory_char_cost = len(memory.long_term_memory)
        char_cost = sum(len(s) for r in records if (s := r.to_dump()) is not None)
        token_cost = (memory_char_cost+char_cost) * 1.5
        conv_cnt = len(records)
        delta_times = format_timedelta(now()-memory.processed_time)

        return f"{role_name:>8s}: {memory_char_cost/1024:2.1f}KB+{char_cost // 1024:3d}KB({conv_cnt // 2:3d}轮)={(memory_char_cost+char_cost) // 1024:3d}KB({token_cost / 1024:3.1f}K) / {delta_times}"


class AssistantManager:
    def __init__(self, llm_manager: LLMClient, item_manager: ItemManager,
                 tomato_manager: TomatoManager, tomato_record_manager: TomatoRecordManager,
                 history_manager: AssistantHistoryManager, memory_manager: AssistantMemoryManager) -> None:
        self.llm_manager = llm_manager
        self.role_manager = RoleManager()
        self.item_manager = item_manager
        self.tomato_manager = tomato_manager
        self.tomato_record_manager = tomato_record_manager
        self.history_manager = history_manager
        self.memory_manager = memory_manager

    def generate(self, owner: str, *, enable_tools=False) -> Generator[str, Any]:
        """流式生成回复：后台消费 LLM 流并保存，前台推送给客户端"""
        if not enable_tools:
            history = self.history_manager.get_history(owner)
            stream = self.llm_manager.generate_stream(history)
            yield from self._consume_simple_stream(stream, owner)
        else:
            yield from self._comsume_tool_stream(owner)
            yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"

    def _consume_simple_stream(self, stream: Generator[str, Any], owner: str) -> Generator[str, Any]:
        """消费简单模式的流"""
        full_answer = []
        try:
            for token in stream:
                full_answer.append(token)
                yield f"data: {json.dumps({'text': token, 'done': False})}\n\n"
            yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"
        except GeneratorExit as e:
            logger.error(f'推送LLM模型消息到客户端中断: {e}')
            # 继续消费上游数据, 确保已经生成的内容依然可以落库
            for token in stream:
                full_answer.append(token)
        except Exception as e:
            # 发生其他异常时，先尝试发送错误信息（如果客户端还在）
            logger.error(f'推送LLM模型消息到客户端异常: {e}')
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        finally:
            content = "".join(full_answer)
            self.history_manager.add_assistant_answer(content, owner)

    def _comsume_tool_stream(self, owner: str) -> Generator[str, Any]:
        tool_desc, tool_map = self.make_tools(owner)

        while True:
            tool_calls_list = []
            full_answer = []
            history = self.history_manager.get_history(owner)
            stream = self.llm_manager.generate_steam_with_tools(history, tool_desc, tool_calls_list)
            for token in stream:
                full_answer.append(token)
                yield f"data: {json.dumps({'text': token, 'done': False})}\n\n"
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

    def make_tools(self, owner:str) -> tuple[Iterable[ChatCompletionToolUnionParam], dict[str, Callable[[str], str]]]:
        def create_f(arg_json:str) -> str:
            try:
                args:dict[str,str] = json.loads(arg_json)
                item = Item(name=args.get('name'), item_type='single', owner=owner,
                            deadline=get_datetime_from_str(args.get('deadline', '')),
                            priority=args.get('priority'))
                self.item_manager.create(item)
                self.item_manager.db.commit()
            except Exception as e:
                return f"error: {e}"
            return "success"

        def query_f(arg_json:str) -> str:
            try:
                args:dict[str,str] = json.loads(arg_json)
                role_name = args.get('name', '')
                question = args.get('question', '')
                if role_name == '' or question == '':
                    return f'查询信息不完整. name={role_name}, question={question}'
                config = self.role_manager.get_role(role_name)
                short_info = f"{config.name}({config.short_desc})"
                prompt = AnyQueryPrompt.format(role_short_info=short_info, question=question)
                content = self.llm_manager.generate_one_shot_with_history(prompt,f'{owner}_AnyQ', simple_client=True)
                logger.info(f'[{config.name}] 提问 [{question}] 获得回答 [{content}]')
                return content or '查询结果为空'
            except Exception as e:
                return f'error: {e}'

        return [CreatItemTool, AnyQueryTool], {"create_item": create_f, 'query_info': query_f}


    def chat(self, prompt: str, owner: str) ->  Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        inject_content = self.make_user_inject_content(status, owner)
        self.history_manager.add_user_prompt(prompt, inject_content, owner)
        return self.generate(owner, enable_tools=bool(status.enable_tools))

    def remake(self, owner: str) ->  Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        self.history_manager.remove_last_assistant(owner)
        return self.generate(owner, enable_tools=bool(status.enable_tools))

    def delete(self, num: int,  owner: str) -> bool:
        if num < 1:
            return False

        for _ in range(num):
            self.history_manager.remove_last_pair(owner)
        return True

    def replace(self, prompt: str, owner: str) ->  Generator[str, Any]:
        self.history_manager.remove_last_pair(owner)
        return self.chat(prompt, owner)

    def auto_switch(self, *, role_keyword: str, owner:str) -> Generator[str, Any]:
        config = self.role_manager.get_role(role_keyword)
        self.history_manager.switch(role_config=config, owner=owner)
        content = f"切换到角色: {config.name}"
        yield f"data: {json.dumps({'text': content, 'done': True})}\n\n"

    def change_mode(self, role_mode: int, owner:str) -> Generator[str, Any]:
        self.history_manager.change_mode(role_mode, owner)
        content = f"切换到模式: {assistant_mode_str(role_mode)}"
        yield f"data: {json.dumps({'text': content, 'done': True})}\n\n"

    def make_user_inject_content(self, status: Status, owner:str) -> str:
        # 扮演模式不注入任何系统相关的信息
        if status.assistant_mode == AssistantModeType.RolePlaying:
            return ""

        # 非扮演模式查询具体的状态信息
        # 当前番茄钟状态
        start = self.history_manager.get_last_assistant_mode_time(status)
        begin_time, begin_state = self.get_tomato_state_begin_time()
        state = self.get_tomato_state(owner=owner, begin_time=begin_time, begin_state=begin_state)
        content = f"番茄钟状态: {state}\n"

        # 事件信息, 可能没有事件
        # 如果已经跨越了1天时间, 则昨天产生的信息不再继续追加到当前会话中
        start = tb if (tb:=today_begin()) > start else start
        event_info = self.get_event_info(owner, start)
        if event_info != "":
            content += "用户新增的事件记录:\n" + event_info

        return content

    def get_role_info_list(self) -> Generator[str, Any]:
        raw_list = self.role_manager.get_role_list()
        for role in raw_list:
            name = role.name
            desc = role.short_desc
            content = f"{name}: {desc}\n"
            yield f"data: {json.dumps({'text': content, 'done': False})}\n\n"
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"

    def show_cost(self, owner:str) -> Generator[str, Any]:
        cost_report = self.memory_manager.evaluate_cost(owner)
        yield f"data: {json.dumps({'text': cost_report, 'done': False})}\n\n"

        yield f"data: {json.dumps({'text': '\n\n当前角色成本明细:\n', 'done': False})}\n\n"
        state = self.history_manager.query_or_init_status(owner)
        cost_report: str = self.history_manager.day_cost_report(state.assistant_name, owner)
        yield f"data: {json.dumps({'text': cost_report, 'done': True})}\n\n"

    def show_memory(self, owner:str) -> Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        memory = self.memory_manager.query_or_init_memory(status.assistant_name, owner)
        yield f"data: {json.dumps({'text': memory.to_dump(), 'done': True})}\n\n"

    def show_last_reason(self, owner:str) -> Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        memory = self.memory_manager.query_or_init_memory(status.assistant_name, owner)
        content = f"压缩记忆: \n{memory.compression_reason}\n\n流言蜚语: \n{memory.rumor_reason}"
        yield f"data: {json.dumps({'text': content, 'done': True})}\n\n"

    def set_memory(self, memory_content: str, owner: str) -> Generator[str, Any]:
        memory_content = memory_content.strip()
        status = self.history_manager.query_or_init_status(owner)
        self.memory_manager.inject_long_term_memory(memory_content=memory_content, role_name=status.assistant_name, owner=owner)
        yield from self.show_memory(owner)

    def set_time(self, time_str: str, owner: str) -> Generator[str, Any]:
        # 使用待办事项截止日期相同格式的时间处理逻辑, 简化输入
        t = parse_befeore_time_str(time_str)
        status = self.history_manager.query_or_init_status(owner)
        self.memory_manager.reset_process_time(t, status.assistant_name, owner)
        yield from self.show_memory(owner)


    def rumor(self, target_keyword: str, owner:str) -> Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        target = self.role_manager.get_role(target_keyword)
        content = f"正在生成{status.assistant_name}收到的关于{target.name}的流言蜚语\n"
        yield f"data: {json.dumps({'text': content, 'done': False})}\n\n"

        history = self.history_manager.select_record_after(target.name, today_begin(), owner)
        new_content = ""
        for record in history:
            r = record.to_openai()
            new_content += json.dumps(r, ensure_ascii=False)
            new_content += "\n"

        prompt = RumorMillPrompt.format(visitor_desc=status.assistant_desc, role_desc=target.get_desc(), new_content=new_content)
        reason, content = self.llm_manager.generate_one_shot(prompt)
        if reason is not None:
            content = f'\n---\n\n{reason}\n\n---\n\n'
            yield f"data: {json.dumps({'text': content, 'done': False})}\n\n"

        if content is None:
            yield f"data: {json.dumps({'text': '生成失败', 'done': True})}\n\n"
            return

        inject_content = f'你的内心产生了一个想法: {content}'
        self.history_manager.add_user_prompt('', inject_content, owner)
        yield from self.generate(owner, enable_tools=bool(status.enable_tools))

    def rumor_propagation(self, owner: str) -> Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        memory = self.memory_manager.query_or_init_memory(status.assistant_name, owner)
        if not memory.short_term_memory:
            yield f"data: {json.dumps({'text': '当前没有可用的流言蜚语\n', 'done': True})}\n\n"

        inject_content = f'你收到了一些传闻: {memory.short_term_memory}'
        self.history_manager.add_user_inject(inject_content, status.assistant_name, owner)
        yield from self.generate(owner, enable_tools=bool(status.enable_tools))

    def inject(self, inject_data:str, user_prompt:str, owner:str) -> Generator[str, Any]:
        self.history_manager.add_user_prompt(user_prompt, inject_data, owner)
        yield from self.generate(owner, enable_tools=False)

    def __is_zero_tomoto_task(self, name:str) -> bool:
        # 打卡类任务可瞬间完成无需番茄钟.  午间和晚间任务不占用番茄钟
        keywords = ['打卡', '午间', '晚间']
        return any(word in name for word in keywords)


    def get_event_info(self, owner:str, begin_time: datetime) -> str:
        content = ""
        # 新增番茄钟记录
        events = get_event_log_after(self.item_manager.db, begin_time, owner)
        for e in events:
            content += f"{get_hour_str_from(e.create_time)}: {e.msg}\n"

        return content

    def get_tomato_state_begin_time(self) -> tuple[datetime, str]:
        now_time = now()
        today_morning_start = datetime(now_time.year, now_time.month, now_time.day, 8, 0, 0)
        today_morning_end = datetime(now_time.year, now_time.month, now_time.day, 12, 0, 0)
        today_afternoon_end = datetime(now_time.year, now_time.month, now_time.day, 18, 0, 0)

        if now_time < today_morning_end:
            return today_morning_start, '上午'

        if now_time < today_afternoon_end:
            return today_morning_end, '下午'

        return today_afternoon_end, '晚上'

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


    def get_tomato_state(self, owner: str, begin_time: datetime, begin_state: str) -> str:
        # 首先检查是否是番茄钟工作状态, 该状态优先级最高, 因此用户实际上可以在任意时间开始番茄钟
        state = self.tomato_manager.query_task(owner=owner)
        if state:
            last_group_cnt, last_tomato_cnt, _ = self.get_tomoto_record_info(owner=owner, begin_time=begin_time)
            remain_minutes = (state.start_time + timedelta(minutes=25) - now()).total_seconds() / 60
            return f"正在进行{begin_state}第{last_group_cnt+1}组番茄钟内的第{last_tomato_cnt+1}个番茄钟, 当前为工作状态, 工作项目为[{state.name}], 工作时间剩余{remain_minutes:.2f}分钟\n"

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
                return f"已完成{begin_state}第{last_group_cnt}组番茄钟, 当前为大组之间的休息时间, 剩余{20 - elapsed_minutes:.2f}分钟\n"
            else:
                return f"已完成{begin_state}第{last_group_cnt}组番茄钟, 已完成大组之间的休息, 当前进入规划状态, 已持续{elapsed_minutes - 20:.2f}分钟\n"

        # 如果不是最后一个番茄钟
        if elapsed_minutes < 5:
            # 休息时间不注入任务名, 该部分信息已经包含在事件列表中
            # 进入这个状态是已经把当前番茄钟的记录写入, 因此无需再+1了
            return f"正在进行{begin_state}第{last_group_cnt+1}组番茄钟内的第{last_tomato_cnt}个番茄钟, 当前为休息状态, 休息时间剩余{5 - elapsed_minutes:.2f}分钟\n"
        else:
            return f"已完成{begin_state}第{last_group_cnt+1}组番茄钟内的第{last_tomato_cnt}个番茄钟, 当前进入规划状态, 已持续{elapsed_minutes - 5:.2f}分钟\n"


    def get_tomoto_record_info(self, owner: str, begin_time:datetime) -> tuple[int, int, TomatoTaskRecord | None]:
        tomato_records = self.tomato_record_manager.select_record_after(owner=owner, time=begin_time)
        record_cnt = len(tomato_records)

        if record_cnt == 0:
            return 0,0, None

        last_group_cnt = record_cnt // 4
        last_tomato_cnt = record_cnt % 4
        return last_group_cnt, last_tomato_cnt, tomato_records[-1]


    def get_web_history(self, owner:str) -> list[dict]:
        return self.history_manager.get_web_history(owner)

    def get_more_web_history(self, end_time_str: str,  owner: str) -> list[dict]:
        if end_time_str == '':
            return []

        end_time = get_datetime_from_str(end_time_str)
        return self.history_manager.get_more_web_history(end_time=end_time, owner=owner)

    def dump_history(self, owner:str) -> Generator[str, Any]:
        _, memory, record = self.history_manager.select_record(owner)
        if memory is not None:
            yield f"data: {json.dumps({'text': memory.to_dump(), 'done': False})}\n\n"

        for item in record:
            v = item.to_dump()
            yield f"data: {json.dumps({'text': v, 'done': False})}\n\n"
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"

    def dump_user_prompt(self, owner: str) ->Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)

        mode =  assistant_mode_str(status.assistant_mode)
        config = self.role_manager.get_role(status.assistant_name)
        content = f"【当前状态信息】\n角色名: {status.assistant_name}\n角色模式: {mode}\n角色描述: {config.short_desc}\n"

        to_inject_content = self.make_user_inject_content(status, owner)
        content += f'\n【即将注入的信息】\n{to_inject_content}'
        yield f"data: {json.dumps({'text': content, 'done': True})}\n\n"

