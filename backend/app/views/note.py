from flask import Blueprint, request

from app import item_manager
from app.views.authority import authority_check
from app.views.tool import get_xid_from_request

note_bp = Blueprint('note', __name__)


@note_bp.post('/api/note/content')
@authority_check()
def note_content(owner: str):
    nid = get_xid_from_request()
    return item_manager.get_note(nid, owner=owner)


@note_bp.post('/api/note/update')
@authority_check()
def note_update(owner: str):
    nid = get_xid_from_request()
    content = request.get_json().get("content")
    item_manager.update_note(nid, owner=owner, content=content)
