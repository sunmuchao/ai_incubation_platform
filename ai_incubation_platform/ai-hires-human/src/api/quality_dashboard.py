"""
质量保证仪表板 API - 提供统一的质量数据视图和分析功能。

整合以下服务的数据：
1. 质量预测服务
2. 智能验收服务
3. 黄金标准测试服务
4. 争议预防服务
5. 质量改进服务
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quality-dashboard", tags=["quality_dashboard"])


@router.get("/overview")
async def get_quality_overview(
    days: int = Query(30, description="统计天数"),
):
    """
    获取质量保证概览数据。

    整合所有质量相关服务的核心指标。
    """
    # 注：实际实现需要从数据库聚合数据
    # 这里是模拟实现，展示仪表板应包含的指标

    cutoff_date = datetime.now() - timedelta(days=days)

    return {
        "overview": {
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
        },
        "metrics": {
            # 质量预测指标
            "predictions": {
                "total_predictions": 0,
                "high_risk_predictions": 0,
                "prediction_accuracy": 0.0,
            },
            # 智能验收指标
            "acceptance": {
                "total_inspections": 0,
                "auto_approved": 0,
                "auto_rejected": 0,
                "manual_review_required": 0,
                "average_confidence": 0.0,
            },
            # 黄金标准测试指标
            "golden_standard": {
                "active_tests": 0,
                "total_attempts": 0,
                "pass_rate": 0.0,
                "active_certifications": 0,
            },
            # 争议预防指标
            "dispute_prevention": {
                "total_assessments": 0,
                "high_risk_tasks": 0,
                "disputes_prevented": 0,
                "actual_disputes": 0,
            },
            # 质量改进指标
            "improvement": {
                "total_analyses": 0,
                "average_quality_score": 0.0,
                "workers_improved": 0,
            },
        },
        "trends": {
            "quality_score_trend": [],
            "dispute_rate_trend": [],
            "auto_approval_rate_trend": [],
        },
    }


@router.get("/quality-prediction")
async def get_quality_prediction_dashboard(
    days: int = Query(7, description="统计天数"),
):
    """获取质量预测仪表板数据。"""
    from services.quality_prediction_service import quality_prediction_service

    # 获取预测统计
    all_predictions = quality_prediction_service._predictions.values()

    # 按质量等级分组
    level_counts = {}
    for pred in all_predictions:
        level = pred.predicted_quality_level.value
        level_counts[level] = level_counts.get(level, 0) + 1

    # 计算平均得分
    if all_predictions:
        avg_score = sum(p.quality_score for p in all_predictions) / len(all_predictions)
        avg_confidence = sum(p.confidence for p in all_predictions) / len(all_predictions)
    else:
        avg_score = 0.0
        avg_confidence = 0.0

    return {
        "summary": {
            "total_predictions": len(all_predictions),
            "average_quality_score": round(avg_score, 3),
            "average_confidence": round(avg_confidence, 3),
        },
        "distribution": {
            "by_level": level_counts,
            "by_risk": {
                "low": sum(1 for p in all_predictions if p.risk_score < 0.3),
                "medium": sum(1 for p in all_predictions if 0.3 <= p.risk_score < 0.7),
                "high": sum(1 for p in all_predictions if p.risk_score >= 0.7),
            },
        },
        "top_risk_factors": _get_top_risk_factors(all_predictions),
    }


@router.get("/intelligent-acceptance")
async def get_intelligent_acceptance_dashboard(
    days: int = Query(7, description="统计天数"),
):
    """获取智能验收仪表板数据。"""
    from services.intelligent_acceptance_service import intelligent_acceptance_service

    all_reports = list(intelligent_acceptance_service._reports.values())

    # 统计结果分布
    result_counts = {"pass": 0, "fail": 0, "warning": 0, "skipped": 0}
    for report in all_reports:
        result = report.overall_result.value
        result_counts[result] = result_counts.get(result, 0) + 1

    # 计算平均置信度
    if all_reports:
        avg_score = sum(r.overall_score for r in all_reports) / len(all_reports)
        avg_confidence = sum(r.confidence for r in all_reports) / len(all_reports)
    else:
        avg_score = 0.0
        avg_confidence = 0.0

    return {
        "summary": {
            "total_inspections": len(all_reports),
            "average_score": round(avg_score, 3),
            "average_confidence": round(avg_confidence, 3),
        },
        "result_distribution": result_counts,
        "recommendations": {
            "approve": sum(1 for r in all_reports if r.ai_recommendation == "approve"),
            "reject": sum(1 for r in all_reports if r.ai_recommendation == "reject"),
            "manual_review": sum(1 for r in all_reports if r.ai_recommendation == "manual_review"),
        },
    }


@router.get("/golden-standard")
async def get_golden_standard_dashboard():
    """获取黄金标准测试仪表板数据。"""
    # 注：实际应从数据库获取
    return {
        "summary": {
            "message": "Data available via /api/golden-standard/tests/{test_id}/statistics",
        },
        "note": "Golden standard data is available through the dedicated API endpoints",
    }


@router.get("/dispute-prevention")
async def get_dispute_prevention_dashboard(
    days: int = Query(7, description="统计天数"),
):
    """获取争议预防仪表板数据。"""
    from services.dispute_prevention_service import dispute_prevention_service

    stats = dispute_prevention_service.get_risk_statistics()
    high_risk_tasks = dispute_prevention_service.get_high_risk_tasks()

    return {
        "summary": stats,
        "high_risk_tasks": [
            {
                "risk_id": r.risk_id,
                "task_id": r.task_id,
                "risk_level": r.risk_level.value,
                "risk_score": r.risk_score,
            }
            for r in high_risk_tasks[:10]  # 最多返回 10 个
        ],
        "risk_factor_distribution": _get_dispute_factor_distribution(),
    }


@router.get("/quality-improvement")
async def get_quality_improvement_dashboard(
    days: int = Query(7, description="统计天数"),
):
    """获取质量改进仪表板数据。"""
    from services.quality_improvement_service import quality_improvement_service

    stats = quality_improvement_service.get_improvement_stats()

    return {
        "summary": stats,
        "issue_categories": stats.get("issue_distribution", {}),
        "most_common_issue": stats.get("most_common_issue", "unknown"),
    }


@router.get("/worker/{worker_id}/quality-profile")
async def get_worker_quality_profile(worker_id: str):
    """
    获取工人的完整质量画像。

    整合工人在所有质量维度的数据。
    """
    from services.quality_prediction_service import quality_prediction_service
    from services.quality_improvement_service import quality_improvement_service

    # 质量预测统计
    prediction_stats = quality_prediction_service.get_worker_quality_stats(worker_id)

    # 质量改进趋势
    improvement_trend = quality_improvement_service.get_worker_quality_trend(worker_id)

    return {
        "worker_id": worker_id,
        "quality_profile": {
            "prediction_stats": prediction_stats,
            "improvement_trend": improvement_trend,
        },
        "composite_score": _calculate_composite_quality_score(
            prediction_stats,
            improvement_trend,
        ),
    }


@router.get("/alerts")
async def get_quality_alerts(
    min_severity: str = Query("medium", description="最低严重级别 (low/medium/high/critical)"),
    limit: int = Query(20, description="返回数量限制"),
):
    """
    获取质量相关的告警列表。

    整合来自各服务的高优先级告警。
    """
    alerts = []

    # 1. 质量预测高风险告警
    from services.quality_prediction_service import quality_prediction_service

    for pred in quality_prediction_service._predictions.values():
        if pred.risk_score >= 0.7:
            alerts.append({
                "type": "quality_prediction",
                "severity": "high" if pred.risk_score >= 0.85 else "medium",
                "task_id": pred.task_id,
                "worker_id": pred.worker_id,
                "message": f"质量风险预警：{pred.predicted_quality_level.value} (风险得分{pred.risk_score:.2f})",
                "created_at": pred.created_at.isoformat(),
            })

    # 2. 争议预防高风险告警
    from services.dispute_prevention_service import dispute_prevention_service
    from services.dispute_prevention_service import DisputeRiskLevel

    for record in dispute_prevention_service.get_high_risk_tasks():
        alerts.append({
            "type": "dispute_prevention",
            "severity": record.risk_level.value,
            "task_id": record.task_id,
            "message": f"争议风险预警：{record.risk_level.value} (风险得分{record.risk_score:.2f})",
            "created_at": record.created_at.isoformat(),
        })

    # 按严重级别排序
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 4))

    return {
        "alerts": alerts[:limit],
        "total": len(alerts),
    }


# ========== 辅助函数 ==========

def _get_top_risk_factors(predictions, top_n: int = 5) -> List[Dict]:
    """获取最常见的风险因素。"""
    factor_counts = {}
    for pred in predictions:
        for factor in pred.risk_factors:
            # 简化：直接使用因素名称
            factor_counts[factor] = factor_counts.get(factor, 0) + 1

    sorted_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"factor": f, "count": c} for f, c in sorted_factors[:top_n]]


def _get_dispute_factor_distribution() -> Dict[str, int]:
    """获取争议因素分布。"""
    from services.dispute_prevention_service import dispute_prevention_service

    factor_counts = {}
    for record in dispute_prevention_service._risk_records.values():
        for factor in record.dispute_factors:
            factor_type = factor.factor_type.value
            factor_counts[factor_type] = factor_counts.get(factor_type, 0) + 1

    return factor_counts


def _calculate_composite_quality_score(prediction_stats: Dict, improvement_trend: Dict) -> float:
    """计算工人的综合质量得分。"""
    score = 0.5  # 基础分

    # 基于预测统计调整
    if prediction_stats.get("total_tasks", 0) > 0:
        avg_quality = prediction_stats.get("avg_quality", 0.5)
        score += avg_quality * 0.3

    # 基于改进趋势调整
    trend = improvement_trend.get("trend", "unknown")
    if trend == "improving":
        score += 0.1
    elif trend == "declining":
        score -= 0.1

    return round(min(1.0, max(0.0, score)), 3)
