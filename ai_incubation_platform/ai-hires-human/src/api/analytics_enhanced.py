"""
P27 数据分析增强 - API 层。

提供数据分析增强的 HTTP 接口，包括：
- 平台数据统计
- 用户行为分析
- 匹配效果分析
- 收入分析报表
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_session
from services.analytics_enhanced_services import (
    PlatformStatisticsService,
    UserBehaviorService,
    MatchingEffectivenessService,
    RevenueAnalyticsService,
    get_platform_statistics_service,
    get_user_behavior_service,
    get_matching_effectiveness_service,
    get_revenue_analytics_service,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics_enhanced"])


# ==================== 平台数据统计接口 ====================

@router.get("/platform/stats", summary="获取平台实时统计")
async def get_platform_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取平台实时统计数据。

    包含：
    - 任务统计（总数/活跃/完成）
    - 用户统计（工人/雇主）
    - 财务统计（GMV/平台收入）
    """
    service = get_platform_statistics_service(db)

    try:
        stats = await service.get_realtime_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get platform stats: {str(e)}"
        )


@router.get("/platform/trends", summary="获取平台历史趋势")
async def get_platform_trends(
    start_date: Optional[str] = Query(default=None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="结束日期 YYYY-MM-DD"),
    granularity: str = Query(default="day", description="时间粒度 (day/week/month)"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取平台历史趋势数据。

    - start_date: 开始日期 (YYYY-MM-DD)，默认 30 天前
    - end_date: 结束日期 (YYYY-MM-DD)，默认今天
    - granularity: 时间粒度 (day/week/month)
    """
    service = get_platform_statistics_service(db)

    # 解析日期
    start_dt = None
    end_dt = None

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    else:
        start_dt = datetime.utcnow() - timedelta(days=30)

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    else:
        end_dt = datetime.utcnow()

    try:
        trends = await service.get_historical_stats(start_dt, end_dt, granularity)
        return {
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "granularity": granularity,
            "trends": trends,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trends: {str(e)}"
        )


@router.get("/platform/categories", summary="获取类别分布")
async def get_category_breakdown(
    period: str = Query(default="30d", description="统计周期 (7d/30d/90d)"),
    db: AsyncSession = Depends(get_db_session),
):
    """获取任务类别分布统计。"""
    service = get_platform_statistics_service(db)

    try:
        breakdown = await service.get_category_breakdown(period)
        return breakdown
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get category breakdown: {str(e)}"
        )


@router.get("/platform/geo", summary="获取地理分布")
async def get_geographic_distribution(
    db: AsyncSession = Depends(get_db_session),
):
    """获取用户地理分布统计。"""
    service = get_platform_statistics_service(db)

    try:
        distribution = await service.get_geographic_distribution()
        return distribution
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get geographic distribution: {str(e)}"
        )


# ==================== 用户行为分析接口 ====================

@router.post("/behavior/track", summary="追踪用户行为")
async def track_user_behavior(
    user_id: int,
    user_type: str,
    action_type: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """
    追踪用户行为。

    - user_id: 用户 ID
    - user_type: 用户类型 (employer/worker)
    - action_type: 行为类型 (view/click/apply/submit/complete)
    - target_type: 目标类型 (task/profile/etc)
    - target_id: 目标 ID
    - metadata: 额外元数据
    """
    service = get_user_behavior_service(db)

    try:
        behavior = await service.track_behavior(
            user_id=user_id,
            user_type=user_type,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata,
        )
        return {
            "success": True,
            "behavior_id": behavior.id,
            "timestamp": behavior.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track behavior: {str(e)}"
        )


@router.get("/behavior/profile", summary="获取用户行为画像")
async def get_user_behavior_profile(
    user_id: int,
    user_type: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取用户行为画像分析。"""
    service = get_user_behavior_service(db)

    try:
        profile = await service.get_user_profile(user_id, user_type)
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user profile: {str(e)}"
        )


@router.get("/behavior/funnel", summary="获取行为漏斗分析")
async def get_behavior_funnel(
    period: str = Query(default="7d", description="分析周期 (7d/14d/30d)"),
    db: AsyncSession = Depends(get_db_session),
):
    """获取用户行为漏斗分析。"""
    service = get_user_behavior_service(db)

    try:
        funnel = await service.get_behavior_funnel(period)
        return funnel
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get funnel: {str(e)}"
        )


@router.get("/behavior/retention", summary="获取留存分析")
async def get_retention_analysis(
    cohort_date: Optional[str] = Query(default=None, description="队列日期 YYYY-MM-DD"),
    period: str = Query(default="30d", description="分析周期"),
    db: AsyncSession = Depends(get_db_session),
):
    """获取用户留存分析。"""
    service = get_user_behavior_service(db)

    if not cohort_date:
        cohort_date = datetime.utcnow().date().isoformat()

    try:
        retention = await service.get_retention_cohort(cohort_date, period)
        return retention
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get retention: {str(e)}"
        )


# ==================== 匹配效果分析接口 ====================

@router.post("/matching/record", summary="记录匹配结果")
async def record_matching_result(
    task_id: int,
    algorithm_version: str,
    recommended_workers: list,
    accepted_worker_id: Optional[int] = None,
    time_to_accept: Optional[int] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """记录匹配结果用于后续分析。"""
    service = get_matching_effectiveness_service(db)

    try:
        record = await service.record_match_result(
            task_id=task_id,
            algorithm_version=algorithm_version,
            recommended_workers=recommended_workers,
            accepted_worker_id=accepted_worker_id,
            time_to_accept=time_to_accept,
        )
        return {
            "success": True,
            "record_id": record.id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record match: {str(e)}"
        )


@router.get("/matching/performance", summary="获取算法性能表现")
async def get_matching_performance(
    algorithm_version: Optional[str] = Query(default=None, description="算法版本"),
    period: str = Query(default="30d", description="分析周期"),
    db: AsyncSession = Depends(get_db_session),
):
    """获取匹配算法性能表现。"""
    service = get_matching_effectiveness_service(db)

    try:
        performance = await service.get_algorithm_performance(algorithm_version, period)
        return performance
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance: {str(e)}"
        )


@router.get("/matching/insights", summary="获取推荐洞察")
async def get_matching_insights(
    db: AsyncSession = Depends(get_db_session),
):
    """获取推荐系统洞察和改进建议。"""
    service = get_matching_effectiveness_service(db)

    try:
        insights = await service.get_recommendation_insights()
        return insights
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get insights: {str(e)}"
        )


# ==================== 收入分析接口 ====================

@router.get("/revenue/report", summary="获取收入报表")
async def get_revenue_report(
    period: str = Query(default="30d", description="分析周期 (7d/30d/90d)"),
    group_by: str = Query(default="day", description="分组方式 (day/week/month)"),
    db: AsyncSession = Depends(get_db_session),
):
    """获取收入报表。"""
    service = get_revenue_analytics_service(db)

    try:
        report = await service.get_revenue_report(period, group_by)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get revenue report: {str(e)}"
        )


@router.get("/revenue/breakdown", summary="获取收入分解")
async def get_revenue_breakdown(
    period: str = Query(default="30d", description="分析周期"),
    db: AsyncSession = Depends(get_db_session),
):
    """获取收入分解分析。"""
    service = get_revenue_analytics_service(db)

    try:
        breakdown = await service.get_revenue_breakdown(period)
        return breakdown
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get revenue breakdown: {str(e)}"
        )


@router.get("/revenue/forecast", summary="获取收入预测")
async def get_revenue_forecast(
    forecast_period: str = Query(default="7d", description="预测周期 (7d/14d/30d)"),
    db: AsyncSession = Depends(get_db_session),
):
    """获取收入预测。"""
    service = get_revenue_analytics_service(db)

    try:
        forecast = await service.get_forecast(forecast_period)
        return forecast
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get forecast: {str(e)}"
        )


# ==================== 综合分析仪表板 ====================

@router.get("/enhanced-dashboard", summary="数据分析增强仪表板")
async def get_enhanced_analytics_dashboard(
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取数据分析增强仪表板。

    整合所有数据分析功能，提供一站式数据视图。
    """
    platform_service = get_platform_statistics_service(db)
    behavior_service = get_user_behavior_service(db)
    matching_service = get_matching_effectiveness_service(db)
    revenue_service = get_revenue_analytics_service(db)

    try:
        # 并发获取所有数据
        platform_stats = await platform_service.get_realtime_stats()
        behavior_funnel = await behavior_service.get_behavior_funnel("7d")
        matching_performance = await matching_service.get_algorithm_performance(period="30d")
        revenue_report = await revenue_service.get_revenue_report("30d")

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "platform_stats": platform_stats,
            "behavior_analysis": {
                "funnel": behavior_funnel,
            },
            "matching_analysis": matching_performance,
            "revenue_analysis": {
                "report": revenue_report,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard: {str(e)}"
        )


# ==================== 帮助接口 ====================

@router.get("/help/metrics", summary="获取分析指标说明")
async def get_analytics_metrics_help():
    """获取数据分析指标的定义和说明。"""
    return {
        "platform_statistics": {
            "gmv": "总交易额 (Gross Merchandise Value)",
            "platform_fee": "平台收入",
            "active_workers": "活跃工人数（近 7 天有行为）",
            "active_employers": "活跃雇主数（近 7 天发布任务）",
        },
        "behavior_analysis": {
            "engagement_score": "用户活跃度评分 (0-100)",
            "conversion_rate": "转化率（从浏览到完成任务）",
            "retention_rate": "留存率",
        },
        "matching_analysis": {
            "acceptance_rate": "任务接受率",
            "completion_rate": "任务完成率",
            "time_to_accept": "平均接单耗时",
        },
        "revenue_analysis": {
            "growth_rate": "环比增长率",
            "forecast": "基于历史数据的预测",
        },
    }
