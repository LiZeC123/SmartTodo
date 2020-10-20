import os
import shutil
import traceback
from os import mkdir
from os.path import exists

from entity import Item
from tool4log import logger
from tool4web import download


def copy_file(src: str, dst: str):
    r = shutil.copyfile(src, dst)
    logger.info(f"{__name__}: Copy Data File: {r}")


class FileManager:
    _USER_FOLDER = "database"
    _UPLOAD_FOLDER = "filebase"
    _DOWNLOAD_FOLDER = "static/file"

    def __init__(self):
        if not exists(FileManager._UPLOAD_FOLDER):
            mkdir(FileManager._USER_FOLDER)
        if not exists(FileManager._DOWNLOAD_FOLDER):
            mkdir(FileManager._DOWNLOAD_FOLDER)

    @staticmethod
    def save_upload_file(f):
        name = os.path.join(FileManager._UPLOAD_FOLDER, f.filename)
        f.save(name)
        return f.filename, f"file/{f.filename}"

    @staticmethod
    def download_file(item: Item):
        # 由于当前是多线程模型, 因此可以在请求线程上直接执行下载操作
        # 等待下载完毕后再返回结果, 从而简化操作
        remote_url = item.name
        # 下载到静态文件目录, 因此文件路径也是访问的URL路径
        item.url = download(remote_url, FileManager._DOWNLOAD_FOLDER)

    @staticmethod
    def remove(filename):
        try:
            os.remove(filename)
        except OSError:
            logger.warn(f"{FileManager.__name__}: Fail to Remove File: Name = {filename}")
            traceback.print_exc()

    @staticmethod
    def backup_database_file(username):
        src = os.path.join(FileManager._USER_FOLDER, f"{username}.json")
        dst = os.path.join(FileManager._DOWNLOAD_FOLDER, f"{username}.json")
        copy_file(src, dst)
        return f"/smart-todo/{dst}"

    def file2remote(self):
        pass
