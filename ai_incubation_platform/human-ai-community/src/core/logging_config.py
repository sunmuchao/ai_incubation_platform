"""
日志配置模块
"""
import logging
import sys
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = False,
    log_file: Optional[str] = None,
    log_format: str = "structured",
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别
        log_to_file: 是否写入文件
        log_file: 日志文件路径
        log_format: 日志格式 (structured / colored / simple)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    if log_format == "structured":
        # 结构化日志格式（JSON 风格，便于日志收集）
        formatter = logging.Formatter(
            fmt='{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(module)s", "function": "%(funcName)s", '
            '"line": %(lineno)d, "message": "%(message)s", '
            '"trace_id": "%(trace_id)s"}',
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        # 添加 trace_id 过滤器
        console_handler.addFilter(TraceIdFilter())
    elif log_format == "colored":
        formatter = ColoredFormatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器
    if log_to_file and log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 抑制部分库的日志噪音
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


class TraceIdFilter(logging.Filter):
    """Trace ID 过滤器 - 为每条日志添加追踪 ID"""

    def filter(self, record):
        # 尝试从上下文获取 trace_id，如果没有则生成新的
        trace_id = getattr(record, "trace_id", None)
        if not trace_id:
            import uuid
            trace_id = str(uuid.uuid4())[:8]
        record.trace_id = trace_id
        return True


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器"""
    return logging.getLogger(name)


# 快捷日志函数（用于模块级别快速记录）
_logger = None


def _get_logger():
    global _logger
    if _logger is None:
        _logger = get_logger("community")
    return _logger


def log_debug(message: str, **kwargs) -> None:
    """记录 DEBUG 日志"""
    logger = _get_logger()
    extra_msg = f" | {', '.join(f'{k}={v}' for k, v in kwargs.items())}" if kwargs else ""
    logger.debug(f"{message}{extra_msg}")


def log_info(message: str, **kwargs) -> None:
    """记录 INFO 日志"""
    logger = _get_logger()
    extra_msg = f" | {', '.join(f'{k}={v}' for k, v in kwargs.items())}" if kwargs else ""
    logger.info(f"{message}{extra_msg}")


def log_warning(message: str, **kwargs) -> None:
    """记录 WARNING 日志"""
    logger = _get_logger()
    extra_msg = f" | {', '.join(f'{k}={v}' for k, v in kwargs.items())}" if kwargs else ""
    logger.warning(f"{message}{extra_msg}")


def log_error(message: str, exc: Exception = None, **kwargs) -> None:
    """记录 ERROR 日志"""
    logger = _get_logger()
    extra_msg = f" | {', '.join(f'{k}={v}' for k, v in kwargs.items())}" if kwargs else ""
    if exc:
        logger.error(f"{message}{extra_msg}", exc_info=exc)
    else:
        logger.error(f"{message}{extra_msg}")
