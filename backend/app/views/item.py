from typing import Dict, Sequence

from flask import Blueprint, request

from app import db
from app.models.item import Item
from app.services.item_manager import ItemManager
from app.tools.exception import IllegalArgumentException
from app.tools.time import parse_deadline_timestamp
from app.views.authority import authority_check
from app.views.tool import get_xid_from_request, try_get_parent_from_request

item_bp = Blueprint('item', __name__)
item_manager = ItemManager(db)


# ####################### API For Item #######################
@item_bp.post("/api/item/create")
@authority_check()
def create_item(owner: str):
    f: Dict = request.get_json()
    item = Item(name=f['name'], item_type=f['itemType'], owner=owner)

    if "deadline" in f:
        item.deadline = parse_deadline_timestamp(f["deadline"])

    if "repeatable" in f:
        item.repeatable = bool(f["repeatable"])

    if "specific" in f:
        item.specific = int(f["specific"])

    if "parent" in f:
        item.parent = int(f["parent"])

    if "tags" in f:
        item.tags = ",".join(f["tags"])

    item_manager.create(item)


@item_bp.post('/api/item/getAll')
@authority_check()
def get_all_item(owner: str):
    parent = try_get_parent_from_request()
    return item_manager.select_all(owner=owner, parent=parent)


@item_bp.post('/api/item/getActivate')
@authority_check()
def get_activate_item(owner: str):
    parent = try_get_parent_from_request()
    return item_manager.select_activate(owner, parent=parent)


@item_bp.post('/api/item/back')
@authority_check()
def back_item(owner: str) -> bool:
    xid = get_xid_from_request()
    return item_manager.undo(xid=xid, owner=owner)


@item_bp.post("/api/item/remove")
@authority_check()
def remove_item(owner: str):
    iid = get_xid_from_request()
    return item_manager.remove_by_id(xid=iid, owner=owner)


@item_bp.post('/api/item/incExpTime')
@authority_check()
def increase_expected_tomato(owner: str) -> bool:
    xid = get_xid_from_request()
    return item_manager.increase_expected_tomato(xid=xid, owner=owner)


@item_bp.post('/api/item/incUsedTime')
@authority_check()
def increase_used_tomato(owner: str) -> bool:
    xid = get_xid_from_request()
    return item_manager.finish_used_tomato(xid=xid, owner=owner)


@item_bp.post('/api/item/toTodayTask')
@authority_check()
def to_today_task(owner: str) -> bool:
    xid = get_xid_from_request()
    return item_manager.to_today_task(xid=xid, owner=owner)


@item_bp.post("/api/item/getTitle")
@authority_check()
def get_title(owner: str):
    iid = get_xid_from_request()
    return item_manager.get_title(iid, owner)


@item_bp.post("/api/item/getTomato")
@authority_check()
def get_tomato_item(owner: str):
    return item_manager.get_tomato_item(owner)


@item_bp.post("/api/item/getItemWithSubTask")
@authority_check()
def get_item_with_sub_task(owner: str):
    return item_manager.get_item_with_sub_task(owner)


@item_bp.post("/api/item/getDeadlineItem")
@authority_check()
def get_deadline_item(owner: str):
    return item_manager.get_deadline_item(owner)


def get_required_value_from_request(f: Dict, names: Sequence[str]) -> tuple:
    rst = []
    for name in names:
        v = f.get(name)
        if v is None:
            raise IllegalArgumentException(f"fail to get {name} from request")
        rst.append(v)
    return tuple(rst)
