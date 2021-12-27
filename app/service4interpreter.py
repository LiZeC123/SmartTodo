from entity import Item
from tool4log import logger
from tool4time import now_str_fn


class OpInterpreter:
    def __init__(self, manager):
        self.manager = manager

    def batch_create_item(self, data: str, parent: int, owner: str):
        names = [d.strip() for d in data.split("-") if not d.isspace()]
        for name in names:
            item = Item(0, name, "single", owner)
            item.parent = parent
            self.manager.create(item)

    def instance_backup(self, parent: int, owner: str):
        import shutil
        name = f"SmartTodo_Database({now_str_fn()})"
        shutil.make_archive(f"data/filebase/{name}", 'zip', "data/database")
        item = Item(0, f"{name}.zip", "file", owner)
        item.parent = parent
        item.url = f"/file/{name}.zip"
        self.manager.item_manager.create(item)

    def shrink_item_with_parent(self, parent: int, owner: str):
        return self.manager.shrink(parent, owner)

    def exec_function(self, command: str, data: str, parent: int, owner: str):
        logger.info(f"执行指令: {command} 指令数据: {data} 父任务ID: {parent} 执行人: {owner}")
        if command == "m":
            return self.batch_create_item(data, parent, owner)
        elif command == "backup":
            return self.instance_backup(parent, owner)
        elif command == "gc":
            return self.manager.garbage_collection()
        elif command == "shrink":
            return self.shrink_item_with_parent(parent, owner)
        else:
            logger.error(f"Unknown Command: {command} {data}")
