"""
数据库索引和审计日志表定义
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class AuditLog(Base):
    """
    审计日志表 - 记录所有敏感操作

    用于：
    - 安全审计
    - 问题排查
    - 合规要求
    - 行为分析
    """
    __tablename__ = "audit_logs"

    id = Column(String(100), primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    actor = Column(String(100), nullable=False, comment="操作者 ID")
    action = Column(String(100), nullable=False, comment="操作类型")
    resource = Column(String(200), nullable=True, comment="资源 ID")
    request = Column(Text, nullable=True, comment="JSON 请求内容")
    response = Column(Text, nullable=True, comment="JSON 响应内容")
    status = Column(String(20), nullable=False, comment="操作状态：success/failure")
    trace_id = Column(String(100), nullable=True, comment="追踪 ID")

    def __repr__(self):
        return f"<AuditLog {self.id} {self.actor} {self.action}>"


# 索引定义（用于 Alembic 迁移脚本参考）
INDEX_DEFINITIONS = """
-- 审计日志表索引
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource);
CREATE INDEX IF NOT EXISTS idx_audit_logs_trace_id ON audit_logs(trace_id);

-- 复合索引用于常见查询
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_timestamp ON audit_logs(actor, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_timestamp ON audit_logs(action, timestamp DESC);
"""


def create_audit_logs_table(engine):
    """创建审计日志表"""
    Base.metadata.create_all(bind=engine)


def drop_audit_logs_table(engine):
    """删除审计日志表"""
    Base.metadata.drop_all(bind=engine)
