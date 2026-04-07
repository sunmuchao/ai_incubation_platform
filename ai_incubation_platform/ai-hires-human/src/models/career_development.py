"""
职业发展支持数据模型。

v1.20.0 新增：职业发展支持功能
- 职业规划（长期目标/里程碑）
- 技能提升（学习资源/培训推荐）
- 就业指导（简历优化/面试辅导）
- 创业支持（商业计划/融资建议）
- 人脉拓展（引荐/内推）
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ========== 职业规划相关模型 ==========

class GoalStatus(str, Enum):
    """目标状态。"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 进行中
    COMPLETED = "completed"  # 已完成
    ABANDONED = "abandoned"  # 已放弃


class GoalType(str, Enum):
    """目标类型。"""
    SHORT_TERM = "short_term"  # 短期（1-3 个月）
    MID_TERM = "mid_term"  # 中期（3-12 个月）
    LONG_TERM = "long_term"  # 长期（1-3 年）


class CareerGoal(BaseModel):
    """职业目标。"""
    goal_id: str
    worker_id: str
    title: str
    description: str
    goal_type: GoalType
    status: GoalStatus = GoalStatus.DRAFT
    target_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 里程碑
    milestones: List[CareerMilestone] = Field(default_factory=list)

    # 关联技能
    related_skills: List[str] = Field(default_factory=list)

    # 进度（0-100）
    progress: float = 0.0

    # 备注
    notes: str = ""


class CareerMilestone(BaseModel):
    """职业里程碑。"""
    milestone_id: str
    goal_id: str
    title: str
    description: str
    status: GoalStatus = GoalStatus.DRAFT
    target_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # 验收标准
    success_criteria: List[str] = Field(default_factory=list)


class CareerGoalCreate(BaseModel):
    """创建职业目标。"""
    worker_id: str
    title: str
    description: str
    goal_type: GoalType
    target_date: Optional[datetime] = None
    related_skills: List[str] = Field(default_factory=list)
    milestones: List[Dict] = Field(default_factory=list)


class CareerGoalUpdate(BaseModel):
    """更新职业目标。"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[GoalStatus] = None
    target_date: Optional[datetime] = None
    progress: Optional[float] = None
    notes: Optional[str] = None


# ========== 技能提升相关模型 ==========

class SkillLevel(str, Enum):
    """技能等级。"""
    BEGINNER = "beginner"  # 入门
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"  # 高级
    EXPERT = "expert"  # 专家


class LearningResourceType(str, Enum):
    """学习资源类型。"""
    COURSE = "course"  # 在线课程
    TUTORIAL = "tutorial"  # 教程
    BOOK = "book"  # 书籍
    VIDEO = "video"  # 视频
    PRACTICE = "practice"  # 实践项目
    CERTIFICATION = "certification"  # 认证考试


class LearningResource(BaseModel):
    """学习资源。"""
    resource_id: str
    title: str
    description: str
    resource_type: LearningResourceType
    skill_name: str  # 关联的技能
    provider: str  # 提供方（如 Coursera、Udemy 等）
    url: Optional[str] = None
    duration_hours: Optional[float] = None  # 预计学习时长（小时）
    difficulty: SkillLevel = SkillLevel.BEGINNER
    rating: float = 0.0  # 评分（0-5）
    is_free: bool = False
    prerequisites: List[str] = Field(default_factory=list)  # 前置要求
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SkillAssessment(BaseModel):
    """技能评估。"""
    assessment_id: str
    worker_id: str
    skill_name: str
    current_level: SkillLevel
    target_level: SkillLevel
    assessment_date: Optional[datetime] = None

    # 评估详情
    strengths: List[str] = Field(default_factory=list)  # 优势
    weaknesses: List[str] = Field(default_factory=list)  # 需要改进的地方

    # 推荐学习路径
    recommended_resources: List[str] = Field(default_factory=list)  # 资源 ID 列表

    # 评估得分（0-100）
    score: float = 0.0


class LearningProgress(BaseModel):
    """学习进度。"""
    progress_id: str
    worker_id: str
    resource_id: str
    status: GoalStatus = GoalStatus.ACTIVE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0  # 0-100
    notes: str = ""


class SkillImprovementPlan(BaseModel):
    """技能提升计划。"""
    plan_id: str
    worker_id: str
    skill_name: str
    current_level: SkillLevel
    target_level: SkillLevel
    target_date: Optional[datetime] = None
    status: GoalStatus = GoalStatus.DRAFT

    # 学习资源列表
    resource_ids: List[str] = Field(default_factory=list)

    # 每周学习计划
    weekly_hours: int = 5

    # 进度
    progress: float = 0.0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 就业指导相关模型 ==========

class ResumeSection(str, Enum):
    """简历部分。"""
    SUMMARY = "summary"  # 个人总结
    EXPERIENCE = "experience"  # 工作经历
    EDUCATION = "education"  # 教育背景
    SKILLS = "skills"  # 技能
    PROJECTS = "projects"  # 项目经验
    CERTIFICATIONS = "certifications"  # 认证


class ResumeFeedback(BaseModel):
    """简历反馈。"""
    feedback_id: str
    worker_id: str
    resume_content: str  # 简历内容
    overall_score: float  # 总体评分（0-100）

    # 各部分评分和建议
    section_scores: Dict[str, float] = Field(default_factory=dict)
    section_feedback: Dict[str, str] = Field(default_factory=dict)

    # 总体建议
    overall_suggestions: List[str] = Field(default_factory=list)

    # ATS 兼容性评分
    ats_score: Optional[float] = None

    created_at: Optional[datetime] = None


class InterviewPreparation(BaseModel):
    """面试准备。"""
    prep_id: str
    worker_id: str
    job_title: str
    company_name: Optional[str] = None
    interview_date: Optional[datetime] = None
    interview_type: str = "general"  # general, technical, behavioral

    # 准备状态
    preparation_status: GoalStatus = GoalStatus.DRAFT

    # 常见问题及回答
    common_questions: List[Dict] = Field(default_factory=list)
    practice_answers: Dict[str, str] = Field(default_factory=dict)

    # 模拟面试结果
    mock_interview_scores: List[Dict] = Field(default_factory=list)

    # 面试技巧建议
    tips: List[str] = Field(default_factory=list)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JobApplication(BaseModel):
    """求职申请。"""
    application_id: str
    worker_id: str
    job_title: str
    company_name: str
    job_description: Optional[str] = None
    application_url: Optional[str] = None

    # 申请状态
    status: str = "applied"  # applied, interviewing, offered, rejected, withdrawn

    # 申请日期
    applied_at: Optional[datetime] = None

    # 面试轮次
    interview_rounds: int = 0

    # 备注
    notes: str = ""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 创业支持相关模型 ==========

class StartupStage(str, Enum):
    """创业阶段。"""
    IDEA = "idea"  # 创意阶段
    VALIDATION = "validation"  # 验证阶段
    MVP = "mvp"  # 最小可行产品
    GROWTH = "growth"  # 增长阶段
    SCALING = "scaling"  # 扩张阶段


class FundingType(str, Enum):
    """融资类型。"""
    BOOTSTRAP = "bootstrap"  # 自筹资金
    SEED = "seed"  # 种子轮
    ANGEL = "angel"  # 天使轮
    SERIES_A = "series_a"  # A 轮
    SERIES_B = "series_b"  # B 轮
    SERIES_C_PLUS = "series_c_plus"  # C 轮及以后


class BusinessIdea(BaseModel):
    """商业创意。"""
    idea_id: str
    worker_id: str
    title: str
    description: str

    # 目标市场
    target_market: str = ""
    target_customers: str = ""

    # 价值主张
    value_proposition: str = ""

    # 竞争优势
    competitive_advantages: List[str] = Field(default_factory=list)

    # 商业模式
    business_model: str = ""

    # 所需资源
    required_resources: List[str] = Field(default_factory=list)

    # 风险评估
    risks: List[str] = Field(default_factory=list)

    # 状态
    status: StartupStage = StartupStage.IDEA

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BusinessPlan(BaseModel):
    """商业计划书。"""
    plan_id: str
    idea_id: str
    worker_id: str
    title: str

    # 执行摘要
    executive_summary: str = ""

    # 公司描述
    company_description: str = ""

    # 市场分析
    market_analysis: Dict = Field(default_factory=dict)

    # 产品/服务描述
    products_services: str = ""

    # 营销策略
    marketing_strategy: str = ""

    # 运营计划
    operational_plan: str = ""

    # 管理团队
    management_team: List[str] = Field(default_factory=list)

    # 财务计划
    financial_plan: Dict = Field(default_factory=dict)

    # 资金需求
    funding_requirements: Dict = Field(default_factory=dict)

    # 状态
    status: StartupStage = StartupStage.IDEA

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FundingOpportunity(BaseModel):
    """融资机会。"""
    opportunity_id: str
    title: str
    description: str
    funding_type: FundingType
    amount_range: Optional[str] = None  # 如 "$50K-$100K"

    # 投资方信息
    investor_name: Optional[str] = None
    investor_type: str = ""  # VC, Angel, Accelerator, etc.

    # 申请要求
    requirements: List[str] = Field(default_factory=list)

    # 申请截止日期
    deadline: Optional[datetime] = None

    # 申请链接
    application_url: Optional[str] = None

    # 匹配度评分（0-100）
    match_score: float = 0.0

    created_at: Optional[datetime] = None


class MentorshipMatch(BaseModel):
    """导师匹配。"""
    match_id: str
    mentee_worker_id: str
    mentor_worker_id: str

    # 匹配领域
    mentorship_areas: List[str] = Field(default_factory=list)

    # 匹配原因
    match_reasons: List[str] = Field(default_factory=list)

    # 匹配得分（0-100）
    match_score: float = 0.0

    # 状态
    status: GoalStatus = GoalStatus.DRAFT

    # 期望
    expectations: str = ""

    # 会议安排
    meeting_schedule: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 人脉拓展相关模型 ==========

class ConnectionType(str, Enum):
    """人脉类型。"""
    COLLEAGUE = "colleague"  # 同事
    MENTOR = "mentor"  # 导师
    MENTEE = "mentee"  # 学员
    CLIENT = "client"  # 客户
    PARTNER = "partner"  # 合作伙伴
    INVESTOR = "investor"  # 投资人
    RECRUITER = "recruiter"  # 招聘者
    OTHER = "other"  # 其他


class ProfessionalConnection(BaseModel):
    """职业人脉。"""
    connection_id: str
    worker_id: str  # 当前用户
    connected_worker_id: str  # 被连接的用户
    connection_type: ConnectionType

    # 关系描述
    relationship_description: str = ""

    # 共同点
    common_interests: List[str] = Field(default_factory=list)
    common_skills: List[str] = Field(default_factory=list)

    # 互动历史
    interaction_count: int = 0
    last_interaction_date: Optional[datetime] = None

    # 推荐强度
    recommendation_strength: float = 0.0  # 0-100

    # 状态
    status: str = "active"  # active, pending, blocked

    created_at: Optional[datetime] = None


class ReferralOpportunity(BaseModel):
    """内推机会。"""
    referral_id: str
    worker_id: str
    job_title: str
    company_name: str
    company_description: Optional[str] = None

    # 内推详情
    job_description: str = ""
    requirements: List[str] = Field(default_factory=list)

    # 报酬
    referral_bonus: Optional[str] = None

    # 状态
    status: str = "open"  # open, referred, hired, closed

    # 匹配度
    match_score: float = 0.0

    # 申请截止日期
    deadline: Optional[datetime] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NetworkingEvent(BaseModel):
    """人脉活动。"""
    event_id: str
    title: str
    description: str
    event_type: str  # conference, meetup, webinar, workshop, etc.

    # 时间地点
    start_date: datetime
    end_date: Optional[datetime] = None
    location: Optional[str] = None  # 线下地址
    virtual_url: Optional[str] = None  # 线上链接

    # 主办方
    organizer: str = ""

    # 参会者
    attendee_count: int = 0
    attendees: List[str] = Field(default_factory=list)  # worker_ids

    # 状态
    status: str = "upcoming"  # upcoming, ongoing, completed

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 响应模型 ==========

class CareerGoalResponse(BaseModel):
    """职业目标响应。"""
    goal_id: str
    worker_id: str
    title: str
    description: str
    goal_type: GoalType
    status: GoalStatus
    target_date: Optional[datetime] = None
    progress: float
    milestones_count: int
    completed_milestones: int
    related_skills: List[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SkillImprovementResponse(BaseModel):
    """技能提升响应。"""
    worker_id: str
    skill_name: str
    current_level: SkillLevel
    target_level: SkillLevel
    plan_id: Optional[str] = None
    progress: float
    recommended_resources: List[LearningResource]
    estimated_completion_date: Optional[datetime] = None


class CareerDevelopmentSummary(BaseModel):
    """职业发展摘要。"""
    worker_id: str
    active_goals: int
    completed_goals: int
    skills_in_progress: int
    learning_hours_total: float
    resume_score: Optional[float] = None
    connections_count: int
    upcoming_interviews: int
    referral_opportunities: int


class LearningResourceList(BaseModel):
    """学习资源列表。"""
    resources: List[LearningResource]
    total: int
    skip: int
    limit: int


class CareerGoalList(BaseModel):
    """职业目标列表。"""
    goals: List[CareerGoal]
    total: int
    skip: int
    limit: int


class JobApplicationList(BaseModel):
    """求职申请列表。"""
    applications: List[JobApplication]
    total: int
    skip: int
    limit: int
