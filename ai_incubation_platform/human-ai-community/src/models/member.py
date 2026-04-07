"""
社区成员模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum


class MemberType(str, Enum):
    HUMAN = "human"
    AI = "ai"


class MemberRole(str, Enum):
    MEMBER = "member"
    MODERATOR = "moderator"
    ADMIN = "admin"


class CommunityMember(BaseModel):
    """社区成员模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: Optional[str] = None
    member_type: MemberType = MemberType.HUMAN
    role: MemberRole = MemberRole.MEMBER

    # AI 成员特有
    ai_model: Optional[str] = None
    ai_persona: Optional[str] = None

    # 统计
    post_count: int = 0
    join_date: datetime = Field(default_factory=datetime.now)

    # 用户等级系统
    experience_points: int = 0
    level: int = 1
    last_checkin_date: Optional[datetime] = None


class Post(BaseModel):
    """帖子模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    author_id: str
    author_type: MemberType = MemberType.HUMAN
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MemberCreate(BaseModel):
    """创建成员请求"""
    name: str
    email: Optional[str] = None
    member_type: MemberType = MemberType.HUMAN
    ai_model: Optional[str] = None
    ai_persona: Optional[str] = None


class PostCreate(BaseModel):
    """创建帖子请求"""
    author_id: str
    author_type: MemberType = MemberType.HUMAN
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)


class Comment(BaseModel):
    """评论模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    post_id: str
    author_id: str
    author_type: MemberType = MemberType.HUMAN
    content: str
    parent_id: Optional[str] = None  # 回复的评论ID，顶层评论为None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CommentCreate(BaseModel):
    """创建评论请求"""
    post_id: str
    author_id: str
    author_type: MemberType = MemberType.HUMAN
    content: str
    parent_id: Optional[str] = None


class ContentType(str, Enum):
    """内容类型"""
    POST = "post"
    COMMENT = "comment"


class ReviewStatus(str, Enum):
    """审核状态"""
    PENDING = "pending"      # 待审核
    APPROVED = "approved"    # 已通过
    REJECTED = "rejected"    # 已拒绝
    FLAGGED = "flagged"      # 已标记需人工审核


class ReviewResult(BaseModel):
    """审核结果"""
    status: ReviewStatus
    reason: Optional[str] = None
    reviewer: Optional[str] = None  # 审核者ID，AI审核为模型名，人工审核为用户ID
    review_time: datetime = Field(default_factory=datetime.now)
    risk_score: float = 0.0  # 风险分数，0-1，越高越危险


class ContentReview(BaseModel):
    """内容审核记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_id: str  # 内容ID（帖子ID或评论ID）
    content_type: ContentType
    content: str  # 待审核内容
    author_id: str
    author_type: MemberType
    status: ReviewStatus = ReviewStatus.PENDING
    submit_time: datetime = Field(default_factory=datetime.now)
    review_result: Optional[ReviewResult] = None


class ReviewRule(BaseModel):
    """审核规则"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    rule_type: str  # 规则类型：keyword, ai, regex, custom
    config: Dict[str, Any] = Field(default_factory=dict)  # 规则配置
    enabled: bool = True
    risk_score: float = 0.5  # 触发时的风险分数
    action: str = "flag"  # 触发后的动作：flag, reject, warn
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AgentCallRecord(BaseModel):
    """AI Agent调用记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str  # Agent名称/标识
    action: str  # 动作：post, reply, review
    content_id: Optional[str] = None  # 关联的内容ID
    input_params: Dict[str, Any] = Field(default_factory=dict)  # 调用参数
    output_result: Dict[str, Any] = Field(default_factory=dict)  # 返回结果
    status: str = "success"  # 调用状态：success, failed, timeout
    error_message: Optional[str] = None
    call_time: datetime = Field(default_factory=datetime.now)
    response_time: float = 0.0  # 响应时间（毫秒）


class RateLimitConfig(BaseModel):
    """速率限制配置"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resource: str  # 受限资源：post, comment, login等
    limit: int  # 限制次数
    window_seconds: int  # 时间窗口（秒）
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class ReportType(str, Enum):
    """举报类型"""
    SPAM = "spam"  # 垃圾广告
    VIOLENCE = "violence"  # 暴力内容
    PORNOGRAPHY = "pornography"  # 色情内容
    HATE_SPEECH = "hate_speech"  # 仇恨言论
    COPYRIGHT = "copyright"  # 版权侵权
    ADVERTISEMENT = "advertisement"  # 垃圾广告
    OTHER = "other"  # 其他


class ReportStatus(str, Enum):
    """举报处理状态"""
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    RESOLVED = "resolved"  # 已处理
    DISMISS = "dismiss"  # 已驳回 (兼容旧代码)
    DISMISSED = "dismissed"  # 已驳回


class Report(BaseModel):
    """举报记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reporter_id: str  # 举报人ID
    reported_content_id: str  # 被举报内容ID
    reported_content_type: ContentType  # 被举报内容类型
    report_type: ReportType
    description: Optional[str] = None
    evidence: Optional[List[str]] = None  # 证据图片/链接
    status: ReportStatus = ReportStatus.PENDING
    handler_id: Optional[str] = None  # 处理人ID
    handler_note: Optional[str] = None  # 处理备注
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class BanReason(str, Enum):
    """封禁原因"""
    SPAM = "spam"  # 垃圾广告
    VIOLENCE = "violence"  # 暴力内容
    PORNOGRAPHY = "pornography"  # 色情内容
    HATE_SPEECH = "hate_speech"  # 仇恨言论
    HARASSMENT = "harassment"  # 骚扰行为
    COPYRIGHT = "copyright"  # 版权侵权
    FRAUD = "fraud"  # 欺诈行为
    TERMS_VIOLATION = "terms_violation"  # 违反条款
    OTHER = "other"  # 其他


class BanStatus(str, Enum):
    """封禁状态"""
    ACTIVE = "active"  # 生效中
    EXPIRED = "expired"  # 已过期
    LIFTED = "lifted"  # 已解除


class BanRecord(BaseModel):
    """封禁记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # 被封禁用户ID
    reason: str  # 封禁原因
    ban_type: str  # 封禁类型：post, comment, login, all
    duration_hours: Optional[int] = None  # 封禁时长（小时），None表示永久
    status: BanStatus = BanStatus.ACTIVE
    operator_id: str  # 操作人ID
    expire_time: Optional[datetime] = None  # 过期时间
    created_at: datetime = Field(default_factory=datetime.now)
    lifted_at: Optional[datetime] = None  # 解封时间
    lift_reason: Optional[str] = None  # 解封原因


class OperationType(str, Enum):
    """操作类型"""
    CREATE_POST = "create_post"
    UPDATE_POST = "update_post"
    DELETE_POST = "delete_post"
    CREATE_COMMENT = "create_comment"
    UPDATE_COMMENT = "update_comment"
    DELETE_COMMENT = "delete_comment"
    CREATE_MEMBER = "create_member"
    UPDATE_MEMBER = "update_member"
    DELETE_MEMBER = "delete_member"
    BAN_USER = "ban_user"
    LIFT_BAN = "lift_ban"
    PROCESS_REPORT = "process_report"
    UPDATE_REVIEW_RULE = "update_review_rule"
    LOGIN = "login"
    LOGOUT = "logout"


class AuditLog(BaseModel):
    """审计日志"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operator_id: str  # 操作者ID
    operator_type: MemberType  # 操作者类型
    operation_type: OperationType
    resource_type: Optional[str] = None  # 资源类型
    resource_id: Optional[str] = None  # 资源ID
    before: Optional[Dict[str, Any]] = None  # 操作前状态
    after: Optional[Dict[str, Any]] = None  # 操作后状态
    ip_address: Optional[str] = None  # IP地址
    user_agent: Optional[str] = None  # 客户端信息
    status: str = "success"  # 操作状态：success, failed
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class UnifiedUserInfo(BaseModel):
    """统一账号体系用户信息"""
    user_id: str
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    is_verified: bool = False
    created_at: datetime
    last_login_at: Optional[datetime] = None
