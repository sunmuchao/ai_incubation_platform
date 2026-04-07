"""
工人能力画像数据模型。
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WorkerProfile(BaseModel):
    """工人能力画像。"""

    worker_id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    skills: Dict[str, str] = Field(default_factory=dict)  # 技能标签与等级
    completed_tasks: int = 0  # 完成任务数
    success_rate: float = 1.0  # 任务成功率
    average_rating: float = 5.0  # 平均评分
    total_earnings: float = 0.0  # 总收入
    level: int = 1  # 用户等级
    tags: List[str] = Field(default_factory=list)  # 自定义标签
    external_profile_id: Optional[str] = None  # 外部系统画像 ID
    metadata: Dict = Field(default_factory=dict)  # 扩展字段
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ===== 优化 1: 任务偏好设置（智能推荐用）=====
    preferred_interaction_types: List[str] = Field(default_factory=list)
    """偏好的交互类型：digital, physical, hybrid"""
    min_reward_preference: float = 0.0
    """最低报酬偏好"""
    max_task_duration_hours: Optional[int] = None
    """最大任务时长（小时），None 表示无限制"""
    active_hours: List[int] = Field(default_factory=lambda: list(range(9, 18)))
    """活跃时段（24 小时制的小时列表）"""

    # ===== 优化 2: 可信度评分（质量控制用）=====
    trust_score: float = 1.0
    """可信度评分 (0-1)，基于黄金标准测试和历史表现"""
    gold_standard_tests_passed: int = 0
    """通过的黄金标准测试次数"""
    gold_standard_tests_total: int = 0
    """黄金标准测试总次数"""
    quality_tier: str = "bronze"
    """质量等级：bronze, silver, gold, platinum"""

    # ===== 优化 3: 资格认证（认证系统用）=====
    certifications: List[str] = Field(default_factory=list)
    """已获得的资格认证 ID 列表"""
    verified_skills: List[str] = Field(default_factory=list)
    """已验证的技能列表"""


class WorkerProfileCreate(BaseModel):
    """创建工人画像。"""

    worker_id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    skills: Dict[str, str] = Field(default_factory=dict)
    level: int = 1
    tags: List[str] = Field(default_factory=list)
    external_profile_id: Optional[str] = None


class WorkerProfileUpdate(BaseModel):
    """更新工人画像。"""

    name: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[Dict[str, str]] = None
    level: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class WorkerSearchRequest(BaseModel):
    """工人搜索请求。"""

    skills: Optional[List[str]] = None
    location: Optional[str] = None
    min_level: int = 0
    min_rating: float = 0.0
    min_success_rate: float = 0.0
    skip: int = 0
    limit: int = 100


class WorkerStats(BaseModel):
    """工人统计数据。"""

    worker_id: str
    total_tasks: int = 0  # 总任务数
    completed_tasks: int = 0  # 完成任务数
    in_progress_tasks: int = 0  # 进行中任务数
    success_rate: float = 0.0  # 成功率
    average_rating: float = 0.0  # 平均评分
    total_earnings: float = 0.0  # 总收入
    recent_tasks: List[Dict] = Field(default_factory=list)  # 最近任务


class WorkerListResponse(BaseModel):
    """工人列表响应。"""

    workers: List[WorkerProfile]
    total: int
    skip: int
    limit: int


# ===== 优化 1: 推荐系统相关模型 =====
class WorkerPreferenceUpdate(BaseModel):
    """更新工人任务偏好。"""
    preferred_interaction_types: Optional[List[str]] = None
    min_reward_preference: Optional[float] = None
    max_task_duration_hours: Optional[int] = None
    active_hours: Optional[List[int]] = None


class TaskRecommendation(BaseModel):
    """推荐任务响应。"""
    task_id: str
    title: str
    reward_amount: float
    interaction_type: str
    match_score: float
    match_reasons: List[str]


class RecommendationRequest(BaseModel):
    """推荐请求。"""
    worker_id: str
    limit: int = 10


class RecommendationResponse(BaseModel):
    """推荐响应。"""
    worker_id: str
    recommendations: List[TaskRecommendation]
    total_available: int


# ===== v1.16.0 新增：双向推荐相关模型 =====
class WorkerRecommendation(BaseModel):
    """推荐给雇主的工人。"""
    worker_id: str
    name: Optional[str] = None
    skills: Dict[str, str] = Field(default_factory=dict)
    trust_score: float
    success_rate: float
    quality_tier: str
    completed_tasks: int
    average_rating: float
    match_score: float
    match_reasons: List[str]
    estimated_reward_range: Optional[str] = None


class EmployerRecommendationRequest(BaseModel):
    """雇主推荐工人请求。"""
    task_id: str
    limit: int = 10


class EmployerRecommendationResponse(BaseModel):
    """雇主推荐工人响应。"""
    task_id: str
    recommendations: List[WorkerRecommendation]
    total_available: int


class RecommendationExplanation(BaseModel):
    """推荐解释报告。"""
    task_id: str
    worker_id: str
    overall_score: float
    dimension_scores: Dict[str, float]
    match_reasons: List[str]
    recommendation_level: str
    skill_match_details: Optional[Dict] = None
    historical_performance_details: Optional[Dict] = None


# ===== 优化 2: 质量控制相关模型 =====
class TrustScoreResponse(BaseModel):
    """可信度评分响应。"""
    worker_id: str
    trust_score: float
    quality_tier: str
    gold_standard_passed: int
    gold_standard_total: int


# ===== 优化 3: 资格认证相关模型 =====
class Certification(BaseModel):
    """资格认证。"""
    certification_id: str
    name: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    is_active: bool = True


class CertificationCreate(BaseModel):
    """创建认证。"""
    certification_id: str
    name: str
    description: str
    required_skills: List[str] = Field(default_factory=list)


class CertificationRequest(BaseModel):
    """申请认证。"""
    worker_id: str
    certification_id: str
