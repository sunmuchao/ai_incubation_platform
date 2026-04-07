"""
日志配置模块
提供结构化日志配置，支持请求追踪和多级别日志输出
"""
import logging
import sys
from typing import Optional
from core.config import settings


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器，便于终端阅读"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # 保存原始级别
        levelname = record.levelname
        if self.is_tty() and levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        result = super().format(record)
        record.levelname = levelname  # 恢复原始级别
        return result

    @staticmethod
    def is_tty() -> bool:
        """检查是否为终端输出"""
        return sys.stderr.isatty()


class RequestIdFilter(logging.Filter):
    """请求 ID 过滤器，为日志添加请求追踪标识"""

    def filter(self, record: logging.LogRecord) -> bool:
        # 尝试从记录中获取 request_id
        if not hasattr(record, 'request_id'):
            # 尝试从 extra 中获取
            record.request_id = getattr(record, 'request_id', '-')
        return True


def setup_logging(
    level: str = None,
    log_file: Optional[str] = None,
    json_format: bool = False
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别，默认从配置读取
        log_file: 日志文件路径，不指定则只输出到控制台
        json_format: 是否使用 JSON 格式（便于日志收集系统解析）
    """
    log_level = level or ("DEBUG" if settings.DEBUG else "INFO")

    # 根日志配置
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 选择格式化器
    if json_format:
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "request_id": "%(request_id)s", '
            '"message": "%(message)s", "module": "%(module)s", '
            '"function": "%(funcName)s", "line": %(lineno)d}'
        )
    else:
        formatter = ColoredFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s [request_id=%(request_id)s]",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())
    root_logger.addHandler(console_handler)

    # 文件处理器（可选）
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            # 文件日志使用普通格式化器（不带颜色）
            file_formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s [request_id=%(request_id)s]",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
            file_handler.addFilter(RequestIdFilter())
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"Failed to create log file handler: {e}")

    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel("WARNING")
    logging.getLogger("uvicorn.access").setLevel("WARNING")
    logging.getLogger("sqlalchemy").setLevel("WARNING") if settings.DEBUG else logging.getLogger("sqlalchemy").setLevel("ERROR")


def get_logger(name: str) -> logging.Logger:
    """
    获取命名日志器

    Args:
        name: 日志器名称，通常使用 __name__

    Returns:
        logging.Logger: 配置好的日志器实例

    Example:
        ```python
        logger = get_logger(__name__)
        logger.info("操作成功", extra={"request_id": "abc123"})
        ```
    """
    return logging.getLogger(name)


# 快捷函数，用于在请求上下文中记录日志
def log_with_request_id(
    logger: logging.Logger,
    level: int,
    message: str,
    request_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    带请求 ID 的日志记录快捷函数

    Args:
        logger: 日志器实例
        level: 日志级别
        message: 日志消息
        request_id: 请求 ID
        **kwargs: 其他 extra 参数
    """
    extra = {"request_id": request_id or "-"}
    extra.update(kwargs)
    logger.log(level, message, extra=extra)
