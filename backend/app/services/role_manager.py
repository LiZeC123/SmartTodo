import json
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class RoleConfig:
    name: str  # 角色姓名
    enable_tools: bool  # 是否允许调用工具
    memory_compress: str  # 记忆压缩策略
    enable_rumor: bool  # 是否启用流言蜚语系统(获得流言蜚语信息)
    visible_in_rumor: bool  # 是否在流言蜚语系统中可见(可以产生传闻并被其他角色获知)
    short_desc: str  # 角色的简短描述
    long_desc: str  # 角色的详细设定
    memory_policy: str  # 使用记忆的策略

    def get_self_desc(self):
        return f"你是一位{self.short_desc}, 名叫{self.name}. {self.long_desc}"


DefaultRoleConfig = RoleConfig(
    name="默认助手",
    enable_tools=False,
    memory_compress="No",
    enable_rumor=False,
    visible_in_rumor=False,
    short_desc="有用的助手.",
    long_desc="",
    memory_policy="None",
)


class RoleManager:
    def __init__(self) -> None:
        self.role_map = {item.name: item for item in self.get_role_list()}

    def get_role_map(self) -> dict[str, RoleConfig]:
        return {item.name: item for item in self.get_role_list()}

    def get_role(self, *, name: str = "", keyword: str = "") -> RoleConfig:
        """
        获取角色配置信息, 可以使用角色名进行精确匹配或者按照关键词在角色描述中进行匹配
        同时指定角色名和关键词时以角色名查找优先. 没有匹配结果时返回默认角色配置
        """
        if name:
            return self.role_map.get(name, DefaultRoleConfig)

        it = (role for _, role in self.role_map.items() if keyword in role.get_self_desc())
        return next(it, DefaultRoleConfig)

    def get_role_list(self) -> Iterable[RoleConfig]:
        try:
            return self.__load_file()
        except OSError:
            # 文件不存在时, 直接返回空即可, 相当于没有额外的角色设定
            return []

    def reload(self):
        self.role_map = {item.name: item for item in self.get_role_list()}

    def __load_file(self) -> Iterable[RoleConfig]:
        with open("config/role/Assistant.jsonl") as f:
            return [RoleConfig(**json.loads(s)) for role in f if (s := role.strip()) != "" and not s.startswith("//")]
