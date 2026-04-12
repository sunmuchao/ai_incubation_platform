"""
共同活动推荐服务

推荐用户可以一起做的活动：
- 基于双方兴趣分析
- 考虑地理位置
- 考虑时间预算
- 考虑关系阶段
- AI 生成个性化推荐
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from utils.logger import logger
from services.base_service import BaseService


class JointActivityService(BaseService):
    """共同活动推荐服务"""

    # 活动类型配置
    ACTIVITY_TYPES = [
        {
            "type": "outdoor",
            "name": "户外活动",
            "activities": ["徒步", "骑行", "爬山", "露营", "野餐", "公园散步"],
            "duration_range": "1-6小时",
            "cost_range": "免费-中等"
        },
        {
            "type": "entertainment",
            "name": "娱乐休闲",
            "activities": ["看电影", "音乐会", "演唱会", "展览", "博物馆", "主题乐园"],
            "duration_range": "2-4小时",
            "cost_range": "中等"
        },
        {
            "type": "food",
            "name": "美食体验",
            "activities": ["餐厅用餐", "咖啡厅", "茶馆", "酒吧", "烹饪课", "美食探店"],
            "duration_range": "1-3小时",
            "cost_range": "中等-高"
        },
        {
            "type": "culture",
            "name": "文化艺术",
            "activities": ["书店", "画廊", "手工艺", "陶艺课", "画展", "话剧"],
            "duration_range": "2-4小时",
            "cost_range": "免费-中等"
        },
        {
            "type": "sports",
            "name": "运动健身",
            "activities": ["健身房", "瑜伽", "游泳", "羽毛球", "网球", "攀岩"],
            "duration_range": "1-2小时",
            "cost_range": "低-中等"
        },
        {
            "type": "relax",
            "name": "放松休闲",
            "activities": ["SPA", "按摩", "温泉", "图书馆", "书店", "咖啡馆"],
            "duration_range": "2-4小时",
            "cost_range": "中等-高"
        }
    ]

    def __init__(self, db: Session):
        super().__init__(db)
        self.db = db

    async def generate_activity_recommendations(
        self,
        user_profile: Dict[str, Any],
        partner_profile: Dict[str, Any],
        location: str,
        time_budget: str = "half_day",  # quick/half_day/full_day
        relationship_stage: str = "dating",
        budget_preference: str = "medium"  # free/low/medium/high
    ) -> List[Dict[str, Any]]:
        """
        AI 生成活动推荐

        基于双方兴趣、地理位置等生成个性化推荐

        Args:
            user_profile: 用户资料
            partner_profile: 对方资料
            location: 地理位置
            time_budget: 时间预算
            relationship_stage: 关系阶段
            budget_preference: 预算偏好

        Returns:
            活动推荐列表
        """
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        # 分析共同兴趣
        common_interests = self._find_common_interests(
            user_profile.get("interests", []),
            partner_profile.get("interests", [])
        )

        # 分析互补兴趣
        complementary_interests = self._find_complementary_interests(
            user_profile.get("interests", []),
            partner_profile.get("interests", [])
        )

        prompt = f"""请为以下两位用户推荐共同活动：

用户 A：
- 年龄：{user_profile.get('age')}
- 兴趣：{user_profile.get('interests', [])}
- 简介：{user_profile.get('bio', '')}

用户 B：
- 年龄：{partner_profile.get('age')}
- 兴趣：{partner_profile.get('interests', [])}
- 简介：{partner_profile.get('bio', '')}

共同兴趣：{common_interests}
互补兴趣：{complementary_interests}

位置：{location}
时间预算：{time_budget}（quick=1-2小时，half_day=3-5小时，full_day=全天）
关系阶段：{relationship_stage}
预算偏好：{budget_preference}

请推荐 5 个合适的活动：
1. 每个活动要说明为什么适合这两位用户
2. 每个活动给出具体建议（地点、时间、注意事项）
3. 每个活动标注难度级别（适合初次约会/适合熟悉后）
4. 每个活动给出预期效果

回复格式：
[
  {
    "activity_name": "活动名称",
    "activity_type": "outdoor/entertainment/food/culture/sports/relax",
    "description": "活动描述",
    "suitability_reason": "为什么适合",
    "specific_suggestions": {
      "location_suggestion": "具体地点建议",
      "timing_suggestion": "时间建议",
      "notes": "注意事项"
    },
    "difficulty_level": "easy/medium/advanced",
    "expected_effect": "预期效果",
    "estimated_duration": "预计时长",
    "estimated_cost": "预计花费",
    "confidence": 0.85
  },
  ...
]"""

        try:
            result = await llm_service.generate(prompt)
            import json
            recommendations = json.loads(result)

            # 记录推荐历史
            await self._record_recommendation_history(
                user_profile.get("id", ""),
                partner_profile.get("id", ""),
                recommendations
            )

            return recommendations
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            # 返回默认推荐
            return self._get_default_recommendations(common_interests)

    def _find_common_interests(
        self,
        interests_a: List[str],
        interests_b: List[str]
    ) -> List[str]:
        """发现共同兴趣"""
        if not interests_a or not interests_b:
            return []
        return list(set(interests_a) & set(interests_b))

    def _find_complementary_interests(
        self,
        interests_a: List[str],
        interests_b: List[str]
    ) -> Dict[str, List[str]]:
        """发现互补兴趣"""
        return {
            "user_a_unique": list(set(interests_a) - set(interests_b)) if interests_a else [],
            "user_b_unique": list(set(interests_b) - set(interests_a)) if interests_b else []
        }

    async def _record_recommendation_history(
        self,
        user_id: str,
        partner_id: str,
        recommendations: List[Dict]
    ):
        """记录推荐历史"""
        from models.joint_activity import ActivityRecommendationHistoryDB

        for rec in recommendations:
            history = ActivityRecommendationHistoryDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                partner_id=partner_id,
                activity_name=rec.get("activity_name"),
                activity_type=rec.get("activity_type"),
                created_at=datetime.now()
            )
            self.db.add(history)

        self.db.commit()

    def _get_default_recommendations(self, common_interests: List[str]) -> List[Dict]:
        """获取默认推荐"""
        default = [
            {
                "activity_name": "咖啡厅聊天",
                "activity_type": "food",
                "description": "轻松的咖啡厅环境，适合初次见面",
                "suitability_reason": "低压力环境，容易沟通",
                "difficulty_level": "easy",
                "estimated_duration": "1-2小时",
                "confidence": 0.7
            },
            {
                "activity_name": "公园散步",
                "activity_type": "outdoor",
                "description": "户外轻松活动",
                "suitability_reason": "自然环境，放松身心",
                "difficulty_level": "easy",
                "estimated_duration": "1-2小时",
                "confidence": 0.7
            }
        ]

        # 如果有共同兴趣，添加相关活动
        if common_interests:
            for interest in common_interests[:2]:
                default.append({
                    "activity_name": f"{interest}相关活动",
                    "activity_type": "culture",
                    "description": f"基于共同兴趣：{interest}",
                    "suitability_reason": "共同兴趣增加共鸣",
                    "difficulty_level": "medium",
                    "confidence": 0.8
                })

        return default

    def get_activity_types(self) -> List[Dict[str, Any]]:
        """获取活动类型列表"""
        return self.ACTIVITY_TYPES

    async def get_activity_detail(
        self,
        activity_name: str,
        location: str
    ) -> Dict[str, Any]:
        """
        获取活动详情

        AI 生成活动的具体建议和注意事项
        """
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        prompt = f"""请为活动"{activity_name}"生成详细建议：

位置：{location}

请给出：
1. 推荐的具体地点（3-5个）
2. 最佳时间建议
3. 需要准备的物品
4. 预算估计
5. 注意事项
6. 如何让活动更有趣

回复格式：
{
  "recommended_locations": ["地点1", "地点2", ...],
  "best_time": "时间建议",
  "preparation_items": ["物品1", "物品2", ...],
  "budget_estimate": "预算估计",
  "important_notes": ["注意事项"],
  "fun_enhancement": ["如何更有趣"],
  "confidence": 0.85
}"""

        try:
            result = await llm_service.generate(prompt)
            import json
            detail = json.loads(result)
            return detail
        except Exception as e:
            logger.error(f"Failed to get activity detail: {e}")
            return {"confidence": 0.5}

    def record_activity_feedback(
        self,
        user_id: str,
        activity_name: str,
        rating: int,  # 1-5
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """记录活动反馈"""
        from models.joint_activity import ActivityFeedbackDB

        feedback_id = str(uuid.uuid4())

        record = ActivityFeedbackDB(
            id=feedback_id,
            user_id=user_id,
            activity_name=activity_name,
            rating=rating,
            feedback=feedback,
            created_at=datetime.now()
        )
        self.db.add(record)
        self.db.commit()

        return {
            "feedback_id": feedback_id,
            "activity_name": activity_name,
            "rating": rating
        }


# 服务工厂函数
def get_joint_activity_service(db: Session) -> JointActivityService:
    """获取共同活动服务实例"""
    return JointActivityService(db)