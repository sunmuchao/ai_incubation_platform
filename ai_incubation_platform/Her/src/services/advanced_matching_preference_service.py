"""
高级匹配偏好服务

提供更细化的匹配条件设置：
- 年龄范围
- 身高范围
- 教育程度
- 职业/行业
- 生活习惯（作息、运动、饮食）
- 兴趣爱好标签
- 地理位置
- 交友目的
- 关系期望
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from utils.logger import logger
from services.base_service import BaseService


class AdvancedMatchingPreferenceService(BaseService):
    """高级匹配偏好服务"""

    # 偏好维度配置
    DIMENSIONS = [
        {
            "name": "age_range",
            "label": "年龄范围",
            "type": "range",
            "default": {"min": 18, "max": 45}
        },
        {
            "name": "height_range",
            "label": "身高范围",
            "type": "range",
            "default": {"min": 150, "max": 200}
        },
        {
            "name": "education",
            "label": "教育程度",
            "type": "multi_select",
            "options": ["高中", "大专", "本科", "硕士", "博士", "不限"]
        },
        {
            "name": "occupation",
            "label": "职业/行业",
            "type": "multi_select",
            "options": ["互联网", "金融", "教育", "医疗", "艺术", "公务员", "学生", "其他"]
        },
        {
            "name": "lifestyle",
            "label": "生活习惯",
            "type": "multi_select",
            "options": ["早睡早起", "熬夜党", "运动达人", "宅家派", "吃货", "健康饮食"]
        },
        {
            "name": "interests",
            "label": "兴趣爱好",
            "type": "tags",
            "max_count": 10
        },
        {
            "name": "location",
            "label": "地理位置",
            "type": "location",
            "default": {"max_distance": 50}  # 最大距离（km）
        },
        {
            "name": "relationship_goal",
            "label": "交友目的",
            "type": "single_select",
            "options": ["寻找伴侣", "结交朋友", "拓展人脉", "随缘"]
        },
        {
            "name": "relationship_expectation",
            "label": "关系期望",
            "type": "multi_select",
            "options": ["长期关系", "短期接触", "先了解再说", "不确定"]
        },
        {
            "name": "deal_breakers",
            "label": "雷区（不接受）",
            "type": "tags",
            "max_count": 5
        }
    ]

    # 优先级权重配置
    WEIGHT_CONFIG = {
        "age_range": 0.15,
        "interests": 0.25,
        "location": 0.15,
        "relationship_goal": 0.15,
        "lifestyle": 0.10,
        "education": 0.05,
        "occupation": 0.05,
        "height_range": 0.05
    }

    def __init__(self, db: Session):
        super().__init__(db)
        self.db = db

    def get_preference_schema(self) -> List[Dict[str, Any]]:
        """
        获取偏好配置模板

        返回所有维度的配置信息
        """
        return self.DIMENSIONS

    def save_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        保存用户匹配偏好

        Args:
            user_id: 用户 ID
            preferences: 偏好设置字典

        Returns:
            保存结果
        """
        from models.matching_preference import UserMatchingPreferenceDB

        preference_id = str(uuid.uuid4())

        # 检查是否已有偏好设置
        existing = self.db.query(UserMatchingPreferenceDB).filter(
            UserMatchingPreferenceDB.user_id == user_id
        ).first()

        if existing:
            # 更新现有偏好
            for key, value in preferences.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now()
            self.db.commit()
            logger.info(f"Updated matching preferences for user {user_id}")

            return {
                "success": True,
                "preference_id": existing.id,
                "user_id": user_id,
                "message": "偏好已更新"
            }

        # 创建新偏好
        new_preference = UserMatchingPreferenceDB(
            id=preference_id,
            user_id=user_id,
            age_min=preferences.get("age_min", 18),
            age_max=preferences.get("age_max", 45),
            height_min=preferences.get("height_min"),
            height_max=preferences.get("height_max"),
            education=preferences.get("education"),
            occupation=preferences.get("occupation"),
            lifestyle=preferences.get("lifestyle"),
            interests=preferences.get("interests"),
            location_city=preferences.get("location_city"),
            max_distance=preferences.get("max_distance", 50),
            relationship_goal=preferences.get("relationship_goal"),
            relationship_expectation=preferences.get("relationship_expectation"),
            deal_breakers=preferences.get("deal_breakers"),
            weight_config=preferences.get("weight_config", self.WEIGHT_CONFIG),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(new_preference)
        self.db.commit()

        logger.info(f"Created matching preferences for user {user_id}")

        return {
            "success": True,
            "preference_id": preference_id,
            "user_id": user_id,
            "message": "偏好已保存"
        }

    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户匹配偏好

        Args:
            user_id: 用户 ID

        Returns:
            偏好设置
        """
        from models.matching_preference import UserMatchingPreferenceDB

        preference = self.db.query(UserMatchingPreferenceDB).filter(
            UserMatchingPreferenceDB.user_id == user_id
        ).first()

        if preference:
            return {
                "preference_id": preference.id,
                "user_id": preference.user_id,
                "age_min": preference.age_min,
                "age_max": preference.age_max,
                "height_min": preference.height_min,
                "height_max": preference.height_max,
                "education": preference.education,
                "occupation": preference.occupation,
                "lifestyle": preference.lifestyle,
                "interests": preference.interests,
                "location_city": preference.location_city,
                "max_distance": preference.max_distance,
                "relationship_goal": preference.relationship_goal,
                "relationship_expectation": preference.relationship_expectation,
                "deal_breakers": preference.deal_breakers,
                "weight_config": preference.weight_config,
                "created_at": preference.created_at.isoformat(),
                "updated_at": preference.updated_at.isoformat()
            }

        return None

    def calculate_match_score(
        self,
        user_preferences: Dict[str, Any],
        candidate_profile: Dict[str, Any]
    ) -> float:
        """
        计算匹配分数

        根据用户偏好和候选人资料计算匹配度

        Args:
            user_preferences: 用户偏好
            candidate_profile: 候选人资料

        Returns:
            匹配分数（0-1）
        """
        weight_config = user_preferences.get("weight_config", self.WEIGHT_CONFIG)
        total_score = 0.0

        # 年龄匹配
        age_score = self._score_age_range(
            user_preferences.get("age_min", 18),
            user_preferences.get("age_max", 45),
            candidate_profile.get("age", 25)
        )
        total_score += age_score * weight_config.get("age_range", 0.15)

        # 兴趣匹配
        interest_score = self._score_interests(
            user_preferences.get("interests", []),
            candidate_profile.get("interests", [])
        )
        total_score += interest_score * weight_config.get("interests", 0.25)

        # 地理位置匹配
        location_score = self._score_location(
            user_preferences.get("location_city"),
            user_preferences.get("max_distance", 50),
            candidate_profile.get("location")
        )
        total_score += location_score * weight_config.get("location", 0.15)

        # 交友目的匹配
        goal_score = self._score_relationship_goal(
            user_preferences.get("relationship_goal"),
            candidate_profile.get("goal")
        )
        total_score += goal_score * weight_config.get("relationship_goal", 0.15)

        # 生活习惯匹配
        lifestyle_score = self._score_lifestyle(
            user_preferences.get("lifestyle", []),
            candidate_profile.get("lifestyle", [])
        )
        total_score += lifestyle_score * weight_config.get("lifestyle", 0.10)

        # 教育匹配
        education_score = self._score_education(
            user_preferences.get("education", []),
            candidate_profile.get("education")
        )
        total_score += education_score * weight_config.get("education", 0.05)

        # 职业匹配
        occupation_score = self._score_occupation(
            user_preferences.get("occupation", []),
            candidate_profile.get("occupation")
        )
        total_score += occupation_score * weight_config.get("occupation", 0.05)

        # 身高匹配
        height_score = self._score_height_range(
            user_preferences.get("height_min"),
            user_preferences.get("height_max"),
            candidate_profile.get("height")
        )
        total_score += height_score * weight_config.get("height_range", 0.05)

        # 雷区检查
        if self._check_deal_breakers(
            user_preferences.get("deal_breakers", []),
            candidate_profile
        ):
            total_score *= 0.3  # 触碰雷区，分数大幅降低

        return min(total_score, 1.0)

    def _score_age_range(self, min_age: int, max_age: int, candidate_age: int) -> float:
        """计算年龄匹配分数"""
        if min_age <= candidate_age <= max_age:
            return 1.0
        # 超出范围，按距离衰减
        if candidate_age < min_age:
            return max(0, 1 - (min_age - candidate_age) / 10)
        else:
            return max(0, 1 - (candidate_age - max_age) / 10)

    def _score_interests(self, user_interests: List, candidate_interests: List) -> float:
        """计算兴趣匹配分数"""
        if not user_interests or not candidate_interests:
            return 0.5

        common = set(user_interests) & set(candidate_interests)
        return len(common) / min(len(user_interests), 5)  # 最多算5个兴趣

    def _score_location(self, user_city: str, max_distance: int, candidate_location: str) -> float:
        """计算地理位置匹配分数"""
        if not user_city or not candidate_location:
            return 0.5

        if user_city == candidate_location:
            return 1.0

        # 距离计算简化实现：同城返回 1.0，否则返回 0.5
        # 注：精确距离计算需集成地理位置服务（如高德 API）
        return 0.5

    def _score_relationship_goal(self, user_goal: str, candidate_goal: str) -> float:
        """计算交友目的匹配分数"""
        if not user_goal or not candidate_goal:
            return 0.5

        # 完全匹配
        if user_goal == candidate_goal:
            return 1.0

        # 相容目标
        compatible_goals = {
            "寻找伴侣": ["寻找伴侣", "长期关系"],
            "结交朋友": ["结交朋友", "拓展人脉"],
            "随缘": ["随缘", "先了解再说"]
        }

        if candidate_goal in compatible_goals.get(user_goal, []):
            return 0.8

        return 0.3

    def _score_lifestyle(self, user_lifestyle: List, candidate_lifestyle: List) -> float:
        """计算生活习惯匹配分数"""
        if not user_lifestyle or not candidate_lifestyle:
            return 0.5

        common = set(user_lifestyle) & set(candidate_lifestyle)
        return min(len(common) / 3, 1.0)

    def _score_education(self, user_education: List, candidate_education: str) -> float:
        """计算教育匹配分数"""
        if not user_education or "不限" in user_education:
            return 1.0

        if candidate_education in user_education:
            return 1.0

        return 0.5

    def _score_occupation(self, user_occupation: List, candidate_occupation: str) -> float:
        """计算职业匹配分数"""
        if not user_occupation:
            return 1.0

        if candidate_occupation in user_occupation:
            return 1.0

        return 0.5

    def _score_height_range(self, min_height: int, max_height: int, candidate_height: int) -> float:
        """计算身高匹配分数"""
        if not min_height or not max_height or not candidate_height:
            return 0.5

        if min_height <= candidate_height <= max_height:
            return 1.0

        return 0.5

    def _check_deal_breakers(self, deal_breakers: List, candidate_profile: Dict) -> bool:
        """检查是否触碰雷区"""
        if not deal_breakers:
            return False

        # 简单检查：检查候选人的属性是否包含雷区关键词
        for breaker in deal_breakers:
            for key, value in candidate_profile.items():
                if isinstance(value, str) and breaker.lower() in value.lower():
                    return True
                if isinstance(value, list) and breaker in value:
                    return True

        return False

    async def generate_preference_suggestions(
        self,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI 生成偏好建议

        根据用户资料，AI 建议合适的匹配偏好

        Args:
            user_profile: 用户资料

        Returns:
            建议的偏好设置
        """
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        prompt = f"""请根据用户资料，建议合适的匹配偏好设置：

用户资料：
- 年龄：{user_profile.get('age')}
- 性别：{user_profile.get('gender')}
- 位置：{user_profile.get('location')}
- 兴趣：{user_profile.get('interests', [])}
- 简介：{user_profile.get('bio')}
- 交友目的：{user_profile.get('goal')}

请建议：
1. 年龄范围（考虑用户年龄）
2. 兴趣匹配优先级
3. 地理距离偏好
4. 生活习惯兼容性
5. 关系期望

回复格式：
{
  "age_range": {"min": X, "max": Y, "reason": "原因"},
  "interests_priority": ["优先匹配的兴趣"],
  "max_distance": 距离,
  "lifestyle_compatibility": ["期望的生活习惯"],
  "relationship_expectation": "建议",
  "confidence": 0.8
}"""

        try:
            result = await llm_service.generate(prompt)
            import json
            suggestions = json.loads(result)
            return suggestions
        except Exception as e:
            logger.error(f"Failed to generate preference suggestions: {e}")
            return {
                "age_range": {"min": user_profile.get('age') - 5, "max": user_profile.get('age') + 10},
                "max_distance": 50,
                "confidence": 0.5
            }


# 服务工厂函数
def get_advanced_matching_preference_service(db: Session) -> AdvancedMatchingPreferenceService:
    """获取高级匹配偏好服务实例"""
    return AdvancedMatchingPreferenceService(db)