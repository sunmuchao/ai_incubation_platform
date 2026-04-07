"""
全文搜索 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.search_service import SearchService
from db.manager import db_manager

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchResult(BaseModel):
    """搜索结果响应模型"""
    query: str
    total: int
    limit: int
    offset: int
    results: List[Dict[str, Any]]
    search_type: str
    filters: Dict[str, Any] = {}


class GlobalSearchResult(BaseModel):
    """全局搜索结果响应模型"""
    query: str
    posts: Dict[str, Any]
    comments: Dict[str, Any]
    members: Dict[str, Any]


class SearchSuggestion(BaseModel):
    """搜索建议响应模型"""
    posts: List[str]
    members: List[str]


@router.get("/posts", response_model=SearchResult)
async def search_posts(
    q: str = Query(..., description="搜索关键词"),
    author_type: Optional[str] = Query(None, description="作者类型 (human/ai)"),
    sort_by: str = Query(default="relevance", description="排序方式 (relevance/time)"),
    time_range: Optional[str] = Query(None, description="时间范围 (24h/7d/30d)"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量")
):
    """
    搜索帖子

    支持全文搜索帖子标题和内容，可按作者类型、时间范围筛选，支持相关性和时间排序。

    搜索示例:
    - `/api/search/posts?q=AI 技术` - 搜索包含"AI 技术"的帖子
    - `/api/search/posts?q=Python&author_type=human` - 搜索人类用户发布的 Python 相关帖子
    - `/api/search/posts?q=教程&time_range=7d&sort_by=time` - 搜索最近 7 天的教程帖子
    """
    async with db_manager.get_session() as db:
        search_service = SearchService(db)
        try:
            results = await search_service.search_posts(
                q=q,
                author_type=author_type,
                sort_by=sort_by,
                time_range=time_range,
                limit=limit,
                offset=offset
            )
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@router.get("/comments", response_model=SearchResult)
async def search_comments(
    q: str = Query(..., description="搜索关键词"),
    post_id: Optional[str] = Query(None, description="帖子 ID 筛选"),
    author_type: Optional[str] = Query(None, description="作者类型 (human/ai)"),
    sort_by: str = Query(default="relevance", description="排序方式 (relevance/time)"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量")
):
    """
    搜索评论

    支持全文搜索评论内容，可按帖子 ID 和作者类型筛选。

    搜索示例:
    - `/api/search/comments?q=有帮助` - 搜索包含"有帮助"的评论
    - `/api/search/comments?q=提问&post_id=xxx` - 搜索指定帖子的提问评论
    """
    async with db_manager.get_session() as db:
        search_service = SearchService(db)
        try:
            results = await search_service.search_comments(
                q=q,
                post_id=post_id,
                author_type=author_type,
                sort_by=sort_by,
                limit=limit,
                offset=offset
            )
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@router.get("/users", response_model=SearchResult)
async def search_users(
    q: str = Query(..., description="搜索关键词"),
    member_type: Optional[str] = Query(None, description="成员类型 (human/ai)"),
    sort_by: str = Query(default="relevance", description="排序方式 (relevance/time)"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量")
):
    """
    搜索用户

    支持全文搜索用户名。

    搜索示例:
    - `/api/search/users?q=小明` - 搜索用户名包含"小明"的用户
    - `/api/search/users?q=Bot&member_type=ai` - 搜索 AI 机器人用户
    """
    async with db_manager.get_session() as db:
        search_service = SearchService(db)
        try:
            results = await search_service.search_members(
                q=q,
                member_type=member_type,
                sort_by=sort_by,
                limit=limit,
                offset=offset
            )
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@router.get("/all", response_model=GlobalSearchResult)
async def search_all(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(default=20, ge=1, le=50, description="每类结果返回数量")
):
    """
    全局搜索

    同时搜索帖子、评论和用户，返回综合结果。

    搜索示例:
    - `/api/search/all?q=AI` - 搜索所有与 AI 相关的内容
    """
    async with db_manager.get_session() as db:
        search_service = SearchService(db)
        try:
            results = await search_service.search_all(q=q, limit=limit)
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@router.get("/suggestions", response_model=SearchSuggestion)
async def get_search_suggestions(
    q: str = Query(..., description="搜索前缀"),
    limit: int = Query(default=10, ge=1, le=20, description="返回数量限制")
):
    """
    获取搜索建议

    根据输入前缀提供帖子标题和用户名的搜索建议。

    示例:
    - `/api/search/suggestions?q=Py` - 获取以"Py"开头的帖子标题和用户名建议
    """
    async with db_manager.get_session() as db:
        search_service = SearchService(db)
        try:
            suggestions = await search_service.get_search_suggestions(q=q, limit=limit)
            return suggestions
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取搜索建议失败：{str(e)}")


@router.post("/index/init")
async def init_search_index():
    """
    初始化搜索索引

    创建全文搜索所需的数据库索引（通常只需在部署时执行一次）。
    """
    async with db_manager.get_session() as db:
        search_service = SearchService(db)
        try:
            success = await search_service.init_search_index()
            if success:
                return {"status": "success", "message": "搜索索引创建成功"}
            else:
                return {"status": "warning", "message": "搜索索引可能已存在"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"创建索引失败：{str(e)}")
