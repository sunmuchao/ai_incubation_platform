# -*- coding: utf-8 -*-
"""
v14.0.0 绩效评估增强 - 数据模型层

性能评估体系数据模型：
- 360 度评估反馈
- OKR 目标管理
- 绩效仪表盘
- 1 对 1 会议记录
- 晋升推荐

作者：AI Employee Platform Team
创建日期：2026-04-05
版本：v14.0.0
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship

from config.database import Base


def get_utc_now() -> datetime:
    """获取当前 UTC 时间"""
    return datetime.utcnow()


# ==================== 枚举类型 ====================

class ReviewType(str, Enum):
    """评估类型"""
    SELF = "self"  # 自评
    MANAGER = "manager"  # 上级评估
    PEER = "peer"  # 同级评估
    SUBORDINATE = "subordinate"  # 下级评估
    CUSTOMER = "customer"  # 客户评估
    SYSTEM = "system"  # 系统自动评估
    _360 = "360"  # 360 度综合评估


class ReviewStatus(str, Enum):
    """评估状态"""
    DRAFT = "draft"  # 草稿
    IN_PROGRESS = "in_progress"  # 进行中
    SUBMITTED = "submitted"  # 已提交
    COMPLETED = "completed"  # 已完成
    OVERDUE = "overdue"  # 已逾期


class ObjectiveStatus(str, Enum):
    """目标状态"""
    ON_TRACK = "on_track"  # 正常进行中
    AT_RISK = "at_risk"  # 有风险
    OFF_TRACK = "off_track"  # 偏离轨道
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class MetricType(str, Enum):
    """指标类型"""
    PERCENTAGE = "percentage"  # 百分比
    NUMBER = "number"  # 数字
    BOOLEAN = "boolean"  # 布尔值
    CURRENCY = "currency"  # 货币


class ActionItemStatus(str, Enum):
    """行动项状态"""
    PENDING = "pending"  # 待处理
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class PromotionStatus(str, Enum):
    """晋升状态"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    COMPLETED = "completed"  # 已完成


class ReviewCycleStatus(str, Enum):
    """评估周期状态"""
    PLANNED = "planned"  # 计划中
    ACTIVE = "active"  # 进行中
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"  # 已归档


# ==================== 360 度评估模型 ====================

class ReviewCycle(Base):
    """评估周期

    用于管理一批绩效评估的整体进度
    例如："2026 Q1 绩效评估"、"年度评估"
    """
    __tablename__ = "p14_review_cycles"

    id = Column(String(64), primary_key=True)
    name = Column(String(200), nullable=False)  # 周期名称
    description = Column(Text, nullable=True)  # 描述

    # 时间设置
    start_date = Column(DateTime, nullable=False)  # 开始日期
    end_date = Column(DateTime, nullable=False)  # 结束日期

    # 周期配置
    review_type = Column(SQLEnum(ReviewType), nullable=False, default=ReviewType._360)  # 评估类型
    target_employee_ids = Column(JSON, nullable=True)  # 目标员工 ID 列表，None 表示所有员工

    # 状态管理
    status = Column(SQLEnum(ReviewCycleStatus), nullable=False, default=ReviewCycleStatus.PLANNED)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)
    created_by = Column(String(64), nullable=True)  # 创建人

    # 关联
    reviews = relationship("PerformanceReview", back_populates="cycle", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "review_type": self.review_type.value,
            "target_employee_ids": self.target_employee_ids,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "progress": self.calculate_progress(),
        }

    def calculate_progress(self) -> Dict[str, Any]:
        """计算周期进度"""
        if not self.reviews:
            return {"total": 0, "completed": 0, "in_progress": 0, "pending": 0, "completion_rate": 0.0}

        total = len(self.reviews)
        completed = sum(1 for r in self.reviews if r.status == ReviewStatus.COMPLETED)
        in_progress = sum(1 for r in self.reviews if r.status == ReviewStatus.IN_PROGRESS)
        pending = sum(1 for r in self.reviews if r.status in [ReviewStatus.DRAFT, ReviewStatus.SUBMITTED])

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "completion_rate": round(completed / total * 100, 2) if total > 0 else 0.0
        }


class ReviewDimension(Base):
    """评估维度

    定义评估的具体维度，如"技能水平"、"响应速度"等
    """
    __tablename__ = "p14_review_dimensions"

    id = Column(String(64), primary_key=True)
    cycle_id = Column(String(64), ForeignKey("p14_review_cycles.id"), nullable=True)  # 关联周期，None 表示全局维度

    name = Column(String(100), nullable=False)  # 维度名称
    description = Column(Text, nullable=True)  # 维度描述
    weight = Column(Float, default=1.0)  # 权重
    max_score = Column(Float, default=5.0)  # 满分

    # 维度类型
    dimension_type = Column(String(50), default="custom")  # custom/skill/quality/efficiency/collaboration

    created_at = Column(DateTime, default=get_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "max_score": self.max_score,
            "dimension_type": self.dimension_type,
        }


class PerformanceReview(Base):
    """绩效评估

    记录一次具体的绩效评估
    """
    __tablename__ = "p14_performance_reviews"

    id = Column(String(64), primary_key=True)

    # 关联
    employee_id = Column(String(64), nullable=False, index=True)  # 被评估的 AI 员工
    cycle_id = Column(String(64), ForeignKey("p14_review_cycles.id"), nullable=True)  # 所属周期
    reviewer_id = Column(String(64), nullable=False)  # 评估人 ID

    # 评估信息
    review_type = Column(SQLEnum(ReviewType), nullable=False, default=ReviewType.MANAGER)
    status = Column(SQLEnum(ReviewStatus), nullable=False, default=ReviewStatus.DRAFT)

    # 评估内容
    scores = Column(JSON, nullable=True)  # {维度 ID: 分数}
    overall_score = Column(Float, nullable=True)  # 综合分数
    comments = Column(Text, nullable=True)  # 文字评价
    strengths = Column(JSON, nullable=True)  # 优势列表
    areas_for_improvement = Column(JSON, nullable=True)  # 待改进领域
    goals = Column(JSON, nullable=True)  # 下期目标

    # 时间追踪
    started_at = Column(DateTime, nullable=True)  # 开始评估时间
    submitted_at = Column(DateTime, nullable=True)  # 提交时间
    completed_at = Column(DateTime, nullable=True)  # 完成时间
    due_date = Column(DateTime, nullable=True)  # 截止日期

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关联
    cycle = relationship("ReviewCycle", back_populates="reviews")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "cycle_id": self.cycle_id,
            "reviewer_id": self.reviewer_id,
            "review_type": self.review_type.value,
            "status": self.status.value,
            "scores": self.scores or {},
            "overall_score": self.overall_score,
            "comments": self.comments,
            "strengths": self.strengths or [],
            "areas_for_improvement": self.areas_for_improvement or [],
            "goals": self.goals or [],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_overdue": self._is_overdue(),
        }

    def _is_overdue(self) -> bool:
        """检查是否逾期"""
        if self.status == ReviewStatus.COMPLETED:
            return False
        if self.due_date and datetime.utcnow() > self.due_date:
            return True
        return False


# ==================== OKR 目标管理模型 ====================

class Objective(Base):
    """OKR 目标

    支持层级结构：公司 → 部门 → 个人 AI 员工
    """
    __tablename__ = "p14_objectives"

    id = Column(String(64), primary_key=True)

    # 关联
    employee_id = Column(String(64), nullable=True, index=True)  # 所属员工（个人目标）
    department_id = Column(String(64), nullable=True)  # 所属部门
    company_id = Column(String(64), nullable=True)  # 公司级目标

    parent_objective_id = Column(String(64), ForeignKey("p14_objectives.id"), nullable=True)  # 上级目标

    # 目标信息
    title = Column(String(200), nullable=False)  # 目标标题
    description = Column(Text, nullable=True)  # 目标描述

    # 时间设置
    start_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)

    # 进度追踪
    progress = Column(Float, default=0.0)  # 0-100
    status = Column(SQLEnum(ObjectiveStatus), nullable=False, default=ObjectiveStatus.ON_TRACK)

    # 信心指数（1-10，表示对达成目标的信心）
    confidence_level = Column(Integer, default=5)

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)
    created_by = Column(String(64), nullable=True)

    # 关联
    parent = relationship("Objective", remote_side=[id], backref="children")
    key_results = relationship("KeyResult", back_populates="objective", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "department_id": self.department_id,
            "company_id": self.company_id,
            "parent_objective_id": self.parent_objective_id,
            "title": self.title,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "progress": self.progress,
            "status": self.status.value,
            "confidence_level": self.confidence_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "key_results_count": len(self.key_results),
            "children_count": len(self.children) if hasattr(self, 'children') else 0,
        }


class KeyResult(Base):
    """关键结果

    用于衡量目标达成的定量指标
    """
    __tablename__ = "p14_key_results"

    id = Column(String(64), primary_key=True)
    objective_id = Column(String(64), ForeignKey("p14_objectives.id"), nullable=False)

    # 关键结果信息
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 度量设置
    metric_type = Column(SQLEnum(MetricType), nullable=False, default=MetricType.NUMBER)
    unit = Column(String(50), nullable=True)  # 单位，如"%"、"个"、"$"

    # 目标值设定
    start_value = Column(Float, default=0.0)  # 起始值
    target_value = Column(Float, nullable=False)  # 目标值
    current_value = Column(Float, default=0.0)  # 当前值

    # 进度计算
    progress = Column(Float, default=0.0)  # 自动计算的进度百分比
    stretch_target = Column(Float, nullable=True)  # 延展目标（超越期望的值）

    # 信心指数
    confidence_level = Column(Integer, default=5)

    # 检查点（用于追踪历史值）
    checkpoints = Column(JSON, nullable=True)  # [{date, value}, ...]

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关联
    objective = relationship("Objective", back_populates="key_results")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "objective_id": self.objective_id,
            "title": self.title,
            "description": self.description,
            "metric_type": self.metric_type.value,
            "unit": self.unit,
            "start_value": self.start_value,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "progress": self.progress,
            "stretch_target": self.stretch_target,
            "confidence_level": self.confidence_level,
            "checkpoints": self.checkpoints or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_stretch": self.current_value > self.target_value if self.current_value else False,
        }

    def calculate_progress(self) -> float:
        """计算进度百分比"""
        if self.target_value == self.start_value:
            return 100.0 if self.current_value >= self.target_value else 0.0

        range_size = self.target_value - self.start_value
        current_progress = self.current_value - self.start_value

        return min(100.0, max(0.0, (current_progress / range_size) * 100))


# ==================== 绩效指标模型 ====================

class PerformanceMetrics(Base):
    """绩效指标快照

    定期计算的绩效指标快照，用于趋势分析
    """
    __tablename__ = "p14_performance_metrics"

    id = Column(String(64), primary_key=True)
    employee_id = Column(String(64), nullable=False, index=True)

    # 时间周期
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # 效率指标
    avg_response_time = Column(Float, nullable=True)  # 平均响应时间（秒）
    task_completion_rate = Column(Float, nullable=True)  # 任务完成率（0-100）
    on_time_delivery_rate = Column(Float, nullable=True)  # 准时交付率（0-100）
    tasks_completed = Column(Integer, default=0)  # 完成任务数

    # 质量指标
    error_rate = Column(Float, nullable=True)  # 错误率（0-100）
    customer_satisfaction = Column(Float, nullable=True)  # 客户满意度（1-5）
    rework_rate = Column(Float, nullable=True)  # 返工率（0-100）

    # 贡献指标
    revenue_generated = Column(Float, default=0.0)  # 创造收入
    cost_saved = Column(Float, default=0.0)  # 节省成本
    hours_saved = Column(Float, default=0.0)  # 节省工时

    # 成长指标
    skills_improved = Column(JSON, nullable=True)  # 提升的技能列表
    certifications_earned = Column(Integer, default=0)  # 获得认证数
    training_hours = Column(Float, default=0.0)  # 培训时长

    # 综合分数
    overall_performance_score = Column(Float, nullable=True)

    # 原始数据快照
    raw_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=get_utc_now)
    calculated_at = Column(DateTime, default=get_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "efficiency_metrics": {
                "avg_response_time": self.avg_response_time,
                "task_completion_rate": self.task_completion_rate,
                "on_time_delivery_rate": self.on_time_delivery_rate,
                "tasks_completed": self.tasks_completed,
            },
            "quality_metrics": {
                "error_rate": self.error_rate,
                "customer_satisfaction": self.customer_satisfaction,
                "rework_rate": self.rework_rate,
            },
            "contribution_metrics": {
                "revenue_generated": self.revenue_generated,
                "cost_saved": self.cost_saved,
                "hours_saved": self.hours_saved,
            },
            "growth_metrics": {
                "skills_improved": self.skills_improved or [],
                "certifications_earned": self.certifications_earned,
                "training_hours": self.training_hours,
            },
            "overall_performance_score": self.overall_performance_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================== 1 对 1 会议模型 ====================

class OneOnOneMeeting(Base):
    """1 对 1 会议记录

    记录与 AI 员工的反馈会话
    """
    __tablename__ = "p14_one_on_one_meetings"

    id = Column(String(64), primary_key=True)

    # 关联
    employee_id = Column(String(64), nullable=False, index=True)  # AI 员工
    manager_id = Column(String(64), nullable=False)  # 管理者/用户

    # 会议信息
    meeting_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=True)  # 会议时长（分钟）
    meeting_type = Column(String(50), default="regular")  # regular/feedback/checkin/planning

    # 会议内容
    agenda = Column(Text, nullable=True)  # 议程
    notes = Column(Text, nullable=True)  # 会议笔记
    summary = Column(Text, nullable=True)  # AI 生成的摘要

    # 讨论话题
    topics_discussed = Column(JSON, nullable=True)  # ["项目进展", "技能提升", ...]

    # 时间追踪
    follow_up_date = Column(DateTime, nullable=True)  # 下次会议日期

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关联
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "manager_id": self.manager_id,
            "meeting_date": self.meeting_date.isoformat() if self.meeting_date else None,
            "duration_minutes": self.duration_minutes,
            "meeting_type": self.meeting_type,
            "agenda": self.agenda,
            "notes": self.notes,
            "summary": self.summary,
            "topics_discussed": self.topics_discussed or [],
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "action_items_count": len(self.action_items) if hasattr(self, 'action_items') else 0,
            "completed_action_items": sum(1 for ai in self.action_items if ai.status == ActionItemStatus.COMPLETED) if hasattr(self, 'action_items') else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ActionItem(Base):
    """行动项

    从会议中产生的待办事项
    """
    __tablename__ = "p14_action_items"

    id = Column(String(64), primary_key=True)
    meeting_id = Column(String(64), ForeignKey("p14_one_on_one_meetings.id"), nullable=False)

    # 行动项信息
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="medium")  # low/medium/high/urgent

    # 负责人
    owner_id = Column(String(64), nullable=False)  # 负责人 ID
    owner_type = Column(String(20), default="employee")  # employee/manager/both

    # 状态追踪
    status = Column(SQLEnum(ActionItemStatus), nullable=False, default=ActionItemStatus.PENDING)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 备注
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关联
    meeting = relationship("OneOnOneMeeting", back_populates="action_items")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "description": self.description,
            "priority": self.priority,
            "owner_id": self.owner_id,
            "owner_type": self.owner_type,
            "status": self.status.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
            "is_overdue": self._is_overdue(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def _is_overdue(self) -> bool:
        """检查是否逾期"""
        if self.status == ActionItemStatus.COMPLETED:
            return False
        if self.due_date and datetime.utcnow() > self.due_date:
            return True
        return False


# ==================== 晋升推荐模型 ====================

class PromotionRecommendation(Base):
    """晋升推荐

    基于绩效数据自动生成的晋升建议
    """
    __tablename__ = "p14_promotion_recommendations"

    id = Column(String(64), primary_key=True)
    employee_id = Column(String(64), nullable=False, index=True)

    # 晋升信息
    current_level = Column(String(100), nullable=False)  # 当前等级
    recommended_level = Column(String(100), nullable=False)  # 推荐等级

    # 推荐评分
    recommendation_score = Column(Float, nullable=False)  # 0-100

    # 推荐理由
    reasons = Column(JSON, nullable=True)  # 推荐理由列表
    supporting_evidence = Column(JSON, nullable=True)  # 支持证据

    # 详细评估
    performance_score = Column(Float, nullable=True)  # 绩效分数
    tenure_months = Column(Integer, nullable=True)  # 在职月数
    skills_assessment = Column(JSON, nullable=True)  # 技能评估

    # 状态
    status = Column(SQLEnum(PromotionStatus), nullable=False, default=PromotionStatus.PENDING)
    reviewed_by = Column(String(64), nullable=True)  # 审批人
    reviewed_at = Column(DateTime, nullable=True)  # 审批时间
    review_comments = Column(Text, nullable=True)  # 审批意见

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "current_level": self.current_level,
            "recommended_level": self.recommended_level,
            "recommendation_score": self.recommendation_score,
            "reasons": self.reasons or [],
            "supporting_evidence": self.supporting_evidence or [],
            "performance_score": self.performance_score,
            "tenure_months": self.tenure_months,
            "skills_assessment": self.skills_assessment or {},
            "status": self.status.value,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_comments": self.review_comments,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PromotionHistory(Base):
    """晋升历史

    记录 AI 员工的晋升历史
    """
    __tablename__ = "p14_promotion_history"

    id = Column(String(64), primary_key=True)
    employee_id = Column(String(64), nullable=False, index=True)

    # 晋升信息
    from_level = Column(String(100), nullable=False)
    to_level = Column(String(100), nullable=False)

    # 晋升日期
    effective_date = Column(DateTime, nullable=False)

    # 关联的推荐
    recommendation_id = Column(String(64), ForeignKey("p14_promotion_recommendations.id"), nullable=True)

    # 备注
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "recommendation_id": self.recommendation_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================== 绩效基准模型 ====================

class PerformanceBenchmark(Base):
    """绩效基准

    用于对比的行业基准或内部基准
    """
    __tablename__ = "p14_performance_benchmarks"

    id = Column(String(64), primary_key=True)

    # 基准信息
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)  # 分类，如技能名称

    # 基准值
    percentile_25 = Column(Float, nullable=True)  # P25
    percentile_50 = Column(Float, nullable=True)  # P50（中位数）
    percentile_75 = Column(Float, nullable=True)  # P75
    average = Column(Float, nullable=True)  # 平均值

    # 样本信息
    sample_size = Column(Integer, nullable=True)
    data_source = Column(String(100), nullable=True)  # internal/industry

    # 适用条件
    min_experience_months = Column(Integer, nullable=True)  # 最小经验要求
    skill_level = Column(String(50), nullable=True)  # 技能等级要求

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "percentiles": {
                "p25": self.percentile_25,
                "p50": self.percentile_50,
                "p75": self.percentile_75,
            },
            "average": self.average,
            "sample_size": self.sample_size,
            "data_source": self.data_source,
            "requirements": {
                "min_experience_months": self.min_experience_months,
                "skill_level": self.skill_level,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
