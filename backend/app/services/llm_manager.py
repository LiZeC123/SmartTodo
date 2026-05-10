import json
import random
import re
from collections.abc import Callable, Generator, Iterable
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

from app.models.assistant import AssistantModeType, AssistantType, History, Memory, Status, make_assistant_status
from app.models.item import Item
from app.models.tomato import TomatoTaskRecord
from app.services.config_manager import ConfigManager
from app.services.event_log_manager import get_event_log_after
from app.services.item_manager import ItemManager
from app.services.tomato_manager import TomatoManager, TomatoRecordManager
from app.template.prompt import AssistantSp, EnableToolDesc, LongTermMemoryPrompt, RolePalyingSp, RumorMillPrompt
from app.template.tools import CreatItemTool
from app.tools.llm import LLMClient
from app.tools.log import logger
from app.tools.time import (
    format_timedelta,
    get_datetime_from_str,
    get_hour_str_from,
    now,
    parse_befeore_time_str,
    the_day_begin,
    today_begin,
)


@dataclass
class RoleConfig:
    name: str
    enable_tools: bool
    memory_compress: str
    desc: str

@dataclass
class CompressionPolicy:
    day_delta: int
    char_cost: int

KB = 1024

AggressivePolicy = CompressionPolicy(day_delta=1, char_cost=20*KB)
ModeratePolicy = CompressionPolicy(day_delta=2, char_cost=20*KB)
LazyPolicy = CompressionPolicy(day_delta=3, char_cost=20*KB)



class RoleManager:
    def __init__(self) -> None:
        pass

    def __load_file(self) -> list[RoleConfig]:
        with open("config/role/Assistant.jsonl") as f:
            return [RoleConfig(**json.loads(s)) for role in f if (s:=role.strip()) != ""]

    def get_role_list(self) -> list[RoleConfig]:
        try:
            return self.__load_file()
        except OSError:
            # 文件不存在时, 直接返回空即可, 相当于没有额外的角色设定
            return []

    def get_role(self, role_keyword: str) -> RoleConfig:
        roles =self.get_role_list()
        if len(roles) == 0:
            logger.warning('角色列表为空, 加载默认角色')
            return RoleConfig(name='默认角色', enable_tools=False, memory_compress='No', desc='你是一个有用的助手.')

        random_role = random.choice(roles)
        if role_keyword == "":
            return random_role

        it = (role for role in roles if role_keyword in role.desc)
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

    def add_user_prompt(self, prompt: str, inject: str, owner:str, /, tag:int=0):
        status = self.query_or_init_status(owner)
        msg = History(role='user', content=prompt, system_inject_content=inject, owner=owner,
                               assistant_name=status.assistant_name, assistant_mode=status.assistant_mode, tag=tag)
        self.db.add(msg)
        self.db.flush()
        self.db.commit()

    def add_assistant_prompt(self, content: str,owner:str, /, tag:int=0):
        status = self.query_or_init_status(owner)
        msg = History(role='assistant', content=content, owner=owner,
                               assistant_name=status.assistant_name, assistant_mode=status.assistant_mode, tag=tag)
        self.db.add(msg)
        self.db.flush()
        self.db.commit()

    def switch(self, /, role_config: RoleConfig, role_mode: int, owner:str):
        status = self.query_or_init_status(owner)
        status.assistant_name = role_config.name
        status.assistant_desc = role_config.desc
        status.enable_tools = role_config.enable_tools
        status.assistant_mode = role_mode
        self.db.flush()
        self.db.commit()

    def remove_last_assistant(self, owner: str) -> bool:
        last =  self.select_last_msg(owner)
        if last is None:
            return False

        if last.role != AssistantType.Assistant:
            return False

        self.db.delete(last)
        self.db.flush()
        self.db.commit()
        return True

    def remove_last_user(self, owner: str) -> bool:
        last =  self.select_last_msg(owner)
        if last is None:
            return False

        if last.role != AssistantType.User:
            return False

        self.db.delete(last)
        self.db.flush()
        self.db.commit()
        return True

    def remove_last_pair(self, owner: str) -> bool:
        a = self.remove_last_assistant(owner)
        u = self.remove_last_user(owner)
        return a and u

    def query_or_init_status(self, owner: str) -> Status:
        stmt = sal.select(Status).where(Status.owner == owner)
        t = self.db.scalar(stmt)
        if t is None:
            t = make_assistant_status(owner=owner)
            self.db.add(t)
            self.db.flush()
            self.db.commit()
        return t


    def select_last_msg(self, owner: str) -> History | None:
        status = self.query_or_init_status(owner)
        stmt = sal.select(History).where(History.owner==owner, History.assistant_name==status.assistant_name).order_by(History.id.desc()).limit(1)
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

        stmt = sal.select(Memory).where(Memory.assistant_name==status.assistant_name,Memory.owner==owner)
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

    def select_record_between(self, role_name: str, start_time:datetime, end_time:datetime, owner: str):
        stmt = sal.select(History)\
                  .where(History.owner == owner,
                         History.create_time > start_time, History.create_time < end_time,
                         History.assistant_name == role_name)
        return self.db.scalars(stmt)

    def get_history(self, owner:str)-> list[ChatCompletionMessageParam]:
        status, memory, records = self.select_record(owner)
        sp = self.make_system_prompt(status)

        if memory is None:
            return [sp] + [msg.to_openai() for msg in records]

        mp = ChatCompletionUserMessageParam(role='user',content=memory.to_assistant())
        return [sp, mp] + [msg.to_openai() for msg in records]

    def get_web_history(self, owner: str) -> list[dict]:
        status = self.query_or_init_status(owner)
        start = today_begin() - timedelta(days=3)
        records = self.select_record_after(status.assistant_name, start, owner)
        return [{'role': msg.role, 'msg': msg.to_web()} for msg in records if msg.role in [AssistantType.User, AssistantType.Assistant]]

    def evalute_day_cost(self, owner: str) -> str:
        status = self.query_or_init_status(owner)
        start_day = now() - timedelta(days=14)
        stmt = sal.select(sal.func.date(History.create_time).label("stat_date"),
                          sal.func.sum(sal.func.length(History.content) +sal.func.length(History.system_inject_content)).label("total_chars"),
                          sal.func.count().label('msg_count')) \
                  .where(History.owner == owner,History.assistant_name == status.assistant_name, History.create_time > start_day) \
                  .group_by(sal.func.date(History.create_time)) \
                  .order_by("stat_date")
        records = self.db.execute(stmt)
        return "\n".join([f"{r.stat_date}: {r.total_chars / 1024:6.2f} KB / {r.msg_count // 2:4d} Msg" for r in records])

    def make_system_prompt(self, status: Status) -> ChatCompletionSystemMessageParam:
        if status.assistant_mode == AssistantModeType.RolePlaying:
            return ChatCompletionSystemMessageParam(role="system", content=RolePalyingSp.format(role_desc=status.assistant_desc))

        tool_desc = EnableToolDesc if status.enable_tools else ''
        return ChatCompletionSystemMessageParam(
            role="system",
            content=AssistantSp.format(role_desc=status.assistant_desc, tool_desc=tool_desc)
        )



class AssistantMemoryManager:
    def __init__(self, db: scoped_session[Session], llm_client: LLMClient) -> None:
        self.db = db
        self.config_manager = ConfigManager()
        self.role_manager = RoleManager()
        self.cliet = llm_client

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
        end_time = now() - timedelta(days=policy.day_delta)
        memory = self.query_or_init_memory(config.name, owner)
        stmt = sal.select(History) \
                  .where(History.owner == owner, History.assistant_name == config.name,
                         History.create_time > memory.processed_time, History.create_time < end_time)
        records = self.db.scalars(stmt).all()


        cost = sum(len(s) for r in records if (s := r.to_dump()) is not None)
        if cost < policy.char_cost:
            logger.info(f"[{owner}:{config.name}]: 跳过压缩, 当前费用 {cost / KB:.2f} KB < 目标阈值 {policy.char_cost / KB:.2f} KB")
            return False

        new_content = "\n".join([json.dumps(r.to_openai(), ensure_ascii=False) for r in records])
        prompt = LongTermMemoryPrompt.format(role_desc=config.desc, old_memory=memory.long_term_memory, new_content=new_content)
        reason, content = self.cliet.generate_one_shot(prompt)

        new_memory = memory.deep_copy(processed_time=end_time)
        if reason is not None:
            new_memory.compression_reason = reason

        if content is not None:
            new_memory.long_term_memory = content
            self.db.add(new_memory)
            self.db.commit()
            logger.info(f"[{owner}:{config.name}]: 记忆压缩完毕, 新记忆长度为 {len(content)/KB:.2f} KB")
            return True
        else:
            logger.warning(f'模型返回记忆为空. 用户:{owner} 助手:{config.name}')
            return False

    #TODO: 记忆压缩任务定时开启
    def auto_update_long_term_memory(self):
        users = self.config_manager.get_all_users()
        g = ((u, r) for u in users for r in self.get_recent_assistant_list(u))
        for user, role in g:
            config = self.role_manager.get_role(role)
            self.update_long_term_memory(config=config, owner=user)
        pass

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
        memory.long_term_memory = memory_content
        self.db.flush()
        self.db.commit()

    def reset_process_time(self, new_time: datetime,  role_name:str, owner:str) -> bool:
        memory = self.query_or_init_memory(role_name, owner)
        memory.processed_time = new_time
        self.db.flush()
        self.db.commit()
        return True

    def get_recent_assistant_list(self, owner: str) -> Iterable[str]:
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
        history = self.history_manager.get_history(owner)
        if enable_tools:
            # print("历史内容", history)
            tool_desc, tool_map = self.make_tools(owner)
            stream = self.llm_manager.generate_steam_with_tools(history, tool_desc, tool_map)
        else:
            stream = self.llm_manager.generate_stream(history)
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
            self.history_manager.add_assistant_prompt(content, owner)


    def make_tools(self, owner:str) -> tuple[Iterable[ChatCompletionToolUnionParam], dict[str, Callable[[str], str]]]:
        def create_f(arg_json:str) -> str:
            try:
                print(f"执行创建事项函数: {arg_json}")
                args:dict[str,str] = json.loads(arg_json)
                item = Item(name=args.get('name'), item_type='single', owner=owner,
                            deadline=get_datetime_from_str(args.get('deadline', '')),
                            priority=args.get('priority'))
                self.item_manager.create(item)
                self.item_manager.db.commit()
            except Exception as e:
                return f"error: {e}"
            return "success"

        return [CreatItemTool], {"create_item": create_f}


    def chat(self, prompt: str, owner: str) ->  Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        inject_content = self.make_user_inject_content(status, owner)
        self.history_manager.add_user_prompt(prompt, inject_content, owner)
        return self.generate(owner, enable_tools=bool(status.enable_tools))

    def remake(self, owner: str) ->  Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        self.history_manager.remove_last_assistant(owner)
        return self.generate(owner, enable_tools=bool(status.enable_tools))

    def delete(self, owner: str) -> bool:
        return self.history_manager.remove_last_pair(owner)

    def replace(self, prompt: str, owner: str) ->  Generator[str, Any]:
        self.history_manager.remove_last_pair(owner)
        return self.chat(prompt, owner)

    def reset(self, owner: str, role_keyword: str = '') -> Generator[str, Any]:
        # reset功能不存在了, 先不删除, 后续看有无必要实现
        raise Exception('reset not implemented')

    def switch(self, *, role_keyword: str, role_mode: int, owner:str)-> Generator[str, Any]:
        config = self.role_manager.get_role(role_keyword)
        self.history_manager.switch(role_config=config, role_mode=role_mode, owner=owner)
        content = f"切换到角色: {config.name}"
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
        event_info = self.get_event_info(owner, start)
        if event_info != "":
            content += "用户新增的事件记录:\n" + event_info

        return content

    def get_role_info_list(self) -> Generator[str, Any]:
        raw_list = self.role_manager.get_role_list()
        for role in raw_list:
            name = role.name
            desc = role.desc.split(",")[0]
            content = f"{name}: {desc}\n"
            yield f"data: {json.dumps({'text': content, 'done': False})}\n\n"
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"

    def show_cost(self, owner:str) -> Generator[str, Any]:
        cost_report = self.memory_manager.evaluate_cost(owner)
        yield f"data: {json.dumps({'text': cost_report, 'done': True})}\n\n"

    def show_day_cost(self, owner: str) -> Generator[str, Any]:
        cost_report = self.history_manager.evalute_day_cost(owner)
        yield f"data: {json.dumps({'text': cost_report, 'done': True})}\n\n"

    def show_memory(self, owner:str) -> Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        memory = self.memory_manager.query_or_init_memory(status.assistant_name, owner)
        yield f"data: {json.dumps({'text': memory.to_dump(), 'done': True})}\n\n"

    def compress_memory(self, _: str, owner:str) -> Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        config=self.role_manager.get_role(status.assistant_name)

        msg = f"正在压缩 {config.name} 的记忆, 记忆策略: {config.memory_compress} ...\n"
        yield f"data: {json.dumps({'text': msg, 'done': False})}\n\n"

        ok = self.memory_manager.update_long_term_memory(config=config, owner=owner)
        if ok:
            yield from self.show_memory(owner)
        else:
            yield f"data: {json.dumps({'text': '记忆压缩未成功, 具体原因可查看日志', 'done': True})}\n\n"

    def show_last_reason(self, owner:str) -> Generator[str, Any]:
        status = self.history_manager.query_or_init_status(owner)
        memory = self.memory_manager.query_or_init_memory(status.assistant_name, owner)
        yield f"data: {json.dumps({'text': memory.compression_reason, 'done': True})}\n\n"

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


        prompt = RumorMillPrompt.format(visitor_desc=status.assistant_desc, role_desc=target.desc, new_content=new_content)

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

    def show_day_history(self, day_str: str, owner:str) -> Generator[str, Any]:
        t = parse_befeore_time_str(day_str)
        start = the_day_begin(t)
        end = start + timedelta(days=1)
        status = self.history_manager.query_or_init_status(owner)
        history = self.history_manager.select_record_between(status.assistant_name, start_time=start, end_time=end, owner=owner)

        for item in history:
            v = item.to_dump()
            yield f"data: {json.dumps({'text': v, 'done': False})}\n\n"
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"

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
        content = self.make_user_inject_content(status, owner)
        yield f"data: {json.dumps({'text': content, 'done': False})}\n\n"

        mode = '扮演模式' if status.assistant_mode == AssistantModeType.RolePlaying else '助理模式'
        content = f"\n当前状态信息\n 角色名: {status.assistant_name}\n 角色模式: {mode}\n 角色描述: {status.assistant_desc}\n"
        yield f"data: {json.dumps({'text': content, 'done': False})}\n\n"

        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"

    @staticmethod
    def parse_number(s: str) -> int:
        """
        解析字符串为数字：
        - 如果是 正整数 或 0 → 返回对应的数字
        - 如果是空字符串 "" → 返回 -1
        - 其他所有解析失败情况 → 返回 -2
        """
        # 空字符串 → 返回 -1
        if s == "":
            return -1

        try:
            # 尝试转整数
            num = int(s)
            # 是整数，但必须 >= 0 才合法
            if num >= 0:
                return num
            else:
                # 负数 → 解析错误
                return -2
        except (ValueError, TypeError):
            # 无法转整数 → 解析错误
            return -2


    @staticmethod
    def extract_role_name(text):
        """提取角色名, 角色描述中需要包含 '名为xxx,' 的文字, 提取该部分作为角色名"""
        # 正则表达式：匹配 名叫(任意1+字符), 捕获中间的内容
        pattern = r"名叫(.+?),"
        # 查找第一个匹配项
        match = re.search(pattern, text)

        if match:
            return match.group(1)  # 返回括号内捕获的名字
        return None
