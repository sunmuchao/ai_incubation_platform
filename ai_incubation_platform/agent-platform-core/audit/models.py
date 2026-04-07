"""
审计数据模型

定义审计日志的数据结构
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time
import uuid


class AuditLogStatus(Enum):
    """审计日志状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    STARTED = "started"
    CANCELLED = "cancelled"


class AuditResourceType(Enum):
    """资源类型"""
    USER = "user"
    TOOL = "tool"
    WORKFLOW = "workflow"
    DATA = "data"
    CONFIG = "config"
    SYSTEM = "system"
    OTHER = "other"


@dataclass
class AuditLog:
    """
    审计日志记录

    记录所有敏感操作的详细信息
    """
    # 唯一标识
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # 执行者信息
    actor: str = ""  # 用户 ID 或系统标识
    actor_type: str = "user"  # user/system/service
    actor_ip: Optional[str] = None
    actor_user_agent: Optional[str] = None

    # 操作信息
    action: str = ""  # 操作类型，如 create/update/delete/execute
    resource_type: AuditResourceType = AuditResourceType.OTHER
    resource: str = ""  # 资源标识
    resource_details: Optional[Dict[str, Any]] = None

    # 请求信息
    request: Dict[str, Any] = field(default_factory=dict)
    request_hash: Optional[str] = None  # 请求内容的哈希（用于大请求）

    # 响应信息
    response: Dict[str, Any] = field(default_factory=dict)
    response_size: int = 0

    # 执行结果
    status: AuditLogStatus = AuditLogStatus.SUCCESS
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    # 追踪信息
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_trace_id: Optional[str] = None

    # 上下文信息
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    # 时间信息
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    # 系统字段
    created_at: float = field(default_factory=time.time)
    version: int = 1

    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.trace_id:
            self.trace_id = f"audit_{self.id}"

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.end_time is not None

    @property
    def execution_time_ms(self) -> float:
        """执行时间（毫秒）"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return self.duration_ms

    def mark_success(self, response: Optional[Dict] = None) -> None:
        """标记成功"""
        self.status = AuditLogStatus.SUCCESS
        self.end_time = time.time()
        if response:
            self.response = response
            self.response_size = len(str(response))

    def mark_failed(self, error: str, error_code: Optional[str] = None) -> None:
        """标记失败"""
        self.status = AuditLogStatus.FAILED
        self.end_time = time.time()
        self.error_message = error
        self.error_code = error_code

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "actor_ip": self.actor_ip,
            "action": self.action,
            "resource_type": self.resource_type.value,
            "resource": self.resource,
            "resource_details": self.resource_details,
            "request": self.request,
            "response": self.response,
            "status": self.status.value,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "trace_id": self.trace_id,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.execution_time_ms,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditLog':
        """从字典创建"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            actor=data.get("actor", ""),
            actor_type=data.get("actor_type", "user"),
            actor_ip=data.get("actor_ip"),
            action=data.get("action", ""),
            resource_type=AuditResourceType(data.get("resource_type", "other")),
            resource=data.get("resource", ""),
            resource_details=data.get("resource_details"),
            request=data.get("request", {}),
            response=data.get("response", {}),
            status=AuditLogStatus(data.get("status", "success")),
            error_message=data.get("error_message"),
            error_code=data.get("error_code"),
            trace_id=data.get("trace_id"),
            tenant_id=data.get("tenant_id"),
            session_id=data.get("session_id"),
            request_id=data.get("request_id"),
            start_time=data.get("start_time", time.time()),
            end_time=data.get("end_time"),
            duration_ms=data.get("duration_ms", 0.0),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", [])
        )

    def __str__(self) -> str:
        return (
            f"AuditLog(id={self.id}, actor={self.actor}, "
            f"action={self.action}, resource={self.resource}, "
            f"status={self.status.value})"
        )


@dataclass
class AuditQuery:
    """
    审计查询条件

    用于查询审计日志
    """
    # 执行者过滤
    actor: Optional[str] = None
    actor_type: Optional[str] = None

    # 操作过滤
    action: Optional[str] = None
    resource_type: Optional[AuditResourceType] = None
    resource: Optional[str] = None

    # 状态过滤
    status: Optional[AuditLogStatus] = None
    has_error: Optional[bool] = None

    # 时间范围
    start_time_from: Optional[float] = None
    start_time_to: Optional[float] = None
    duration_min: Optional[float] = None
    duration_max: Optional[float] = None

    # 追踪过滤
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # 全文搜索
    search_text: Optional[str] = None

    # 分页
    limit: int = 100
    offset: int = 0

    # 排序
    sort_by: str = "start_time"
    sort_desc: bool = True

    # 标签过滤
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "actor": self.actor,
            "actor_type": self.actor_type,
            "action": self.action,
            "resource_type": self.resource_type.value if self.resource_type else None,
            "resource": self.resource,
            "status": self.status.value if self.status else None,
            "has_error": self.has_error,
            "start_time_from": self.start_time_from,
            "start_time_to": self.start_time_to,
            "duration_min": self.duration_min,
            "duration_max": self.duration_max,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "search_text": self.search_text,
            "limit": self.limit,
            "offset": self.offset,
            "sort_by": self.sort_by,
            "sort_desc": self.sort_desc,
            "tags": self.tags
        }

    def matches(self, log: AuditLog) -> bool:
        """检查日志是否匹配查询条件"""
        # 执行者过滤
        if self.actor and self.actor.lower() not in log.actor.lower():
            return False
        if self.actor_type and self.actor_type != log.actor_type:
            return False

        # 操作过滤
        if self.action and self.action.lower() not in log.action.lower():
            return False
        if self.resource_type and self.resource_type != log.resource_type:
            return False
        if self.resource and self.resource.lower() not in log.resource.lower():
            return False

        # 状态过滤
        if self.status and self.status != log.status:
            return False
        if self.has_error is not None:
            has_error = log.error_message is not None
            if self.has_error != has_error:
                return False

        # 时间范围
        if self.start_time_from and log.start_time < self.start_time_from:
            return False
        if self.start_time_to and log.start_time > self.start_time_to:
            return False
        if self.duration_min and log.execution_time_ms < self.duration_min:
            return False
        if self.duration_max and log.execution_time_ms > self.duration_max:
            return False

        # 追踪过滤
        if self.trace_id and self.trace_id != log.trace_id:
            return False
        if self.session_id and self.session_id != log.session_id:
            return False
        if self.tenant_id and self.tenant_id != log.tenant_id:
            return False

        # 标签过滤
        if self.tags:
            if not any(tag in log.tags for tag in self.tags):
                return False

        # 全文搜索
        if self.search_text:
            search_lower = self.search_text.lower()
            searchable = (
                f"{log.actor} {log.action} {log.resource} "
                f"{log.error_message or ''}"
            ).lower()
            if search_lower not in searchable:
                return False

        return True


@dataclass
class AuditReport:
    """
    审计报告

    用于生成审计报告和统计
    """
    # 报告时间范围
    start_time: float
    end_time: float

    # 统计信息
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    avg_duration_ms: float = 0.0

    # 按执行者统计
    by_actor: Dict[str, int] = field(default_factory=dict)

    # 按操作类型统计
    by_action: Dict[str, int] = field(default_factory=dict)

    # 按资源类型统计
    by_resource_type: Dict[str, int] = field(default_factory=dict)

    # 错误统计
    errors: List[Dict[str, Any]] = field(default_factory=list)

    # 慢操作（>1 秒）
    slow_operations: List[AuditLog] = field(default_factory=list)

    def add_log(self, log: AuditLog) -> None:
        """添加日志到报告"""
        self.total_count += 1

        if log.status == AuditLogStatus.SUCCESS:
            self.success_count += 1
        else:
            self.failed_count += 1
            self.errors.append({
                "id": log.id,
                "actor": log.actor,
                "action": log.action,
                "resource": log.resource,
                "error": log.error_message,
                "time": log.start_time
            })

        # 统计执行者
        self.by_actor[log.actor] = self.by_actor.get(log.actor, 0) + 1

        # 统计操作类型
        self.by_action[log.action] = self.by_action.get(log.action, 0) + 1

        # 统计资源类型
        rt_key = log.resource_type.value
        self.by_resource_type[rt_key] = self.by_resource_type.get(rt_key, 0) + 1

        # 慢操作
        if log.execution_time_ms > 1000:
            self.slow_operations.append(log)

    def finalize(self) -> None:
        """完成报告计算"""
        if self.total_count > 0:
            self.avg_duration_ms = (
                sum(log.execution_time_ms for log in self.slow_operations) /
                len(self.slow_operations)
                if self.slow_operations else 0
            )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "success_rate": self.success_count / self.total_count if self.total_count > 0 else 0,
            "avg_duration_ms": self.avg_duration_ms,
            "by_actor": self.by_actor,
            "by_action": self.by_action,
            "by_resource_type": self.by_resource_type,
            "error_count": len(self.errors),
            "slow_operation_count": len(self.slow_operations)
        }
