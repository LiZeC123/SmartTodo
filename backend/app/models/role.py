from dataclasses import dataclass

from app.models.memory import KB, MemoryPolicy

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


@dataclass(slots=True)
class RoleConfig:
    name: str  # 角色姓名
    short_desc: str  # 角色的简短描述
    memory_policy: str  # 使用记忆的策略
    enable_tools: bool  # 是否允许调用工具
    visible_in_rumor: bool  # 是否在流言蜚语系统中可见(可以产生传闻并被其他角色获知)
    long_desc: str  # 角色的详细设定

    def get_self_desc(self):
        return f"你是一位{self.short_desc}, 名叫{self.name}. {self.long_desc}"

    def get_memory_policy(self) -> MemoryPolicy:
        policy = MemoryPolicyDict.get(self.memory_policy)
        return policy if policy else DefaultMemoryPolicy


DefaultRoleConfig = RoleConfig(
    name="默认助手",
    enable_tools=False,
    visible_in_rumor=False,
    short_desc="有用的助手.",
    long_desc="",
    memory_policy="None",
)
