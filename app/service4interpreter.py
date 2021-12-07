from entity import Item
from tool4log import logger


class OpInterpreter:
    def __init__(self, manager):
        self.manager = manager

    def batch_create_item(self, data: str, parent: int, owner: str):
        names = [d.strip() for d in data.split("-") if not d.isspace()]
        for name in names:
            item = Item(0, name, "single", owner)
            item.parent = parent
            self.manager.create(item)

    def exec_function(self, command: str, data: str, parent: int, owner: str):
        if command == "m":
            return self.batch_create_item(data, parent, owner)
        else:
            logger.error("Unknown Command")
