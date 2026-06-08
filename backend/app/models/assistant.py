import json
import warnings
from datetime import datetime

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
from app.models.exception import LLMIllegalStatusException
from app.tools.time import get_str_from_datetime, now


class AssistantType:
    User = "user"
    Assistant = "assistant"
    Tool = "tool"

class AssistantModeType:
    Assistant = 0
    RolePlaying = 1

class AssistantTagType:
    NoTag = 0
    Rumor = 1
    NewTopic = 2


Tag2Text = {
    AssistantTagType.NoTag: "[用户没有任何输入]",
    AssistantTagType.Rumor: "[助手收到了一些传闻]",
    AssistantTagType.NewTopic: "[助手发起了一个新话题]"
}


def assistant_mode_str(mode: int) -> str:
    if mode == AssistantModeType.Assistant:
        return "助理模式"
    if mode == AssistantModeType.RolePlaying:
        return "扮演模式"

    return "未知模式"

def parse_assistant_mode(mode: str) -> int:
    if mode in ['助理', '助理模式']:
        return AssistantModeType.Assistant
    if mode in ['扮演', '扮演模式']:
        return AssistantModeType.RolePlaying

    return AssistantModeType.RolePlaying

class History(Base):
    __tablename__ = "assistant_history"

    id: Mapped[int]                     = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str]                   = mapped_column(String(10), nullable=False)
    content: Mapped[str]                = mapped_column(Text, nullable=False, default='')
    create_time: Mapped[datetime]       = mapped_column(DateTime, nullable=False, default=now)
    system_inject_content: Mapped[str]  = mapped_column(Text, nullable=False, default='')   # 系统自动注入的待办相关信息
    tool_call_list_json:Mapped[str]     = mapped_column(String, nullable=False, default='') # 模型请求工具调用信息序列化为JSON
    tool_call_id:Mapped[str]            = mapped_column(String, nullable=False, default='') # 工具的ID
    owner: Mapped[str]                  = mapped_column(String(15), nullable=False)

    assistant_name: Mapped[str]         = mapped_column(String(15), nullable=False, default='') # 助理的角色名
    assistant_mode: Mapped[int]         = mapped_column(Integer, nullable=False, default=0)     # 助理的模式 0: 助理模式 1: 扮演模式

    # 扩展字段, 后续可能会对消息增加额外的标记
    tag: Mapped[int]                    = mapped_column(Integer, nullable=False, default=0)     # 消息标记 参考 AssistantTagType


    # 定义联合索引
    __table_args__ = (
        # 查询单个用户聊天历史
        Index('idx_history_owner_time', "owner", "create_time"),
    )

    def to_openai(self) -> ChatCompletionMessageParam:
        if self.role == "system":
            return ChatCompletionSystemMessageParam(content=self.content, role="system")
        if self.role == "user":
            content = f"当前时间: {self.create_time.strftime("%Y-%m-%d %H:%M:%S %a")}\n<info>{self.system_inject_content}</info>\n{self.content}"
            return ChatCompletionUserMessageParam(content=content, role="user")
        if self.role == 'assistant':
            if self.tool_call_list_json == '':
                return ChatCompletionAssistantMessageParam(content=self.content, role='assistant')
            else:
                tool_call_list = json.loads(self.tool_call_list_json)
                return ChatCompletionAssistantMessageParam(content=self.content, role='assistant', tool_calls=tool_call_list)
        if self.role == 'tool':
            return ChatCompletionToolMessageParam(content=self.content, role='tool', tool_call_id=self.tool_call_id)
        raise LLMIllegalStatusException(f"unknown role: {self.role}")

    def to_str_msg(self) -> str | None:
        if self.role in ['system', 'tool']:
            return None
        if self.role in "assistant":
            return self.content
        if self.role == 'user':
            return self.content if self.content else Tag2Text.get(self.tag)

    def to_web_json(self) -> dict:
        return {"role": self.role, "content": self.to_str_msg(), "createTime": get_str_from_datetime(self.create_time)}


    def to_dump(self) -> str | None:
        if self.role in ['system', 'tool']:
            return None
        if self.role in "assistant":
            return f"{self.role}:\n{self.content}\n\n-------------------------------\n\n"
        if self.role == 'user':
            return f"{self.role}: [当前时间: {self.create_time.strftime("%Y-%m-%d %H:%M:%S %a")}\n{self.system_inject_content}]\n{self.content}\n\n"

class Status(Base):
    __tablename__ = "assistant_status"

    id: Mapped[int]                 = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]              = mapped_column(String(15), nullable=False)
    assistant_name: Mapped[str]     = mapped_column(String(15), nullable=False, default='') # 当前助理的角色名
    assistant_mode: Mapped[int]     = mapped_column(Integer, nullable=False, default=0)     # 助理的模式 0: 助理模式 1: 扮演模式
    auto_continue: Mapped[int]      = mapped_column(Integer, nullable=False, default=0)     # 自动序列控制 0: 关闭自动续写 正数: 续写触发阈值, 回复消息字符数小于该值自动触发续写

def make_assistant_status(owner: str):
    return Status(owner=owner)


@warnings.deprecated("Use MemoryDetail instead")
class Memory(Base):
    """助手记忆表, 流水存储用户的每一个助理的记忆, 只插入不更新"""
    __tablename__ = "assistant_memory"

    id: Mapped[int]                 = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str]              = mapped_column(String(15), nullable=False)
    assistant_name: Mapped[str]     = mapped_column(String(15), nullable=False, default='') # 当前助理的角色名
    short_term_memory: Mapped[str]  = mapped_column(String(15), nullable=False, default='')
    long_term_memory: Mapped[str]   = mapped_column(String(15), nullable=False, default='')
    compression_reason: Mapped[str] = mapped_column(Text, nullable=False, default='') # 记忆压缩的思考过程
    rumor_reason: Mapped[str]       = mapped_column(Text, nullable=False, default='') # 流言蜚语扩散的思考过程
    processed_time: Mapped[datetime]= mapped_column(DateTime, nullable=False, default=datetime(year=2026, month=5, day=1)) # 已经处理过的记录的截止时间

    def deep_copy(self, processed_time:datetime) -> 'Memory':
        return Memory(owner=self.owner, assistant_name=self.assistant_name,
                      short_term_memory='', long_term_memory='', compression_reason='', rumor_reason='', processed_time=processed_time)

    def to_assistant(self) -> str:
        content = f"#内容说明\n这是你之前梳理的截止对话开始前你与用户之间的已经发生过的重要事件信息\n{self.long_term_memory}"
        return content

    def to_dump(self) -> str:
        return f"角色名: {self.assistant_name}\n记忆处理时间: {self.processed_time}\n短期记忆:\n{self.short_term_memory}\n长期记忆:\n{self.long_term_memory}"




