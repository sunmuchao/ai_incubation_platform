"""
内容热度算法服务
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from datetime import datetime, timedelta
import logging
import math

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import DBPost, DBComment, DBLike, DBBookmark
from models.member import MemberType

logger = logging.getLogger(__name__)


# 热度算法配置
class HeatConfig:
    """热度算法配置"""
    # 互动权重
    LIKE_WEIGHT = 10          # 点赞权重
    BOOKMARK_WEIGHT = 15      # 收藏权重
    COMMENT_WEIGHT = 5        # 评论权重
    VIEW_WEIGHT = 0.1         # 浏览权重

    # 时间衰减因子（每小时）
    TIME_DECAY_FACTOR = 0.05

    # 基础分数
    BASE_SCORE = 100

    # 优质内容阈值
    QUALITY_SCORE_THRESHOLD = 500      # 优质内容阈值
    HOT_SCORE_THRESHOLD = 1000         # 热门内容阈值

    # 时间范围
    TIME_RANGE_24H = 24
    TIME_RANGE_7D = 7 * 24
    TIME_RANGE_30D = 30 * 24


class HeatService:
    """内容热度服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_post_heat_score(
        self,
        post_id: str,
        post_created_at: datetime
    ) -> float:
        """
        计算帖子热度分数

        热度分数公式:
        score = (likes * LIKE_WEIGHT + bookmarks * BOOKMARK_WEIGHT +
                 comments * COMMENT_WEIGHT + views * VIEW_WEIGHT) *
                TIME_DECAY + BASE_SCORE

        其中 TIME_DECAY = e^(-TIME_DECAY_FACTOR * age_hours)
        """
        # 获取互动数据
        like_count = await self._get_like_count(post_id, "post")
        bookmark_count = await self._get_bookmark_count(post_id, "post")
        comment_count = await self._get_comment_count(post_id)

        # 计算时间衰减
        age_hours = (datetime.now() - post_created_at).total_seconds() / 3600
        time_decay = math.exp(-HeatConfig.TIME_DECAY_FACTOR * age_hours)

        # 计算热度分数
        interaction_score = (
            like_count * HeatConfig.LIKE_WEIGHT +
            bookmark_count * HeatConfig.BOOKMARK_WEIGHT +
            comment_count * HeatConfig.COMMENT_WEIGHT
        )

        # 基础分数 + 互动分数 * 时间衰减
        heat_score = HeatConfig.BASE_SCORE + interaction_score * time_decay

        return heat_score

    async def _get_like_count(self, content_id: str, content_type: str) -> int:
        """获取点赞数"""
        result = await self.db.execute(
            select(func.count(DBLike.id)).where(
                DBLike.content_id == content_id,
                DBLike.content_type == content_type
            )
        )
        return result.scalar() or 0

    async def _get_bookmark_count(self, content_id: str, content_type: str) -> int:
        """获取收藏数"""
        result = await self.db.execute(
            select(func.count(DBBookmark.id)).where(
                DBBookmark.content_id == content_id,
                DBBookmark.content_type == content_type
            )
        )
        return result.scalar() or 0

    async def _get_comment_count(self, post_id: str) -> int:
        """获取评论数"""
        result = await self.db.execute(
            select(func.count(DBComment.id)).where(
                DBComment.post_id == post_id,
                DBComment.status == "published"
            )
        )
        return result.scalar() or 0

    async def get_hot_posts(
        self,
        time_range: str = "24h",
        limit: int = 50,
        author_type: Optional[MemberType] = None
    ) -> List[Dict[str, Any]]:
        """
        获取热门帖子列表

        Args:
            time_range: 时间范围 (24h, 7d, 30d, all)
            limit: 返回数量
            author_type: 作者类型筛选

        Returns:
            热门帖子列表，包含热度分数
        """
        # 计算时间范围
        now = datetime.now()
        if time_range == "24h":
            start_time = now - timedelta(hours=HeatConfig.TIME_RANGE_24H)
        elif time_range == "7d":
            start_time = now - timedelta(hours=HeatConfig.TIME_RANGE_7D)
        elif time_range == "30d":
            start_time = now - timedelta(hours=HeatConfig.TIME_RANGE_30D)
        else:
            start_time = None  # 全部时间

        # 构建查询条件
        conditions = [
            DBPost.status == "published",
        ]

        if start_time:
            conditions.append(DBPost.created_at >= start_time)

        if author_type:
            conditions.append(DBPost.author_type == author_type)

        # 获取帖子列表
        result = await self.db.execute(
            select(DBPost).where(and_(*conditions))
            .order_by(desc(DBPost.created_at))
            .limit(limit * 2)  # 多取一些用于排序
        )

        posts = result.scalars().all()

        # 计算每个帖子的热度分数
        posts_with_scores = []
        for post in posts:
            score = await self.calculate_post_heat_score(post.id, post.created_at)
            posts_with_scores.append({
                "post": post,
                "heat_score": score,
            })

        # 按热度分数排序
        posts_with_scores.sort(key=lambda x: x["heat_score"], reverse=True)

        # 返回指定数量的结果
        return posts_with_scores[:limit]

    async def get_trending_posts(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取实时上升帖子

        基于最近 2 小时内的互动增长率
        """
        two_hours_ago = datetime.now() - timedelta(hours=2)

        result = await self.db.execute(
            select(DBPost).where(
                DBPost.status == "published",
                DBPost.created_at >= two_hours_ago
            )
            .order_by(desc(DBPost.created_at))
            .limit(limit * 2)
        )

        posts = result.scalars().all()

        # 计算增长趋势分数
        trending_posts = []
        for post in posts:
            score = await self.calculate_post_heat_score(post.id, post.created_at)
            # 新帖子的时间衰减较小，所以增长更快
            age_hours = (datetime.now() - post.created_at).total_seconds() / 3600
            if age_hours < 1:
                trend_score = score * 1.5  # 1 小时内新帖加分
            else:
                trend_score = score

            trending_posts.append({
                "post": post,
                "trend_score": trend_score,
            })

        trending_posts.sort(key=lambda x: x["trend_score"], reverse=True)
        return trending_posts[:limit]

    async def identify_quality_content(
        self,
        post_id: str
    ) -> Dict[str, Any]:
        """
        识别优质内容

        基于热度分数、互动质量等维度判断
        """
        result = await self.db.execute(
            select(DBPost).where(DBPost.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            return None

        heat_score = await self.calculate_post_heat_score(post.id, post.created_at)

        # 获取互动数据
        like_count = await self._get_like_count(post.id, "post")
        bookmark_count = await self._get_bookmark_count(post.id, "post")
        comment_count = await self._get_comment_count(post.id)

        # 计算互动质量分数
        # 收藏/点赞 比例高表示内容质量高
        if like_count > 0:
            bookmark_like_ratio = bookmark_count / like_count
        else:
            bookmark_like_ratio = 0

        quality_score = heat_score * (1 + bookmark_like_ratio * 0.5)

        # 判定是否优质内容
        is_quality = quality_score >= HeatConfig.QUALITY_SCORE_THRESHOLD
        is_hot = heat_score >= HeatConfig.HOT_SCORE_THRESHOLD

        return {
            "post_id": post_id,
            "heat_score": heat_score,
            "quality_score": quality_score,
            "is_quality": is_quality,
            "is_hot": is_hot,
            "like_count": like_count,
            "bookmark_count": bookmark_count,
            "comment_count": comment_count,
        }

    async def get_personalized_recommendations(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取个性化推荐（基础版本）

        基于用户历史互动（点赞、收藏、评论）的内容类型
        推荐相似的高热度内容

        TODO: 未来可以实现更复杂的推荐算法
        """
        # 获取用户历史互动数据
        user_likes = await self.db.execute(
            select(DBLike.content_id).where(
                DBLike.user_id == user_id,
                DBLike.content_type == "post"
            )
        )
        liked_post_ids = set(row[0] for row in user_likes.fetchall())

        # 获取热门帖子
        hot_posts = await self.get_hot_posts(time_range="7d", limit=limit * 2)

        # 过滤用户已互动过的内容
        recommendations = []
        for item in hot_posts:
            if item["post"].id not in liked_post_ids:
                recommendations.append(item)

        return recommendations[:limit]

    async def refresh_heat_scores(self) -> int:
        """
        刷新所有帖子的热度分数

        用于定时任务，更新缓存的热度分数
        """
        result = await self.db.execute(
            select(DBPost).where(DBPost.status == "published")
        )
        posts = result.scalars().all()

        updated_count = 0
        for post in posts:
            # 计算新的热度分数
            score = await self.calculate_post_heat_score(post.id, post.created_at)
            # 这里可以选择将分数存入缓存或数据库
            updated_count += 1

        logger.info(f"刷新了 {updated_count} 个帖子的热度分数")
        return updated_count


# 全局服务实例
_heat_service = None


def get_heat_service(db: AsyncSession) -> HeatService:
    """获取热度服务实例"""
    global _heat_service
    if _heat_service is None or _heat_service.db is not db:
        _heat_service = HeatService(db)
    return _heat_service
