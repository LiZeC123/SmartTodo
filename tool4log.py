import logging
from logging import handlers
from os import mkdir
from os.path import exists

_LOG_FILE = "log"

if not exists(_LOG_FILE):
    mkdir(_LOG_FILE)

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
th = handlers.TimedRotatingFileHandler(filename="log/log.txt", when='midnight', backupCount=14, encoding='utf-8')
th.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(th)
