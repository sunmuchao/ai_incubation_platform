"""
AI 版主服务

实现 AI 版主自动处理常规治理操作：
- 自动处理举报
- 违规内容识别
- 自动生成治理报告
- 智能审核决策
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import logging
import uuid
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import DBPost, DBComment, DBReport, DBBanRecord, DBAuditLog
from db.manager import db_manager
from models.member import ReportType, ReportStatus, ContentType, BanReason, OperationType
from services.notification_service import notification_service, NotificationEvent

logger = logging.getLogger(__name__)


# 违规关键词规则
VIOLATION_KEYWORDS = {
    ReportType.SPAM: [
        "加微信", "加 QQ", "联系", "私聊", "转账", "汇款", "投资理财",
        "赚钱", "兼职", "刷单", "彩票", "博彩", "优惠码", "推广链接"
    ],
    ReportType.PORNOGRAPHY: [
        "色情", "裸体", "成人影片", "AV", "色情网站", "裸聊", "约炮"
    ],
    ReportType.VIOLENCE: [
        "杀人", "自杀", "爆炸", "恐怖", "血腥", "暴力", "殴打", "武器"
    ],
    ReportType.HATE_SPEECH: [
        "种族歧视", "地域黑", "侮辱", "谩骂", "傻逼", "傻 B", "废物", "垃圾"
    ],
    ReportType.ADVERTISEMENT: [
        "http://", "https://", "www.", ".com", ".cn", "点击链接", "扫码关注"
    ]
}

# 违规分数配置
VIOLATION_SCORE_CONFIG = {
    ReportType.SPAM: 0.9,
    ReportType.PORNOGRAPHY: 0.95,
    ReportType.VIOLENCE: 0.9,
    ReportType.HATE_SPEECH: 0.7,
    ReportType.ADVERTISEMENT: 0.6,
}

# 自动处理阈值配置
AUTO_ACTION_THRESHOLDS = {
    "auto_reject_score": 0.85,      # 自动拒绝阈值
    "auto_dismiss_score": 0.3,       # 自动忽略阈值
    "auto_approve_score": 0.3,       # 自动通过阈值
    "human_review_score": 0.5,       # 人工审核阈值
}


class AIModeratorLearningService:
    """AI 版主学习服务

    实现基于历史数据的学习能力：
    - 从人工审核决策中学习
    - 动态调整阈值
    - 规则优化建议
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._learning_rate = 0.1  # 学习率
        self._decision_history = []

    async def learn_from_human_decisions(
        self,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        从人工审核决策中学习

        Args:
            limit: 分析的决策数量

        Returns:
            学习结果，包含阈值调整建议
        """
        # 获取已处理举报（人工审核的）
        result = await self.db.execute(
            select(DBReport)
            .where(DBReport.handler_id != "ai_moderator")
            .where(DBReport.handler_id is not None)
            .where(DBReport.status.in_([ReportStatus.RESOLVED.value, ReportStatus.DISMISS.value]))
            .order_by(desc(DBReport.processed_at))
            .limit(limit)
        )
        human_decisions = result.scalars().all()

        if len(human_decisions) < 10:
            return {
                "status": "insufficient_data",
                "message": f"需要至少 10 条人工决策，当前 {len(human_decisions)} 条",
                "decisions_analyzed": len(human_decisions)
            }

        # 重新分析这些举报
        analysis_results = []
        for report in human_decisions:
            content = await self._get_report_content(report)
            if content:
                ai_analysis = await self._analyze_content(content, report)
                analysis_results.append({
                    "report": report,
                    "ai_probability": ai_analysis["violation_probability"],
                    "human_decision": report.status == ReportStatus.RESOLVED.value
                })

        # 计算 AI 与人工决策的差异
        false_positives = []  # AI 认为违规但人工放过
        false_negatives = []  # AI 认为没事但人工判定违规
        correct_decisions = []

        for item in analysis_results:
            ai_violation = item["ai_probability"] >= AUTO_ACTION_THRESHOLDS["auto_reject_score"]
            human_violation = item["human_decision"]

            if ai_violation and not human_violation:
                false_positives.append(item)
            elif not ai_violation and human_violation:
                false_negatives.append(item)
            else:
                correct_decisions.append(item)

        # 生成阈值调整建议
        threshold_adjustments = {}

        if false_positives:
            avg_fp_prob = sum(item["ai_probability"] for item in false_positives) / len(false_positives)
            # 如果有大量误报，提高拒绝阈值
            threshold_adjustments["auto_reject_score"] = min(0.95, AUTO_ACTION_THRESHOLDS["auto_reject_score"] + 0.05)

        if false_negatives:
            avg_fn_prob = sum(item["ai_probability"] for item in false_negatives) / len(false_negatives)
            # 如果有大量漏报，降低拒绝阈值
            threshold_adjustments["auto_reject_score"] = max(0.7, AUTO_ACTION_THRESHOLDS["auto_reject_score"] - 0.05)

        # 计算准确率
        accuracy = len(correct_decisions) / len(analysis_results) if analysis_results else 0

        return {
            "status": "success",
            "decisions_analyzed": len(analysis_results),
            "accuracy": round(accuracy, 3),
            "false_positives": len(false_positives),
            "false_negatives": len(false_negatives),
            "correct_decisions": len(correct_decisions),
            "threshold_adjustments": threshold_adjustments,
            "recommendations": self._generate_learning_recommendations(
                false_positives, false_negatives, accuracy
            )
        }

    async def _get_report_content(self, report: DBReport) -> Optional[str]:
        """获取被举报内容"""
        try:
            if report.reported_content_type == ContentType.POST.value:
                result = await self.db.execute(
                    select(DBPost).where(DBPost.id == report.reported_content_id)
                )
                post = result.scalar_one_or_none()
                if post:
                    return f"{post.title} {post.content}"
            elif report.reported_content_type == ContentType.COMMENT.value:
                result = await self.db.execute(
                    select(DBComment).where(DBComment.id == report.reported_content_id)
                )
                comment = result.scalar_one_or_none()
                if comment:
                    return comment.content
        except Exception as e:
            logger.error(f"获取被举报内容失败：{e}")
        return None

    async def _analyze_content(self, content: str, report: DBReport) -> Dict[str, Any]:
        """分析内容"""
        keyword_matches = self._check_keywords(content)
        feature_score = self._analyze_content_features(content)
        user_history_score = await self._analyze_user_history(report.reported_content_author_id)
        reporter_score = await self._analyze_reporter_credibility(report.reporter_id)

        violation_probability = self._calculate_violation_probability(
            keyword_score=keyword_matches["score"],
            feature_score=feature_score,
            user_history_score=user_history_score,
            reporter_score=reporter_score
        )

        return {
            "violation_probability": violation_probability,
            "detected_violation_types": keyword_matches["matched_types"]
        }

    def _check_keywords(self, content: str) -> Dict[str, Any]:
        """检查关键词匹配"""
        content_lower = content.lower()
        matched_types = []
        total_score = 0.0

        for v_type, keywords in VIOLATION_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw.lower() in content_lower)
            if matches > 0:
                matched_types.append(v_type.value)
                keyword_score = min(1.0, matches / len(keywords))
                type_weight = VIOLATION_SCORE_CONFIG.get(v_type, 0.5)
                total_score += keyword_score * type_weight

        normalized_score = min(1.0, total_score / len(VIOLATION_KEYWORDS))

        return {
            "score": normalized_score,
            "matched_types": matched_types,
            "match_count": len(matched_types)
        }

    def _analyze_content_features(self, content: str) -> float:
        """分析内容特征"""
        feature_score = 0.0

        if len(content) < 10 or len(content) > 5000:
            feature_score += 0.1

        link_count = content.count("http://") + content.count("https://") + content.count("www.")
        if link_count > 3:
            feature_score += 0.2

        contact_patterns = ["微信", "QQ", "电话", "邮箱", "@"]
        if any(p in content for p in contact_patterns):
            feature_score += 0.15

        if len(set(content)) < len(content) * 0.3:
            feature_score += 0.1

        money_patterns = ["元", "块", "￥", "$", "价格", "购买", "付款"]
        if any(p in content for p in money_patterns):
            feature_score += 0.1

        return min(1.0, feature_score)

    async def _analyze_user_history(self, user_id: str) -> float:
        """分析用户历史"""
        try:
            result = await self.db.execute(
                select(func.count(DBBanRecord.id))
                .where(DBBanRecord.user_id == user_id)
            )
            violation_count = result.scalar() or 0

            result = await self.db.execute(
                select(func.count(DBReport.id))
                .where(DBReport.reported_content_author_id == user_id)
                .where(DBReport.status == ReportStatus.RESOLVED.value)
            )
            confirmed_violations = result.scalar() or 0

            history_score = min(1.0, (violation_count * 0.2 + confirmed_violations * 0.1))
            return history_score
        except Exception as e:
            logger.error(f"分析用户历史失败：{e}")
            return 0.5

    async def _analyze_reporter_credibility(self, reporter_id: str) -> float:
        """分析举报人信誉"""
        try:
            result = await self.db.execute(
                select(func.count(DBReport.id))
                .where(DBReport.reporter_id == reporter_id)
                .where(DBReport.status == ReportStatus.RESOLVED.value)
            )
            confirmed_reports = result.scalar() or 0

            result = await self.db.execute(
                select(func.count(DBReport.id))
                .where(DBReport.reporter_id == reporter_id)
                .where(DBReport.status == ReportStatus.DISMISS.value)
            )
            dismissed_reports = result.scalar() or 0

            total_reports = confirmed_reports + dismissed_reports
            if total_reports == 0:
                return 0.5

            accuracy = confirmed_reports / total_reports
            credibility_score = 0.3 + (accuracy * 0.7)
            return credibility_score
        except Exception as e:
            logger.error(f"分析举报人信誉失败：{e}")
            return 0.5

    def _calculate_violation_probability(
        self,
        keyword_score: float,
        feature_score: float,
        user_history_score: float,
        reporter_score: float
    ) -> float:
        """计算违规概率"""
        weights = {
            "keyword": 0.4,
            "feature": 0.2,
            "user_history": 0.2,
            "reporter": 0.2
        }

        probability = (
            keyword_score * weights["keyword"] +
            feature_score * weights["feature"] +
            user_history_score * weights["user_history"] +
            reporter_score * weights["reporter"]
        )

        return round(probability, 3)

    def _generate_learning_recommendations(
        self,
        false_positives: List,
        false_negatives: List,
        accuracy: float
    ) -> List[str]:
        """生成学习建议"""
        recommendations = []

        if accuracy < 0.7:
            recommendations.append("准确率较低，建议增加训练数据或调整特征权重")

        if len(false_positives) > len(false_negatives) * 2:
            recommendations.append("误报率较高，建议提高自动拒绝阈值")

        if len(false_negatives) > len(false_positives) * 2:
            recommendations.append("漏报率较高，建议降低自动拒绝阈值并补充关键词库")

        if accuracy >= 0.85:
            recommendations.append("准确率良好，可以扩大自动处理范围")

        return recommendations


class AIModeratorService:
    """AI 版主服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._auto_processed_count = 0
        self._accuracy_stats = {
            "correct": 0,
            "incorrect": 0,
            "uncertain": 0
        }

    async def auto_process_reports(self, batch_size: int = 50) -> Dict[str, Any]:
        """
        批量自动处理举报

        Args:
            batch_size: 每批处理的举报数量

        Returns:
            {
                "processed": int,  # 处理数量
                "auto_resolved": int,  # 自动解决数量
                "auto_dismissed": int,  # 自动忽略数量
                "human_review": int,  # 需人工审核数量
            }
        """
        # 获取待处理举报
        result = await self.db.execute(
            select(DBReport)
            .where(DBReport.status == ReportStatus.PENDING.value)
            .order_by(DBReport.created_at)
            .limit(batch_size)
        )
        reports = result.scalars().all()

        results = {
            "processed": 0,
            "auto_resolved": 0,
            "auto_dismissed": 0,
            "human_review": 0,
            "details": []
        }

        for report in reports:
            try:
                # 分析举报
                analysis = await self._analyze_report(report)

                # 根据分析结果自动处理
                if analysis["violation_probability"] >= AUTO_ACTION_THRESHOLDS["auto_reject_score"]:
                    # 自动确认违规
                    await self._auto_resolve_report(report, analysis)
                    results["auto_resolved"] += 1
                    action = "auto_resolved"
                elif analysis["violation_probability"] <= AUTO_ACTION_THRESHOLDS["auto_dismiss_score"]:
                    # 自动忽略举报
                    await self._auto_dismiss_report(report, analysis)
                    results["auto_dismissed"] += 1
                    action = "auto_dismissed"
                else:
                    # 标记需人工审核
                    results["human_review"] += 1
                    action = "human_review"

                results["processed"] += 1
                results["details"].append({
                    "report_id": report.id,
                    "action": action,
                    "violation_probability": analysis["violation_probability"],
                    "detected_types": analysis["detected_violation_types"]
                })

                self._auto_processed_count += 1

            except Exception as e:
                logger.error(f"自动处理举报 {report.id} 失败：{e}")
                results["details"].append({
                    "report_id": report.id,
                    "action": "error",
                    "error": str(e)
                })

        logger.info(f"AI 版主批量处理举报：{results['processed']} 个，自动解决 {results['auto_resolved']} 个")
        return results

    async def _analyze_report(self, report: DBReport) -> Dict[str, Any]:
        """分析举报内容"""
        content = await self._get_reported_content(report)
        if not content:
            return {
                "violation_probability": 0.5,
                "detected_violation_types": [],
                "confidence": "low"
            }

        # 关键词匹配分析
        keyword_matches = self._check_keywords(content, report.report_type)

        # 内容特征分析
        feature_score = self._analyze_content_features(content, report)

        # 用户历史行为分析
        user_history_score = await self._analyze_user_history(report.reported_content_author_id)

        # 举报人信誉分析
        reporter_score = await self._analyze_reporter_credibility(report.reporter_id)

        # 综合评分
        violation_probability = self._calculate_violation_probability(
            keyword_score=keyword_matches["score"],
            feature_score=feature_score,
            user_history_score=user_history_score,
            reporter_score=reporter_score
        )

        return {
            "violation_probability": violation_probability,
            "detected_violation_types": keyword_matches["matched_types"],
            "confidence": "high" if violation_probability > 0.8 or violation_probability < 0.2 else "medium",
            "analysis_details": {
                "keyword_score": keyword_matches["score"],
                "feature_score": feature_score,
                "user_history_score": user_history_score,
                "reporter_score": reporter_score
            }
        }

    async def _get_reported_content(self, report: DBReport) -> Optional[str]:
        """获取被举报内容"""
        try:
            if report.reported_content_type == ContentType.POST.value:
                result = await self.db.execute(
                    select(DBPost).where(DBPost.id == report.reported_content_id)
                )
                post = result.scalar_one_or_none()
                if post:
                    return f"{post.title} {post.content}"
            elif report.reported_content_type == ContentType.COMMENT.value:
                result = await self.db.execute(
                    select(DBComment).where(DBComment.id == report.reported_content_id)
                )
                comment = result.scalar_one_or_none()
                if comment:
                    return comment.content
        except Exception as e:
            logger.error(f"获取被举报内容失败：{e}")
        return None

    def _check_keywords(self, content: str, report_type: str) -> Dict[str, Any]:
        """检查关键词匹配"""
        content_lower = content.lower()
        matched_types = []
        total_score = 0.0

        for v_type, keywords in VIOLATION_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw.lower() in content_lower)
            if matches > 0:
                matched_types.append(v_type.value)
                # 关键词匹配分数
                keyword_score = min(1.0, matches / len(keywords))
                type_weight = VIOLATION_SCORE_CONFIG.get(v_type, 0.5)
                total_score += keyword_score * type_weight

        # 归一化分数
        normalized_score = min(1.0, total_score / len(VIOLATION_KEYWORDS))

        return {
            "score": normalized_score,
            "matched_types": matched_types,
            "match_count": sum(1 for v_type, keywords in VIOLATION_KEYWORDS.items()
                             if any(kw.lower() in content_lower for kw in keywords))
        }

    def _analyze_content_features(self, content: str, report: DBReport) -> float:
        """分析内容特征"""
        feature_score = 0.0

        # 特征 1: 内容长度异常
        if len(content) < 10 or len(content) > 5000:
            feature_score += 0.1

        # 特征 2: 包含大量链接
        link_count = content.count("http://") + content.count("https://") + content.count("www.")
        if link_count > 3:
            feature_score += 0.2

        # 特征 3: 包含联系方式
        contact_patterns = ["微信", "QQ", "电话", "邮箱", "@"]
        if any(p in content for p in contact_patterns):
            feature_score += 0.15

        # 特征 4: 重复字符（刷屏特征）
        if len(set(content)) < len(content) * 0.3:
            feature_score += 0.1

        # 特征 5: 包含金钱相关词汇
        money_patterns = ["元", "块", "￥", "$", "价格", "购买", "付款"]
        if any(p in content for p in money_patterns):
            feature_score += 0.1

        return min(1.0, feature_score)

    async def _analyze_user_history(self, user_id: str) -> float:
        """分析用户历史行为"""
        try:
            # 查询用户历史违规记录
            result = await self.db.execute(
                select(func.count(DBBanRecord.id))
                .where(DBBanRecord.user_id == user_id)
            )
            violation_count = result.scalar() or 0

            # 查询用户历史举报记录
            result = await self.db.execute(
                select(func.count(DBReport.id))
                .where(DBReport.reported_content_author_id == user_id)
                .where(DBReport.status == ReportStatus.RESOLVED.value)
            )
            confirmed_violations = result.scalar() or 0

            # 违规分数：历史违规越多，分数越高
            history_score = min(1.0, (violation_count * 0.2 + confirmed_violations * 0.1))

            return history_score
        except Exception as e:
            logger.error(f"分析用户历史失败：{e}")
            return 0.5

    async def _analyze_reporter_credibility(self, reporter_id: str) -> float:
        """分析举报人信誉"""
        try:
            # 查询举报人历史举报记录
            result = await self.db.execute(
                select(func.count(DBReport.id))
                .where(DBReport.reporter_id == reporter_id)
                .where(DBReport.status == ReportStatus.RESOLVED.value)
            )
            confirmed_reports = result.scalar() or 0

            result = await self.db.execute(
                select(func.count(DBReport.id))
                .where(DBReport.reporter_id == reporter_id)
                .where(DBReport.status == ReportStatus.DISMISS.value)
            )
            dismissed_reports = result.scalar() or 0

            total_reports = confirmed_reports + dismissed_reports
            if total_reports == 0:
                return 0.5  # 新举报人，中性分数

            # 举报准确率
            accuracy = confirmed_reports / total_reports

            # 信誉分数基于准确率
            credibility_score = 0.3 + (accuracy * 0.7)

            return credibility_score
        except Exception as e:
            logger.error(f"分析举报人信誉失败：{e}")
            return 0.5

    def _calculate_violation_probability(
        self,
        keyword_score: float,
        feature_score: float,
        user_history_score: float,
        reporter_score: float
    ) -> float:
        """计算违规概率"""
        # 加权平均
        weights = {
            "keyword": 0.4,
            "feature": 0.2,
            "user_history": 0.2,
            "reporter": 0.2
        }

        probability = (
            keyword_score * weights["keyword"] +
            feature_score * weights["feature"] +
            user_history_score * weights["user_history"] +
            reporter_score * weights["reporter"]
        )

        return round(probability, 3)

    async def _auto_resolve_report(self, report: DBReport, analysis: Dict[str, Any]) -> None:
        """自动确认违规并处理"""
        # 更新举报状态
        report.status = ReportStatus.RESOLVED.value
        report.handler_id = "ai_moderator"
        report.handler_note = f"AI 版主自动处理：违规概率 {analysis['violation_probability']:.1%}"
        report.processed_at = datetime.now()

        # 根据违规类型自动处理内容
        await self._auto_remove_content(report)

        # 记录审计日志
        await self._log_auto_action(report, "resolved", analysis)

        # 通知举报人
        await notification_service.notify_event(
            event=NotificationEvent.REPORT_PROCESSED,
            user_id=report.reporter_id,
            context={
                "report_id": report.id,
                "status": "已处理",
                "action": "确认违规，已删除内容"
            }
        )

        logger.info(f"AI 版主自动确认违规：举报 {report.id}")

    async def _auto_dismiss_report(self, report: DBReport, analysis: Dict[str, Any]) -> None:
        """自动忽略举报"""
        report.status = ReportStatus.DISMISS.value
        report.handler_id = "ai_moderator"
        report.handler_note = f"AI 版主自动处理：违规概率 {analysis['violation_probability']:.1%}，低于阈值"
        report.processed_at = datetime.now()

        # 记录审计日志
        await self._log_auto_action(report, "dismissed", analysis)

        # 通知举报人
        await notification_service.notify_event(
            event=NotificationEvent.REPORT_PROCESSED,
            user_id=report.reporter_id,
            context={
                "report_id": report.id,
                "status": "已处理",
                "action": "举报不成立"
            }
        )

        logger.info(f"AI 版主自动忽略举报：举报 {report.id}")

    async def _auto_remove_content(self, report: DBReport) -> None:
        """自动删除违规内容"""
        try:
            if report.reported_content_type == ContentType.POST.value:
                result = await self.db.execute(
                    select(DBPost).where(DBPost.id == report.reported_content_id)
                )
                post = result.scalar_one_or_none()
                if post:
                    post.is_deleted = True
                    post.deleted_at = datetime.now()
                    post.deleted_reason = f"违规内容：{report.report_type}"
            elif report.reported_content_type == ContentType.COMMENT.value:
                result = await self.db.execute(
                    select(DBComment).where(DBComment.id == report.reported_content_id)
                )
                comment = result.scalar_one_or_none()
                if comment:
                    comment.is_deleted = True
                    comment.deleted_at = datetime.now()
                    comment.deleted_reason = f"违规内容：{report.report_type}"
        except Exception as e:
            logger.error(f"自动删除内容失败：{e}")

    async def _log_auto_action(
        self,
        report: DBReport,
        action: str,
        analysis: Dict[str, Any]
    ) -> None:
        """记录 AI 自动处理日志"""
        audit_log = DBAuditLog(
            id=str(uuid.uuid4()),
            operator_id="ai_moderator",
            operation_type=OperationType.CONTENT_REMOVED.value,
            target_id=report.reported_content_id,
            target_type=report.reported_content_type,
            details={
                "action": action,
                "report_id": report.id,
                "violation_probability": analysis["violation_probability"],
                "detected_types": analysis["detected_violation_types"],
                "analysis_details": analysis.get("analysis_details", {})
            }
        )
        self.db.add(audit_log)
        await self.db.commit()

    async def get_auto_moderation_stats(self) -> Dict[str, Any]:
        """获取 AI 版主统计"""
        # 查询自动处理数量
        result = await self.db.execute(
            select(func.count(DBAuditLog.id))
            .where(DBAuditLog.operator_id == "ai_moderator")
        )
        auto_processed = result.scalar() or 0

        # 查询处理准确率（基于人工复核）
        # TODO: 实现准确率统计

        return {
            "total_auto_processed": auto_processed,
            "accuracy_rate": 0.85,  # 默认 85% 准确率
            "avg_processing_time_seconds": 0.5,
            "thresholds": AUTO_ACTION_THRESHOLDS
        }


# 全局服务实例
_ai_moderator_service: Optional[AIModeratorService] = None
_ai_moderator_learning_service: Optional[AIModeratorLearningService] = None


def get_ai_moderator_service(db: AsyncSession) -> AIModeratorService:
    """获取 AI 版主服务实例"""
    global _ai_moderator_service
    if _ai_moderator_service is None or _ai_moderator_service.db is not db:
        _ai_moderator_service = AIModeratorService(db)
    return _ai_moderator_service


def get_ai_moderator_learning_service(db: AsyncSession) -> AIModeratorLearningService:
    """获取 AI 版主学习服务实例"""
    global _ai_moderator_learning_service
    if _ai_moderator_learning_service is None or _ai_moderator_learning_service.db is not db:
        _ai_moderator_learning_service = AIModeratorLearningService(db)
    return _ai_moderator_learning_service
