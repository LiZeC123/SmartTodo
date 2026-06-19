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
    Rumor = 11  # [已废弃] 流言蜚语


class MemoryDetail(Base):
    """
    助手记忆详细表, 按照时间顺序存储助手的各种类型的记忆信息
    记忆内容只新增不原地更新, 使用时结合水位线按需加载最新的记忆
    """

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
class MemoryPolicy:
    """
    记忆策略控制角色使用和压缩记忆的各项参数配置, 决定了角色的记忆使用倾向和压缩频率.
    使用不同的配置, 将使得对话产生不同偏向的影响. 常见策略包括 S: 设定优先 D:连续性优先 T: 话题优先
    不同策略具有不同的等级, 一般数字越大, 则记忆的长度越短.

    日记和话题的区别: 日记是一般性的记忆总结, 话题是针对性的记忆总结.
    有些助手不需要太强的针对性, 每天都要处理新的信息, 因此保持大致的记忆即可. 有的助手处理的信息比较少, 保持上一次话题的连续性更重要一些.
    """

    # 是否启用新增角色设定
    enable_role_setting: bool

    # 是否启用用户偏好预测
    enable_preference: bool

    # 最大引入的近期话题数量, 对于主要为讨论的场景, 需要保留更多的话题
    max_topic_num: int

    # 最大日记数量, 对于对话连贯性的场景, 需要更多日记
    max_diary_num: int

    # 原始文本保留的字符数, 无论采用何种压缩方式, 都需要保留一部分上下文, 否则会使聊天风格产生一些微妙的变化
    # 相对地, 如果觉得当前的聊天风格有一些腐化, 也可以通过清除保留的上下文, 使得风格重置
    raw_content_size: int

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


MemoryPolicyDict = {
    # 角色设定优先, 适合人设与故事背景会缓慢变化, 但对于对话连续性要求一般的场景
    "S1": MemoryPolicy(
        enable_role_setting=True, enable_preference=False, max_topic_num=0, max_diary_num=5, raw_content_size=15 * KB
    ),
    # 角色设定优先, 类似于S1, 但对于对话连续性要求更低
    "S2": MemoryPolicy(
        enable_role_setting=True, enable_preference=False, max_topic_num=0, max_diary_num=3, raw_content_size=9 * KB
    ),
    # 对话连续性优先, 适合人设几乎不变, 话题快速更换的场景, 但需要对整体一致性要求较高的场景
    "D1": MemoryPolicy(
        enable_role_setting=False, enable_preference=False, max_topic_num=0, max_diary_num=7, raw_content_size=15 * KB
    ),
    # 对话连续性优先, 类似D1, 但导入记忆更少, 更轻量
    "D2": MemoryPolicy(
        enable_role_setting=False, enable_preference=False, max_topic_num=0, max_diary_num=5, raw_content_size=9 * KB
    ),
    # 话题优先, 适合人设几乎不会变化, 且历史对话没有太大关联, 经常讨论不同话题的场景
    "T1": MemoryPolicy(
        enable_role_setting=False, enable_preference=False, max_topic_num=12, max_diary_num=5, raw_content_size=5 * KB
    ),
}

DefaultMemoryPolicy = MemoryPolicy(
    enable_role_setting=False, enable_preference=False, max_topic_num=0, max_diary_num=0, raw_content_size=10 * KB
)


def get_policy_from(policy_name: str) -> MemoryPolicy:
    policy = MemoryPolicyDict.get(policy_name)
    return policy if policy else DefaultMemoryPolicy
