"""
统一日志工具
提供结构化日志输出，支持审计追踪
"""
import logging
import sys
from pythonjsonlogger import jsonlogger
from typing import Any, Dict
from datetime import datetime
import uuid
from contextvars import ContextVar

# 上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
connector_name_var: ContextVar[str] = ContextVar("connector_name", default="")


class ContextFilter(logging.Filter):
    """上下文过滤器，添加请求上下文信息到日志"""

    def filter(self, record):
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.connector_name = connector_name_var.get()
        record.timestamp = datetime.utcnow().isoformat()
        return True


def setup_logger() -> logging.Logger:
    """设置结构化日志"""
    logger = logging.getLogger("data-agent-connector")
    logger.setLevel(logging.INFO)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # JSON 格式处理器
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(timestamp)s %(levelname)s %(name)s %(request_id)s %(user_id)s %(connector_name)s %(message)s %(extra)s"
    )
    handler.setFormatter(formatter)

    # 添加上下文过滤器
    handler.addFilter(ContextFilter())

    logger.addHandler(handler)
    logger.propagate = False

    return logger


# 全局日志实例
logger = setup_logger()


def log_with_context(
    level: str,
    message: str,
    extra: Dict[str, Any] = None,
    **kwargs
) -> None:
    """
    记录带上下文的日志
    """
    extra = extra or {}
    extra.update(kwargs)

    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra={"extra": extra})


def generate_request_id() -> str:
    """生成唯一请求ID"""
    return str(uuid.uuid4())
