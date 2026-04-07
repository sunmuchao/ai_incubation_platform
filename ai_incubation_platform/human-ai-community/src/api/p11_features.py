"""
P11 API 路由：AI 生成内容质量检测增强

在 P10 基础检测能力之上，提供质量增强功能：
1. 带质量评估的 AI 检测
2. 语言学特征分析
3. 质量评分查询
4. 可解释性报告
5. 批量质量扫描
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import db_manager
from sqlalchemy.ext.asyncio import AsyncSession
from services.quality_detection_service import (
    get_quality_detection_service,
    QualityDetectionService,
    QualityScore,
    ExplainabilityReport,
    LinguisticFeatures
)

router = APIRouter(prefix="/api/p11", tags=["p11-quality-detection"])


# ==================== 请求/响应模型 ====================

class DetectWithQualityRequest(BaseModel):
    """带质量检测的请求"""
    content_id: str = Field(..., description="内容 ID")
    content_type: str = Field(..., description="内容类型：post/comment")
    content_text: str = Field(..., description="内容文本")


class DetectWithQualityResponse(BaseModel):
    """带质量检测的响应"""
    success: bool
    detection: Dict[str, Any]
    quality_score: Dict[str, Any]
    explainability_report: Dict[str, Any]


class BatchQualityScanRequest(BaseModel):
    """批量质量扫描请求"""
    content_ids: List[str] = Field(..., description="内容 ID 列表")
    batch_size: int = Field(default=10, description="批次大小")


# ==================== 质量检测功能 ====================

@router.post("/detect-with-quality", response_model=DetectWithQualityResponse)
async def detect_with_quality(request: DetectWithQualityRequest):
    """
    带质量评估的 AI 检测

    在基础 AI 检测之上，提供：
    - 多维度质量评分（原创性、深度、真实性、互动性）
    - 语言学特征分析
    - 可解释性报告
    - 建议操作

    适用于需要高质量内容审核的场景
    """
    async with db_manager._session_factory() as session:
        service = get_quality_detection_service(session)

        try:
            detection_result, quality_score, explain_report = await service.detect_with_quality(
                content_id=request.content_id,
                content_type=request.content_type,
                content_text=request.content_text
            )

            return DetectWithQualityResponse(
                success=True,
                detection={
                    "id": detection_result.id,
                    "content_id": detection_result.content_id,
                    "content_type": detection_result.content_type,
                    "is_ai_generated": detection_result.is_ai_generated,
                    "ai_probability": detection_result.ai_probability,
                    "confidence": detection_result.confidence.value,
                    "detection_methods": [m.value for m in detection_result.detection_methods],
                    "perplexity_score": detection_result.perplexity_score,
                    "burstiness_score": detection_result.burstiness_score,
                    "pattern_score": detection_result.pattern_score,
                    "semantic_score": detection_result.semantic_score,
                    "detected_at": detection_result.detected_at.isoformat()
                },
                quality_score={
                    "content_id": quality_score.content_id,
                    "content_type": quality_score.content_type,
                    "overall_score": quality_score.overall_score,
                    "originality_score": quality_score.originality_score,
                    "depth_score": quality_score.depth_score,
                    "authenticity_score": quality_score.authenticity_score,
                    "engagement_score": quality_score.engagement_score,
                    "quality_tier": quality_score.quality_tier,
                    "ai_probability": quality_score.ai_probability,
                    "evaluated_at": quality_score.evaluated_at.isoformat()
                },
                explainability_report={
                    "content_id": explain_report.content_id,
                    "detection_id": explain_report.detection_id,
                    "is_ai_generated": explain_report.is_ai_generated,
                    "ai_probability": explain_report.ai_probability,
                    "confidence": explain_report.confidence,
                    "evidence": explain_report.evidence,
                    "feature_weights": explain_report.feature_weights,
                    "decision_rationale": explain_report.decision_rationale,
                    "uncertainty_factors": explain_report.uncertainty_factors,
                    "recommended_action": explain_report.recommended_action,
                    "generated_at": explain_report.generated_at.isoformat()
                }
            )
        except Exception as e:
            logger.error(f"质量检测失败：{e}")
            raise HTTPException(status_code=500, detail=f"质量检测失败：{str(e)}")


@router.get("/quality-score/{content_id}")
async def get_quality_score(content_id: str):
    """
    获取内容的质量评分

    返回内容的多维度质量评分：
    - 原创性：基于词汇丰富度和 AI 概率
    - 深度：基于句子复杂度和连贯性
    - 真实性：基于个人风格和情感表达
    - 互动性：基于连接词和可读性
    """
    async with db_manager._session_factory() as session:
        service = get_quality_detection_service(session)

        quality_score = await service.get_quality_score(content_id)

        if not quality_score:
            raise HTTPException(
                status_code=404,
                detail=f"未找到内容 {content_id} 的质量评分，请先进行检测"
            )

        return {
            "success": True,
            "quality_score": {
                "content_id": quality_score.content_id,
                "content_type": quality_score.content_type,
                "overall_score": quality_score.overall_score,
                "originality_score": quality_score.originality_score,
                "depth_score": quality_score.depth_score,
                "authenticity_score": quality_score.authenticity_score,
                "engagement_score": quality_score.engagement_score,
                "quality_tier": quality_score.quality_tier,
                "ai_probability": quality_score.ai_probability,
                "detection_confidence": quality_score.detection_confidence,
                "evaluated_at": quality_score.evaluated_at.isoformat()
            }
        }


@router.get("/explainability-report/{content_id}")
async def get_explainability_report(content_id: str):
    """
    获取检测结果的可解释性报告

    提供详细的决策依据：
    - 关键特征证据
    - 特征权重分析
    - 决策依据说明
    - 不确定性来源
    - 建议操作
    """
    async with db_manager._session_factory() as session:
        service = get_quality_detection_service(session)

        report = await service.get_explainability_report(content_id)

        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"未找到内容 {content_id} 的可解释性报告"
            )

        return {
            "success": True,
            "report": {
                "content_id": report.content_id,
                "detection_id": report.detection_id,
                "is_ai_generated": report.is_ai_generated,
                "ai_probability": report.ai_probability,
                "confidence": report.confidence,
                "evidence": report.evidence,
                "feature_weights": report.feature_weights,
                "decision_rationale": report.decision_rationale,
                "uncertainty_factors": report.uncertainty_factors,
                "recommended_action": report.recommended_action,
                "generated_at": report.generated_at.isoformat()
            }
        }


@router.post("/analyze-linguistic-features")
async def analyze_linguistic_features(
    content_id: str = Query(...),
    content_text: str = Query(...)
):
    """
    分析内容的语言学特征

    提供详细的语言学分析：
    - 词汇特征：丰富度、平均词长、独特词比例
    - 句法特征：复杂度、平均句长、句长方差
    - 语篇特征：连贯性、连接词使用
    - 风格特征：正式程度、情感色调、个人风格
    - AI 指示器：7 种常见 AI 写作模式
    """
    async with db_manager._session_factory() as session:
        service = get_quality_detection_service(session)

        features = await service._analyze_linguistic_features(content_id, content_text)

        return {
            "success": True,
            "linguistic_features": {
                "content_id": features.content_id,
                "vocabulary": {
                    "richness": features.vocabulary_richness,
                    "avg_word_length": features.avg_word_length,
                    "unique_word_ratio": features.unique_word_ratio
                },
                "syntax": {
                    "complexity": features.sentence_complexity,
                    "avg_sentence_length": features.avg_sentence_length,
                    "length_variance": features.sentence_length_variance
                },
                "discourse": {
                    "coherence": features.coherence_score,
                    "transition_usage": features.transition_usage
                },
                "style": {
                    "formality": features.formality_level,
                    "emotional_tone": features.emotional_tone,
                    "personal_voice": features.personal_voice
                },
                "ai_indicators": features.ai_indicators,
                "analyzed_at": features.analyzed_at.isoformat()
            }
        }


@router.post("/batch-scan")
async def batch_quality_scan(request: BatchQualityScanRequest):
    """
    批量质量扫描

    对多个内容进行批量质量评估，返回：
    - 总处理数量
    - 质量等级分布
    - 平均质量评分
    - AI 检出数量
    - 详细内容列表
    """
    async with db_manager._session_factory() as session:
        service = get_quality_detection_service(session)

        results = await service.batch_quality_scan(
            content_ids=request.content_ids,
            batch_size=request.batch_size
        )

        return {
            "success": True,
            "batch_results": results
        }


@router.get("/quality-distribution")
async def get_quality_distribution(
    content_type: Optional[str] = Query(default=None, description="内容类型过滤"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """
    获取质量等级分布统计

    统计不同质量等级的内容分布情况
    """
    async with db_manager._session_factory() as session:
        service = get_quality_detection_service(session)

        # 获取所有内容
        from db.models import DBPost, DBComment
        from sqlalchemy import select

        content_ids = []

        if content_type is None or content_type == "post":
            result = await session.execute(select(DBPost.id).limit(limit))
            content_ids.extend([r[0] for r in result.all()])

        if content_type is None or content_type == "comment":
            result = await session.execute(select(DBComment.id).limit(limit))
            content_ids.extend([r[0] for r in result.all()])

        if not content_ids:
            return {
                "success": True,
                "distribution": {
                    "excellent": 0,
                    "good": 0,
                    "fair": 0,
                    "poor": 0
                },
                "total": 0
            }

        # 批量扫描
        results = await service.batch_quality_scan(content_ids[:50], batch_size=10)

        return {
            "success": True,
            "distribution": results["quality_distribution"],
            "avg_quality_score": results["avg_quality_score"],
            "total": results["processed"]
        }


@router.get("/quality-tiers")
async def get_quality_tiers_info():
    """
    获取质量等级说明

    返回各质量等级的定义和阈值
    """
    return {
        "success": True,
        "tiers": {
            "excellent": {
                "name": "优秀",
                "threshold": "85-100",
                "description": "高度原创、深度分析、真实表达、强互动性"
            },
            "good": {
                "name": "良好",
                "threshold": "70-84",
                "description": "较好原创性、一定深度、较真实、较好互动"
            },
            "fair": {
                "name": "一般",
                "threshold": "50-69",
                "description": "中等原创性、浅层分析、一般表达"
            },
            "poor": {
                "name": "较差",
                "threshold": "0-49",
                "description": "原创性低、缺乏深度、表达生硬"
            }
        },
        "dimensions": {
            "originality": {
                "name": "原创性",
                "weight": 0.25,
                "factors": ["词汇丰富度", "独特词比例", "AI 概率"]
            },
            "depth": {
                "name": "深度",
                "weight": 0.20,
                "factors": ["句子复杂度", "连贯性", "内容长度"]
            },
            "authenticity": {
                "name": "真实性",
                "weight": 0.30,
                "factors": ["个人风格", "情感表达", "AI 指示器数量"]
            },
            "engagement": {
                "name": "互动性",
                "weight": 0.25,
                "factors": ["连接词使用", "正式程度", "可读性"]
            }
        }
    }


# 导入 logger
import logging
logger = logging.getLogger(__name__)
