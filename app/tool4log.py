import logging
from logging import handlers
from os import mkdir
from os.path import exists, join

_LOG_BASE = join("data", "log")
Log_File = join(_LOG_BASE, "log.txt")

if not exists(_LOG_BASE):
    import os
    print(os.getcwd())
    mkdir(_LOG_BASE)


logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
th = handlers.TimedRotatingFileHandler(filename=Log_File, when='midnight', backupCount=14, encoding='utf-8')
th.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(th)

task_logger = logging.getLogger("task")
