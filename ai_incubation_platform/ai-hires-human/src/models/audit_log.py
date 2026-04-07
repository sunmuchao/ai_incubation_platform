"""
审计日志模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AuditLog(Base):
    """
    审计日志 - 记录所有敏感操作

    记录的操作包括：
    - 数据变更（增删改）
    - 权限相关操作
    - 支付/交易操作
    - AI 自主决策执行
    """
    __tablename__ = "audit_logs"

    id = Column(String(100), primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    actor = Column(String(100), nullable=False, index=True, comment="操作者 ID")
    action = Column(String(100), nullable=False, index=True, comment="操作类型")
    resource = Column(String(200), nullable=True, index=True, comment="资源 ID")
    request = Column(Text, nullable=True, comment="JSON 请求内容")
    response = Column(Text, nullable=True, comment="JSON 响应内容")
    status = Column(String(20), nullable=False, comment="操作状态：success/failure")
    trace_id = Column(String(100), nullable=True, index=True, comment="追踪 ID")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, actor={self.actor}, action={self.action}, status={self.status})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "request": self.request,
            "response": self.response,
            "status": self.status,
            "trace_id": self.trace_id,
        }
