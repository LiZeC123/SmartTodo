from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

KB = 1024
MinCompressionSize = 2 * KB


# 记忆项目按照类型存储, 可以灵活的增减记忆类型, 同时在需要时按需加载记忆项目, 处理更灵活. 只新增不更新有利于回滚.
class MemoryDetailType:
    # 已废弃, 不存在此类型
    # ToDoItem = 1

    RoleSetting = 2  # 角色或者背景设定
    RecentTopic = 3
    Preference = 4  # 用户偏好预测
    Diary = 5  # 日记

    # 以下三个类型为固化类型, 总结合并之前的相关内容, 同时也作为水位线, 表示再此之前的项废弃
    FixedSetting = 6  # 固化角色设定
    FixedPreference = 7  # 固化角色偏好
    Milestone = 8  # 里程碑事件

    Thinking = 9  # 模型思考内容
    StartTime = 10  # 对话历史起始标记, 该时间之后的对话保持原始内容
    Rumor   = 11 # 流言蜚语


class MemoryDetail(Base):
    """助手记忆详细表, 按照时间顺序存储助手的各种类型的记忆信息, 记忆内容只新增不原地更新, 使用时按需加载最新的记忆"""

    __tablename__ = "assistant_memory_detail"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(15), nullable=False)
    assistant_name: Mapped[str] = mapped_column(String(15), nullable=False)
    tag: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 消息类型, 见 MemoryDetailType
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 记忆的内容发生的时间

    # 定义联合索引
    __table_args__ = (
        # 查询用户的某个助手的指定类型的记忆
        Index("idx_memory_detail_owner_role_tag", "owner", "assistant_name", "tag"),
    )


def make_memory_detail(content, *, reason="", assistant_name: str, owner: str, tag: int, content_time: datetime):
    """创建一个新的记忆详情项. 注意content_time对应内容本身的时间而不是创建该项记忆的时间"""
    return MemoryDetail(
        owner=owner, assistant_name=assistant_name, tag=tag, content=content, reason=reason, content_time=content_time
    )


@dataclass
class CompressionPolicy:
    """
    压缩策略由原始文本的天数和字符数控制, 取两者中保留内容最多的.
    例如day_delta=1, char_cost=3K时, 则无论昨天的文本有多少内容, 至少保留1天的对话内容. 如果昨天的对话内容不足3KB, 则会向前加载更多天的对话, 直到超过3KB
    """

    day_delta: int  # 始终保留原始聊天上下文的天数
    char_cost: int  # 至少保留的对话文本字符数

    @staticmethod
    def get_policy(policy_name: str) -> "CompressionPolicy":
        if policy_name == "Aggressive":
            # 如果剩余的聊天内容太短, 会对聊天风格产生明显的影响, 导致一些难以量化但是可以察觉出来的微妙变化
            # 因此即使是最激进的压缩模式, 也需要保留一些内容
            return CompressionPolicy(day_delta=1, char_cost=6 * KB)
        if policy_name == "Lazy":
            return CompressionPolicy(day_delta=1, char_cost=14 * KB)

        # 默认 Moderate
        return CompressionPolicy(day_delta=1, char_cost=10 * KB)


@dataclass
class MemoryPolicy:
    """
    记忆策略控制角色使用和压缩记忆的各项参数配置, 决定了角色的记忆使用倾向和压缩频率.
    使用不同的配置, 将使得对话产生不同偏向的影响. 常见策略包括 S: 设定优先 D:连续性优先 T: 话题优先
    不同策略具有不同的等级, 一般数字越大, 则记忆的长度越短.
    """

    enable_role_setting: bool
    enable_preference: bool
    max_topic_num: int
    max_diary_num: int
    raw_content_size: int

    @staticmethod
    def get_policy(policy_name: str) -> "MemoryPolicy":
        if policy_name == "S1":
            # 角色设定优先, 适合人设与故事背景会缓慢变化, 但对于对话连续性要求一般的场景
            return MemoryPolicy(
                enable_role_setting=True,
                enable_preference=False,
                max_topic_num=0,
                max_diary_num=2,
                raw_content_size=5 * KB,
            )
        if policy_name == "S2":
            # 角色设定优先, 类似于S1, 但对于对话连续性要求更低
            return MemoryPolicy(
                enable_role_setting=True,
                enable_preference=False,
                max_topic_num=0,
                max_diary_num=1,
                raw_content_size=3 * KB,
            )
        if policy_name == "D1":
            # 对话连续性优先, 适合人设几乎不变, 话题快速更换的场景, 但需要对整体一致性要求较高的场景
            return MemoryPolicy(
                enable_role_setting=False,
                enable_preference=False,
                max_topic_num=0,
                max_diary_num=3,
                raw_content_size=3 * KB,
            )
        if policy_name == "D2":
            # 对话连续性优先, 类似D1, 但导入记忆更少, 更轻量
            return MemoryPolicy(
                enable_role_setting=False,
                enable_preference=False,
                max_topic_num=0,
                max_diary_num=2,
                raw_content_size=3 * KB,
            )
        if policy_name == "T1":
            # 话题优先, 适合人设几乎不会变化, 且历史对话没有太大关联, 经常讨论不同话题的场景
            return MemoryPolicy(
                enable_role_setting=False,
                enable_preference=False,
                max_topic_num=12,
                max_diary_num=2,
                raw_content_size=1 * KB,
            )

        # 默认 None, 禁用所有记忆内容
        return MemoryPolicy(
            enable_role_setting=False,
            enable_preference=False,
            max_topic_num=0,
            max_diary_num=0,
            raw_content_size=6 * KB,
        )

    @staticmethod
    def to_str(policy_name: str) -> str:
        if policy_name.startswith("S"):
            return f"角色设定优先({policy_name})"
        if policy_name.startswith("D"):
            return f"对话连续性优先({policy_name})"
        if policy_name.startswith("T"):
            return f"话题优先({policy_name})"
        if policy_name == "None":
            return "未开启记忆策略"

        return f"无效的记忆策略({policy_name})"
