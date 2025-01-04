import logging
from logging.handlers import RotatingFileHandler

def configure_logging(log_file, level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(level)
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
