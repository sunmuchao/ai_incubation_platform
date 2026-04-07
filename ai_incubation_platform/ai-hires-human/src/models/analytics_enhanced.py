"""
P27 数据分析增强 - 数据模型层。

定义数据分析增强相关的数据库模型。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, JSON, Boolean, Date, Index
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import Base


class PlatformStatistics(Base):
    """平台统计数据模型。"""
    __tablename__ = "platform_statistics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stat_date = Column(Date, nullable=False, index=True)

    # 任务统计
    total_tasks = Column(Integer, default=0)
    active_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)

    # 用户统计
    total_workers = Column(Integer, default=0)
    active_workers = Column(Integer, default=0)
    total_employers = Column(Integer, default=0)
    active_employers = Column(Integer, default=0)

    # 财务统计
    gmv = Column(DECIMAL(20, 2), default=0)  # 总交易额
    platform_fee = Column(DECIMAL(20, 2), default=0)  # 平台收入

    # 其他指标
    avg_task_reward = Column(DECIMAL(10, 2), default=0)  # 平均任务报酬
    avg_completion_time = Column(Integer, default=0)  # 平均完成时间 (小时)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stat_date": self.stat_date.isoformat() if self.stat_date else None,
            "total_tasks": self.total_tasks,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_workers": self.total_workers,
            "active_workers": self.active_workers,
            "total_employers": self.total_employers,
            "active_employers": self.active_employers,
            "gmv": float(self.gmv) if self.gmv else 0,
            "platform_fee": float(self.platform_fee) if self.platform_fee else 0,
            "avg_task_reward": float(self.avg_task_reward) if self.avg_task_reward else 0,
            "avg_completion_time": self.avg_completion_time,
        }


class UserBehavior(Base):
    """用户行为追踪模型。"""
    __tablename__ = "user_behaviors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    user_type = Column(String(20), nullable=False)  # employer/worker
    action_type = Column(String(50), nullable=False, index=True)  # view/click/apply/submit/etc
    target_type = Column(String(50))  # task/profile/etc
    target_id = Column(Integer)
    extra_data = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_user_behaviors_composite', 'user_id', 'user_type', 'timestamp'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_type": self.user_type,
            "action_type": self.action_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "extra_data": self.extra_data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class MatchingEffectiveness(Base):
    """匹配效果记录模型。"""
    __tablename__ = "matching_effectiveness"

    id = Column(Integer, primary_key=True, autoincrement=True)
    algorithm_version = Column(String(50))  # 算法版本
    task_id = Column(Integer, nullable=False, index=True)
    recommended_workers = Column(JSON, default=list)  # 推荐的工人 ID 列表
    accepted_worker_id = Column(Integer)  # 最终接单的工人 ID
    time_to_accept = Column(Integer)  # 接单耗时 (秒)
    task_completed = Column(Boolean, default=False)
    quality_score = Column(DECIMAL(5, 4), default=0)  # 质量评分 (0-1)

    # 分析字段
    click_through_rate = Column(DECIMAL(5, 4), default=0)  # 点击率
    conversion_rate = Column(DECIMAL(5, 4), default=0)  # 转化率

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "algorithm_version": self.algorithm_version,
            "task_id": self.task_id,
            "recommended_workers": self.recommended_workers,
            "accepted_worker_id": self.accepted_worker_id,
            "time_to_accept": self.time_to_accept,
            "task_completed": self.task_completed,
            "quality_score": float(self.quality_score) if self.quality_score else 0,
            "click_through_rate": float(self.click_through_rate) if self.click_through_rate else 0,
            "conversion_rate": float(self.conversion_rate) if self.conversion_rate else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RevenueAnalysis(Base):
    """收入分析记录模型。"""
    __tablename__ = "revenue_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_date = Column(DateTime, nullable=False, index=True)
    period = Column(String(20), nullable=False)  # daily/weekly/monthly

    # 收入统计
    total_revenue = Column(DECIMAL(20, 2), default=0)
    revenue_by_category = Column(JSON, default={})  # 按类别分解
    revenue_by_task_type = Column(JSON, default={})  # 按任务类型分解
    revenue_by_region = Column(JSON, default={})  # 按地区分解

    # 增长指标
    growth_rate = Column(DECIMAL(10, 4), default=0)  # 环比增长率
    forecast_next_period = Column(DECIMAL(20, 2), default=0)  # 下期预测

    # 定价分析
    avg_task_price = Column(DECIMAL(10, 2), default=0)
    price_elasticity = Column(DECIMAL(10, 4), default=0)  # 价格弹性

    # 洞察
    insights = Column(JSON, default=[])
    recommendations = Column(JSON, default=[])

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "analysis_date": self.analysis_date.isoformat() if self.analysis_date else None,
            "period": self.period,
            "total_revenue": float(self.total_revenue) if self.total_revenue else 0,
            "revenue_by_category": self.revenue_by_category,
            "revenue_by_task_type": self.revenue_by_task_type,
            "revenue_by_region": self.revenue_by_region,
            "growth_rate": float(self.growth_rate) if self.growth_rate else 0,
            "forecast_next_period": float(self.forecast_next_period) if self.forecast_next_period else 0,
            "avg_task_price": float(self.avg_task_price) if self.avg_task_price else 0,
            "insights": self.insights,
            "recommendations": self.recommendations,
        }


# ==================== 查询参数和响应模型 ====================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PlatformStatsQuery(BaseModel):
    """平台统计查询参数。"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    granularity: str = Field(default="day", description="时间粒度 (day/week/month)")


class PlatformStatsResponse(BaseModel):
    """平台统计响应。"""
    generated_at: str
    current_stats: Dict[str, Any]
    historical_trends: List[Dict[str, Any]]
    growth_metrics: Dict[str, Any]


class UserBehaviorProfile(BaseModel):
    """用户行为画像响应。"""
    user_id: int
    user_type: str
    total_actions: int
    action_breakdown: Dict[str, int]
    most_active_period: str
    favorite_categories: List[str]
    engagement_score: float


class BehaviorFunnelResponse(BaseModel):
    """行为漏斗响应。"""
    funnel_stages: List[Dict[str, Any]]
    conversion_rates: Dict[str, float]
    drop_off_points: List[str]


class MatchingPerformanceResponse(BaseModel):
    """匹配性能响应。"""
    algorithm_version: str
    total_matches: int
    acceptance_rate: float
    avg_time_to_accept: float
    task_completion_rate: float
    avg_quality_score: float
    top_performing_variants: List[Dict[str, Any]]


class RevenueReportResponse(BaseModel):
    """收入报表响应。"""
    period: str
    total_revenue: float
    revenue_breakdown: Dict[str, Any]
    growth_rate: float
    forecast: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]
