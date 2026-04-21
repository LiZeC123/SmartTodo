from datetime import datetime
import json

from dataclasses import dataclass
import random
from typing import Any, Dict, Generator, List

from app.services.event_log_manager import get_event_log_after
from app.services.item_manager import ItemManager
from app.services.tomato_manager import TomatoManager, TomatoRecordManager
from app.tools.llm import LLMClient
from app.tools.time import get_datetime_from_str, get_hour_str_from, now, now_str, today_begin

from openai.types.chat import ChatCompletionMessageParam



@dataclass
class MemoryItem:
    meta: Dict[str, str]
    message: ChatCompletionMessageParam


class UserMemory:
    def __init__(self, system_prompt: str):
        message: ChatCompletionMessageParam = {
            "role": "system",
            "content": system_prompt,
        }
        self.messages: List[MemoryItem] = [MemoryItem(self.make_meta(), message)]

    def add_user_prompt(self, prompt: str):
        meta = self.make_meta()
        message: ChatCompletionMessageParam = {"role": "user", "content": prompt}
        self.messages.append(MemoryItem(meta, message))

    def add_assistant_prompt(self, content: str):
        meta = self.make_meta()
        message: ChatCompletionMessageParam = {"role": "assistant", "content": content}
        self.messages.append(MemoryItem(meta, message))

    def make_meta(self) -> Dict[str, str]:
        return {"time": now_str()}
    
    def get_last_chat_time(self) ->datetime:
        v = self.messages[-1]
        d = v.meta.get("time")
        if d is None:
            return now()
        return get_datetime_from_str(d)
    
    def remove_last_assistant(self):
        v = self.messages[-1]
        if v.message.get("role") == "assistant":
            self.messages.pop()
    
    def remove_last_pair(self):
        if len(self.messages) < 2:
            return
        self.messages.pop()
        self.messages.pop()
        
    
    def get_history(self) -> List[ChatCompletionMessageParam]:
        return [item.message for item in self.messages]


class AssistantManager:
    def __init__(self, llm_manager: LLMClient, item_manager: ItemManager, tomato_manager: TomatoManager, tomato_record_manager: TomatoRecordManager) -> None:
        self.llm_manager = llm_manager
        self.item_manager = item_manager
        self.tomato_manager = tomato_manager
        self.tomato_record_manager = tomato_record_manager
        self.memory: Dict[str, UserMemory] = {}
        self.role_keyword = ''

    def get_memory(self, owner: str) -> UserMemory:
        m = self.memory.get(owner)
        if m is None:
            sp = self.make_system_prompt(owner)
            m = UserMemory(sp)
            self.memory[owner] = m
        return m
    
    def generate(self, memory: UserMemory) -> Generator[str, Any, None]:
        history = memory.get_history()
        stream = self.llm_manager.generate_stream(history)
        answer = []
        # 读取数据流, 在本地记录的同时返回流给上层
        try:
            for token in stream:
                answer.append(token)
                yield f"data: {json.dumps({'text': token, 'done': False})}\n\n"
            yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        
        # 流读取结束后, 将内容写入到记忆列表
        memory.add_assistant_prompt("".join(answer))
            
    def chat(self, prompt: str, owner: str) ->  Generator[str, Any, None]:
        memory = self.get_memory(owner)
        start = memory.get_last_chat_time()
        prompt = self.make_user_prompt(prompt, start, owner)
        memory.add_user_prompt(prompt)
        return self.generate(memory)
        
    def remake(self, owner: str) ->  Generator[str, Any, None]:
        memory = self.get_memory(owner)
        memory.remove_last_assistant()
        return self.generate(memory)
    
    def delete(self, owner: str) -> bool:
        memory = self.get_memory(owner)
        memory.remove_last_pair()
        return True
    
    def replace(self, prompt: str, owner: str) ->  Generator[str, Any, None]:
        memory = self.get_memory(owner)
        memory.remove_last_pair()
        return self.chat(prompt, owner)
    
    def reset(self, owner: str, role_keyword: str = '') -> bool:
        self.memory.pop(owner)
        self.role_keyword = role_keyword
        return True

    def make_system_prompt(self, owner: str) -> str:
        role_info = self.get_role_info(self.get_role_list(), self.role_keyword)
        task_table = self.get_task_info(owner)
        event_table = self.get_event_info(owner, today_begin())
        if event_table == "":
            event_table = "当前用户还未完成任何事项"
        

        return f'''### 角色设定

你是我的个人代办事项管理助理. {role_info}

### 用户的工作时间表

| 时段     | 起止时间      | 番茄钟数量 |
| -------- | ------------- | ---------- |
| 早间准备  | 9:00 ~ 9:20   | 准备时间无需番茄钟 |
| 上午     | 9:20 ~ 11:20  | 4个        |
| 午间休息  | 11:20 ~ 14:20 | /   |
| 下午1    | 14:20 ~ 16:20 | 4个        |
| 下午休息 | 16:20 ~ 16:40 | /   |
| 下午2    | 16:40 ~ 17:40 | 2个        |
| 晚间休息  | 17:40 ~ 19:00 | /   |
| 晚上     | 19:00 ~ 20:00 | 2个        |
| 晚上sp   | 20:00 ~ 21:00 | 根据完成情况决定工作或休息 |

> 每天晚上21点至第二天9点为休息时间, 不用于完成规划的任务

### 用户今日规划的代办事项
{task_table}

> 部分任务(例如打卡)仅需要完成, 但无需番茄钟

### 用户截止当前时间的事件记录
{event_table}

### 关键注意事项

1. 根据用户的作息时间表和今天的规划, 结合用户的事件记录评估当前的完成情况
2. 一个番茄钟的周期是工作25分钟后休息5分钟, 结合当前时间判断工作和休息状态
3. 每次回复需要至少200字
'''

    def make_user_prompt(self, prompt: str, start: datetime, owner: str) -> str:        
        content = f"当前时间: {now_str()}\n"
        
        event_info = self.get_event_info(owner, start)
        if event_info != "":
            content = "用户截止当前时间的事件记录:\n" + event_info
                
        # 当前番茄钟情况(如果有)
        state = self.tomato_manager.query_task(owner)
        if state is not None:
            content += f"用户当前正在进行的番茄钟: {state.name} 开始时间: {get_hour_str_from(state.start_time)}\n"
        
        # 用户可以不输入任何内容, 全部使用自动填充的信息
        if prompt != "":
            content += "\n---\n\n"
            content += prompt
    
        return content


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
        
        print(role_keyword)
        for role in roles:
            print(role_keyword in role)
        
        random_role = random.choice(roles)
        if role_keyword == "":
            return random_role      

        it = (role for role in roles if role_keyword in role)
        return next(it, random_role)

    def get_task_info(self, owner:str) -> str:
        content =  '''
项目名 | 预计番茄钟数量 | 任务截止时间| 优先级 
------|--------------|-----------|---------
'''
        tasks = self.item_manager.get_tomato_item(owner=owner)
        for task in tasks:
            for item in task['children']:
                expected_tomato = 0 if self.__is_zero_tomoto_task(item["name"]) else item["expected_tomato"]
                line = f"{item["name"]} | {expected_tomato} | {item["deadline"]} | {item["priority"]}\n"
                content = content + line
   
        return content
    
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

    def get_web_history(self, owner:str) -> List[str]:
        m_list = self.get_memory(owner).messages
        if len(m_list) <= 1:
            return []
        
        rst: List[str] = []
        for item in m_list[1:]:
            if item.message.get("role") == "assistant":
                rst.append(str(item.message.get("content")))
            else:
                v = str(item.message.get("content"))
                # 用户的prompt使用'---'分割了系统数据和用户输入数据, 在web端不展示系统数据
                parts = v.split("---", 1)
                if len(parts) == 2:
                    rst.append(parts[1].strip())
                else:
                    rst.append("[用户没有输入]")
        return rst
    
    def dump_history(self, owner:str) -> Generator[str, Any, None]:
        m_list = self.get_memory(owner).messages
        
        for item in m_list:
            v = str(item.message.get("content"))
            yield f"data: {json.dumps({'text': v, 'done': False})}\n\n"
            yield f"data: {json.dumps({'text': '\n\n---------------------------\n\n', 'done': False})}\n\n"
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"