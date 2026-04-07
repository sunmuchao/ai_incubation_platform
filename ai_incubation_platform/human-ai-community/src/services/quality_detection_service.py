"""
P11 AI 生成内容质量检测服务

在 P10 基础检测能力之上，提供质量增强功能：
1. 多维度语言学特征分析
2. 集成检测模型（Ensemble）
3. 质量评分系统
4. 可解释性报告生成
5. 检测置信度校准
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from pydantic import BaseModel, Field
import logging
import uuid
import math
import re
import json

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
from services.ai_detection_service import (
    AIDetectionService, get_ai_detection_service,
    _calculate_perplexity, _calculate_burstiness,
    _analyze_patterns, _analyze_semantic_features,
    _get_confidence_level
)

logger = logging.getLogger(__name__)


# ==================== 质量评分实体 ====================

class QualityScore(BaseModel):
    """内容质量评分"""
    content_id: str
    content_type: str

    # 综合质量分 (0-100)
    overall_score: float

    # 维度评分
    originality_score: float  # 原创性 (0-100)
    depth_score: float  # 深度 (0-100)
    authenticity_score: float  # 真实性 (0-100)
    engagement_score: float  # 互动性 (0-100)

    # AI 检测相关
    ai_probability: float  # AI 概率 (0-1)
    detection_confidence: str  # 检测置信度

    # 质量等级
    quality_tier: str  # excellent/good/fair/poor

    # 评估时间
    evaluated_at: datetime = Field(default_factory=datetime.now)


class ExplainabilityReport(BaseModel):
    """检测结果可解释性报告"""
    content_id: str
    detection_id: str

    # 总体判定
    is_ai_generated: bool
    ai_probability: float
    confidence: str

    # 关键特征证据
    evidence: List[Dict[str, Any]]

    # 特征权重分析
    feature_weights: Dict[str, float]

    # 决策依据说明
    decision_rationale: str

    # 不确定性来源
    uncertainty_factors: List[str]

    # 建议操作
    recommended_action: str  # approve/reject/manual_review

    # 报告生成时间
    generated_at: datetime = Field(default_factory=datetime.now)


class LinguisticFeatures(BaseModel):
    """语言学特征分析结果"""
    content_id: str

    # 词汇特征
    vocabulary_richness: float  # 词汇丰富度 (0-1)
    avg_word_length: float  # 平均词长
    unique_word_ratio: float  # 独特词比例

    # 句法特征
    sentence_complexity: float  # 句子复杂度
    avg_sentence_length: float  # 平均句长
    sentence_length_variance: float  # 句长方差

    # 语篇特征
    coherence_score: float  # 连贯性评分
    transition_usage: float  # 连接词使用频率

    # 风格特征
    formality_level: float  # 正式程度
    emotional_tone: float  # 情感色调
    personal_voice: float  # 个人风格强度

    # AI 指示器
    ai_indicators: List[Dict[str, Any]]

    # 分析时间
    analyzed_at: datetime = Field(default_factory=datetime.now)


# ==================== 质量检测服务 ====================

class QualityDetectionService(AIDetectionService):
    """
    增强版 AI 质量检测服务

    继承自 AIDetectionService，在原有检测能力基础上添加：
    1. 多维度语言学特征分析
    2. 集成检测模型
    3. 质量评分系统
    4. 可解释性报告
    5. 置信度校准
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db)

        # 质量评分权重配置
        self.quality_weights = {
            "originality": 0.25,
            "depth": 0.20,
            "authenticity": 0.30,
            "engagement": 0.25
        }

        # 特征权重（用于可解释性）
        self.feature_weights = {
            "perplexity": 0.20,
            "burstiness": 0.15,
            "pattern": 0.20,
            "semantic": 0.15,
            "linguistic": 0.15,
            "metadata": 0.15
        }

        # AI 指示器列表
        self.ai_indicators = [
            "low_perplexity",
            "uniform_sentence_structure",
            "common_ai_phrases",
            "lack_personal_experience",
            "overly_formal_tone",
            "excessive_hedging",
            "repetitive_patterns"
        ]

    async def detect_with_quality(
        self,
        content_id: str,
        content_type: str,
        content_text: str,
        existing_label: Optional[Dict[str, Any]] = None
    ) -> Tuple[AIDetectionResult, QualityScore, ExplainabilityReport]:
        """
        带质量评估的 AI 检测

        Args:
            content_id: 内容 ID
            content_type: 内容类型
            content_text: 内容文本
            existing_label: 现有标注

        Returns:
            Tuple[AIDetectionResult, QualityScore, ExplainabilityReport]:
                检测结果、质量评分、可解释性报告
        """
        logger.info(f"开始质量增强检测：{content_id}")

        # 1. 基础 AI 检测（使用父类方法）
        detection_result = await self.detect_content(
            content_id=content_id,
            content_type=content_type,
            content_text=content_text,
            existing_label=existing_label
        )

        # 2. 语言学特征分析
        linguistic_features = await self._analyze_linguistic_features(
            content_id=content_id,
            content_text=content_text
        )

        # 3. 计算质量评分
        quality_score = await self._calculate_quality_score(
            content_id=content_id,
            content_type=content_type,
            content_text=content_text,
            detection_result=detection_result,
            linguistic_features=linguistic_features
        )

        # 4. 生成可解释性报告
        explain_report = await self._generate_explainability_report(
            content_id=content_id,
            detection_result=detection_result,
            linguistic_features=linguistic_features,
            quality_score=quality_score
        )

        logger.info(
            f"质量检测完成：{content_id}, "
            f"AI 概率={detection_result.ai_probability:.3f}, "
            f"质量分={quality_score.overall_score:.1f}"
        )

        return detection_result, quality_score, explain_report

    async def _analyze_linguistic_features(
        self,
        content_id: str,
        content_text: str
    ) -> LinguisticFeatures:
        """
        分析语言学特征

        Args:
            content_id: 内容 ID
            content_text: 内容文本

        Returns:
            LinguisticFeatures: 语言学特征分析结果
        """
        if not content_text or len(content_text) < 10:
            return LinguisticFeatures(
                content_id=content_id,
                vocabulary_richness=0.5,
                avg_word_length=0.0,
                unique_word_ratio=0.5,
                sentence_complexity=0.5,
                avg_sentence_length=0.0,
                sentence_length_variance=0.5,
                coherence_score=0.5,
                transition_usage=0.5,
                formality_level=0.5,
                emotional_tone=0.5,
                personal_voice=0.5,
                ai_indicators=[]
            )

        # 分词（简化的中文分词）
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+|\d+', content_text)
        sentences = re.split(r'[.!?.。！？\n]', content_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 词汇特征
        unique_words = set(words)
        vocabulary_richness = len(unique_words) / len(words) if words else 0
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        unique_word_ratio = len(unique_words) / len(words) if words else 0

        # 句法特征
        sentence_lengths = [len(s) for s in sentences]
        avg_sentence_length = sum(sentence_lengths) / len(sentences) if sentences else 0

        if len(sentences) >= 2:
            mean_len = avg_sentence_length
            variance = sum((l - mean_len) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            sentence_length_variance = variance / (mean_len ** 2) if mean_len > 0 else 0
        else:
            sentence_length_variance = 0

        sentence_complexity = min(1.0, avg_sentence_length / 50)

        # 语篇特征 - 连接词检测
        transitions_cn = ['因此', '所以', '然而', '但是', '而且', '此外', '同时', '另外',
                          '首先', '其次', '最后', '总之', '综上所述', '值得注意的是']
        transitions_en = ['therefore', 'however', 'moreover', 'furthermore', 'additionally',
                          'first', 'second', 'finally', 'in conclusion', 'in summary']

        transition_count = sum(1 for t in transitions_cn + transitions_en if t in content_text)
        transition_usage = min(1.0, transition_count / 10)

        # 连贯性评分（基于连接词和段落结构）
        paragraphs = content_text.split('\n\n')
        coherence_score = min(1.0, (transition_count * 0.1 + len(paragraphs) * 0.1))

        # 风格特征
        formal_words = ['兹', '谨', '敬', '谨此', '特此', '敬请', '贵', '敝']
        formality_level = min(1.0, sum(content_text.count(w) for w in formal_words) / 5)

        # 情感分析（简化的情感词检测）
        emotional_words = ['非常', '特别', '极其', '太', '很', '真', '超级', '特别']
        emotional_tone = min(1.0, sum(content_text.count(w) for w in emotional_words) / 5)

        # 个人风格（第一人称使用）
        first_person = ['我', '我们', '我的', '我们的', 'I', 'we', 'my', 'our']
        personal_voice = min(1.0, sum(content_text.count(p) for p in first_person) / 5)

        # AI 指示器检测
        ai_indicators = []

        # 指示器 1: 低困惑度
        perplexity = _calculate_perplexity(content_text)
        if perplexity < 0.4:
            ai_indicators.append({
                "indicator": "low_perplexity",
                "value": perplexity,
                "threshold": 0.4,
                "description": "文本困惑度较低，可能是 AI 生成"
            })

        # 指示器 2: 句子结构过于均匀
        if sentence_length_variance < 0.2 and len(sentences) >= 3:
            ai_indicators.append({
                "indicator": "uniform_sentence_structure",
                "value": sentence_length_variance,
                "threshold": 0.2,
                "description": "句子长度过于均匀，可能是 AI 生成"
            })

        # 指示器 3: 常见 AI 短语
        ai_phrases = ['总而言之', '综上所述', '值得注意的是', '从...角度来看',
                      'in conclusion', 'moreover', 'furthermore', 'it is important to']
        found_phrases = [p for p in ai_phrases if p in content_text.lower()]
        if len(found_phrases) >= 2:
            ai_indicators.append({
                "indicator": "common_ai_phrases",
                "value": len(found_phrases),
                "threshold": 2,
                "description": f"发现常见 AI 短语：{found_phrases}"
            })

        # 指示器 4: 缺乏个人经历
        if len(content_text) > 100 and personal_voice < 0.2:
            ai_indicators.append({
                "indicator": "lack_personal_experience",
                "value": personal_voice,
                "threshold": 0.2,
                "description": "缺乏第一人称叙述，可能缺乏个人经历"
            })

        # 指示器 5: 过度正式语气
        if formality_level > 0.6 and len(content_text) > 100:
            ai_indicators.append({
                "indicator": "overly_formal_tone",
                "value": formality_level,
                "threshold": 0.6,
                "description": "语气过于正式，可能是 AI 生成"
            })

        # 指示器 6: 过度使用模糊限定词
        hedging_words = ['可能', '或许', '大概', '似乎', '某种程度上', 'generally', 'typically', 'often']
        hedging_count = sum(content_text.count(w) for w in hedging_words)
        if hedging_count > 5 and len(content_text) > 100:
            ai_indicators.append({
                "indicator": "excessive_hedging",
                "value": hedging_count,
                "threshold": 5,
                "description": "过度使用模糊限定词，可能是 AI 生成"
            })

        # 指示器 7: 重复模式
        if len(sentences) >= 4:
            sentence_patterns = [s[:20] if len(s) >= 20 else s for s in sentences]
            pattern_counts = {}
            for p in sentence_patterns:
                pattern_counts[p] = pattern_counts.get(p, 0) + 1
            max_repeat = max(pattern_counts.values()) if pattern_counts else 1
            if max_repeat >= 2:
                ai_indicators.append({
                    "indicator": "repetitive_patterns",
                    "value": max_repeat,
                    "threshold": 2,
                    "description": "发现重复的句子模式"
                })

        return LinguisticFeatures(
            content_id=content_id,
            vocabulary_richness=round(vocabulary_richness, 3),
            avg_word_length=round(avg_word_length, 2),
            unique_word_ratio=round(unique_word_ratio, 3),
            sentence_complexity=round(sentence_complexity, 3),
            avg_sentence_length=round(avg_sentence_length, 2),
            sentence_length_variance=round(sentence_length_variance, 3),
            coherence_score=round(coherence_score, 3),
            transition_usage=round(transition_usage, 3),
            formality_level=round(formality_level, 3),
            emotional_tone=round(emotional_tone, 3),
            personal_voice=round(personal_voice, 3),
            ai_indicators=ai_indicators
        )

    async def _calculate_quality_score(
        self,
        content_id: str,
        content_type: str,
        content_text: str,
        detection_result: AIDetectionResult,
        linguistic_features: LinguisticFeatures
    ) -> QualityScore:
        """
        计算内容质量评分

        Args:
            content_id: 内容 ID
            content_type: 内容类型
            content_text: 内容文本
            detection_result: AI 检测结果
            linguistic_features: 语言学特征

        Returns:
            QualityScore: 质量评分
        """
        # 原创性评分（基于词汇丰富度和 AI 概率）
        # 高 AI 概率降低原创性评分
        originality_score = (
            linguistic_features.vocabulary_richness * 0.4 +
            linguistic_features.unique_word_ratio * 0.3 +
            (1 - detection_result.ai_probability) * 0.3
        ) * 100

        # 深度评分（基于句子复杂度和连贯性）
        depth_score = (
            linguistic_features.sentence_complexity * 0.3 +
            linguistic_features.coherence_score * 0.4 +
            min(1.0, len(content_text) / 500) * 0.3  # 长度因素
        ) * 100

        # 真实性评分（基于个人风格和情感表达）
        authenticity_score = (
            linguistic_features.personal_voice * 0.4 +
            linguistic_features.emotional_tone * 0.3 +
            (1 - len(linguistic_features.ai_indicators) / 7) * 0.3  # AI 指示器越少越真实
        ) * 100

        # 互动性评分（基于连接词和可读性）
        engagement_score = (
            linguistic_features.transition_usage * 0.3 +
            (1 - abs(linguistic_features.formality_level - 0.5) * 2) * 0.3 +  # 适中正式度最佳
            min(1.0, len(content_text) / 300) * 0.4
        ) * 100

        # 综合评分（加权平均）
        overall_score = (
            originality_score * self.quality_weights["originality"] +
            depth_score * self.quality_weights["depth"] +
            authenticity_score * self.quality_weights["authenticity"] +
            engagement_score * self.quality_weights["engagement"]
        )

        # 确定质量等级
        if overall_score >= 85:
            quality_tier = "excellent"
        elif overall_score >= 70:
            quality_tier = "good"
        elif overall_score >= 50:
            quality_tier = "fair"
        else:
            quality_tier = "poor"

        return QualityScore(
            content_id=content_id,
            content_type=content_type,
            overall_score=round(overall_score, 2),
            originality_score=round(originality_score, 2),
            depth_score=round(depth_score, 2),
            authenticity_score=round(authenticity_score, 2),
            engagement_score=round(engagement_score, 2),
            ai_probability=detection_result.ai_probability,
            detection_confidence=detection_result.confidence.value,
            quality_tier=quality_tier
        )

    async def _generate_explainability_report(
        self,
        content_id: str,
        detection_result: AIDetectionResult,
        linguistic_features: LinguisticFeatures,
        quality_score: QualityScore
    ) -> ExplainabilityReport:
        """
        生成可解释性报告

        Args:
            content_id: 内容 ID
            detection_result: AI 检测结果
            linguistic_features: 语言学特征
            quality_score: 质量评分

        Returns:
            ExplainabilityReport: 可解释性报告
        """
        evidence = []
        feature_contributions = {}

        # 证据 1: 困惑度分析
        if detection_result.perplexity_score:
            perplex_contrib = detection_result.perplexity_score * self.feature_weights["perplexity"]
            evidence.append({
                "feature": "perplexity",
                "value": detection_result.perplexity_score,
                "contribution": perplex_contrib,
                "interpretation": "较低" if detection_result.perplexity_score < 0.4 else "正常",
                "description": f"困惑度分数：{detection_result.perplexity_score:.3f}"
            })
            feature_contributions["perplexity"] = perplex_contrib

        # 证据 2: 爆发度分析
        if detection_result.burstiness_score:
            burstiness_contrib = detection_result.burstiness_score * self.feature_weights["burstiness"]
            evidence.append({
                "feature": "burstiness",
                "value": detection_result.burstiness_score,
                "contribution": burstiness_contrib,
                "interpretation": "较低" if detection_result.burstiness_score < 0.4 else "正常",
                "description": f"爆发度分数：{detection_result.burstiness_score:.3f}"
            })
            feature_contributions["burstiness"] = burstiness_contrib

        # 证据 3: 模式分析
        if detection_result.pattern_score:
            pattern_contrib = detection_result.pattern_score * self.feature_weights["pattern"]
            evidence.append({
                "feature": "pattern",
                "value": detection_result.pattern_score,
                "contribution": pattern_contrib,
                "interpretation": "发现 AI 模式" if detection_result.pattern_score > 0.5 else "正常",
                "description": f"模式分数：{detection_result.pattern_score:.3f}"
            })
            feature_contributions["pattern"] = pattern_contrib

        # 证据 4: 语义分析
        if detection_result.semantic_score:
            semantic_contrib = detection_result.semantic_score * self.feature_weights["semantic"]
            evidence.append({
                "feature": "semantic",
                "value": detection_result.semantic_score,
                "contribution": semantic_contrib,
                "interpretation": "缺乏语义深度" if detection_result.semantic_score > 0.5 else "正常",
                "description": f"语义分数：{detection_result.semantic_score:.3f}"
            })
            feature_contributions["semantic"] = semantic_contrib

        # 证据 5: 语言学特征
        linguistic_contrib = len(linguistic_features.ai_indicators) / 7 * self.feature_weights["linguistic"]
        if linguistic_features.ai_indicators:
            evidence.append({
                "feature": "linguistic",
                "value": len(linguistic_features.ai_indicators),
                "contribution": linguistic_contrib,
                "interpretation": f"发现 {len(linguistic_features.ai_indicators)} 个 AI 指示器",
                "details": linguistic_features.ai_indicators[:3]  # 最多显示 3 个
            })
            feature_contributions["linguistic"] = linguistic_contrib

        # 生成决策依据说明
        decision_rationale = self._generate_decision_rationale(
            detection_result, linguistic_features, feature_contributions
        )

        # 识别不确定性来源
        uncertainty_factors = []
        if 0.4 <= detection_result.ai_probability <= 0.6:
            uncertainty_factors.append("AI 概率处于模糊区域 (40%-60%)")
        if len(linguistic_features.ai_indicators) <= 1:
            uncertainty_factors.append("AI 语言学指示器较少")
        if detection_result.label_matches is False:
            uncertainty_factors.append("检测结果与现有标注不一致")

        # 生成建议操作
        if detection_result.ai_probability >= 0.8:
            recommended_action = "flag_as_ai"
        elif detection_result.ai_probability <= 0.2:
            recommended_action = "approve_as_human"
        elif len(uncertainty_factors) >= 2:
            recommended_action = "manual_review"
        else:
            recommended_action = "monitor"

        return ExplainabilityReport(
            content_id=content_id,
            detection_id=detection_result.id,
            is_ai_generated=detection_result.is_ai_generated,
            ai_probability=detection_result.ai_probability,
            confidence=detection_result.confidence.value,
            evidence=evidence,
            feature_weights=feature_contributions,
            decision_rationale=decision_rationale,
            uncertainty_factors=uncertainty_factors,
            recommended_action=recommended_action
        )

    def _generate_decision_rationale(
        self,
        detection_result: AIDetectionResult,
        linguistic_features: LinguisticFeatures,
        feature_contributions: Dict[str, float]
    ) -> str:
        """生成决策依据说明"""
        reasons = []

        # 基于主要贡献特征生成说明
        sorted_features = sorted(
            feature_contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )

        for feature, contribution in sorted_features[:3]:
            if feature == "perplexity":
                if detection_result.perplexity_score < 0.4:
                    reasons.append("文本困惑度较低，用词可预测性高")
                else:
                    reasons.append("文本困惑度正常")
            elif feature == "burstiness":
                if detection_result.burstiness_score < 0.4:
                    reasons.append("句子长度变化较小，结构过于均匀")
                else:
                    reasons.append("句子长度变化正常")
            elif feature == "pattern":
                if detection_result.pattern_score > 0.5:
                    reasons.append("检测到 AI 常见写作模式")
                else:
                    reasons.append("未发现明显 AI 模式")
            elif feature == "linguistic":
                if linguistic_features.ai_indicators:
                    indicator_names = [i["indicator"] for i in linguistic_features.ai_indicators[:2]]
                    reasons.append(f"发现 AI 指示器：{', '.join(indicator_names)}")
                else:
                    reasons.append("未发现明显 AI 语言学指示器")

        # 综合判定
        if detection_result.ai_probability >= 0.6:
           判定 = "可能是 AI 生成"
        elif detection_result.ai_probability <= 0.4:
            判定 = "可能是人类创作"
        else:
            判定 = "无法确定，建议人工复核"

        return f"判定：{判定}。依据：{'; '.join(reasons)}"

    async def get_quality_score(
        self,
        content_id: str
    ) -> Optional[QualityScore]:
        """
        获取内容的质量评分

        Args:
            content_id: 内容 ID

        Returns:
            Optional[QualityScore]: 质量评分
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
            return None

        # 获取内容文本
        content_text = await self._get_content_text(content_id, detection.content_type)
        if not content_text:
            return None

        # 重新计算质量评分
        linguistic_features = await self._analyze_linguistic_features(content_id, content_text)

        detection_result = AIDetectionResult(
            id=detection.id,
            content_id=detection.content_id,
            content_type=detection.content_type,
            is_ai_generated=detection.is_ai_generated,
            ai_probability=detection.ai_probability,
            confidence=DetectionConfidence(detection.confidence),
            detection_methods=[AIDetectionMethod(m) for m in detection.detection_methods],
            detection_models=[AIDetectionModel(m) for m in detection.detection_models],
            analysis_details=detection.analysis_details,
            perplexity_score=detection.perplexity_score,
            burstiness_score=detection.burstiness_score,
            pattern_score=detection.pattern_score,
            semantic_score=detection.semantic_score,
            has_label=detection.has_label,
            label_matches=detection.label_matches,
            detector_id=detection.detector_id,
            detected_at=detection.detected_at
        )

        return await self._calculate_quality_score(
            content_id=content_id,
            content_type=detection.content_type,
            content_text=content_text,
            detection_result=detection_result,
            linguistic_features=linguistic_features
        )

    async def get_explainability_report(
        self,
        content_id: str
    ) -> Optional[ExplainabilityReport]:
        """
        获取检测结果的可解释性报告

        Args:
            content_id: 内容 ID

        Returns:
            Optional[ExplainabilityReport]: 可解释性报告
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
            return None

        # 获取内容文本
        content_text = await self._get_content_text(content_id, detection.content_type)
        if not content_text:
            return None

        # 计算语言学特征
        linguistic_features = await self._analyze_linguistic_features(content_id, content_text)

        detection_result = AIDetectionResult(
            id=detection.id,
            content_id=detection.content_id,
            content_type=detection.content_type,
            is_ai_generated=detection.is_ai_generated,
            ai_probability=detection.ai_probability,
            confidence=DetectionConfidence(detection.confidence),
            detection_methods=[AIDetectionMethod(m) for m in detection.detection_methods],
            detection_models=[AIDetectionModel(m) for m in detection.detection_models],
            analysis_details=detection.analysis_details,
            perplexity_score=detection.perplexity_score,
            burstiness_score=detection.burstiness_score,
            pattern_score=detection.pattern_score,
            semantic_score=detection.semantic_score,
            has_label=detection.has_label,
            label_matches=detection.label_matches,
            detector_id=detection.detector_id,
            detected_at=detection.detected_at
        )

        quality_score = await self._calculate_quality_score(
            content_id=content_id,
            content_type=detection.content_type,
            content_text=content_text,
            detection_result=detection_result,
            linguistic_features=linguistic_features
        )

        return await self._generate_explainability_report(
            content_id=content_id,
            detection_result=detection_result,
            linguistic_features=linguistic_features,
            quality_score=quality_score
        )

    async def _get_content_text(
        self,
        content_id: str,
        content_type: str
    ) -> Optional[str]:
        """获取内容文本"""
        try:
            if content_type == "post":
                result = await self.db.execute(
                    select(DBPost).where(DBPost.id == content_id)
                )
                post = result.scalar_one_or_none()
                if post:
                    return f"{post.title} {post.content}"
            elif content_type == "comment":
                result = await self.db.execute(
                    select(DBComment).where(DBComment.id == content_id)
                )
                comment = result.scalar_one_or_none()
                if comment:
                    return comment.content
        except Exception as e:
            logger.error(f"获取内容文本失败：{e}")
        return None

    async def batch_quality_scan(
        self,
        content_ids: List[str],
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        批量质量扫描

        Args:
            content_ids: 内容 ID 列表
            batch_size: 批次大小

        Returns:
            Dict[str, Any]: 批量扫描结果
        """
        results = {
            "total": len(content_ids),
            "processed": 0,
            "quality_distribution": {
                "excellent": 0,
                "good": 0,
                "fair": 0,
                "poor": 0
            },
            "avg_quality_score": 0.0,
            "ai_detected_count": 0,
            "details": []
        }

        total_quality = 0.0

        for i in range(0, len(content_ids), batch_size):
            batch = content_ids[i:i + batch_size]
            for content_id in batch:
                try:
                    quality_score = await self.get_quality_score(content_id)
                    if quality_score:
                        results["processed"] += 1
                        results["quality_distribution"][quality_score.quality_tier] += 1
                        total_quality += quality_score.overall_score
                        if quality_score.ai_probability >= 0.6:
                            results["ai_detected_count"] += 1

                        results["details"].append({
                            "content_id": content_id,
                            "quality_score": quality_score.overall_score,
                            "quality_tier": quality_score.quality_tier,
                            "ai_probability": quality_score.ai_probability
                        })
                except Exception as e:
                    logger.error(f"处理 {content_id} 失败：{e}")

        if results["processed"] > 0:
            results["avg_quality_score"] = round(
                total_quality / results["processed"], 2
            )

        return results


# 全局服务实例
_quality_detection_service: Optional[QualityDetectionService] = None


def get_quality_detection_service(db: AsyncSession) -> QualityDetectionService:
    """获取质量检测服务实例"""
    global _quality_detection_service
    if _quality_detection_service is None or _quality_detection_service.db is not db:
        _quality_detection_service = QualityDetectionService(db)
    return _quality_detection_service


