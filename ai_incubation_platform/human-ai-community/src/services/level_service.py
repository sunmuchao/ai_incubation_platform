"""
用户等级系统服务
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, distinct
from datetime import datetime, timedelta
import logging
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.level_models import DBExperienceLog, ExperienceSourceType, DBLevelPrivilege
from db.models import DBCommunityMember
from models.member import MemberType

logger = logging.getLogger(__name__)


# 等级配置 - 1-18 级所需经验值
# 采用递增曲线：等级越高，升级所需经验越多
LEVEL_CONFIG = {
    1: 0,       # 1 级：0 经验
    2: 100,     # 2 级：100 经验
    3: 300,     # 3 级：300 经验
    4: 600,     # 4 级：600 经验
    5: 1000,    # 5 级：1000 经验
    6: 1500,    # 6 级：1500 经验
    7: 2200,    # 7 级：2200 经验
    8: 3000,    # 8 级：3000 经验
    9: 4000,    # 9 级：4000 经验
    10: 5200,   # 10 级：5200 经验
    11: 6600,   # 11 级：6600 经验
    12: 8200,   # 12 级：8200 经验
    13: 10000,  # 13 级：10000 经验
    14: 12000,  # 14 级：12000 经验
    15: 14500,  # 15 级：14500 经验
    16: 17500,  # 16 级：17500 经验
    17: 21000,  # 17 级：21000 经验
    18: 25000,  # 18 级：25000 经验
}

# 经验值获取规则
EXPERIENCE_RULES = {
    "post": 5,              # 发帖：+5 经验
    "comment": 2,           # 评论：+2 经验
    "like_received": 1,     # 被点赞：+1 经验/次
    "bookmark_received": 2, # 被收藏：+2 经验/次
    "daily_checkin": 5,     # 每日签到：+5 经验
    "quality_content": 50,  # 优质内容加精：+50 经验
    "first_post": 20,       # 首次发帖奖励：+20 经验
    "first_comment": 10,    # 首次评论奖励：+10 经验
}

# 每日经验获取上限
DAILY_LIMITS = {
    "post": 50,     # 发帖每日最多 50 经验（10 帖）
    "comment": 20,  # 评论每日最多 20 经验（10 条）
    "daily_checkin": 5,  # 签到每日最多 5 经验
}

# 等级特权配置
LEVEL_PRIVILEGES = {
    # 1-3 级：新用户，发帖频率受限
    1: {
        "title": "新手村民",
        "post_limit_per_hour": 1,
        "comment_limit_per_hour": 5,
        "can_use_custom_title": False,
        "can_edit_posts_within_minutes": 5,
        "badge_color": "#999999",
    },
    2: {
        "title": "新手村民",
        "post_limit_per_hour": 2,
        "comment_limit_per_hour": 10,
        "can_use_custom_title": False,
        "can_edit_posts_within_minutes": 10,
        "badge_color": "#999999",
    },
    3: {
        "title": "新手村民",
        "post_limit_per_hour": 3,
        "comment_limit_per_hour": 15,
        "can_use_custom_title": False,
        "can_edit_posts_within_minutes": 15,
        "badge_color": "#999999",
    },
    # 4-6 级：普通用户，基础权限
    4: {
        "title": "社区成员",
        "post_limit_per_hour": 5,
        "comment_limit_per_hour": 20,
        "can_use_custom_title": False,
        "can_edit_posts_within_minutes": 30,
        "badge_color": "#4CAF50",
    },
    5: {
        "title": "社区成员",
        "post_limit_per_hour": 5,
        "comment_limit_per_hour": 30,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 60,
        "badge_color": "#4CAF50",
    },
    6: {
        "title": "社区成员",
        "post_limit_per_hour": 5,
        "comment_limit_per_hour": 30,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 60,
        "badge_color": "#4CAF50",
    },
    # 7-12 级：活跃用户，自定义头衔
    7: {
        "title": "活跃成员",
        "post_limit_per_hour": 10,
        "comment_limit_per_hour": 50,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 120,
        "badge_color": "#2196F3",
    },
    8: {
        "title": "活跃成员",
        "post_limit_per_hour": 10,
        "comment_limit_per_hour": 50,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 120,
        "badge_color": "#2196F3",
    },
    9: {
        "title": "活跃成员",
        "post_limit_per_hour": 10,
        "comment_limit_per_hour": 50,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 120,
        "badge_color": "#2196F3",
    },
    10: {
        "title": "活跃达人",
        "post_limit_per_hour": 15,
        "comment_limit_per_hour": 60,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 180,
        "badge_color": "#2196F3",
    },
    11: {
        "title": "活跃达人",
        "post_limit_per_hour": 15,
        "comment_limit_per_hour": 60,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 180,
        "badge_color": "#2196F3",
    },
    12: {
        "title": "活跃达人",
        "post_limit_per_hour": 15,
        "comment_limit_per_hour": 60,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 180,
        "badge_color": "#2196F3",
    },
    # 13-18 级：资深用户，专属标识、优先审核
    13: {
        "title": "社区元老",
        "post_limit_per_hour": 20,
        "comment_limit_per_hour": 80,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 240,
        "badge_color": "#FF9800",
        "priority_review": True,
    },
    14: {
        "title": "社区元老",
        "post_limit_per_hour": 20,
        "comment_limit_per_hour": 80,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 240,
        "badge_color": "#FF9800",
        "priority_review": True,
    },
    15: {
        "title": "社区元老",
        "post_limit_per_hour": 20,
        "comment_limit_per_hour": 80,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 240,
        "badge_color": "#FF9800",
        "priority_review": True,
    },
    16: {
        "title": "传奇人物",
        "post_limit_per_hour": 30,
        "comment_limit_per_hour": 100,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 360,
        "badge_color": "#9C27B0",
        "priority_review": True,
        "can_create_channels": True,
    },
    17: {
        "title": "传奇人物",
        "post_limit_per_hour": 30,
        "comment_limit_per_hour": 100,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 360,
        "badge_color": "#9C27B0",
        "priority_review": True,
        "can_create_channels": True,
    },
    18: {
        "title": "传说人物",
        "post_limit_per_hour": 50,
        "comment_limit_per_hour": 200,
        "can_use_custom_title": True,
        "can_edit_posts_within_minutes": 1440,
        "badge_color": "#E91E63",
        "priority_review": True,
        "can_create_channels": True,
        "can_moderate_content": True,
    },
}


class LevelService:
    """用户等级服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.db = db

    async def get_user_level(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户等级信息

        Returns:
            {
                "user_id": str,
                "level": int,
                "experience": int,
                "next_level": int,
                "experience_to_next_level": int,
                "progress_percent": float,
                "title": str,
                "badge_color": str,
            }
        """
        result = await self.db.execute(
            select(DBCommunityMember).where(DBCommunityMember.id == user_id)
        )
        member = result.scalar_one_or_none()

        if not member:
            return None

        current_level = member.level
        current_exp = member.experience_points

        # 计算下一级所需经验
        next_level = min(current_level + 1, 18)
        exp_for_next = LEVEL_CONFIG.get(next_level, LEVEL_CONFIG[18])
        exp_for_current = LEVEL_CONFIG.get(current_level, 0)

        # 计算进度百分比
        level_exp_range = exp_for_next - exp_for_current
        if level_exp_range > 0:
            progress_percent = ((current_exp - exp_for_current) / level_exp_range) * 100
        else:
            progress_percent = 100.0

        # 获取等级特权
        privileges = LEVEL_PRIVILEGES.get(current_level, LEVEL_PRIVILEGES[1])

        return {
            "user_id": user_id,
            "level": current_level,
            "experience": current_exp,
            "next_level": next_level if current_level < 18 else None,
            "experience_to_next_level": exp_for_next - current_exp if current_level < 18 else 0,
            "progress_percent": round(progress_percent, 2),
            "title": privileges.get("title", "社区成员"),
            "badge_color": privileges.get("badge_color", "#4CAF50"),
        }

    async def add_experience(
        self,
        user_id: str,
        source_type: ExperienceSourceType,
        points: int,
        description: str = None,
        related_content_id: str = None
    ) -> Dict[str, Any]:
        """
        添加经验值

        Args:
            user_id: 用户 ID
            source_type: 经验来源类型
            points: 经验值
            description: 描述
            related_content_id: 关联内容 ID

        Returns:
            {
                "added_points": int,  # 实际添加的经验值
                "total_experience": int,  # 总经验值
                "old_level": int,  # 原等级
                "new_level": int,  # 新等级
                "leveled_up": bool,  # 是否升级
            }
        """
        # 获取用户
        result = await self.db.execute(
            select(DBCommunityMember).where(DBCommunityMember.id == user_id)
        )
        member = result.scalar_one_or_none()

        if not member:
            raise ValueError(f"User {user_id} not found")

        old_level = member.level
        old_exp = member.experience_points

        # 检查每日上限
        today = datetime.now().date()
        if source_type.value in DAILY_LIMITS:
            daily_limit = DAILY_LIMITS[source_type.value]
            # 计算今日已获取的经验
            start_of_day = datetime.combine(today, datetime.min.time())
            result = await self.db.execute(
                select(func.sum(DBExperienceLog.points)).where(
                    DBExperienceLog.user_id == user_id,
                    DBExperienceLog.source_type == source_type,
                    DBExperienceLog.created_at >= start_of_day
                )
            )
            today_exp = result.scalar() or 0

            if today_exp >= daily_limit:
                # 今日已达到上限
                return {
                    "added_points": 0,
                    "total_experience": old_exp,
                    "old_level": old_level,
                    "new_level": old_level,
                    "leveled_up": False,
                    "daily_limit_reached": True,
                }

            # 调整添加的经验值
            remaining = daily_limit - today_exp
            if points > remaining:
                points = remaining

        # 创建经验流水记录
        log = DBExperienceLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            source_type=source_type,
            points=points,
            description=description or f"获得 {points} 经验",
            related_content_id=related_content_id,
        )
        self.db.add(log)

        # 更新用户经验值
        member.experience_points = old_exp + points

        # 检查是否需要升级
        new_level = self._calculate_level(member.experience_points)
        leveled_up = new_level > old_level

        if leveled_up:
            member.level = new_level
            logger.info(f"用户 {user_id} 从 {old_level} 级升级到 {new_level} 级")

        await self.db.commit()

        return {
            "added_points": points,
            "total_experience": member.experience_points,
            "old_level": old_level,
            "new_level": new_level,
            "leveled_up": leveled_up,
        }

    def _calculate_level(self, experience: int) -> int:
        """根据经验值计算等级"""
        for level in range(18, 0, -1):
            if experience >= LEVEL_CONFIG[level]:
                return level
        return 1

    async def get_experience_history(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取用户经验获取历史"""
        start_date = datetime.now() - timedelta(days=days)

        result = await self.db.execute(
            select(DBExperienceLog)
            .where(
                DBExperienceLog.user_id == user_id,
                DBExperienceLog.created_at >= start_date
            )
            .order_by(desc(DBExperienceLog.created_at))
            .limit(limit)
        )

        logs = result.scalars().all()
        return [
            {
                "id": log.id,
                "source_type": log.source_type.value,
                "points": log.points,
                "description": log.description,
                "related_content_id": log.related_content_id,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]

    async def get_leaderboard(
        self,
        limit: int = 50,
        level_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取等级排行榜

        Args:
            limit: 返回数量
            level_filter: 等级筛选（返回指定等级以上的用户）
        """
        query = select(DBCommunityMember).order_by(
            desc(DBCommunityMember.experience_points),
            desc(DBCommunityMember.level)
        )

        if level_filter:
            query = query.where(DBCommunityMember.level >= level_filter)

        query = query.limit(limit)
        result = await self.db.execute(query)
        members = result.scalars().all()

        return [
            {
                "user_id": m.id,
                "name": m.name,
                "member_type": m.member_type.value,
                "level": m.level,
                "experience": m.experience_points,
                "title": LEVEL_PRIVILEGES.get(m.level, {}).get("title", "社区成员"),
            }
            for m in members
        ]

    async def daily_checkin(self, user_id: str) -> Dict[str, Any]:
        """
        每日签到

        Returns:
            {
                "success": bool,
                "message": str,
                "points": int,
                "streak_days": int,  # 连续签到天数
            }
        """
        result = await self.db.execute(
            select(DBCommunityMember).where(DBCommunityMember.id == user_id)
        )
        member = result.scalar_one_or_none()

        if not member:
            raise ValueError(f"User {user_id} not found")

        # 检查今日是否已签到
        today = datetime.now().date()
        if member.last_checkin_date:
            last_checkin = member.last_checkin_date.date()
            if last_checkin == today:
                return {
                    "success": False,
                    "message": "今日已签到",
                    "points": 0,
                    "already_checked_in": True,
                }

        # 添加签到经验
        points = EXPERIENCE_RULES["daily_checkin"]
        result = await self.add_experience(
            user_id=user_id,
            source_type=ExperienceSourceType.DAILY_CHECKIN,
            points=points,
            description="每日签到"
        )

        # 更新最后签到时间
        member.last_checkin_date = datetime.now()
        await self.db.commit()

        # 计算连续签到天数（简化实现）
        streak_days = 1  # TODO: 实现连续签到计算

        return {
            "success": True,
            "message": f"签到成功，获得 {points} 经验",
            "points": points,
            "streak_days": streak_days,
            "total_experience": result["total_experience"],
            "leveled_up": result["leveled_up"],
        }

    async def get_level_privileges(self, level: int) -> Dict[str, Any]:
        """获取指定等级的特权配置"""
        return LEVEL_PRIVILEGES.get(level, LEVEL_PRIVILEGES[1])

    async def get_all_levels(self) -> List[Dict[str, Any]]:
        """获取所有等级信息"""
        levels = []
        for level in range(1, 19):
            exp_required = LEVEL_CONFIG[level]
            privileges = LEVEL_PRIVILEGES.get(level, {})
            levels.append({
                "level": level,
                "experience_required": exp_required,
                "title": privileges.get("title", "社区成员"),
                "badge_color": privileges.get("badge_color", "#4CAF50"),
                "privileges": privileges,
            })
        return levels

    async def check_user_privilege(
        self,
        user_id: str,
        privilege_type: str
    ) -> bool:
        """
        检查用户是否拥有指定特权

        Args:
            user_id: 用户 ID
            privilege_type: 特权类型（如 can_use_custom_title）

        Returns:
            bool: 是否拥有该特权
        """
        level_info = await self.get_user_level(user_id)
        if not level_info:
            return False

        privileges = LEVEL_PRIVILEGES.get(level_info["level"], {})
        return privileges.get(privilege_type, False)


# 全局服务实例
_level_service = None


def get_level_service(db: AsyncSession) -> LevelService:
    """获取等级服务实例"""
    global _level_service
    if _level_service is None or _level_service.db is not db:
        _level_service = LevelService(db)
    return _level_service
