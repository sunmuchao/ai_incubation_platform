"""
统一日志模块

提供日志配置和格式化功能
"""

import logging
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """
    JSON 格式日志格式化器

    输出结构化的 JSON 日志
    """

    def __init__(
        self,
        include_extra: bool = True,
        static_fields: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 JSON 格式化器

        Args:
            include_extra: 是否包含额外字段
            static_fields: 静态字段（每条日志都包含）
        """
        super().__init__()
        self.include_extra = include_extra
        self.static_fields = static_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加静态字段
        log_data.update(self.static_fields)

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        # 添加额外字段
        if self.include_extra:
            extra_fields = {
                key: value for key, value in record.__dict__.items()
                if key not in (
                    'name', 'msg', 'args', 'created', 'filename', 'funcName',
                    'levelname', 'levelno', 'lineno', 'module', 'msecs',
                    'pathname', 'process', 'processName', 'relativeCreated',
                    'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                    'taskName', 'message'
                )
            }
            log_data.update(extra_fields)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """
    文本格式日志格式化器

    带颜色的可读格式
    """

    # ANSI 颜色代码
    COLORS = {
        logging.DEBUG: "\033[36m",      # 青色
        logging.INFO: "\033[32m",       # 绿色
        logging.WARNING: "\033[33m",    # 黄色
        logging.ERROR: "\033[31m",      # 红色
        logging.CRITICAL: "\033[35m",   # 紫色
    }
    RESET = "\033[0m"

    def __init__(self, include_color: bool = True):
        """
        初始化文本格式化器

        Args:
            include_color: 是否包含颜色
        """
        super().__init__()
        self.include_color = include_color

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        message = record.getMessage()

        if self.include_color:
            color = self.COLORS.get(record.levelno, self.RESET)
            level = f"{color}{level}{self.RESET}"

        return f"{timestamp} [{level}] {record.name}: {message}"


def setup_logging(
    level: str = "INFO",
    format_type: str = "text",  # text/json
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    include_timestamp: bool = True,
    static_fields: Optional[Dict[str, Any]] = None
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别
        format_type: 格式类型 (text/json)
        log_file: 日志文件路径（可选）
        log_format: 自定义格式字符串
        include_timestamp: 是否包含时间戳
        static_fields: 静态字段（JSON 格式时使用）
    """
    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    # 设置格式化器
    if format_type == "json":
        formatter = JsonFormatter(static_fields=static_fields)
    elif log_format:
        formatter = logging.Formatter(log_format)
    else:
        formatter = TextFormatter(include_color=sys.stdout.isatty())

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 设置第三方库日志级别
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器

    Args:
        name: 日志器名称（通常是__name__）

    Returns:
        logging.Logger: 日志器实例
    """
    return logging.getLogger(name)


class StructuredLogger:
    """
    结构化日志器

    提供结构化的日志记录方法
    """

    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        初始化结构化日志器

        Args:
            name: 日志器名称
            context: 上下文信息（自动附加到每条日志）
        """
        self.logger = logging.getLogger(name)
        self.context = context or {}

    def _log(
        self,
        level: int,
        message: str,
        **kwargs
    ) -> None:
        """记录日志"""
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """记录 DEBUG 日志"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """记录 INFO 日志"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """记录 WARNING 日志"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """记录 ERROR 日志"""
        if exc_info:
            self.logger.error(message, exc_info=True, extra={**self.context, **kwargs})
        else:
            self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """记录 CRITICAL 日志"""
        if exc_info:
            self.logger.critical(message, exc_info=True, extra={**self.context, **kwargs})
        else:
            self._log(logging.CRITICAL, message, **kwargs)

    def child(self, **kwargs) -> 'StructuredLogger':
        """创建带额外上下文的子日志器"""
        new_context = {**self.context, **kwargs}
        return StructuredLogger(self.logger.name, new_context)


class RequestLoggingMiddleware:
    """
    请求日志中间件

    用于记录 HTTP 请求的日志
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        include_body: bool = False,
        sensitive_headers: Optional[list] = None
    ):
        """
        初始化请求日志中间件

        Args:
            logger: 日志器
            include_body: 是否包含请求体
            sensitive_headers: 敏感请求头（将被脱敏）
        """
        self.logger = logger or logging.getLogger("http")
        self.include_body = include_body
        self.sensitive_headers = sensitive_headers or [
            "authorization", "cookie", "set-cookie", "x-api-key"
        ]

    def _mask_sensitive_headers(self, headers: dict) -> dict:
        """脱敏敏感请求头"""
        masked = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if any(s in key_lower for s in self.sensitive_headers):
                masked[key] = "***REDACTED***"
            else:
                masked[key] = value
        return masked

    def log_request(
        self,
        method: str,
        path: str,
        headers: dict,
        body: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> None:
        """记录请求日志"""
        log_data = {
            "type": "request",
            "method": method,
            "path": path,
            "headers": self._mask_sensitive_headers(headers),
            "request_id": request_id
        }
        if self.include_body and body:
            log_data["body"] = body

        self.logger.info(f"HTTP {method} {path}", extra=log_data)

    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: Optional[str] = None
    ) -> None:
        """记录响应日志"""
        log_data = {
            "type": "response",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": request_id
        }

        level = logging.INFO
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING

        self.logger.log(level, f"HTTP {method} {path} {status_code}", extra=log_data)


# 便捷函数
def log_execution_time(logger: Optional[logging.Logger] = None):
    """
    记录函数执行时间的装饰器

    Args:
        logger: 日志器
    """
    import time
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                log.debug(f"{func.__name__} completed in {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                log.error(f"{func.__name__} failed after {duration:.2f}ms: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                log.debug(f"{func.__name__} completed in {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                log.error(f"{func.__name__} failed after {duration:.2f}ms: {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


import asyncio
