"""
P13 培训效果评估增强 - 数据模型层

v13 新增功能:
- 培训前后技能对比 (Pre/Post Assessment)
- 培训 ROI 计算 (Return on Investment)
- 学习路径推荐 (Learning Path Recommendation)
- 培训效果追踪 (Training Impact Tracking)
- 技能认证深度集成 (Certification Integration)
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import uuid


# ==================== 枚举定义 ====================

class AssessmentType(str, Enum):
    """评估类型"""
    PRE_ASSESSMENT = "pre_assessment"  # 培训前测
    POST_ASSESSMENT = "post_assessment"  # 培训后测
    FOLLOW_UP_ASSESSMENT = "follow_up_assessment"  # 跟踪评估


class SkillLevel(str, Enum):
    """技能等级"""
    BEGINNER = "beginner"  # 初学者 (0-25%)
    INTERMEDIATE = "intermediate"  # 中级 (26-50%)
    ADVANCED = "advanced"  # 高级 (51-75%)
    EXPERT = "expert"  # 专家 (76-100%)


class LearningPathStatus(str, Enum):
    """学习路径状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class PathRecommendationReason(str, Enum):
    """路径推荐理由"""
    SKILL_GAP = "skill_gap"  # 技能差距
    CAREER_GOAL = "career_goal"  # 职业目标
    TRENDING_SKILL = "trending_skill"  # 热门技能
    PREREQUISITE = "prerequisite"  # 前置要求
    PERSONALIZED = "personalized"  # 个性化推荐


class ROIStatus(str, Enum):
    """ROI 状态"""
    POSITIVE = "positive"  # 正 ROI
    NEGATIVE = "negative"  # 负 ROI
    BREAK_EVEN = "break_even"  # 收支平衡
    PENDING = "pending"  # 待评估


# ==================== 数据模型 ====================

class SkillAssessment(BaseModel):
    """
    技能评估记录

    用于培训前后的技能水平评估
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    user_id: str
    tenant_id: str

    # 评估类型
    assessment_type: AssessmentType

    # 关联的培训/认证
    training_id: Optional[str] = None
    certification_id: Optional[str] = None

    # 技能评估结果
    skill_scores: Dict[str, float] = Field(default_factory=dict)  # {skill_name: score 0-100}
    skill_levels: Dict[str, SkillLevel] = Field(default_factory=dict)  # {skill_name: level}

    # 综合评分
    overall_score: float = 0.0
    overall_level: SkillLevel = SkillLevel.BEGINNER

    # 评估详情
    assessment_data: Dict[str, Any] = Field(default_factory=dict)  # 原始评估数据
    comments: Optional[str] = None

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrainingROI(BaseModel):
    """
    培训投资回报率 (ROI) 计算模型

    ROI = (收益 - 成本) / 成本 * 100%
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    tenant_id: str

    # 关联的培训
    training_id: Optional[str] = None
    certification_id: Optional[str] = None

    # 成本计算
    training_cost: float = 0.0  # 培训费用
    time_cost_hours: float = 0.0  # 投入时间 (小时)
    opportunity_cost: float = 0.0  # 机会成本
    total_cost: float = 0.0  # 总成本

    # 收益计算
    productivity_gain: float = 0.0  # 生产力提升收益
    quality_improvement: float = 0.0  # 质量提升收益
    time_savings: float = 0.0  # 时间节省收益
    error_reduction: float = 0.0  # 错误减少收益
    total_benefit: float = 0.0  # 总收益

    # ROI 计算结果
    roi_percentage: float = 0.0  # ROI 百分比
    roi_status: ROIStatus = ROIStatus.PENDING
    payback_period_days: int = 0  # 回收周期 (天)

    # 计算周期
    calculation_period_days: int = 30  # 计算周期 (天)

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    calculated_at: datetime = Field(default_factory=datetime.now)

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LearningPathItem(BaseModel):
    """
    学习路径中的单个项目
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 学习内容
    content_type: str  # certification, training, course, practice, project
    content_id: str
    content_name: str
    content_description: Optional[str] = None

    # 学习顺序
    sequence_order: int = 0
    is_prerequisite: bool = False  # 是否为前置必修

    # 预计时间
    estimated_hours: float = 0.0

    # 完成情况
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    score: Optional[float] = None

    # 关联技能
    target_skills: List[str] = Field(default_factory=list)

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LearningPath(BaseModel):
    """
    个性化学习路径

    基于用户当前技能水平和目标技能的差距，推荐学习路径
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    user_id: str
    tenant_id: str

    # 路径目标
    goal_name: str  # 目标名称，如"成为高级 Python 开发者"
    goal_description: Optional[str] = None

    # 技能差距分析
    current_skills: Dict[str, float] = Field(default_factory=dict)  # 当前技能 {skill: score}
    target_skills: Dict[str, float] = Field(default_factory=dict)  # 目标技能 {skill: score}
    skill_gaps: Dict[str, float] = Field(default_factory=dict)  # 技能差距 {skill: gap}

    # 路径项目
    path_items: List[LearningPathItem] = Field(default_factory=list)

    # 总体进度
    status: LearningPathStatus = LearningPathStatus.NOT_STARTED
    overall_progress: float = 0.0  # 总体进度百分比
    estimated_total_hours: float = 0.0
    actual_hours_spent: float = 0.0

    # 推荐理由
    recommendation_reason: PathRecommendationReason = PathRecommendationReason.SKILL_GAP
    recommendation_score: float = 0.0  # 推荐分数 0-100

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    estimated_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrainingImpactTracker(BaseModel):
    """
    培训效果追踪器

    长期追踪培训对员工表现的影响
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    tenant_id: str

    # 关联的培训
    training_id: Optional[str] = None
    certification_id: Optional[str] = None
    training_name: str

    # 培训前后对比
    pre_training_score: float = 0.0  # 培训前评分
    post_training_score: float = 0.0  # 培训后评分
    improvement_percentage: float = 0.0  # 提升百分比

    # 持续追踪数据
    follow_up_scores: List[Dict[str, Any]] = Field(default_factory=list)
    # [{date, score, metrics}, ...]

    # 关键指标变化
    metrics_improvement: Dict[str, float] = Field(default_factory=dict)
    # {metric_name: improvement_percentage}

    # 技能保持情况
    skill_retention_rate: float = 0.0  # 技能保持率
    skill_decay_rate: float = 0.0  # 技能衰减率

    # 培训效果分类
    impact_level: str = "pending"  # high, medium, low, pending

    # 时间戳
    training_completed_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    last_tracked_at: datetime = Field(default_factory=datetime.now)
    tracking_end_date: Optional[datetime] = None

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CertificationIntegration(BaseModel):
    """
    认证集成记录

    连接 P5 认证系统与培训效果评估
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    user_id: str
    tenant_id: str

    # 认证信息
    certification_id: str
    certification_name: str
    certification_level: str  # basic, intermediate, advanced, expert

    # 考试成绩
    exam_score: float = 0.0
    exam_passed: bool = False
    exam_attempts: int = 0

    # 技能映射
    mapped_skills: Dict[str, float] = Field(default_factory=dict)
    # {skill_name: confidence_score}

    # 证书信息
    certificate_id: Optional[str] = None
    certificate_issued_at: Optional[datetime] = None
    certificate_expires_at: Optional[datetime] = None

    # 培训关联
    related_training_ids: List[str] = Field(default_factory=list)
    prerequisite_certifications: List[str] = Field(default_factory=list)

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    passed_at: Optional[datetime] = None

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrainingEffectivenessReport(BaseModel):
    """
    培训效果综合报告

    整合所有评估数据的综合报告
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    tenant_id: str

    # 报告周期
    report_period: str  # last_30_days, last_90_days, all_time

    # 培训概览
    total_trainings: int = 0
    completed_trainings: int = 0
    in_progress_trainings: int = 0

    # 技能提升概览
    skills_improved: List[str] = Field(default_factory=list)
    average_improvement: float = 0.0
    max_improvement: float = 0.0

    # ROI 概览
    total_training_cost: float = 0.0
    total_benefit: float = 0.0
    average_roi: float = 0.0

    # 认证概览
    total_certifications: int = 0
    passed_certifications: int = 0
    certification_rate: float = 0.0

    # 学习路径概览
    active_learning_paths: int = 0
    completed_learning_paths: int = 0
    learning_path_completion_rate: float = 0.0

    # 详细数据
    training_details: List[Dict[str, Any]] = Field(default_factory=list)
    roi_details: List[Dict[str, Any]] = Field(default_factory=list)
    certification_details: List[Dict[str, Any]] = Field(default_factory=list)

    # 洞察和建议
    insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # 时间戳
    generated_at: datetime = Field(default_factory=datetime.now)

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== 请求/响应模型 ====================

class CreateAssessmentRequest(BaseModel):
    """创建技能评估请求"""
    employee_id: str
    user_id: str
    tenant_id: str
    assessment_type: AssessmentType
    training_id: Optional[str] = None
    certification_id: Optional[str] = None
    skill_scores: Dict[str, float] = Field(default_factory=dict)
    comments: Optional[str] = None


class AssessmentComparisonResponse(BaseModel):
    """评估对比响应"""
    employee_id: str
    pre_assessment: Optional[Dict[str, Any]] = None
    post_assessment: Optional[Dict[str, Any]] = None
    skill_improvements: Dict[str, float] = Field(default_factory=dict)
    overall_improvement: float = 0.0
    improvement_level: str = "none"


class CalculateROIRequest(BaseModel):
    """计算 ROI 请求"""
    employee_id: str
    training_id: Optional[str] = None
    certification_id: Optional[str] = None
    training_cost: float = 0.0
    time_cost_hours: float = 0.0
    hourly_rate: float = 0.0
    period_days: int = 30


class ROIResponse(BaseModel):
    """ROI 响应"""
    employee_id: str
    training_id: Optional[str]
    roi_percentage: float
    roi_status: str
    total_cost: float
    total_benefit: float
    payback_period_days: int
    breakdown: Dict[str, Any]


class CreateLearningPathRequest(BaseModel):
    """创建学习路径请求"""
    employee_id: str
    user_id: str
    tenant_id: str
    goal_name: str
    goal_description: Optional[str] = None
    target_skills: Dict[str, float] = Field(default_factory=dict)
    recommendation_reason: PathRecommendationReason = PathRecommendationReason.SKILL_GAP


class LearningPathResponse(BaseModel):
    """学习路径响应"""
    path_id: str
    employee_id: str
    goal_name: str
    status: str
    overall_progress: float
    total_items: int
    completed_items: int
    estimated_hours: float
    path_items: List[Dict[str, Any]]
    recommendations: List[str]


class ImpactTrackerResponse(BaseModel):
    """效果追踪响应"""
    tracker_id: str
    employee_id: str
    training_name: str
    pre_score: float
    post_score: float
    improvement: float
    impact_level: str
    skill_retention_rate: float
    follow_up_count: int
    last_tracked_at: str


# ==================== 内存存储模型 (用于开发测试) ====================

class P13Storage:
    """P13 数据存储服务（内存版，用于开发和测试）"""

    def __init__(self):
        self.assessments: Dict[str, SkillAssessment] = {}
        self.training_rois: Dict[str, TrainingROI] = {}
        self.learning_paths: Dict[str, LearningPath] = {}
        self.impact_trackers: Dict[str, TrainingImpactTracker] = {}
        self.certification_integrations: Dict[str, CertificationIntegration] = {}
        self.reports: Dict[str, TrainingEffectivenessReport] = {}

    def save_assessment(self, assessment: SkillAssessment):
        self.assessments[assessment.id] = assessment

    def get_assessment(self, assessment_id: str) -> Optional[SkillAssessment]:
        return self.assessments.get(assessment_id)

    def save_roi(self, roi: TrainingROI):
        self.training_rois[roi.id] = roi

    def get_roi(self, roi_id: str) -> Optional[TrainingROI]:
        return self.training_rois.get(roi_id)

    def save_learning_path(self, path: LearningPath):
        self.learning_paths[path.id] = path

    def get_learning_path(self, path_id: str) -> Optional[LearningPath]:
        return self.learning_paths.get(path_id)

    def save_impact_tracker(self, tracker: TrainingImpactTracker):
        self.impact_trackers[tracker.id] = tracker

    def get_impact_tracker(self, tracker_id: str) -> Optional[TrainingImpactTracker]:
        return self.impact_trackers.get(tracker_id)

    def save_certification_integration(self, cert: CertificationIntegration):
        self.certification_integrations[cert.id] = cert

    def get_certification_integration(self, cert_id: str) -> Optional[CertificationIntegration]:
        return self.certification_integrations.get(cert_id)

    def save_report(self, report: TrainingEffectivenessReport):
        self.reports[report.id] = report

    def get_report(self, report_id: str) -> Optional[TrainingEffectivenessReport]:
        return self.reports.get(report_id)


# 全局存储实例
p13_storage = P13Storage()
