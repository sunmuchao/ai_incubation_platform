"""
质量控制服务 - 提供自动化质量验证机制。

功能：
1. 黄金标准测试（预知答案的测试任务）
2. 多重校验（同一任务分发给多个工人）
3. 置信度评估（自动评估交付质量）
4. 工人可信度动态评分

核心机制：
- 随机插入黄金任务到工人工作流
- 根据黄金任务表现调整工人可信度
- 低可信度工人的交付自动进入人工复核
- 高可信度工人享受快速通道
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
from collections import Counter

from pydantic import BaseModel, Field

from models.task import Task, TaskStatus
from models.worker_profile import WorkerProfile

logger = logging.getLogger(__name__)


class QualityTier(str, Enum):
    """质量等级枚举。"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class GoldStandardTest(BaseModel):
    """黄金标准测试任务。"""
    test_id: str
    task_id: str  # 关联的实际任务 ID
    expected_answer: str  # 预期答案
    weight: float = 1.0  # 测试权重
    is_passed: Optional[bool] = None  # 是否通过
    submitted_answer: Optional[str] = None  # 工人提交的答案
    created_at: datetime = Field(default_factory=datetime.now)


class QualityCheckResult(BaseModel):
    """质量检查结果。"""
    task_id: str
    worker_id: str
    quality_score: float  # 质量分数 (0-1)
    confidence_level: str  # low, medium, high
    requires_manual_review: bool
    check_details: Dict = Field(default_factory=dict)


class MultiValidationResult(BaseModel):
    """多重校验结果。"""
    task_id: str
    submissions: List[Dict] = Field(default_factory=list)
    agreement_rate: float  # 一致性比率
    final_answer: Optional[str]  # 最终采纳的答案
    confidence: float  # 置信度


class QualityControlService:
    """
    质量控制服务。

    核心能力：
    1. 黄金标准测试管理
    2. 工人可信度评估
    3. 交付质量自动检查
    4. 多重校验（多数表决）
    """

    def __init__(self) -> None:
        # 黄金标准测试库
        self._gold_tests: Dict[str, GoldStandardTest] = {}
        # 工人 - 黄金测试映射
        self._worker_test_assignments: Dict[str, List[str]] = {}
        # 任务多重校验记录
        self._multi_validations: Dict[str, MultiValidationResult] = {}

        # 配置参数
        self.GOLD_TEST_RATIO = 0.1  # 黄金任务占比 (10%)
        self.MIN_TRUST_FOR_FAST_TRACK = 0.8  # 快速通道最低可信度
        self.AUTO_REJECT_TRUST_THRESHOLD = 0.3  # 自动拒绝的低可信度阈值
        self.MULTI_VALIDATION_WORKERS = 3  # 多重校验的工人数量
        self.AGREEMENT_THRESHOLD = 0.67  # 一致性阈值 (2/3)

    # ========== 黄金标准测试管理 ==========

    def create_gold_standard_test(
        self,
        task_id: str,
        expected_answer: str,
        weight: float = 1.0
    ) -> GoldStandardTest:
        """创建黄金标准测试。"""
        test_id = f"gold_{hashlib.sha256(task_id.encode()).hexdigest()[:12]}"
        test = GoldStandardTest(
            test_id=test_id,
            task_id=task_id,
            expected_answer=expected_answer,
            weight=weight
        )
        self._gold_tests[test_id] = test
        logger.info("Created gold standard test: %s for task %s", test_id, task_id)
        return test

    def assign_gold_test_to_worker(
        self,
        worker_id: str,
        test_id: str
    ) -> bool:
        """分配黄金测试给工人。"""
        if test_id not in self._gold_tests:
            return False

        if worker_id not in self._worker_test_assignments:
            self._worker_test_assignments[worker_id] = []

        self._worker_test_assignments[worker_id].append(test_id)
        return True

    def evaluate_gold_test_submission(
        self,
        worker_id: str,
        test_id: str,
        submitted_answer: str
    ) -> Tuple[bool, float]:
        """
        评估工人提交的黄金测试答案。
        返回 (是否通过，质量分数)
        """
        test = self._gold_tests.get(test_id)
        if not test:
            logger.warning("Gold test not found: %s", test_id)
            return False, 0.0

        # 计算答案相似度
        quality_score = self._calculate_answer_similarity(
            test.expected_answer,
            submitted_answer
        )

        is_passed = quality_score >= 0.8  # 80% 相似度阈值
        test.is_passed = is_passed
        test.submitted_answer = submitted_answer

        logger.info(
            "Gold test evaluation: test=%s, worker=%s, passed=%s, score=%.2f",
            test_id, worker_id, is_passed, quality_score
        )

        return is_passed, quality_score

    def _calculate_answer_similarity(self, expected: str, actual: str) -> float:
        """计算答案相似度（简化版，基于文本匹配）。"""
        if not expected or not actual:
            return 0.0

        # 归一化处理
        expected_norm = expected.lower().strip()
        actual_norm = actual.lower().strip()

        # 完全匹配
        if expected_norm == actual_norm:
            return 1.0

        # 基于词组的相似度
        expected_tokens = set(expected_norm.split())
        actual_tokens = set(actual_norm.split())

        if not expected_tokens or not actual_tokens:
            return 0.0

        intersection = len(expected_tokens & actual_tokens)
        union = len(expected_tokens | actual_tokens)

        return intersection / union if union > 0 else 0.0

    def get_worker_gold_test_stats(
        self,
        worker_id: str
    ) -> Dict:
        """获取工人黄金测试统计。"""
        test_ids = self._worker_test_assignments.get(worker_id, [])
        tests = [self._gold_tests[tid] for tid in test_ids if tid in self._gold_tests]

        passed = sum(1 for t in tests if t.is_passed)
        total = len(tests)

        return {
            "worker_id": worker_id,
            "tests_taken": total,
            "tests_passed": passed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "average_score": sum(
                self._calculate_answer_similarity(t.expected_answer, t.submitted_answer or "")
                for t in tests
            ) / total if total > 0 else 0.0
        }

    # ========== 工人可信度评估 ==========

    def update_worker_trust_score(
        self,
        worker: WorkerProfile,
        gold_test_passed: Optional[bool] = None,
        task_outcome: Optional[bool] = None
    ) -> float:
        """
        更新工人可信度评分。

        Args:
            worker: 工人画像
            gold_test_passed: 黄金测试是否通过 (None 表示无新测试结果)
            task_outcome: 任务验收结果 (True=通过，False=拒绝，None 表示无新结果)

        Returns:
            更新后的可信度评分
        """
        # 获取黄金测试统计
        gold_stats = self.get_worker_gold_test_stats(worker.worker_id)

        # 更新黄金测试计数
        if gold_test_passed is not None:
            worker.gold_standard_tests_total += 1
            if gold_test_passed:
                worker.gold_standard_tests_passed += 1

        # 计算黄金测试可信度 (0-0.5)
        if worker.gold_standard_tests_total > 0:
            gold_trust = (worker.gold_standard_tests_passed / worker.gold_standard_tests_total) * 0.5
        else:
            gold_trust = 0.25  # 默认基础分

        # 计算历史表现可信度 (0-0.5)
        history_trust = worker.success_rate * 0.5

        # 综合可信度
        new_trust_score = gold_trust + history_trust
        worker.trust_score = min(1.0, max(0.0, new_trust_score))

        # 更新质量等级
        self._update_quality_tier(worker)

        logger.info(
            "Updated trust score for worker %s: %.2f (gold=%.2f, history=%.2f)",
            worker.worker_id, worker.trust_score, gold_trust, history_trust
        )

        return worker.trust_score

    def _update_quality_tier(self, worker: WorkerProfile) -> str:
        """更新工人质量等级。"""
        score = worker.trust_score

        if score >= 0.9:
            worker.quality_tier = QualityTier.PLATINUM.value
        elif score >= 0.75:
            worker.quality_tier = QualityTier.GOLD.value
        elif score >= 0.5:
            worker.quality_tier = QualityTier.SILVER.value
        else:
            worker.quality_tier = QualityTier.BRONZE.value

        return worker.quality_tier

    def should_fast_track(self, worker: WorkerProfile) -> bool:
        """判断工人是否可享受快速通道（免检或抽检）。"""
        return worker.trust_score >= self.MIN_TRUST_FOR_FAST_TRACK

    def requires_manual_review(self, worker: WorkerProfile) -> bool:
        """判断工人交付是否需要人工复核。"""
        return worker.trust_score < self.AUTO_REJECT_TRUST_THRESHOLD

    # ========== 交付质量检查 ==========

    def check_delivery_quality(
        self,
        task: Task,
        worker: WorkerProfile
    ) -> QualityCheckResult:
        """
        检查交付质量。

        检查维度：
        1. 工人可信度
        2. 内容完整性
        3. 与验收标准的匹配度
        """
        check_details = {}
        quality_score = 0.0

        # 1. 工人可信度评分 (0-0.4)
        trust_component = worker.trust_score * 0.4
        check_details["trust_component"] = trust_component
        check_details["worker_trust_score"] = worker.trust_score

        # 2. 内容完整性检查 (0-0.3)
        content_score = self._check_content_completeness(task, worker)
        check_details["content_completeness"] = content_score
        quality_score += content_score * 0.3

        # 3. 验收标准匹配度 (0-0.3)
        criteria_score = self._check_criteria_match(task, worker)
        check_details["criteria_match"] = criteria_score
        quality_score += criteria_score * 0.3

        # 总分
        quality_score = trust_component + quality_score

        # 确定置信度等级
        if quality_score >= 0.8:
            confidence_level = "high"
        elif quality_score >= 0.5:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        # 是否需要人工复核
        requires_review = (
            worker.trust_score < self.AUTO_REJECT_TRUST_THRESHOLD or
            quality_score < 0.4 or
            content_score < 0.3
        )

        return QualityCheckResult(
            task_id=task.id,
            worker_id=worker.worker_id,
            quality_score=quality_score,
            confidence_level=confidence_level,
            requires_manual_review=requires_review,
            check_details=check_details
        )

    def _check_content_completeness(
        self,
        task: Task,
        worker: WorkerProfile
    ) -> float:
        """检查交付内容完整性。"""
        if not task.delivery_content:
            return 0.0

        # 基础完整性检查
        score = 0.5  # 有内容就给基础分

        # 内容长度检查
        if len(task.delivery_content) >= 50:
            score += 0.2

        # 有附件加分
        if task.delivery_attachments:
            score += 0.3

        return min(1.0, score)

    def _check_criteria_match(
        self,
        task: Task,
        worker: WorkerProfile
    ) -> float:
        """检查交付与验收标准的匹配度（简化版）。"""
        if not task.acceptance_criteria:
            return 0.8  # 无验收标准，给默认分

        if not task.delivery_content:
            return 0.0

        # 简单关键词匹配
        content_lower = task.delivery_content.lower()
        matched_criteria = 0

        for criterion in task.acceptance_criteria:
            if criterion.lower() in content_lower:
                matched_criteria += 1

        return matched_criteria / len(task.acceptance_criteria)

    # ========== 多重校验 ==========

    def create_multi_validation(
        self,
        task_id: str,
        num_workers: int = None
    ) -> MultiValidationResult:
        """创建多重校验任务。"""
        num_workers = num_workers or self.MULTI_VALIDATION_WORKERS

        result = MultiValidationResult(
            task_id=task_id,
            agreement_rate=0.0,
            confidence=0.0
        )
        self._multi_validations[task_id] = result
        return result

    def add_validation_submission(
        self,
        task_id: str,
        worker_id: str,
        answer: str
    ) -> Optional[MultiValidationResult]:
        """添加校验提交并计算一致性。"""
        validation = self._multi_validations.get(task_id)
        if not validation:
            logger.warning("Multi-validation not found for task: %s", task_id)
            return None

        validation.submissions.append({
            "worker_id": worker_id,
            "answer": answer,
            "submitted_at": datetime.now().isoformat()
        })

        # 计算一致性
        if len(validation.submissions) >= 2:
            self._calculate_agreement(validation)

        # 如果达到工人数量，确定最终答案
        if len(validation.submissions) >= self.MULTI_VALIDATION_WORKERS:
            self._determine_final_answer(validation)

        return validation

    def _calculate_agreement(self, validation: MultiValidationResult) -> None:
        """计算提交答案的一致性。"""
        answers = [s["answer"] for s in validation.submissions]
        if len(answers) < 2:
            return

        # 计算答案哈希用于比较
        answer_hashes = [
            hashlib.sha256(a.encode()).hexdigest()
            for a in answers
        ]

        # 统计相同答案的数量
        hash_counts = Counter(answer_hashes)
        max_count = max(hash_counts.values())

        validation.agreement_rate = max_count / len(answers)
        validation.confidence = validation.agreement_rate

    def _determine_final_answer(self, validation: MultiValidationResult) -> None:
        """根据多数表决确定最终答案。"""
        if not validation.submissions:
            return

        answers = [s["answer"] for s in validation.submissions]
        answer_counts = Counter(answers)

        # 获取得票最多的答案
        most_common = answer_counts.most_common(1)[0]
        validation.final_answer = most_common[0]

        # 检查是否达到一致性阈值
        if validation.agreement_rate >= self.AGREEMENT_THRESHOLD:
            logger.info(
                "Multi-validation consensus reached for task %s: agreement=%.1f%%",
                validation.task_id, validation.agreement_rate * 100
            )
        else:
            logger.warning(
                "Multi-validation no consensus for task %s: agreement=%.1f%%",
                validation.task_id, validation.agreement_rate * 100
            )

    # ========== 质量报告 ==========

    def get_quality_report(self) -> Dict:
        """生成质量报告。"""
        total_tests = len(self._gold_tests)
        passed_tests = sum(1 for t in self._gold_tests.values() if t.is_passed)

        return {
            "total_gold_tests": total_tests,
            "passed_tests": passed_tests,
            "pass_rate": passed_tests / total_tests if total_tests > 0 else 0.0,
            "total_multi_validations": len(self._multi_validations),
            "consensus_reached": sum(
                1 for v in self._multi_validations.values()
                if v.agreement_rate >= self.AGREEMENT_THRESHOLD
            )
        }

    def reset_state(self) -> None:
        """重置状态（用于测试）。"""
        self._gold_tests.clear()
        self._worker_test_assignments.clear()
        self._multi_validations.clear()


# 全局服务实例
quality_control_service = QualityControlService()
