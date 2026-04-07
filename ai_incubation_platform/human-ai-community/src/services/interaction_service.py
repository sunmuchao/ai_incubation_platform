"""
互动服务层 - 点赞、收藏、关注等功能
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.member import ContentType, MemberType
from db.models import DBLike, DBBookmark, DBFollow, DBNotification
from repositories.like_repository import LikeRepository
from repositories.bookmark_repository import BookmarkRepository
from repositories.follow_repository import FollowRepository
from repositories.notification_repository import NotificationRepository
from repositories.member_repository import MemberRepository
from db.manager import db_manager


class InteractionService:
    """互动服务"""

    def __init__(self):
        self._db = None
        self._like_repo: Optional[LikeRepository] = None
        self._bookmark_repo: Optional[BookmarkRepository] = None
        self._follow_repo: Optional[FollowRepository] = None
        self._notification_repo: Optional[NotificationRepository] = None
        self._member_repo: Optional[MemberRepository] = None

    def _get_repos(self, db):
        """获取 repository 实例"""
        return {
            "like": LikeRepository(db),
            "bookmark": BookmarkRepository(db),
            "follow": FollowRepository(db),
            "notification": NotificationRepository(db),
            "member": MemberRepository(db),
        }

    # ==================== 点赞功能 ====================
    async def toggle_like(
        self,
        db,
        user_id: str,
        content_id: str,
        content_type: ContentType
    ) -> Dict[str, Any]:
        """切换点赞状态（点赞/取消点赞）"""
        like_repo = LikeRepository(db)

        # 检查是否已点赞
        existing_like = await like_repo.get_by_user_and_content(
            user_id, content_id, content_type
        )

        if existing_like:
            # 取消点赞
            await like_repo.delete(existing_like.id)
            return {"liked": False, "action": "unliked"}
        else:
            # 创建点赞
            like = DBLike(
                user_id=user_id,
                content_id=content_id,
                content_type=content_type,
            )
            await like_repo.create(like)

            # 发送通知给内容作者（如果是帖子或评论）
            await self._notify_like(db, user_id, content_id, content_type)

            return {"liked": True, "action": "liked"}

    async def get_like_status(
        self,
        db,
        user_id: str,
        content_id: str,
        content_type: ContentType
    ) -> Dict[str, Any]:
        """获取点赞状态"""
        like_repo = LikeRepository(db)
        is_liked = await like_repo.get_by_user_and_content(user_id, content_id, content_type)
        count = await like_repo.count_by_content(content_id, content_type)

        return {
            "is_liked": is_liked is not None,
            "like_count": count
        }

    async def get_user_likes(
        self,
        db,
        user_id: str,
        limit: int = 50
    ) -> List[DBLike]:
        """获取用户的点赞列表"""
        like_repo = LikeRepository(db)
        return await like_repo.list_by_user(user_id, limit)

    async def _notify_like(
        self,
        db,
        user_id: str,
        content_id: str,
        content_type: ContentType
    ):
        """发送点赞通知（简化实现，待完善）"""
        # 这里可以获取内容作者 ID 并发送通知
        # 由于需要查询帖子或评论，暂时简化处理
        pass

    # ==================== 收藏功能 ====================
    async def toggle_bookmark(
        self,
        db,
        user_id: str,
        content_id: str,
        content_type: ContentType,
        folder: str = "default",
        note: str = None
    ) -> Dict[str, Any]:
        """切换收藏状态（收藏/取消收藏）"""
        bookmark_repo = BookmarkRepository(db)

        # 检查是否已收藏
        existing_bookmark = await bookmark_repo.get_by_user_and_content(
            user_id, content_id, content_type
        )

        if existing_bookmark:
            # 取消收藏
            await bookmark_repo.delete(existing_bookmark.id)
            return {"bookmarked": False, "action": "unbookmarked"}
        else:
            # 创建收藏
            bookmark = DBBookmark(
                user_id=user_id,
                content_id=content_id,
                content_type=content_type,
                folder=folder,
                note=note,
            )
            await bookmark_repo.create(bookmark)
            return {"bookmarked": True, "action": "bookmarked"}

    async def get_bookmark_status(
        self,
        db,
        user_id: str,
        content_id: str,
        content_type: ContentType
    ) -> bool:
        """获取收藏状态"""
        bookmark_repo = BookmarkRepository(db)
        existing = await bookmark_repo.get_by_user_and_content(user_id, content_id, content_type)
        return existing is not None

    async def get_user_bookmarks(
        self,
        db,
        user_id: str,
        folder: Optional[str] = None,
        limit: int = 50
    ) -> List[DBBookmark]:
        """获取用户的收藏列表"""
        bookmark_repo = BookmarkRepository(db)
        return await bookmark_repo.list_by_user(user_id, folder, limit)

    async def get_user_folders(self, db, user_id: str) -> List[str]:
        """获取用户的所有收藏夹名称"""
        bookmark_repo = BookmarkRepository(db)
        return await bookmark_repo.list_folders(user_id)

    # ==================== 关注功能 ====================
    async def toggle_follow(
        self,
        db,
        follower_id: str,
        following_id: str
    ) -> Dict[str, Any]:
        """切换关注状态（关注/取消关注）"""
        follow_repo = FollowRepository(db)
        member_repo = MemberRepository(db)

        # 不能关注自己
        if follower_id == following_id:
            return {"error": "不能关注自己"}

        # 验证被关注用户存在
        following_user = await member_repo.get(following_id)
        if not following_user:
            return {"error": "用户不存在"}

        # 检查是否已关注
        existing = await follow_repo.get_follow_relationship(follower_id, following_id)

        if existing:
            # 取消关注
            await follow_repo.delete(existing.id)
            return {"following": False, "action": "unfollowed"}
        else:
            # 创建关注
            follow = DBFollow(
                follower_id=follower_id,
                following_id=following_id,
            )
            await follow_repo.create(follow)

            # 发送通知给被关注的用户
            await self._notify_new_follower(db, follower_id, following_id)

            return {"following": True, "action": "followed"}

    async def get_follow_status(
        self,
        db,
        follower_id: str,
        following_id: str
    ) -> bool:
        """获取关注状态"""
        follow_repo = FollowRepository(db)
        return await follow_repo.is_following(follower_id, following_id)

    async def get_following_list(
        self,
        db,
        user_id: str,
        limit: int = 100
    ) -> List[DBFollow]:
        """获取用户关注的列表"""
        follow_repo = FollowRepository(db)
        return await follow_repo.list_following(user_id, limit)

    async def get_followers_list(
        self,
        db,
        user_id: str,
        limit: int = 100
    ) -> List[DBFollow]:
        """获取用户的粉丝列表"""
        follow_repo = FollowRepository(db)
        return await follow_repo.list_followers(user_id, limit)

    async def get_follow_stats(
        self,
        db,
        user_id: str
    ) -> Dict[str, int]:
        """获取用户的关注统计"""
        follow_repo = FollowRepository(db)
        following_count = await follow_repo.count_following(user_id)
        followers_count = await follow_repo.count_followers(user_id)

        return {
            "following_count": following_count,
            "followers_count": followers_count
        }

    async def _notify_new_follower(
        self,
        db,
        follower_id: str,
        following_id: str
    ):
        """发送新粉丝通知"""
        notification_repo = NotificationRepository(db)
        member_repo = MemberRepository(db)

        follower = await member_repo.get(follower_id)
        follower_name = follower.name if follower else follower_id

        notification = DBNotification(
            recipient_id=following_id,
            sender_id=follower_id,
            notification_type="new_follower",
            title="新粉丝",
            content=f"{follower_name} 关注了你",
        )
        await notification_repo.create(notification)


# 全局服务实例
interaction_service = InteractionService()
