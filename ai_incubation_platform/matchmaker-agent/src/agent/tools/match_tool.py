"""
匹配计算工具

用于执行匹配算法计算，返回匹配结果列表。
"""
from typing import Dict, Any, List
from db.database import get_db
from db.repositories import UserRepository
from utils.logger import logger
from matching.matcher import matchmaker


class MatchTool:
    """
    匹配计算工具

    功能：
    - 执行匹配算法
    - 返回匹配结果列表
    - 支持筛选和排序
    """

    name = "match_compute"
    description = "执行匹配计算，返回匹配结果列表"
    tags = ["match", "compute", "algorithm"]

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
                "limit": {
                    "type": "integer",
                    "description": "返回匹配结果数量上限",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100
                },
                "min_score": {
                    "type": "number",
                    "description": "最低匹配度阈值",
                    "default": 0.0,
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["user_id"]
        }

    @staticmethod
    def handle(user_id: str, limit: int = 10, min_score: float = 0.0) -> dict:
        """
        处理匹配计算请求

        Args:
            user_id: 用户 ID
            limit: 返回结果数量上限
            min_score: 最低匹配度阈值

        Returns:
            匹配结果列表
        """
        logger.info(f"MatchTool: Computing matches for user {user_id}, limit={limit}, min_score={min_score}")

        try:
            # 确保用户已在匹配系统中注册
            if user_id not in matchmaker._users:
                db = next(get_db())
                user_repo = UserRepository(db)
                db_user = user_repo.get_by_id(user_id)
                if db_user:
                    from api.users import _from_db
                    matchmaker.register_user(_from_db(db_user).model_dump())
                    logger.info(f"MatchTool: User {user_id} registered to matching system")
                else:
                    return {"error": "User not found"}

            # 执行匹配计算
            matches = matchmaker.find_matches(user_id, limit=limit)

            # 过滤低于阈值的匹配
            filtered_matches = [m for m in matches if m["score"] >= min_score]

            logger.info(f"MatchTool: Found {len(filtered_matches)} matches for user {user_id}")

            return {
                "matches": filtered_matches,
                "total": len(filtered_matches),
                "has_more": len(matches) > len(filtered_matches)
            }

        except Exception as e:
            logger.error(f"MatchTool: Failed to compute matches: {e}")
            return {"error": str(e)}

    @staticmethod
    def handle_single_match(user_id: str, target_user_id: str) -> dict:
        """
        计算两个用户之间的匹配度

        Args:
            user_id: 用户 ID
            target_user_id: 目标用户 ID

        Returns:
            匹配度和详细分析
        """
        logger.info(f"MatchTool: Computing compatibility between {user_id} and {target_user_id}")

        try:
            db = next(get_db())
            user_repo = UserRepository(db)

            db_user = user_repo.get_by_id(user_id)
            db_target = user_repo.get_by_id(target_user_id)

            if not db_user or not db_target:
                return {"error": "User not found"}

            from api.users import _from_db
            user = _from_db(db_user)
            target = _from_db(db_target)

            score, breakdown = matchmaker._calculate_compatibility(
                user.model_dump(),
                target.model_dump()
            )

            common_interests = list(set(user.interests) & set(target.interests))

            logger.info(f"MatchTool: Compatibility score: {score:.3f}")

            return {
                "compatibility_score": score,
                "score_breakdown": breakdown,
                "common_interests": common_interests,
                "is_mutual": target_user_id in [m["user_id"] for m in matchmaker.find_matches(user_id, limit=100)]
            }

        except Exception as e:
            logger.error(f"MatchTool: Failed to compute compatibility: {e}")
            return {"error": str(e)}
