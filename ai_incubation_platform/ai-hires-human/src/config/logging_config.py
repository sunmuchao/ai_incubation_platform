"""
统一日志配置模块。

提供结构化日志、链路追踪、审计日志功能。
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# 上下文变量：用于链路追踪的 request_id
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# 上下文变量：用于标识当前操作的用户/工人 ID
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON 格式日志器，便于日志聚合分析。"""

    def __init__(self, app_name: str = "ai-hires-human"):
        super().__init__()
        self.app_name = app_name

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "app": self.app_name,
        }

        # 添加链路追踪 ID
        req_id = request_id_var.get()
        if req_id:
            log_data["request_id"] = req_id

        # 添加用户 ID
        usr_id = user_id_var.get()
        if usr_id:
            log_data["user_id"] = usr_id

        # 添加位置信息（仅 DEBUG 模式）
        if record.levelno == logging.DEBUG:
            log_data["location"] = f"{record.pathname}:{record.lineno}"

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        for key, value in record.__dict__.items():
            if key not in ("name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "pathname", "process", "processName", "relativeCreated",
                          "stack_info", "exc_info", "exc_text", "thread", "threadName",
                          "message", "asctime"):
                try:
                    json.dumps(value)  # 确保可序列化
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """文本格式日志器，便于本地开发调试。"""

    def __init__(self, color: bool = True):
        super().__init__()
        self.color = color
        self.colors = {
            "DEBUG": "\033[36m",     # 青色
            "INFO": "\033[32m",      # 绿色
            "WARNING": "\033[33m",   # 黄色
            "ERROR": "\033[31m",     # 红色
            "CRITICAL": "\033[35m",  # 紫色
            "RESET": "\033[0m",
        }

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        message = record.getMessage()

        # 添加链路追踪 ID
        req_id = request_id_var.get()
        req_prefix = f"[{req_id[:8]}] " if req_id else ""

        # 添加用户 ID
        usr_id = user_id_var.get()
        usr_prefix = f"[user:{usr_id}] " if usr_id else ""

        if self.color:
            color = self.colors.get(level, self.colors["RESET"])
            return f"{color}{timestamp} {level:8}{self.colors['RESET']} {req_prefix}{usr_prefix}{message}"
        else:
            return f"{timestamp} {level:8} {req_prefix}{usr_prefix}{message}"


def setup_logging(
    level: str = None,
    json_format: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    配置全局日志系统。

    Args:
        level: 日志级别，默认从 LOG_LEVEL 环境变量读取，否则为 INFO
        json_format: 是否使用 JSON 格式，默认从 LOG_FORMAT=json 环境变量读取
        log_file: 日志文件路径，可选
    """
    # 读取配置
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    if not json_format:
        json_format = os.getenv("LOG_FORMAT", "").lower() == "json"

    # 获取或创建根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level, logging.INFO))

    # 清除现有 handler（避免重复）
    root_logger.handlers.clear()

    # 创建控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(TextFormatter(color=sys.stdout.isatty()))

    root_logger.addHandler(console_handler)

    # 创建文件 handler（如果指定了日志文件）
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    # 抑制第三方库的冗余日志
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def generate_request_id() -> str:
    """生成请求追踪 ID。"""
    return str(uuid.uuid4())


def set_request_context(request_id: str = None, user_id: str = None) -> None:
    """
    设置请求上下文。

    Args:
        request_id: 请求追踪 ID，如不提供则自动生成
        user_id: 用户/工人 ID
    """
    if request_id is None:
        request_id = generate_request_id()
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """清除请求上下文。"""
    request_id_var.set(None)
    user_id_var.set(None)


def get_request_id() -> Optional[str]:
    """获取当前请求 ID。"""
    return request_id_var.get()


class AuditLogger:
    """
    审计日志记录器。

    用于记录关键业务操作：状态变更、支付、审核等。
    """

    def __init__(self, logger_name: str = "audit"):
        self.logger = logging.getLogger(logger_name)

    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_id: str,
        details: Dict[str, Any] = None,
        result: str = "success",
    ) -> None:
        """
        记录审计日志。

        Args:
            action: 操作类型 (create, update, delete, approve, reject, etc.)
            resource_type: 资源类型 (task, payment, worker, etc.)
            resource_id: 资源 ID
            actor_id: 操作人 ID
            details: 操作详情（如变更前后数据）
            result: 操作结果 (success, failure)
        """
        log_entry = {
            "audit": True,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "actor_id": actor_id,
            "result": result,
            "details": details or {},
        }

        if result == "success":
            self.logger.info(log_entry)
        else:
            self.logger.warning(log_entry)

    def log_state_change(
        self,
        resource_type: str,
        resource_id: str,
        from_state: str,
        to_state: str,
        actor_id: str,
        reason: str = None,
    ) -> None:
        """记录状态变更审计日志。"""
        self.log_action(
            action="state_change",
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            details={
                "from_state": from_state,
                "to_state": to_state,
                "reason": reason,
            },
        )

    def log_payment(
        self,
        transaction_id: str,
        transaction_type: str,
        amount: float,
        payer_id: str,
        payee_id: str,
        task_id: str = None,
        status: str = "success",
    ) -> None:
        """记录支付审计日志。"""
        self.log_action(
            action="payment",
            resource_type="transaction",
            resource_id=transaction_id,
            actor_id=payer_id,
            details={
                "transaction_type": transaction_type,
                "amount": amount,
                "payer_id": payer_id,
                "payee_id": payee_id,
                "task_id": task_id,
            },
            result=status,
        )


# 全局审计日志实例
audit_logger = AuditLogger()
