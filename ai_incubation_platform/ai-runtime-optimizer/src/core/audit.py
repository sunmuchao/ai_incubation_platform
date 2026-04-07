"""
审计日志模块：记录 Agent 运行 trace 与工具调用链
用于可观测性、问题排查与合规审计
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from enum import Enum


class AuditEventType(str, Enum):
    """审计事件类型"""
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    STRATEGY_EXECUTE = "strategy_execute"
    CODE_GENERATE = "code_generate"
    LLM_CALL = "llm_call"
    STORAGE_READ = "storage_read"
    STORAGE_WRITE = "storage_write"
    ADAPTER_CALL = "adapter_call"
    ERROR = "error"


class AuditStatus(str, Enum):
    """审计事件状态"""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str = field(default_factory=lambda: f"audit-{uuid.uuid4().hex[:12]}")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: AuditEventType = AuditEventType.API_REQUEST
    status: AuditStatus = AuditStatus.PENDING
    trace_id: Optional[str] = None  # 关联的用户请求 trace_id
    service_name: Optional[str] = None  # 服务名称
    actor: Optional[str] = None  # 操作者（API 用户、系统任务等）
    action: str = ""  # 具体动作描述
    input_data: Optional[Dict[str, Any]] = None  # 输入数据（脱敏后）
    output_data: Optional[Dict[str, Any]] = None  # 输出数据（脱敏后）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    duration_ms: Optional[float] = None  # 耗时（毫秒）
    error_message: Optional[str] = None  # 错误消息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("audit")
        self._handlers: List[Callable[[AuditEvent], None]] = []

    def add_handler(self, handler: Callable[[AuditEvent], None]):
        """添加事件处理器"""
        self._handlers.append(handler)

    def log(self, event: AuditEvent):
        """记录审计事件"""
        # 调用所有注册的处理器
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Audit handler failed: {e}")

        # 同时输出到标准日志
        log_data = event.to_dict()
        log_data["timestamp"] = event.timestamp.isoformat()

        if event.status == AuditStatus.FAILURE:
            self.logger.error(f"AuditEvent: {log_data}")
        else:
            self.logger.info(f"AuditEvent: {log_data}")

    def _create_event(
        self,
        event_type: AuditEventType,
        action: str,
        trace_id: Optional[str] = None,
        service_name: Optional[str] = None,
        **kwargs
    ) -> AuditEvent:
        """创建审计事件"""
        return AuditEvent(
            event_type=event_type,
            action=action,
            trace_id=trace_id,
            service_name=service_name,
            **kwargs
        )

    def log_api_request(
        self,
        endpoint: str,
        method: str,
        body: Optional[Dict[str, Any]],
        trace_id: Optional[str] = None,
        service_name: Optional[str] = None,
        actor: Optional[str] = None
    ):
        """记录 API 请求"""
        event = self._create_event(
            event_type=AuditEventType.API_REQUEST,
            action=f"{method} {endpoint}",
            trace_id=trace_id,
            service_name=service_name,
            actor=actor,
            input_data={"endpoint": endpoint, "method": method, "body": body},
            status=AuditStatus.PENDING
        )
        self.log(event)
        return event.event_id

    def log_api_response(
        self,
        event_id: str,
        status_code: int,
        response: Optional[Dict[str, Any]],
        duration_ms: float
    ):
        """记录 API 响应"""
        event = AuditEvent(
            event_id=event_id,
            event_type=AuditEventType.API_RESPONSE,
            status=AuditStatus.SUCCESS if status_code < 400 else AuditStatus.FAILURE,
            action="api_response",
            output_data={"status_code": status_code, "response": response},
            duration_ms=duration_ms
        )
        self.log(event)

    def log_strategy_execute(
        self,
        strategy_id: str,
        strategy_type: str,
        input_data: Dict[str, Any],
        suggestions_count: int,
        trace_id: Optional[str] = None,
        service_name: Optional[str] = None,
        duration_ms: Optional[float] = None,
        status: AuditStatus = AuditStatus.SUCCESS
    ):
        """记录策略执行"""
        event = self._create_event(
            event_type=AuditEventType.STRATEGY_EXECUTE,
            action=f"execute_strategy:{strategy_id}",
            trace_id=trace_id,
            service_name=service_name,
            input_data={"strategy_id": strategy_id, "strategy_type": strategy_type},
            output_data={"suggestions_count": suggestions_count},
            duration_ms=duration_ms,
            status=status
        )
        self.log(event)

    def log_code_generate(
        self,
        patch_id: str,
        suggestion_id: str,
        language: str,
        trace_id: Optional[str] = None,
        service_name: Optional[str] = None,
        duration_ms: Optional[float] = None,
        status: AuditStatus = AuditStatus.SUCCESS
    ):
        """记录代码生成"""
        event = self._create_event(
            event_type=AuditEventType.CODE_GENERATE,
            action=f"generate_code:{patch_id}",
            trace_id=trace_id,
            service_name=service_name,
            input_data={"suggestion_id": suggestion_id, "language": language},
            duration_ms=duration_ms,
            status=status
        )
        self.log(event)

    def log_llm_call(
        self,
        provider: str,
        model: str,
        operation: str,
        trace_id: Optional[str] = None,
        service_name: Optional[str] = None,
        duration_ms: Optional[float] = None,
        status: AuditStatus = AuditStatus.SUCCESS,
        error_message: Optional[str] = None
    ):
        """记录 LLM 调用"""
        event = self._create_event(
            event_type=AuditEventType.LLM_CALL,
            action=f"llm_{operation}:{provider}/{model}",
            trace_id=trace_id,
            service_name=service_name,
            metadata={"provider": provider, "model": model, "operation": operation},
            duration_ms=duration_ms,
            status=status,
            error_message=error_message
        )
        self.log(event)

    def log_storage_operation(
        self,
        operation: str,
        entity_type: str,
        entity_id: Optional[str],
        service_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        status: AuditStatus = AuditStatus.SUCCESS
    ):
        """记录存储操作"""
        event = self._create_event(
            event_type=AuditEventType.STORAGE_READ if operation == "read" else AuditEventType.STORAGE_WRITE,
            action=f"storage_{operation}:{entity_type}",
            trace_id=trace_id,
            service_name=service_name,
            input_data={"entity_type": entity_type, "entity_id": entity_id},
            duration_ms=duration_ms,
            status=status
        )
        self.log(event)

    def log_adapter_call(
        self,
        adapter_name: str,
        method: str,
        service_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        status: AuditStatus = AuditStatus.SUCCESS,
        error_message: Optional[str] = None
    ):
        """记录适配器调用"""
        event = self._create_event(
            event_type=AuditEventType.ADAPTER_CALL,
            action=f"adapter:{adapter_name}.{method}",
            trace_id=trace_id,
            service_name=service_name,
            metadata={"adapter_name": adapter_name, "method": method},
            duration_ms=duration_ms,
            status=status,
            error_message=error_message
        )
        self.log(event)

    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        service_name: Optional[str] = None
    ):
        """记录错误"""
        event = self._create_event(
            event_type=AuditEventType.ERROR,
            action=f"error:{error_type}",
            trace_id=trace_id,
            service_name=service_name,
            input_data=context,
            status=AuditStatus.FAILURE,
            error_message=error_message
        )
        self.log(event)

    @contextmanager
    def trace_operation(
        self,
        event_type: AuditEventType,
        action: str,
        trace_id: Optional[str] = None,
        service_name: Optional[str] = None
    ):
        """上下文管理器：自动记录操作开始和结束"""
        import time
        start_time = time.time()

        event = self._create_event(
            event_type=event_type,
            action=action,
            trace_id=trace_id,
            service_name=service_name,
            status=AuditStatus.PENDING
        )

        try:
            yield event
            duration_ms = (time.time() - start_time) * 1000
            event.status = AuditStatus.SUCCESS
            event.duration_ms = duration_ms
            self.log(event)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            event.status = AuditStatus.FAILURE
            event.duration_ms = duration_ms
            event.error_message = str(e)
            self.log(event)
            raise


# 全局审计日志实例
audit_logger = AuditLogger()


def get_trace_id() -> str:
    """生成或获取 trace_id"""
    return f"trace-{uuid.uuid4().hex[:12]}"
