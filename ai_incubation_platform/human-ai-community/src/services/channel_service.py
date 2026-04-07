"""
频道/版块系统服务
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.channel_models import (
    DBChannelCategory,
    DBChannel,
    DBChannelMember,
    DBChannelPermission,
    DBChannelPost,
    ChannelCategoryType,
    ChannelAccessLevel,
)
from db.models import DBCommunityMember, DBPost, DBNotification
from services.notification_service import notification_service, NotificationEvent, NotificationMessage, NotificationPriority


class ChannelService:
    """频道服务"""

    def __init__(self):
        pass

    # ==================== 频道分类管理 ====================
    async def create_category(
        self,
        db: AsyncSession,
        name: str,
        description: str = None,
        category_type: str = ChannelCategoryType.OTHER.value,
        sort_order: int = 0,
        icon: str = None,
    ) -> DBChannelCategory:
        """创建频道分类"""
        # 检查名称是否已存在
        result = await db.execute(
            select(DBChannelCategory).where(DBChannelCategory.name == name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(f"分类名称 '{name}' 已存在")

        category = DBChannelCategory(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            category_type=category_type,
            sort_order=sort_order,
            icon=icon,
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    async def get_category(self, db: AsyncSession, category_id: str) -> Optional[DBChannelCategory]:
        """获取频道分类详情"""
        result = await db.execute(
            select(DBChannelCategory)
            .options(selectinload(DBChannelCategory.channels))
            .where(DBChannelCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    async def list_categories(
        self,
        db: AsyncSession,
        include_inactive: bool = False,
    ) -> List[DBChannelCategory]:
        """获取频道分类列表"""
        query = select(DBChannelCategory).order_by(DBChannelCategory.sort_order)
        if not include_inactive:
            query = query.where(DBChannelCategory.is_active == True)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_category(
        self,
        db: AsyncSession,
        category_id: str,
        **kwargs,
    ) -> Optional[DBChannelCategory]:
        """更新频道分类"""
        category = await self.get_category(db, category_id)
        if not category:
            return None

        for key, value in kwargs.items():
            if hasattr(category, key) and value is not None:
                setattr(category, key, value)

        await db.commit()
        await db.refresh(category)
        return category

    async def delete_category(self, db: AsyncSession, category_id: str) -> bool:
        """删除频道分类（软删除）"""
        category = await self.get_category(db, category_id)
        if not category:
            return False

        category.is_active = False
        await db.commit()
        return True

    # ==================== 频道管理 ====================
    async def create_channel(
        self,
        db: AsyncSession,
        category_id: str,
        name: str,
        slug: str,
        description: str = None,
        access_level: str = ChannelAccessLevel.PUBLIC.value,
        icon: str = None,
        banner: str = None,
        sort_order: int = 0,
        rules: List[str] = None,
        settings: Dict[str, Any] = None,
        owner_id: str = None,
        is_official: bool = False,
    ) -> DBChannel:
        """创建频道"""
        # 检查分类是否存在
        category = await self.get_category(db, category_id)
        if not category:
            raise ValueError("分类不存在")

        # 检查 slug 是否已存在
        result = await db.execute(
            select(DBChannel).where(DBChannel.slug == slug)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(f"频道标识符 '{slug}' 已存在")

        # 检查名称是否已存在
        result = await db.execute(
            select(DBChannel).where(DBChannel.name == name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(f"频道名称 '{name}' 已存在")

        channel = DBChannel(
            id=str(uuid.uuid4()),
            category_id=category_id,
            name=name,
            slug=slug,
            description=description,
            access_level=access_level,
            icon=icon,
            banner=banner,
            sort_order=sort_order,
            rules=rules or [],
            settings=settings or {},
            owner_id=owner_id,
            is_official=is_official,
        )
        db.add(channel)

        # 创建者自动成为频道所有者
        if owner_id:
            member = DBChannelMember(
                id=str(uuid.uuid4()),
                channel_id=channel.id,
                member_id=owner_id,
                role="owner",
            )
            db.add(member)

        # 初始化默认权限
        await self._init_channel_permissions(db, channel)

        await db.commit()
        await db.refresh(channel)
        return channel

    async def _init_channel_permissions(self, db: AsyncSession, channel: DBChannel):
        """初始化频道默认权限"""
        default_permissions = {
            "owner": ["all"],
            "admin": ["manage_channel", "manage_members", "manage_posts", "manage_comments"],
            "moderator": ["manage_posts", "manage_comments", "pin_post", "feature_post"],
            "member": ["create_post", "create_comment", "view_channel"],
        }

        for role, perms in default_permissions.items():
            permission = DBChannelPermission(
                id=str(uuid.uuid4()),
                channel_id=channel.id,
                role=role,
                permissions=perms,
            )
            db.add(permission)

    async def get_channel(self, db: AsyncSession, channel_id: str) -> Optional[DBChannel]:
        """获取频道详情"""
        result = await db.execute(
            select(DBChannel)
            .options(
                selectinload(DBChannel.category),
                selectinload(DBChannel.members),
            )
            .where(DBChannel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def get_channel_by_slug(self, db: AsyncSession, slug: str) -> Optional[DBChannel]:
        """通过 slug 获取频道"""
        result = await db.execute(
            select(DBChannel)
            .options(selectinload(DBChannel.category))
            .where(DBChannel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_channels(
        self,
        db: AsyncSession,
        category_id: str = None,
        access_level: str = None,
        is_official: bool = None,
        limit: int = 100,
    ) -> List[DBChannel]:
        """获取频道列表"""
        query = select(DBChannel).order_by(DBChannel.sort_order)

        if category_id:
            query = query.where(DBChannel.category_id == category_id)
        if access_level:
            query = query.where(DBChannel.access_level == access_level)
        if is_official is not None:
            query = query.where(DBChannel.is_official == is_official)

        query = query.where(DBChannel.is_active == True)
        query = query.limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_channel(
        self,
        db: AsyncSession,
        channel_id: str,
        **kwargs,
    ) -> Optional[DBChannel]:
        """更新频道"""
        channel = await self.get_channel(db, channel_id)
        if not channel:
            return None

        for key, value in kwargs.items():
            if hasattr(channel, key) and value is not None:
                setattr(channel, key, value)

        await db.commit()
        await db.refresh(channel)
        return channel

    async def delete_channel(self, db: AsyncSession, channel_id: str) -> bool:
        """删除频道（软删除）"""
        channel = await self.get_channel(db, channel_id)
        if not channel:
            return False

        channel.is_active = False
        await db.commit()
        return True

    # ==================== 频道成员管理 ====================
    async def join_channel(
        self,
        db: AsyncSession,
        channel_id: str,
        member_id: str,
    ) -> DBChannelMember:
        """加入频道"""
        # 检查频道是否存在
        channel = await self.get_channel(db, channel_id)
        if not channel:
            raise ValueError("频道不存在")

        # 检查是否已是成员
        result = await db.execute(
            select(DBChannelMember).where(
                DBChannelMember.channel_id == channel_id,
                DBChannelMember.member_id == member_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_active = True
            await db.commit()
            await db.refresh(existing)
            return existing

        # 创建成员记录
        member = DBChannelMember(
            id=str(uuid.uuid4()),
            channel_id=channel_id,
            member_id=member_id,
            role="member",
        )
        db.add(member)

        # 更新频道成员数
        channel.member_count += 1
        await db.commit()
        await db.refresh(member)

        # 发送加入通知
        await self._notify_channel_join(db, channel, member_id)

        return member

    async def leave_channel(
        self,
        db: AsyncSession,
        channel_id: str,
        member_id: str,
    ) -> bool:
        """退出频道"""
        result = await db.execute(
            select(DBChannelMember).where(
                DBChannelMember.channel_id == channel_id,
                DBChannelMember.member_id == member_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False

        # 如果是频道所有者，需要先转移所有权
        if member.role == "owner":
            raise ValueError("频道所有者不能退出，需要先转移所有权")

        member.is_active = False
        await db.commit()

        # 更新频道成员数
        channel = await self.get_channel(db, channel_id)
        if channel:
            channel.member_count = max(0, channel.member_count - 1)
            await db.commit()

        return True

    async def get_channel_member(
        self,
        db: AsyncSession,
        channel_id: str,
        member_id: str,
    ) -> Optional[DBChannelMember]:
        """获取频道成员信息"""
        result = await db.execute(
            select(DBChannelMember).where(
                DBChannelMember.channel_id == channel_id,
                DBChannelMember.member_id == member_id,
                DBChannelMember.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def list_channel_members(
        self,
        db: AsyncSession,
        channel_id: str,
        role: str = None,
        limit: int = 100,
    ) -> List[DBChannelMember]:
        """获取频道成员列表"""
        query = select(DBChannelMember).where(
            DBChannelMember.channel_id == channel_id,
            DBChannelMember.is_active == True,
        )
        if role:
            query = query.where(DBChannelMember.role == role)
        query = query.order_by(DBChannelMember.joined_at.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_member_role(
        self,
        db: AsyncSession,
        channel_id: str,
        member_id: str,
        new_role: str,
    ) -> Optional[DBChannelMember]:
        """更新成员角色"""
        member = await self.get_channel_member(db, channel_id, member_id)
        if not member:
            return None

        valid_roles = ["owner", "admin", "moderator", "member"]
        if new_role not in valid_roles:
            raise ValueError(f"无效的角色类型：{new_role}")

        # 如果是转移所有权，需要先处理原所有者
        if new_role == "owner":
            # 查找当前所有者
            result = await db.execute(
                select(DBChannelMember).where(
                    DBChannelMember.channel_id == channel_id,
                    DBChannelMember.role == "owner",
                    DBChannelMember.is_active == True,
                )
            )
            current_owner = result.scalar_one_or_none()
            if current_owner and current_owner.member_id != member_id:
                current_owner.role = "admin"

        member.role = new_role
        await db.commit()
        await db.refresh(member)
        return member

    async def _notify_channel_join(
        self,
        db: AsyncSession,
        channel: DBChannel,
        member_id: str,
    ):
        """发送加入频道通知"""
        notification = DBNotification(
            id=str(uuid.uuid4()),
            recipient_id=member_id,
            sender_id=None,
            notification_type="channel_join",
            title=f"欢迎加入 {channel.name}",
            content=f"您已成功加入频道「{channel.name}」，开始探索和分享吧！",
            related_content_id=channel.id,
            related_content_type="channel",
            is_read=False,
        )
        db.add(notification)

    # ==================== 频道权限管理 ====================
    async def get_channel_permissions(
        self,
        db: AsyncSession,
        channel_id: str,
        role: str = None,
    ) -> List[DBChannelPermission]:
        """获取频道权限配置"""
        query = select(DBChannelPermission).where(DBChannelPermission.channel_id == channel_id)
        if role:
            query = query.where(DBChannelPermission.role == role)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_channel_permissions(
        self,
        db: AsyncSession,
        channel_id: str,
        role: str,
        permissions: List[str],
    ) -> DBChannelPermission:
        """更新频道权限配置"""
        result = await db.execute(
            select(DBChannelPermission).where(
                DBChannelPermission.channel_id == channel_id,
                DBChannelPermission.role == role,
            )
        )
        permission = result.scalar_one_or_none()

        if permission:
            permission.permissions = permissions
            permission.updated_at = datetime.now()
        else:
            permission = DBChannelPermission(
                id=str(uuid.uuid4()),
                channel_id=channel_id,
                role=role,
                permissions=permissions,
            )
            db.add(permission)

        await db.commit()
        await db.refresh(permission)
        return permission

    async def check_channel_permission(
        self,
        db: AsyncSession,
        channel_id: str,
        member_id: str,
        permission: str,
    ) -> bool:
        """检查用户是否有频道权限"""
        # 获取用户在频道的角色
        member = await self.get_channel_member(db, channel_id, member_id)
        if not member:
            return False

        # 获取角色权限
        result = await db.execute(
            select(DBChannelPermission).where(
                DBChannelPermission.channel_id == channel_id,
                DBChannelPermission.role == member.role,
            )
        )
        channel_permission = result.scalar_one_or_none()
        if not channel_permission:
            return False

        # 检查是否有权限
        if "all" in channel_permission.permissions:
            return True
        return permission in channel_permission.permissions

    # ==================== 频道内容管理 ====================
    async def get_channel_posts(
        self,
        db: AsyncSession,
        channel_id: str,
        sort: str = "hot",
        limit: int = 50,
        offset: int = 0,
    ) -> List[DBPost]:
        """获取频道帖子列表"""
        # 获取频道所有置顶帖子
        result = await db.execute(
            select(DBChannelPost)
            .where(DBChannelPost.channel_id == channel_id)
            .where(DBChannelPost.is_pinned == True)
            .order_by(DBChannelPost.created_at.desc())
        )
        pinned_posts = result.scalars().all()
        pinned_post_ids = [p.post_id for p in pinned_posts]

        # 获取普通帖子（排除已删除的）
        from db.models import DBPost
        query = select(DBPost).where(
            DBPost.id.in_(pinned_post_ids) if pinned_post_ids else False  # 如果没有置顶帖，跳过此查询
        )

        # 单独查询普通帖子
        query = select(DBPost).where(
            DBPost.id.notin_(pinned_post_ids) if pinned_post_ids else True
        )

        # TODO: 根据 sort 参数进行排序
        query = query.order_by(DBPost.created_at.desc()).limit(limit).offset(offset)

        result = await db.execute(query)
        posts = list(result.scalars().all())

        # 置顶帖子排在前面
        if pinned_posts:
            pinned_result = await db.execute(
                select(DBPost).where(DBPost.id.in_(pinned_post_ids))
            )
            pinned_posts_data = pinned_result.scalars().all()
            posts = list(pinned_posts_data) + posts

        return posts

    async def pin_post(
        self,
        db: AsyncSession,
        channel_id: str,
        post_id: str,
        is_pinned: bool = True,
    ) -> Optional[DBChannelPost]:
        """置顶/取消置顶帖子"""
        result = await db.execute(
            select(DBChannelPost).where(
                DBChannelPost.channel_id == channel_id,
                DBChannelPost.post_id == post_id,
            )
        )
        channel_post = result.scalar_one_or_none()

        if channel_post:
            channel_post.is_pinned = is_pinned
        else:
            channel_post = DBChannelPost(
                id=str(uuid.uuid4()),
                channel_id=channel_id,
                post_id=post_id,
                is_pinned=is_pinned,
            )
            db.add(channel_post)

        await db.commit()
        await db.refresh(channel_post)
        return channel_post

    async def feature_post(
        self,
        db: AsyncSession,
        channel_id: str,
        post_id: str,
        is_featured: bool = True,
    ) -> Optional[DBChannelPost]:
        """加精/取消加精华帖子"""
        result = await db.execute(
            select(DBChannelPost).where(
                DBChannelPost.channel_id == channel_id,
                DBChannelPost.post_id == post_id,
            )
        )
        channel_post = result.scalar_one_or_none()

        if channel_post:
            channel_post.is_featured = is_featured
        else:
            channel_post = DBChannelPost(
                id=str(uuid.uuid4()),
                channel_id=channel_id,
                post_id=post_id,
                is_featured=is_featured,
            )
            db.add(channel_post)

        await db.commit()
        await db.refresh(channel_post)
        return channel_post

    # ==================== 频道统计 ====================
    async def get_channel_stats(self, db: AsyncSession, channel_id: str) -> Dict[str, Any]:
        """获取频道统计数据"""
        channel = await self.get_channel(db, channel_id)
        if not channel:
            return {}

        # 统计成员数
        result = await db.execute(
            select(func.count(DBChannelMember.id)).where(
                DBChannelMember.channel_id == channel_id,
                DBChannelMember.is_active == True,
            )
        )
        member_count = result.scalar() or 0

        # 统计帖子数
        result = await db.execute(
            select(func.count(DBChannelPost.id)).where(
                DBChannelPost.channel_id == channel_id,
            )
        )
        post_count = result.scalar() or 0

        return {
            "channel_id": channel_id,
            "name": channel.name,
            "member_count": member_count,
            "post_count": post_count,
            "last_activity_at": channel.last_activity_at,
        }


# 全局服务实例
channel_service = ChannelService()
