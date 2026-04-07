"""
全文搜索服务
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.search_repository import SearchRepository
from models.member import MemberType

logger = logging.getLogger(__name__)


class SearchService:
    """全文搜索服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.search_repository = SearchRepository(db)

    async def search_posts(
        self,
        q: str,
        author_type: Optional[str] = None,
        sort_by: str = "relevance",
        time_range: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        搜索帖子

        Args:
            q: 搜索关键词
            author_type: 作者类型 (human/ai)
            sort_by: 排序方式 (relevance/time)
            time_range: 时间范围 (24h/7d/30d)
            limit: 返回数量
            offset: 偏移量

        Returns:
            搜索结果
        """
        if not q or not q.strip():
            return {
                "query": q,
                "total": 0,
                "results": [],
                "search_type": "posts"
            }

        try:
            parsed_author_type = None
            if author_type:
                try:
                    parsed_author_type = MemberType(author_type)
                except ValueError:
                    pass  # 无效的类型将被忽略

            results = await self.search_repository.search_posts(
                query=q.strip(),
                author_type=parsed_author_type,
                sort_by=sort_by,
                time_range=time_range,
                limit=limit,
                offset=offset
            )

            # 获取总数（用于分页）
            total = len(results)  # 简化处理，实际应该用 COUNT 查询

            return {
                "query": q,
                "total": total,
                "limit": limit,
                "offset": offset,
                "results": results,
                "search_type": "posts",
                "filters": {
                    "author_type": author_type,
                    "sort_by": sort_by,
                    "time_range": time_range
                }
            }

        except Exception as e:
            logger.error(f"搜索帖子失败：{e}")
            raise e

    async def search_comments(
        self,
        q: str,
        post_id: Optional[str] = None,
        author_type: Optional[str] = None,
        sort_by: str = "relevance",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        搜索评论

        Args:
            q: 搜索关键词
            post_id: 帖子 ID 筛选
            author_type: 作者类型
            sort_by: 排序方式
            limit: 返回数量
            offset: 偏移量

        Returns:
            搜索结果
        """
        if not q or not q.strip():
            return {
                "query": q,
                "total": 0,
                "results": [],
                "search_type": "comments"
            }

        try:
            parsed_author_type = None
            if author_type:
                try:
                    parsed_author_type = MemberType(author_type)
                except ValueError:
                    pass

            results = await self.search_repository.search_comments(
                query=q.strip(),
                post_id=post_id,
                author_type=parsed_author_type,
                sort_by=sort_by,
                limit=limit,
                offset=offset
            )

            return {
                "query": q,
                "total": len(results),
                "limit": limit,
                "offset": offset,
                "results": results,
                "search_type": "comments",
                "filters": {
                    "post_id": post_id,
                    "author_type": author_type,
                    "sort_by": sort_by
                }
            }

        except Exception as e:
            logger.error(f"搜索评论失败：{e}")
            raise e

    async def search_members(
        self,
        q: str,
        member_type: Optional[str] = None,
        sort_by: str = "relevance",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        搜索用户

        Args:
            q: 搜索关键词
            member_type: 成员类型
            sort_by: 排序方式
            limit: 返回数量
            offset: 偏移量

        Returns:
            搜索结果
        """
        if not q or not q.strip():
            return {
                "query": q,
                "total": 0,
                "results": [],
                "search_type": "members"
            }

        try:
            parsed_member_type = None
            if member_type:
                try:
                    parsed_member_type = MemberType(member_type)
                except ValueError:
                    pass

            results = await self.search_repository.search_members(
                query=q.strip(),
                member_type=parsed_member_type,
                sort_by=sort_by,
                limit=limit,
                offset=offset
            )

            return {
                "query": q,
                "total": len(results),
                "limit": limit,
                "offset": offset,
                "results": results,
                "search_type": "members",
                "filters": {
                    "member_type": member_type,
                    "sort_by": sort_by
                }
            }

        except Exception as e:
            logger.error(f"搜索用户失败：{e}")
            raise e

    async def search_all(
        self,
        q: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        全局搜索 - 同时搜索帖子、评论和用户

        Args:
            q: 搜索关键词
            limit: 每类结果的返回数量

        Returns:
            综合搜索结果
        """
        if not q or not q.strip():
            return {
                "query": q,
                "posts": [],
                "comments": [],
                "members": []
            }

        try:
            # 并发执行三个搜索
            posts_result, comments_result, members_result = await asyncio.gather(
                self.search_repository.search_posts(query=q.strip(), limit=limit),
                self.search_repository.search_comments(query=q.strip(), limit=limit),
                self.search_repository.search_members(query=q.strip(), limit=limit)
            )

            return {
                "query": q,
                "posts": {
                    "total": len(posts_result),
                    "results": posts_result
                },
                "comments": {
                    "total": len(comments_result),
                    "results": comments_result
                },
                "members": {
                    "total": len(members_result),
                    "results": members_result
                }
            }

        except Exception as e:
            logger.error(f"全局搜索失败：{e}")
            raise e

    async def get_search_suggestions(self, q: str, limit: int = 10) -> Dict[str, List[str]]:
        """
        获取搜索建议

        Args:
            q: 搜索前缀
            limit: 返回数量

        Returns:
            搜索建议
        """
        if not q or len(q.strip()) < 1:
            return {"posts": [], "members": []}

        try:
            return await self.search_repository.get_search_suggestions(
                query=q.strip(),
                limit=limit
            )
        except Exception as e:
            logger.error(f"获取搜索建议失败：{e}")
            return {"posts": [], "members": []}

    async def init_search_index(self) -> bool:
        """
        初始化搜索索引

        在应用启动时调用，创建必要的全文搜索索引
        """
        try:
            return await self.search_repository.create_search_index()
        except Exception as e:
            logger.error(f"创建搜索索引失败：{e}")
            return False


# 导入 asyncio（用于 search_all 方法）
import asyncio
