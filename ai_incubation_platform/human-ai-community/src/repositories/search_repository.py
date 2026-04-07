"""
全文搜索 Repository - 使用 PostgreSQL 全文搜索功能
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func, desc
from sqlalchemy.orm import aliased

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBPost, DBComment, DBCommunityMember
from models.member import MemberType


class SearchRepository(BaseRepository):
    """全文搜索 Repository - 使用 PostgreSQL tsvector/tsquery"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBPost, db)  # 使用 DBPost 作为默认模型

    async def search_posts(
        self,
        query: str,
        author_type: Optional[MemberType] = None,
        channel_id: Optional[str] = None,
        sort_by: str = "relevance",
        time_range: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        搜索帖子

        Args:
            query: 搜索关键词
            author_type: 作者类型筛选
            channel_id: 频道 ID 筛选（预留）
            sort_by: 排序方式 - relevance(相关性) 或 time(时间)
            time_range: 时间范围 - 24h, 7d, 30d
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            搜索结果列表，包含帖子信息和相关性得分
        """
        # 构建时间范围条件
        time_filter = ""
        if time_range:
            if time_range == "24h":
                time_filter = "AND created_at >= NOW() - INTERVAL '24 hours'"
            elif time_range == "7d":
                time_filter = "AND created_at >= NOW() - INTERVAL '7 days'"
            elif time_range == "30d":
                time_filter = "AND created_at >= NOW() - INTERVAL '30 days'"

        # 构建作者类型条件
        author_filter = ""
        if author_type:
            author_filter = f"AND author_type = '{author_type.value}'"

        # PostgreSQL 全文搜索查询 - 使用 tsvector 和 tsquery
        # 对标题给予更高的权重
        search_query = text(f"""
            SELECT
                p.id,
                p.author_id,
                p.author_type,
                p.title,
                p.content,
                p.tags,
                p.status,
                p.created_at,
                p.updated_at,
                m.name as author_name,
                m.member_type as author_member_type,
                ts_rank(
                    setweight(to_tsvector('simple', coalesce(p.title, '')), 'A') ||
                    setweight(to_tsvector('simple', coalesce(p.content, '')), 'B'),
                    plainto_tsquery('simple', :query)
                ) as relevance_score
            FROM posts p
            LEFT JOIN community_members m ON p.author_id = m.id
            WHERE
                setweight(to_tsvector('simple', coalesce(p.title, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(p.content, '')), 'B') @@ plainto_tsquery('simple', :query)
                AND p.status = 'published'
                {author_filter}
                {time_filter}
            ORDER BY
                {"relevance_score DESC" if sort_by == "relevance" else "p.created_at DESC"}
            LIMIT :limit OFFSET :offset
        """)

        result = await self.db.execute(
            search_query,
            {"query": query, "limit": limit, "offset": offset}
        )

        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "author_id": row.author_id,
                "author_type": row.author_type,
                "title": row.title,
                "content": row.content,
                "tags": row.tags,
                "status": row.status,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "author_name": row.author_name,
                "author_member_type": row.author_member_type,
                "relevance_score": float(row.relevance_score) if row.relevance_score else 0.0
            }
            for row in rows
        ]

    async def search_comments(
        self,
        query: str,
        post_id: Optional[str] = None,
        author_type: Optional[MemberType] = None,
        sort_by: str = "relevance",
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        搜索评论

        Args:
            query: 搜索关键词
            post_id: 帖子 ID 筛选
            author_type: 作者类型筛选
            sort_by: 排序方式
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            搜索结果列表
        """
        post_filter = f"AND post_id = '{post_id}'" if post_id else ""
        author_filter = f"AND author_type = '{author_type.value}'" if author_type else ""

        search_query = text(f"""
            SELECT
                c.id,
                c.post_id,
                c.author_id,
                c.author_type,
                c.content,
                c.parent_id,
                c.status,
                c.created_at,
                m.name as author_name,
                m.member_type as author_member_type,
                ts_rank(
                    to_tsvector('simple', coalesce(c.content, '')),
                    plainto_tsquery('simple', :query)
                ) as relevance_score
            FROM comments c
            LEFT JOIN community_members m ON c.author_id = m.id
            WHERE
                to_tsvector('simple', coalesce(c.content, '')) @@ plainto_tsquery('simple', :query)
                AND c.status = 'published'
                {post_filter}
                {author_filter}
            ORDER BY
                {"relevance_score DESC" if sort_by == "relevance" else "c.created_at DESC"}
            LIMIT :limit OFFSET :offset
        """)

        result = await self.db.execute(
            search_query,
            {"query": query, "limit": limit, "offset": offset}
        )

        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "post_id": row.post_id,
                "author_id": row.author_id,
                "author_type": row.author_type,
                "content": row.content,
                "parent_id": row.parent_id,
                "status": row.status,
                "created_at": row.created_at,
                "author_name": row.author_name,
                "author_member_type": row.author_member_type,
                "relevance_score": float(row.relevance_score) if row.relevance_score else 0.0
            }
            for row in rows
        ]

    async def search_members(
        self,
        query: str,
        member_type: Optional[MemberType] = None,
        sort_by: str = "relevance",
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        搜索用户/成员

        Args:
            query: 搜索关键词
            member_type: 成员类型筛选
            sort_by: 排序方式
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            搜索结果列表
        """
        type_filter = f"AND member_type = '{member_type.value}'" if member_type else ""

        search_query = text(f"""
            SELECT
                id,
                name,
                email,
                member_type,
                role,
                ai_model,
                post_count,
                join_date,
                ts_rank(
                    to_tsvector('simple', coalesce(name, '')),
                    plainto_tsquery('simple', :query)
                ) as relevance_score
            FROM community_members
            WHERE
                to_tsvector('simple', coalesce(name, '')) @@ plainto_tsquery('simple', :query)
                {type_filter}
            ORDER BY
                {"relevance_score DESC" if sort_by == "relevance" else "join_date DESC"}
            LIMIT :limit OFFSET :offset
        """)

        result = await self.db.execute(
            search_query,
            {"query": query, "limit": limit, "offset": offset}
        )

        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "member_type": row.member_type,
                "role": row.role,
                "ai_model": row.ai_model,
                "post_count": row.post_count,
                "join_date": row.join_date,
                "relevance_score": float(row.relevance_score) if row.relevance_score else 0.0
            }
            for row in rows
        ]

    async def create_search_index(self) -> bool:
        """
        创建全文搜索索引（初始化时使用）

        为 posts 和 comments 表创建 tsvector 索引以提升搜索性能
        """
        try:
            # 为帖子表创建索引
            await self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_posts_search
                ON posts
                USING GIN (
                    setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
                    setweight(to_tsvector('simple', coalesce(content, '')), 'B')
                )
            """))

            # 为评论表创建索引
            await self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_comments_search
                ON comments
                USING GIN (to_tsvector('simple', coalesce(content, '')))
            """))

            # 为成员表创建索引
            await self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_members_search
                ON community_members
                USING GIN (to_tsvector('simple', coalesce(name, '')))
            """))

            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_search_suggestions(
        self,
        query: str,
        limit: int = 10
    ) -> Dict[str, List[str]]:
        """
        获取搜索建议

        Args:
            query: 搜索前缀
            limit: 返回数量限制

        Returns:
            包含帖子标题和用户名的建议列表
        """
        # 获取帖子标题建议
        post_suggestions = await self.db.execute(
            text("""
                SELECT DISTINCT title
                FROM posts
                WHERE title ILIKE :query || '%'
                AND status = 'published'
                LIMIT :limit
            """),
            {"query": query, "limit": limit}
        )

        # 获取用户名建议
        member_suggestions = await self.db.execute(
            text("""
                SELECT DISTINCT name
                FROM community_members
                WHERE name ILIKE :query || '%'
                LIMIT :limit
            """),
            {"query": query, "limit": limit}
        )

        return {
            "posts": [row.title for row in post_suggestions.fetchall()],
            "members": [row.name for row in member_suggestions.fetchall()]
        }
