import logging
from logging import handlers
from os import mkdir
from os.path import exists, join

_LOG_BASE = join("data", "log")
if not exists(_LOG_BASE):
    mkdir(_LOG_BASE)

Log_File = join(_LOG_BASE, "log.txt")

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
th = handlers.TimedRotatingFileHandler(filename=Log_File, when='midnight', backupCount=14, encoding='utf-8')
th.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(th)

logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').addHandler(th)
