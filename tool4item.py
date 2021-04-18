from typing import NoReturn

from tool4log import logger
from tool4time import now, today, get_day_from_str, get_datetime_from_str, now_str


def check_specific_item_is_todo(item):
    # 特定任务在每周设定的日期, 如果完成时间没有被更新,则重置到todo列表
    create_day = get_day_from_str(item['create_time'])
    if create_day.weekday() == today().weekday():
        if item['finish_time'] is None:
            # 没有完成时间则必定属于todo列表
            return True
        else:
            # 否则检查完成时间是否小于今天, 是则说明以前完成了, 但今天还需要重复完成
            finish_day = get_day_from_str(item['finish_time'])
            return finish_day < today()


def group_all_item_with(owner: str, parent: int):
    def group_by(item: dict) -> str:
        if owner != item['owner'] or parent != item['parent']:
            return "miss"
        if item['old'] is True:
            return "old"
        if item['finish_time'] is None:
            return "todo"
        if item['specific'] != 0:
            return "todo" if check_specific_item_is_todo(item) else "done"
        if item['repeatable'] is True:
            return "done"

        finish_day = get_day_from_str(item['finish_time'])
        if finish_day == today():
            return "done"

    return group_by


def where_select_todo_with(owner: str, parent: int):
    group_by = group_all_item_with(owner, parent)

    def select(item: dict) -> bool:
        return group_by(item) == 'todo'

    return select


def where_select_all_file(item: dict) -> bool:
    return item['item_type'] == 'file'


def where_can_delete(item: dict) -> bool:
    return item['item_type'] == 'single' and item['finish_time'] is not None \
           and get_day_from_str(item['finish_time']) != today()


def map_file(item):
    if item['item_type'] == "file":
        if item['finish_time'] is None:
            return "todo"
        finish_day = get_day_from_str(item['finish_time'])
        return "done" if finish_day == today() else "delete"
    return "delete"


def where_id_equal(iid: int):
    return lambda item: item['id'] == iid


def where_equal(xid: int, owner: str):
    return lambda item: item['id'] == xid and item['owner'] == owner


def finish_item(item: dict):
    item['finish_time'] = now_str()
    logger.info(f"Move Item {item['name']} To Done Lists")


def undo_item(item: dict):
    item['finish_time'] = None
    logger.info(f"Move Item {item['name']} To Todo Lists")


def old_item(item: dict):
    item['old'] = True
    logger.info(f"Move Item {item['name']} To Old Lists")


def where_update_urgent_level(item: dict) -> bool:
    return item['deadline'] is not None


def update_urgent_level(item: dict) -> NoReturn:
    deadline = get_datetime_from_str(item['deadline'])
    # 时间相减后的形式是 xx days, xx:xx:xx, 直接忽略不足一天的部分
    delta = (deadline - now()).days
    item['deadline'] = delta


def where_update_repeatable_item(item) -> bool:
    return item['repeatable'] is True and item['finish_time'] is not None


def update_repeatable_item(item) -> NoReturn:
    finish_day = get_day_from_str(item['finish_time'])
    # 如果小于当前日期, 则重置
    if finish_day < today():
        item['create_time'] = now_str()
        item['finish_time'] = None
        logger.info(f"DataManager: Reset Repeatable Item {item['name']} To Todo")


def update_note_url(item) -> NoReturn:
    item['url'] = f"note/{item.id}"
