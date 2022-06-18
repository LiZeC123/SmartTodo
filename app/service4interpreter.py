from typing import Optional

import sqlalchemy as sal

from entity import Item, ItemType, db_session, TomatoType
from tool4log import logger
from tool4time import now_str_fn


class OpInterpreter:
    def __init__(self, manager):
        self.manager = manager

    def batch_create_item(self, data: str, parent: int, owner: str):
        names = [d.strip() for d in data.split("-") if not d.isspace()]
        for name in names:
            item = Item(name=name, item_type=ItemType.Single, tomato_type=TomatoType.Today, owner=owner, parent=parent)
            self.manager.create(item)

    def instance_backup(self, parent: int, owner: str):
        import shutil
        name = f"SmartTodo_Database({now_str_fn()})"
        shutil.make_archive(f"data/filebase/{name}", 'zip', "data/database")
        item = Item(name=f"{name}.zip", item_type=ItemType.File, owner=owner, parent=parent, url=f"/file/{name}.zip")
        self.manager.item_manager.create(item)

    @staticmethod
    def get_item_by_name(name: str, parent: int, owner: str) -> Optional[Item]:
        pass
        stmt = sal.select(Item).where(Item.name.like(f"%{name}%"), Item.parent == parent, Item.owner == owner)
        items = db_session.execute(stmt).scalars().all()

        if len(items) != 1:
            logger.error(f"待办事项获取失败: 多个待办事项符合名称要求: {[p.name for p in items]}")
            return None
        return items[0]

    def split_item_with_number(self, name: str, num: int, suffix: str, parent: int, owner: str):
        subtasks = [f"第{i + 1}{suffix}" for i in range(num)]
        return self.split_item_with_subtask(name, subtasks, parent, owner)

    def split_item_with_subtask(self, name, subtasks: list, parent: int, owner: str):
        item = self.get_item_by_name(name, parent, owner)
        if item is not None:
            name = item.name
        for subtask in reversed(subtasks):
            sub_item = Item(name=f"{name}：{subtask}", item_type=ItemType.Single, tomato_type=TomatoType.Today,
                            owner=owner, parent=parent)
            self.manager.create(sub_item)

    def create_habit(self, data: str, parent: int, owner: str):
        name, count = parse_habit_data(data)
        item = Item(name=name, item_type=ItemType.Single, owner=owner, parent=parent)
        item.habit_expected = count
        item.repeatable = True
        self.manager.create(item)

    def exec_function(self, command: str, data: str, parent: int, owner: str):
        logger.info(f"执行指令: {command} 指令数据: {data} 父任务ID: {parent} 执行人: {owner}")
        if command == "m":
            return self.batch_create_item(data, parent, owner)
        elif command == "backup":
            return self.instance_backup(parent, owner)
        elif command == "gc":
            return self.manager.garbage_collection()
        elif command == "sn":
            name, num, suffix = parse_sn_data(data)
            return self.split_item_with_number(name, num, suffix, parent, owner)
        elif command == "sx":
            name, subtasks = parse_sx_data(data)
            return self.split_item_with_subtask(name, subtasks, parent, owner)
        elif command == "rename":
            old, new_name = data.split()
            item = self.get_item_by_name(old, parent, owner)
            if item is not None:
                item.name = new_name
                db_session.commit()
        elif command == "habit":
            self.create_habit(data, parent, owner)
        else:
            logger.error(f"未知的指令: {command} 指令数据: {data} 父任务ID: {parent} 执行人: {owner}")


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
            logger.error("解析sn指令数据失败: 参数数量不匹配")
    except ValueError:
        logger.error("解析sn指令数据失败: 数据解析失败")


def parse_sx_data(data):
    # 被拆分项目名称  - 子任务1名称 -子任务2名称 ...
    elem = data.split("-")
    if len(elem) >= 2:
        name = elem[0].strip()
        subtasks = [e.strip() for e in elem[1:] if not e.isspace()]
        return name, subtasks
    else:
        logger.error("解析sx指令数据失败: 参数数量不匹配")


def parse_habit_data(data):
    try:
        elem = list(filter(not_empty, data.split(" ")))
        name = elem[0]
        count = -1

        if len(elem) == 2:
            count = int(elem[1])

        return name, count
    except ValueError:
        return None, -1


if __name__ == '__main__':
    ans = parse_habit_data("")
    print(ans)
