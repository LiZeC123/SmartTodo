import os

from app.tools.file import FILE_FOLDER

if not os.path.exists(FILE_FOLDER):
    os.mkdir(FILE_FOLDER)