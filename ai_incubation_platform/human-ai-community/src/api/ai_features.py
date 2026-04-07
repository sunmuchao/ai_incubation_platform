"""
AI 深化功能 API 路由

提供 AI 版主、AI 辅助创作、智能推荐等功能
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import db_manager
from sqlalchemy.ext.asyncio import AsyncSession
from services.ai_moderator_service import get_ai_moderator_service, AIModeratorService
from services.ai_assist_service import get_ai_assist_service, AIAssistType
from services.recommendation_service import get_recommendation_service


router = APIRouter(prefix="/api/ai", tags=["ai-features"])


# ==================== 请求/响应模型 ====================

class PolishRequest(BaseModel):
    """润色请求"""
    content: str = Field(..., description="待润色内容")
    style: str = Field(default="formal", description="风格：formal, casual, academic, creative")
    user_id: Optional[str] = Field(None, description="用户 ID")


class ExpandRequest(BaseModel):
    """扩写请求"""
    content: str = Field(..., description="待扩写内容")
    direction: str = Field(default="detail", description="方向：detail, example, explain")
    target_length: Optional[int] = Field(None, description="目标长度")
    user_id: Optional[str] = Field(None, description="用户 ID")


class TranslateRequest(BaseModel):
    """翻译请求"""
    content: str = Field(..., description="待翻译内容")
    target_lang: str = Field(default="en", description="目标语言：en, zh, ja, ko, fr, de, es")
    user_id: Optional[str] = Field(None, description="用户 ID")


class SummarizeRequest(BaseModel):
    """摘要请求"""
    content: str = Field(..., description="待摘要内容")
    max_length: int = Field(default=200, description="最大长度")
    user_id: Optional[str] = Field(None, description="用户 ID")


class GenerateRequest(BaseModel):
    """生成请求"""
    topic: str = Field(..., description="主题")
    style: str = Field(default="normal", description="风格")
    length: str = Field(default="medium", description="长度：short, medium, long")
    user_id: Optional[str] = Field(None, description="用户 ID")


class SuggestRequest(BaseModel):
    """建议请求"""
    content: str = Field(..., description="内容")
    user_id: Optional[str] = Field(None, description="用户 ID")


class AutoModerateRequest(BaseModel):
    """自动审核请求"""
    batch_size: int = Field(default=50, description="批次大小")


class RecommendationRequest(BaseModel):
    """推荐请求"""
    user_id: str = Field(..., description="用户 ID")
    limit: int = Field(default=20, description="返回数量")
    exclude_read: bool = Field(default=True, description="排除已读")


# ==================== AI 版主功能 ====================

@router.post("/moderator/auto-process")
async def auto_process_reports(request: AutoModerateRequest):
    """
    AI 版主自动处理举报

    AI 版主会自动分析举报内容，根据违规概率进行自动处理：
    - 违规概率 >= 85%: 自动确认违规，删除内容
    - 违规概率 <= 30%: 自动忽略举报
    - 30% < 违规概率 < 85%: 标记需人工审核
    """
    async with db_manager._session_factory() as session:
        service = get_ai_moderator_service(session)
        result = await service.auto_process_reports(batch_size=request.batch_size)
        return {
            "success": True,
            "stats": result
        }


@router.get("/moderator/stats")
async def get_moderator_stats():
    """获取 AI 版主统计信息"""
    async with db_manager._session_factory() as session:
        service = get_ai_moderator_service(session)
        stats = await service.get_auto_moderation_stats()
        return {
            "success": True,
            "stats": stats
        }


# ==================== AI 辅助创作功能 ====================

@router.post("/assist/polish")
async def polish_content(request: PolishRequest):
    """
    AI 润色内容

    提供多种风格选择：
    - formal: 正式、专业
    - casual: 轻松、口语化
    - academic: 学术、严谨
    - creative: 创意、生动
    """
    async with db_manager._session_factory() as session:
        service = get_ai_assist_service(session)
        result = await service.polish_content(
            content=request.content,
            style=request.style,
            user_id=request.user_id
        )
        return {
            "success": True,
            "data": result
        }


@router.post("/assist/expand")
async def expand_content(request: ExpandRequest):
    """
    AI 扩写内容

    支持多种扩写方向：
    - detail: 增加更多细节
    - example: 添加具体例子
    - explain: 增加解释说明
    """
    async with db_manager._session_factory() as session:
        service = get_ai_assist_service(session)
        result = await service.expand_content(
            content=request.content,
            direction=request.direction,
            target_length=request.target_length,
            user_id=request.user_id
        )
        return {
            "success": True,
            "data": result
        }


@router.post("/assist/translate")
async def translate_content(request: TranslateRequest):
    """
    AI 翻译内容

    支持的语言：
    - en: 英语
    - zh: 中文
    - ja: 日语
    - ko: 韩语
    - fr: 法语
    - de: 德语
    - es: 西班牙语
    """
    async with db_manager._session_factory() as session:
        service = get_ai_assist_service(session)
        result = await service.translate_content(
            content=request.content,
            target_lang=request.target_lang,
            user_id=request.user_id
        )
        return {
            "success": True,
            "data": result
        }


@router.post("/assist/summarize")
async def summarize_content(request: SummarizeRequest):
    """
    AI 摘要内容

    自动提取内容核心信息，生成简洁概述
    """
    async with db_manager._session_factory() as session:
        service = get_ai_assist_service(session)
        result = await service.summarize_content(
            content=request.content,
            max_length=request.max_length,
            user_id=request.user_id
        )
        return {
            "success": True,
            "data": result
        }


@router.post("/assist/generate")
async def generate_content(request: GenerateRequest):
    """
    AI 生成内容

    根据主题自动生成内容，支持不同风格和长度

    **注意**: AI 生成的内容会明确标注"🤖 AI 生成"标识
    """
    async with db_manager._session_factory() as session:
        service = get_ai_assist_service(session)
        result = await service.generate_content(
            topic=request.topic,
            style=request.style,
            length=request.length,
            user_id=request.user_id
        )
        return {
            "success": True,
            "data": result,
            "ai_generated": True,
            "badge": "🤖 AI 生成"
        }


@router.post("/assist/suggest")
async def get_writing_suggestions(request: SuggestRequest):
    """
    AI 写作建议

    分析内容并提供改进建议：
    - 结构优化
    - 表达清晰度
    - 吸引力提升
    """
    async with db_manager._session_factory() as session:
        service = get_ai_assist_service(session)
        result = await service.get_writing_suggestions(
            content=request.content,
            user_id=request.user_id
        )
        return {
            "success": True,
            "data": result
        }


@router.get("/assist/history")
async def get_assist_history(
    user_id: Optional[str] = Query(None),
    limit: int = Query(default=20, ge=1, le=100)
):
    """获取 AI 辅助历史"""
    async with db_manager._session_factory() as session:
        service = get_ai_assist_service(session)
        history = service.get_assist_history(user_id=user_id, limit=limit)
        return {
            "success": True,
            "history": history
        }


# ==================== 智能推荐功能 ====================

@router.post("/recommend/personalized")
async def get_personalized_recommendations(request: RecommendationRequest):
    """
    个性化推荐

    基于用户兴趣和行为历史生成个性化推荐内容

    推荐算法考虑因素：
    - 用户关注的频道和作者
    - 用户点赞、收藏、评论历史
    - 内容热度
    - 内容时效性
    """
    async with db_manager._session_factory() as session:
        service = get_recommendation_service(session)
        recommendations = await service.get_personalized_recommendations(
            user_id=request.user_id,
            limit=request.limit,
            exclude_read=request.exclude_read
        )
        return {
            "success": True,
            "recommendations": recommendations,
            "algorithm": "personalized_v1"
        }


@router.get("/recommend/hot")
async def get_hot_recommendations(
    limit: int = Query(default=20, ge=1, le=100),
    time_range: str = Query(default="24h", description="时间范围：24h, 7d, 30d")
):
    """
    热门推荐

    基于内容热度算法推荐热门内容

    热度计算公式：
    score = (点赞数×10 + 评论数×5 + 浏览数×0.1) × 时间衰减因子
    """
    async with db_manager._session_factory() as session:
        service = get_recommendation_service(session)
        recommendations = await service.get_hot_recommendations(
            limit=limit,
            time_range=time_range
        )
        return {
            "success": True,
            "recommendations": recommendations,
            "time_range": time_range
        }


@router.get("/recommend/similar/{post_id}")
async def get_similar_content(
    post_id: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    相似内容推荐

    基于内容相似度推荐相关内容

    相似度计算因素：
    - 频道匹配
    - 标题关键词重叠
    - 标签相似度
    """
    async with db_manager._session_factory() as session:
        service = get_recommendation_service(session)
        recommendations = await service.get_similar_content(
            post_id=post_id,
            limit=limit
        )
        return {
            "success": True,
            "recommendations": recommendations,
            "source_post_id": post_id
        }


@router.get("/recommend/channels/{user_id}")
async def get_channel_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    推荐频道

    基于用户兴趣推荐可能感兴趣的频道
    """
    async with db_manager._session_factory() as session:
        service = get_recommendation_service(session)
        recommendations = await service.get_channel_recommendations(
            user_id=user_id,
            limit=limit
        )
        return {
            "success": True,
            "recommendations": recommendations
        }


@router.post("/recommend/refresh-cache")
async def refresh_recommendation_cache():
    """刷新推荐缓存"""
    async with db_manager._session_factory() as session:
        service = get_recommendation_service(session)
        await service.refresh_cache()
        return {
            "success": True,
            "message": "推荐缓存已刷新"
        }
