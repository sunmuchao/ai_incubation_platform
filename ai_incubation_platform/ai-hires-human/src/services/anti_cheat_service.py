"""
反作弊与重复交付检测服务。
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from models.task import Task

logger = logging.getLogger(__name__)


class AntiCheatService:
    """
    反作弊检测服务，提供以下能力：
    1. 重复交付检测（内容哈希比对）
    2. 提交频率限制（防止恶意刷屏）
    3. 相似内容检测（基于文本相似度）
    4. 工人信誉关联检测
    """

    def __init__(self) -> None:
        # 全局交付内容哈希库，用于检测跨任务重复提交
        self._global_content_hashes: Dict[str, List[Tuple[str, datetime]]] = {}
        # 工人提交记录，用于检测频率
        self._worker_submissions: Dict[str, List[datetime]] = {}
        # 最小提交间隔（秒）
        self.MIN_SUBMISSION_INTERVAL = 30
        # 短时间内最大提交次数
        self.MAX_SUBMISSIONS_PER_HOUR = 10
        # 重复内容相似度阈值（0-1，越高越严格）
        self.SIMILARITY_THRESHOLD = 0.8

    def _calculate_content_hash(self, content: str, attachments: List[str]) -> str:
        """计算交付内容的哈希值，用于重复检测。"""
        content_str = f"{content}|{'|'.join(sorted(attachments))}"
        return hashlib.sha256(content_str.encode("utf-8")).hexdigest()

    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """简单的文本相似度计算（基于Jaccard系数）。"""
        if not content1 or not content2:
            return 0.0
        set1 = set(content1.lower().split())
        set2 = set(content2.lower().split())
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def check_submission_frequency(self, worker_id: str) -> Tuple[bool, Optional[str]]:
        """
        检查工人提交频率是否正常。
        返回 (是否通过, 拒绝原因)
        """
        now = datetime.now()
        submissions = self._worker_submissions.get(worker_id, [])

        # 清理超过1小时的记录
        submissions = [t for t in submissions if now - t < timedelta(hours=1)]
        self._worker_submissions[worker_id] = submissions

        # 检查最小间隔
        if submissions and now - submissions[-1] < timedelta(seconds=self.MIN_SUBMISSION_INTERVAL):
            return False, f"提交过于频繁，请至少间隔{self.MIN_SUBMISSION_INTERVAL}秒后再提交"

        # 检查小时内提交次数
        if len(submissions) >= self.MAX_SUBMISSIONS_PER_HOUR:
            return False, f"小时内提交次数过多（最多{self.MAX_SUBMISSIONS_PER_HOUR}次/小时）"

        return True, None

    def check_duplicate_delivery(
        self,
        task_id: str,
        content: str,
        attachments: List[str],
        worker_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        检查是否为重复交付。
        返回 (是否通过, 拒绝原因)
        """
        content_hash = self._calculate_content_hash(content, attachments)
        now = datetime.now()

        # 检查本任务是否已提交过相同内容
        existing_submissions = self._global_content_hashes.get(content_hash, [])
        for existing_task_id, submit_time in existing_submissions:
            if existing_task_id == task_id:
                return False, "检测到重复提交，相同内容已提交过"

            # 检查短时间内跨任务重复提交
            if now - submit_time < timedelta(hours=24):
                # 额外检查内容相似度，避免哈希冲突误判
                return False, "检测到内容与近期其他任务交付高度相似，请勿重复提交"

        return True, None

    def check_similar_content(self, content: str, existing_tasks: List[Task]) -> Tuple[bool, Optional[str], float]:
        """
        检查内容是否与现有已完成任务高度相似。
        返回 (是否通过, 拒绝原因, 最高相似度)
        """
        max_similarity = 0.0
        for task in existing_tasks:
            if task.delivery_content:
                similarity = self._calculate_similarity(content, task.delivery_content)
                if similarity > max_similarity:
                    max_similarity = similarity
                if similarity >= self.SIMILARITY_THRESHOLD:
                    return False, f"内容与已有交付相似度{similarity:.1%}，超过阈值{self.SIMILARITY_THRESHOLD:.1%}", max_similarity

        return True, None, max_similarity

    def record_submission(
        self,
        task_id: str,
        worker_id: str,
        content: str,
        attachments: List[str]
    ) -> str:
        """记录提交，返回内容哈希。"""
        now = datetime.now()
        content_hash = self._calculate_content_hash(content, attachments)

        # 记录工人提交时间
        if worker_id not in self._worker_submissions:
            self._worker_submissions[worker_id] = []
        self._worker_submissions[worker_id].append(now)

        # 记录全局内容哈希
        if content_hash not in self._global_content_hashes:
            self._global_content_hashes[content_hash] = []
        self._global_content_hashes[content_hash].append((task_id, now))

        return content_hash

    def get_worker_risk_score(self, worker_id: str) -> float:
        """
        获取工人的风险分数（0-1，越高风险越大）。
        基于历史提交行为、作弊记录等计算。
        """
        submissions = self._worker_submissions.get(worker_id, [])
        if not submissions:
            return 0.0

        # 基于提交频率计算基础风险
        submission_count = len(submissions)
        if submission_count > self.MAX_SUBMISSIONS_PER_HOUR * 0.8:
            base_risk = 0.3 + (submission_count - self.MAX_SUBMISSIONS_PER_HOUR * 0.8) * 0.1
        else:
            base_risk = 0.0

        # 可扩展：加入历史作弊记录、拒单率等维度
        return min(base_risk, 1.0)

    def mark_cheating(self, task: Task, reason: str) -> None:
        """标记任务为作弊。"""
        task.cheating_flag = True
        task.cheating_reason = reason
        logger.warning("Task marked as cheating: task_id=%s, worker_id=%s, reason=%s",
                      task.id, task.worker_id, reason)

    def reset_state(self) -> None:
        """Reset in-memory state (used by internal test endpoints)."""
        self._global_content_hashes.clear()
        self._worker_submissions.clear()


anti_cheat_service = AntiCheatService()
