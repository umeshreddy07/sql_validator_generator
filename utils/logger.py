import logging

logger = logging.getLogger("text2sql")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

if not logger.hasHandlers():
    logger.addHandler(ch)

def log_error(msg):
    logger.error(msg)

def log_info(msg):
    logger.info(msg) 