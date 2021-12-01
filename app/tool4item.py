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
        elif item['is_delete']:
            return "delete"
        else:
            return item['tomato_type']

    return group_by


def where_select_activate_with(owner: str, parent: int):
    def select(item: dict) -> bool:
        return owner == item['owner'] and parent == item['parent'] and item['tomato_type'] == 'activate'

    return select


def where_select_all_file(item: dict) -> bool:
    return item['item_type'] == 'file'


def where_can_delete(item: dict) -> bool:
    return item['repeatable'] is False and item['specific'] == 0 and item['finish_time'] is not None \
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


def select_id(item: dict):
    return item['id']


def select_title(item: dict):
    return item['name']


def where_unreferenced(parent: list):
    return lambda item: item['parent'] != 0 and item['parent'] not in parent


def undo_item(item: dict):
    item['create_time'] = now_str()
    item['tomato_type'] = 'activate'
    logger.info(f"Undo Item {item['name']}")


def inc_expected_tomato(item: dict):
    item['expected_tomato'] += 1


def inc_used_tomato(item: dict):
    item['used_tomato'] += 1


def urgent_task(item: dict):
    item['tomato_type'] = "urgent"


def today_task(item: dict):
    item['tomato_type'] = "today"


def where_update_repeatable_item(item: dict) -> bool:
    return item['repeatable'] is True and item['finish_time'] is not None


def update_repeatable_item(item: dict) -> NoReturn:
    finish_day = get_day_from_str(item['finish_time'])
    # 如果小于当前日期, 则重置
    if finish_day < today():
        item['create_time'] = now_str()
        item['finish_time'] = None
        logger.info(f"Reset Repeatable Item {item['name']} To Todo")


def update_note_url(item: dict) -> NoReturn:
    item['url'] = f"note/{item['id']}"
