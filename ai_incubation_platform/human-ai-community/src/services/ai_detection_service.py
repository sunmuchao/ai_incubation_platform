"""
P10 AI 检测服务

实现自动 AI 内容检测功能：
- 多模型集成检测
- 自动扫描未标注内容
- 标注争议处理
- 检测报告生成
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
import logging
import uuid
import math
import re

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.p10_models import DBAIDetection, DBAIDispute, DBAIDetectionConfig
from db.models import DBPost, DBComment, DBContentLabel
from models.p10_entities import (
    AIDetectionMethod, AIDetectionModel, DetectionConfidence,
    AIDetectionResult, AIDisputeType, AIDisputeRecord,
    AIDetectionStats, AIDisputeResolution, DetectionThresholds, ScanConfig
)
from db.manager import db_manager
from services.notification_service import notification_service, NotificationEvent, NotificationType

logger = logging.getLogger(__name__)


# 默认阈值配置
DEFAULT_THRESHOLDS = DetectionThresholds(
    ai_definitive=0.85,    # 确认 AI 阈值
    ai_likely=0.60,        # 可能 AI 阈值
    human_definitive=0.20, # 确认人类阈值
    human_likely=0.40      # 可能人类阈值
)

# 默认扫描配置
DEFAULT_SCAN_CONFIG = ScanConfig(
    batch_size=100,
    scan_interval_hours=24,
    auto_label=True,
    notify_user=True,
    priority_scan_new=True
)


def _get_confidence_level(probability: float) -> DetectionConfidence:
    """根据概率值获取置信度等级"""
    if probability >= 0.8:
        return DetectionConfidence.VERY_HIGH
    elif probability >= 0.6:
        return DetectionConfidence.HIGH
    elif probability >= 0.4:
        return DetectionConfidence.MEDIUM
    elif probability >= 0.2:
        return DetectionConfidence.LOW
    else:
        return DetectionConfidence.VERY_LOW


def _calculate_perplexity(text: str) -> float:
    """
    计算文本困惑度（简化版）
    AI 生成文本通常具有较低的困惑度（更可预测）
    """
    if not text or len(text) < 10:
        return 0.5

    # 基于字符频率的简化困惑度计算
    char_freq = {}
    for char in text:
        char_freq[char] = char_freq.get(char, 0) + 1

    # 计算平均频率
    avg_freq = len(text) / len(char_freq) if char_freq else 1

    # 归一化到 0-1 范围（越低越可能是 AI）
    normalized = min(1.0, avg_freq / 10)
    return 1.0 - normalized  # 反转：低困惑度=高 AI 概率


def _calculate_burstiness(text: str) -> float:
    """
    计算文本爆发度（简化版）
    人类写作通常有更高的爆发度（句子长度变化大）
    AI 写作通常更均匀
    """
    if not text or len(text) < 20:
        return 0.5

    # 按句子分割
    sentences = re.split(r'[.!?.]', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) < 2:
        return 0.5

    # 计算句子长度标准差
    lengths = [len(s) for s in sentences]
    avg_length = sum(lengths) / len(lengths)
    variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)

    # 变异系数（标准差/平均值）
    cv = std_dev / avg_length if avg_length > 0 else 0

    # 归一化到 0-1（人类写作通常有更高的变异系数）
    normalized = min(1.0, cv / 0.5)
    return 1.0 - normalized  # 反转：低爆发度=高 AI 概率


def _analyze_patterns(text: str) -> Tuple[float, Dict[str, Any]]:
    """
    分析文本模式
    AI 文本常见模式：过度使用某些短语、结构过于规整等
    """
    details = {}
    pattern_score = 0.0

    if not text:
        return 0.5, details

    text_lower = text.lower()

    # 检测 AI 常见短语模式
    ai_phrases = [
        "总而言之", "综上所述", "值得注意的是", "需要考虑的是",
        "从...角度来看", "在此基础上", "进一步来说",
        "in conclusion", "moreover", "furthermore", "additionally",
        "it is important to", "it's worth noting"
    ]

    phrase_count = sum(1 for phrase in ai_phrases if phrase in text_lower)
    details["ai_phrase_count"] = phrase_count
    if phrase_count > 3:
        pattern_score += 0.3
    elif phrase_count > 1:
        pattern_score += 0.15

    # 检测段落结构规整度
    paragraphs = text.split('\n\n')
    if len(paragraphs) >= 3:
        para_lengths = [len(p) for p in paragraphs if p.strip()]
        if para_lengths:
            avg_len = sum(para_lengths) / len(para_lengths)
            length_variance = sum((l - avg_len) ** 2 for l in para_lengths) / len(para_lengths)
            # 过于规整的段落结构可能是 AI 生成
            if length_variance < avg_len * 0.3:
                pattern_score += 0.2
                details["uniform_structure"] = True

    # 检测列表使用（AI 喜欢用列表）
    list_patterns = [r'\d+\.', r'[-*]\s', r'\([a-zA-Z]\)']
    list_count = sum(1 for pattern in list_patterns if re.search(pattern, text))
    if list_count >= 2:
        pattern_score += 0.1
        details["list_usage"] = True

    details["pattern_score"] = min(1.0, pattern_score)
    return min(1.0, pattern_score), details


def _analyze_semantic_features(text: str) -> Tuple[float, Dict[str, Any]]:
    """
    分析语义特征
    AI 文本可能缺乏深度、个人经历、具体细节
    """
    details = {}
    semantic_score = 0.0

    if not text or len(text) < 50:
        return 0.5, details

    # 检测第一人称使用（人类更常用）
    first_person = ['我', '我们', 'I', 'we', 'my', 'our']
    first_person_count = sum(text.count(p) for p in first_person)
    details["first_person_count"] = first_person_count

    if first_person_count == 0 and len(text) > 100:
        # 完全没有第一人称可能是 AI
        semantic_score += 0.2
        details["no_first_person"] = True

    # 检测具体数字和统计数据（人类更可能引用具体数据）
    numbers = re.findall(r'\d+', text)
    details["number_count"] = len(numbers)

    # 检测引用和来源
    citations = re.findall(r'["「](.+?)["」]', text)
    details["citation_count"] = len(citations)

    # 检测情感表达
    emotional_words = ['非常', '特别', '极其', 'really', 'very', 'extremely', 'love', 'hate']
    emotional_count = sum(text.count(w) for w in emotional_words)
    details["emotional_word_count"] = emotional_count

    if emotional_count == 0 and len(text) > 100:
        semantic_score += 0.15
        details["low_emotion"] = True

    details["semantic_score"] = min(1.0, semantic_score)
    return min(1.0, semantic_score), details


class AIDetectionService:
    """AI 检测服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.thresholds = DEFAULT_THRESHOLDS
        self.scan_config = DEFAULT_SCAN_CONFIG
        self._detection_count = 0
        self._accuracy_stats = {
            "total": 0,
            "confirmed": 0,
            "disputed": 0
        }

    async def detect_content(
        self,
        content_id: str,
        content_type: str,
        content_text: str,
        existing_label: Optional[Dict[str, Any]] = None
    ) -> AIDetectionResult:
        """
        检测内容是否由 AI 生成

        Args:
            content_id: 内容 ID
            content_type: 内容类型（post/comment）
            content_text: 内容文本
            existing_label: 现有的 AI 标注（如果有）

        Returns:
            AIDetectionResult: 检测结果
        """
        logger.info(f"开始检测内容 {content_id}, 类型：{content_type}")

        # 1. 困惑度分析
        perplexity_score = _calculate_perplexity(content_text)

        # 2. 爆发度分析
        burstiness_score = _calculate_burstiness(content_text)

        # 3. 模式分析
        pattern_score, pattern_details = _analyze_patterns(content_text)

        # 4. 语义分析
        semantic_score, semantic_details = _analyze_semantic_features(content_text)

        # 5. 综合评分（加权平均）
        weights = {
            "perplexity": 0.25,
            "burstiness": 0.25,
            "pattern": 0.25,
            "semantic": 0.25
        }

        ai_probability = (
            perplexity_score * weights["perplexity"] +
            burstiness_score * weights["burstiness"] +
            pattern_score * weights["pattern"] +
            semantic_score * weights["semantic"]
        )

        # 确定是否 AI 生成
        is_ai_generated = ai_probability >= self.thresholds.ai_likely

        # 获取置信度等级
        confidence = _get_confidence_level(ai_probability)

        # 检查是否有现有标注
        has_label = existing_label is not None
        label_matches = True

        if has_label:
            # 检查检测结果与标注是否一致
            label_ai_type = existing_label.get("author_type", "human")
            if label_ai_type == "human" and is_ai_generated:
                label_matches = False
            elif label_ai_type == "ai" and not is_ai_generated:
                label_matches = False

        # 构建检测结果
        result = AIDetectionResult(
            content_id=content_id,
            content_type=content_type,
            is_ai_generated=is_ai_generated,
            ai_probability=round(ai_probability, 3),
            confidence=confidence,
            detection_methods=[
                AIDetectionMethod.STATISTICAL,
                AIDetectionMethod.PATTERN,
                AIDetectionMethod.SEMANTIC
            ],
            detection_models=[AIDetectionModel.CUSTOM_TRANSFORMER],
            analysis_details={
                "perplexity": perplexity_score,
                "burstiness": burstiness_score,
                "pattern": pattern_score,
                "semantic": semantic_score,
                "pattern_details": pattern_details,
                "semantic_details": semantic_details
            },
            perplexity_score=round(perplexity_score, 3),
            burstiness_score=round(burstiness_score, 3),
            pattern_score=round(pattern_score, 3),
            semantic_score=round(semantic_score, 3),
            has_label=has_label,
            label_matches=label_matches,
            detector_id="ai_detector_v1"
        )

        # 保存检测结果到数据库
        await self._save_detection_result(result)

        self._detection_count += 1
        self._accuracy_stats["total"] += 1

        logger.info(
            f"检测完成：{content_id}, AI 概率={ai_probability:.3f}, "
            f"置信度={confidence.value}, 是否 AI={is_ai_generated}"
        )

        return result

    async def _save_detection_result(self, result: AIDetectionResult) -> None:
        """保存检测结果到数据库"""
        try:
            detection = DBAIDetection(
                id=result.id,
                content_id=result.content_id,
                content_type=result.content_type,
                is_ai_generated=result.is_ai_generated,
                ai_probability=result.ai_probability,
                confidence=result.confidence.value,
                detection_methods=[m.value for m in result.detection_methods],
                detection_models=[m.value for m in result.detection_models],
                analysis_details=result.analysis_details,
                perplexity_score=result.perplexity_score,
                burstiness_score=result.burstiness_score,
                pattern_score=result.pattern_score,
                semantic_score=result.semantic_score,
                has_label=result.has_label,
                label_matches=result.label_matches,
                detector_id=result.detector_id
            )
            self.db.add(detection)
            await self.db.commit()
        except Exception as e:
            logger.error(f"保存检测结果失败：{e}")
            await self.db.rollback()

    async def scan_unlabeled_content(
        self,
        batch_size: int = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        扫描未标注 AI 标签的内容

        Args:
            batch_size: 批次大小
            content_type: 内容类型过滤（post/comment）

        Returns:
            扫描结果统计
        """
        if batch_size is None:
            batch_size = self.scan_config.batch_size

        logger.info(f"开始扫描未标注内容，批次大小：{batch_size}")

        # 查询未标注的帖子
        if content_type is None or content_type == "post":
            result = await self.db.execute(
                select(DBPost)
                .outerjoin(DBContentLabel, DBPost.id == DBContentLabel.content_id)
                .where(DBContentLabel.id.is_(None))
                .limit(batch_size // 2)
            )
            unlabeled_posts = result.scalars().all()

        # 查询未标注的评论
        if content_type is None or content_type == "comment":
            result = await self.db.execute(
                select(DBComment)
                .outerjoin(DBContentLabel, DBComment.id == DBContentLabel.content_id)
                .where(DBContentLabel.id.is_(None))
                .limit(batch_size // 2)
            )
            unlabeled_comments = result.scalars().all()

        results = {
            "scanned": 0,
            "ai_detected": 0,
            "human_verified": 0,
            "uncertain": 0,
            "auto_labeled": 0,
            "details": []
        }

        # 检测帖子
        for post in unlabeled_posts:
            try:
                content_text = f"{post.title} {post.content}"
                detection = await self.detect_content(
                    content_id=post.id,
                    content_type="post",
                    content_text=content_text
                )

                results["scanned"] += 1
                if detection.is_ai_generated:
                    results["ai_detected"] += 1
                elif detection.confidence in [DetectionConfidence.VERY_LOW, DetectionConfidence.LOW]:
                    results["human_verified"] += 1
                else:
                    results["uncertain"] += 1

                # 如果置信度高且配置了自动标注，则创建标签
                if (self.scan_config.auto_label and
                    detection.confidence in [DetectionConfidence.VERY_HIGH, DetectionConfidence.HIGH]):
                    await self._auto_create_label(post.author_id, post.id, "post", detection)
                    results["auto_labeled"] += 1

                results["details"].append({
                    "content_id": post.id,
                    "content_type": "post",
                    "is_ai_generated": detection.is_ai_generated,
                    "ai_probability": detection.ai_probability,
                    "confidence": detection.confidence.value
                })

            except Exception as e:
                logger.error(f"扫描帖子 {post.id} 失败：{e}")

        # 检测评论
        for comment in unlabeled_comments:
            try:
                detection = await self.detect_content(
                    content_id=comment.id,
                    content_type="comment",
                    content_text=comment.content
                )

                results["scanned"] += 1
                if detection.is_ai_generated:
                    results["ai_detected"] += 1
                elif detection.confidence in [DetectionConfidence.VERY_LOW, DetectionConfidence.LOW]:
                    results["human_verified"] += 1
                else:
                    results["uncertain"] += 1

                # 自动标注
                if (self.scan_config.auto_label and
                    detection.confidence in [DetectionConfidence.VERY_HIGH, DetectionConfidence.HIGH]):
                    await self._auto_create_label(comment.author_id, comment.id, "comment", detection)
                    results["auto_labeled"] += 1

                results["details"].append({
                    "content_id": comment.id,
                    "content_type": "comment",
                    "is_ai_generated": detection.is_ai_generated,
                    "ai_probability": detection.ai_probability,
                    "confidence": detection.confidence.value
                })

            except Exception as e:
                logger.error(f"扫描评论 {comment.id} 失败：{e}")

        logger.info(
            f"扫描完成：共扫描 {results['scanned']} 条内容，"
            f"检出 AI {results['ai_detected']} 条，"
            f"自动标注 {results['auto_labeled']} 条"
        )

        return results

    async def _auto_create_label(
        self,
        author_id: str,
        content_id: str,
        content_type: str,
        detection: AIDetectionResult
    ) -> None:
        """自动创建 AI 标签"""
        try:
            from models.p9_entities import AuthorType, AIAssistLevel

            # 根据检测结果确定作者类型
            if detection.ai_probability >= self.thresholds.ai_definitive:
                author_type = AuthorType.AI
                ai_level = AIAssistLevel.FULL
                ai_rate = 100.0
            elif detection.ai_probability >= self.thresholds.ai_likely:
                author_type = AuthorType.HYBRID
                ai_level = AIAssistLevel.HIGH
                ai_rate = detection.ai_probability * 100
            else:
                author_type = AuthorType.HUMAN
                ai_level = AIAssistLevel.NONE
                ai_rate = 0.0

            # 创建标签
            label = DBContentLabel(
                content_id=content_id,
                content_type=content_type,
                author_type=author_type.value,
                ai_assist_level=ai_level.value,
                ai_assist_types=["ai_detected"] if author_type != AuthorType.HUMAN else [],
                ai_participation_rate=ai_rate,
                is_verified=False,
                badge_text=self._generate_badge_text(author_type, ai_level)
            )

            self.db.add(label)
            await self.db.commit()

            logger.info(f"自动创建标签：{content_id}, 作者类型={author_type.value}")

        except Exception as e:
            logger.error(f"自动创建标签失败：{e}")
            await self.db.rollback()

    def _generate_badge_text(self, author_type: str, ai_level: str) -> str:
        """生成徽章文本"""
        if author_type == "human":
            return "👤 人类创作"
        elif author_type == "ai":
            return "🤖 AI 生成 (自动检测)"
        else:
            return "🤝 人机协作 (自动检测)"

    async def create_dispute(
        self,
        content_id: str,
        content_type: str,
        submitter_id: str,
        dispute_type: AIDisputeType,
        description: str,
        evidence: Optional[List[str]] = None
    ) -> AIDisputeRecord:
        """
        创建 AI 检测争议

        Args:
            content_id: 内容 ID
            content_type: 内容类型
            submitter_id: 提交者 ID
            dispute_type: 争议类型
            description: 争议描述
            evidence: 证据列表

        Returns:
            AIDisputeRecord: 争议记录
        """
        # 获取最近的检测结果
        result = await self.db.execute(
            select(DBAIDetection)
            .where(DBAIDetection.content_id == content_id)
            .order_by(desc(DBAIDetection.detected_at))
            .limit(1)
        )
        detection = result.scalar_one_or_none()

        if not detection:
            raise ValueError(f"未找到内容 {content_id} 的检测结果")

        # 创建争议记录
        dispute = AIDisputeRecord(
            content_id=content_id,
            content_type=content_type,
            detection_id=detection.id,
            submitter_id=submitter_id,
            dispute_type=dispute_type,
            description=description,
            evidence=evidence or []
        )

        # 保存到数据库
        db_dispute = DBAIDispute(
            id=dispute.id,
            dispute_id=dispute.dispute_id,
            content_id=content_id,
            content_type=content_type,
            detection_id=dispute.detection_id,
            submitter_id=submitter_id,
            dispute_type=dispute_type.value,
            description=description,
            evidence=evidence or []
        )

        self.db.add(db_dispute)
        await self.db.commit()

        # 通知用户
        if self.scan_config.notify_user:
            from services.notification_service import NotificationMessage, NotificationEvent
            message = NotificationMessage(
                recipient_id=submitter_id,
                event_type=NotificationEvent.REPORT_PROCESSED,
                title="争议已提交",
                content=f"您的 AI 检测争议已提交，等待审核",
                metadata={"dispute_id": dispute.dispute_id}
            )
            notification_service.send_notification(message)

        self._accuracy_stats["disputed"] += 1

        logger.info(f"创建争议记录：{dispute.dispute_id}, 类型={dispute_type.value}")

        return dispute

    async def resolve_dispute(
        self,
        dispute_id: str,
        resolver_id: str,
        resolution: str,
        final_determination: str,
        review_result: Optional[Dict[str, Any]] = None
    ) -> AIDisputeResolution:
        """
        处理 AI 检测争议

        Args:
            dispute_id: 争议 ID
            resolver_id: 处理者 ID
            resolution: 处理结果描述
            final_determination: 最终裁定
            review_result: 复核结果

        Returns:
            AIDisputeResolution: 处理结果
        """
        # 获取争议记录
        result = await self.db.execute(
            select(DBAIDispute)
            .where(DBAIDispute.dispute_id == dispute_id)
        )
        dispute = result.scalar_one_or_none()

        if not dispute:
            raise ValueError(f"未找到争议记录 {dispute_id}")

        if dispute.status != "pending":
            raise ValueError(f"争议 {dispute_id} 已处理")

        # 更新争议状态
        dispute.status = "resolved"
        dispute.resolution = resolution
        dispute.resolved_at = datetime.now()
        dispute.resolved_by = resolver_id
        dispute.review_result = review_result
        dispute.final_determination = final_determination

        # 根据裁定更新检测结果
        detection_updated = False
        label_updated = False

        if final_determination == "overturned":
            # 推翻原检测结果
            detection_result = await self.db.execute(
                select(DBAIDetection)
                .where(DBAIDetection.id == dispute.detection_id)
            )
            detection = detection_result.scalar_one_or_none()

            if detection:
                # 反转检测结果
                detection.is_ai_generated = not detection.is_ai_generated
                detection.ai_probability = 1.0 - detection.ai_probability
                detection.confidence = _get_confidence_level(detection.ai_probability).value
                detection.label_matches = True
                detection_updated = True

                # 更新标签
                await self._update_label_from_dispute(
                    dispute.content_id,
                    dispute.content_type,
                    final_determination
                )
                label_updated = True

        # 提交
        await self.db.commit()

        self._accuracy_stats["confirmed"] += 1

        # 生成处理结果
        action_taken = "更新检测结果" if detection_updated else "维持原判"

        return AIDisputeResolution(
            dispute_id=dispute_id,
            status="upheld" if final_determination == "confirmed" else "overturned",
            reason=resolution,
            action_taken=action_taken,
            detection_updated=detection_updated,
            label_updated=label_updated,
            user_notified=True
        )

    async def _update_label_from_dispute(
        self,
        content_id: str,
        content_type: str,
        determination: str
    ) -> None:
        """根据争议裁定更新标签"""
        try:
            from models.p9_entities import AuthorType, AIAssistLevel

            result = await self.db.execute(
                select(DBContentLabel)
                .where(DBContentLabel.content_id == content_id)
            )
            label = result.scalar_one_or_none()

            if label:
                if determination == "overturned":
                    # 改为人类创作
                    label.author_type = AuthorType.HUMAN.value
                    label.ai_assist_level = AIAssistLevel.NONE.value
                    label.ai_participation_rate = 0.0
                    label.badge_text = "👤 人类创作 (申诉成功)"
                else:
                    # 维持 AI 标注
                    label.is_verified = True
                    label.verified_at = datetime.now()

                await self.db.commit()
                logger.info(f"更新标签：{content_id}, 裁定={determination}")

        except Exception as e:
            logger.error(f"更新标签失败：{e}")
            await self.db.rollback()

    async def get_detection_stats(self) -> AIDetectionStats:
        """获取 AI 检测统计"""
        # 总检测数
        result = await self.db.execute(
            select(func.count(DBAIDetection.id))
        )
        total_scanned = result.scalar() or 0

        # AI 检出数
        result = await self.db.execute(
            select(func.count(DBAIDetection.id))
            .where(DBAIDetection.is_ai_generated == True)
        )
        ai_detected = result.scalar() or 0

        # 按置信度统计
        confidence_counts = {}
        for conf in DetectionConfidence:
            result = await self.db.execute(
                select(func.count(DBAIDetection.id))
                .where(DBAIDetection.confidence == conf.value)
            )
            confidence_counts[conf.value] = result.scalar() or 0

        # 争议统计
        result = await self.db.execute(
            select(func.count(DBAIDispute.id))
        )
        total_disputes = result.scalar() or 0

        result = await self.db.execute(
            select(func.count(DBAIDispute.id))
            .where(DBAIDispute.status == "resolved")
        )
        resolved_disputes = result.scalar() or 0

        # 计算被推翻的检测数
        result = await self.db.execute(
            select(func.count(DBAIDispute.id))
            .where(DBAIDispute.final_determination == "overturned")
        )
        overturned = result.scalar() or 0

        # 计算误报率
        false_positive_rate = (overturned / total_disputes) if total_disputes > 0 else 0.0

        # 计算扫描覆盖率
        result = await self.db.execute(
            select(func.count(DBPost.id))
        )
        total_posts = result.scalar() or 0

        result = await self.db.execute(
            select(func.count(DBComment.id))
        )
        total_comments = result.scalar() or 0

        total_content = total_posts + total_comments
        scan_coverage_rate = (total_scanned / total_content) if total_content > 0 else 0.0

        return AIDetectionStats(
            total_scanned=total_scanned,
            ai_detected=ai_detected,
            human_verified=total_scanned - ai_detected,
            uncertain=confidence_counts.get("medium", 0),
            by_confidence=confidence_counts,
            total_disputes=total_disputes,
            resolved_disputes=resolved_disputes,
            overturned_detections=overturned,
            false_positive_rate=round(false_positive_rate, 3),
            false_negative_rate=0.0,  # 需要更多数据
            scan_coverage_rate=round(scan_coverage_rate, 3)
        )

    async def get_content_detection(
        self,
        content_id: str,
        limit: int = 10
    ) -> List[AIDetectionResult]:
        """获取内容的检测历史"""
        result = await self.db.execute(
            select(DBAIDetection)
            .where(DBAIDetection.content_id == content_id)
            .order_by(desc(DBAIDetection.detected_at))
            .limit(limit)
        )
        detections = result.scalars().all()

        return [
            AIDetectionResult(
                id=d.id,
                content_id=d.content_id,
                content_type=d.content_type,
                is_ai_generated=d.is_ai_generated,
                ai_probability=d.ai_probability,
                confidence=DetectionConfidence(d.confidence),
                detection_methods=[AIDetectionMethod(m) for m in d.detection_methods],
                detection_models=[AIDetectionModel(m) for m in d.detection_models],
                analysis_details=d.analysis_details,
                perplexity_score=d.perplexity_score,
                burstiness_score=d.burstiness_score,
                pattern_score=d.pattern_score,
                semantic_score=d.semantic_score,
                has_label=d.has_label,
                label_matches=d.label_matches,
                detector_id=d.detector_id,
                detected_at=d.detected_at
            )
            for d in detections
        ]

    async def get_disputes(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[AIDisputeRecord]:
        """获取争议列表"""
        query = select(DBAIDispute)
        if status:
            query = query.where(DBAIDispute.status == status)
        query = query.order_by(desc(DBAIDispute.created_at)).limit(limit)

        result = await self.db.execute(query)
        disputes = result.scalars().all()

        return [
            AIDisputeRecord(
                id=d.id,
                dispute_id=d.dispute_id,
                content_id=d.content_id,
                content_type=d.content_type,
                detection_id=d.detection_id,
                submitter_id=d.submitter_id,
                dispute_type=AIDisputeType(d.dispute_type),
                description=d.description,
                evidence=d.evidence or [],
                status=d.status,
                resolution=d.resolution,
                resolved_at=d.resolved_at,
                resolved_by=d.resolved_by,
                review_result=d.review_result,
                final_determination=d.final_determination,
                created_at=d.created_at,
                updated_at=d.updated_at
            )
            for d in disputes
        ]


# 全局服务实例
_ai_detection_service: Optional[AIDetectionService] = None


def get_ai_detection_service(db: AsyncSession) -> AIDetectionService:
    """获取 AI 检测服务实例"""
    global _ai_detection_service
    if _ai_detection_service is None or _ai_detection_service.db is not db:
        _ai_detection_service = AIDetectionService(db)
    return _ai_detection_service
