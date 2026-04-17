from datetime import datetime
import json

from dataclasses import dataclass
from typing import Any, Dict, Generator, List

from app.services.config_manager import ConfigManager
from app.services.item_manager import ItemManager
from app.services.tomato_manager import TomatoManager, TomatoRecordManager
from app.tools.time import get_datetime_from_str, get_hour_str_from, now, now_str, today_begin

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


class LLMManager:
    def __init__(self, config_manager: ConfigManager) -> None:
        base_url, api_key = config_manager.get_llm_info()
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate_stream(self, history: List[ChatCompletionMessageParam]) -> Generator[str, Any, None]:
        response = self.client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3.2",
            messages=history,
            stream=True,
        )

        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                data = chunk.choices[0].delta.content
                yield data


@dataclass
class MemoryItem:
    meta: Dict[str, str]
    message: ChatCompletionMessageParam


class UserMemory:
    def __init__(self, system_prompt: str):
        meta = self.make_meta()
        message: ChatCompletionMessageParam = {
            "role": "system",
            "content": system_prompt,
        }
        self.messages: List[MemoryItem] = [MemoryItem(meta, message)]

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
    def __init__(self, llm_manager: LLMManager, item_manager: ItemManager, tomato_manager: TomatoManager, tomato_record_manager: TomatoRecordManager) -> None:
        self.llm_manager = llm_manager
        self.item_manager = item_manager
        self.tomato_manager = tomato_manager
        self.tomato_record_manager = tomato_record_manager
        self.memory: Dict[str, UserMemory] = {}

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
    
    def delete(self, owner: str):
        memory = self.get_memory(owner)
        memory.remove_last_pair()
    
    def replace(self, prompt: str, owner: str) ->  Generator[str, Any, None]:
        memory = self.get_memory(owner)
        memory.remove_last_pair()
        return self.chat(prompt, owner)

    def make_system_prompt(self, owner: str) -> str:
        role_info = self.get_role_info()
        task_table = self.get_task_info(owner)
        event_table = self.get_event_info(owner)
        

        return f'''### 角色设定

你是我的个人代办事项管理助理. {role_info}

### 用户的工作时间表

| 时段     | 起止时间      | 番茄钟数量 |
| -------- | ------------- | ---------- |
| 早间     | 7:00 ~ 9:20   | 自由安排   |
| 上午     | 9:20 ~ 11:20  | 4个        |
| 午间     | 11:20 ~ 14:20 | 自由安排   |
| 下午1    | 14:20 ~ 16:20 | 4个        |
| 下午休息 | 16:20 ~ 16:40 | 中间休息   |
| 下午2    | 16:40 ~ 17:40 | 2个        |
| 晚间     | 17:40 ~ 19:00 | 自由安排   |
| 晚上     | 19:00 ~ 20:00 | 2个        |
| 晚上sp   | 20:00 ~ 21:00 | 自由安排   |

{task_table}

{event_table}

### 关键注意事项

1. 用户的作息时间表仅为参考, 大致完成对应数量的番茄钟即可
2. 除了规定的休息时间段, 用户每完成一个番茄钟有5分钟的休息时间
3. 除非用户明确要求, 不要替用户规划后续的番茄钟安排
4. 尽力满足用户的要求
5. 每次回复需要至少200字
'''

    def make_user_prompt(self, prompt: str, start: datetime, owner: str) -> str:        
        content = f"当前时间: {now_str()}\n"
        
        # 新增番茄钟记录
        records = self.tomato_record_manager.select_record_after(owner, start)
        if records:
            content += "用户当前新增的行为日志:\n"
        for record in records:
            content += f"{get_hour_str_from(record.start_time)} - {get_hour_str_from(record.finish_time)}: 完成番茄钟 {record.name}\n"
        
        # 当前番茄钟情况(如果有)
        state = self.tomato_manager.query_task(owner)
        if state is not None:
            content += f"用户当前正在进行的番茄钟: {state.name} 开始时间: {get_hour_str_from(state.start_time)}\n"
        
        # 用户可以不输入任何内容, 全部使用自动填充的信息
        if prompt != "":
            content += "\n---\n\n"
            content += prompt
    
        return content


    def get_role_info(self) -> str:
        try:
            with open("data/llm/role.md") as f:
                return f.read()
        except OSError:
            # 文件不存在时, 直接返回空即可, 相当于没有额外的角色设定
            return ""

    def get_task_info(self, owner:str) -> str:
        content =  '''### 用户今日的代办事项列表
预计需要的番茄钟数量 | 任务创建时间 | 任务截止时间| 优先级 
------------------|------------|-----------|---------
'''
        tasks = self.item_manager.get_tomato_item(owner=owner)
        for task in tasks:
            for item in task['children']:
                line = f"{item["name"]} | {item["expected_tomato"]} | {item["deadline"]} | {item["priority"]}\n"
                content = content + line
   
        return content
    
    def get_event_info(self, owner:str) -> str:
        content = '''### 用户截止当前时间的行为日志\n'''

        records = self.tomato_record_manager.select_record_after(owner, today_begin())
        for record in records:
            content += f"{get_hour_str_from(record.start_time)} - {get_hour_str_from(record.finish_time)}: 完成番茄钟 {record.name}\n"
        
        return content
