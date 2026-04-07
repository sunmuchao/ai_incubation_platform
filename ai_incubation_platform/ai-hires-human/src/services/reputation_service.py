"""
信誉体系服务。

实现工人和雇主的信誉评分系统，包括：
1. 工人信誉评分算法
2. 雇主信誉评分
3. 信誉分应用场景（任务准入门槛、保证金额度）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ReputationLevel(str, Enum):
    """信誉等级。"""
    BRONZE = "bronze"      # 青铜：0-30
    SILVER = "silver"      # 白银：30-60
    GOLD = "gold"          # 黄金：60-80
    PLATINUM = "platinum"  # 白金：80-90
    DIAMOND = "diamond"    # 钻石：90-100


@dataclass
class ReputationRecord:
    """信誉记录。"""
    user_id: str
    user_type: str  # "worker" or "employer"
    score: float = 50.0  # 初始基础分
    level: ReputationLevel = ReputationLevel.SILVER
    total_tasks: int = 0
    completed_tasks: int = 0
    cancelled_tasks: int = 0
    disputed_tasks: int = 0
    on_time_delivery_rate: float = 1.0
    average_rating: float = 5.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 信誉事件历史
    events: List[Dict] = field(default_factory=list)

    def get_level_from_score(self) -> ReputationLevel:
        """根据分数获取等级。"""
        if self.score >= 90:
            return ReputationLevel.DIAMOND
        elif self.score >= 80:
            return ReputationLevel.PLATINUM
        elif self.score >= 60:
            return ReputationLevel.GOLD
        elif self.score >= 30:
            return ReputationLevel.SILVER
        else:
            return ReputationLevel.BRONZE

    def can_accept_task(self, min_reputation: float = 0) -> bool:
        """判断是否可以接受任务（需要达到最低信誉要求）。"""
        return self.score >= min_reputation

    def get_required_deposit(self, base_amount: float) -> float:
        """
        根据信誉分计算需要缴纳的保证金。

        信誉分越高，保证金比例越低：
        - 钻石：0% (免保证金)
        - 白金：5%
        - 黄金：10%
        - 白银：20%
        - 青铜：30%
        """
        deposit_rates = {
            ReputationLevel.DIAMOND: 0.0,
            ReputationLevel.PLATINUM: 0.05,
            ReputationLevel.GOLD: 0.10,
            ReputationLevel.SILVER: 0.20,
            ReputationLevel.BRONZE: 0.30,
        }
        rate = deposit_rates.get(self.level, 0.30)
        return base_amount * rate


class ReputationService:
    """
    信誉服务。

    功能：
    1. 信誉分计算与更新
    2. 信誉等级评定
    3. 信誉事件记录
    4. 信誉分应用场景
    """

    def __init__(self) -> None:
        # 内存存储信誉记录
        self._records: Dict[str, ReputationRecord] = {}
        # 信誉事件类型
        self._event_types = {
            "TASK_COMPLETED": {"score_delta": 5, "description": "完成任务"},
            "TASK_CANCELLED": {"score_delta": -3, "description": "取消任务"},
            "TASK_DISPUTE_LOST": {"score_delta": -10, "description": "争议败诉"},
            "TASK_DISPUTE_WON": {"score_delta": 3, "description": "争议胜诉"},
            "LATE_DELIVERY": {"score_delta": -5, "description": "逾期交付"},
            "EARLY_DELIVERY": {"score_delta": 2, "description": "提前交付"},
            "HIGH_RATING": {"score_delta": 3, "description": "获得好评"},
            "LOW_RATING": {"score_delta": -5, "description": "获得差评"},
            "CHEATING_DETECTED": {"score_delta": -20, "description": "作弊 detected"},
            "FIRST_TASK": {"score_delta": 5, "description": "首次完成任务"},
        }

    def get_or_create_record(self, user_id: str, user_type: str) -> ReputationRecord:
        """获取或创建用户信誉记录。"""
        if user_id not in self._records:
            self._records[user_id] = ReputationRecord(
                user_id=user_id,
                user_type=user_type,
            )
        return self._records[user_id]

    def add_event(
        self,
        user_id: str,
        event_type: str,
        task_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[ReputationRecord]:
        """
        添加信誉事件并更新分数。

        Args:
            user_id: 用户 ID
            event_type: 事件类型
            task_id: 相关任务 ID
            description: 事件描述

        Returns:
            更新后的信誉记录
        """
        record = self._records.get(user_id)
        if not record:
            logger.warning("User reputation record not found: %s", user_id)
            return None

        if event_type not in self._event_types:
            logger.warning("Unknown event type: %s", event_type)
            return None

        event_config = self._event_types[event_type]
        score_delta = event_config["score_delta"]

        # 更新分数（限制在 0-100 范围内）
        old_score = record.score
        record.score = max(0, min(100, record.score + score_delta))
        record.level = record.get_level_from_score()
        record.updated_at = datetime.now()

        # 记录事件
        event = {
            "event_type": event_type,
            "event_description": event_config["description"],
            "custom_description": description,
            "score_delta": score_delta,
            "old_score": old_score,
            "new_score": record.score,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
        }
        record.events.append(event)

        logger.info(
            "Reputation event: user=%s event=%s score_change=%.1f -> %.1f",
            user_id, event_type, old_score, record.score
        )

        return record

    def record_task_completed(
        self,
        user_id: str,
        user_type: str,
        task_id: str,
        rating: Optional[float] = None,
        on_time: bool = True,
    ) -> Optional[ReputationRecord]:
        """
        记录任务完成事件。

        Args:
            user_id: 用户 ID
            user_type: 用户类型 (worker/employer)
            task_id: 任务 ID
            rating: 评分 (1-5)
            on_time: 是否准时交付

        Returns:
            更新后的信誉记录
        """
        record = self.get_or_create_record(user_id, user_type)
        record.total_tasks += 1
        record.completed_tasks += 1

        # 基础完成分数
        self.add_event(user_id, "TASK_COMPLETED", task_id)

        # 首次完成任务奖励
        if record.completed_tasks == 1:
            self.add_event(user_id, "FIRST_TASK", task_id)

        # 准时/提前交付奖励
        if on_time:
            self.add_event(user_id, "EARLY_DELIVERY", task_id)
        else:
            self.add_event(user_id, "LATE_DELIVERY", task_id)

        # 评分处理
        if rating is not None:
            if rating >= 4.5:
                self.add_event(user_id, "HIGH_RATING", task_id, f"获得 {rating} 星好评")
            elif rating <= 2.0:
                self.add_event(user_id, "LOW_RATING", task_id, f"获得 {rating} 星差评")

        # 更新准时交付率
        total_deliveries = record.completed_tasks
        if on_time:
            # 简单移动平均
            record.on_time_delivery_rate = (
                (record.on_time_delivery_rate * (total_deliveries - 1) + 1) / total_deliveries
            )
        else:
            record.on_time_delivery_rate = (
                (record.on_time_delivery_rate * (total_deliveries - 1) + 0) / total_deliveries
            )

        # 更新平均评分
        if rating is not None:
            total_ratings = record.completed_tasks
            record.average_rating = (
                (record.average_rating * (total_ratings - 1) + rating) / total_ratings
            )

        return record

    def record_task_cancelled(
        self,
        user_id: str,
        user_type: str,
        task_id: str,
        reason: Optional[str] = None,
    ) -> Optional[ReputationRecord]:
        """记录任务取消事件。"""
        record = self.get_or_create_record(user_id, user_type)
        record.cancelled_tasks += 1
        self.add_event(user_id, "TASK_CANCELLED", task_id, reason)
        return record

    def record_dispute_result(
        self,
        user_id: str,
        user_type: str,
        task_id: str,
        won: bool,
    ) -> Optional[ReputationRecord]:
        """记录争议结果。"""
        record = self.get_or_create_record(user_id, user_type)
        record.disputed_tasks += 1
        if won:
            self.add_event(user_id, "TASK_DISPUTE_WON", task_id)
        else:
            self.add_event(user_id, "TASK_DISPUTE_LOST", task_id)
        return record

    def record_cheating(
        self,
        user_id: str,
        user_type: str,
        task_id: str,
        reason: str,
    ) -> Optional[ReputationRecord]:
        """记录作弊行为（大幅扣分）。"""
        record = self.get_or_create_record(user_id, user_type)
        self.add_event(user_id, "CHEATING_DETECTED", task_id, reason)
        return record

    def get_reputation_summary(self, user_id: str) -> Optional[Dict]:
        """
        获取用户信誉摘要。

        Returns:
            信誉摘要字典
        """
        record = self._records.get(user_id)
        if not record:
            return None

        return {
            "user_id": record.user_id,
            "user_type": record.user_type,
            "score": round(record.score, 2),
            "level": record.level.value,
            "total_tasks": record.total_tasks,
            "completed_tasks": record.completed_tasks,
            "completion_rate": round(
                record.completed_tasks / max(record.total_tasks, 1) * 100, 2
            ),
            "on_time_delivery_rate": round(record.on_time_delivery_rate * 100, 2),
            "average_rating": round(record.average_rating, 2),
            "can_accept_tasks": record.can_accept_task(),
            "recent_events": record.events[-10:],  # 最近 10 个事件
        }

    def get_leaderboard(
        self,
        user_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        获取信誉排行榜。

        Args:
            user_type: 用户类型筛选 (worker/employer)
            limit: 返回数量限制

        Returns:
            排行榜列表
        """
        records = list(self._records.values())
        if user_type:
            records = [r for r in records if r.user_type == user_type]

        # 按分数降序排序
        records.sort(key=lambda r: r.score, reverse=True)

        return [
            {
                "rank": i + 1,
                "user_id": r.user_id,
                "score": round(r.score, 2),
                "level": r.level.value,
                "completed_tasks": r.completed_tasks,
            }
            for i, r in enumerate(records[:limit])
        ]

    def calculate_comprehensive_score(
        self,
        user_id: str,
    ) -> Optional[Dict]:
        """
        计算综合信誉分数（考虑多个维度）。

        维度权重：
        - 基础分数：40%
        - 完成率：20%
        - 准时交付率：15%
        - 平均评分：15%
        - 争议率：10%

        Returns:
            详细评分信息
        """
        record = self._records.get(user_id)
        if not record:
            return None

        # 各维度得分
        base_score = record.score  # 0-100
        completion_rate_score = (record.completed_tasks / max(record.total_tasks, 1)) * 100
        delivery_score = record.on_time_delivery_rate * 100
        rating_score = (record.average_rating / 5.0) * 100
        dispute_penalty = (record.disputed_tasks / max(record.total_tasks, 1)) * 100

        # 加权计算
        comprehensive_score = (
            base_score * 0.40 +
            completion_rate_score * 0.20 +
            delivery_score * 0.15 +
            rating_score * 0.15 -
            dispute_penalty * 0.10
        )

        # 限制在 0-100 范围内
        comprehensive_score = max(0, min(100, comprehensive_score))

        level = ReputationLevel.SILVER
        if comprehensive_score >= 90:
            level = ReputationLevel.DIAMOND
        elif comprehensive_score >= 80:
            level = ReputationLevel.PLATINUM
        elif comprehensive_score >= 60:
            level = ReputationLevel.GOLD
        elif comprehensive_score >= 30:
            level = ReputationLevel.SILVER
        else:
            level = ReputationLevel.BRONZE

        return {
            "user_id": user_id,
            "comprehensive_score": round(comprehensive_score, 2),
            "level": level.value,
            "breakdown": {
                "base_score": round(base_score, 2),
                "completion_rate": round(completion_rate_score, 2),
                "delivery_rate": round(delivery_score, 2),
                "rating": round(rating_score, 2),
                "dispute_penalty": round(dispute_penalty, 2),
            },
            "weights": {
                "base": 0.40,
                "completion_rate": 0.20,
                "delivery_rate": 0.15,
                "rating": 0.15,
                "dispute": 0.10,
            },
        }

    def reset_state(self) -> None:
        """重置状态（用于测试）。"""
        self._records.clear()


# 全局信誉服务实例
reputation_service = ReputationService()
