"""
结构化日志配置

提供统一的日志格式和级别配置，支持日志追踪和审计。
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
import os


class StructuredFormatter(logging.Formatter):
    """
    结构化日志格式器

    输出 JSON 格式的日志，便于日志收集和分析系统解析。
    """

    def __init__(
        self,
        include_extra: bool = True,
        include_stack_info: bool = True
    ):
        super().__init__()
        self.include_extra = include_extra
        self.include_stack_info = include_stack_info

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加请求追踪信息
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id

        # 添加额外字段
        if self.include_extra:
            extra_fields = {
                k: v for k, v in record.__dict__.items()
                if k not in {
                    'name', 'msg', 'args', 'created', 'filename', 'funcName',
                    'levelname', 'levelno', 'lineno', 'module', 'msecs',
                    'pathname', 'process', 'processName', 'relativeCreated',
                    'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                    'message', 'request_id', 'user_id', 'taskName'
                }
            }
            if extra_fields:
                log_data["extra"] = extra_fields

        # 添加异常堆栈
        if self.include_stack_info and record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        return json.dumps(log_data, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """
    控制台日志格式器

    输出人类可读的日志格式，适合开发环境。
    """

    # ANSI 颜色代码
    COLORS = {
        logging.DEBUG: "\033[36m",     # 青色
        logging.INFO: "\033[32m",      # 绿色
        logging.WARNING: "\033[33m",   # 黄色
        logging.ERROR: "\033[31m",     # 红色
        logging.CRITICAL: "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录，添加颜色"""
        # 添加颜色
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"

        # 添加请求 ID
        if hasattr(record, 'request_id'):
            record.msg = f"[{record.request_id[:8]}] {record.msg}"

        return super().format(record)


def setup_logging(
    level: str = None,
    log_format: str = None,
    log_file: str = None,
    include_service_name: bool = True
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 日志格式 (json, console)
        log_file: 日志文件路径
        include_service_name: 是否在日志中包含服务名称
    """
    # 从环境变量获取配置
    level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = log_format or os.getenv("LOG_FORMAT", "console").lower()
    log_file = log_file or os.getenv("LOG_FILE")

    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level, logging.INFO))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    if log_format == "json":
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())

    root_logger.addHandler(console_handler)

    # 创建文件处理器（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取命名 logger

    使用方式:
    logger = get_logger(__name__)
    logger.info("消息", extra={"request_id": "xxx"})
    """
    return logging.getLogger(name)


class RequestContextFilter(logging.Filter):
    """
    日志上下文过滤器

    自动为日志添加请求上下文信息。
    """

    def __init__(self, request_id: str, user_id: Optional[str] = None):
        super().__init__()
        self.request_id = request_id
        self.user_id = user_id

    def filter(self, record: logging.LogRecord) -> bool:
        """添加上下文信息到日志记录"""
        record.request_id = self.request_id
        if self.user_id:
            record.user_id = self.user_id
        return True


class PerformanceLogger:
    """
    性能日志记录器

    用于记录代码块的执行时间。

    使用方式:
    with PerformanceLogger("操作名称", logger):
        # 执行代码
    """

    def __init__(
        self,
        operation: str,
        logger: Optional[logging.Logger] = None,
        threshold: float = 1.0
    ):
        self.operation = operation
        self.logger = logger or logging.getLogger(__name__)
        self.threshold = threshold  # 慢操作阈值（秒）
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = datetime.now().timestamp()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = datetime.now().timestamp() - self.start_time

        if elapsed > self.threshold:
            self.logger.warning(
                f"慢操作：{self.operation}, 耗时：{elapsed:.3f}s",
                extra={"elapsed": elapsed, "operation": self.operation}
            )
        else:
            self.logger.debug(
                f"操作完成：{self.operation}, 耗时：{elapsed:.3f}s",
                extra={"elapsed": elapsed, "operation": self.operation}
            )

        return False  # 不抑制异常


class AuditLogger:
    """
    审计日志记录器

    专门用于记录敏感操作和变更。
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or get_logger("audit")

    def log_action(
        self,
        action: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        result: str = "success"
    ):
        """
        记录审计日志

        Args:
            action: 操作类型 (create, update, delete, read)
            user_id: 操作用户 ID
            resource_type: 资源类型
            resource_id: 资源 ID
            details: 操作详情
            result: 操作结果
        """
        self.logger.info(
            f"审计：{action} {resource_type}/{resource_id}",
            extra={
                "audit": True,
                "action": action,
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "result": result
            }
        )

    def log_data_change(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        field: str,
        old_value: Any,
        new_value: Any
    ):
        """记录数据变更"""
        self.log_action(
            action="update",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "field": field,
                "old_value": old_value,
                "new_value": new_value
            }
        )


# 创建全局审计日志实例
audit_logger = AuditLogger()
