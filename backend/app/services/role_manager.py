import csv
from collections.abc import Iterable

from app.models.role import DefaultRoleConfig, RoleConfig


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
        configs = []
        with open("config/role/Assistant.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 布尔值转换：假设文件中为 'true'/'false' 或 'True'/'False'
                enable_tools = row["enable_tools"].strip().lower() == "true"
                visible_in_rumor = row["visible_in_rumor"].strip().lower() == "true"

                config = RoleConfig(
                    name=row["name"],
                    short_desc=row["short_desc"],
                    memory_policy=row["memory_policy"],
                    enable_tools=enable_tools,
                    visible_in_rumor=visible_in_rumor,
                    long_desc=row["long_desc"],
                )
                configs.append(config)
            return configs
