"""
团队权限系统 - 数据模型。

支持企业客户的组织架构、角色权限管理。
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class OrganizationDB(Base):
    """组织表 - 企业客户主体。"""
    __tablename__ = "organizations"

    org_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_name: Mapped[str] = mapped_column(String(200))  # 组织名称
    org_type: Mapped[str] = mapped_column(String(50), default="enterprise")  # enterprise/team/individual

    # 组织信息
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 所属行业
    company_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 公司规模

    # 联系方式
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/suspended/deleted
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已验证

    # 配额限制
    max_members: Mapped[int] = mapped_column(Integer, default=10)  # 最大成员数
    max_tasks_per_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 月度任务限额

    # 审计
    created_by: Mapped[str] = mapped_column(String(255))  # 创建者用户 ID
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class TeamMemberDB(Base):
    """团队成员表 - 组织与用户的关联。"""
    __tablename__ = "team_members"

    member_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 关联
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.org_id"), index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)  # 用户 ID（对接统一账号系统）

    # 角色信息
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.role_id"))

    # 成员状态
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/pending/removed
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    invited_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 邀请人用户 ID
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 审计
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    # 唯一约束：同一用户在同一组织只能有一个成员记录
    __table_args__ = (
        UniqueConstraint('org_id', 'user_id', name='uq_org_user'),
    )


class RoleDB(Base):
    """角色表 - 预定义和自定义角色。"""
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 角色信息
    role_name: Mapped[str] = mapped_column(String(100))  # 角色名称
    role_name_zh: Mapped[str] = mapped_column(String(100))  # 角色中文名称

    # 角色类型
    role_type: Mapped[str] = mapped_column(String(50), default="custom")  # system/custom
    org_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.org_id"), index=True, nullable=True)
    # 系统角色 org_id 为 NULL，自定义角色关联到具体组织

    # 角色描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 权限列表（JSON 存储）
    permissions: Mapped[str] = mapped_column(JSON, default="[]")

    # 状态
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deletable: Mapped[bool] = mapped_column(Boolean, default=True)  # 系统角色不可删除

    # 审计
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class PermissionDB(Base):
    """权限定义表 - 系统权限元数据。"""
    __tablename__ = "permissions"

    permission_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    permission_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # 权限标识
    permission_name: Mapped[str] = mapped_column(String(200))  # 权限名称
    permission_name_zh: Mapped[str] = mapped_column(String(200))  # 权限中文名称

    # 权限分类
    category: Mapped[str] = mapped_column(String(50), index=True)  # task/worker/financial/settings/admin

    # 权限描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 权限级别
    level: Mapped[str] = mapped_column(String(20), default="read")  # read/write/admin

    # 审计
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class TeamInvitationDB(Base):
    """团队邀请表 - 成员邀请记录。"""
    __tablename__ = "team_invitations"

    invitation_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 邀请信息
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.org_id"), index=True)
    invitee_email: Mapped[str] = mapped_column(String(255), index=True)  # 被邀请人邮箱
    invitee_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 被邀请人姓名

    # 角色
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.role_id"))

    # 邀请状态
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/accepted/declined/expired

    # 时间
    invited_by: Mapped[str] = mapped_column(String(255))  # 邀请人用户 ID
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # 过期时间
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 审计
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class OrganizationAuditLogDB(Base):
    """组织审计日志表 - 记录组织内的重要操作。"""
    __tablename__ = "organization_audit_logs"

    log_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 关联
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.org_id"), index=True)

    # 操作信息
    action: Mapped[str] = mapped_column(String(100), index=True)  # 操作类型
    resource_type: Mapped[str] = mapped_column(String(50))  # 资源类型
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 资源 ID

    # 操作者
    actor_user_id: Mapped[str] = mapped_column(String(255), index=True)  # 操作用户 ID
    actor_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 操作者角色

    # 操作详情
    action_details: Mapped[Dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)


# ==================== 预定义系统角色 ====================

SYSTEM_ROLES = {
    "org_admin": {
        "role_name": "org_admin",
        "role_name_zh": "组织管理员",
        "description": "拥有组织内的全部权限",
        "permissions": [
            "task:create", "task:read", "task:update", "task:delete", "task:approve",
            "worker:read", "worker:manage",
            "financial:read", "financial:manage",
            "team:read", "team:manage",
            "settings:read", "settings:manage",
            "report:read", "report:export",
        ],
    },
    "project_manager": {
        "role_name": "project_manager",
        "role_name_zh": "项目经理",
        "description": "负责任务创建和管理",
        "permissions": [
            "task:create", "task:read", "task:update", "task:approve",
            "worker:read",
            "financial:read",
            "team:read",
            "report:read", "report:export",
        ],
    },
    "reviewer": {
        "role_name": "reviewer",
        "role_name_zh": "审核员",
        "description": "负责任务交付的验收审核",
        "permissions": [
            "task:read", "task:approve", "task:reject",
            "worker:read",
            "report:read",
        ],
    },
    "finance": {
        "role_name": "finance",
        "role_name_zh": "财务",
        "description": "负责财务报表和钱包管理",
        "permissions": [
            "financial:read", "financial:manage",
            "task:read",
            "report:read", "report:export",
        ],
    },
    "member": {
        "role_name": "member",
        "role_name_zh": "普通成员",
        "description": "查看任务和提交反馈",
        "permissions": [
            "task:read",
            "worker:read",
            "report:read",
        ],
    },
}
