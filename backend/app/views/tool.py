from typing import Dict, Optional

from flask import request

from app.tools.exception import IllegalArgumentException

def get_xid_from_request() -> int:
    f: Dict = request.get_json()
    xid = f.get('id')
    if xid is None:
        raise IllegalArgumentException("fail to get id")
    return int(xid)

def try_get_parent_from_request() -> Optional[int]:
    f: Dict = request.get_json()
    parent = f.get("parent")
    if parent is None:
        return None

    return int(parent)