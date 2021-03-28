import os
from os import mkdir
from os.path import exists

from tool4log import logger


class NoteManager:
    _NOTE_FOLDER = "notebase"

    def __init__(self):
        if not exists(NoteManager._NOTE_FOLDER):
            mkdir(NoteManager._NOTE_FOLDER)

    @staticmethod
    def create(nid: int, title: str):
        filename = os.path.join(NoteManager._NOTE_FOLDER, str(nid))
        with open(filename, "w") as f:
            content = f"<h1>{title}</h1>" \
                      f"<div>====================</div>" \
                      f"<div><br></div><div><br></div><div><br></div><div><br></div>"
            f.write(content)

    @staticmethod
    def get(nid: int):
        filename = os.path.join(NoteManager._NOTE_FOLDER, str(nid))
        with open(filename, 'r') as f:
            return f.read()

    @staticmethod
    def update(nid: int, content: str):
        filename = os.path.join(NoteManager._NOTE_FOLDER, str(nid))
        with open(filename, "w") as f:
            f.write(content)

    @staticmethod
    def remove(nid: int):
        filename = os.path.join(NoteManager._NOTE_FOLDER, str(nid))
        try:
            os.remove(filename)
        except OSError:
            logger.exception(f"{NoteManager.__name__}:Fail to Remove Note: Id = {nid}")
