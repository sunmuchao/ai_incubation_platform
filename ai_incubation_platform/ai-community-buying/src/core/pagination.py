"""
分页工具模块

提供统一的分页参数和响应格式。
"""
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginationParams(BaseModel):
    """
    分页参数

    用于 API 请求的分页参数解析和验证。
    """
    page: int = Field(default=1, ge=1, description="页码（从 1 开始）")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """获取限制数量"""
        return self.page_size


class PageInfo(BaseModel):
    """
    分页信息

    用于 API 响应中返回分页元数据。
    """
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total: int = Field(..., description="总记录数")
    total_pages: int = Field(..., description="总页数")

    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """是否有上一页"""
        return self.page > 1

    @property
    def next_page(self) -> Optional[int]:
        """下一页页码"""
        return self.page + 1 if self.has_next else None

    @property
    def previous_page(self) -> Optional[int]:
        """上一页页码"""
        return self.page - 1 if self.has_previous else None


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应

    通用的分页响应格式，包含数据和分页信息。

    使用示例:
    @router.get("/items")
    def list_items(params: PaginationParams = Depends()):
        items, total = service.get_items(params.offset, params.limit)
        return PaginatedResponse(items=items, total=total, params=params)
    """
    success: bool = Field(default=True, description="是否成功")
    items: List[T] = Field(..., description="数据列表")
    pagination: PageInfo = Field(..., description="分页信息")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        params: PaginationParams
    ) -> "PaginatedResponse[T]":
        """
        创建分页响应

        Args:
            items: 数据列表
            total: 总记录数
            params: 分页参数

        Returns:
            分页响应对象
        """
        total_pages = (total + params.page_size - 1) // params.page_size

        return cls(
            success=True,
            items=items,
            pagination=PageInfo(
                page=params.page,
                page_size=params.page_size,
                total=total,
                total_pages=total_pages
            )
        )


class CursorPaginationParams(BaseModel):
    """
    游标分页参数

    适用于大数据量、需要高性能的场景。
    使用游标（cursor）而非页码进行分页。
    """
    cursor: Optional[str] = Field(default=None, description="游标（用于定位下一页）")
    limit: int = Field(default=20, ge=1, le=100, description="每页数量")

    def to_offset_limit(self) -> tuple:
        """
        转换为传统的 offset/limit

        注意：这只在游标为数字编码时有效
        对于真正的游标分页，应直接使用游标查询
        """
        if self.cursor:
            try:
                offset = int(self.cursor)
            except ValueError:
                offset = 0
        else:
            offset = 0
        return offset, self.limit


class CursorPageInfo(BaseModel):
    """
    游标分页信息
    """
    limit: int = Field(..., description="每页数量")
    has_next: bool = Field(..., description="是否有下一页")
    has_previous: bool = Field(..., description="是否有上一页")
    next_cursor: Optional[str] = Field(default=None, description="下一页游标")
    previous_cursor: Optional[str] = Field(default=None, description="上一页游标")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """
    游标分页响应
    """
    success: bool = Field(default=True, description="是否成功")
    items: List[T] = Field(..., description="数据列表")
    pagination: CursorPageInfo = Field(..., description="分页信息")

    @classmethod
    def create(
        cls,
        items: List[T],
        limit: int,
        has_next: bool = False,
        has_previous: bool = False,
        next_cursor: Optional[str] = None,
        previous_cursor: Optional[str] = None
    ) -> "CursorPaginatedResponse[T]":
        """
        创建游标分页响应

        Args:
            items: 数据列表
            limit: 每页数量
            has_next: 是否有下一页
            has_previous: 是否有上一页
            next_cursor: 下一页游标
            previous_cursor: 上一页游标

        Returns:
            游标分页响应对象
        """
        return cls(
            success=True,
            items=items,
            pagination=CursorPageInfo(
                limit=limit,
                has_next=has_next,
                has_previous=has_previous,
                next_cursor=next_cursor,
                previous_cursor=previous_cursor
            )
        )


def paginate_query(
    query,
    page: int = 1,
    page_size: int = 20,
    count_query=None
):
    """
    对 SQLAlchemy 查询应用分页

    Args:
        query: SQLAlchemy 查询对象
        page: 页码
        page_size: 每页数量
        count_query: 可选的计数查询（用于优化性能）

    Returns:
        (items, total, page_info)
    """
    offset = (page - 1) * page_size

    # 获取总数
    if count_query:
        total = count_query.scalar()
    else:
        total = query.count()

    # 应用分页
    items = query.offset(offset).limit(page_size).all()

    # 计算分页信息
    total_pages = (total + page_size - 1) // page_size
    page_info = PageInfo(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages
    )

    return items, total, page_info


def create_paginated_response(
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    创建分页响应字典

    适用于直接返回字典而非 Pydantic 模型的场景。

    Returns:
        分页响应字典
    """
    total_pages = (total + page_size - 1) // page_size

    return {
        "success": True,
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None
        }
    }
