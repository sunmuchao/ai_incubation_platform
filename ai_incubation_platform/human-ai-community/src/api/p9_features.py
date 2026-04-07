"""
P9 AI 内容标注与身份标识 API
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import db_manager
from services.content_labeling_service import get_content_labeling_service
from models.p9_entities import (
    AuthorType, AIAssistLevel, AIAssistType,
    ContentLabel, AIAssistRecord,
    ContentLabelCreate, ContentLabelUpdate, AIAssistCreate,
    ContentTransparencyReport, AIAssistStats, AuthorTypeStats
)

router = APIRouter(prefix="/api/p9", tags=["P9-AI 内容标注"])


class ContentLabelResponse(BaseModel):
    """内容标签响应"""
    success: bool
    data: Optional[ContentLabel] = None
    message: Optional[str] = None


class ContentLabelListResponse(BaseModel):
    """内容标签列表响应"""
    success: bool
    data: List[ContentLabel]
    total: int


class AIAssistRecordResponse(BaseModel):
    """AI 辅助记录响应"""
    success: bool
    data: Optional[AIAssistRecord] = None
    message: Optional[str] = None


class AIAssistRecordListResponse(BaseModel):
    """AI 辅助记录列表响应"""
    success: bool
    data: List[AIAssistRecord]
    total: int


class TransparencyReportResponse(BaseModel):
    """透明度报告响应"""
    success: bool
    data: Optional[ContentTransparencyReport] = None
    message: Optional[str] = None


class StatsResponse(BaseModel):
    """统计响应"""
    success: bool
    data: Dict[str, Any]


@router.post("/content-label", response_model=ContentLabelResponse)
async def create_content_label(
    label_data: ContentLabelCreate
):
    """
    创建内容标签

    用于标注内容的作者类型和 AI 辅助信息
    """
    try:
        async with db_manager.get_session() as db:
            service = get_content_labeling_service(db)
            label = await service.create_content_label(label_data)
            await db.commit()
            return ContentLabelResponse(success=True, data=label)
    except Exception as e:
        return ContentLabelResponse(success=False, message=str(e))


@router.get("/content-label/{content_id}", response_model=ContentLabelResponse)
async def get_content_label(content_id: str):
    """
    获取内容标签

    通过内容 ID 查询标签信息
    """
    try:
        async with db_manager.get_session() as db:
            service = get_content_labeling_service(db)
            label = await service.get_content_label(content_id)
            if label:
                return ContentLabelResponse(success=True, data=label)
            else:
                return ContentLabelResponse(success=False, message="标签不存在")
    except Exception as e:
        return ContentLabelResponse(success=False, message=str(e))


@router.put("/content-label/{content_id}", response_model=ContentLabelResponse)
async def update_content_label(
    content_id: str,
    update_data: ContentLabelUpdate
):
    """
    更新内容标签

    更新内容的标签信息
    """
    try:
        async with db_manager.get_session() as db:
            service = get_content_labeling_service(db)
            label = await service.update_content_label(content_id, update_data)
            if label:
                await db.commit()
                return ContentLabelResponse(success=True, data=label)
            else:
                return ContentLabelResponse(success=False, message="标签不存在")
    except Exception as e:
        return ContentLabelResponse(success=False, message=str(e))


@router.post("/ai-assist-record", response_model=AIAssistRecordResponse)
async def create_ai_assist_record(
    record_data: AIAssistCreate
):
    """
    创建 AI 辅助记录

    记录 AI 辅助创作的详细过程
    """
    try:
        async with db_manager.get_session() as db:
            service = get_content_labeling_service(db)
            record = await service.create_ai_assist_record(record_data)
            await db.commit()
            return AIAssistRecordResponse(success=True, data=record)
    except Exception as e:
        return AIAssistRecordResponse(success=False, message=str(e))


@router.get("/ai-assist-record/{content_id}", response_model=AIAssistRecordListResponse)
async def get_ai_assist_records(content_id: str):
    """
    获取 AI 辅助记录列表

    获取指定内容的所有 AI 辅助记录
    """
    try:
        async with db_manager.get_session() as db:
            service = get_content_labeling_service(db)
            records = await service.get_assist_records_by_content(content_id)
            return AIAssistRecordListResponse(success=True, data=records, total=len(records))
    except Exception as e:
        return AIAssistRecordListResponse(success=False, data=[], message=str(e))


@router.get("/transparency-report/{content_id}", response_model=TransparencyReportResponse)
async def get_transparency_report(content_id: str):
    """
    获取内容透明度报告

    获取完整的内容透明度信息，包括 AI 辅助历史和透明度评分
    """
    try:
        async with db_manager.get_session() as db:
            service = get_content_labeling_service(db)
            report = await service.get_transparency_report(content_id)
            if report:
                return TransparencyReportResponse(success=True, data=report)
            else:
                return TransparencyReportResponse(success=False, message="未找到标签信息")
    except Exception as e:
        return TransparencyReportResponse(success=False, message=str(e))


@router.get("/stats/overview", response_model=StatsResponse)
async def get_stats_overview():
    """
    获取 AI 辅助统计概览

    获取平台 AI 辅助内容的统计数据
    """
    try:
        async with db_manager.get_session() as db:
            service = get_content_labeling_service(db)
            stats = await service.get_stats_overview()
            return StatsResponse(
                success=True,
                data={
                    "total_assisted_content": stats.total_assisted_content,
                    "by_level": stats.by_level,
                    "by_type": stats.by_type,
                    "avg_ai_participation": stats.avg_ai_participation,
                    "top_ai_models": stats.top_ai_models,
                    "transparency_rate": stats.transparency_rate,
                }
            )
    except Exception as e:
        return StatsResponse(success=False, data={}, message=str(e))


@router.get("/stats/author-type", response_model=StatsResponse)
async def get_author_type_stats():
    """
    获取作者类型统计

    获取内容按作者类型（人类/AI/混合）的分布统计
    """
    try:
        async with db_manager.get_session() as db:
            service = get_content_labeling_service(db)
            stats = await service.get_author_type_stats()
            return StatsResponse(
                success=True,
                data={
                    "total_content": stats.total_content,
                    "human_created": stats.human_created,
                    "ai_generated": stats.ai_generated,
                    "hybrid_created": stats.hybrid_created,
                    "human_percentage": stats.human_percentage,
                    "ai_percentage": stats.ai_percentage,
                    "hybrid_percentage": stats.hybrid_percentage,
                }
            )
    except Exception as e:
        return StatsResponse(success=False, data={}, message=str(e))


@router.get("/ai-assist-levels", response_model=StatsResponse)
async def get_ai_assist_levels():
    """
    获取 AI 辅助程度说明

    返回 AI 辅助程度的定义和阈值
    """
    levels = {
        AIAssistLevel.NONE.value: {
            "description": "无 AI 辅助",
            "range": "0%",
            "icon": "👤"
        },
        AIAssistLevel.MINIMAL.value: {
            "description": "轻微辅助",
            "range": "1-25%",
            "icon": "✨"
        },
        AIAssistLevel.MODERATE.value: {
            "description": "中度辅助",
            "range": "26-50%",
            "icon": "🤝"
        },
        AIAssistLevel.SUBSTANTIAL.value: {
            "description": "大量辅助",
            "range": "51-75%",
            "icon": "🤖"
        },
        AIAssistLevel.HIGH.value: {
            "description": "高度辅助",
            "range": "76-99%",
            "icon": "🤖"
        },
        AIAssistLevel.FULL.value: {
            "description": "完全 AI 生成",
            "range": "100%",
            "icon": "🤖"
        },
    }
    return StatsResponse(success=True, data={"levels": levels})


@router.get("/author-types", response_model=StatsResponse)
async def get_author_types():
    """
    获取作者类型说明

    返回作者类型的定义
    """
    types = {
        AuthorType.HUMAN.value: {
            "description": "纯人类创作",
            "icon": "👤",
            "badge": "人类创作"
        },
        AuthorType.AI.value: {
            "description": "纯 AI 生成内容",
            "icon": "🤖",
            "badge": "AI 生成"
        },
        AuthorType.HYBRID.value: {
            "description": "人机协作（人类创作+AI 辅助）",
            "icon": "🤝",
            "badge": "人机协作"
        },
    }
    return StatsResponse(success=True, data={"types": types})
