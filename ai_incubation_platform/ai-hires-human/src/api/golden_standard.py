"""
黄金标准测试 API - 提供完整的测试创建、答题、认证管理等功能。

功能端点:
1. 测试管理：创建、查询、更新、停用黄金标准测试
2. 答题管理：开始答题、提交答案、查看结果
3. 认证管理：创建认证、查询认证、撤销认证
4. 统计分析：测试统计、工人测试历史
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.golden_standard_service import (
    GoldenStandardService,
    GoldenStandardTestCreate,
    Question,
    CertificationCreate,
)
from database import AsyncSessionLocal

router = APIRouter(prefix="/api/golden-standard", tags=["golden-standard"])


# ========== 请求/响应模型 ==========

class QuestionRequest(BaseModel):
    """题目请求模型。"""
    question_id: str
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    points: float = 1.0
    question_type: str = "multiple_choice"


class TestCreateRequest(BaseModel):
    """创建测试请求模型。"""
    task_id: str
    test_name: str
    test_description: str
    questions: List[QuestionRequest]
    test_type: str = "multiple_choice"
    passing_score: float = 80.0
    max_attempts: int = 3


class AttemptSubmitRequest(BaseModel):
    """提交答案请求模型。"""
    answers: Dict[str, str] = Field(..., description="答案字典，key 为 question_id，value 为答案")


# ========== 辅助函数 ==========

def create_service() -> GoldenStandardService:
    """创建服务实例（同步包装器）。"""
    return GoldenStandardService(AsyncSessionLocal())


# ========== 测试管理端点 ==========

@router.post("/tests", response_model=Dict)
async def create_test(request: TestCreateRequest, ai_employer_id: str = Query(..., description="AI 雇主 ID")):
    """
    创建黄金标准测试。

    黄金标准测试是预知答案的测试，用于：
    1. 筛选合格的工人
    2. 评估工人能力
    3. 作为任务验收的参考

    **题目类型支持**:
    - multiple_choice: 选择题
    - boolean: 判断题
    - scale: 评分题 (1-5 分)
    - text_match: 文本匹配题

    **示例**:
    ```json
    {
        "ai_employer_id": "agent_001",
        "task_id": "task_123",
        "test_name": "数据标注质量测试",
        "test_description": "测试工人是否能正确标注数据",
        "questions": [
            {
                "question_id": "q1",
                "question": "这张图片中是否有行人？",
                "options": ["是", "否", "不确定"],
                "correct_answer": "是",
                "points": 1.0,
                "question_type": "multiple_choice"
            }
        ],
        "test_type": "multiple_choice",
        "passing_score": 80.0,
        "max_attempts": 3
    }
    ```
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        # 转换题目格式
        questions = [
            Question(
                question_id=q.question_id,
                question=q.question,
                options=q.options,
                correct_answer=q.correct_answer,
                points=q.points,
                question_type=q.question_type
            )
            for q in request.questions
        ]

        test_data = GoldenStandardTestCreate(
            task_id=request.task_id,
            test_name=request.test_name,
            test_description=request.test_description,
            questions=questions,
            test_type=request.test_type,
            passing_score=request.passing_score,
            max_attempts=request.max_attempts
        )

        test = await service.create_test(ai_employer_id, test_data)

        return {
            "message": "Golden standard test created successfully",
            "test": {
                "test_id": test.test_id,
                "task_id": test.task_id,
                "test_name": test.test_name,
                "test_description": test.test_description,
                "test_type": test.test_type,
                "passing_score": test.passing_score,
                "max_attempts": test.max_attempts,
                "question_count": len(test.questions),
                "is_active": test.is_active,
                "created_at": test.created_at.isoformat()
            }
        }
    finally:
        await db.close()


@router.get("/tests/{test_id}", response_model=Dict)
async def get_test(test_id: str):
    """
    获取测试详情。

    返回测试的完整信息，包括题目列表（不含正确答案）。
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        test = await service.get_test(test_id)
        if not test:
            raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")

        # 移除正确答案后返回题目
        questions_without_answers = []
        for q in test.questions:
            q_copy = {k: v for k, v in q.items() if k != "correct_answer"}
            questions_without_answers.append(q_copy)

        return {
            "test": {
                "test_id": test.test_id,
                "task_id": test.task_id,
                "ai_employer_id": test.ai_employer_id,
                "test_name": test.test_name,
                "test_description": test.test_description,
                "test_type": test.test_type,
                "passing_score": test.passing_score,
                "max_attempts": test.max_attempts,
                "is_active": test.is_active,
                "questions": questions_without_answers,
                "created_at": test.created_at.isoformat(),
                "updated_at": test.updated_at.isoformat()
            }
        }
    finally:
        await db.close()


@router.get("/tasks/{task_id}/tests", response_model=Dict)
async def get_tests_by_task(task_id: str):
    """
    获取任务相关的所有测试。

    返回任务下所有激活的黄金标准测试列表。
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)
        tests = await service.get_tests_by_task(task_id)

        return {
            "task_id": task_id,
            "tests": [
                {
                    "test_id": t.test_id,
                    "test_name": t.test_name,
                    "test_type": t.test_type,
                    "passing_score": t.passing_score,
                    "max_attempts": t.max_attempts,
                    "question_count": len(t.questions),
                    "is_active": t.is_active,
                    "created_at": t.created_at.isoformat()
                }
                for t in tests
            ]
        }
    finally:
        await db.close()


@router.post("/tests/{test_id}/deactivate", response_model=Dict)
async def deactivate_test(test_id: str):
    """
    停用测试。

    停用后的测试不再接受新的答题尝试，但历史记录保留。
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        success = await service.deactivate_test(test_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")

        return {
            "message": "Test deactivated successfully",
            "test_id": test_id
        }
    finally:
        await db.close()


@router.get("/tests/{test_id}/statistics", response_model=Dict)
async def get_test_statistics(test_id: str):
    """
    获取测试统计信息。

    返回测试的答题统计，包括：
    - 总尝试次数
    - 完成次数
    - 通过次数
    - 通过率
    - 平均分
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        stats = await service.get_test_statistics(test_id)
        if not stats:
            raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")

        return {"statistics": stats}
    finally:
        await db.close()


# ========== 答题管理端点 ==========

@router.post("/tests/{test_id}/attempts/start", response_model=Dict)
async def start_attempt(
    test_id: str,
    worker_id: str = Query(..., description="工人 ID"),
    task_id: Optional[str] = Query(None, description="关联任务 ID")
):
    """
    开始答题尝试。

    工人开始一个测试前，必须先调用此接口创建答题记录。
    系统会检查是否超过最大尝试次数。

    **注意**:
    - 每个测试有最大尝试次数限制
    - 超过限制后无法再开始新的尝试
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        # 检查测试是否存在
        test = await service.get_test(test_id)
        if not test:
            raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")

        if not test.is_active:
            raise HTTPException(status_code=400, detail="Test is no longer active")

        # 获取关联任务 ID（如果未提供）
        if not task_id:
            task_id = test.task_id

        attempt = await service.start_attempt(test_id, worker_id, task_id)
        if not attempt:
            raise HTTPException(
                status_code=400,
                detail="Failed to start attempt (may have reached max attempts)"
            )

        # 返回题目（不含正确答案）
        test_detail = await service.get_test(test_id)
        questions = []
        for q in test_detail.questions:
            q_copy = {k: v for k, v in q.items() if k != "correct_answer"}
            questions.append(q_copy)

        return {
            "message": "Attempt started successfully",
            "attempt": {
                "attempt_id": attempt.attempt_id,
                "test_id": attempt.test_id,
                "worker_id": attempt.worker_id,
                "task_id": attempt.task_id,
                "attempt_number": attempt.attempt_number,
                "questions": questions,
                "started_at": attempt.started_at.isoformat()
            }
        }
    finally:
        await db.close()


@router.post("/attempts/{attempt_id}/submit", response_model=Dict)
async def submit_attempt(attempt_id: str, request: AttemptSubmitRequest):
    """
    提交答题答案。

    提交后系统会自动评分，并返回结果。

    **答案格式**:
    ```json
    {
        "answers": {
            "q1": "a",
            "q2": "是",
            "q3": "4"
        }
    }
    ```
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        result = await service.submit_answers(attempt_id, request.answers)
        if not result:
            raise HTTPException(status_code=404, detail=f"Attempt not found: {attempt_id}")

        return {
            "message": "Answers submitted successfully",
            "result": {
                "attempt_id": result.attempt_id,
                "test_id": result.test_id,
                "worker_id": result.worker_id,
                "score": result.score,
                "max_score": result.max_score,
                "percentage": result.percentage,
                "passed": result.passed,
                "answers": result.answers,
                "completed_at": result.completed_at.isoformat()
            }
        }
    finally:
        await db.close()


@router.get("/attempts/{attempt_id}", response_model=Dict)
async def get_attempt(attempt_id: str):
    """
    获取答题尝试详情。

    返回答题的完整信息，包括答案和评分结果。
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        attempt = await service.get_attempt(attempt_id)
        if not attempt:
            raise HTTPException(status_code=404, detail=f"Attempt not found: {attempt_id}")

        return {
            "attempt": {
                "attempt_id": attempt.attempt_id,
                "test_id": attempt.test_id,
                "worker_id": attempt.worker_id,
                "task_id": attempt.task_id,
                "attempt_number": attempt.attempt_number,
                "answers": attempt.answers,
                "score": attempt.score,
                "max_score": attempt.max_score,
                "percentage": attempt.percentage,
                "passed": attempt.passed,
                "started_at": attempt.started_at.isoformat(),
                "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None
            }
        }
    finally:
        await db.close()


@router.get("/workers/{worker_id}/attempts", response_model=Dict)
async def get_worker_attempts(worker_id: str, test_id: Optional[str] = None):
    """
    获取工人的答题历史。

    可选择性地按测试 ID 筛选。
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        attempts = await service.get_worker_attempts(worker_id, test_id)

        history = []
        for attempt in attempts:
            test = await service.get_test(attempt.test_id)
            history.append({
                "attempt_id": attempt.attempt_id,
                "test_id": attempt.test_id,
                "test_name": test.test_name if test else "Unknown",
                "attempt_number": attempt.attempt_number,
                "score": attempt.score,
                "max_score": attempt.max_score,
                "percentage": attempt.percentage,
                "passed": attempt.passed,
                "started_at": attempt.started_at.isoformat(),
                "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None
            })

        return {
            "worker_id": worker_id,
            "test_id": test_id,
            "total_attempts": len(history),
            "attempts": history
        }
    finally:
        await db.close()


# ========== 认证管理端点 ==========

@router.post("/certifications", response_model=Dict)
async def create_certification(
    worker_id: str,
    certification_type: str,
    certification_name: str,
    certification_level: str = "bronze"
):
    """
    创建工人认证。

    认证用于标识工人具备特定技能或资质。

    **认证等级**:
    - bronze: 青铜级（入门）
    - silver: 白银级（熟练）
    - gold: 黄金级（专家）
    - diamond: 钻石级（顶尖）

    **认证类型示例**:
    - data_annotation: 数据标注
    - content_moderation: 内容审核
    - translation: 翻译
    - survey: 问卷调查
    - transcription: 转录
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        cert_data = CertificationCreate(
            worker_id=worker_id,
            certification_type=certification_type,
            certification_name=certification_name,
            certification_level=certification_level
        )

        cert = await service.create_certification(cert_data)

        return {
            "message": "Certification created successfully",
            "certification": {
                "certification_id": cert.certification_id,
                "worker_id": cert.worker_id,
                "certification_type": cert.certification_type,
                "certification_name": cert.certification_name,
                "certification_level": cert.certification_level,
                "status": cert.status,
                "issued_at": cert.issued_at.isoformat()
            }
        }
    finally:
        await db.close()


@router.get("/workers/{worker_id}/certifications", response_model=Dict)
async def get_worker_certifications(worker_id: str):
    """
    获取工人的所有认证。

    返回工人拥有的所有认证（包括已过期和已撤销的）。
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        certifications = await service.get_worker_certifications(worker_id)

        return {
            "worker_id": worker_id,
            "total_certifications": len(certifications),
            "active_certifications": sum(1 for c in certifications if c.status == "active"),
            "certifications": [
                {
                    "certification_id": c.certification_id,
                    "certification_type": c.certification_type,
                    "certification_name": c.certification_name,
                    "certification_level": c.certification_level,
                    "status": c.status,
                    "score": c.score,
                    "issued_at": c.issued_at.isoformat(),
                    "expires_at": c.expires_at.isoformat() if c.expires_at else None
                }
                for c in certifications
            ]
        }
    finally:
        await db.close()


@router.get("/certifications/{certification_id}", response_model=Dict)
async def get_certification(certification_id: str):
    """获取认证详情。"""
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        cert = await service.get_certification(certification_id)
        if not cert:
            raise HTTPException(status_code=404, detail=f"Certification not found: {certification_id}")

        return {
            "certification": {
                "certification_id": cert.certification_id,
                "worker_id": cert.worker_id,
                "certification_type": cert.certification_type,
                "certification_name": cert.certification_name,
                "certification_level": cert.certification_level,
                "status": cert.status,
                "score": cert.score,
                "issued_at": cert.issued_at.isoformat(),
                "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,
                "cert_data": cert.cert_data
            }
        }
    finally:
        await db.close()


@router.post("/certifications/{certification_id}/revoke", response_model=Dict)
async def revoke_certification(certification_id: str, reason: str = Query(..., description="撤销原因")):
    """
    撤销认证。

    撤销后的认证状态变为 revoked，无法恢复。
    需要提供撤销原因，记录在案。
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        success = await service.revoke_certification(certification_id, reason)
        if not success:
            raise HTTPException(status_code=404, detail=f"Certification not found: {certification_id}")

        return {
            "message": "Certification revoked successfully",
            "certification_id": certification_id,
            "reason": reason
        }
    finally:
        await db.close()


@router.post("/certifications/{certification_id}/update-status", response_model=Dict)
async def update_certification_status(certification_id: str, status: str = Query(..., description="新状态")):
    """
    更新认证状态。

    可用于手动过期认证或恢复认证。
    """
    if status not in ["active", "expired", "revoked"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be one of: active, expired, revoked"
        )

    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        success = await service.update_certification_status(certification_id, status)
        if not success:
            raise HTTPException(status_code=404, detail=f"Certification not found: {certification_id}")

        return {
            "message": "Certification status updated",
            "certification_id": certification_id,
            "new_status": status
        }
    finally:
        await db.close()


# ========== 历史记录端点 ==========

@router.get("/workers/{worker_id}/test-history", response_model=Dict)
async def get_worker_test_history(worker_id: str):
    """
    获取工人的完整测试历史。

    返回工人所有测试尝试的详细记录。
    """
    db = AsyncSessionLocal()
    try:
        service = GoldenStandardService(db)

        history = await service.get_worker_test_history(worker_id)

        passed_count = sum(1 for h in history if h.get("passed"))
        total_completed = sum(1 for h in history if h.get("completed_at"))

        return {
            "worker_id": worker_id,
            "summary": {
                "total_tests": len(history),
                "completed_tests": total_completed,
                "passed_tests": passed_count,
                "overall_pass_rate": passed_count / total_completed if total_completed > 0 else 0.0
            },
            "history": history
        }
    finally:
        await db.close()