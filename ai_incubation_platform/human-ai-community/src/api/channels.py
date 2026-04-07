"""
频道/版块系统 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import db_manager
from sqlalchemy.ext.asyncio import AsyncSession
from services.channel_service import channel_service
from db.channel_models import ChannelCategoryType, ChannelAccessLevel


router = APIRouter(prefix="/api/channels", tags=["channels"])


# ==================== 请求/响应模型 ====================
class ChannelCategoryCreate(BaseModel):
    """创建频道分类请求"""
    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    category_type: str = Field(default=ChannelCategoryType.OTHER.value, description="分类类型")
    sort_order: int = Field(default=0, description="排序顺序")
    icon: Optional[str] = Field(None, description="图标")


class ChannelCategoryResponse(BaseModel):
    """频道分类响应"""
    id: str
    name: str
    description: Optional[str]
    category_type: str
    sort_order: int
    icon: Optional[str]
    is_active: bool
    channel_count: int = 0


class ChannelCreate(BaseModel):
    """创建频道请求"""
    category_id: str = Field(..., description="所属分类 ID")
    name: str = Field(..., description="频道名称")
    slug: str = Field(..., description="频道标识符")
    description: Optional[str] = Field(None, description="频道描述")
    access_level: str = Field(default=ChannelAccessLevel.PUBLIC.value, description="访问权限级别")
    icon: Optional[str] = Field(None, description="频道图标")
    banner: Optional[str] = Field(None, description="频道横幅")
    sort_order: int = Field(default=0, description="排序顺序")
    rules: Optional[List[str]] = Field(default=None, description="频道规则列表")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="频道配置")
    owner_id: Optional[str] = Field(None, description="频道所有者 ID")
    is_official: bool = Field(default=False, description="是否官方频道")


class ChannelUpdate(BaseModel):
    """更新频道请求"""
    name: Optional[str] = Field(None, description="频道名称")
    description: Optional[str] = Field(None, description="频道描述")
    access_level: Optional[str] = Field(None, description="访问权限级别")
    icon: Optional[str] = Field(None, description="频道图标")
    banner: Optional[str] = Field(None, description="频道横幅")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    rules: Optional[List[str]] = Field(default=None, description="频道规则列表")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="频道配置")
    is_official: Optional[bool] = Field(None, description="是否官方频道")


class ChannelResponse(BaseModel):
    """频道响应"""
    id: str
    category_id: str
    category_name: Optional[str]
    name: str
    slug: str
    description: Optional[str]
    access_level: str
    icon: Optional[str]
    banner: Optional[str]
    sort_order: int
    rules: List[str]
    settings: Dict[str, Any]
    member_count: int
    post_count: int
    owner_id: Optional[str]
    is_official: bool
    is_active: bool


class ChannelMemberResponse(BaseModel):
    """频道成员响应"""
    id: str
    channel_id: str
    member_id: str
    member_name: Optional[str]
    role: str
    joined_at: str
    is_active: bool


class ChannelJoinRequest(BaseModel):
    """加入频道请求"""
    member_id: str = Field(..., description="成员 ID")


class ChannelMemberRoleUpdate(BaseModel):
    """更新成员角色请求"""
    role: str = Field(..., description="新角色：owner/admin/moderator/member")


class ChannelPermissionUpdate(BaseModel):
    """更新频道权限请求"""
    role: str = Field(..., description="角色类型")
    permissions: List[str] = Field(..., description="权限列表")


class ChannelStatsResponse(BaseModel):
    """频道统计响应"""
    channel_id: str
    name: str
    member_count: int
    post_count: int
    last_activity_at: Optional[str]


# ==================== 频道分类管理 ====================
@router.post("/categories")
async def create_category(category: ChannelCategoryCreate):
    """创建频道分类"""
    async with db_manager._session_factory() as session:
        try:
            result = await channel_service.create_category(
                session,
                name=category.name,
                description=category.description,
                category_type=category.category_type,
                sort_order=category.sort_order,
                icon=category.icon,
            )
            return {
                "success": True,
                "category": {
                    "id": result.id,
                    "name": result.name,
                    "description": result.description,
                    "category_type": result.category_type,
                    "sort_order": result.sort_order,
                    "icon": result.icon,
                    "is_active": result.is_active,
                }
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/categories")
async def list_categories(include_inactive: bool = False):
    """获取频道分类列表"""
    async with db_manager._session_factory() as session:
        categories = await channel_service.list_categories(session, include_inactive)
        return {
            "categories": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "category_type": c.category_type,
                    "sort_order": c.sort_order,
                    "icon": c.icon,
                    "is_active": c.is_active,
                    "channel_count": len(c.channels) if hasattr(c, 'channels') else 0,
                }
                for c in categories
            ]
        }


@router.get("/categories/{category_id}")
async def get_category(category_id: str):
    """获取频道分类详情"""
    async with db_manager._session_factory() as session:
        category = await channel_service.get_category(session, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        return {
            "category": {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "category_type": category.category_type,
                "sort_order": category.sort_order,
                "icon": category.icon,
                "is_active": category.is_active,
                "channels": [
                    {
                        "id": ch.id,
                        "name": ch.name,
                        "slug": ch.slug,
                        "description": ch.description,
                        "member_count": ch.member_count,
                    }
                    for ch in category.channels
                ] if hasattr(category, 'channels') else [],
            }
        }


@router.put("/categories/{category_id}")
async def update_category(category_id: str, category: ChannelCategoryCreate):
    """更新频道分类"""
    async with db_manager._session_factory() as session:
        result = await channel_service.update_category(
            session,
            category_id,
            name=category.name,
            description=category.description,
            category_type=category.category_type,
            sort_order=category.sort_order,
            icon=category.icon,
        )
        if not result:
            raise HTTPException(status_code=404, detail="分类不存在")
        return {"success": True, "category_id": category_id}


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str):
    """删除频道分类"""
    async with db_manager._session_factory() as session:
        success = await channel_service.delete_category(session, category_id)
        if not success:
            raise HTTPException(status_code=404, detail="分类不存在")
        return {"success": True, "category_id": category_id}


# ==================== 频道管理 ====================
@router.post("")
async def create_channel(channel: ChannelCreate):
    """创建频道"""
    async with db_manager._session_factory() as session:
        try:
            result = await channel_service.create_channel(
                session,
                category_id=channel.category_id,
                name=channel.name,
                slug=channel.slug,
                description=channel.description,
                access_level=channel.access_level,
                icon=channel.icon,
                banner=channel.banner,
                sort_order=channel.sort_order,
                rules=channel.rules,
                settings=channel.settings,
                owner_id=channel.owner_id,
                is_official=channel.is_official,
            )
            return {
                "success": True,
                "channel": {
                    "id": result.id,
                    "name": result.name,
                    "slug": result.slug,
                    "category_id": result.category_id,
                }
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_channels(
    category_id: Optional[str] = Query(None),
    access_level: Optional[str] = Query(None),
    is_official: Optional[bool] = Query(None),
    limit: int = Query(default=100, ge=1, le=200),
):
    """获取频道列表"""
    async with db_manager._session_factory() as session:
        channels = await channel_service.list_channels(
            session,
            category_id=category_id,
            access_level=access_level,
            is_official=is_official,
            limit=limit,
        )
        return {
            "channels": [
                {
                    "id": ch.id,
                    "name": ch.name,
                    "slug": ch.slug,
                    "description": ch.description,
                    "category_id": ch.category_id,
                    "category_name": ch.category.name if ch.category else None,
                    "access_level": ch.access_level,
                    "icon": ch.icon,
                    "member_count": ch.member_count,
                    "post_count": ch.post_count,
                    "is_official": ch.is_official,
                }
                for ch in channels
            ]
        }


@router.get("/slug/{slug}")
async def get_channel_by_slug(slug: str):
    """通过 slug 获取频道"""
    async with db_manager._session_factory() as session:
        channel = await channel_service.get_channel_by_slug(session, slug)
        if not channel:
            raise HTTPException(status_code=404, detail="频道不存在")
        return {
            "channel": {
                "id": channel.id,
                "name": channel.name,
                "slug": channel.slug,
                "description": channel.description,
                "category_id": channel.category_id,
                "category_name": channel.category.name if channel.category else None,
                "access_level": channel.access_level,
                "icon": channel.icon,
                "banner": channel.banner,
                "rules": channel.rules,
                "settings": channel.settings,
                "member_count": channel.member_count,
                "post_count": channel.post_count,
                "is_official": channel.is_official,
            }
        }


@router.get("/{channel_id}")
async def get_channel(channel_id: str):
    """获取频道详情"""
    async with db_manager._session_factory() as session:
        channel = await channel_service.get_channel(session, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="频道不存在")
        return {
            "channel": {
                "id": channel.id,
                "name": channel.name,
                "slug": channel.slug,
                "description": channel.description,
                "category_id": channel.category_id,
                "category_name": channel.category.name if channel.category else None,
                "access_level": channel.access_level,
                "icon": channel.icon,
                "banner": channel.banner,
                "rules": channel.rules,
                "settings": channel.settings,
                "member_count": channel.member_count,
                "post_count": channel.post_count,
                "owner_id": channel.owner_id,
                "is_official": channel.is_official,
            }
        }


@router.put("/{channel_id}")
async def update_channel(channel_id: str, channel: ChannelUpdate):
    """更新频道"""
    async with db_manager._session_factory() as session:
        result = await channel_service.update_channel(
            session,
            channel_id,
            **channel.model_dump(exclude_unset=True),
        )
        if not result:
            raise HTTPException(status_code=404, detail="频道不存在")
        return {"success": True, "channel_id": channel_id}


@router.delete("/{channel_id}")
async def delete_channel(channel_id: str):
    """删除频道"""
    async with db_manager._session_factory() as session:
        success = await channel_service.delete_channel(session, channel_id)
        if not success:
            raise HTTPException(status_code=404, detail="频道不存在")
        return {"success": True, "channel_id": channel_id}


# ==================== 频道成员管理 ====================
@router.post("/{channel_id}/join")
async def join_channel(channel_id: str, request: ChannelJoinRequest):
    """加入频道"""
    async with db_manager._session_factory() as session:
        try:
            result = await channel_service.join_channel(
                session,
                channel_id,
                request.member_id,
            )
            return {
                "success": True,
                "membership": {
                    "id": result.id,
                    "channel_id": result.channel_id,
                    "member_id": result.member_id,
                    "role": result.role,
                    "joined_at": result.joined_at.isoformat(),
                }
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.post("/{channel_id}/leave")
async def leave_channel(channel_id: str, request: ChannelJoinRequest):
    """退出频道"""
    async with db_manager._session_factory() as session:
        success = await channel_service.leave_channel(session, channel_id, request.member_id)
        if not success:
            raise HTTPException(status_code=404, detail="不是频道成员")
        return {"success": True}


@router.get("/{channel_id}/members")
async def list_channel_members(
    channel_id: str,
    role: Optional[str] = Query(None),
    limit: int = Query(default=100, ge=1, le=200),
):
    """获取频道成员列表"""
    async with db_manager._session_factory() as session:
        members = await channel_service.list_channel_members(
            session,
            channel_id,
            role=role,
            limit=limit,
        )
        return {
            "members": [
                {
                    "id": m.id,
                    "member_id": m.member_id,
                    "role": m.role,
                    "joined_at": m.joined_at.isoformat(),
                }
                for m in members
            ],
            "total": len(members),
        }


@router.put("/{channel_id}/members/{member_id}/role")
async def update_member_role(
    channel_id: str,
    member_id: str,
    request: ChannelMemberRoleUpdate,
):
    """更新成员角色"""
    async with db_manager._session_factory() as session:
        try:
            result = await channel_service.update_member_role(
                session,
                channel_id,
                member_id,
                request.role,
            )
            if not result:
                raise HTTPException(status_code=404, detail="成员不存在")
            return {
                "success": True,
                "member_id": member_id,
                "new_role": result.role,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ==================== 频道权限管理 ====================
@router.get("/{channel_id}/permissions")
async def get_channel_permissions(channel_id: str, role: Optional[str] = Query(None)):
    """获取频道权限配置"""
    async with db_manager._session_factory() as session:
        permissions = await channel_service.get_channel_permissions(session, channel_id, role)
        return {
            "permissions": [
                {
                    "id": p.id,
                    "role": p.role,
                    "permissions": p.permissions,
                }
                for p in permissions
            ]
        }


@router.put("/{channel_id}/permissions")
async def update_channel_permissions(channel_id: str, request: ChannelPermissionUpdate):
    """更新频道权限配置"""
    async with db_manager._session_factory() as session:
        result = await channel_service.update_channel_permissions(
            session,
            channel_id,
            request.role,
            request.permissions,
        )
        return {
            "success": True,
            "permission": {
                "id": result.id,
                "role": result.role,
                "permissions": result.permissions,
            }
        }


@router.get("/{channel_id}/permissions/check")
async def check_channel_permission(
    channel_id: str,
    member_id: str = Query(...),
    permission: str = Query(...),
):
    """检查用户权限"""
    async with db_manager._session_factory() as session:
        has_permission = await channel_service.check_channel_permission(
            session,
            channel_id,
            member_id,
            permission,
        )
        return {
            "channel_id": channel_id,
            "member_id": member_id,
            "permission": permission,
            "has_permission": has_permission,
        }


# ==================== 频道内容管理 ====================
@router.get("/{channel_id}/posts")
async def get_channel_posts(
    channel_id: str,
    sort: str = Query(default="hot", description="排序方式：hot/new/top"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """获取频道帖子列表"""
    async with db_manager._session_factory() as session:
        posts = await channel_service.get_channel_posts(
            session,
            channel_id,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        return {
            "posts": [
                {
                    "id": p.id,
                    "title": p.title,
                    "author_id": p.author_id,
                    "created_at": p.created_at.isoformat(),
                }
                for p in posts
            ],
            "total": len(posts),
        }


@router.post("/{channel_id}/posts/{post_id}/pin")
async def pin_post(channel_id: str, post_id: str, is_pinned: bool = Query(default=True)):
    """置顶/取消置顶帖子"""
    async with db_manager._session_factory() as session:
        result = await channel_service.pin_post(session, channel_id, post_id, is_pinned)
        return {
            "success": True,
            "is_pinned": result.is_pinned,
        }


@router.post("/{channel_id}/posts/{post_id}/feature")
async def feature_post(channel_id: str, post_id: str, is_featured: bool = Query(default=True)):
    """加精/取消加精华帖子"""
    async with db_manager._session_factory() as session:
        result = await channel_service.feature_post(session, channel_id, post_id, is_featured)
        return {
            "success": True,
            "is_featured": result.is_featured,
        }


# ==================== 频道统计 ====================
@router.get("/{channel_id}/stats")
async def get_channel_stats(channel_id: str):
    """获取频道统计数据"""
    async with db_manager._session_factory() as session:
        stats = await channel_service.get_channel_stats(session, channel_id)
        if not stats:
            raise HTTPException(status_code=404, detail="频道不存在")
        return {"stats": stats}
