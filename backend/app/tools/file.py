import os
from os.path import join

from app.models.item import Item
from app.tools.logger import logger
from app.tools.web import download

FILE_FOLDER = "data/filebase"

def create_upload_file(f):
    """将上传的文件保存到服务器"""
    path = join(FILE_FOLDER, f.filename)
    f.save(path)
    url = path.replace("\\", "/").replace(FILE_FOLDER, '/file')
    return f.filename, url

def create_download_file(file_url: str) -> str:
    """从指定的URL下载文件到服务器"""
    path = download(file_url, FILE_FOLDER)
    return path.replace(FILE_FOLDER, '/file').replace("\\", "/")

def delete_file_from_url(url: str) -> bool:
    filename = url.replace("/file", FILE_FOLDER)
    try:
        os.remove(filename)
        return True
    except FileNotFoundError:
        # 对于文件没有找到这种情况, 视为删除成功
        logger.warnning(f"File Not Found: {filename}")
        return True
