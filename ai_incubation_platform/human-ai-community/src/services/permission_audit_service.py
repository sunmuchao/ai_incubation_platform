"""
权限审计日志服务

提供权限相关操作的审计功能：
- 权限变更记录
- 权限检查日志
- 审计查询与导出
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json


class AuditEventType(str, Enum):
    """审计事件类型"""
    # 权限变更
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    PERMISSION_DENIED = "permission_denied"
    ROLE_PERMISSIONS_UPDATED = "role_permissions_updated"

    # 角色变更
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # 频道权限
    CHANNEL_PERMISSION_UPDATED = "channel_permission_updated"
    CHANNEL_ACCESS_GRANTED = "channel_access_granted"
    CHANNEL_ACCESS_REVOKED = "channel_access_revoked"

    # 内容访问
    CONTENT_ACCESS_DENIED = "content_access_denied"
    CONTENT_ACCESS_GRANTED = "content_access_granted"

    # 管理操作
    ADMIN_ACTION = "admin_action"
    CONFIG_EXPORTED = "config_exported"
    CONFIG_IMPORTED = "config_imported"


class AuditLogEntry:
    """审计日志条目"""

    def __init__(
        self,
        event_type: AuditEventType,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.actor_id = actor_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = details
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "actor_id": self.actor_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat()
        }


class PermissionAuditService:
    """权限审计服务"""

    def __init__(self):
        self._logs: List[AuditLogEntry] = []
        self._index_by_actor: Dict[str, List[AuditLogEntry]] = {}
        self._index_by_resource: Dict[str, List[AuditLogEntry]] = {}
        self._index_by_event: Dict[str, List[AuditLogEntry]] = {}
        self._index_by_timestamp: List[AuditLogEntry] = []

    def log(
        self,
        event_type: AuditEventType,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLogEntry:
        """记录审计日志"""
        entry = AuditLogEntry(
            event_type=event_type,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self._logs.append(entry)

        # 更新索引
        if actor_id not in self._index_by_actor:
            self._index_by_actor[actor_id] = []
        self._index_by_actor[actor_id].append(entry)

        resource_key = f"{resource_type}:{resource_id}"
        if resource_key not in self._index_by_resource:
            self._index_by_resource[resource_key] = []
        self._index_by_resource[resource_key].append(entry)

        event_key = event_type.value
        if event_key not in self._index_by_event:
            self._index_by_event[event_key] = []
        self._index_by_event[event_key].append(entry)

        self._index_by_timestamp.append(entry)

        return entry

    def log_permission_granted(
        self,
        actor_id: str,
        target_user_id: str,
        permission: str,
        operator_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditLogEntry:
        """记录权限授予事件"""
        return self.log(
            event_type=AuditEventType.PERMISSION_GRANTED,
            actor_id=actor_id,
            resource_type="user",
            resource_id=target_user_id,
            details={
                "permission": permission,
                "operator_id": operator_id
            },
            ip_address=ip_address
        )

    def log_permission_revoked(
        self,
        actor_id: str,
        target_user_id: str,
        permission: str,
        operator_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditLogEntry:
        """记录权限撤销事件"""
        return self.log(
            event_type=AuditEventType.PERMISSION_REVOKED,
            actor_id=actor_id,
            resource_type="user",
            resource_id=target_user_id,
            details={
                "permission": permission,
                "operator_id": operator_id
            },
            ip_address=ip_address
        )

    def log_role_permissions_updated(
        self,
        actor_id: str,
        role: str,
        added_permissions: List[str],
        removed_permissions: List[str],
        ip_address: Optional[str] = None
    ) -> AuditLogEntry:
        """记录角色权限变更事件"""
        return self.log(
            event_type=AuditEventType.ROLE_PERMISSIONS_UPDATED,
            actor_id=actor_id,
            resource_type="role",
            resource_id=role,
            details={
                "added_permissions": added_permissions,
                "removed_permissions": removed_permissions
            },
            ip_address=ip_address
        )

    def log_channel_permission_updated(
        self,
        actor_id: str,
        channel_id: str,
        role: str,
        permissions: List[str],
        ip_address: Optional[str] = None
    ) -> AuditLogEntry:
        """记录频道权限变更事件"""
        return self.log(
            event_type=AuditEventType.CHANNEL_PERMISSION_UPDATED,
            actor_id=actor_id,
            resource_type="channel",
            resource_id=channel_id,
            details={
                "role": role,
                "permissions": permissions
            },
            ip_address=ip_address
        )

    def log_content_access_denied(
        self,
        user_id: str,
        content_type: str,
        content_id: str,
        required_permission: str,
        user_role: str,
        ip_address: Optional[str] = None
    ) -> AuditLogEntry:
        """记录内容访问拒绝事件"""
        return self.log(
            event_type=AuditEventType.CONTENT_ACCESS_DENIED,
            actor_id=user_id,
            resource_type=content_type,
            resource_id=content_id,
            details={
                "required_permission": required_permission,
                "user_role": user_role
            },
            ip_address=ip_address
        )

    def get_logs_by_actor(
        self,
        actor_id: str,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """获取用户的操作日志"""
        logs = self._index_by_actor.get(actor_id, [])
        return self._filter_and_format_logs(logs, limit, start_time, end_time)

    def get_logs_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """获取资源的操作日志"""
        key = f"{resource_type}:{resource_id}"
        logs = self._index_by_resource.get(key, [])
        return self._filter_and_format_logs(logs, limit, start_time, end_time)

    def get_logs_by_event_type(
        self,
        event_type: AuditEventType,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """获取指定类型的操作日志"""
        logs = self._index_by_event.get(event_type.value, [])
        return self._filter_and_format_logs(logs, limit, start_time, end_time)

    def get_recent_logs(
        self,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """获取最近的日志"""
        # 按时间倒序
        logs = sorted(self._index_by_timestamp, key=lambda x: x.timestamp, reverse=True)
        return self._filter_and_format_logs(logs[:limit*2], limit, start_time, end_time)

    def _filter_and_format_logs(
        self,
        logs: List[AuditLogEntry],
        limit: int,
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """过滤和格式化日志"""
        # 时间过滤
        if start_time:
            logs = [l for l in logs if l.timestamp >= start_time]
        if end_time:
            logs = [l for l in logs if l.timestamp <= end_time]

        # 按时间倒序
        logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)

        # 限制数量
        logs = logs[:limit]

        return [l.to_dict() for l in logs]

    def get_audit_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取审计统计"""
        logs = self._index_by_timestamp

        # 时间过滤
        if start_time:
            logs = [l for l in logs if l.timestamp >= start_time]
        if end_time:
            logs = [l for l in logs if l.timestamp <= end_time]

        # 按事件类型统计
        event_counts = {}
        for log in logs:
            event_key = log.event_type.value
            event_counts[event_key] = event_counts.get(event_key, 0) + 1

        # 按资源类型统计
        resource_counts = {}
        for log in logs:
            resource_key = log.resource_type
            resource_counts[resource_key] = resource_counts.get(resource_key, 0) + 1

        return {
            "total_logs": len(logs),
            "event_counts": event_counts,
            "resource_counts": resource_counts,
            "unique_actors": len(self._index_by_actor)
        }

    def export_logs(
        self,
        format: str = "json",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> str:
        """导出审计日志"""
        logs = self.get_recent_logs(limit=10000, start_time=start_time, end_time=end_time)

        if format == "json":
            return json.dumps(logs, indent=2, ensure_ascii=False)
        elif format == "csv":
            return self._export_to_csv(logs)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_to_csv(self, logs: List[Dict[str, Any]]) -> str:
        """导出为 CSV 格式"""
        headers = ["id", "timestamp", "event_type", "actor_id", "resource_type", "resource_id", "details"]
        lines = [",".join(headers)]

        for log in logs:
            row = [
                log["id"],
                log["timestamp"],
                log["event_type"],
                log["actor_id"],
                log["resource_type"],
                log["resource_id"],
                json.dumps(log["details"]).replace('"', '""')
            ]
            lines.append(",".join(row))

        return "\n".join(lines)


# 全局服务实例
permission_audit_service = PermissionAuditService()
