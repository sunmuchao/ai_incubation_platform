"""
黄金标准测试服务 (Golden Standard Test Service)。

功能：
1. 创建和管理黄金标准测试（预知答案的测试题）
2. 工人答题和自动评分
3. 测试嵌入任务流程
4. 工人认证管理

核心机制：
- 雇主在发布任务时可创建黄金标准测试
- 工人接单前/后需要完成测试
- 自动评分并判定是否通过
- 测试成绩影响工人信誉和任务验收
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import (
    GoldenStandardTestDB,
    WorkerTestAttemptDB,
    WorkerCertificationDB,
    TaskDB,
)

logger = logging.getLogger(__name__)


class TestType(str, Enum):
    """测试类型枚举。"""
    MULTIPLE_CHOICE = "multiple_choice"
    BOOLEAN = "boolean"
    SCALE = "scale"
    TEXT_MATCH = "text_match"


class CertificationLevel(str, Enum):
    """认证等级枚举。"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    DIAMOND = "diamond"


class CertificationStatus(str, Enum):
    """认证状态枚举。"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Question(BaseModel):
    """测试题目模型。"""
    question_id: str
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    points: float = 1.0
    question_type: str = "multiple_choice"


class GoldenStandardTestCreate(BaseModel):
    """创建黄金标准测试请求模型。"""
    task_id: str
    test_name: str
    test_description: str
    questions: List[Question]
    test_type: str = "multiple_choice"
    passing_score: float = 80.0
    max_attempts: int = 3


class TestAttemptResult(BaseModel):
    """测试尝试结果模型。"""
    attempt_id: str
    test_id: str
    worker_id: str
    score: float
    max_score: float
    percentage: float
    passed: bool
    answers: Dict[str, str]
    completed_at: datetime


class CertificationCreate(BaseModel):
    """创建认证请求模型。"""
    worker_id: str
    certification_type: str
    certification_name: str
    certification_level: str = "bronze"


class GoldenStandardService:
    """
    黄金标准测试服务。

    核心能力：
    1. 黄金标准测试 CRUD
    2. 工人答题和自动评分
    3. 认证管理
    4. 测试统计分析
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ========== 黄金标准测试管理 ==========

    async def create_test(
        self,
        ai_employer_id: str,
        test_data: GoldenStandardTestCreate
    ) -> GoldenStandardTestDB:
        """创建黄金标准测试。"""
        test_id = f"gst_{uuid.uuid4().hex[:20]}"
        record_id = uuid.uuid4().hex  # 用于主键 id

        # 将问题转换为 JSON 格式
        questions_json = [q.model_dump() for q in test_data.questions]

        test = GoldenStandardTestDB(
            id=record_id,
            test_id=test_id,
            task_id=test_data.task_id,
            ai_employer_id=ai_employer_id,
            test_name=test_data.test_name,
            test_description=test_data.test_description,
            test_type=test_data.test_type,
            questions=questions_json,
            passing_score=test_data.passing_score,
            max_attempts=test_data.max_attempts,
            is_active=True
        )

        self.db.add(test)
        await self.db.commit()
        await self.db.refresh(test)

        logger.info(
            "Created golden standard test: %s for task %s by employer %s",
            test_id, test_data.task_id, ai_employer_id
        )
        return test

    async def get_test(self, test_id: str) -> Optional[GoldenStandardTestDB]:
        """获取测试详情。"""
        result = await self.db.execute(
            select(GoldenStandardTestDB).where(GoldenStandardTestDB.test_id == test_id)
        )
        return result.scalar_one_or_none()

    async def get_tests_by_task(self, task_id: str) -> List[GoldenStandardTestDB]:
        """获取任务相关的所有测试。"""
        result = await self.db.execute(
            select(GoldenStandardTestDB)
            .where(GoldenStandardTestDB.task_id == task_id)
            .where(GoldenStandardTestDB.is_active == True)
        )
        return list(result.scalars().all())

    async def update_test(
        self,
        test_id: str,
        updates: Dict
    ) -> Optional[GoldenStandardTestDB]:
        """更新测试配置。"""
        test = await self.get_test(test_id)
        if not test:
            return None

        for key, value in updates.items():
            if hasattr(test, key):
                setattr(test, key, value)

        await self.db.commit()
        await self.db.refresh(test)
        return test

    async def deactivate_test(self, test_id: str) -> bool:
        """停用测试。"""
        test = await self.get_test(test_id)
        if not test:
            return False

        test.is_active = False
        await self.db.commit()
        logger.info("Deactivated golden standard test: %s", test_id)
        return True

    # ========== 答题管理 ==========

    async def start_attempt(
        self,
        test_id: str,
        worker_id: str,
        task_id: str
    ) -> Optional[WorkerTestAttemptDB]:
        """开始一次答题尝试。"""
        # 检查测试是否存在
        test = await self.get_test(test_id)
        if not test:
            logger.warning("Test not found: %s", test_id)
            return None

        # 检查工人是否已达到最大尝试次数
        existing_attempts = await self.get_worker_attempts(worker_id, test_id)
        if len(existing_attempts) >= test.max_attempts:
            logger.warning(
                "Worker %s has reached max attempts (%d) for test %s",
                worker_id, test.max_attempts, test_id
            )
            return None

        # 创建新的尝试记录
        attempt_id = f"att_{uuid.uuid4().hex[:20]}"
        record_id = uuid.uuid4().hex  # 用于主键 id
        attempt_number = len(existing_attempts) + 1

        attempt = WorkerTestAttemptDB(
            id=record_id,
            attempt_id=attempt_id,
            test_id=test_id,
            task_id=task_id,
            worker_id=worker_id,
            attempt_number=attempt_number,
            answers={},
            score=0.0,
            max_score=100.0,
            percentage=0.0,
            passed=False
        )

        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)

        logger.info(
            "Started test attempt: %s for worker %s on test %s (attempt #%d)",
            attempt_id, worker_id, test_id, attempt_number
        )
        return attempt

    async def submit_answers(
        self,
        attempt_id: str,
        answers: Dict[str, str]
    ) -> Optional[TestAttemptResult]:
        """提交答案并自动评分。"""
        # 获取尝试记录
        result = await self.db.execute(
            select(WorkerTestAttemptDB).where(WorkerTestAttemptDB.attempt_id == attempt_id)
        )
        attempt = result.scalar_one_or_none()

        if not attempt:
            logger.warning("Attempt not found: %s", attempt_id)
            return None

        # 获取测试题目
        test = await self.get_test(attempt.test_id)
        if not test:
            logger.warning("Test not found for attempt: %s", attempt_id)
            return None

        # 评分
        score, max_score, percentage = self._grade_answers(
            answers, test.questions
        )

        # 更新尝试记录
        attempt.answers = answers
        attempt.score = score
        attempt.max_score = max_score
        attempt.percentage = percentage
        attempt.passed = percentage >= test.passing_score
        attempt.completed_at = datetime.now()

        await self.db.commit()
        await self.db.refresh(attempt)

        logger.info(
            "Submitted test answers: attempt=%s, score=%.1f/%.1f (%.1f%%), passed=%s",
            attempt_id, score, max_score, percentage, attempt.passed
        )

        return TestAttemptResult(
            attempt_id=attempt.attempt_id,
            test_id=attempt.test_id,
            worker_id=attempt.worker_id,
            score=attempt.score,
            max_score=attempt.max_score,
            percentage=attempt.percentage,
            passed=attempt.passed,
            answers=attempt.answers,
            completed_at=attempt.completed_at
        )

    def _grade_answers(
        self,
        answers: Dict[str, str],
        questions: List[Dict]
    ) -> Tuple[float, float, float]:
        """
        评分答案。

        Returns:
            (得分，满分，百分比)
        """
        score = 0.0
        max_score = 0.0

        # 构建问题映射
        question_map = {q["question_id"]: q for q in questions}

        for question_id, answer in answers.items():
            question = question_map.get(question_id)
            if not question:
                continue

            correct_answer = question.get("correct_answer", "")
            points = question.get("points", 1.0)
            max_score += points

            # 根据题型判断答案是否正确
            question_type = question.get("question_type", "multiple_choice")

            if question_type == "text_match":
                # 文本匹配：不区分大小写的精确匹配
                if answer.lower().strip() == correct_answer.lower().strip():
                    score += points
            else:
                # 其他题型：精确匹配
                if answer == correct_answer:
                    score += points

        percentage = (score / max_score * 100) if max_score > 0 else 0.0
        return score, max_score, percentage

    async def get_worker_attempts(
        self,
        worker_id: str,
        test_id: Optional[str] = None
    ) -> List[WorkerTestAttemptDB]:
        """获取工人的答题尝试记录。"""
        query = select(WorkerTestAttemptDB).where(WorkerTestAttemptDB.worker_id == worker_id)
        if test_id:
            query = query.where(WorkerTestAttemptDB.test_id == test_id)
        query = query.order_by(WorkerTestAttemptDB.started_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_attempt(self, attempt_id: str) -> Optional[WorkerTestAttemptDB]:
        """获取答题尝试详情。"""
        result = await self.db.execute(
            select(WorkerTestAttemptDB).where(WorkerTestAttemptDB.attempt_id == attempt_id)
        )
        return result.scalar_one_or_none()

    # ========== 认证管理 ==========

    async def create_certification(
        self,
        certification_data: CertificationCreate
    ) -> WorkerCertificationDB:
        """创建工人认证。"""
        certification_id = f"cert_{uuid.uuid4().hex[:20]}"
        record_id = uuid.uuid4().hex  # 用于主键 id

        certification = WorkerCertificationDB(
            id=record_id,
            certification_id=certification_id,
            worker_id=certification_data.worker_id,
            certification_type=certification_data.certification_type,
            certification_name=certification_data.certification_name,
            certification_level=certification_data.certification_level,
            status="active"
        )

        self.db.add(certification)
        await self.db.commit()
        await self.db.refresh(certification)

        logger.info(
            "Created certification: %s for worker %s (%s - %s)",
            certification_id, certification_data.worker_id,
            certification_data.certification_type, certification_data.certification_level
        )
        return certification

    async def get_worker_certifications(
        self,
        worker_id: str
    ) -> List[WorkerCertificationDB]:
        """获取工人的所有认证。"""
        result = await self.db.execute(
            select(WorkerCertificationDB)
            .where(WorkerCertificationDB.worker_id == worker_id)
            .order_by(WorkerCertificationDB.issued_at.desc())
        )
        return list(result.scalars().all())

    async def get_certification(
        self,
        certification_id: str
    ) -> Optional[WorkerCertificationDB]:
        """获取认证详情。"""
        result = await self.db.execute(
            select(WorkerCertificationDB)
            .where(WorkerCertificationDB.certification_id == certification_id)
        )
        return result.scalar_one_or_none()

    async def update_certification_status(
        self,
        certification_id: str,
        status: str
    ) -> bool:
        """更新认证状态。"""
        certification = await self.get_certification(certification_id)
        if not certification:
            return False

        certification.status = status
        await self.db.commit()
        logger.info("Updated certification status: %s -> %s", certification_id, status)
        return True

    async def revoke_certification(
        self,
        certification_id: str,
        reason: str
    ) -> bool:
        """撤销认证。"""
        certification = await self.get_certification(certification_id)
        if not certification:
            return False

        certification.status = "revoked"
        if certification.cert_data is None:
            certification.cert_data = {}
        certification.cert_data["revoked_reason"] = reason
        certification.cert_data["revoked_at"] = datetime.now().isoformat()

        await self.db.commit()
        logger.info("Revoked certification: %s, reason: %s", certification_id, reason)
        return True

    # ========== 统计分析 ==========

    async def get_test_statistics(self, test_id: str) -> Dict:
        """获取测试统计信息。"""
        test = await self.get_test(test_id)
        if not test:
            return {}

        # 获取所有尝试
        result = await self.db.execute(
            select(WorkerTestAttemptDB)
            .where(WorkerTestAttemptDB.test_id == test_id)
        )
        attempts = list(result.scalars().all())

        # 计算统计
        total_attempts = len(attempts)
        completed_attempts = [a for a in attempts if a.completed_at]
        passed_attempts = [a for a in completed_attempts if a.passed]

        avg_score = (
            sum(a.percentage for a in completed_attempts) / len(completed_attempts)
            if completed_attempts else 0.0
        )

        return {
            "test_id": test_id,
            "test_name": test.test_name,
            "total_attempts": total_attempts,
            "completed_attempts": len(completed_attempts),
            "passed_attempts": len(passed_attempts),
            "pass_rate": len(passed_attempts) / len(completed_attempts) if completed_attempts else 0.0,
            "average_score": avg_score
        }

    async def get_worker_test_history(self, worker_id: str) -> List[Dict]:
        """获取工人的测试历史。"""
        attempts = await self.get_worker_attempts(worker_id)

        history = []
        for attempt in attempts:
            test = await self.get_test(attempt.test_id)
            history.append({
                "attempt_id": attempt.attempt_id,
                "test_id": attempt.test_id,
                "test_name": test.test_name if test else "Unknown",
                "attempt_number": attempt.attempt_number,
                "score": attempt.score,
                "max_score": attempt.max_score,
                "percentage": attempt.percentage,
                "passed": attempt.passed,
                "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None
            })

        return history

    async def reset_state(self) -> None:
        """重置状态（用于测试）。"""
        logger.info("GoldenStandardService state reset (test mode only)")
