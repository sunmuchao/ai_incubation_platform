"""
智能内容推荐服务

基于用户兴趣和行为的内容推荐算法：
- 协同过滤推荐
- 基于内容推荐
- 热度推荐
- 个性化推荐流
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from collections import defaultdict
import logging
import math
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import DBPost, DBComment, DBLike, DBBookmark, DBFollow
from db.channel_models import ChannelCategoryType, DBChannelMember, DBChannel
from models.member import ContentType

logger = logging.getLogger(__name__)


class RecommendationService:
    """智能推荐服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._user_interests_cache = {}
        self._content_features_cache = {}
        self._similarity_cache = {}

        # 推荐算法权重配置
        self.weights = {
            "content_similarity": 0.3,   # 内容相似度
            "collaborative": 0.3,        # 协同过滤
            "recency": 0.2,              # 时效性
            "hotness": 0.2,              # 热度
        }

        # 兴趣标签权重
        self.interest_weights = {
            "like": 1.0,                 # 点赞
            "bookmark": 2.0,             # 收藏（权重更高）
            "comment": 0.5,              # 评论
            "view": 0.1,                 # 浏览
            "follow": 1.5,               # 关注
        }

    async def get_personalized_recommendations(
        self,
        user_id: str,
        limit: int = 20,
        exclude_read: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取个性化推荐

        Args:
            user_id: 用户 ID
            limit: 返回数量
            exclude_read: 排除已读内容

        Returns:
            推荐内容列表
        """
        logger.info(f"为用户 {user_id} 生成个性化推荐")

        # 1. 获取用户兴趣画像
        user_interests = await self._get_user_interests(user_id)

        # 2. 获取候选内容
        candidates = await self._get_candidate_posts(user_id, exclude_read, limit * 5)

        if not candidates:
            # 冷启动：返回热门内容
            return await self.get_hot_recommendations(limit)

        # 3. 计算推荐分数
        scored_posts = []
        for post in candidates:
            score = await self._calculate_recommendation_score(
                user_id=user_id,
                post=post,
                user_interests=user_interests
            )
            scored_posts.append({
                "post": post,
                "score": score,
                "reason": self._explain_recommendation(score, user_interests, post)
            })

        # 4. 按分数排序并返回
        scored_posts.sort(key=lambda x: x["score"], reverse=True)

        return [
            {
                "id": sp["post"].id,
                "title": sp["post"].title,
                "author_id": sp["post"].author_id,
                "channel_id": sp["post"].channel_id,
                "score": round(sp["score"], 3),
                "reason": sp["reason"],
                "created_at": sp["post"].created_at.isoformat(),
            }
            for sp in scored_posts[:limit]
        ]

    async def get_hot_recommendations(
        self,
        limit: int = 20,
        time_range: str = "24h"
    ) -> List[Dict[str, Any]]:
        """
        获取热门推荐

        Args:
            limit: 返回数量
            time_range: 时间范围（24h, 7d, 30d）

        Returns:
            热门内容列表
        """
        # 计算时间边界
        now = datetime.now()
        if time_range == "24h":
            time_boundary = now - timedelta(hours=24)
        elif time_range == "7d":
            time_boundary = now - timedelta(days=7)
        elif time_range == "30d":
            time_boundary = now - timedelta(days=30)
        else:
            time_boundary = now - timedelta(hours=24)

        # 获取时间范围内的帖子
        result = await self.db.execute(
            select(DBPost)
            .where(DBPost.created_at >= time_boundary)
            .where(DBPost.is_deleted == False)
            .order_by(desc(DBPost.like_count + DBComment.count * 2 + DBPost.view_count * 0.1))
            .limit(limit * 2)
        )
        posts = result.scalars().all()

        # 计算热度分数
        scored_posts = []
        for post in posts:
            hot_score = self._calculate_hotness_score(
                like_count=post.like_count or 0,
                comment_count=post.comment_count or 0,
                view_count=post.view_count or 0,
                created_at=post.created_at
            )
            scored_posts.append({
                "post": post,
                "score": hot_score
            })

        scored_posts.sort(key=lambda x: x["score"], reverse=True)

        return [
            {
                "id": sp["post"].id,
                "title": sp["post"].title,
                "author_id": sp["post"].author_id,
                "score": round(sp["score"], 3),
                "created_at": sp["post"].created_at.isoformat(),
            }
            for sp in scored_posts[:limit]
        ]

    async def get_similar_content(
        self,
        post_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取相似内容

        Args:
            post_id: 帖子 ID
            limit: 返回数量

        Returns:
            相似内容列表
        """
        # 获取原帖子
        result = await self.db.execute(
            select(DBPost).where(DBPost.id == post_id)
        )
        source_post = result.scalar_one_or_none()

        if not source_post:
            return []

        # 获取同频道/同标签的帖子
        query = select(DBPost).where(
            and_(
                DBPost.id != post_id,
                DBPost.is_deleted == False,
            )
        )

        # 优先同频道
        if source_post.channel_id:
            query = query.where(DBPost.channel_id == source_post.channel_id)

        query = query.order_by(desc(DBPost.created_at)).limit(limit * 2)

        result = await self.db.execute(query)
        candidates = result.scalars().all()

        # 计算内容相似度
        scored_posts = []
        for post in candidates:
            similarity = self._calculate_content_similarity(source_post, post)
            if similarity > 0.3:  # 相似度阈值
                scored_posts.append({
                    "post": post,
                    "similarity": similarity
                })

        scored_posts.sort(key=lambda x: x["similarity"], reverse=True)

        return [
            {
                "id": sp["post"].id,
                "title": sp["post"].title,
                "author_id": sp["post"].author_id,
                "similarity": round(sp["similarity"], 3),
                "created_at": sp["post"].created_at.isoformat(),
            }
            for sp in scored_posts[:limit]
        ]

    async def get_channel_recommendations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        推荐频道

        Args:
            user_id: 用户 ID
            limit: 返回数量

        Returns:
            推荐频道列表
        """
        # 获取用户已加入的频道
        result = await self.db.execute(
            select(DBChannelMember.channel_id)
            .where(DBChannelMember.member_id == user_id)
            .where(DBChannelMember.is_active == True)
        )
        joined_channel_ids = set(r[0] for r in result.all())

        # 获取用户关注的作者
        result = await self.db.execute(
            select(DBFollow.following_id)
            .where(DBFollow.follower_id == user_id)
        )
        following_ids = set(r[0] for r in result.all())

        # 获取候选频道
        query = select(DBChannel).where(
            and_(
                DBChannel.is_active == True,
                DBChannel.is_official == True,  # 优先推荐官方频道
            )
        )
        if joined_channel_ids:
            query = query.where(DBChannel.id.notin_(joined_channel_ids))

        query = query.order_by(desc(DBChannel.member_count)).limit(limit * 2)
        result = await self.db.execute(query)
        channels = result.scalars().all()

        # 根据用户兴趣排序
        # TODO: 实现更复杂的频道推荐算法

        return [
            {
                "id": ch.id,
                "name": ch.name,
                "slug": ch.slug,
                "description": ch.description,
                "member_count": ch.member_count,
                "is_official": ch.is_official,
            }
            for ch in channels[:limit]
        ]

    async def _get_user_interests(self, user_id: str) -> Dict[str, Any]:
        """获取用户兴趣画像"""
        # 检查缓存
        if user_id in self._user_interests_cache:
            return self._user_interests_cache[user_id]

        interests = {
            "preferred_channels": [],
            "preferred_categories": [],
            "preferred_authors": [],
            "activity_score": 0.0,
        }

        # 分析用户点赞历史
        result = await self.db.execute(
            select(DBLike.target_id, DBLike.target_type)
            .where(DBLike.user_id == user_id)
            .order_by(desc(DBLike.created_at))
            .limit(100)
        )
        likes = result.all()

        # 分析用户收藏历史
        result = await self.db.execute(
            select(DBBookmark.post_id)
            .where(DBBookmark.user_id == user_id)
            .order_by(desc(DBBookmark.created_at))
            .limit(50)
        )
        bookmarks = result.scalars().all()

        # 分析用户关注
        result = await self.db.execute(
            select(DBFollow.following_id)
            .where(DBFollow.follower_id == user_id)
        )
        follows = result.scalars().all()
        interests["preferred_authors"] = [f for f in follows]

        # 获取用户活跃频道
        result = await self.db.execute(
            select(DBChannelMember.channel_id)
            .where(DBChannelMember.member_id == user_id)
            .where(DBChannelMember.is_active == True)
        )
        channel_members = result.scalars().all()
        interests["preferred_channels"] = [c for c in channel_members]

        # 计算频道偏好
        if channel_members:
            result = await self.db.execute(
                select(DBChannel.category_id)
                .where(DBChannel.id.in_(channel_members))
            )
            categories = result.scalars().all()
            interests["preferred_categories"] = list(set(categories))

        # 计算活跃度
        interests["activity_score"] = (
            len(likes) * self.interest_weights["like"] +
            len(bookmarks) * self.interest_weights["bookmark"] +
            len(follows) * self.interest_weights["follow"]
        )

        # 缓存
        self._user_interests_cache[user_id] = interests
        return interests

    async def _get_candidate_posts(
        self,
        user_id: str,
        exclude_read: bool,
        limit: int
    ) -> List[DBPost]:
        """获取候选内容"""
        query = select(DBPost).where(DBPost.is_deleted == False)

        # 排除已读
        if exclude_read:
            # TODO: 实现已读过滤（需要阅读记录表）
            pass

        # 排除自己的帖子
        query = query.where(DBPost.author_id != user_id)

        # 按时间排序
        query = query.order_by(desc(DBPost.created_at)).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _calculate_recommendation_score(
        self,
        user_id: str,
        post: DBPost,
        user_interests: Dict[str, Any]
    ) -> float:
        """计算推荐分数"""
        score = 0.0

        # 1. 频道匹配分数
        if post.channel_id in user_interests.get("preferred_channels", []):
            score += 0.3

        # 2. 关注作者分数
        if post.author_id in user_interests.get("preferred_authors", []):
            score += 0.3

        # 3. 内容热度分数
        hot_score = self._calculate_hotness_score(
            like_count=post.like_count or 0,
            comment_count=post.comment_count or 0,
            view_count=post.view_count or 0,
            created_at=post.created_at
        )
        score += hot_score * 0.2

        # 4. 时效性分数
        recency_score = self._calculate_recency_score(post.created_at)
        score += recency_score * 0.2

        return score

    def _calculate_hotness_score(
        self,
        like_count: int,
        comment_count: int,
        view_count: int,
        created_at: datetime
    ) -> float:
        """计算热度分数"""
        # 基础互动分数
        base_score = (
            like_count * 10 +
            comment_count * 5 +
            view_count * 0.1
        )

        # 时间衰减（牛顿冷却定律）
        hours_since_creation = (datetime.now() - created_at).total_seconds() / 3600
        decay_factor = 1 / (1 + hours_since_creation / 24)  # 24 小时半衰期

        return base_score * decay_factor

    def _calculate_recency_score(self, created_at: datetime) -> float:
        """计算时效性分数"""
        hours_since_creation = (datetime.now() - created_at).total_seconds() / 3600

        if hours_since_creation < 1:
            return 1.0
        elif hours_since_creation < 24:
            return 0.8
        elif hours_since_creation < 72:
            return 0.6
        elif hours_since_creation < 168:  # 7 天
            return 0.4
        else:
            return 0.2

    def _calculate_content_similarity(
        self,
        post1: DBPost,
        post2: DBPost
    ) -> float:
        """计算内容相似度"""
        cache_key = f"{post1.id}_{post2.id}"
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]

        similarity = 0.0

        # 1. 频道相同
        if post1.channel_id and post1.channel_id == post2.channel_id:
            similarity += 0.3

        # 2. 标题相似度（简单关键词重叠）
        title1_words = set(post1.title.lower().split())
        title2_words = set(post2.title.lower().split())
        if title1_words and title2_words:
            title_overlap = len(title1_words & title2_words) / max(len(title1_words), len(title2_words))
            similarity += title_overlap * 0.3

        # 3. 标签相似度（如果有标签）
        # TODO: 实现标签相似度

        self._similarity_cache[cache_key] = similarity
        return similarity

    def _explain_recommendation(
        self,
        score: float,
        user_interests: Dict[str, Any],
        post: DBPost
    ) -> str:
        """解释推荐理由"""
        reasons = []

        if post.channel_id in user_interests.get("preferred_channels", []):
            reasons.append("你关注了这个频道")

        if post.author_id in user_interests.get("preferred_authors", []):
            reasons.append("你关注的作者")

        if (post.like_count or 0) > 10:
            reasons.append("热门内容")

        if not reasons:
            reasons.append("根据你的兴趣推荐")

        return ", ".join(reasons)

    async def refresh_cache(self):
        """刷新缓存"""
        self._user_interests_cache.clear()
        self._content_features_cache.clear()
        self._similarity_cache.clear()
        logger.info("推荐缓存已刷新")


# 全局服务实例
_recommendation_service: Optional[RecommendationService] = None


def get_recommendation_service(db: AsyncSession) -> RecommendationService:
    """获取推荐服务实例"""
    global _recommendation_service
    if _recommendation_service is None or _recommendation_service.db is not db:
        _recommendation_service = RecommendationService(db)
    return _recommendation_service
