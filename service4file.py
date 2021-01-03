import os
import shutil
from os import mkdir
from os.path import exists, join

from entity import Item
from tool4log import logger
from tool4web import download


def copy_file(src: str, dst: str):
    shutil.copyfile(src, dst)
    logger.info(f"{FileManager.__name__}: Copy File From {src} to {dst}")


class FileManager:
    _USER_FOLDER = "database"
    _UPLOAD_FOLDER = "filebase"
    _DOWNLOAD_FOLDER = join("static", "file")
    _DOWNLOAD_URL = "static/file"  # 文件路径根据操作系统不同, 可能有不同的表示, 但URL只能使用反斜杠

    def __init__(self):
        if not exists(FileManager._UPLOAD_FOLDER):
            mkdir(FileManager._UPLOAD_FOLDER)
        if not exists(FileManager._DOWNLOAD_FOLDER):
            mkdir(FileManager._DOWNLOAD_FOLDER)

    def save_upload_file(self, f):
        name = join(FileManager._UPLOAD_FOLDER, f.filename)
        f.save(name)
        return f.filename, self.get_file_url(f.filename, filetype='private')

    @staticmethod
    def download_file(item: Item):
        # 由于当前是多线程模型, 因此可以在请求线程上直接执行下载操作
        # 等待下载完毕后再返回结果, 从而简化操作
        remote_url = item.name
        # 下载到静态文件目录, 因此文件路径也是访问的URL路径
        item.url = download(remote_url, FileManager._DOWNLOAD_FOLDER)

    def remove(self, filename, filetype=None):
        if filetype is not None:
            filename = self.get_file_full_name(filename, filetype)

        try:
            os.remove(filename)
        except OSError:
            logger.exception(f"{FileManager.__name__}: Fail to Remove File: Name = {filename}")

    @staticmethod
    def get_file_url(filename, filetype):
        """根据文件名获取文件的URL"""
        if filetype == "private":
            return f"file/{filename}"
        elif filetype == 'public':
            return f"{FileManager._DOWNLOAD_URL}/{filename}"

    @staticmethod
    def get_file_full_name(filename, filetype):
        if filetype == "private":
            return join(FileManager._UPLOAD_FOLDER, filename)
        elif filetype == 'public':
            return join(FileManager._DOWNLOAD_FOLDER, filename)

    @staticmethod
    def backup_database_file(username):
        src = join(FileManager._USER_FOLDER, f"{username}.json")
        dst = join(FileManager._DOWNLOAD_FOLDER, f"{username}.json")
        copy_file(src, dst)
        return f"/smart-todo/{dst}"

    @staticmethod
    def file2public(filename):
        src = join(FileManager._UPLOAD_FOLDER, filename)
        dst = join(FileManager._DOWNLOAD_FOLDER, filename)
        copy_file(src, dst)
        return dst

    @staticmethod
    def file2private(filename):
        src = join(FileManager._DOWNLOAD_FOLDER, filename)
        dst = join(FileManager._UPLOAD_FOLDER, filename)
        copy_file(src, dst)
        return dst

    def file2remote(self):
        pass
