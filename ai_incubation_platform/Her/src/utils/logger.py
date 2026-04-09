"""
日志工具模块
支持结构化日志、敏感字段自动脱敏、链路追踪
"""
import logging
import json
import time
import uuid
import functools
from contextvars import ContextVar
from typing import Any, Dict, Optional, Callable
from pythonjsonlogger import jsonlogger
from config import settings
import re

# 链路追踪上下文变量（线程/协程安全）
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_span_id_var: ContextVar[Optional[str]] = ContextVar("span_id", default=None)


class SensitiveDataFilter(logging.Filter):
    """敏感数据脱敏过滤器"""

    def __init__(self):
        super().__init__()
        self.sensitive_fields = settings.sensitive_fields
        self.sensitive_fields_lower = [str(f).lower() for f in self.sensitive_fields]
        # 敏感字段正则匹配（不区分大小写）
        self.sensitive_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(field) for field in self.sensitive_fields) + r')\b',
            re.IGNORECASE
        )
        # 邮箱正则
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        # 手机号正则（中国大陆）
        self.phone_pattern = re.compile(r'\b1[3-9]\d{9}\b')

        # JWT-like（三段式）/ Bearer token
        jwt_segment = r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
        self.jwt_pattern = re.compile(rf"\b{jwt_segment}\b")
        self.bearer_pattern = re.compile(rf"(?i)\bBearer\s+({jwt_segment})\b")

        # key=value / JSON key="xxx" 形式的敏感值脱敏（只替换值，不整句吞掉）
        kv_keys = r"(password|password_hash|token|secret|jwt|access_token|refresh_token|api_key|apikey|id_card|bank_card|location)"
        self.key_value_pattern = re.compile(rf"(?i)\b{kv_keys}\b\s*[:=]\s*([^\s,;]+)")
        self.json_key_value_pattern = re.compile(
            rf"(?i)\"{kv_keys}\"\s*:\s*\"([^\"]*)\""
        )

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录，脱敏敏感信息"""
        # 处理消息
        if hasattr(record, 'msg'):
            record.msg = self._desensitize(record.msg)

        # 处理参数
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._desensitize(v) for k, v in record.args.items()}
            else:
                record.args = tuple(self._desensitize(arg) for arg in record.args)

        # 处理异常信息
        if hasattr(record, 'exc_info') and record.exc_info:
            record.exc_info = self._desensitize_exc_info(record.exc_info)

        return True

    def _desensitize(self, value: Any) -> Any:
        """对值进行脱敏处理"""
        if value is None:
            return value

        if isinstance(value, str):
            # 脱敏邮箱
            value = self.email_pattern.sub(self._mask_email, value)
            # 脱敏手机号
            value = self.phone_pattern.sub(self._mask_phone, value)
            # 脱敏 Bearer token
            value = self.bearer_pattern.sub("Bearer [SENSITIVE_TOKEN]", value)
            # 脱敏 JWT-like 字符串（包含在 Bearer 之外的日志/异常里也能覆盖）
            value = self.jwt_pattern.sub("[SENSITIVE_JWT]", value)
            # 脱敏 JSON key="value"
            value = self.json_key_value_pattern.sub(
                lambda m: f"\"{m.group(1)}\":\"[SENSITIVE]\"",
                value,
            )
            # 脱敏 key=value
            value = self.key_value_pattern.sub(
                lambda m: f"{m.group(1)}=[SENSITIVE]",
                value,
            )
            return value

        if isinstance(value, dict):
            def _is_sensitive_key(key: Any) -> bool:
                k_lower = str(key).lower()

                # 1) 精确匹配（password / token / email 等）
                if k_lower in self.sensitive_fields_lower:
                    return True

                # 2) 复合字段名匹配（user_password / password_hash / bank_card_number 等）
                #    避免对过于通用的 `key` 进行无条件子串匹配，降低误脱敏风险
                if any(f != "key" and f.lower() in k_lower for f in self.sensitive_fields):
                    return True

                # 3) 对 *_key / api_key / apikey 这类更明确的密钥命名做补充规则
                return k_lower.endswith("_key") or "api_key" in k_lower or k_lower == "apikey" or "apikey" in k_lower

            return {k: "[SENSITIVE]" if _is_sensitive_key(k) else self._desensitize(v) for k, v in value.items()}

        if isinstance(value, (list, tuple)):
            return type(value)(self._desensitize(item) for item in value)

        return value

    def _desensitize_exc_info(self, exc_info: tuple) -> tuple:
        """脱敏异常信息"""
        exc_type, exc_value, exc_traceback = exc_info
        if exc_value:
            exc_value.args = tuple(self._desensitize(arg) for arg in exc_value.args)
        return (exc_type, exc_value, exc_traceback)

    @staticmethod
    def _mask_email(match: re.Match) -> str:
        """掩码邮箱：a***@example.com"""
        email = match.group()
        username, domain = email.split('@', 1)
        if len(username) <= 1:
            return f"{username}***@{domain}"
        return f"{username[0]}***@{domain}"

    @staticmethod
    def _mask_phone(match: re.Match) -> str:
        """掩码手机号：138****1234"""
        phone = match.group()
        return f"{phone[:3]}****{phone[7:]}"


# ========== 链路追踪支持 ==========

def get_trace_id() -> str:
    """获取当前链路追踪 ID，不存在则创建新的"""
    trace_id = _trace_id_var.get()
    if trace_id is None:
        trace_id = str(uuid.uuid4().hex[:16])
        _trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """设置当前链路追踪 ID（用于接收上游请求）"""
    _trace_id_var.set(trace_id)


def get_span_id() -> str:
    """获取当前_span ID，用于区分同一链路中的不同操作"""
    span_id = _span_id_var.get()
    if span_id is None:
        span_id = str(uuid.uuid4().hex[:8])
        _span_id_var.set(span_id)
    return span_id


def set_span_id(span_id: str) -> None:
    """设置当前 span ID"""
    _span_id_var.set(span_id)


def create_child_span(parent_span_id: str) -> str:
    """创建子 span，用于嵌套调用追踪"""
    child_span = str(uuid.uuid4().hex[:8])
    _span_id_var.set(child_span)
    return child_span


def clear_trace_context() -> None:
    """清除当前上下文的追踪信息（请求结束时调用）"""
    _trace_id_var.set(None)
    _span_id_var.set(None)


class TraceContextFilter(logging.Filter):
    """日志过滤器：自动注入 trace_id 和 span_id"""

    def filter(self, record: logging.LogRecord) -> bool:
        """注入链路追踪信息到日志记录"""
        record.trace_id = get_trace_id()
        record.span_id = get_span_id()
        return True


def setup_logger() -> logging.Logger:
    """配置并返回日志记录器"""
    logger = logging.getLogger("matchmaker-agent")
    logger.setLevel(logging.DEBUG)  # 设置为 DEBUG 以记录所有日志

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 添加敏感数据过滤器
    sensitive_filter = SensitiveDataFilter()
    logger.addFilter(sensitive_filter)

    # 添加链路追踪过滤器
    trace_filter = TraceContextFilter()
    logger.addFilter(trace_filter)

    # 创建文件处理器 - 本地日志文件
    import os
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.FileHandler(
        filename=os.path.join(log_dir, 'server.log'),
        mode='a',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.addFilter(sensitive_filter)
    file_handler.addFilter(trace_filter)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.log_level.upper())
    console_handler.addFilter(sensitive_filter)
    console_handler.addFilter(trace_filter)

    # 设置格式
    if settings.log_format.lower() == "json":
        file_formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d %(trace_id)s %(span_id)s"
        )
        console_formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d %(trace_id)s %(span_id)s"
        )
    else:
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s:%(span_id)s] - %(message)s"
        )
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s:%(span_id)s] - %(message)s"
        )

    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Logger initialized, log file: {os.path.join(log_dir, 'server.log')}")

    return logger


# 全局日志实例
logger = setup_logger()


# ========== 日志装饰器 ==========

def log_execution(
    logger: Optional[logging.Logger] = None,
    log_level: str = "INFO",
    log_inputs: bool = False,
    log_outputs: bool = False,
    log_exceptions: bool = True,
    prefix: str = ""
) -> Callable:
    """
    日志装饰器：自动记录函数执行的入口、出口、异常和耗时

    Args:
        logger: 使用的日志记录器，默认使用全局 logger
        log_level: 日志级别 (INFO/DEBUG/WARNING/ERROR)
        log_inputs: 是否记录输入参数
        log_outputs: 是否记录返回值
        log_exceptions: 是否记录异常
        prefix: 日志前缀标识

    Example:
        @log_execution(log_inputs=True, log_outputs=True, prefix="[UserService]")
        def get_user(self, user_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            _logger = logger or globals().get('logger')
            if not _logger:
                return await func(*args, **kwargs)

            func_name = f"{prefix}{func.__module__}.{func.__qualname__}" if prefix else f"{func.__module__}.{func.__qualname__}"
            start_time = time.time()
            span_id = get_span_id()

            # 记录入口
            _logger.log(
                getattr(logging, log_level.upper()),
                f"▶️ ENTER {func_name}(span={span_id})" +
                (f" args={args}, kwargs={kwargs}" if log_inputs else "")
            )

            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000

                # 记录出口
                _logger.log(
                    getattr(logging, log_level.upper()),
                    f"✅ EXIT {func_name}(span={span_id}) elapsed={elapsed_ms:.2f}ms" +
                    (f" result={result}" if log_outputs and len(str(result)) < 1000 else "")
                )

                return result

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                if log_exceptions:
                    _logger.error(
                        f"❌ EXCEPTION {func_name}(span={span_id}) elapsed={elapsed_ms:.2f}ms error={str(e)}",
                        exc_info=True
                    )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            _logger = logger or globals().get('logger')
            if not _logger:
                return func(*args, **kwargs)

            func_name = f"{prefix}{func.__module__}.{func.__qualname__}" if prefix else f"{func.__module__}.{func.__qualname__}"
            start_time = time.time()
            span_id = get_span_id()

            # 记录入口
            _logger.log(
                getattr(logging, log_level.upper()),
                f"▶️ ENTER {func_name}(span={span_id})" +
                (f" args={args}, kwargs={kwargs}" if log_inputs else "")
            )

            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000

                # 记录出口
                _logger.log(
                    getattr(logging, log_level.upper()),
                    f"✅ EXIT {func_name}(span={span_id}) elapsed={elapsed_ms:.2f}ms" +
                    (f" result={result}" if log_outputs and len(str(result)) < 1000 else "")
                )

                return result

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                if log_exceptions:
                    _logger.error(
                        f"❌ EXCEPTION {func_name}(span={span_id}) elapsed={elapsed_ms:.2f}ms error={str(e)}",
                        exc_info=True
                    )
                raise

        # 检测是否为异步函数
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_api_call(
    logger: Optional[logging.Logger] = None,
    endpoint_name: str = ""
) -> Callable:
    """
    API 专用日志装饰器：记录 API 调用的完整生命周期

    自动记录：
    - 请求入口（方法、路径、关键参数）
    - 执行耗时
    - 响应状态
    - 异常情况

    Example:
        @router.get("/users/{user_id}")
        @log_api_call(endpoint_name="get_user")
        async def get_user(user_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            _logger = logger or globals().get('logger')
            if not _logger:
                return await func(*args, **kwargs)

            # 确保有 trace_id
            trace_id = get_trace_id()

            start_time = time.time()
            _logger.info(
                f"📡 API [{endpoint_name or func.__name__}] START trace_id={trace_id} " +
                f"kwargs={kwargs}"
            )

            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000
                _logger.info(
                    f"📡 API [{endpoint_name or func.__name__}] SUCCESS trace_id={trace_id} " +
                    f"elapsed={elapsed_ms:.2f}ms"
                )
                return result

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                _logger.error(
                    f"📡 API [{endpoint_name or func.__name__}] FAILED trace_id={trace_id} " +
                    f"elapsed={elapsed_ms:.2f}ms error={str(e)}",
                    exc_info=True
                )
                raise

        return async_wrapper

    return decorator
