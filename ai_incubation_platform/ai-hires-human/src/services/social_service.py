"""
社交网络服务层 - v1.19 社交网络增强

提供好友动态、社区圈子、内容分享、社交图谱、隐私设置等核心业务逻辑
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid
import logging

from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.social_db import (
    SocialPostDB, SocialCommentDB, PostInteractionDB, BookmarkDB, ShareDB,
    SocialRelationshipDB, FriendRequestDB, SocialCircleDB, CircleMemberDB,
    CircleJoinRequestDB, PrivacySettingsDB, SocialNotificationDB, SocialGraphConnectionDB
)
from models.social import (
    SocialPost, SocialComment, SocialCircle, CircleMember, SocialRelationship,
    FriendRequest, SocialNotification, PrivacySettings, FeedPost, FeedResponse,
    PostVisibility, CircleType, CircleRole, RelationshipType, PostStatus, SocialNotificationType
)

logger = logging.getLogger(__name__)


# ==================== 社交帖子服务 ====================

class SocialPostService:
    """社交帖子服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_post(
        self,
        author_id: str,
        author_type: str,
        author_name: Optional[str],
        content: str,
        content_type: str = "text",
        media_urls: Optional[List[str]] = None,
        visibility: str = "public",
        tags: Optional[List[str]] = None,
        circle_id: Optional[str] = None
    ) -> SocialPostDB:
        """创建社交帖子"""
        post_id = str(uuid.uuid4())

        post = SocialPostDB(
            post_id=post_id,
            author_id=author_id,
            author_type=author_type,
            author_name=author_name,
            content=content,
            content_type=content_type,
            media_urls=media_urls or [],
            visibility=visibility,
            tags=tags or [],
            circle_id=circle_id,
            published_at=datetime.now() if visibility != "draft" else None,
            status="published" if visibility != "draft" else "draft"
        )

        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)

        # 如果是圈子帖子，增加圈子帖子计数
        if circle_id:
            await self._increment_circle_post_count(circle_id)

        logger.info(f"创建社交帖子：{post_id}, author={author_id}")
        return post

    async def get_post(self, post_id: str) -> Optional[SocialPostDB]:
        """获取帖子详情"""
        result = await self.db.execute(
            select(SocialPostDB).where(SocialPostDB.post_id == post_id)
        )
        return result.scalar_one_or_none()

    async def get_user_feed(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[SocialPostDB], int]:
        """获取用户 Feed（首页动态）"""
        # 获取用户的好友列表和加入的圈子
        friend_ids = await self._get_user_friend_ids(user_id)
        circle_ids = await self._get_user_circle_ids(user_id)

        # 构建可见性条件
        visibility_conditions = [
            SocialPostDB.visibility == "public",
            and_(SocialPostDB.visibility == "friends", SocialPostDB.author_id.in_(friend_ids)) if friend_ids else SocialPostDB.visibility == "friends",
            and_(SocialPostDB.visibility == "circle", SocialPostDB.circle_id.in_(circle_ids)) if circle_ids else SocialPostDB.visibility == "circle",
            and_(SocialPostDB.visibility == "workers", SocialPostDB.author_type == "worker"),
            and_(SocialPostDB.visibility == "employers", SocialPostDB.author_type == "employer"),
            SocialPostDB.author_id == user_id,  # 自己发的帖子总能看到
        ]

        # 过滤条件
        filter_conditions = [
            or_(*visibility_conditions),
            SocialPostDB.status == "published",
        ]

        # 查询
        query = select(SocialPostDB).where(
            and_(*filter_conditions)
        ).order_by(
            desc(SocialPostDB.created_at)
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        posts = result.scalars().all()

        # 获取总数
        count_query = select(func.count()).select_from(
            SocialPostDB
        ).where(and_(*filter_conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return list(posts), total

    async def get_circle_feed(
        self,
        circle_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[SocialPostDB], int]:
        """获取圈子 Feed"""
        # 检查用户是否是圈子成员
        is_member = await self._is_circle_member(circle_id, user_id)
        if not is_member:
            # 检查圈子是否公开
            circle_result = await self.db.execute(
                select(SocialCircleDB).where(SocialCircleDB.circle_id == circle_id)
            )
            circle = circle_result.scalar_one_or_none()
            if not circle or circle.visibility != "public":
                return [], 0

        query = select(SocialPostDB).where(
            and_(
                SocialPostDB.circle_id == circle_id,
                SocialPostDB.status == "published"
            )
        ).order_by(
            desc(SocialPostDB.created_at)
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        posts = result.scalars().all()

        count_query = select(func.count()).select_from(
            SocialPostDB
        ).where(
            and_(
                SocialPostDB.circle_id == circle_id,
                SocialPostDB.status == "published"
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return list(posts), total

    async def get_user_posts(
        self,
        user_id: str,
        viewer_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[SocialPostDB], int]:
        """获取用户帖子列表"""
        # 检查隐私设置
        if viewer_id and viewer_id != user_id:
            can_see = await self._can_view_user_posts(user_id, viewer_id)
            if not can_see:
                return [], 0

        query = select(SocialPostDB).where(
            and_(
                SocialPostDB.author_id == user_id,
                SocialPostDB.status == "published"
            )
        ).order_by(
            desc(SocialPostDB.created_at)
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        posts = result.scalars().all()

        count_query = select(func.count()).select_from(
            SocialPostDB
        ).where(
            and_(
                SocialPostDB.author_id == user_id,
                SocialPostDB.status == "published"
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return list(posts), total

    async def update_post(
        self,
        post_id: str,
        author_id: str,
        content: Optional[str] = None,
        visibility: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[SocialPostDB]:
        """更新帖子"""
        post = await self.get_post(post_id)
        if not post or post.author_id != author_id:
            return None

        if content is not None:
            post.content = content
        if visibility is not None:
            post.visibility = visibility
        if tags is not None:
            post.tags = tags

        post.updated_at = datetime.now()

        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def delete_post(self, post_id: str, author_id: str) -> bool:
        """删除帖子"""
        post = await self.get_post(post_id)
        if not post or post.author_id != author_id:
            return False

        post.status = "deleted"
        post.updated_at = datetime.now()

        # 如果是圈子帖子，减少圈子帖子计数
        if post.circle_id:
            await self._decrement_circle_post_count(post.circle_id)

        await self.db.commit()
        logger.info(f"删除帖子：{post_id}")
        return True

    async def like_post(self, post_id: str, user_id: str, user_type: str = "user") -> bool:
        """点赞帖子"""
        # 检查是否已点赞
        existing = await self.db.execute(
            select(PostInteractionDB).where(
                and_(
                    PostInteractionDB.post_id == post_id,
                    PostInteractionDB.user_id == user_id
                )
            )
        )
        if existing.scalar_one_or_none():
            return False

        interaction = PostInteractionDB(
            interaction_id=str(uuid.uuid4()),
            post_id=post_id,
            user_id=user_id,
            user_type=user_type,
            interaction_type="like"
        )
        self.db.add(interaction)

        # 增加点赞计数
        await self.db.execute(
            select(SocialPostDB).where(SocialPostDB.post_id == post_id)
        )
        post = (await self.db.execute(
            select(SocialPostDB).where(SocialPostDB.post_id == post_id)
        )).scalar_one()
        post.like_count += 1

        await self.db.commit()

        # 创建通知
        if user_id != post.author_id:
            await self._create_notification(
                recipient_id=post.author_id,
                sender_id=user_id,
                notification_type="like",
                post_id=post_id
            )

        return True

    async def unlike_post(self, post_id: str, user_id: str) -> bool:
        """取消点赞"""
        interaction = await self.db.execute(
            select(PostInteractionDB).where(
                and_(
                    PostInteractionDB.post_id == post_id,
                    PostInteractionDB.user_id == user_id
                )
            )
        )
        interaction_db = interaction.scalar_one_or_none()
        if not interaction_db:
            return False

        await self.db.delete(interaction_db)

        # 减少点赞计数
        post = (await self.db.execute(
            select(SocialPostDB).where(SocialPostDB.post_id == post_id)
        )).scalar_one()
        post.like_count = max(0, post.like_count - 1)

        await self.db.commit()
        return True

    async def add_comment(
        self,
        post_id: str,
        author_id: str,
        author_type: str,
        author_name: Optional[str],
        content: str,
        parent_comment_id: Optional[str] = None
    ) -> SocialCommentDB:
        """添加评论"""
        comment_id = str(uuid.uuid4())

        comment = SocialCommentDB(
            comment_id=comment_id,
            post_id=post_id,
            parent_comment_id=parent_comment_id,
            author_id=author_id,
            author_type=author_type,
            author_name=author_name,
            content=content
        )
        self.db.add(comment)

        # 增加评论计数
        post = (await self.db.execute(
            select(SocialPostDB).where(SocialPostDB.post_id == post_id)
        )).scalar_one()
        post.comment_count += 1

        await self.db.commit()
        await self.db.refresh(comment)

        # 创建通知
        if author_id != post.author_id:
            await self._create_notification(
                recipient_id=post.author_id,
                sender_id=author_id,
                notification_type="comment",
                post_id=post_id,
                preview_content=content[:100]
            )

        return comment

    async def get_post_comments(
        self,
        post_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[SocialCommentDB]:
        """获取帖子评论"""
        query = select(SocialCommentDB).where(
            and_(
                SocialCommentDB.post_id == post_id,
                SocialCommentDB.status == "published",
                SocialCommentDB.is_deleted == False
            )
        ).order_by(
            SocialCommentDB.created_at
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def bookmark_post(self, post_id: str, user_id: str) -> bool:
        """收藏帖子"""
        existing = await self.db.execute(
            select(BookmarkDB).where(
                and_(
                    BookmarkDB.post_id == post_id,
                    BookmarkDB.user_id == user_id
                )
            )
        )
        if existing.scalar_one_or_none():
            return False

        bookmark = BookmarkDB(
            bookmark_id=str(uuid.uuid4()),
            user_id=user_id,
            post_id=post_id
        )
        self.db.add(bookmark)
        await self.db.commit()
        return True

    async def share_post(
        self,
        post_id: str,
        user_id: str,
        share_type: str = "repost",
        share_content: Optional[str] = None
    ) -> ShareDB:
        """分享帖子"""
        share_id = str(uuid.uuid4())

        share = ShareDB(
            share_id=share_id,
            user_id=user_id,
            post_id=post_id,
            share_type=share_type,
            share_content=share_content
        )
        self.db.add(share)

        # 增加分享计数
        post = (await self.db.execute(
            select(SocialPostDB).where(SocialPostDB.post_id == post_id)
        )).scalar_one()
        post.share_count += 1

        await self.db.commit()
        await self.db.refresh(share)

        # 创建通知
        original_post = await self.get_post(post_id)
        if user_id != original_post.author_id:
            await self._create_notification(
                recipient_id=original_post.author_id,
                sender_id=user_id,
                notification_type="share",
                post_id=post_id
            )

        return share

    async def _increment_circle_post_count(self, circle_id: str):
        """增加圈子帖子计数"""
        circle = (await self.db.execute(
            select(SocialCircleDB).where(SocialCircleDB.circle_id == circle_id)
        )).scalar_one()
        circle.post_count += 1
        await self.db.commit()

    async def _decrement_circle_post_count(self, circle_id: str):
        """减少圈子帖子计数"""
        circle = (await self.db.execute(
            select(SocialCircleDB).where(SocialCircleDB.circle_id == circle_id)
        )).scalar_one()
        circle.post_count = max(0, circle.post_count - 1)
        await self.db.commit()

    async def _get_user_friend_ids(self, user_id: str) -> List[str]:
        """获取用户好友 ID 列表"""
        result = await self.db.execute(
            select(SocialRelationshipDB).where(
                or_(
                    and_(
                        SocialRelationshipDB.user_id == user_id,
                        SocialRelationshipDB.relationship_type == "friend",
                        SocialRelationshipDB.is_mutual == True,
                        SocialRelationshipDB.status == "active"
                    ),
                    and_(
                        SocialRelationshipDB.target_id == user_id,
                        SocialRelationshipDB.relationship_type == "friend",
                        SocialRelationshipDB.is_mutual == True,
                        SocialRelationshipDB.status == "active"
                    )
                )
            )
        )
        relationships = result.scalars().all()
        friend_ids = []
        for rel in relationships:
            if rel.user_id == user_id:
                friend_ids.append(rel.target_id)
            else:
                friend_ids.append(rel.user_id)
        return friend_ids

    async def _get_user_circle_ids(self, user_id: str) -> List[str]:
        """获取用户加入的圈子 ID 列表"""
        result = await self.db.execute(
            select(CircleMemberDB).where(
                and_(
                    CircleMemberDB.user_id == user_id,
                    CircleMemberDB.status == "active"
                )
            )
        )
        members = result.scalars().all()
        return [m.circle_id for m in members]

    async def _is_circle_member(self, circle_id: str, user_id: str) -> bool:
        """检查用户是否是圈子成员"""
        result = await self.db.execute(
            select(CircleMemberDB).where(
                and_(
                    CircleMemberDB.circle_id == circle_id,
                    CircleMemberDB.user_id == user_id,
                    CircleMemberDB.status == "active"
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def _can_view_user_posts(self, user_id: str, viewer_id: str) -> bool:
        """检查查看者是否能看用户的帖子"""
        privacy_result = await self.db.execute(
            select(PrivacySettingsDB).where(PrivacySettingsDB.user_id == user_id)
        )
        privacy = privacy_result.scalar_one_or_none()

        if not privacy:
            return True  # 没有设置默认公开

        if privacy.who_can_see_posts == "everyone":
            return True
        elif privacy.who_can_see_posts == "friends":
            friend_ids = await self._get_user_friend_ids(user_id)
            return viewer_id in friend_ids
        elif privacy.who_can_see_posts == "self":
            return viewer_id == user_id

        return True

    async def _create_notification(
        self,
        recipient_id: str,
        sender_id: str,
        notification_type: str,
        post_id: Optional[str] = None,
        preview_content: Optional[str] = None
    ):
        """创建社交通知"""
        notification = SocialNotificationDB(
            notification_id=str(uuid.uuid4()),
            recipient_id=recipient_id,
            notification_type=notification_type,
            sender_id=sender_id,
            post_id=post_id,
            preview_content=preview_content
        )
        self.db.add(notification)
        await self.db.commit()


# ==================== 社交关系服务 ====================

class SocialRelationshipService:
    """社交关系服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_friend_request(
        self,
        sender_id: str,
        receiver_id: str,
        message: Optional[str] = None
    ) -> FriendRequestDB:
        """发送好友请求"""
        # 检查是否已有好友关系
        existing = await self.db.execute(
            select(SocialRelationshipDB).where(
                or_(
                    and_(
                        SocialRelationshipDB.user_id == sender_id,
                        SocialRelationshipDB.target_id == receiver_id
                    ),
                    and_(
                        SocialRelationshipDB.user_id == receiver_id,
                        SocialRelationshipDB.target_id == sender_id
                    )
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("已存在好友关系")

        # 检查是否已有待处理请求
        pending = await self.db.execute(
            select(FriendRequestDB).where(
                and_(
                    FriendRequestDB.sender_id == sender_id,
                    FriendRequestDB.receiver_id == receiver_id,
                    FriendRequestDB.status == "pending"
                )
            )
        )
        if pending.scalar_one_or_none():
            raise ValueError("已有待处理的好友请求")

        request_id = str(uuid.uuid4())
        request = FriendRequestDB(
            request_id=request_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message
        )
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)

        logger.info(f"发送好友请求：{request_id}, from={sender_id}, to={receiver_id}")
        return request

    async def respond_friend_request(
        self,
        request_id: str,
        user_id: str,
        accept: bool
    ) -> bool:
        """响应好友请求"""
        request = (await self.db.execute(
            select(FriendRequestDB).where(FriendRequestDB.request_id == request_id)
        )).scalar_one_or_none()

        if not request or request.receiver_id != user_id:
            return False

        if accept:
            # 创建双向好友关系
            relationship1 = SocialRelationshipDB(
                relationship_id=str(uuid.uuid4()),
                user_id=request.sender_id,
                target_id=request.receiver_id,
                relationship_type="friend",
                status="active",
                is_mutual=True
            )
            relationship2 = SocialRelationshipDB(
                relationship_id=str(uuid.uuid4()),
                user_id=request.receiver_id,
                target_id=request.sender_id,
                relationship_type="friend",
                status="active",
                is_mutual=True
            )
            self.db.add(relationship1)
            self.db.add(relationship2)

            request.status = "accepted"
        else:
            request.status = "rejected"

        request.responded_at = datetime.now()
        await self.db.commit()
        return True

    async def get_friend_requests(
        self,
        user_id: str,
        status: str = "pending"
    ) -> List[FriendRequestDB]:
        """获取用户的好友请求"""
        result = await self.db.execute(
            select(FriendRequestDB).where(
                and_(
                    FriendRequestDB.receiver_id == user_id,
                    FriendRequestDB.status == status
                )
            ).order_by(desc(FriendRequestDB.created_at))
        )
        return list(result.scalars().all())

    async def get_friends(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[SocialRelationshipDB], int]:
        """获取用户好友列表"""
        query = select(SocialRelationshipDB).where(
            and_(
                SocialRelationshipDB.user_id == user_id,
                SocialRelationshipDB.relationship_type == "friend",
                SocialRelationshipDB.is_mutual == True,
                SocialRelationshipDB.status == "active"
            )
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        relationships = list(result.scalars().all())

        count_query = select(func.count()).select_from(
            SocialRelationshipDB
        ).where(
            and_(
                SocialRelationshipDB.user_id == user_id,
                SocialRelationshipDB.relationship_type == "friend",
                SocialRelationshipDB.is_mutual == True,
                SocialRelationshipDB.status == "active"
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return relationships, total

    async def remove_friend(self, user_id: str, friend_id: str) -> bool:
        """删除好友"""
        # 删除双向关系
        await self.db.execute(
            select(SocialRelationshipDB).where(
                or_(
                    and_(
                        SocialRelationshipDB.user_id == user_id,
                        SocialRelationshipDB.target_id == friend_id
                    ),
                    and_(
                        SocialRelationshipDB.user_id == friend_id,
                        SocialRelationshipDB.target_id == user_id
                    )
                )
            )
        )

        await self.db.commit()
        return True

    async def block_user(self, user_id: str, target_id: str) -> SocialRelationshipDB:
        """拉黑用户"""
        relationship = SocialRelationshipDB(
            relationship_id=str(uuid.uuid4()),
            user_id=user_id,
            target_id=target_id,
            relationship_type="blocked",
            status="active"
        )
        self.db.add(relationship)
        await self.db.commit()
        await self.db.refresh(relationship)
        return relationship

    async def get_mutual_friends(
        self,
        user_id: str,
        target_id: str,
        limit: int = 20
    ) -> List[str]:
        """获取共同好友"""
        # 获取 user_id 的好友列表
        user_friends_result = await self.db.execute(
            select(SocialRelationshipDB).where(
                and_(
                    SocialRelationshipDB.user_id == user_id,
                    SocialRelationshipDB.relationship_type == "friend",
                    SocialRelationshipDB.is_mutual == True
                )
            )
        )
        user_friends = set()
        for rel in user_friends_result.scalars().all():
            if rel.target_id != target_id:
                user_friends.add(rel.target_id)

        # 获取 target_id 的好友列表
        target_friends_result = await self.db.execute(
            select(SocialRelationshipDB).where(
                and_(
                    SocialRelationshipDB.user_id == target_id,
                    SocialRelationshipDB.relationship_type == "friend",
                    SocialRelationshipDB.is_mutual == True
                )
            )
        )
        target_friends = set()
        for rel in target_friends_result.scalars().all():
            if rel.target_id != user_id:
                target_friends.add(rel.target_id)

        # 返回交集
        mutual = user_friends.intersection(target_friends)
        return list(mutual)[:limit]


# ==================== 圈子服务 ====================

class SocialCircleService:
    """社交圈子服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_circle(
        self,
        creator_id: str,
        creator_name: Optional[str],
        name: str,
        description: Optional[str],
        circle_type: str,
        category: Optional[str],
        join_type: str = "open",
        visibility: str = "public",
        rules: Optional[List[str]] = None
    ) -> SocialCircleDB:
        """创建圈子"""
        circle_id = str(uuid.uuid4())

        circle = SocialCircleDB(
            circle_id=circle_id,
            name=name,
            description=description,
            circle_type=circle_type,
            category=category,
            creator_id=creator_id,
            creator_name=creator_name,
            join_type=join_type,
            visibility=visibility,
            rules=rules or [],
            member_count=1,  # 创建者自动成为成员
            is_active=True
        )
        self.db.add(circle)

        # 创建者自动成为管理员
        member = CircleMemberDB(
            membership_id=str(uuid.uuid4()),
            circle_id=circle_id,
            user_id=creator_id,
            user_name=creator_name,
            role="admin",
            status="active"
        )
        self.db.add(member)

        await self.db.commit()
        await self.db.refresh(circle)

        logger.info(f"创建圈子：{circle_id}, name={name}, creator={creator_id}")
        return circle

    async def get_circle(self, circle_id: str) -> Optional[SocialCircleDB]:
        """获取圈子详情"""
        result = await self.db.execute(
            select(SocialCircleDB).where(SocialCircleDB.circle_id == circle_id)
        )
        return result.scalar_one_or_none()

    async def join_circle(
        self,
        circle_id: str,
        user_id: str,
        user_name: Optional[str],
        message: Optional[str] = None
    ) -> Optional[CircleMemberDB]:
        """加入圈子"""
        circle = await self.get_circle(circle_id)
        if not circle or not circle.is_active:
            raise ValueError("圈子不存在或已停用")

        # 检查是否已是成员
        existing = await self.db.execute(
            select(CircleMemberDB).where(
                and_(
                    CircleMemberDB.circle_id == circle_id,
                    CircleMemberDB.user_id == user_id,
                    CircleMemberDB.status == "active"
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("已是圈子成员")

        if circle.join_type == "open":
            # 直接加入
            member = CircleMemberDB(
                membership_id=str(uuid.uuid4()),
                circle_id=circle_id,
                user_id=user_id,
                user_name=user_name,
                role="member",
                status="active",
                join_method="apply"
            )
            self.db.add(member)
            circle.member_count += 1
            await self.db.commit()
            await self.db.refresh(member)
            return member
        elif circle.join_type == "approval":
            # 需要审批
            request = CircleJoinRequestDB(
                request_id=str(uuid.uuid4()),
                circle_id=circle_id,
                user_id=user_id,
                message=message
            )
            self.db.add(request)
            await self.db.commit()
            await self.db.refresh(request)
            return None
        else:
            raise ValueError("圈子仅允许邀请加入")

    async def leave_circle(self, circle_id: str, user_id: str) -> bool:
        """退出圈子"""
        member = (await self.db.execute(
            select(CircleMemberDB).where(
                and_(
                    CircleMemberDB.circle_id == circle_id,
                    CircleMemberDB.user_id == user_id,
                    CircleMemberDB.status == "active"
                )
            )
        )).scalar_one_or_none()

        if not member:
            return False

        # 如果是圈主，不能退出（只能转让）
        if member.role == "admin":
            raise ValueError("圈主不能退出圈子，请先转让圈主身份")

        member.status = "left"
        circle = await self.get_circle(circle_id)
        if circle:
            circle.member_count = max(0, circle.member_count - 1)

        await self.db.commit()
        return True

    async def get_user_circles(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[SocialCircleDB], int]:
        """获取用户加入的圈子"""
        # 先获取成员的圈子 ID
        member_result = await self.db.execute(
            select(CircleMemberDB.circle_id).where(
                and_(
                    CircleMemberDB.user_id == user_id,
                    CircleMemberDB.status == "active"
                )
            ).offset(skip).limit(limit)
        )
        circle_ids = [r[0] for r in member_result.all()]

        if not circle_ids:
            return [], 0

        # 获取圈子详情
        circles_result = await self.db.execute(
            select(SocialCircleDB).where(
                and_(
                    SocialCircleDB.circle_id.in_(circle_ids),
                    SocialCircleDB.is_active == True
                )
            )
        )
        circles = list(circles_result.scalars().all())

        # 获取总数
        count_query = select(func.count()).select_from(
            CircleMemberDB
        ).where(
            and_(
                CircleMemberDB.user_id == user_id,
                CircleMemberDB.status == "active"
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return circles, total

    async def get_circle_members(
        self,
        circle_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[CircleMemberDB], int]:
        """获取圈子成员列表"""
        query = select(CircleMemberDB).where(
            and_(
                CircleMemberDB.circle_id == circle_id,
                CircleMemberDB.status == "active"
            )
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        members = list(result.scalars().all())

        count_query = select(func.count()).select_from(
            CircleMemberDB
        ).where(
            and_(
                CircleMemberDB.circle_id == circle_id,
                CircleMemberDB.status == "active"
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return members, total

    async def approve_join_request(
        self,
        request_id: str,
        approver_id: str
    ) -> bool:
        """批准加入圈子申请"""
        request = (await self.db.execute(
            select(CircleJoinRequestDB).where(
                CircleJoinRequestDB.request_id == request_id
            )
        )).scalar_one_or_none()

        if not request or request.status != "pending":
            return False

        # 检查审批者是否是圈子管理员
        approver_member = (await self.db.execute(
            select(CircleMemberDB).where(
                and_(
                    CircleMemberDB.circle_id == request.circle_id,
                    CircleMemberDB.user_id == approver_id,
                    CircleMemberDB.role.in_(["admin", "moderator"])
                )
            )
        )).scalar_one_or_none()

        if not approver_member:
            raise ValueError("无权限审批")

        # 创建成员记录
        member = CircleMemberDB(
            membership_id=str(uuid.uuid4()),
            circle_id=request.circle_id,
            user_id=request.user_id,
            role="member",
            status="active",
            join_method="apply"
        )
        self.db.add(member)

        # 更新圈子成员数
        circle = await self.get_circle(request.circle_id)
        if circle:
            circle.member_count += 1

        # 更新请求状态
        request.status = "approved"
        request.responded_at = datetime.now()

        await self.db.commit()
        return True

    async def reject_join_request(
        self,
        request_id: str,
        approver_id: str
    ) -> bool:
        """拒绝加入圈子申请"""
        request = (await self.db.execute(
            select(CircleJoinRequestDB).where(
                CircleJoinRequestDB.request_id == request_id
            )
        )).scalar_one_or_none()

        if not request or request.status != "pending":
            return False

        # 检查审批者是否是圈子管理员
        approver_member = (await self.db.execute(
            select(CircleMemberDB).where(
                and_(
                    CircleMemberDB.circle_id == request.circle_id,
                    CircleMemberDB.user_id == approver_id,
                    CircleMemberDB.role.in_(["admin", "moderator"])
                )
            )
        )).scalar_one_or_none()

        if not approver_member:
            raise ValueError("无权限审批")

        request.status = "rejected"
        request.responded_at = datetime.now()

        await self.db.commit()
        return True


# ==================== 隐私设置服务 ====================

class PrivacySettingsService:
    """隐私设置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_settings(self, user_id: str) -> Optional[PrivacySettingsDB]:
        """获取用户隐私设置"""
        result = await self.db.execute(
            select(PrivacySettingsDB).where(PrivacySettingsDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_settings(
        self,
        user_id: str,
        settings: Dict
    ) -> PrivacySettingsDB:
        """更新用户隐私设置"""
        existing = await self.get_settings(user_id)

        if existing:
            # 更新现有设置
            for key, value in settings.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now()
        else:
            # 创建新设置
            existing = PrivacySettingsDB(
                user_id=user_id,
                **{k: v for k, v in settings.items() if hasattr(PrivacySettingsDB, k)}
            )
            self.db.add(existing)

        await self.db.commit()
        await self.db.refresh(existing)
        return existing

    async def block_user(self, user_id: str, target_id: str) -> PrivacySettingsDB:
        """拉黑用户"""
        settings = await self.get_settings(user_id)
        if not settings:
            settings = PrivacySettingsDB(user_id=user_id)
            self.db.add(settings)

        if target_id not in settings.blocked_users:
            settings.blocked_users.append(target_id)

        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def unblock_user(self, user_id: str, target_id: str) -> PrivacySettingsDB:
        """取消拉黑用户"""
        settings = await self.get_settings(user_id)
        if settings and target_id in settings.blocked_users:
            settings.blocked_users.remove(target_id)
            await self.db.commit()
        return settings


# ==================== 通知服务 ====================

class SocialNotificationService:
    """社交通知服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_notifications(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False
    ) -> Tuple[List[SocialNotificationDB], int]:
        """获取用户通知"""
        conditions = [SocialNotificationDB.recipient_id == user_id]
        if unread_only:
            conditions.append(SocialNotificationDB.is_read == False)

        query = select(SocialNotificationDB).where(
            and_(*conditions)
        ).order_by(
            desc(SocialNotificationDB.created_at)
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        count_query = select(func.count()).select_from(
            SocialNotificationDB
        ).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return notifications, total

    async def mark_as_read(self, user_id: str, notification_ids: List[str]) -> int:
        """标记通知为已读"""
        from sqlalchemy import update

        stmt = update(SocialNotificationDB).where(
            and_(
                SocialNotificationDB.notification_id.in_(notification_ids),
                SocialNotificationDB.recipient_id == user_id
            )
        ).values(is_read=True)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def mark_all_as_read(self, user_id: str) -> int:
        """标记所有通知为已读"""
        from sqlalchemy import update

        stmt = update(SocialNotificationDB).where(
            and_(
                SocialNotificationDB.recipient_id == user_id,
                SocialNotificationDB.is_read == False
            )
        ).values(is_read=True)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount


# ==================== 工厂函数 ====================

def get_social_post_service(db: AsyncSession) -> SocialPostService:
    """获取社交帖子服务"""
    return SocialPostService(db)


def get_social_relationship_service(db: AsyncSession) -> SocialRelationshipService:
    """获取社交关系服务"""
    return SocialRelationshipService(db)


def get_social_circle_service(db: AsyncSession) -> SocialCircleService:
    """获取社交圈子服务"""
    return SocialCircleService(db)


def get_privacy_settings_service(db: AsyncSession) -> PrivacySettingsService:
    """获取隐私设置服务"""
    return PrivacySettingsService(db)


def get_social_notification_service(db: AsyncSession) -> SocialNotificationService:
    """获取社交通知服务"""
    return SocialNotificationService(db)
