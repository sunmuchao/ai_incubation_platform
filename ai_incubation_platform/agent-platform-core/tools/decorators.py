"""
工具装饰器

提供便捷的工具注册和增强装饰器
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def tool(
    name: str,
    description: str = "",
    input_schema: Optional[Dict] = None,
    requires_auth: bool = False,
    requires_audit: bool = True,
    rate_limit: Optional[int] = None,
    tags: Optional[List[str]] = None
):
    """
    工具装饰器

    用于将函数注册为工具

    Args:
        name: 工具名称
        description: 工具描述
        input_schema: 输入 schema
        requires_auth: 是否需要认证
        requires_audit: 是否需要审计日志
        rate_limit: 限流配置
        tags: 标签列表

    Example:
        @tool(
            name="search_users",
            description="Search users by name",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            },
            tags=["user", "search"]
        )
        async def search_users(query: str) -> dict:
            return {"users": [...]}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        # 添加工具元数据
        wrapper._tool_config = {
            "name": name,
            "description": description or func.__doc__ or "",
            "input_schema": input_schema or _infer_input_schema(func),
            "requires_auth": requires_auth,
            "requires_audit": requires_audit,
            "rate_limit": rate_limit,
            "tags": tags or []
        }

        return wrapper

    return decorator


def _infer_input_schema(func: Callable) -> Dict[str, Any]:
    """从函数签名推断输入 schema"""
    import inspect

    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    sig = inspect.signature(func)
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object"
    }

    for param_name, param in sig.parameters.items():
        if param_name in ('self', 'cls', 'context'):
            continue

        param_type = param.annotation
        type_name = type_map.get(param_type, "string")

        schema["properties"][param_name] = {
            "type": type_name,
            "description": f"Parameter {param_name}"
        }

        if param.default == inspect.Parameter.empty:
            schema["required"].append(param_name)

    return schema


def validate_input(schema: Dict[str, Any]):
    """
    输入验证装饰器

    Args:
        schema: JSON Schema

    Example:
        @validate_input({
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"}
            },
            "required": ["email"]
        })
        async def send_email(email: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 简单验证
            errors = []

            # 检查必填参数
            required = schema.get("required", [])
            for param in required:
                if param not in kwargs and param not in [
                    str(a) for a in args
                ]:
                    errors.append(f"Missing required parameter: {param}")

            # 类型检查
            properties = schema.get("properties", {})
            for key, value in kwargs.items():
                if key in properties:
                    expected_type = properties[key].get("type")
                    if expected_type == "string" and not isinstance(value, str):
                        errors.append(f"Parameter {key} must be a string")
                    elif expected_type == "integer" and not isinstance(value, int):
                        errors.append(f"Parameter {key} must be an integer")
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        errors.append(f"Parameter {key} must be a number")
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        errors.append(f"Parameter {key} must be a boolean")
                    elif expected_type == "array" and not isinstance(value, list):
                        errors.append(f"Parameter {key} must be an array")
                    elif expected_type == "object" and not isinstance(value, dict):
                        errors.append(f"Parameter {key} must be an object")

            if errors:
                raise ValueError("; ".join(errors))

            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit(limit: int, window: int = 60):
    """
    限流装饰器

    Args:
        limit: 限制次数
        window: 时间窗口（秒）

    Example:
        @rate_limit(limit=10, window=60)
        async def send_notification(user_id: str):
            ...
    """
    # 限流状态存储
    _rate_limit_state: Dict[str, Dict] = {}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            current_time = time.time()

            if key not in _rate_limit_state:
                _rate_limit_state[key] = {"count": 0, "window_start": current_time}

            state = _rate_limit_state[key]

            # 重置窗口
            if current_time - state["window_start"] >= window:
                state["count"] = 0
                state["window_start"] = current_time

            state["count"] += 1

            if state["count"] > limit:
                raise Exception(
                    f"Rate limit exceeded: {limit} requests per {window} seconds"
                )

            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

        return wrapper

    return decorator


def require_auth(required: bool = True):
    """
    认证要求装饰器

    Args:
        required: 是否需要认证

    Example:
        @require_auth()
        async def delete_user(user_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, context=None, **kwargs):
            if required and context:
                if not getattr(context, 'user_id', None):
                    raise PermissionError("Authentication required")
            return await func(*args, context=context, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, context=context, **kwargs)

        wrapper._require_auth = required
        return wrapper

    return decorator


def with_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避因子

    Example:
        @with_retry(max_retries=3, delay=1.0)
        async def call_external_api(url: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import random
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")

                    if attempt < max_retries:
                        jitter = random.uniform(0, current_delay * 0.1)
                        await asyncio.sleep(current_delay + jitter)
                        current_delay *= backoff

            raise last_exception

        return wrapper

    return decorator


def with_timeout(timeout: float):
    """
    超时装饰器

    Args:
        timeout: 超时时间（秒）

    Example:
        @with_timeout(30.0)
        async def long_running_task(data: dict):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                else:
                    return await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, functools.partial(func, *args, **kwargs)),
                        timeout=timeout
                    )
            except asyncio.TimeoutError:
                raise Exception(f"Operation timed out after {timeout} seconds")

        return wrapper

    return decorator


def cache_result(ttl: int = 300):
    """
    缓存结果装饰器

    Args:
        ttl: 缓存过期时间（秒）

    Example:
        @cache_result(ttl=300)
        async def get_user_profile(user_id: str):
            ...
    """
    _cache: Dict[str, Dict] = {}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import hashlib
            key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            key = hashlib.md5(key_data.encode()).hexdigest()
            current_time = time.time()

            if key in _cache:
                entry = _cache[key]
                if current_time - entry["timestamp"] < ttl:
                    return entry["data"]
                else:
                    del _cache[key]

            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            _cache[key] = {
                "data": result,
                "timestamp": current_time
            }

            return result

        wrapper._cache_clear = lambda: _cache.clear()
        return wrapper

    return decorator


def log_execution(logger_obj: Optional[logging.Logger] = None):
    """
    执行日志装饰器

    Args:
        logger_obj: 日志记录器

    Example:
        @log_execution()
        async def process_data(data: dict):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            log = logger_obj or logger
            start_time = time.time()

            log.info(f"Starting {func.__name__}")
            log.debug(f"Args: {args}, Kwargs: {kwargs}")

            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                log.info(f"Completed {func.__name__} in {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                log.error(f"Failed {func.__name__} after {duration:.2f}ms: {e}")
                raise

        return wrapper

    return decorator


def register_tools(registry):
    """
    批量注册工具装饰器

    Args:
        registry: ToolsRegistry 实例

    Example:
        @register_tools(my_registry)
        class MyTools:
            @tool(name="tool1")
            async def tool1(): ...
    """
    def decorator(cls):
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_tool_config'):
                config = attr._tool_config
                registry.register(
                    name=config["name"],
                    handler=attr,
                    description=config["description"],
                    input_schema=config["input_schema"],
                    requires_auth=config["requires_auth"],
                    requires_audit=config["requires_audit"],
                    rate_limit=config["rate_limit"],
                    tags=config["tags"]
                )
        return cls

    return decorator
