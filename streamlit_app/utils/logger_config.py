import logging
import sys

DEFAULT_LOG_LEVEL = logging.INFO # 可以根据环境配置调整，例如 DEBUG
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(funcName)s:%(lineno)d - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def get_logger(name: str, level: int = DEFAULT_LOG_LEVEL) -> logging.Logger:
    """获取配置好的Logger实例"""
    logger = logging.getLogger(name)
    if not logger.handlers: # 防止重复添加handler
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger 