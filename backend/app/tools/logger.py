import logging
from os import mkdir
from os.path import exists, join

from logging import handlers

_LOG_BASE = join("data", "log")
if not exists(_LOG_BASE):
    mkdir(_LOG_BASE)

Log_File = join(_LOG_BASE, "log.txt")

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
th = handlers.TimedRotatingFileHandler(filename=Log_File, when='midnight', backupCount=14, encoding='utf-8')
th.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(th)
