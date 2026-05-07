from datetime import datetime
from typing import Optional

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)
from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


from app.models.base import Base
from app.tools.exception import IllegalArgumentException
from app.tools.time import now


class AssistantType:
    User = "user"
    Assistant = "assistant"
    Tool = "tool"

class AssistantModeType:
    Assistant = 0
    RolePlaying = 1
    
class AssistantTagType:
    RoleSwitch = 1
    ModeSwich = 2

class AssistantHistory(Base):
    __tablename__ = "assistant_history"

    id: Mapped[int]                     = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str]                   = mapped_column(String(10), nullable=False)
    content: Mapped[str]                = mapped_column(Text, nullable=False, default='')
    create_time: Mapped[datetime]       = mapped_column(DateTime, nullable=False, default=now)
    system_inject_content: Mapped[str]  = mapped_column(Text, nullable=False, default='')   # 系统自动注入的待办相关信息
    tool_call_id:Mapped[str]            = mapped_column(String, nullable=False, default='') # 工具的ID
    owner: Mapped[str]                  = mapped_column(String(15), nullable=False)
    
    assistant_name: Mapped[str]         = mapped_column(String(15), nullable=False, default='') # 助理的角色名
    assistant_mode: Mapped[int]         = mapped_column(Integer, nullable=False, default=0)     # 助理的模式 0: 助理模式 1: 扮演模式
    
    # 扩展字段, 后续可能会对消息增加额外的标记
    tag: Mapped[int]                    = mapped_column(Integer, nullable=False, default=0)     # 消息标记 0: 无标记 


    # 定义联合索引
    __table_args__ = (
        # 查询单个用户聊天历史
        Index('idx_history_owner_time', "owner", "create_time"),
    )

    def to_openai(self) -> ChatCompletionMessageParam:
        if self.role == "system":
            return ChatCompletionSystemMessageParam(content=self.content, role="system")
        if self.role == "user":
            content = f"当前时间: {self.create_time.strftime("%Y-%m-%d %H:%M:%S %a")}\n{self.system_inject_content}\n\n---\n\n{self.content}"
            return ChatCompletionUserMessageParam(content=content, role="user")
        if self.role == 'assistant':
            return ChatCompletionAssistantMessageParam(content=self.content, role='assistant')
        if self.role == 'tool':
            return ChatCompletionToolMessageParam(content=self.content, role='tool', tool_call_id=self.tool_call_id)
        raise IllegalArgumentException(f"unknown role: {self.role}")

    def to_web(self) -> Optional[str]:
        if self.role in ['system', 'tool']:
            return None
        if self.role in "assistant":
            return self.content
        if self.role == 'user':
            return self.content if self.content != "" else "[用户没有任何输入]"
        
    def to_dump(self) -> Optional[str]:
        if self.role in ['system', 'tool']:
            return None
        if self.role in "assistant":
            return f"{self.role}:\n{self.content}\n"
        if self.role == 'user':
            return f"{self.role}:\n[当前时间: {self.create_time.strftime("%Y-%m-%d %H:%M:%S %a")}\n{self.system_inject_content}]\n{self.content}\n"

class AssistantStatus(Base):
    __tablename__ = "assistant_status"
    
    id: Mapped[int]                 = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]              = mapped_column(String(15), nullable=False)
    start_time: Mapped[datetime]    = mapped_column(DateTime, nullable=False, default=now)  # 用户聊天记录的起始时间
    assistant_name: Mapped[str]     = mapped_column(String(15), nullable=False, default='') # 当前助理的角色名
    assistant_desc: Mapped[str]     = mapped_column(Text, nullable=False, default='')       # 助理的角色描述
    assistant_mode: Mapped[int]     = mapped_column(Integer, nullable=False, default=0)     # 助理的模式 0: 助理模式 1: 扮演模式
    
    
def make_assistant_status(owner: str, start_time:datetime):
    return AssistantStatus(owner=owner, start_time=start_time)



class AssistantMemory(Base):
    """助手记忆表, 存储用户的每一个助理的记忆"""
    __tablename__ = "assistant_memory"
    
    id: Mapped[int]                 = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]              = mapped_column(String(15), nullable=False)
    assistant_name: Mapped[str]     = mapped_column(String(15), nullable=False, default='') # 当前助理的角色名
    short_term_memory: Mapped[str]  = mapped_column(String(15), nullable=False, default='')
    long_term_memory: Mapped[str]   = mapped_column(String(15), nullable=False, default='')
    processed_time: Mapped[datetime]= mapped_column(DateTime, nullable=False, default=datetime(year=2026, month=5, day=1)) # 记忆已经处理过的记录的时间
    
    def to_assistant(self):
        pass
    
    def to_dump(self) -> str:
        return f"角色名: {self.assistant_name}\n记忆处理时间: {self.processed_time}\n短期记忆:\n{self.short_term_memory}\n长期记忆:\n{self.long_term_memory}"