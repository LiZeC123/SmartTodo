from typing import NoReturn

from tool4log import logger
from tool4time import now_str, get_day_from_str, today


def group_all_item_with(owner: str, parent: int):
    def group_by(item: dict) -> str:
        if owner != item['owner'] or parent != item['parent']:
            return "miss"
        else:
            return item['tomato_type']

    return group_by


def group_today_task_by_parent(owner: str):
    def group_by(item: dict) -> str:
        if owner == item['owner'] and item['tomato_type'] == 'today':
            return str(item['parent'])
        else:
            return "miss"

    return group_by


def where_select_activate_with(owner: str, parent: int):
    def select(item: dict) -> bool:
        return owner == item['owner'] and parent == item['parent'] and item['tomato_type'] == 'activate'

    return select


def where_select_all_file(item: dict) -> bool:
    return item['item_type'] == 'file'


def where_can_delete(item: dict) -> bool:
    # 1. 不是不可回收的特殊类型
    # 2. 处于完成状态
    return item['repeatable'] is False and item['specific'] == 0 \
           and item['expected_tomato'] == item['used_tomato']


def where_id_equal(iid: int):
    return lambda item: item['id'] == iid


def where_equal(xid: int, owner: str):
    return lambda item: item['id'] == xid and item['owner'] == owner


def where_contain_name(name: str, parent: int, owner: str):
    return lambda item: name in item['name'] and item['parent'] == parent and item['owner'] == owner


def select_id(item: dict):
    return item['id']


def select_title(item: dict):
    return item['name']


def where_unreferenced(parent: list):
    return lambda item: item['parent'] != 0 and item['parent'] not in parent


def undo_item(item: dict):
    item['create_time'] = now_str()
    item['tomato_type'] = 'activate'
    logger.info(f"回退任务到活动列表: {item['name']}")


def inc_expected_tomato(item: dict):
    item['expected_tomato'] += 1


def inc_used_tomato(item: dict):
    if item['habit_expected'] != 0:
        if get_day_from_str(item['last_check_time']) != today():
            item['habit_done'] += 1

    if item['used_tomato'] < item['expected_tomato']:
        logger.info("完成任务: " + item['name'])
        item['used_tomato'] += 1


def urgent_task(item: dict):
    item['create_time'] = now_str()
    item['tomato_type'] = "urgent"


def today_task(item: dict):
    item['create_time'] = now_str()
    item['tomato_type'] = "today"


def where_update_repeatable_item(item: dict) -> bool:
    return item['repeatable'] is True


def update_repeatable_item(item: dict) -> NoReturn:
    # item['create_time'] = now_str()
    item['used_tomato'] = 0
    logger.info(f"重置可重复任务: {item['name']}")


def update_note_url(item: dict) -> NoReturn:
    item['url'] = f"note/{item['id']}"


def rename(new_name):
    def f(item: dict):
        item['name'] = new_name

    return f
