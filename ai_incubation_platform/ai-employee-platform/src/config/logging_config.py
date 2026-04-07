"""
日志配置模块
"""
import logging
import sys
from config.settings import settings


def setup_logging() -> None:
    """
    配置应用日志
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # 创建格式化器
    formatter = logging.Formatter(settings.log_format)
    console_handler.setFormatter(formatter)

    # 添加到根日志记录器
    root_logger.addHandler(console_handler)

    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取命名日志记录器

    Args:
        name: 日志记录器名称，通常使用模块名

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    return logger
