"""
审计日志模型

提供审计日志、查询日志、访问日志的实体定义
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid


@dataclass
class AuditLogEntry:
    """审计日志条目"""

    action_type: str  # 操作类型：QUERY_EXECUTE, CONFIG_CHANGE, USER_LOGIN 等
    tenant_id: str
    user_id: Optional[str] = None
    resource_type: Optional[str] = None  # 资源类型：datasource, table, user 等
    resource_id: Optional[str] = None  # 资源 ID
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    request_body: Optional[Dict[str, Any]] = None
    response_status: Optional[int] = None
    response_body: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    connector_name: Optional[str] = None
    query_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.id is None:
            self.id = f"audit_{uuid.uuid4().hex[:12]}"
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "request_body": json.dumps(self.request_body) if self.request_body else None,
            "response_status": self.response_status,
            "response_body": json.dumps(self.response_body) if self.response_body else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "connector_name": self.connector_name,
            "query_id": self.query_id,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLogEntry":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
            tenant_id=data.get("tenant_id"),
            user_id=data.get("user_id"),
            action_type=data.get("action_type"),
            resource_type=data.get("resource_type"),
            resource_id=data.get("resource_id"),
            request_method=data.get("request_method"),
            request_path=data.get("request_path"),
            request_body=json.loads(data["request_body"]) if data.get("request_body") else None,
            response_status=data.get("response_status"),
            response_body=json.loads(data["response_body"]) if data.get("response_body") else None,
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            connector_name=data.get("connector_name"),
            query_id=data.get("query_id"),
            metadata=json.loads(data["metadata"]) if data.get("metadata") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass
class QueryLogEntry:
    """查询日志条目"""

    query_id: str
    datasource: str
    sql: str
    connector_name: str
    tenant_id: str
    user_id: Optional[str] = None
    duration_ms: float = 0.0
    result_rows: int = 0
    status: str = "pending"  # pending, success, error
    error_message: Optional[str] = None
    rows_returned: int = 0
    bytes_processed: int = 0
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.id is None:
            self.id = f"query_{uuid.uuid4().hex[:12]}"
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "query_id": self.query_id,
            "datasource": self.datasource,
            "sql": self.sql,
            "connector_name": self.connector_name,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "duration_ms": self.duration_ms,
            "result_rows": self.result_rows,
            "status": self.status,
            "error_message": self.error_message,
            "rows_returned": self.rows_returned,
            "bytes_processed": self.bytes_processed,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryLogEntry":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            query_id=data.get("query_id"),
            datasource=data.get("datasource"),
            sql=data.get("sql"),
            connector_name=data.get("connector_name"),
            tenant_id=data.get("tenant_id"),
            user_id=data.get("user_id"),
            duration_ms=data.get("duration_ms", 0.0),
            result_rows=data.get("result_rows", 0),
            status=data.get("status", "pending"),
            error_message=data.get("error_message"),
            rows_returned=data.get("rows_returned", 0),
            bytes_processed=data.get("bytes_processed", 0),
            metadata=json.loads(data["metadata"]) if data.get("metadata") else None,
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass
class AccessLogEntry:
    """访问日志条目"""

    user_id: str
    resource: str  # 被访问的资源
    action: str  # 访问动作：read, write, delete
    granted: bool  # 是否允许
    tenant_id: str
    reason: Optional[str] = None  # 拒绝原因
    ip_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.id is None:
            self.id = f"access_{uuid.uuid4().hex[:12]}"
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "resource": self.resource,
            "action": self.action,
            "granted": self.granted,
            "reason": self.reason,
            "ip_address": self.ip_address,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessLogEntry":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
            tenant_id=data.get("tenant_id"),
            user_id=data.get("user_id"),
            resource=data.get("resource"),
            action=data.get("action"),
            granted=data.get("granted", False),
            reason=data.get("reason"),
            ip_address=data.get("ip_address"),
            metadata=json.loads(data["metadata"]) if data.get("metadata") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass
class LogRetentionPolicy:
    """日志保留策略"""

    log_type: str  # audit, query, access
    retention_days: int = 90
    storage_backend: str = "database"  # database, file, s3
    compression_enabled: bool = True
    export_enabled: bool = False
    export_destination: Optional[str] = None
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.id is None:
            self.id = f"policy_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "log_type": self.log_type,
            "retention_days": self.retention_days,
            "storage_backend": self.storage_backend,
            "compression_enabled": self.compression_enabled,
            "export_enabled": self.export_enabled,
            "export_destination": self.export_destination,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogRetentionPolicy":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            log_type=data.get("log_type"),
            retention_days=data.get("retention_days", 90),
            storage_backend=data.get("storage_backend", "database"),
            compression_enabled=data.get("compression_enabled", True),
            export_enabled=data.get("export_enabled", False),
            export_destination=data.get("export_destination"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )


@dataclass
class LogExportJob:
    """日志导出任务"""

    log_type: str
    time_range_start: datetime
    time_range_end: datetime
    tenant_id: str
    format: str = "json"  # json, csv
    destination: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    record_count: int = 0
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.id is None:
            self.id = f"export_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "log_type": self.log_type,
            "time_range_start": self.time_range_start.isoformat() if self.time_range_start else None,
            "time_range_end": self.time_range_end.isoformat() if self.time_range_end else None,
            "format": self.format,
            "destination": self.destination,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "error_message": self.error_message,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "record_count": self.record_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogExportJob":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            log_type=data.get("log_type"),
            time_range_start=datetime.fromisoformat(data["time_range_start"]) if data.get("time_range_start") else None,
            time_range_end=datetime.fromisoformat(data["time_range_end"]) if data.get("time_range_end") else None,
            format=data.get("format", "json"),
            destination=data.get("destination"),
            tenant_id=data.get("tenant_id"),
            status=data.get("status", "pending"),
            error_message=data.get("error_message"),
            file_path=data.get("file_path"),
            file_size_bytes=data.get("file_size_bytes", 0),
            record_count=data.get("record_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )


@dataclass
class UserActivityReport:
    """用户活动报告"""

    user_id: str
    tenant_id: str
    time_range_start: datetime
    time_range_end: datetime
    total_actions: int = 0
    action_breakdown: Dict[str, int] = field(default_factory=dict)
    resources_accessed: List[str] = field(default_factory=list)
    queries_executed: int = 0
    total_query_duration_ms: float = 0.0
    failed_actions: int = 0
    ip_addresses: List[str] = field(default_factory=list)
    generated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "time_range_start": self.time_range_start.isoformat() if self.time_range_start else None,
            "time_range_end": self.time_range_end.isoformat() if self.time_range_end else None,
            "total_actions": self.total_actions,
            "action_breakdown": self.action_breakdown,
            "resources_accessed": self.resources_accessed,
            "queries_executed": self.queries_executed,
            "total_query_duration_ms": self.total_query_duration_ms,
            "failed_actions": self.failed_actions,
            "ip_addresses": self.ip_addresses,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }


@dataclass
class LogAnomaly:
    """日志异常"""

    anomaly_type: str  # unusual_activity, failed_login_spike, query_pattern_change
    severity: str  # low, medium, high, critical
    description: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    affected_resources: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    detected_at: Optional[datetime] = None
    id: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = f"anomaly_{uuid.uuid4().hex[:12]}"
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "description": self.description,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "affected_resources": self.affected_resources,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None
        }


@dataclass
class ComplianceReport:
    """合规报告"""

    report_type: str  # soc2, gdpr, access_review
    tenant_id: str
    time_range_start: datetime
    time_range_end: datetime
    summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    status: str = "draft"  # draft, final
    generated_by: Optional[str] = None
    id: Optional[str] = None
    generated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.id is None:
            self.id = f"compliance_{uuid.uuid4().hex[:12]}"
        if self.generated_at is None:
            self.generated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "report_type": self.report_type,
            "tenant_id": self.tenant_id,
            "time_range_start": self.time_range_start.isoformat() if self.time_range_start else None,
            "time_range_end": self.time_range_end.isoformat() if self.time_range_end else None,
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "status": self.status,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }
