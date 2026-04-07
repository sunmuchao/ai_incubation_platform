"""
P6 阶段实体模型：AI 信誉体系与行为追溯链
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ==================== AI 信誉体系 ====================

class AgentType(str, Enum):
    """AI Agent 类型"""
    MODERATOR = "moderator"  # AI 版主
    ASSISTANT = "assistant"  # AI 助手
    RECOMMENDER = "recommender"  # AI 推荐
    CREATOR = "creator"  # AI 创作


class AgentReputation(BaseModel):
    """AI Agent 信誉记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str  # Agent 标识
    agent_name: str  # Agent 名称
    agent_type: AgentType  # Agent 类型
    model_provider: Optional[str] = None  # 模型提供方
    model_name: Optional[str] = None  # 模型名称
    operator_id: Optional[str] = None  # 运营者 ID

    # 信誉评分
    reputation_score: float = Field(default=0.5, ge=0, le=1)  # 信誉分数 (0-1)
    total_actions: int = 0  # 总行为数
    positive_actions: int = 0  # 正面行为数
    negative_actions: int = 0  # 负面行为数

    # 细分评分
    accuracy_score: float = Field(default=0.5, ge=0, le=1)  # 准确性评分
    fairness_score: float = Field(default=0.5, ge=0, le=1)  # 公平性评分
    transparency_score: float = Field(default=0.5, ge=0, le=1)  # 透明性评分
    response_time_score: float = Field(default=0.5, ge=0, le=1)  # 响应速度评分

    # 统计
    avg_response_time_ms: float = 0  # 平均响应时间 (毫秒)
    user_feedback_count: int = 0  # 用户反馈数
    user_feedback_positive: int = 0  # 正面反馈数

    # 状态
    is_active: bool = True
    last_action_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class AgentReputationSummary(BaseModel):
    """AI Agent 信誉摘要"""
    agent_id: str
    agent_name: str
    agent_type: AgentType
    reputation_score: float
    reputation_level: str  # excellent, good, fair, poor
    total_actions: int
    positive_rate: float
    accuracy_score: float
    fairness_score: float
    transparency_score: float


class AgentRanking(BaseModel):
    """AI Agent 排行榜"""
    rank: int
    agent_id: str
    agent_name: str
    agent_type: AgentType
    reputation_score: float
    total_actions: int
    accuracy_score: float


# ==================== 行为追溯链 ====================

class BehaviorTraceStatus(str, Enum):
    """行为追溯状态"""
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    IN_PROGRESS = "in_progress"


class BehaviorTrace(BaseModel):
    """AI 行为追溯记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str  # 追溯链 ID
    parent_trace_id: Optional[str] = None  # 父追溯 ID

    # AI 标识
    agent_id: str  # Agent 标识
    agent_name: str  # Agent 名称
    model_provider: Optional[str] = None  # 模型提供方
    model_name: Optional[str] = None  # 模型名称
    model_version: Optional[str] = None  # 模型版本
    operator_id: Optional[str] = None  # 运营者 ID

    # 行为信息
    action_type: str  # 行为类型
    action_description: Optional[str] = None  # 行为描述
    resource_type: Optional[str] = None  # 资源类型
    resource_id: Optional[str] = None  # 资源 ID

    # 决策过程
    input_data: Dict[str, Any] = Field(default_factory=dict)  # 输入数据
    decision_process: Dict[str, Any] = Field(default_factory=dict)  # 决策过程详情
    output_result: Dict[str, Any] = Field(default_factory=dict)  # 输出结果

    # 决策依据
    rules_applied: List[str] = Field(default_factory=list)  # 应用的规则列表
    confidence_score: Optional[float] = None  # 置信度分数 (0-1)
    risk_assessment: Optional[Dict[str, Any]] = None  # 风险评估结果

    # 时间与性能
    started_at: datetime  # 开始时间
    completed_at: Optional[datetime] = None  # 完成时间
    duration_ms: Optional[float] = None  # 耗时 (毫秒)

    # 状态与反馈
    status: BehaviorTraceStatus = BehaviorTraceStatus.COMPLETED
    error_message: Optional[str] = None
    user_feedback: Optional[Dict[str, Any]] = None  # 用户反馈
    review_result: Optional[Dict[str, Any]] = None  # 复核结果

    # 审计
    ip_address: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TraceChain(BaseModel):
    """追溯链（多个关联的追溯记录）"""
    chain_id: str
    root_trace: BehaviorTrace
    child_traces: List[BehaviorTrace] = Field(default_factory=list)
    total_duration_ms: float = 0
    decision_path: List[str] = Field(default_factory=list)


# ==================== 治理报告 ====================

class GovernanceReportType(str, Enum):
    """治理报告类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SPECIAL = "special"


class GovernanceReportStatus(str, Enum):
    """治理报告状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class GovernanceReportVisibility(str, Enum):
    """治理报告可见性"""
    ADMIN = "admin"
    MODERATOR = "moderator"
    PUBLIC = "public"


class GovernanceReportMetrics(BaseModel):
    """治理报告指标"""
    total_posts: int = 0
    total_comments: int = 0
    total_reports: int = 0
    auto_processed: int = 0
    manual_reviewed: int = 0
    violation_rate: float = 0
    auto_resolution_rate: float = 0
    avg_response_time: float = 0
    user_satisfaction: float = 0


class GovernanceReport(BaseModel):
    """治理报告"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    report_type: GovernanceReportType
    report_title: str

    # 时间范围
    start_time: datetime
    end_time: datetime
    generated_at: datetime = Field(default_factory=datetime.now)

    # 生成者
    generated_by: str
    agent_id: Optional[str] = None

    # 报告内容
    summary: Optional[str] = None
    content: Dict[str, Any] = Field(default_factory=dict)
    metrics: GovernanceReportMetrics = Field(default_factory=GovernanceReportMetrics)

    # 状态
    status: GovernanceReportStatus = GovernanceReportStatus.DRAFT
    visibility: GovernanceReportVisibility = GovernanceReportVisibility.ADMIN


# ==================== 请求/响应模型 ====================

class AgentReputationCreate(BaseModel):
    """创建 AI Agent 信誉记录请求"""
    agent_id: str
    agent_name: str
    agent_type: AgentType
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    operator_id: Optional[str] = None


class AgentReputationUpdate(BaseModel):
    """更新 AI Agent 信誉记录请求"""
    reputation_score: Optional[float] = Field(None, ge=0, le=1)
    accuracy_score: Optional[float] = Field(None, ge=0, le=1)
    fairness_score: Optional[float] = Field(None, ge=0, le=1)
    transparency_score: Optional[float] = Field(None, ge=0, le=1)
    response_time_score: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None


class BehaviorTraceCreate(BaseModel):
    """创建行为追溯记录请求"""
    agent_id: str
    agent_name: str
    action_type: str
    action_description: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_result: Dict[str, Any] = Field(default_factory=dict)
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    operator_id: Optional[str] = None


class BehaviorTraceFeedback(BaseModel):
    """行为追溯反馈请求"""
    trace_id: str
    rating: int = Field(..., ge=1, le=5, description="评分：1-5 分")
    comment: Optional[str] = None
    is_helpful: Optional[bool] = None


class GovernanceReportCreate(BaseModel):
    """创建治理报告请求"""
    report_type: GovernanceReportType
    report_title: str
    start_time: datetime
    end_time: datetime
    agent_id: Optional[str] = None
    summary: Optional[str] = None


class GovernanceReportPublish(BaseModel):
    """发布治理报告请求"""
    visibility: GovernanceReportVisibility = GovernanceReportVisibility.MODERATOR


# ==================== 查询参数模型 ====================

class AgentReputationQuery(BaseModel):
    """AI Agent 信誉查询参数"""
    agent_type: Optional[AgentType] = None
    min_reputation_score: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class BehaviorTraceQuery(BaseModel):
    """行为追溯查询参数"""
    agent_id: Optional[str] = None
    action_type: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    status: Optional[BehaviorTraceStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class GovernanceReportQuery(BaseModel):
    """治理报告查询参数"""
    report_type: Optional[GovernanceReportType] = None
    status: Optional[GovernanceReportStatus] = None
    visibility: Optional[GovernanceReportVisibility] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
