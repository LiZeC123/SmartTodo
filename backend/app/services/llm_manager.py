from datetime import datetime, timedelta
import json
import random
import re
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, Tuple

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionToolUnionParam
from openai.types.shared_params.function_definition import FunctionDefinition
from openai.types.chat.chat_completion_function_tool_param import ChatCompletionFunctionToolParam
import sqlalchemy as sal
from sqlalchemy.orm import Session, scoped_session

from app.models.assistant import AssistantHistory, AssistantMemory, AssistantModeType, AssistantStatus, AssistantTagType, AssistantType, make_assistant_status
from app.models.item import Item
from app.models.tomato import TomatoTaskRecord
from app.services.event_log_manager import get_event_log_after
from app.services.item_manager import ItemManager
from app.services.tomato_manager import TomatoManager, TomatoRecordManager
from app.tools.llm import LLMClient
from app.tools.log import logger
from app.tools.time import get_datetime_from_str, get_hour_str_from, now, today_begin



SystemPrompt = '''# 角色设定
你是用户的个人待办事项管理助理. {role_desc}

# 用户的工作模式

1. 用户采用番茄工作法, 在 工作 -> 休息 -> 规划 三个状态中循环, 每个番茄钟包含25分钟的工作时间, 5分钟的休息时间. 两个番茄钟之间属于规划时间. 
2. 每4个番茄钟为一个大组, 完成一个大组后有额外的15分钟休息时间. 
3. 当前状态为工作时, 话题围绕当前工作项. 当前状态为休息时, 按照人设和用户对话进行闲聊. 当前状态为规划状态时, 可闲聊并讨论后续任务规划. 

# 用户的休息模式

1. 每天的11:30~14:30为午休时间, 17:30~19:00为晚餐时间. 21:00~23:00为深夜休息时间, 23:00以后为睡眠时间. 
2. 用户有特定的自由行动时间, 该状态会在系统信息中展示
3. 在上述休息时间和自由行动时间时, 不可主动提及工作事项, 仅需要按照人设与用户进行对话.

# 系统权限

1. 你具有创建新的待办事项的权限, 在用户要求创建或添加某个事项时, 你必须通过调用`create_item`工具创建待办事项, 并且明确告知用户执行结果.
2. 事项名称的格式为: [助手名称]:[事项主题]

# 关键注意事项

1. 在用户的对话前有系统插入的当前状态信息和用户行为日志.  
2. 系统会在每天凌晨将用户的可重复任务自动重置为未完成状态, 以便于用户重新进行打卡.
2. 每次回复需要至少200字
'''


# 创建待办事项工具
CreatItemTool: ChatCompletionFunctionToolParam = ChatCompletionFunctionToolParam(
    type="function",
    function=FunctionDefinition(
        name="create_item",
        description="创建一个新的待办事项",
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "待办事项的名称",
                },
                "deadline": {
                    "type": "string",
                    "format": "date-time",
                    "description": "截止时间, 格式为2006-01-02 15:04:05",
                },
                "priority": {
                    "type": "string",
                    "description": "优先级，常用取值：'p0'(两天内完成)、'p1'(本周末前完成)、'p2'(下周末前完成)",
                    "default": "p1",
                    "enum": ["p0", "p1", "p2"],
                },
            },
            "required": ["name", "deadline", "priority"],
        },
    ),
)

class AssistantHistoryManager:
    def __init__(self, db: scoped_session[Session]) -> None:
        self.db = db

    def add_user_prompt(self, prompt: str, inject: str, owner:str, /, tag:int=0):
        status = self.query_or_init_status(owner)
        msg = AssistantHistory(role='user', content=prompt, system_inject_content=inject, owner=owner, 
                               assistant_name=status.assistant_name, assistant_mode=status.assistant_mode, tag=tag)
        self.db.add(msg)
        self.db.flush()
        self.db.commit()
    
    def add_assistant_prompt(self, content: str,owner:str, /, tag:int=0):
        status = self.query_or_init_status(owner)
        msg = AssistantHistory(role='assistant', content=content, owner=owner,
                               assistant_name=status.assistant_name, assistant_mode=status.assistant_mode, tag=tag)
        self.db.add(msg)
        self.db.flush()
        self.db.commit()
        
    def switch(self, /, role_name: str, role_desc:str, role_mode: int, owner:str):
        status = self.query_or_init_status(owner)
        status.assistant_name = role_name
        status.assistant_desc = role_desc
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

    def query_or_init_status(self, owner: str) -> AssistantStatus:
        stmt = sal.select(AssistantStatus).where(AssistantStatus.owner == owner)
        t = self.db.scalar(stmt)
        if t is None:
            start_time = today_begin() - timedelta(days=2)
            t = make_assistant_status(owner=owner, start_time=start_time)
            self.db.add(t)
            self.db.flush()
            self.db.commit()            
        return t
    
  
    def select_last_msg(self, owner: str) -> Optional[AssistantHistory]:
        status = self.query_or_init_status(owner)
        stmt = sal.select(AssistantHistory).where(AssistantHistory.owner==owner, AssistantHistory.assistant_name==status.assistant_name).order_by(AssistantHistory.id.desc()).limit(1)
        return self.db.scalar(stmt)
    
    def get_last_assistant_mode_time(self, status:AssistantStatus) -> datetime:
        # 查询当前助手上一次助手模式的记录时间, 在非助手模式或者其他助手对话过程中产生的记录对当前助手来说是没有见过的
        stmt = sal.select(AssistantHistory).where(AssistantHistory.owner==status.owner, 
                                                  AssistantHistory.assistant_mode==AssistantModeType.Assistant,
                                                  AssistantHistory.assistant_name==status.assistant_name).order_by(AssistantHistory.id.desc()).limit(1)
        last = self.db.scalar(stmt)
        if last is None:
            return today_begin()
        else:
            return last.create_time
    
    def select_record(self, owner:str) -> Tuple[AssistantStatus, Iterable[AssistantHistory]]:
        # 查询当前角色最近2天聊天记录
        status = self.query_or_init_status(owner)
        start_time = today_begin() - timedelta(days=2)
        stmt = sal.select(AssistantHistory).where(AssistantHistory.owner == owner, 
                                                  AssistantHistory.create_time > start_time,
                                                  AssistantHistory.assistant_name == status.assistant_name)
        return (status, self.db.scalars(stmt)) 

    def get_history(self, owner:str)-> List[ChatCompletionMessageParam]:        
        status, records = self.select_record(owner)
        return [self.make_system_prompt(status.assistant_desc)] + [msg.to_openai() for msg in records]
    
    def get_web_history(self, owner: str) -> List[Dict]:
        _, records = self.select_record(owner)
        return [{'role': msg.role, 'msg': msg.to_web()} for msg in records if msg.role in [AssistantType.User, AssistantType.Assistant]]
    
    def make_system_prompt(self, role_desc) -> ChatCompletionSystemMessageParam:
        return ChatCompletionSystemMessageParam(
            role="system",
            content=SystemPrompt.format(role_desc=role_desc)
        )


LongTermMemoryPrompt = """
你是一个长期记忆整合引擎, 处理和整合聊天助手的记忆.

【输出格式与内容说明】

请严格按照如下的章节标题输出内容. 每一章节中包含了该部分内容的要求描述. 输出时不要多余解释，直接输出正文

# 约定和待办

这一部分输出助手明确表达的约定或待办事项, 每一项需要包含事项标题, 预计处理时间和当前状态(例如:待执行、进行中或者挂起等). 不提取系统任务（如番茄钟）和用户的个人规划.
对于旧记忆中已经存在的条目, 需要逐一检查并更新状态, 已完成的事项删除并评估是否进入里程碑条目.

# 助手内心想法

这一部分根据最新的对话文本, 以助手的人设使用一段文本给出一段助手的内心想法. 

# 新增设定

这一部分根据对话提取在助手和用户之间已经确认的新增设定. 该设定应该是长期生效且对角色会产生影响的. 例如在第二天依然会有效.

# 用户偏好预测

## 表层偏好预测

这一部分基于对话内容预测用户可能的偏好, 给出该预测的置信度(高、中、低等)以及简短的证据描述. 根据新的对话调整原有偏好预测的置信度, 合并相似的表达, 移除预测错误的条目.

## 深层偏好推测

这一部分深度分析和推测用户的认知模式、价值观和沟通风格等更为抽象和一般性的偏好. 根据表层偏好预测的变化和新对话调整现有条目的置信度. 
深层偏好的更新应该具有一定的迟滞性. 新增条目的置信度默认为"中". 当新的对话继续支持某个已有条目时提高该条目的置信度, 反之降低该条目的置信度. 已经是低置信度的条目再次产生矛盾时才能删除对应条目.

# 近期话题

这一部分输出助手和用户之间讨论的话题和助手的核心观点. 每个话题用一句话进行概述并给出该话题的提出时间. 给出包含年月日的精确日期以便于后续按照日期进行热度删除处理.
根据新的对话提取助手和用户之间的新增话题, 并优先考虑将新话题与已有话题合并然后更新该条目的提出时间. 最后检查话题数量, 如果已经超过十条, 则抛弃提出时间最久的条目, 使得总条目数量维持在十条以内.

# 共享里程碑

这一部分记录助手和用户之间最重要的节点性时刻的信息, 包含: 事件的时间点, 事件的简要描述.
只记录对于助手和用户共享的、与情感关系相关的最重要的事件. 该部分只能新增与合并, 不能删除, 如果没有重要的事件则保持原有记录不变. 

【其他约束条件】

1. 除了助手状态信息使用助手第一视角以外, 其他部分使用客观视角描述, 即使用助手的名字指代助手, 使用助手对用户的常态称呼指代用户.
2. 冲突信息以最新对话为准, 补充信息时不重复. 
3. 任何部分都不要提取 助手描述信息 中已经描述的信息.

【助手描述信息】

{role_desc}

【旧记忆】

{old_memory}

【新的多轮对话】

{new_content}
"""




class AssistantMemoryManager:
    def __init__(self, db: scoped_session[Session], llm_client: LLMClient) -> None:
        self.db = db
        self.cliet = llm_client
        self.last_reason_content = "" #TODO: 临时存储方案, 后续应该调整
    
    def query_or_init_memory(self, role_name:str, owner:str) -> AssistantMemory:
        stmt = sal.select(AssistantMemory).where(AssistantMemory.assistant_name==role_name,AssistantMemory.owner==owner)
        t = self.db.scalar(stmt)
        if t is None:
            t = AssistantMemory(assistant_name=role_name, owner=owner)
            self.db.add(t)
            self.db.flush()
            self.db.commit()
        return t
        
    def update_long_term_memory(self, /, role_name: str, role_desc:str, owner: str) -> str:
        memory = self.query_or_init_memory(role_name, owner)
        stmt = sal.select(AssistantHistory).where(AssistantHistory.owner == owner, 
                                                  AssistantHistory.create_time > memory.processed_time,
                                                  AssistantHistory.assistant_name == role_name)
        records = self.db.scalars(stmt)

        new_content = ""
        for record in records:
            r = record.to_openai()
            new_content += json.dumps(r, ensure_ascii=False)
            new_content += "\n"
        
        prompt = LongTermMemoryPrompt.format(role_desc=role_desc, old_memory=memory.long_term_memory, new_content=new_content)
        reason, content = self.cliet.generate_one_shot(prompt)
        if reason is not None:
            self.last_reason_content = reason
        
        if content is not None:    
            memory.long_term_memory = content
            memory.processed_time = now()
            self.db.flush()
            self.db.commit()
            return content
        else:
            logger.warning(f'模型返回记忆为空. 用户:{owner} 助手:{role_name}')
            return ""
    
    def evaluate_cost(self, owner: str) -> str:
        stmt = sal.select(AssistantHistory.assistant_name.distinct()).where(AssistantHistory.owner==owner)
        names = self.db.scalars(stmt)
        
        return "\n".join([self.evaluate_one_role_cost(name, owner) for name in names])
    
    def evaluate_one_role_cost(self, role_name: str, owner: str) -> str:
        memory = self.query_or_init_memory(role_name, owner)
        stmt = sal.select(AssistantHistory).where(AssistantHistory.owner == owner, 
                                                  AssistantHistory.create_time > memory.processed_time,
                                                  AssistantHistory.assistant_name == role_name)
        records = self.db.scalars(stmt).all()
        
        char_cost = sum(len(s) for r in records if (s := r.to_dump()) is not None)
        token_cost = char_cost * 1.5
        conv_cnt = len(records)
        return f"角色名: {role_name:>8s} 字符成本: {char_cost // 1024:6d}KB Token预估数量: {token_cost / 1024:6.1f}K 对话轮次: {conv_cnt // 2:3d}轮"



class AssistantManager:
    def __init__(self, llm_manager: LLMClient, item_manager: ItemManager, 
                 tomato_manager: TomatoManager, tomato_record_manager: TomatoRecordManager,
                 history_manager: AssistantHistoryManager, memory_manager: AssistantMemoryManager) -> None:
        self.llm_manager = llm_manager
        self.item_manager = item_manager
        self.tomato_manager = tomato_manager
        self.tomato_record_manager = tomato_record_manager
        self.history_manager = history_manager
        self.memory_manager = memory_manager
    
    def generate(self, owner: str, /, enable_tools=False) -> Generator[str, Any, None]:
        """流式生成回复：后台消费 LLM 流并保存，前台推送给客户端"""
        history = self.history_manager.get_history(owner)
        if enable_tools:
            print("进入包含工具的分支")
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
    

    def make_tools(self, owner:str) -> Tuple[Iterable[ChatCompletionToolUnionParam], Dict[str, Callable[[str], str]]]: 
        def create_f(arg_json:str) -> str:
            try:
                print(f"执行创建事项函数: {arg_json}")
                args:Dict[str,str] = json.loads(arg_json)
                item = Item(name=args.get('name'), item_type='single', owner=owner,
                            deadline=get_datetime_from_str(args.get('deadline', '')),
                            priority=args.get('priority'))
                self.item_manager.create(item)
                self.item_manager.db.commit()
            except Exception as e:
                return f"error: {e}"
            return "success"
        
        return [CreatItemTool], {"create_item": create_f}
             
                
    def chat(self, prompt: str, owner: str) ->  Generator[str, Any, None]:
        status = self.history_manager.query_or_init_status(owner)
        if status.assistant_mode == AssistantModeType.Assistant:
            # 助理模式下注入待办系统的状态信息
            start = self.history_manager.get_last_assistant_mode_time(status)
            inject_content = self.make_user_inject_content(start, owner)
        else:
            # 非助理模式仅注入一个状态提示
            inject_content = "当前状态: 自由行动模式"
            
        self.history_manager.add_user_prompt(prompt, inject_content, owner)
        return self.generate(owner, enable_tools=True)
        
    def remake(self, owner: str) ->  Generator[str, Any, None]:
        self.history_manager.remove_last_assistant(owner)
        return self.generate(owner, enable_tools=True)
    
    def delete(self, owner: str) -> bool:
        return self.history_manager.remove_last_pair(owner)
        
    def replace(self, prompt: str, owner: str) ->  Generator[str, Any, None]:
        self.history_manager.remove_last_pair(owner)
        return self.chat(prompt, owner)
    
    def reset(self, owner: str, role_keyword: str = '') -> Generator[str, Any, None]:
        # reset功能不存在了, 先不删除, 后续看有无必要实现
        raise Exception('reset not implemented')
        
    def switch(self, /, role_keyword: str, role_mode: int, prompt:str, owner:str)-> Generator[str, Any, None]:
        role_name, role_desc = self.make_switch_role(role_keyword)
        self.history_manager.switch(role_name=role_name, role_desc=role_desc, role_mode=role_mode, owner=owner)
        content = f"切换到角色: {role_name}"
        yield f"data: {json.dumps({'text': content, 'done': True})}\n\n"
    
    def make_user_inject_content(self, start: datetime, owner:str) -> str:
        # 当前番茄钟状态
        begin_time, begin_state = self.get_tomato_state_begin_time()
        state = self.get_tomato_state(owner=owner, begin_time=begin_time, begin_state=begin_state)
        content = f"番茄钟状态: {state}\n"
        
        # 事件信息, 可能没有事件
        event_info = self.get_event_info(owner, start)
        if event_info != "":
            content += "用户新增的事件记录:\n" + event_info
            
        return content

    def make_switch_role(self, keyword: str) -> Tuple[str, str]:
        role_desc = self.get_role_info(self.get_role_list(), keyword)
        role_name = extract_role_name(role_desc)
        if role_name is None:
            logger.warning(f"加载的角色描述信息无法提取角色名: {role_desc}")
            role_name = '未知角色'
        return (role_name, role_desc)

    def get_role_list(self) -> List[str]:
        try:
            with open("config/role/Assistant.md") as f:
                return [role.strip() for role in f if role.strip() != ""]
        except OSError:
            # 文件不存在时, 直接返回空即可, 相当于没有额外的角色设定
            return []
    
    def get_role_info(self, roles: List[str], role_keyword: str) -> str:
        if len(roles) == 0:
            return ""
        
        random_role = random.choice(roles)
        if role_keyword == "":
            return random_role      

        it = (role for role in roles if role_keyword in role)
        return next(it, random_role)
    
    def get_role_info_list(self) -> Generator[str, Any, None]:
        raw_list = self.get_role_list()
        for role in raw_list:
            name = extract_role_name(role)
            desc = role.split(",")[0]
            content = f"{name}: {desc}\n"
            yield f"data: {json.dumps({'text': content, 'done': False})}\n\n"
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"            
 
 
    def show_cost(self, owner:str) -> Generator[str, Any, None]:
        cost_report = self.memory_manager.evaluate_cost(owner)
        yield f"data: {json.dumps({'text': cost_report, 'done': True})}\n\n"
        
    def show_memory(self, owner:str) -> Generator[str, Any, None]:
        status = self.history_manager.query_or_init_status(owner)
        memory = self.memory_manager.query_or_init_memory(status.assistant_name, owner)
        content = memory.long_term_memory
        yield f"data: {json.dumps({'text': content, 'done': True})}\n\n"
        
    def compress_memory(self, owner:str) -> Generator[str, Any, None]:
        status = self.history_manager.query_or_init_status(owner)
        yield f"data: {json.dumps({'text': '正在处理中...\n', 'done': False})}\n\n"
        new_memory = self.memory_manager.update_long_term_memory(status.assistant_name, status.assistant_desc, owner)
        yield f"data: {json.dumps({'text': new_memory, 'done': True})}\n\n"
        
    def show_last_reason(self, owner:str) -> Generator[str, Any, None]:
        content = self.memory_manager.last_reason_content
        yield f"data: {json.dumps({'text': content, 'done': True})}\n\n"
        
    
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
    
    def get_tomato_state_begin_time(self) -> Tuple[datetime, str]:
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
            return f"还未开始任何番茄钟\n"
        
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
        
    
    def get_tomoto_record_info(self, owner: str, begin_time:datetime) -> Tuple[int, int, Optional[TomatoTaskRecord]]:
        tomato_records = self.tomato_record_manager.select_record_after(owner=owner, time=begin_time)
        record_cnt = len(tomato_records)
        
        if record_cnt == 0:
            return 0,0, None
        
        last_group_cnt = record_cnt // 4
        last_tomato_cnt = record_cnt % 4
        return last_group_cnt, last_tomato_cnt, tomato_records[-1]
                  

    def get_web_history(self, owner:str) -> List[Dict]:
        return self.history_manager.get_web_history(owner)
        
    
    def dump_history(self, owner:str) -> Generator[str, Any, None]:
        _, record = self.history_manager.select_record(owner)
        
        for item in record:
            v = item.to_dump()
            yield f"data: {json.dumps({'text': v, 'done': False})}\n\n"
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"
        
    def dump_user_prompt(self, owner: str) ->Generator[str, Any, None]:
        status = self.history_manager.query_or_init_status(owner)
        start = self.history_manager.get_last_assistant_mode_time(status)
        
        content = self.make_user_inject_content(start, owner)
        yield f"data: {json.dumps({'text': content, 'done': False})}\n\n"
        
        content = f"\n当前状态信息\n 角色名: {status.assistant_name}\n 角色模式: {status.assistant_mode}\n 角色描述: {status.assistant_desc}\n"
        yield f"data: {json.dumps({'text': content, 'done': False})}\n\n"
        
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"
        

def extract_role_name(text):
    """提取角色名, 角色描述中需要包含 '名为xxx,' 的文字, 提取该部分作为角色名"""
    # 正则表达式：匹配 名叫(任意1+字符), 捕获中间的内容
    pattern = r"名叫(.+?),"
    # 查找第一个匹配项
    match = re.search(pattern, text)
    
    if match:
        return match.group(1)  # 返回括号内捕获的名字
    return None        