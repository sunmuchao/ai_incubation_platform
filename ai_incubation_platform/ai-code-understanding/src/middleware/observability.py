"""
可观测性模块 - 结构化日志与监控指标
提供统一的日志体系、链路追踪和性能监控
"""
import os
import sys
import time
import uuid
import logging
import threading
from typing import Any, Dict, Optional
from datetime import datetime
from collections import defaultdict
from contextlib import contextmanager

# 尝试导入 json logger，如果没有则降级到标准 logging
try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False


class TraceContext:
    """链路追踪上下文 - 线程安全的上下文信息存储"""

    _local = threading.local()

    @classmethod
    def get_trace_id(cls) -> str:
        """获取当前追踪 ID"""
        if not hasattr(cls._local, 'trace_id'):
            cls._local.trace_id = str(uuid.uuid4())
        return cls._local.trace_id

    @classmethod
    def set_trace_id(cls, trace_id: str):
        """设置追踪 ID"""
        cls._local.trace_id = trace_id

    @classmethod
    def get_request_id(cls) -> str:
        """获取当前请求 ID"""
        if not hasattr(cls._local, 'request_id'):
            cls._local.request_id = str(uuid.uuid4())
        return cls._local.request_id

    @classmethod
    def set_request_id(cls, request_id: str):
        """设置请求 ID"""
        cls._local.request_id = request_id

    @classmethod
    def get_context(cls) -> Dict[str, str]:
        """获取完整的上下文信息"""
        return {
            "trace_id": cls.get_trace_id(),
            "request_id": cls.get_request_id(),
            "timestamp": datetime.now().isoformat()
        }

    @classmethod
    def clear(cls):
        """清除上下文"""
        cls._local = threading.local()


class TraceFilter(logging.Filter):
    """日志过滤器 - 自动注入追踪上下文"""

    def filter(self, record: logging.LogRecord) -> bool:
        """为日志记录添加追踪上下文"""
        context = TraceContext.get_context()
        record.trace_id = context["trace_id"]
        record.request_id = context["request_id"]
        record.timestamp = context["timestamp"]
        return True


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self._metrics = defaultdict(list)
        self._lock = threading.Lock()
        self._counters = defaultdict(int)
        self._gauges = {}

    def record_timing(self, metric_name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """记录耗时指标"""
        with self._lock:
            entry = {
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                "tags": tags or {}
            }
            self._metrics[metric_name].append(entry)
            # 只保留最近 1000 条记录
            if len(self._metrics[metric_name]) > 1000:
                self._metrics[metric_name] = self._metrics[metric_name][-1000:]

    def increment_counter(self, counter_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """增加计数器"""
        with self._lock:
            key = f"{counter_name}:{str(tags) if tags else ''}"
            self._counters[key] += value

    def set_gauge(self, gauge_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """设置仪表值"""
        with self._lock:
            key = f"{gauge_name}:{str(tags) if tags else ''}"
            self._gauges[key] = {
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "tags": tags or {}
            }

    def get_stats(self, metric_name: str) -> Dict[str, Any]:
        """获取指标统计信息"""
        with self._lock:
            entries = self._metrics.get(metric_name, [])
            if not entries:
                return {"count": 0}

            durations = [e["duration"] for e in entries]
            return {
                "count": len(durations),
                "min": min(durations),
                "max": max(durations),
                "avg": sum(durations) / len(durations),
                "p50": self._percentile(durations, 50),
                "p90": self._percentile(durations, 90),
                "p99": self._percentile(durations, 99)
            }

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        with self._lock:
            result = {
                "timings": {},
                "counters": dict(self._counters),
                "gauges": dict(self._gauges)
            }
            for metric_name in self._metrics.keys():
                result["timings"][metric_name] = self.get_stats(metric_name)
            return result

    @staticmethod
    def _percentile(data: list, percentile: int) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class ObservableLogger:
    """可观测日志记录器 - 整合日志和指标"""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 添加追踪过滤器
        trace_filter = TraceFilter()
        self.logger.addFilter(trace_filter)

        # 设置处理器
        self._setup_handler()

        # 性能指标
        self.metrics = PerformanceMetrics()

    def _setup_handler(self):
        """设置日志处理器"""
        if not self.logger.handlers:
            if JSON_LOGGER_AVAILABLE:
                # JSON 格式日志（生产环境）
                handler = logging.StreamHandler()
                formatter = jsonlogger.JsonFormatter(
                    fmt='%(asctime)s %(name)s %(levelname)s %(message)s '
                        '%(trace_id)s %(request_id)s %(module)s %(funcName)s %(lineno)d',
                    datefmt='%Y-%m-%dT%H:%M:%S'
                )
                handler.setFormatter(formatter)
            else:
                # 文本格式日志（开发环境）
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    fmt='%(asctime)s [%(trace_id)s] %(levelname)s %(name)s: %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S'
                )
                handler.setFormatter(formatter)

            self.logger.addHandler(handler)

    def debug(self, msg: str, **kwargs):
        """DEBUG 级别日志"""
        extra = kwargs.get('extra', {})
        extra.update(TraceContext.get_context())
        self.logger.debug(msg, extra=extra)

    def info(self, msg: str, **kwargs):
        """INFO 级别日志"""
        extra = kwargs.get('extra', {})
        extra.update(TraceContext.get_context())
        self.logger.info(msg, extra=extra)

    def warning(self, msg: str, **kwargs):
        """WARNING 级别日志"""
        extra = kwargs.get('extra', {})
        extra.update(TraceContext.get_context())
        self.logger.warning(msg, extra=extra)

    def error(self, msg: str, **kwargs):
        """ERROR 级别日志"""
        extra = kwargs.get('extra', {})
        extra.update(TraceContext.get_context())
        self.logger.error(msg, extra=extra, exc_info=kwargs.get('exc_info', True))

    def exception(self, msg: str, **kwargs):
        """异常日志"""
        extra = kwargs.get('extra', {})
        extra.update(TraceContext.get_context())
        self.logger.exception(msg, extra=extra)

    @contextmanager
    def track_time(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """上下文管理器 - 追踪代码块执行时间"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.metrics.record_timing(metric_name, duration, tags)
            self.info(f"[METRIC] {metric_name} completed in {duration:.3f}s",
                     extra={"metric_name": metric_name, "duration": duration})

    def track_api_call(self, endpoint: str, method: str = "POST"):
        """装饰器工厂 - 追踪 API 调用"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                trace_id = TraceContext.get_trace_id()
                self.info(f"API call start: {method} {endpoint}",
                         extra={"endpoint": endpoint, "method": method, "trace_id": trace_id})

                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.metrics.record_timing(f"api.{endpoint}", duration, {"method": method})
                    self.metrics.increment_counter(f"api.{endpoint}.success")
                    self.info(f"API call success: {method} {endpoint} ({duration:.3f}s)",
                             extra={"endpoint": endpoint, "duration": duration})
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.metrics.record_timing(f"api.{endpoint}", duration, {"method": method, "status": "error"})
                    self.metrics.increment_counter(f"api.{endpoint}.error")
                    self.exception(f"API call failed: {method} {endpoint}",
                                  extra={"endpoint": endpoint, "error": str(e)})
                    raise
            return wrapper
        return decorator


# 全局指标收集器
global_metrics = PerformanceMetrics()


# 性能监控装饰器
def monitor_performance(metric_name: str, logger: Optional[ObservableLogger] = None):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            trace_id = TraceContext.get_trace_id()

            if logger:
                logger.debug(f"Starting {metric_name}", extra={"trace_id": trace_id})

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                global_metrics.record_timing(metric_name, duration)

                if logger:
                    logger.info(f"Completed {metric_name} in {duration:.3f}s",
                               extra={"duration": duration, "metric_name": metric_name})
                return result
            except Exception as e:
                duration = time.time() - start_time
                global_metrics.record_timing(f"{metric_name}.error", duration)
                if logger:
                    logger.exception(f"Failed {metric_name}",
                                    extra={"error": str(e), "duration": duration})
                raise
        return wrapper
    return decorator


# 日志关键路径覆盖助手
class LogPathCoverage:
    """确保关键路径日志覆盖的助手类"""

    @staticmethod
    def log_entry(logger: ObservableLogger, func_name: str, args: tuple, kwargs: dict):
        """记录方法入口日志"""
        # 脱敏处理
        safe_args = LogPathCoverage._sanitize_args(args, kwargs)
        logger.info(f"Enter {func_name}", extra={"func_name": func_name, "input_args": safe_args})

    @staticmethod
    def log_exit(logger: ObservableLogger, func_name: str, result: Any):
        """记录方法出口日志"""
        safe_result = LogPathCoverage._sanitize_result(result)
        logger.info(f"Exit {func_name}", extra={"function": func_name, "result_preview": safe_result})

    @staticmethod
    def log_branch(logger: ObservableLogger, branch_name: str, condition: bool, context: Dict[str, Any]):
        """记录分支决策日志"""
        logger.info(f"Branch decision: {branch_name}",
                   extra={"branch": branch_name, "condition": condition, "context": context})

    @staticmethod
    def log_external_call(logger: ObservableLogger, service: str, endpoint: str,
                         request: Dict, response: Optional[Dict] = None, duration: float = 0):
        """记录外部调用日志"""
        log_data = {
            "service": service,
            "endpoint": endpoint,
            "request": LogPathCoverage._sanitize_args(request, {}),
            "duration": duration
        }
        if response:
            log_data["response"] = LogPathCoverage._sanitize_result(response)
        logger.info(f"External call: {service}/{endpoint}", extra=log_data)

    @staticmethod
    def log_exception(logger: ObservableLogger, context: str, exception: Exception):
        """记录异常日志"""
        logger.exception(f"Exception in {context}",
                        extra={"context": context, "error_type": type(exception).__name__})

    @staticmethod
    def _sanitize_args(args: tuple, kwargs: dict) -> Dict[str, Any]:
        """脱敏处理参数"""
        # 简单实现：只记录非敏感信息
        sensitive_keys = ['password', 'secret', 'key', 'token', 'api_key', 'apikey']
        safe_kwargs = {}
        for k, v in kwargs.items():
            if any(s in k.lower() for s in sensitive_keys):
                safe_kwargs[k] = "***REDACTED***"
            else:
                safe_kwargs[k] = str(v)[:100] if len(str(v)) > 100 else str(v)
        return safe_kwargs

    @staticmethod
    def _sanitize_result(result: Any) -> str:
        """脱敏处理结果"""
        if isinstance(result, dict):
            return str({k: v for k, v in result.items() if not isinstance(v, (bytes, bytearray))})[:200]
        return str(result)[:200] if result else "None"


# 创建全局日志实例
def get_logger(name: str, level: int = logging.INFO) -> ObservableLogger:
    """获取可观测日志记录器"""
    return ObservableLogger(name, level)


# 中间件：为每个请求设置追踪上下文
class TraceMiddleware:
    """FastAPI 追踪中间件"""

    def __init__(self, app):
        self.app = app
        self.logger = get_logger("trace_middleware")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # 生成或提取追踪 ID
        headers = dict(scope.get("headers", []))
        trace_id = headers.get(b"x-trace-id", b"").decode() or str(uuid.uuid4())
        request_id = headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())

        TraceContext.set_trace_id(trace_id)
        TraceContext.set_request_id(request_id)

        self.logger.info(f"Request started: {scope['method']} {scope['path']}",
                        extra={"method": scope["method"], "path": scope["path"]})

        start_time = time.time()

        try:
            return await self.app(scope, receive, send)
        finally:
            duration = time.time() - start_time
            global_metrics.record_timing(f"http.{scope['method']}.{scope['path']}", duration)
            self.logger.info(f"Request completed: {scope['method']} {scope['path']} ({duration:.3f}s)",
                            extra={"duration": duration})
            # 清理工件上下文
            TraceContext.clear()


# 监控指标端点数据
def get_metrics_summary() -> Dict[str, Any]:
    """获取监控指标摘要"""
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": global_metrics.get_all_metrics(),
        "active_traces": 0  # 可以扩展为追踪活跃的请求数
    }
