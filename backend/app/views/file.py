from flask import Blueprint, request

from app import item_manager
from app.views.authority import authority_check

file_bp = Blueprint('file', __name__)


@file_bp.post("/api/file/upload")
@authority_check()
def file_do_upload(owner: str):
    file = request.files['myFile']
    parent = int(request.form.get('parent', '0'))

    # 0表示不属于任何类型，转换为None类型进行存储
    if parent == 0:
        parent = None

    item_manager.create_upload_file(file, parent, owner)
    return True
