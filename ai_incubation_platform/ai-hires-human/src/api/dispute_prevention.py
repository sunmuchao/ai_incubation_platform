"""
争议预防 API - 提供争议风险评估、预警和预防建议功能。

功能端点:
1. 风险评估：评估任务的争议风险
2. 风险查询：查询任务的争议风险记录
3. 风险预警：获取高风险任务预警列表
4. 结果记录：记录实际争议结果
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from services.dispute_prevention_service import (
    dispute_prevention_service,
    DisputePreventionRequest,
    DisputeRiskLevel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dispute-prevention", tags=["dispute_prevention"])


@router.post("/assess")
async def assess_dispute_risk(request: DisputePreventionRequest):
    """
    评估争议风险。

    在任务开始前或交付前，评估可能产生争议的风险，
    并提供预防建议以降低争议发生率。

    **请求参数**:
    - task_id: 任务 ID
    - employer_id: 雇主 ID
    - worker_id: 工人 ID
    - task_description: 任务描述
    - acceptance_criteria: 验收标准列表
    - reward_amount: 报酬金额
    - deadline_hours: 期限（小时）
    - worker_history: 工人历史信息（可选）
    - employer_history: 雇主历史信息（可选）

    **返回**:
    - risk_level: 风险等级 (low/medium/high/critical)
    - risk_score: 风险得分 (0-1)
    - dispute_factors: 争议因素列表
    - prevention_recommendations: 预防建议
    - early_warning: 是否需要早期预警
    """
    response = dispute_prevention_service.assess_dispute_risk(request)
    return {
        "success": response.success,
        "risk_id": response.risk_id,
        "risk_level": response.risk_level.value,
        "risk_score": response.risk_score,
        "dispute_factors": [
            {
                "factor_type": factor.factor_type.value,
                "description": factor.description,
                "risk_contribution": factor.risk_contribution,
                "evidence": factor.evidence,
            }
            for factor in response.dispute_factors
        ],
        "prevention_recommendations": response.prevention_recommendations,
        "early_warning": response.early_warning,
        "message": response.message,
    }


@router.get("/risk/{risk_id}")
async def get_risk_record(risk_id: str):
    """
    获取风险记录详情。

    返回指定风险 ID 的完整评估记录。
    """
    record = dispute_prevention_service.get_risk_record(risk_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Risk record not found: {risk_id}")

    return {
        "risk_id": record.risk_id,
        "task_id": record.task_id,
        "employer_id": record.employer_id,
        "worker_id": record.worker_id,
        "risk_level": record.risk_level.value,
        "risk_score": record.risk_score,
        "dispute_factors": [
            {
                "factor_type": factor.factor_type.value,
                "description": factor.description,
                "risk_contribution": factor.risk_contribution,
            }
            for factor in record.dispute_factors
        ],
        "prevention_recommendations": record.prevention_recommendations,
        "status": record.status,
        "actual_dispute_occurred": record.actual_dispute_occurred,
        "created_at": record.created_at.isoformat(),
    }


@router.get("/task/{task_id}/risk")
async def get_task_risk(task_id: str):
    """
    获取任务的争议风险。

    通过任务 ID 查询争议风险评估结果。
    """
    record = dispute_prevention_service.get_risk_by_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"No risk record found for task: {task_id}")

    return {
        "risk_id": record.risk_id,
        "task_id": record.task_id,
        "risk_level": record.risk_level.value,
        "risk_score": record.risk_score,
        "status": record.status,
        "early_warning_issued": record.risk_level in [DisputeRiskLevel.HIGH, DisputeRiskLevel.CRITICAL],
    }


@router.get("/warnings")
async def get_risk_warnings(
    min_risk_level: str = Query("high", description="最低风险等级 (high/critical)"),
    limit: int = Query(50, description="返回数量限制"),
):
    """
    获取高风险预警列表。

    返回所有达到指定风险等级的任务列表。
    """
    risk_level_map = {
        "high": DisputeRiskLevel.HIGH,
        "critical": DisputeRiskLevel.CRITICAL,
    }

    min_level = risk_level_map.get(min_risk_level.lower(), DisputeRiskLevel.HIGH)
    high_risk_tasks = dispute_prevention_service.get_high_risk_tasks(min_level)

    # 按风险得分降序排序
    high_risk_tasks.sort(key=lambda r: r.risk_score, reverse=True)

    return {
        "warnings": [
            {
                "risk_id": record.risk_id,
                "task_id": record.task_id,
                "employer_id": record.employer_id,
                "worker_id": record.worker_id,
                "risk_level": record.risk_level.value,
                "risk_score": record.risk_score,
                "status": record.status,
                "created_at": record.created_at.isoformat(),
            }
            for record in high_risk_tasks[:limit]
        ],
        "total": len(high_risk_tasks),
        "threshold": min_risk_level,
    }


@router.post("/risk/{risk_id}/outcome")
async def record_dispute_outcome(
    risk_id: str,
    dispute_occurred: bool = Query(..., description="是否发生争议"),
    dispute_reason: Optional[str] = Query(None, description="争议原因"),
):
    """
    记录实际争议结果。

    用于验证风险预测的准确性，并持续优化模型。
    """
    success = dispute_prevention_service.record_dispute_outcome(
        risk_id,
        dispute_occurred,
        dispute_reason,
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Risk record not found: {risk_id}")

    return {
        "message": "Dispute outcome recorded successfully",
        "risk_id": risk_id,
        "dispute_occurred": dispute_occurred,
    }


@router.get("/statistics")
async def get_risk_statistics():
    """
    获取争议风险统计信息。

    返回平台整体的争议风险评估统计。
    """
    stats = dispute_prevention_service.get_risk_statistics()
    return {"statistics": stats}


@router.get("/factors")
async def list_dispute_factors():
    """
    获取争议因素说明。

    返回所有争议因素类型的详细说明。
    """
    return {
        "factors": [
            {
                "type": "requirement_clarity",
                "name": "需求清晰度",
                "description": "任务描述和验收标准是否清晰、具体、可量化",
                "weight": 0.25,
                "risk_indicators": [
                    "任务描述过于简短",
                    "验收标准缺失或过于单一",
                    "缺少量化指标",
                    "使用过多主观性描述",
                ],
            },
            {
                "type": "payment_dispute",
                "name": "支付争议",
                "description": "报酬合理性及支付相关的潜在争议",
                "weight": 0.20,
                "risk_indicators": [
                    "报酬过低",
                    "报酬为零或负数",
                    "低于市场均价",
                ],
            },
            {
                "type": "deadline_pressure",
                "name": "期限压力",
                "description": "任务期限是否合理，是否存在时间压力",
                "weight": 0.15,
                "risk_indicators": [
                    "期限过于紧张",
                    "低于预期工时",
                ],
            },
            {
                "type": "quality_mismatch",
                "name": "质量不匹配",
                "description": "雇主期望与工人交付可能存在的质量差异",
                "weight": 0.15,
                "risk_indicators": [
                    "验收标准包含过多主观描述",
                    "缺少质量参考样例",
                ],
            },
            {
                "type": "communication",
                "name": "沟通风险",
                "description": "沟通渠道不明确导致的潜在争议",
                "weight": 0.15,
                "risk_indicators": [
                    "未明确沟通渠道",
                    "未指定响应时间要求",
                ],
            },
            {
                "type": "worker_history",
                "name": "工人历史",
                "description": "工人历史表现相关的风险",
                "weight": 0.05,
                "risk_indicators": [
                    "历史争议率较高",
                    "历史拒绝率较高",
                    "平均评分较低",
                ],
            },
            {
                "type": "employer_history",
                "name": "雇主历史",
                "description": "雇主历史表现相关的风险",
                "weight": 0.05,
                "risk_indicators": [
                    "雇主历史拒绝率较高",
                    "平均支付时间较长",
                    "雇主评分较低",
                ],
            },
        ]
    }


@router.get("/risk-levels")
async def list_risk_levels():
    """获取风险等级说明。"""
    return {
        "levels": [
            {
                "level": "low",
                "name": "低风险",
                "score_range": [0.0, 0.4],
                "description": "争议风险较低，可正常执行任务",
                "recommended_action": "无需特殊处理，按正常流程执行",
            },
            {
                "level": "medium",
                "name": "中风险",
                "score_range": [0.4, 0.7],
                "description": "存在一定争议风险，建议关注预防建议",
                "recommended_action": "参考预防建议，加强沟通确认",
            },
            {
                "level": "high",
                "name": "高风险",
                "score_range": [0.7, 0.85],
                "description": "争议风险较高，强烈建议采取预防措施",
                "recommended_action": "建议人工介入，增加检查节点",
            },
            {
                "level": "critical",
                "name": "极高风险",
                "score_range": [0.85, 1.0],
                "description": "争议风险极高，建议暂停任务并重新评估",
                "recommended_action": "建议暂停任务，重新设计任务要求或更换参与方",
            },
        ]
    }
