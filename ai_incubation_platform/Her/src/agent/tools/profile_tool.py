"""
画像读取工具

用于读取用户完整画像，包括基本信息、兴趣价值观、偏好设置等。
"""
from typing import Dict, Any, Optional
from db.database import get_db
from db.repositories import UserRepository
from utils.logger import logger
from matching.matcher import matchmaker


class ProfileTool:
    """
    画像读取工具

    功能：
    - 读取用户基本信息
    - 读取用户兴趣价值观
    - 读取用户偏好设置
    - 生成用户画像摘要
    """

    name = "profile_read"
    description = "读取用户完整画像信息"
    tags = ["profile", "user", "read"]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "include_sensitive": {
                    "type": "boolean",
                    "description": "是否包含敏感信息（默认 false）",
                    "default": False
                }
            },
            "required": ["user_id"]
        }

    @staticmethod
    def handle(user_id: str, include_sensitive: bool = False) -> dict:
        """
        处理画像读取请求

        Args:
            user_id: 用户 ID
            include_sensitive: 是否包含敏感信息

        Returns:
            用户画像信息
        """
        logger.info(f"ProfileTool: Reading profile for user {user_id}")

        try:
            db = next(get_db())
            user_repo = UserRepository(db)

            # 从数据库读取用户
            db_user = user_repo.get_by_id(user_id)
            if not db_user:
                # 尝试从匹配系统内存中读取
                memory_user = matchmaker._users.get(user_id)
                if memory_user:
                    logger.info(f"ProfileTool: User found in memory: {user_id}")
                    return {
                        "source": "memory",
                        "profile": memory_user
                    }
                logger.warning(f"ProfileTool: User not found: {user_id}")
                return {"error": "User not found"}

            # 转换为 Pydantic 模型
            import json
            interests = []
            if db_user.interests:
                try:
                    interests = json.loads(db_user.interests)
                except json.JSONDecodeError:
                    interests = db_user.interests.split(",") if db_user.interests else []

            values = {}
            if db_user.values:
                try:
                    values = json.loads(db_user.values)
                except json.JSONDecodeError:
                    pass

            # 构建画像
            profile = {
                "id": db_user.id,
                "name": db_user.name,
                "email": db_user.email if include_sensitive else "***@***.***",
                "age": db_user.age,
                "gender": db_user.gender,
                "location": db_user.location,
                "bio": db_user.bio,
                "avatar_url": db_user.avatar_url,
                "interests": interests,
                "values": values,
                "preferred_age_min": db_user.preferred_age_min,
                "preferred_age_max": db_user.preferred_age_max,
                "preferred_gender": db_user.preferred_gender,
                "goal": getattr(db_user, 'goal', 'serious')
            }

            # 生成画像摘要
            summary = ProfileTool._generate_summary(profile)

            logger.info(f"ProfileTool: Profile read successfully for user {user_id}")

            return {
                "source": "database",
                "profile": profile,
                "summary": summary
            }

        except Exception as e:
            logger.error(f"ProfileTool: Failed to read profile: {e}")
            return {"error": str(e)}

    @staticmethod
    def _generate_summary(profile: dict) -> str:
        """
        生成用户画像摘要

        Args:
            profile: 用户画像数据

        Returns:
            摘要字符串
        """
        parts = []

        # 基本信息
        parts.append(f"{profile.get('name', '用户')}，{profile.get('age', '?')}岁，{profile.get('gender', '未知')}")

        # 地点
        location = profile.get('location', '')
        if location:
            parts.append(f"位于{location}")

        # 兴趣
        interests = profile.get('interests', [])
        if interests:
            parts.append(f"兴趣：{', '.join(interests[:3])}{'等' if len(interests) > 3 else ''}")

        # 关系目标
        goal = profile.get('goal', 'serious')
        goal_map = {
            'serious': '认真恋爱',
            'marriage': '以结婚为目的',
            'casual': '轻松交往',
            'friendship': '交朋友'
        }
        parts.append(f"期望：{goal_map.get(goal, goal)}")

        return "，".join(parts) + "。"
