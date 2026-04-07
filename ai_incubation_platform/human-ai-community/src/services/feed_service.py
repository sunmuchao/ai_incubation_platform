"""
P15 阶段：内容推荐系统增强 - 服务层

v1.15 推荐服务增强功能：
1. 个性化 Feed 流（协同过滤 + 内容推荐）
2. 实时热榜（按频道/标签分类）
3. 内容标签系统（标签相似度计算）
4. 阅读历史追踪
5. 推荐多样性控制
6. AI 内容推荐特殊处理（人机内容平衡）
"""
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, distinct
from collections import defaultdict
import logging
import math
import random
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import DBPost, DBComment, DBLike, DBBookmark, DBFollow, DBNotification
from db.channel_models import DBChannel, ChannelCategoryType
from models.member import MemberType, ContentType
from models.p15_recommendation import (
    DBReadingHistory, DBContentTag, DBPostTag, DBUserInterest,
    DBRecommendationLog, DBRecommendationConfig
)

logger = logging.getLogger(__name__)


class RecommendationConfig:
    """推荐系统配置"""
    # 互动权重
    LIKE_WEIGHT = 1.0
    BOOKMARK_WEIGHT = 2.0
    COMMENT_WEIGHT = 0.5
    VIEW_WEIGHT = 0.1
    FOLLOW_WEIGHT = 1.5

    # 时间衰减（每小时）
    TIME_DECAY_FACTOR = 0.03

    # 多样性控制
    MAX_SAME_AUTHOR_RATIO = 0.3  # 同一作者内容最大占比
    MAX_SAME_CHANNEL_RATIO = 0.4  # 同一频道内容最大占比
    AI_HUMAN_BALANCE_RATIO = 0.5  # AI/人类内容平衡比例（50%）

    # 推荐分数阈值
    MIN_RECOMMEND_SCORE = 0.1
    EXCELLENT_SCORE_THRESHOLD = 0.8

    # 冷启动配置
    COLD_START_LIMIT = 20
    TRENDING_TIME_WINDOW_HOURS = 2

    # 标签相似度权重
    TAG_SIMILARITY_WEIGHT = 0.3
    CHANNEL_SIMILARITY_WEIGHT = 0.3
    AUTHOR_SIMILARITY_WEIGHT = 0.2
    RECENCY_WEIGHT = 0.2


class FeedService:
    """Feed 流服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._config_cache = {}
        self._tag_cache = {}

    async def get_personalized_feed(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取个性化 Feed 流

        Args:
            user_id: 用户 ID
            limit: 返回数量
            offset: 偏移量

        Returns:
            Feed 流数据，包含帖子列表和推荐理由
        """
        logger.info(f"为用户 {user_id} 生成个性化 Feed 流")

        # 1. 获取用户兴趣画像
        user_interests = await self._get_user_interests(user_id)

        # 2. 检查是否冷启动（无兴趣数据）
        is_cold_start = len(user_interests.get("preferred_tags", [])) == 0 and \
                        len(user_interests.get("preferred_channels", [])) == 0

        if is_cold_start:
            logger.info(f"用户 {user_id} 冷启动，使用热门内容 + 多样性推荐")
            return await self._get_cold_start_feed(user_id, limit, offset)

        # 3. 获取候选内容
        candidates = await self._get_candidate_posts(user_id, limit * 3)

        # 4. 计算推荐分数
        scored_posts = []
        for post in candidates:
            score, reasons = await self._calculate_feed_score(
                user_id=user_id,
                post=post,
                user_interests=user_interests
            )
            if score > RecommendationConfig.MIN_RECOMMEND_SCORE:
                scored_posts.append({
                    "post": post,
                    "score": score,
                    "reasons": reasons
                })

        # 5. 多样性控制
        diversified_posts = self._apply_diversity_control(scored_posts, limit)

        # 6. 人机内容平衡
        balanced_posts = self._apply_ai_human_balance(diversified_posts, user_id)

        # 7. 记录推荐日志
        recommendation_id = await self._log_recommendation(
            user_id=user_id,
            scene="feed",
            recommended_content=[
                {"id": p["post"].id, "type": "post", "score": p["score"], "reasons": p["reasons"]}
                for p in balanced_posts
            ]
        )

        # 8. 返回结果
        return {
            "recommendation_id": recommendation_id,
            "total": len(balanced_posts),
            "has_more": len(balanced_posts) >= limit,
            "posts": [
                {
                    "id": p["post"].id,
                    "title": p["post"].title,
                    "content": p["post"].content[:200] + "..." if len(p["post"].content) > 200 else p["post"].content,
                    "author_id": p["post"].author_id,
                    "author_type": p["post"].author_type.value,
                    "channel_id": p["post"].channel_id,
                    "tags": p["post"].tags,
                    "created_at": p["post"].created_at.isoformat(),
                    "score": round(p["score"], 3),
                    "reasons": p["reasons"],
                }
                for p in balanced_posts[:limit]
            ]
        }

    async def get_trending_feed(
        self,
        channel_id: Optional[str] = None,
        tag: Optional[str] = None,
        time_range: str = "2h",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取实时上升内容（趋势 Feed）

        Args:
            channel_id: 频道 ID（可选）
            tag: 标签（可选）
            time_range: 时间范围（2h, 6h, 24h）
            limit: 返回数量

        Returns:
            趋势内容列表
        """
        logger.info(f"获取趋势 Feed，channel={channel_id}, tag={tag}, time_range={time_range}")

        # 计算时间窗口
        now = datetime.now()
        time_window = self._parse_time_range(time_range)
        time_boundary = now - timedelta(hours=time_window)

        # 获取候选帖子
        query = select(DBPost).where(
            and_(
                DBPost.status == "published",
                DBPost.created_at >= time_boundary,
            )
        )

        if channel_id:
            query = query.where(DBPost.channel_id == channel_id)

        query = query.order_by(desc(DBPost.created_at)).limit(limit * 3)
        result = await self.db.execute(query)
        posts = result.scalars().all()

        # 计算趋势分数
        scored_posts = []
        for post in posts:
            trend_score = await self._calculate_trend_score(post, time_window)
            if trend_score > 0:
                scored_posts.append({
                    "post": post,
                    "trend_score": trend_score
                })

        # 按趋势分数排序
        scored_posts.sort(key=lambda x: x["trend_score"], reverse=True)

        return {
            "time_range": time_range,
            "channel_id": channel_id,
            "tag": tag,
            "total": len(scored_posts),
            "trending_posts": [
                {
                    "id": p["post"].id,
                    "title": p["post"].title,
                    "author_id": p["post"].author_id,
                    "author_type": p["post"].author_type.value,
                    "trend_score": round(p["trend_score"], 2),
                    "created_at": p["post"].created_at.isoformat(),
                    "heat_growth": self._calculate_heat_growth(p["post"]),
                }
                for p in scored_posts[:limit]
            ]
        }

    async def get_tag_based_recommendations(
        self,
        tag: str,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        基于标签的内容推荐

        Args:
            tag: 标签名称
            user_id: 用户 ID（可选，用于个性化）
            limit: 返回数量

        Returns:
            推荐内容列表
        """
        logger.info(f"基于标签 {tag} 推荐内容")

        # 获取标签
        tag_obj = await self._get_tag_by_name(tag)
        if not tag_obj:
            return {"total": 0, "posts": [], "related_tags": []}

        # 获取同标签帖子
        query = select(DBPost).join(DBPostTag, DBPost.id == DBPostTag.post_id).where(
            and_(
                DBPostTag.tag_id == tag_obj.id,
                DBPost.status == "published",
            )
        ).order_by(desc(DBPost.created_at)).limit(limit * 2)

        result = await self.db.execute(query)
        posts = result.scalars().all()

        # 计算相关性分数
        scored_posts = []
        for post in posts:
            relevance_score = await self._calculate_tag_relevance(post, tag_obj, user_id)
            scored_posts.append({
                "post": post,
                "relevance_score": relevance_score
            })

        scored_posts.sort(key=lambda x: x["relevance_score"], reverse=True)

        # 获取相关标签
        related_tags = await self._get_related_tags(tag_obj)

        return {
            "tag": tag,
            "total": len(scored_posts),
            "posts": [
                {
                    "id": p["post"].id,
                    "title": p["post"].title,
                    "author_id": p["post"].author_id,
                    "relevance_score": round(p["relevance_score"], 3),
                    "created_at": p["post"].created_at.isoformat(),
                }
                for p in scored_posts[:limit]
            ],
            "related_tags": related_tags
        }

    async def record_reading_history(
        self,
        user_id: str,
        content_id: str,
        content_type: str = "post",
        duration_seconds: int = 0,
        read_percentage: float = 0.0,
        source: str = "feed",
        recommendation_id: Optional[str] = None
    ) -> DBReadingHistory:
        """
        记录阅读历史

        Args:
            user_id: 用户 ID
            content_id: 内容 ID
            content_type: 内容类型
            duration_seconds: 阅读时长（秒）
            read_percentage: 阅读进度
            source: 来源
            recommendation_id: 推荐记录 ID

        Returns:
            阅读历史记录
        """
        # 检查是否已有记录
        existing = await self.db.execute(
            select(DBReadingHistory).where(
                and_(
                    DBReadingHistory.user_id == user_id,
                    DBReadingHistory.content_id == content_id,
                    DBReadingHistory.content_type == content_type,
                )
            )
        )
        record = existing.scalar_one_or_none()

        if record:
            # 更新现有记录
            record.read_duration_seconds = max(record.read_duration_seconds, duration_seconds)
            record.read_percentage = max(record.read_percentage, read_percentage)
            record.is_complete = record.read_percentage >= 90
            record.updated_at = datetime.now()
        else:
            # 创建新记录
            record = DBReadingHistory(
                user_id=user_id,
                content_id=content_id,
                content_type=content_type,
                read_duration_seconds=duration_seconds,
                read_percentage=read_percentage,
                is_complete=read_percentage >= 90,
                source=source,
                recommendation_id=recommendation_id,
            )
            self.db.add(record)

        await self.db.flush()
        return record

    async def update_user_interests(
        self,
        user_id: str,
        content_id: str,
        interaction_type: str
    ) -> bool:
        """
        根据用户互动更新兴趣画像

        Args:
            user_id: 用户 ID
            content_id: 内容 ID
            interaction_type: 互动类型（like/bookmark/comment/follow）

        Returns:
            是否成功更新
        """
        # 获取内容
        post = await self.db.execute(select(DBPost).where(DBPost.id == content_id))
        post = post.scalar_one_or_none()

        if not post:
            return False

        # 权重配置
        weights = {
            "like": RecommendationConfig.LIKE_WEIGHT,
            "bookmark": RecommendationConfig.BOOKMARK_WEIGHT,
            "comment": RecommendationConfig.COMMENT_WEIGHT,
            "follow": RecommendationConfig.FOLLOW_WEIGHT,
        }

        weight = weights.get(interaction_type, 0.5)

        # 更新频道兴趣
        if post.channel_id:
            await self._update_interest(
                user_id=user_id,
                interest_type="channel",
                interest_id=post.channel_id,
                delta=weight
            )

        # 更新作者兴趣（关注）
        if interaction_type == "follow":
            await self._update_interest(
                user_id=user_id,
                interest_type="author",
                interest_id=post.author_id,
                delta=weight * 2
            )

        return True

    # ==================== 内部方法 ====================

    async def _get_user_interests(self, user_id: str) -> Dict[str, Any]:
        """获取用户兴趣画像"""
        interests = {
            "preferred_tags": [],
            "preferred_channels": [],
            "preferred_authors": [],
            "read_history": set(),
            "activity_score": 0.0,
        }

        # 获取显式兴趣
        result = await self.db.execute(
            select(DBUserInterest).where(
                and_(
                    DBUserInterest.user_id == user_id,
                    DBUserInterest.score > 0,
                )
            ).order_by(desc(DBUserInterest.score)).limit(50)
        )
        explicit_interests = result.scalars().all()

        for interest in explicit_interests:
            if interest.interest_type == "tag":
                interests["preferred_tags"].append({
                    "id": interest.interest_id,
                    "name": interest.interest_value,
                    "score": interest.score
                })
            elif interest.interest_type == "channel":
                interests["preferred_channels"].append({
                    "id": interest.interest_id,
                    "score": interest.score
                })
            elif interest.interest_type == "author":
                interests["preferred_authors"].append(interest.interest_id)

        # 获取关注列表
        result = await self.db.execute(
            select(DBFollow.following_id).where(DBFollow.follower_id == user_id)
        )
        follows = result.scalars().all()
        interests["preferred_authors"].extend(follows)
        interests["preferred_authors"] = list(set(interests["preferred_authors"]))

        # 获取阅读历史
        result = await self.db.execute(
            select(DBReadingHistory.content_id).where(
                and_(
                    DBReadingHistory.user_id == user_id,
                    DBReadingHistory.content_type == "post",
                )
            ).order_by(desc(DBReadingHistory.created_at)).limit(100)
        )
        read_history = result.scalars().all()
        interests["read_history"] = set(read_history)

        # 计算活跃度
        interests["activity_score"] = len(read_history) * RecommendationConfig.VIEW_WEIGHT

        return interests

    async def _get_candidate_posts(
        self,
        user_id: str,
        limit: int
    ) -> List[DBPost]:
        """获取候选内容"""
        # 排除已读和自己发布的
        query = select(DBPost).where(
            and_(
                DBPost.status == "published",
                DBPost.author_id != user_id,
            )
        ).order_by(desc(DBPost.created_at)).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _calculate_feed_score(
        self,
        user_id: str,
        post: DBPost,
        user_interests: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        计算 Feed 推荐分数

        Returns:
            (分数，推荐理由列表)
        """
        score = 0.0
        reasons = []

        # 1. 频道匹配（权重 0.3）
        preferred_channel_ids = [c["id"] for c in user_interests.get("preferred_channels", [])]
        if post.channel_id in preferred_channel_ids:
            score += 0.3
            reasons.append("来自你关注的频道")

        # 2. 作者匹配（权重 0.2）
        if post.author_id in user_interests.get("preferred_authors", []):
            score += 0.2
            reasons.append("来自你关注的作者")

        # 3. 标签匹配（权重 0.3）
        preferred_tag_ids = [t["id"] for t in user_interests.get("preferred_tags", [])]
        post_tags = await self._get_post_tags(post.id)
        matching_tags = [t for t in post_tags if t in preferred_tag_ids]
        if matching_tags:
            tag_score = min(0.3, len(matching_tags) * 0.1)
            score += tag_score
            reasons.append(f"匹配你感兴趣的标签")

        # 4. 热度分数（权重 0.1）
        hot_score = self._calculate_base_hot_score(post)
        score += hot_score * 0.1
        if hot_score > 0.5:
            reasons.append("热门内容")

        # 5. 时效性分数（权重 0.1）
        recency_score = self._calculate_recency_score(post.created_at)
        score += recency_score * 0.1

        # 6. 内容质量分数
        quality_score = await self._calculate_quality_score(post)
        score += quality_score * 0.1

        # 如果没有具体理由，给一个通用理由
        if not reasons:
            reasons.append("根据你的兴趣推荐")

        return min(1.0, score), reasons

    def _calculate_trend_score(self, post: DBPost, time_window: float) -> float:
        """
        计算趋势分数

        趋势分数 = (最近互动数 / 时间窗口) * 增长系数
        """
        # 基础互动数
        base_interactions = (post.like_count or 0) + (post.comment_count or 0) * 2

        # 时间衰减（越新的内容增长系数越高）
        age_hours = (datetime.now() - post.created_at).total_seconds() / 3600
        if age_hours < 1:
            growth_factor = 2.0
        elif age_hours < time_window / 2:
            growth_factor = 1.5
        else:
            growth_factor = 1.0

        # 趋势分数
        trend_score = (base_interactions / time_window) * growth_factor

        return trend_score

    def _calculate_heat_growth(self, post: DBPost) -> float:
        """计算热度增长率"""
        # 这里简化实现，实际应该对比不同时间段的互动数
        age_hours = (datetime.now() - post.created_at).total_seconds() / 3600
        if age_hours < 0.5:
            return 2.0
        elif age_hours < 2:
            return 1.5
        elif age_hours < 6:
            return 1.2
        else:
            return 1.0

    async def _get_cold_start_feed(
        self,
        user_id: str,
        limit: int,
        offset: int
    ) -> Dict[str, Any]:
        """冷启动 Feed：热门内容 + 多样性"""
        # 获取热门内容
        hot_posts = await self._get_hot_posts(limit * 2)

        # 多样性控制
        diversified = self._apply_diversity_control(
            [{"post": p, "score": 0.5, "reasons": ["热门内容"]} for p in hot_posts],
            limit
        )

        # 人机平衡
        balanced = self._apply_ai_human_balance(diversified, user_id)

        return {
            "recommendation_id": str(uuid.uuid4()),
            "total": len(balanced),
            "has_more": len(balanced) >= limit,
            "is_cold_start": True,
            "posts": [
                {
                    "id": p["post"].id,
                    "title": p["post"].title,
                    "content": p["post"].content[:200] + "..." if len(p["post"].content) > 200 else p["post"].content,
                    "author_id": p["post"].author_id,
                    "author_type": p["post"].author_type.value,
                    "channel_id": p["post"].channel_id,
                    "tags": p["post"].tags,
                    "created_at": p["post"].created_at.isoformat(),
                    "score": round(p["score"], 3),
                    "reasons": p["reasons"],
                }
                for p in balanced[:limit]
            ]
        }

    def _apply_diversity_control(
        self,
        scored_posts: List[Dict],
        limit: int
    ) -> List[Dict]:
        """应用多样性控制"""
        if not scored_posts:
            return []

        result = []
        author_counts = defaultdict(int)
        channel_counts = defaultdict(int)
        total = len(scored_posts)

        for item in scored_posts:
            if len(result) >= limit:
                break

            post = item["post"]
            author_id = post.author_id
            channel_id = post.channel_id

            # 检查作者多样性
            author_ratio = author_counts[author_id] / max(1, len(result))
            if author_ratio >= RecommendationConfig.MAX_SAME_AUTHOR_RATIO:
                continue

            # 检查频道多样性
            channel_ratio = channel_counts[channel_id] / max(1, len(result))
            if channel_id and channel_ratio >= RecommendationConfig.MAX_SAME_CHANNEL_RATIO:
                continue

            result.append(item)
            author_counts[author_id] += 1
            if channel_id:
                channel_counts[channel_id] += 1

        return result

    def _apply_ai_human_balance(
        self,
        posts: List[Dict],
        user_id: str
    ) -> List[Dict]:
        """应用 AI/人类内容平衡"""
        if not posts:
            return []

        result = []
        ai_count = 0
        human_count = 0

        for item in posts:
            post = item["post"]
            is_ai = post.author_type == MemberType.AI

            # 检查是否超过平衡阈值
            total = len(result) + 1
            if is_ai:
                if ai_count / total > RecommendationConfig.AI_HUMAN_BALANCE_RATIO + 0.1:
                    continue
                ai_count += 1
            else:
                if human_count / total > RecommendationConfig.AI_HUMAN_BALANCE_RATIO + 0.1:
                    continue
                human_count += 1

            result.append(item)

        return result

    async def _log_recommendation(
        self,
        user_id: str,
        scene: str,
        recommended_content: List[Dict]
    ) -> str:
        """记录推荐日志"""
        recommendation_id = str(uuid.uuid4())
        log = DBRecommendationLog(
            recommendation_id=recommendation_id,
            user_id=user_id,
            scene=scene,
            recommended_content=recommended_content,
            algorithm_version="v1.15",
        )
        self.db.add(log)
        await self.db.flush()
        return recommendation_id

    def _parse_time_range(self, time_range: str) -> float:
        """解析时间范围字符串为小时数"""
        mapping = {
            "2h": 2,
            "6h": 6,
            "24h": 24,
            "7d": 168,
        }
        return mapping.get(time_range, 2)

    async def _get_tag_by_name(self, tag_name: str) -> Optional[DBContentTag]:
        """根据名称获取标签"""
        result = await self.db.execute(
            select(DBContentTag).where(DBContentTag.name == tag_name)
        )
        return result.scalar_one_or_none()

    async def _get_post_tags(self, post_id: str) -> List[str]:
        """获取帖子标签 ID 列表"""
        result = await self.db.execute(
            select(DBPostTag.tag_id).where(DBPostTag.post_id == post_id)
        )
        return [r[0] for r in result.all()]

    async def _get_related_tags(self, tag: DBContentTag) -> List[Dict]:
        """获取相关标签"""
        # 简单实现：返回同分类的标签
        if not tag.category:
            return []

        result = await self.db.execute(
            select(DBContentTag).where(
                and_(
                    DBContentTag.category == tag.category,
                    DBContentTag.id != tag.id,
                )
            ).limit(5)
        )
        tags = result.scalars().all()
        return [{"id": t.id, "name": t.name} for t in tags]

    async def _calculate_tag_relevance(
        self,
        post: DBPost,
        tag: DBContentTag,
        user_id: Optional[str]
    ) -> float:
        """计算标签相关性"""
        score = 0.5  # 基础分数

        # 热度加成
        hot_score = self._calculate_base_hot_score(post)
        score += hot_score * 0.3

        # 时效性加成
        recency_score = self._calculate_recency_score(post.created_at)
        score += recency_score * 0.2

        return min(1.0, score)

    def _calculate_base_hot_score(self, post: DBPost) -> float:
        """计算基础热度分数"""
        like_count = post.like_count or 0
        comment_count = post.comment_count or 0

        base = like_count * 10 + comment_count * 5
        # 归一化到 0-1
        return min(1.0, base / 1000)

    def _calculate_recency_score(self, created_at: datetime) -> float:
        """计算时效性分数"""
        hours = (datetime.now() - created_at).total_seconds() / 3600
        if hours < 1:
            return 1.0
        elif hours < 24:
            return 0.8
        elif hours < 72:
            return 0.6
        elif hours < 168:
            return 0.4
        else:
            return 0.2

    async def _calculate_quality_score(self, post: DBPost) -> float:
        """计算内容质量分数"""
        # 简单实现：基于互动数和长度
        length_score = min(1.0, len(post.content) / 500)
        interaction_score = min(1.0, (post.like_count or 0) / 50)
        return (length_score + interaction_score) / 2

    async def _update_interest(
        self,
        user_id: str,
        interest_type: str,
        interest_id: str,
        delta: float
    ):
        """更新用户兴趣"""
        # 查找现有兴趣
        result = await self.db.execute(
            select(DBUserInterest).where(
                and_(
                    DBUserInterest.user_id == user_id,
                    DBUserInterest.interest_type == interest_type,
                    DBUserInterest.interest_id == interest_id,
                )
            )
        )
        interest = result.scalar_one_or_none()

        if interest:
            interest.score = min(10.0, interest.score + delta)
            interest.last_interaction_at = datetime.now()
        else:
            interest = DBUserInterest(
                user_id=user_id,
                interest_type=interest_type,
                interest_id=interest_id,
                score=delta,
                last_interaction_at=datetime.now(),
            )
            self.db.add(interest)

        await self.db.flush()


# 全局服务实例
_feed_service: Optional[FeedService] = None


def get_feed_service(db: AsyncSession) -> FeedService:
    """获取 Feed 服务实例"""
    global _feed_service
    if _feed_service is None or _feed_service.db is not db:
        _feed_service = FeedService(db)
    return _feed_service
