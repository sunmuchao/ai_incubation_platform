"""
兴趣社交工具 - 参考 Soul 的灵魂匹配机制

提供兴趣导向的社交功能：
- 兴趣标签云
- 灵魂匹配 (基于兴趣/价值观)
- 兴趣社区推荐
- 话题匹配
"""
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter  # @deprecated: Counter unused, will be removed
from dataclasses import dataclass
import math
from utils.logger import logger
from db.database import get_db
from db.repositories import UserRepository


@dataclass
class InterestMatch:
    """兴趣匹配结果"""
    user_id: str
    matched_user_id: str
    common_interests: List[str]
    interest_score: float
    unique_interests_user: List[str]  # 用户独有的兴趣
    unique_interests_match: List[str]  # 对方独有的兴趣
    conversation_topics: List[str]  # 推荐对话话题


@dataclass
class CommunityRecommendation:
    """社区推荐"""
    community_id: str
    community_name: str
    interest_tag: str
    member_count: int
    activity_level: str  # high, medium, low
    reason: str  # 推荐理由


class InterestService:
    """
    兴趣服务 - 参考 Soul 的兴趣社交机制

    功能：
    - 兴趣标签分析
    - 兴趣匹配算法
    - 社区推荐
    - 话题生成
    """

    # 预定义兴趣分类
    INTEREST_CATEGORIES = {
        "旅行": "lifestyle",
        "摄影": "art",
        "音乐": "entertainment",
        "电影": "entertainment",
        "阅读": "knowledge",
        "健身": "sports",
        "美食": "lifestyle",
        "绘画": "art",
        "游泳": "sports",
        "跑步": "sports",
        "瑜伽": "sports",
        "游戏": "entertainment",
        "咖啡": "lifestyle",
        "品酒": "lifestyle",
        "烘焙": "lifestyle",
        "登山": "sports",
        "滑雪": "sports",
        "冲浪": "sports",
        "编程": "knowledge",
        "科技": "knowledge",
        "历史": "knowledge",
        "心理学": "knowledge",
        "宠物": "lifestyle",
        "植物": "lifestyle",
        "手工艺": "art",
        "舞蹈": "art",
        "唱歌": "entertainment",
        "看剧": "entertainment",
        "动漫": "entertainment",
    }

    # 兴趣兼容性矩阵 (某些兴趣组合更匹配)
    INTEREST_COMPATIBILITY = {
        ("旅行", "摄影"): 1.2,
        ("音乐", "电影"): 1.1,
        ("健身", "跑步"): 1.15,
        ("美食", "烘焙"): 1.1,
        ("阅读", "心理学"): 1.1,
        ("编程", "科技"): 1.2,
        ("宠物", "植物"): 1.05,
    }

    # 热门兴趣社区
    COMMUNITIES = [
        {"id": "comm_travel", "name": "旅行达人", "interest": "旅行", "activity": "high"},
        {"id": "comm_foodie", "name": "美食探索", "interest": "美食", "activity": "high"},
        {"id": "comm_book", "name": "读书会", "interest": "阅读", "activity": "medium"},
        {"id": "comm_fitness", "name": "健身打卡", "interest": "健身", "activity": "high"},
        {"id": "comm_movie", "name": "影迷俱乐部", "interest": "电影", "activity": "medium"},
        {"id": "comm_music", "name": "音乐分享", "interest": "音乐", "activity": "medium"},
        {"id": "comm_photo", "name": "摄影交流", "interest": "摄影", "activity": "medium"},
        {"id": "comm_pet", "name": "宠物爱好者", "interest": "宠物", "activity": "high"},
        {"id": "comm_tech", "name": "科技前沿", "interest": "科技", "activity": "medium"},
        {"id": "comm_art", "name": "艺术创作", "interest": "绘画", "activity": "low"},
    ]

    # 话题库
    CONVERSATION_TOPICS = {
        "旅行": ["最近去过哪里旅行？", "有什么推荐的旅行目的地？", "喜欢什么类型的旅行？"],
        "美食": ["最喜欢什么菜系？", "有什么推荐的餐厅？", "会自己做饭吗？"],
        "音乐": ["最近在听什么歌？", "喜欢什么类型的音乐？", "有去过演唱会吗？"],
        "电影": ["最近看了什么好电影？", "最喜欢什么类型的电影？", "有喜欢的演员吗？"],
        "阅读": ["最近在读什么书？", "最喜欢什么类型的书？", "有推荐的作者吗？"],
        "健身": ["平时做什么运动？", "有去健身房吗？", "健身多久了？"],
        "摄影": ["喜欢拍什么题材？", "用什么设备？", "有特别喜欢的作品吗？"],
        "宠物": ["养了什么宠物？", "宠物叫什么名字？", "有什么有趣的故事？"],
    }

    @staticmethod
    def get_interest_category(interest: str) -> str:
        """获取兴趣所属分类"""
        return InterestService.INTEREST_CATEGORIES.get(interest, "other")

    @staticmethod
    def calculate_interest_similarity(
        user_interests: List[str],
        target_interests: List[str]
    ) -> Tuple[float, List[str]]:
        """
        计算兴趣相似度

        使用 Jaccard 相似度 + 兴趣兼容性加权

        Args:
            user_interests: 用户兴趣列表
            target_interests: 目标用户兴趣列表

        Returns:
            (相似度分数 0-1, 共同兴趣列表)
        """
        user_set = set(user_interests)
        target_set = set(target_interests)

        if not user_set and not target_set:
            return 0.5, []

        # 计算 Jaccard 相似度
        intersection = user_set & target_set
        union = user_set | target_set

        if not union:
            return 0.5, []

        base_similarity = len(intersection) / len(union)

        # 兴趣兼容性加权
        compatibility_bonus = 1.0
        for interest_pair, bonus in InterestService.INTEREST_COMPATIBILITY.items():
            if interest_pair[0] in user_set and interest_pair[1] in target_set:
                compatibility_bonus += (bonus - 1.0) * 0.1
            if interest_pair[1] in user_set and interest_pair[0] in target_set:
                compatibility_bonus += (bonus - 1.0) * 0.1

        final_similarity = min(1.0, base_similarity * compatibility_bonus)
        return round(final_similarity, 3), list(intersection)

    @staticmethod
    def generate_conversation_topics(common_interests: List[str]) -> List[str]:
        """基于共同兴趣生成对话话题"""
        topics = []
        for interest in common_interests[:3]:  # 最多取 3 个共同兴趣
            if interest in InterestService.CONVERSATION_TOPICS:
                available_topics = InterestService.CONVERSATION_TOPICS[interest]
                topics.append(available_topics[0])  # 每个兴趣取一个话题

        # 如果话题不足，补充通用话题
        general_topics = [
            "最近有什么新鲜事分享吗？",
            "周末一般都喜欢做什么？",
            "有什么特别想尝试的事情？"
        ]
        while len(topics) < 3:
            import random
            topics.append(random.choice(general_topics))

        return topics

    @staticmethod
    def recommend_communities(user_interests: List[str], limit: int = 5) -> List[CommunityRecommendation]:
        """
        推荐兴趣社区

        Args:
            user_interests: 用户兴趣列表
            limit: 推荐数量

        Returns:
            社区推荐列表
        """
        scored_communities = []

        for comm in InterestService.COMMUNITIES:
            # 计算匹配度
            match_score = 0
            reason = ""

            if comm["interest"] in user_interests:
                match_score = 0.9
                reason = f"基于你的兴趣：{comm['interest']}"
            else:
                # 检查是否有相关兴趣
                comm_category = InterestService.get_interest_category(comm["interest"])
                for interest in user_interests:
                    if InterestService.get_interest_category(interest) == comm_category:
                        match_score = 0.6
                        reason = f"与你喜欢的 {interest} 相关"
                        break

            if match_score > 0:
                # 活跃度加分
                if comm["activity"] == "high":
                    match_score += 0.1
                elif comm["activity"] == "medium":
                    match_score += 0.05

                scored_communities.append({
                    "community": comm,
                    "score": match_score,
                    "reason": reason
                })

        # 按分数排序
        scored_communities.sort(key=lambda x: x["score"], reverse=True)

        # 返回推荐
        recommendations = []
        for item in scored_communities[:limit]:
            comm = item["community"]
            recommendations.append(CommunityRecommendation(
                community_id=comm["id"],
                community_name=comm["name"],
                interest_tag=comm["interest"],
                member_count=1000 + hash(comm["id"]) % 9000,  # 模拟数据
                activity_level=comm["activity"],
                reason=item["reason"]
            ))

        return recommendations


class InterestTool:
    """
    兴趣工具 - Agent 工具封装

    功能：
    - 兴趣匹配
    - 社区推荐
    - 话题生成
    - 兴趣标签分析
    """

    name = "interest_tool"
    description = "兴趣社交工具 (参考 Soul 的灵魂匹配机制)"
    tags = ["interest", "community", "soul_match", "topics"]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["match_by_interest", "get_communities", "get_topics", "analyze_tags"]
                },
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "target_user_id": {
                    "type": "string",
                    "description": "目标用户 ID (用于匹配)"
                },
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "兴趣列表 (用于分析)"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量上限",
                    "default": 5
                }
            },
            "required": ["action"]
        }

    @staticmethod
    def handle(action: str, **kwargs) -> dict:
        """处理兴趣相关请求"""
        logger.info(f"InterestTool: Executing action={action}")

        try:
            if action == "match_by_interest":
                return InterestTool._handle_interest_match(kwargs)
            elif action == "get_communities":
                return InterestTool._handle_community_recommend(kwargs)
            elif action == "get_topics":
                return InterestTool._handle_topic_generation(kwargs)
            elif action == "analyze_tags":
                return InterestTool._handle_tag_analysis(kwargs)
            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"InterestTool: Failed to execute action {action}: {e}")
            return {"error": str(e)}

    @staticmethod
    def _handle_interest_match(params: dict) -> dict:
        """处理兴趣匹配"""
        user_id = params.get("user_id")
        target_user_id = params.get("target_user_id")

        if not user_id or not target_user_id:
            return {"error": "user_id and target_user_id are required"}

        db = next(get_db())
        user_repo = UserRepository(db)

        db_user = user_repo.get_by_id(user_id)
        db_target = user_repo.get_by_id(target_user_id)

        if not db_user or not db_target:
            return {"error": "User not found"}

        from api.users import _from_db
        user = _from_db(db_user)
        target = _from_db(db_target)

        # 计算兴趣相似度
        similarity, common_interests = InterestService.calculate_interest_similarity(
            user.interests,
            target.interests
        )

        # 生成对话话题
        topics = InterestService.generate_conversation_topics(common_interests)

        # 计算独有兴趣
        user_unique = list(set(user.interests) - set(target.interests))
        target_unique = list(set(target.interests) - set(user.interests))

        result = {
            "user_id": user_id,
            "matched_user_id": target_user_id,
            "common_interests": common_interests,
            "interest_score": similarity,
            "unique_interests_user": user_unique[:5],
            "unique_interests_match": target_unique[:5],
            "conversation_topics": topics,
            "match_level": InterestTool._get_match_level(similarity)
        }

        logger.info(f"InterestTool: Interest match score={similarity}, common={len(common_interests)}")
        return result

    @staticmethod
    def _handle_community_recommend(params: dict) -> dict:
        """处理社区推荐"""
        user_id = params.get("user_id")
        limit = params.get("limit", 5)

        if user_id:
            db = next(get_db())
            user_repo = UserRepository(db)
            db_user = user_repo.get_by_id(user_id)

            if not db_user:
                return {"error": "User not found"}

            from api.users import _from_db
            user = _from_db(db_user)
            user_interests = user.interests
        else:
            # 如果没有用户 ID，使用传入的兴趣列表
            user_interests = params.get("interests", [])

        communities = InterestService.recommend_communities(user_interests, limit)

        return {
            "communities": [
                {
                    "id": c.community_id,
                    "name": c.community_name,
                    "interest": c.interest_tag,
                    "member_count": c.member_count,
                    "activity": c.activity_level,
                    "reason": c.reason
                }
                for c in communities
            ],
            "total": len(communities)
        }

    @staticmethod
    def _handle_topic_generation(params: dict) -> dict:
        """处理话题生成"""
        common_interests = params.get("common_interests", [])

        if not common_interests:
            # 尝试从用户获取
            user_id = params.get("user_id")
            target_user_id = params.get("target_user_id")

            if user_id and target_user_id:
                db = next(get_db())
                user_repo = UserRepository(db)

                db_user = user_repo.get_by_id(user_id)
                db_target = user_repo.get_by_id(target_user_id)

                if db_user and db_target:
                    from api.users import _from_db
                    user = _from_db(db_user)
                    target = _from_db(db_target)

                    _, common_interests = InterestService.calculate_interest_similarity(
                        user.interests,
                        target.interests
                    )

        topics = InterestService.generate_conversation_topics(common_interests)

        return {
            "topics": topics,
            "common_interests": common_interests,
            "topic_count": len(topics)
        }

    @staticmethod
    def _handle_tag_analysis(params: dict) -> dict:
        """处理标签分析"""
        interests = params.get("interests", [])

        if not interests:
            user_id = params.get("user_id")
            if user_id:
                db = next(get_db())
                user_repo = UserRepository(db)
                db_user = user_repo.get_by_id(user_id)

                if db_user:
                    from api.users import _from_db
                    user = _from_db(db_user)
                    interests = user.interests

        # 分析兴趣分类
        category_counts = defaultdict(int)
        for interest in interests:
            category = InterestService.get_interest_category(interest)
            category_counts[category] += 1

        # 生成用户画像标签
        profile_tags = []
        if category_counts.get("knowledge", 0) >= 2:
            profile_tags.append("知识型")
        if category_counts.get("art", 0) >= 2:
            profile_tags.append("文艺范")
        if category_counts.get("sports", 0) >= 2:
            profile_tags.append("运动达人")
        if category_counts.get("entertainment", 0) >= 2:
            profile_tags.append("娱乐达人")
        if category_counts.get("lifestyle", 0) >= 3:
            profile_tags.append("生活家")

        # 计算兴趣多样性
        diversity = len(category_counts) / max(len(interests), 1)

        return {
            "interests": interests,
            "category_distribution": dict(category_counts),
            "profile_tags": profile_tags,
            "diversity_score": round(diversity, 3),
            "dominant_category": max(category_counts, key=category_counts.get) if category_counts else None
        }

    @staticmethod
    def _get_match_level(score: float) -> str:
        """获取匹配等级"""
        if score >= 0.8:
            return "灵魂伴侣"
        elif score >= 0.6:
            return "高度匹配"
        elif score >= 0.4:
            return "有一定默契"
        else:
            return "需要更多了解"
