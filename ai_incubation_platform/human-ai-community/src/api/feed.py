"""
P15 阶段：内容推荐系统增强 - API 路由

v1.15 新增 API 端点：
1. GET /api/feed/personalized - 个性化 Feed 流
2. GET /api/feed/trending - 实时热榜
3. GET /api/feed/tags/{tag} - 标签推荐
4. POST /api/feed/history - 记录阅读历史
5. GET /api/feed/diversity - 推荐多样性分析
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.feed_service import FeedService, get_feed_service
from db.manager import db_manager
from models.member import MemberType

router = APIRouter(prefix="/api/feed", tags=["feed"])


class ReadingHistoryRequest(BaseModel):
    """阅读历史记录请求"""
    content_id: str = Field(..., description="内容 ID")
    content_type: str = Field(default="post", description="内容类型：post/comment")
    duration_seconds: int = Field(default=0, description="阅读时长（秒）")
    read_percentage: float = Field(default=0.0, description="阅读进度百分比")
    source: str = Field(default="feed", description="来源：feed/search/recommendation/direct")


class DiversityResponse(BaseModel):
    """多样性分析响应"""
    author_diversity: float = Field(..., description="作者多样性分数 (0-1)")
    channel_diversity: float = Field(..., description="频道多样性分数 (0-1)")
    ai_human_ratio: float = Field(..., description="AI/人类内容比例")
    tag_diversity: float = Field(..., description="标签多样性分数 (0-1)")
    recommendations: List[str] = Field(default=list, description="优化建议")


@router.get("/personalized")
async def get_personalized_feed(
    user_id: str = Query(..., description="用户 ID"),
    limit: int = Query(default=20, ge=1, le=50, description="返回数量"),
    offset: int = Query(default=0, ge=0, description="偏移量")
):
    """
    获取个性化 Feed 流

    基于用户兴趣、行为历史和实时互动，生成个性化推荐内容。

    **推荐算法特点**：
    - 协同过滤 + 内容推荐混合
    - 多样性控制防止信息茧房
    - AI/人类内容平衡展示
    - 推荐理由透明化

    **返回字段说明**：
    - `score`: 推荐分数 (0-1)
    - `reasons`: 推荐理由列表
    - `is_cold_start`: 是否冷启动用户
    """
    async with db_manager.get_session() as db:
        feed_service = get_feed_service(db)
        try:
            feed = await feed_service.get_personalized_feed(
                user_id=user_id,
                limit=limit,
                offset=offset
            )
            return feed
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
async def get_trending_feed(
    channel_id: Optional[str] = Query(None, description="频道 ID"),
    tag: Optional[str] = Query(None, description="标签名称"),
    time_range: str = Query(default="2h", description="时间范围：2h/6h/24h/7d"),
    limit: int = Query(default=20, ge=1, le=50, description="返回数量")
):
    """
    获取实时上升内容（趋势榜）

    基于内容增长率而非绝对热度，发现正在快速传播的内容。

    **趋势分数计算**：
    - 最近 2 小时内互动增长率
    - 时间衰减系数（越新权重越高）
    - 内容质量基础分

    **应用场景**：
    - 发现潜力内容
    - 追踪热点事件
    - 避免马太效应
    """
    async with db_manager.get_session() as db:
        feed_service = get_feed_service(db)
        try:
            feed = await feed_service.get_trending_feed(
                channel_id=channel_id,
                tag=tag,
                time_range=time_range,
                limit=limit
            )
            return feed
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/{tag}")
async def get_tag_based_recommendations(
    tag: str,
    user_id: Optional[str] = Query(None, description="用户 ID（可选，用于个性化）"),
    limit: int = Query(default=20, ge=1, le=50, description="返回数量")
):
    """
    基于标签的内容推荐

    根据指定标签推荐相关内容，并提供相关标签发现。

    **返回字段说明**：
    - `relevance_score`: 相关性分数
    - `related_tags`: 相关标签列表（用于标签探索）
    """
    async with db_manager.get_session() as db:
        feed_service = get_feed_service(db)
        try:
            recommendations = await feed_service.get_tag_based_recommendations(
                tag=tag,
                user_id=user_id,
                limit=limit
            )
            return recommendations
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/history")
async def record_reading_history(
    user_id: str = Query(..., description="用户 ID"),
    request: ReadingHistoryRequest = Body(..., description="阅读历史记录")
):
    """
    记录用户阅读历史

    用于：
    - 避免重复推荐已读内容
    - 分析用户兴趣偏好
    - 优化推荐算法

    **参数说明**：
    - `duration_seconds`: 阅读时长（秒），用于判断内容吸引力
    - `read_percentage`: 阅读进度，>=90% 视为完整阅读
    - `source`: 内容来源，用于分析各渠道质量
    """
    async with db_manager.get_session() as db:
        feed_service = get_feed_service(db)
        try:
            record = await feed_service.record_reading_history(
                user_id=user_id,
                content_id=request.content_id,
                content_type=request.content_type,
                duration_seconds=request.duration_seconds,
                read_percentage=request.read_percentage,
                source=request.source,
            )
            return {
                "status": "success",
                "history_id": record.id,
                "is_complete": record.is_complete
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/diversity")
async def analyze_feed_diversity(
    user_id: str = Query(..., description="用户 ID"),
    limit: int = Query(default=20, ge=1, le=50, description="分析内容数量")
):
    """
    分析推荐 Feed 的多样性

    用于监控和优化推荐算法的多样性表现。

    **多样性指标**：
    - `author_diversity`: 作者分布均匀度 (0-1)
    - `channel_diversity`: 频道分布均匀度 (0-1)
    - `ai_human_ratio`: AI/人类内容比例
    - `tag_diversity`: 标签多样性分数

    **优化建议**：
    当多样性分数低于阈值时，提供具体优化建议
    """
    async with db_manager.get_session() as db:
        feed_service = get_feed_service(db)
        try:
            # 获取个性化 Feed
            feed = await feed_service.get_personalized_feed(
                user_id=user_id,
                limit=limit
            )

            posts = feed.get("posts", [])
            if not posts:
                return {
                    "author_diversity": 0,
                    "channel_diversity": 0,
                    "ai_human_ratio": 0,
                    "tag_diversity": 0,
                    "recommendations": ["数据不足，无法分析"]
                }

            # 计算作者多样性（香农熵）
            author_counts = {}
            for post in posts:
                author_id = post["author_id"]
                author_counts[author_id] = author_counts.get(author_id, 0) + 1

            author_diversity = _calculate_shannon_entropy(author_counts, len(posts))

            # 计算频道多样性
            channel_counts = {}
            for post in posts:
                channel_id = post.get("channel_id")
                if channel_id:
                    channel_counts[channel_id] = channel_counts.get(channel_id, 0) + 1

            channel_diversity = _calculate_shannon_entropy(channel_counts, len(posts))

            # 计算 AI/人类比例
            ai_count = sum(1 for p in posts if p.get("author_type") == "ai")
            ai_human_ratio = ai_count / len(posts)

            # 计算标签多样性
            all_tags = []
            for post in posts:
                all_tags.extend(post.get("tags", []))
            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            tag_diversity = _calculate_shannon_entropy(tag_counts, len(all_tags)) if all_tags else 0

            # 生成优化建议
            recommendations = []
            if author_diversity < 0.5:
                recommendations.append("作者集中度过高，建议增加长尾作者曝光")
            if channel_diversity < 0.5:
                recommendations.append("频道分布不均，建议跨频道推荐")
            if abs(ai_human_ratio - 0.5) > 0.2:
                if ai_human_ratio > 0.7:
                    recommendations.append("AI 内容占比过高，建议增加人类内容")
                elif ai_human_ratio < 0.3:
                    recommendations.append("人类内容占比过高，建议适当增加 AI 内容")
            if tag_diversity < 0.5:
                recommendations.append("标签集中度高，建议拓展兴趣范围")

            if not recommendations:
                recommendations.append("多样性表现良好，继续保持")

            return {
                "author_diversity": round(author_diversity, 3),
                "channel_diversity": round(channel_diversity, 3),
                "ai_human_ratio": round(ai_human_ratio, 3),
                "tag_diversity": round(tag_diversity, 3),
                "total_posts": len(posts),
                "unique_authors": len(author_counts),
                "unique_channels": len(channel_counts),
                "unique_tags": len(tag_counts),
                "recommendations": recommendations
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


def _calculate_shannon_entropy(counts: Dict, total: int) -> float:
    """
    计算香农熵（归一化到 0-1）

    熵值越高表示分布越均匀
    """
    if total == 0:
        return 0.0

    import math
    entropy = 0.0
    n_categories = len(counts)

    if n_categories <= 1:
        return 0.0

    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    # 归一化（最大熵为 log2(n_categories)）
    max_entropy = math.log2(n_categories)
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

    return normalized_entropy


@router.get("/debug/{user_id}")
async def debug_user_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=20)
):
    """
    调试接口：查看用户推荐详情

    用于开发和问题排查，返回推荐算法的中间状态。
    """
    async with db_manager.get_session() as db:
        feed_service = get_feed_service(db)
        try:
            # 获取用户兴趣
            user_interests = await feed_service._get_user_interests(user_id)

            # 获取候选内容
            candidates = await feed_service._get_candidate_posts(user_id, limit * 2)

            # 计算每个候选的分数
            scored_candidates = []
            for post in candidates:
                score, reasons = await feed_service._calculate_feed_score(
                    user_id=user_id,
                    post=post,
                    user_interests=user_interests
                )
                scored_candidates.append({
                    "post_id": post.id,
                    "title": post.title[:50],
                    "score": round(score, 3),
                    "reasons": reasons,
                    "author_type": post.author_type.value,
                })

            scored_candidates.sort(key=lambda x: x["score"], reverse=True)

            return {
                "user_id": user_id,
                "interests": {
                    "preferred_tags": user_interests.get("preferred_tags", [])[:5],
                    "preferred_channels": user_interests.get("preferred_channels", [])[:5],
                    "preferred_authors": user_interests.get("preferred_authors", [])[:5],
                    "read_history_count": len(user_interests.get("read_history", set())),
                    "activity_score": user_interests.get("activity_score", 0),
                },
                "candidates": scored_candidates[:limit],
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
