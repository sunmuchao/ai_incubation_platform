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

        统一使用 matchmaker.find_matches() 进行匹配，确保 REST API 和 Skill 路径逻辑一致。

        Args:
            user_id: 用户 ID
            limit: 返回结果数量上限
            min_score: 最低匹配度阈值

        Returns:
            匹配结果列表
        """
        logger.info(f"MatchTool: Computing matches for user {user_id}, limit={limit}, min_score={min_score}")

        try:
            db = next(get_db())
            user_repo = UserRepository(db)

            # 检查用户是否存在于数据库
            db_user = user_repo.get_by_id(user_id)
            user_exists = db_user is not None

            # ===== 统一：先加载所有活跃用户到匹配系统 =====
            all_users = user_repo.list_all(is_active=True)
            loaded_count = 0
            for db_user_item in all_users:
                if db_user_item.id not in matchmaker._users:
                    from api.users import _from_db
                    matchmaker.register_user(_from_db(db_user_item).model_dump())
                    loaded_count += 1
            if loaded_count > 0:
                logger.info(f"MatchTool: Loaded {loaded_count} active users to matching system")

            # ===== 统一：确保当前用户已在匹配系统中注册 =====
            if user_id not in matchmaker._users:
                if user_exists:
                    # 已注册用户：从数据库加载
                    from api.users import _from_db
                    matchmaker.register_user(_from_db(db_user).model_dump())
                    logger.info(f"MatchTool: User {user_id} registered to matching system")
                else:
                    # 匿名用户：构造虚拟用户并注册到 matchmaker
                    # 这样匿名用户也能走统一的匹配逻辑
                    anonymous_user = {
                        "id": user_id,
                        "gender": 'male',
                        "sexual_orientation": 'heterosexual',
                        "age": 25,
                        "preferred_age_min": 20,
                        "preferred_age_max": 40,
                        "location": "",
                        "preferred_locations": None,
                        "goal": "serious",
                        "interests": [],
                        "values": {}
                    }
                    matchmaker.register_user(anonymous_user)
                    logger.info(f"MatchTool: Anonymous user {user_id} registered to matching system")

            # ===== 统一：调用 matchmaker.find_matches() =====
            matches = matchmaker.find_matches(user_id, limit=limit)

            # 过滤低于阈值的匹配
            filtered_matches = [m for m in matches if m["score"] >= min_score]

            # 为每个 match 补充用户详情（解决 matchmaker.find_matches() 只返回 user_id 的问题）
            enriched_matches = []
            for match in filtered_matches:
                target_user_id = match.get("user_id")
                if not target_user_id:
                    continue
                db_target = user_repo.get_by_id(target_user_id)
                if db_target:
                    from api.users import _from_db
                    user_dict = _from_db(db_target).model_dump()
                    match["user"] = user_dict
                    enriched_matches.append(match)

            logger.info(f"MatchTool: Found {len(enriched_matches)} matches for user {user_id} (anonymous={not user_exists})")

            # 输出结果性别分布（调试用）
            male_matches = sum(1 for c in enriched_matches if c.get('user', {}).get('gender') == 'male')
            female_matches = sum(1 for c in enriched_matches if c.get('user', {}).get('gender') == 'female')
            logger.info(f"MatchTool: Match gender distribution: male={male_matches}, female={female_matches}")

            return {
                "matches": enriched_matches,
                "total": len(enriched_matches),
                "has_more": len(matches) > len(enriched_matches)
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
