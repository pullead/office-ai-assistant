# -*- coding: utf-8 -*-
from loguru import logger
import sys

def setup_logger():
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/app.log", rotation="1 MB", level="DEBUG")
    return logger