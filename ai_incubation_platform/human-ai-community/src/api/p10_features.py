"""
P10 API 路由：自动 AI 检测集成

提供以下功能：
- AI 内容检测
- 批量扫描未标注内容
- 检测争议提交与处理
- 检测统计与报告
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import db_manager
from sqlalchemy.ext.asyncio import AsyncSession
from services.ai_detection_service import get_ai_detection_service, AIDetectionService
from models.p10_entities import (
    AIDetectionMethod, AIDetectionModel, DetectionConfidence,
    AIDisputeType, AIDetectionStats
)

router = APIRouter(prefix="/api/p10", tags=["p10-ai-detection"])


# ==================== 请求/响应模型 ====================

class DetectContentRequest(BaseModel):
    """内容检测请求"""
    content_id: str = Field(..., description="内容 ID")
    content_type: str = Field(..., description="内容类型：post/comment")
    content_text: str = Field(..., description="内容文本")


class CreateDisputeRequest(BaseModel):
    """创建争议请求"""
    content_id: str = Field(..., description="内容 ID")
    dispute_type: str = Field(..., description="争议类型")
    description: str = Field(..., description="争议描述")
    evidence: Optional[List[str]] = Field(default=None, description="证据列表")


class ResolveDisputeRequest(BaseModel):
    """处理争议请求"""
    resolution: str = Field(..., description="处理结果描述")
    final_determination: str = Field(..., description="最终裁定：confirmed/overturned")
    review_result: Optional[Dict[str, Any]] = Field(default=None, description="复核结果")


class ScanContentRequest(BaseModel):
    """扫描内容请求"""
    batch_size: int = Field(default=100, description="批次大小")
    content_type: Optional[str] = Field(default=None, description="内容类型过滤")


# ==================== AI 检测功能 ====================

@router.post("/detect")
async def detect_content(request: DetectContentRequest):
    """
    检测内容是否由 AI 生成

    使用多种检测方法：
    - 困惑度分析：AI 文本通常困惑度较低
    - 爆发度分析：AI 文本句子长度更均匀
    - 模式分析：检测 AI 常见写作模式
    - 语义分析：检测缺乏个人经历和情感表达
    """
    async with db_manager._session_factory() as session:
        service = get_ai_detection_service(session)

        # 检查是否已有标注
        from db.models import DBContentLabel
        from sqlalchemy import select
        result = await session.execute(
            select(DBContentLabel)
            .where(DBContentLabel.content_id == request.content_id)
        )
        existing_label = result.scalar_one_or_none()
        label_dict = None
        if existing_label:
            label_dict = {
                "author_type": existing_label.author_type,
                "ai_assist_level": existing_label.ai_assist_level
            }

        detection = await service.detect_content(
            content_id=request.content_id,
            content_type=request.content_type,
            content_text=request.content_text,
            existing_label=label_dict
        )

        return {
            "success": True,
            "detection": {
                "id": detection.id,
                "content_id": detection.content_id,
                "content_type": detection.content_type,
                "is_ai_generated": detection.is_ai_generated,
                "ai_probability": detection.ai_probability,
                "confidence": detection.confidence.value,
                "detection_methods": [m.value for m in detection.detection_methods],
                "analysis_details": detection.analysis_details,
                "has_label": detection.has_label,
                "label_matches": detection.label_matches,
                "detected_at": detection.detected_at.isoformat()
            }
        }


@router.post("/scan")
async def scan_unlabeled_content(request: ScanContentRequest):
    """
    批量扫描未标注 AI 标签的内容

    可指定内容类型过滤（post/comment），默认扫描两者
    """
    async with db_manager._session_factory() as session:
        service = get_ai_detection_service(session)
        results = await service.scan_unlabeled_content(
            batch_size=request.batch_size,
            content_type=request.content_type
        )

        return {
            "success": True,
            "scan_results": results
        }


@router.get("/detection/{content_id}")
async def get_content_detection(
    content_id: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """获取内容的检测历史"""
    async with db_manager._session_factory() as session:
        service = get_ai_detection_service(session)
        detections = await service.get_content_detection(
            content_id=content_id,
            limit=limit
        )

        return {
            "success": True,
            "detections": [
                {
                    "id": d.id,
                    "ai_probability": d.ai_probability,
                    "is_ai_generated": d.is_ai_generated,
                    "confidence": d.confidence.value,
                    "detected_at": d.detected_at.isoformat()
                }
                for d in detections
            ]
        }


# ==================== 争议处理功能 ====================

@router.post("/dispute")
async def create_dispute(request: CreateDisputeRequest, user_id: str = Query(...)):
    """
    提交 AI 检测争议

    用户可对检测结果提出异议，支持以下争议类型：
    - false_positive: 误报（人类内容被检为 AI）
    - false_negative: 漏报（AI 内容未被检出）
    - label_dispute: 标注争议
    - appeal: 申诉
    """
    try:
        dispute_type = AIDisputeType(request.dispute_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的争议类型，可选值：{[t.value for t in AIDisputeType]}"
        )

    async with db_manager._session_factory() as session:
        service = get_ai_detection_service(session)

        # 先检测内容（如果还没有检测结果）
        from db.p10_models import DBAIDetection
        from sqlalchemy import select
        result = await session.execute(
            select(DBAIDetection)
            .where(DBAIDetection.content_id == request.content_id)
            .limit(1)
        )
        existing_detection = result.scalar_one_or_none()

        if not existing_detection:
            # 需要先检测
            raise HTTPException(
                status_code=400,
                detail="该内容尚未进行检测，请先调用 /detect 接口"
            )

        dispute = await service.create_dispute(
            content_id=request.content_id,
            content_type="post",  # TODO: 从数据库获取
            submitter_id=user_id,
            dispute_type=dispute_type,
            description=request.description,
            evidence=request.evidence
        )

        return {
            "success": True,
            "dispute": {
                "dispute_id": dispute.dispute_id,
                "status": dispute.status,
                "message": "争议已提交，等待审核"
            }
        }


@router.post("/dispute/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    request: ResolveDisputeRequest,
    resolver_id: str = Query(...)
):
    """
    处理 AI 检测争议

    管理员可审查争议并做出最终裁定：
    - confirmed: 维持原检测结果
    - overturned: 推翻原检测结果
    """
    async with db_manager._session_factory() as session:
        service = get_ai_detection_service(session)

        try:
            result = await service.resolve_dispute(
                dispute_id=dispute_id,
                resolver_id=resolver_id,
                resolution=request.resolution,
                final_determination=request.final_determination,
                review_result=request.review_result
            )

            return {
                "success": True,
                "resolution": {
                    "dispute_id": result.dispute_id,
                    "status": result.status,
                    "reason": result.reason,
                    "action_taken": result.action_taken,
                    "detection_updated": result.detection_updated,
                    "label_updated": result.label_updated
                }
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/disputes")
async def get_disputes(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100)
):
    """获取争议列表"""
    async with db_manager._session_factory() as session:
        service = get_ai_detection_service(session)
        disputes = await service.get_disputes(status=status, limit=limit)

        return {
            "success": True,
            "disputes": [
                {
                    "dispute_id": d.dispute_id,
                    "content_id": d.content_id,
                    "dispute_type": d.dispute_type.value,
                    "status": d.status,
                    "submitter_id": d.submitter_id,
                    "created_at": d.created_at.isoformat(),
                    "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
                    "final_determination": d.final_determination
                }
                for d in disputes
            ]
        }


# ==================== 统计与报告 ====================

@router.get("/stats")
async def get_detection_stats():
    """
    获取 AI 检测统计信息

    包含：
    - 总扫描数、AI 检出数
    - 按置信度分布
    - 争议统计
    - 误报率
    - 扫描覆盖率
    """
    async with db_manager._session_factory() as session:
        service = get_ai_detection_service(session)
        stats = await service.get_detection_stats()

        return {
            "success": True,
            "stats": {
                "total_scanned": stats.total_scanned,
                "ai_detected": stats.ai_detected,
                "human_verified": stats.human_verified,
                "uncertain": stats.uncertain,
                "by_confidence": stats.by_confidence,
                "total_disputes": stats.total_disputes,
                "resolved_disputes": stats.resolved_disputes,
                "overturned_detections": stats.overturned_detections,
                "false_positive_rate": stats.false_positive_rate,
                "scan_coverage_rate": stats.scan_coverage_rate
            }
        }


@router.get("/methods")
async def get_detection_methods():
    """获取检测方法说明"""
    return {
        "success": True,
        "methods": [
            {
                "name": m.value,
                "description": _get_method_description(m)
            }
            for m in AIDetectionMethod
        ]
    }


@router.get("/models")
async def get_detection_models():
    """获取检测模型说明"""
    return {
        "success": True,
        "models": [
            {
                "name": m.value,
                "description": _get_model_description(m)
            }
            for m in AIDetectionModel
        ]
    }


@router.get("/confidence-levels")
async def get_confidence_levels():
    """获取置信度等级说明"""
    return {
        "success": True,
        "levels": [
            {
                "name": c.value,
                "probability_range": _get_confidence_range(c),
                "description": _get_confidence_description(c)
            }
            for c in DetectionConfidence
        ]
    }


def _get_method_description(method: AIDetectionMethod) -> str:
    """获取检测方法说明"""
    descriptions = {
        AIDetectionMethod.STATISTICAL: "基于统计特征（困惑度、爆发度）分析",
        AIDetectionMethod.MODEL_BASED: "使用专门训练的 AI 检测模型",
        AIDetectionMethod.WATERMARK: "检测 AI 模型水印信号",
        AIDetectionMethod.METADATA: "分析内容元数据特征",
        AIDetectionMethod.ENSEMBLE: "集成多种检测方法综合判断",
        AIDetectionMethod.PATTERN: "检测 AI 常见写作模式和短语",
        AIDetectionMethod.SEMANTIC: "分析语义特征和情感表达"
    }
    return descriptions.get(method, "未知检测方法")


def _get_model_description(model: AIDetectionModel) -> str:
    """获取检测模型说明"""
    descriptions = {
        AIDetectionModel.OPENAI_CLASSIFIER: "OpenAI 官方 AI 文本分类器",
        AIDetectionModel.GPTZERO: "GPTZero 检测服务",
        AIDetectionModel.ORIGINALITY_AI: "Originality.ai 专业检测",
        AIDetectionModel.COHERE_DETOX: "Cohere Detoxify 模型",
        AIDetectionModel.CUSTOM_TRANSFORMER: "自研 Transformer 检测模型",
        AIDetectionModel.RULE_BASED: "基于规则的启发式检测"
    }
    return descriptions.get(model, "未知检测模型")


def _get_confidence_range(confidence: DetectionConfidence) -> str:
    """获取置信度对应的概率范围"""
    ranges = {
        DetectionConfidence.VERY_HIGH: "80-100%",
        DetectionConfidence.HIGH: "60-80%",
        DetectionConfidence.MEDIUM: "40-60%",
        DetectionConfidence.LOW: "20-40%",
        DetectionConfidence.VERY_LOW: "0-20%"
    }
    return ranges.get(confidence, "未知")


def _get_confidence_description(confidence: DetectionConfidence) -> str:
    """获取置信度说明"""
    descriptions = {
        DetectionConfidence.VERY_HIGH: "极高置信度，检测结果非常可靠",
        DetectionConfidence.HIGH: "高置信度，检测结果较可靠",
        DetectionConfidence.MEDIUM: "中等置信度，建议人工复核",
        DetectionConfidence.LOW: "低置信度，可能是人类创作",
        DetectionConfidence.VERY_LOW: "极低置信度，基本确认为人类创作"
    }
    return descriptions.get(confidence, "未知置信度")
