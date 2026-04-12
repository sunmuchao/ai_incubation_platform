"""
Who Likes Me 服务

参考 Tinder Gold 会员功能：
- 显示已经喜欢你的用户列表
- 会员可查看完整列表并直接匹配
- 非会员只能看到模糊预览（数量提示）
- 支持排序：按时间、按匹配度
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from utils.logger import logger
from db.models import SwipeActionDB as SwipeDB  # 使用 SwipeActionDB，别名 SwipeDB 保持兼容
from services.base_service import BaseService


class WhoLikesMeService(BaseService):
    """Who Likes Me 服务"""

    # 配置
    MAX_FREE_PREVIEW = 3  # 非会员最多预览数量（模糊）
    PREVIEW_BLUR_LEVEL = "medium"  # 预览模糊级别

    def __init__(self, db: Session):
        super().__init__(db)

    def get_likes_received(
        self,
        user_id: str,
        is_member: bool = False,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "time"  # time | compatibility
    ) -> Dict[str, Any]:
        """
        获取喜欢我的用户列表

        Args:
            user_id: 当前用户 ID
            is_member: 是否为会员
            limit: 返回数量限制
            offset: 偏移量
            sort_by: 排序方式（time=按时间, compatibility=按匹配度）

        Returns:
            {
                "total_count": 总数量,
                "has_more": 是否有更多,
                "is_member": 是否会员,
                "likes": [
                    {
                        "user_id": 喜欢者 ID,
                        "name": 名称（会员可见完整，非会员模糊）,
                        "avatar": 头像（会员可见，非会员模糊）,
                        "liked_at": 喜欢时间,
                        "compatibility_score": 匹配度（会员可见）,
                        "is_blurred": 是否模糊显示
                    }
                ]
            }
        """
        # 查询所有喜欢当前用户但未被处理的记录
        likes = self.db.query(SwipeDB).filter(
            SwipeDB.target_user_id == user_id,
            SwipeDB.action == "like",
            SwipeDB.is_matched == False  # 尚未匹配
        ).all()

        # 计算总数
        total_count = len(likes)

        # 按排序方式处理
        if sort_by == "time":
            # 按时间倒序
            likes_sorted = sorted(likes, key=lambda x: x.created_at, reverse=True)
        else:
            # 按匹配度排序（需要计算匹配度）
            likes_sorted = self._sort_by_compatibility(user_id, likes)

        # 分页
        paginated_likes = likes_sorted[offset:offset + limit]
        has_more = offset + limit < total_count

        # 构建返回数据
        result_likes = []
        for swipe in paginated_likes:
            like_data = self._build_like_data(swipe, user_id, is_member)
            result_likes.append(like_data)

        return {
            "total_count": total_count,
            "has_more": has_more,
            "is_member": is_member,
            "likes": result_likes,
            "free_preview_count": min(total_count, self.MAX_FREE_PREVIEW) if not is_member else total_count
        }

    def _sort_by_compatibility(self, user_id: str, likes: List[SwipeDB]) -> List[SwipeDB]:
        """按匹配度排序"""
        # 获取用户画像并计算匹配度
        from services.matching_service import MatchingService

        matching_service = MatchingService(self.db)
        likes_with_score = []

        for swipe in likes:
            try:
                score = matching_service.calculate_compatibility(user_id, swipe.user_id)
                likes_with_score.append((swipe, score))
            except Exception:
                # 无法计算匹配度时，使用默认值
                likes_with_score.append((swipe, 0))

        # 按匹配度降序排序
        likes_with_score.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in likes_with_score]

    def _build_like_data(
        self,
        swipe: SwipeDB,
        current_user_id: str,
        is_member: bool
    ) -> Dict[str, Any]:
        """构建单个喜欢数据"""
        from db.models import UserDB

        # 获取喜欢者信息
        liker = self.db.query(UserDB).filter(UserDB.id == swipe.user_id).first()

        if not liker:
            return {
                "user_id": swipe.user_id,
                "name": "用户",
                "avatar": None,
                "liked_at": swipe.created_at.isoformat(),
                "compatibility_score": 0,
                "is_blurred": True
            }

        # 计算匹配度（会员可见完整分数）
        compatibility_score = 0
        if is_member:
            try:
                from services.matching_service import MatchingService
                matching_service = MatchingService(self.db)
                compatibility_score = matching_service.calculate_compatibility(
                    current_user_id, swipe.user_id
                )
            except Exception:
                compatibility_score = 0

        # 非会员：模糊显示
        is_blurred = not is_member

        # 模糊处理名称
        name = liker.name if is_member else self._blur_name(liker.name)

        # 模糊处理头像
        avatar = liker.avatar_url if is_member else None

        return {
            "user_id": swipe.user_id,
            "name": name,
            "avatar": avatar,
            "avatar_blurred": liker.avatar_url if not is_member else None,  # 提供模糊头像 URL
            "liked_at": swipe.created_at.isoformat(),
            "compatibility_score": compatibility_score if is_member else None,
            "is_blurred": is_blurred,
            "blur_level": self.PREVIEW_BLUR_LEVEL if is_blurred else None
        }

    def _blur_name(self, name: str) -> str:
        """模糊处理名称"""
        if not name:
            return "用户"
        # 只显示第一个字，其余用 * 替代
        if len(name) <= 1:
            return name[0] + "*"
        return name[0] + "*" * (len(name) - 1)

    def get_likes_count(self, user_id: str) -> int:
        """
        获取喜欢我的用户数量（快速查询）

        用于在首页显示徽章数量
        """
        count = self.db.query(SwipeDB).filter(
            SwipeDB.target_user_id == user_id,
            SwipeDB.action == "like",
            SwipeDB.is_matched == False
        ).count()

        return count

    def like_back(
        self,
        user_id: str,
        target_user_id: str
    ) -> Dict[str, Any]:
        """
        回喜欢（喜欢喜欢我的人）

        会员功能：直接匹配
        """
        from services.matching_service import MatchingService

        # 检查对方是否确实喜欢了自己
        existing_like = self.db.query(SwipeDB).filter(
            SwipeDB.user_id == target_user_id,
            SwipeDB.target_user_id == user_id,
            SwipeDB.action == "like"
        ).first()

        if not existing_like:
            return {
                "success": False,
                "message": "对方未喜欢你",
                "matched": False
            }

        # 创建自己的喜欢记录
        my_swipe = SwipeDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            target_user_id=target_user_id,
            action="like",
            created_at=datetime.now()
        )
        self.db.add(my_swipe)

        # 检查是否匹配
        if existing_like.action == "like":
            # 双向喜欢，匹配成功
            my_swipe.is_matched = True
            existing_like.is_matched = True
            self.db.commit()

            # 创建匹配记录
            matching_service = MatchingService(self.db)
            match = matching_service.create_match(user_id, target_user_id)

            logger.info(f"Match created: {user_id} <-> {target_user_id} via like_back")

            return {
                "success": True,
                "message": "匹配成功！",
                "matched": True,
                "match_id": match.get("match_id") if match else None
            }

        self.db.commit()
        return {
            "success": True,
            "message": "已喜欢",
            "matched": False
        }

    def get_new_likes_count_since(
        self,
        user_id: str,
        since_time: datetime
    ) -> int:
        """
        获取指定时间以来的新喜欢数量

        用于推送通知
        """
        count = self.db.query(SwipeDB).filter(
            SwipeDB.target_user_id == user_id,
            SwipeDB.action == "like",
            SwipeDB.is_matched == False,
            SwipeDB.created_at > since_time
        ).count()

        return count


# 服务工厂函数
def get_who_likes_me_service(db: Session) -> WhoLikesMeService:
    """获取 Who Likes Me 服务实例"""
    return WhoLikesMeService(db)