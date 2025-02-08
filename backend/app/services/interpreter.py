import shutil
from typing import Optional

from app.models.base import ItemType, TomatoType
from app.models.item import Item
from app.tools.exception import IllegalArgumentException, BaseSmartTodoException
from app.services.item_manager import ItemManager
from app.tools.logger import logger
from app.tools.time import now_str_fn


class OpInterpreter:
    def __init__(self, item_manager: ItemManager):
        self.item_manager = item_manager

    def batch_create_item(self, data: str, parent: Optional[int], owner: str):
        names = [d.strip() for d in data.split("-") if not d.isspace()]
        for name in names:
            item = Item(name=name, item_type=ItemType.Single, tomato_type=TomatoType.Activate, owner=owner,
                        parent=parent)
            self.item_manager.create(item)

    def instance_backup(self, parent: Optional[int], owner: str):
        name = f"SmartTodo_Database({now_str_fn()}).db"
        shutil.copy("data/data.db", f"data/filebase/{name}")
        item = Item(name=f"{name}", item_type=ItemType.File, owner=owner, parent=parent, url=f"/file/{name}")
        self.item_manager.base_manager.create(item)

    def split_item_with_number(self, name: str, num: int, suffix: str, parent: Optional[int], owner: str):
        subtasks = [f"第{i + 1}{suffix}" for i in range(num)]
        return self.split_item_with_subtask(name, subtasks, parent, owner)

    def split_item_with_subtask(self, name, subtasks: list, parent: Optional[int], owner: str):
        item = self.item_manager.get_unique_or_null_item_by_name(name, parent, owner)
        if item is not None:
            name = item.name
        for subtask in reversed(subtasks):
            sub_item = Item(name=f"{name}：{subtask}", item_type=ItemType.Single, tomato_type=TomatoType.Activate,
                            owner=owner, parent=parent)
            self.item_manager.create(sub_item)

    def renew(self, name: str, renew_day: int, parent: Optional[int], owner: str):
        item = self.item_manager.get_unique_item_by_name(name, parent, owner)
        self.item_manager.renew(item.id, item.owner, renew_day)

    def set_tag(self, name: str, tag: str, parent: Optional[int], owner: str):
        item = self.item_manager.get_unique_item_by_name(name, parent, owner)
        item.tags = tag if item.tags == "" else f"{item.tags},{tag}"

    def exec_function(self, command: str, data: str, parent: Optional[int], owner: str):
        logger.info(f"执行指令: {command} 指令数据: {data} 父任务ID: {parent} 执行人: {owner}")
        try:
            self.exec_function_with_exception(command, data, parent, owner)
        except BaseSmartTodoException as e:
            logger.exception(e)

    def exec_function_with_exception(self, command: str, data: str, parent: Optional[int], owner: str):
        if command == "m":
            return self.batch_create_item(data, parent, owner)
        elif command == "backup":
            return self.instance_backup(parent, owner)
        elif command == "gc":
            return self.item_manager.garbage_collection()
        elif command == "sn":
            name, num, suffix = parse_sn_data(data)
            return self.split_item_with_number(name, num, suffix, parent, owner)
        elif command == "sx":
            name, subtasks = parse_sx_data(data)
            return self.split_item_with_subtask(name, subtasks, parent, owner)
        elif command == "renew":
            name, renew_day = parse_renew_data(data)
            self.renew(name, renew_day, parent, owner)
        elif command == "tag":
            name, tag = parse_tag_data(data)
            self.set_tag(name, tag, parent, owner)
        else:
            raise IllegalArgumentException(f"未知的指令: {command} 指令数据: {data} 父任务ID: {parent} 执行人: {owner}")


def not_empty(s):
    return len(s) != 0


def parse_sn_data(data):
    # 被拆分项目名称 拆分数量 拆分后缀
    try:
        elem = list(filter(not_empty, data.split(" ")))
        if len(elem) == 3:
            name = elem[0]
            num = int(elem[1])
            suffix = elem[2]
            return name, num, suffix
        elif len(elem) == 2:
            name = elem[0]
            num = int(elem[1])
            return name, num, "部分"
        elif len(elem) == 1:
            name = elem[0]
            return name, 3, "部分"
        else:
            raise IllegalArgumentException("解析sn指令数据失败: 参数数量不匹配")
    except ValueError:
        raise IllegalArgumentException("解析sn指令数据失败")


def parse_sx_data(data):
    # 被拆分项目名称  - 子任务1名称 -子任务2名称 ...
    elem = data.split("-")
    if len(elem) >= 2:
        name = elem[0].strip()
        subtasks = [e.strip() for e in elem[1:] if not e.isspace()]
        return name, subtasks
    else:
        raise IllegalArgumentException("解析sx指令数据失败: 参数数量不匹配")


def parse_renew_data(data):
    try:
        elem = list(filter(not_empty, data.split(" ")))
        name = elem[0]
        renew_day = int(elem[1])
        return name, renew_day
    except (ValueError, IndexError):
        raise IllegalArgumentException("解析renew指令数据失败")


def parse_tag_data(data):
    try:
        elem = list(filter(not_empty, data.split(" ")))
        name = elem[0]
        tag = elem[1]
        return name, tag
    except (ValueError, IndexError):
        raise IllegalArgumentException("解析tag指令数据失败")