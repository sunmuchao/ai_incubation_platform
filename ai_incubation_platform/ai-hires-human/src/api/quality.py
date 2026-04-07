"""
质量控制 API - 提供黄金标准测试、可信度评估等功能。
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.worker_profile import TrustScoreResponse
from services.worker_profile_service import worker_profile_service
from services.quality_control_service import (
    quality_control_service,
    GoldStandardTest,
)
from services.task_service import task_service

router = APIRouter(prefix="/api/quality", tags=["quality"])


@router.post("/gold-tests")
async def create_gold_standard_test(
    task_id: str,
    expected_answer: str,
    weight: float = 1.0
):
    """
    创建黄金标准测试。

    黄金标准测试是预知答案的测试任务，用于：
    1. 评估工人可信度
    2. 自动筛选低质量交付
    3. 动态调整工人质量等级

    Args:
        task_id: 关联的任务 ID
        expected_answer: 预期答案
        weight: 测试权重 (默认 1.0)
    """
    test = quality_control_service.create_gold_standard_test(
        task_id=task_id,
        expected_answer=expected_answer,
        weight=weight
    )

    return {
        "message": "Gold standard test created",
        "test_id": test.test_id,
        "task_id": test.task_id,
        "weight": test.weight
    }


@router.post("/gold-tests/{test_id}/submit")
async def submit_gold_test_answer(
    test_id: str,
    worker_id: str,
    answer: str
):
    """
    提交黄金测试答案。

    系统会自动评估答案并更新工人可信度评分。
    """
    # 评估答案
    is_passed, score = quality_control_service.evaluate_gold_test_submission(
        worker_id=worker_id,
        test_id=test_id,
        submitted_answer=answer
    )

    # 分配测试给工人
    quality_control_service.assign_gold_test_to_worker(worker_id, test_id)

    # 更新工人可信度
    worker = worker_profile_service.get_profile(worker_id)
    if worker:
        new_trust_score = quality_control_service.update_worker_trust_score(
            worker=worker,
            gold_test_passed=is_passed
        )

    return {
        "test_id": test_id,
        "worker_id": worker_id,
        "passed": is_passed,
        "quality_score": round(score, 2),
        "new_trust_score": worker.trust_score if worker else None,
        "new_quality_tier": worker.quality_tier if worker else None
    }


@router.get("/workers/{worker_id}/gold-tests")
async def get_worker_gold_test_stats(worker_id: str):
    """获取工人黄金测试统计。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    stats = quality_control_service.get_worker_gold_test_stats(worker_id)

    return {
        **stats,
        "quality_tier": worker.quality_tier,
        "trust_score": worker.trust_score
    }


@router.get("/workers/{worker_id}/trust-score", response_model=TrustScoreResponse)
async def get_worker_trust_score(worker_id: str):
    """获取工人可信度评分。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    return TrustScoreResponse(
        worker_id=worker_id,
        trust_score=worker.trust_score,
        quality_tier=worker.quality_tier,
        gold_standard_passed=worker.gold_standard_tests_passed,
        gold_standard_total=worker.gold_standard_tests_total
    )


@router.post("/workers/{worker_id}/trust-score/recalculate")
async def recalculate_worker_trust_score(
    worker_id: str,
    task_outcome: Optional[bool] = None
):
    """
    重新计算工人可信度评分。

    Args:
        worker_id: 工人 ID
        task_outcome: 最新任务验收结果 (True=通过，False=拒绝)
    """
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    new_trust_score = quality_control_service.update_worker_trust_score(
        worker=worker,
        task_outcome=task_outcome
    )

    return {
        "worker_id": worker_id,
        "trust_score": new_trust_score,
        "quality_tier": worker.quality_tier,
        "fast_track_eligible": quality_control_service.should_fast_track(worker),
        "requires_manual_review": quality_control_service.requires_manual_review(worker)
    }


@router.get("/workers/{worker_id}/quality-status")
async def get_worker_quality_status(worker_id: str):
    """获取工人质量状态详情。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    gold_stats = quality_control_service.get_worker_gold_test_stats(worker_id)

    return {
        "worker_id": worker_id,
        "trust_score": worker.trust_score,
        "quality_tier": worker.quality_tier,
        "success_rate": worker.success_rate,
        "gold_test_stats": gold_stats,
        "fast_track_eligible": quality_control_service.should_fast_track(worker),
        "requires_manual_review": quality_control_service.requires_manual_review(worker),
        "quality_tier_progress": {
            "bronze": 0.0,
            "silver": 0.5,
            "gold": 0.75,
            "platinum": 0.9
        }
    }


@router.post("/tasks/{task_id}/quality-check")
async def check_task_delivery_quality(task_id: str, worker_id: str):
    """
    检查任务交付质量。

    返回质量评分、置信度等级和是否需要人工复核。
    """
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    result = quality_control_service.check_delivery_quality(task, worker)

    return {
        "task_id": task_id,
        "worker_id": worker_id,
        "quality_score": round(result.quality_score, 2),
        "confidence_level": result.confidence_level,
        "requires_manual_review": result.requires_manual_review,
        "check_details": result.check_details
    }


@router.post("/tasks/{task_id}/multi-validation")
async def create_multi_validation(task_id: str, num_workers: int = 3):
    """
    创建多重校验任务。

    将同一任务分发给多个工人，通过多数表决确定最终答案。
    适用于高价值或高不确定性任务。
    """
    result = quality_control_service.create_multi_validation(
        task_id=task_id,
        num_workers=num_workers
    )

    return {
        "message": "Multi-validation created",
        "task_id": task_id,
        "required_workers": num_workers,
        "validation_id": task_id  # 使用 task_id 作为 validation_id
    }


@router.post("/tasks/{task_id}/multi-validation/submit")
async def submit_multi_validation_answer(
    task_id: str,
    worker_id: str,
    answer: str
):
    """提交多重校验答案。"""
    result = quality_control_service.add_validation_submission(
        task_id=task_id,
        worker_id=worker_id,
        answer=answer
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Multi-validation not found for task: {task_id}"
        )

    return {
        "task_id": task_id,
        "submissions_count": len(result.submissions),
        "agreement_rate": round(result.agreement_rate, 2),
        "final_answer": result.final_answer,
        "consensus_reached": result.agreement_rate >= 0.67
    }


@router.get("/report")
async def get_quality_report():
    """获取质量报告。"""
    report = quality_control_service.get_quality_report()
    return report


@router.get("/tiers")
async def get_quality_tier_info():
    """获取质量等级说明。"""
    return {
        "tiers": {
            "bronze": {
                "min_score": 0.0,
                "description": "新工人或低可信度工人",
                "review_policy": "所有交付需人工复核"
            },
            "silver": {
                "min_score": 0.5,
                "description": "普通工人",
                "review_policy": "随机抽检"
            },
            "gold": {
                "min_score": 0.75,
                "description": "高可信度工人",
                "review_policy": "低抽检率"
            },
            "platinum": {
                "min_score": 0.9,
                "description": "精英工人",
                "review_policy": "快速通道，几乎免检"
            }
        }
    }
