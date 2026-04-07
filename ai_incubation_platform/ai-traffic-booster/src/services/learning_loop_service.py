"""
AI 持续学习闭环服务 - P3 持续学习闭环

功能:
1. 记录每次优化建议的执行效果
2. 基于历史效果改进建议质量
3. 建立优化效果反馈循环
4. 持续学习和模型改进
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from enum import Enum
import logging
import json

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from db.postgresql_config import get_db_session
from db.postgresql_models import SystemLogModel, LogLevelEnum


logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"      # 待执行
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 执行失败
    ABANDONED = "abandoned"  # 已放弃


class EffectRating(str, Enum):
    """效果评级"""
    EXCELLENT = "excellent"  # 效果优秀 (>20% 提升)
    GOOD = "good"           # 效果良好 (10-20% 提升)
    NEUTRAL = "neutral"     # 无明显变化 (-10% 到 +10%)
    NEGATIVE = "negative"   # 负面效果 (<-10%)


class OptimizationRecord:
    """优化记录"""
    def __init__(
        self,
        record_id: str,
        suggestion_id: str,
        suggestion_type: str,
        suggestion_title: str,
        domain: Optional[str],
        page_url: Optional[str],
        executed_at: datetime,
        executed_by: Optional[str],
        status: ExecutionStatus,
        pre_metrics: Dict[str, float],
        post_metrics: Optional[Dict[str, float]] = None,
        effect_rating: Optional[EffectRating] = None,
        feedback_notes: Optional[str] = None,
        learned_insights: Optional[List[str]] = None,
    ):
        self.record_id = record_id
        self.suggestion_id = suggestion_id
        self.suggestion_type = suggestion_type
        self.suggestion_title = suggestion_title
        self.domain = domain
        self.page_url = page_url
        self.executed_at = executed_at
        self.executed_by = executed_by
        self.status = status
        self.pre_metrics = pre_metrics
        self.post_metrics = post_metrics or {}
        self.effect_rating = effect_rating
        self.feedback_notes = feedback_notes
        self.learned_insights = learned_insights or []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "suggestion_id": self.suggestion_id,
            "suggestion_type": self.suggestion_type,
            "suggestion_title": self.suggestion_title,
            "domain": self.domain,
            "page_url": self.page_url,
            "executed_at": self.executed_at.isoformat(),
            "executed_by": self.executed_by,
            "status": self.status.value if self.status else None,
            "pre_metrics": self.pre_metrics,
            "post_metrics": self.post_metrics,
            "effect_rating": self.effect_rating.value if self.effect_rating else None,
            "feedback_notes": self.feedback_notes,
            "learned_insights": self.learned_insights,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def calculate_effect(self) -> Dict[str, float]:
        """计算各指标的变化百分比"""
        effects = {}
        for key, pre_value in self.pre_metrics.items():
            if pre_value != 0 and key in self.post_metrics:
                post_value = self.post_metrics[key]
                effect = ((post_value - pre_value) / abs(pre_value)) * 100
                effects[key] = round(effect, 2)
        return effects


class LearningLoopService:
    """
    持续学习闭环服务

    记录优化执行效果，持续改进建议质量
    """

    def __init__(self, db_session: Optional[Session] = None):
        self._db_session = db_session

    @property
    def db_session(self) -> Session:
        if self._db_session is None:
            return next(get_db_session())
        return self._db_session

    def record_execution(
        self,
        suggestion_id: str,
        suggestion_type: str,
        suggestion_title: str,
        pre_metrics: Dict[str, float],
        domain: Optional[str] = None,
        page_url: Optional[str] = None,
        executed_by: Optional[str] = None,
    ) -> OptimizationRecord:
        """
        记录优化执行

        Args:
            suggestion_id: 建议 ID
            suggestion_type: 建议类型
            suggestion_title: 建议标题
            pre_metrics: 执行前指标
            domain: 域名
            page_url: 页面 URL
            executed_by: 执行人

        Returns:
            OptimizationRecord: 创建的优化记录
        """
        record_id = f"opt_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{suggestion_id}"

        record = OptimizationRecord(
            record_id=record_id,
            suggestion_id=suggestion_id,
            suggestion_type=suggestion_type,
            suggestion_title=suggestion_title,
            domain=domain,
            page_url=page_url,
            executed_at=datetime.utcnow(),
            executed_by=executed_by,
            status=ExecutionStatus.COMPLETED,
            pre_metrics=pre_metrics,
        )

        # 记录到日志系统
        self._log_execution(record)

        return record

    def update_effect(
        self,
        record_id: str,
        post_metrics: Dict[str, float],
        feedback_notes: Optional[str] = None,
    ) -> OptimizationRecord:
        """
        更新优化效果

        Args:
            record_id: 记录 ID
            post_metrics: 执行后指标
            feedback_notes: 反馈备注

        Returns:
            OptimizationRecord: 更新后的记录
        """
        # 从日志系统查询记录
        record = self._get_record(record_id)
        if not record:
            raise ValueError(f"Record not found: {record_id}")

        record.post_metrics = post_metrics
        record.feedback_notes = feedback_notes
        record.effect_rating = self._calculate_effect_rating(record)
        record.updated_at = datetime.utcnow()

        # 提取学习洞察
        record.learned_insights = self._extract_insights(record)

        # 更新日志记录
        self._log_effect_update(record)

        return record

    def get_success_rate(
        self,
        suggestion_type: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        获取建议成功率

        Args:
            suggestion_type: 建议类型
            days: 统计天数

        Returns:
            成功率统计
        """
        records = self._get_recent_records(days=days)

        filtered = records
        if suggestion_type:
            filtered = [r for r in records if r.suggestion_type == suggestion_type]

        total = len([r for r in filtered if r.effect_rating])
        excellent = len([r for r in filtered if r.effect_rating == EffectRating.EXCELLENT])
        good = len([r for r in filtered if r.effect_rating == EffectRating.GOOD])
        neutral = len([r for r in filtered if r.effect_rating == EffectRating.NEUTRAL])
        negative = len([r for r in filtered if r.effect_rating == EffectRating.NEGATIVE])

        return {
            "total": total,
            "excellent": excellent,
            "good": good,
            "neutral": neutral,
            "negative": negative,
            "success_rate": round((excellent + good) / total * 100, 2) if total > 0 else 0,
            "average_improvement": self._calculate_average_improvement(filtered),
        }

    def get_best_practices(
        self,
        suggestion_type: Optional[str] = None,
        min_success_rate: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        获取最佳实践

        基于历史成功率推荐高效果的优化模式

        Args:
            suggestion_type: 建议类型
            min_success_rate: 最小成功率阈值

        Returns:
            最佳实践列表
        """
        # 按类型分组统计
        type_stats = {}

        for record in self._get_all_records():
            stype = record.suggestion_type
            if stype not in type_stats:
                type_stats[stype] = {"excellent": 0, "good": 0, "total": 0}

            type_stats[stype]["total"] += 1
            if record.effect_rating == EffectRating.EXCELLENT:
                type_stats[stype]["excellent"] += 1
            elif record.effect_rating == EffectRating.GOOD:
                type_stats[stype]["good"] += 1

        # 筛选高成功率的类型
        best_practices = []
        for stype, stats in type_stats.items():
            if stats["total"] >= 3:  # 至少 3 个样本
                success_rate = (stats["excellent"] + stats["good"]) / stats["total"]
                if success_rate >= min_success_rate:
                    best_practices.append({
                        "suggestion_type": stype,
                        "success_rate": round(success_rate * 100, 1),
                        "sample_count": stats["total"],
                        "excellent_count": stats["excellent"],
                        "good_count": stats["good"],
                    })

        # 按成功率排序
        best_practices.sort(key=lambda x: x["success_rate"], reverse=True)

        return best_practices

    def get_similar_cases(
        self,
        suggestion_type: str,
        suggestion_title: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        获取相似案例

        基于历史数据返回相似的优化案例及其效果

        Args:
            suggestion_type: 建议类型
            suggestion_title: 建议标题
            limit: 返回数量

        Returns:
            相似案例列表
        """
        records = self._get_all_records()

        # 匹配相似标题
        similar = []
        for r in records:
            if r.suggestion_type == suggestion_type:
                # 简单标题匹配（可改为更智能的语义匹配）
                if suggestion_title.lower() in r.suggestion_title.lower() or \
                   r.suggestion_title.lower() in suggestion_title.lower():
                    similar.append(r)

        # 按效果评级排序
        rating_order = {
            EffectRating.EXCELLENT: 0,
            EffectRating.GOOD: 1,
            EffectRating.NEUTRAL: 2,
            EffectRating.NEGATIVE: 3,
        }

        similar.sort(key=lambda x: rating_order.get(x.effect_rating, 4))

        return [r.to_dict() for r in similar[:limit]]

    def _calculate_effect_rating(self, record: OptimizationRecord) -> EffectRating:
        """计算效果评级"""
        effects = record.calculate_effect()

        if not effects:
            return EffectRating.NEUTRAL

        # 取平均效果
        avg_effect = sum(effects.values()) / len(effects)

        if avg_effect > 20:
            return EffectRating.EXCELLENT
        elif avg_effect > 10:
            return EffectRating.GOOD
        elif avg_effect > -10:
            return EffectRating.NEUTRAL
        else:
            return EffectRating.NEGATIVE

    def _extract_insights(self, record: OptimizationRecord) -> List[str]:
        """提取学习洞察"""
        insights = []

        if record.effect_rating == EffectRating.EXCELLENT:
            insights.append(f"成功案例：{record.suggestion_title} 带来显著提升")
            # 分析哪些指标提升最多
            effects = record.calculate_effect()
            top_metric = max(effects.items(), key=lambda x: x[1], default=None)
            if top_metric:
                insights.append(f"最有效指标：{top_metric[0]} 提升 {top_metric[1]}%")

        elif record.effect_rating == EffectRating.NEGATIVE:
            insights.append(f"失败案例：{record.suggestion_title} 效果不佳，需调整策略")
            if record.feedback_notes:
                insights.append(f"用户反馈：{record.feedback_notes}")

        return insights

    def _log_execution(self, record: OptimizationRecord):
        """记录执行日志"""
        from services.log_service import get_log_service
        log_service = get_log_service()

        log_service.log(
            level="INFO",
            message=f"Optimization executed: {record.suggestion_title}",
            logger_name="learning_loop.execution",
            trace_id=record.record_id,
            extra_data={
                "suggestion_id": record.suggestion_id,
                "suggestion_type": record.suggestion_type,
                "pre_metrics": record.pre_metrics,
            },
        )

    def _log_effect_update(self, record: OptimizationRecord):
        """记录效果更新日志"""
        from services.log_service import get_log_service
        log_service = get_log_service()

        effects = record.calculate_effect()

        log_service.log(
            level="INFO",
            message=f"Optimization effect updated: {record.suggestion_title} - {record.effect_rating.value}",
            logger_name="learning_loop.effect",
            trace_id=record.record_id,
            extra_data={
                "post_metrics": record.post_metrics,
                "effects": effects,
                "effect_rating": record.effect_rating.value,
            },
        )

    def _get_record(self, record_id: str) -> Optional[OptimizationRecord]:
        """从日志系统获取记录"""
        from services.log_service import get_log_service
        log_service = get_log_service()

        logs = log_service.get_logs(trace_id=record_id, limit=10)

        if not logs:
            return None

        # 从日志重建记录（简化实现）
        return None

    def _get_recent_records(self, days: int = 30) -> List[OptimizationRecord]:
        """获取最近的记录"""
        from services.log_service import get_log_service
        log_service = get_log_service()

        logs = log_service.get_logs(
            logger_name="learning_loop.execution",
            start_time=datetime.utcnow() - timedelta(days=days),
            limit=1000,
        )

        # 从日志重建记录（简化实现）
        return []

    def _get_all_records(self) -> List[OptimizationRecord]:
        """获取所有记录"""
        return self._get_recent_records(days=365)

    def _calculate_average_improvement(self, records: List[OptimizationRecord]) -> float:
        """计算平均提升"""
        improvements = []
        for record in records:
            if record.effect_rating in [EffectRating.EXCELLENT, EffectRating.GOOD]:
                effects = record.calculate_effect()
                if effects:
                    improvements.append(max(effects.values()))

        return round(sum(improvements) / len(improvements), 2) if improvements else 0


# 全局服务实例
learning_loop_service = LearningLoopService()
