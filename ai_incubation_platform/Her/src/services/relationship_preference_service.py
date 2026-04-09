"""
P6 关系类型标签服务

帮助用户表达自己的关系意图，提高匹配精准度。
支持多种关系类型标签和偏好设置。
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
import uuid

from db.models import UserRelationshipPreferenceDB, UserDB


# 关系类型定义
RELATIONSHIP_TYPES = {
    "serious_relationship": {
        "name": "认真恋爱",
        "description": "寻找长期稳定的恋爱关系",
        "category": "romantic",
    },
    "casual_dating": {
        "name": "轻松约会",
        "description": "随意的约会，不带太多压力",
        "category": "romantic",
    },
    "marriage_minded": {
        "name": "以结婚为目的",
        "description": "寻找结婚对象，认真对待每一段关系",
        "category": "romantic",
    },
    "friendship_first": {
        "name": "从朋友开始",
        "description": "先从朋友做起，慢慢了解彼此",
        "category": "friendship",
    },
    "networking": {
        "name": "拓展社交圈",
        "description": "认识新朋友，拓展社交圈",
        "category": "social",
    },
    "not_sure": {
        "name": "还没想好",
        "description": "还在探索自己想要什么",
        "category": "exploring",
    },
    "open_to_explore": {
        "name": "开放探索",
        "description": "对不同类型关系都持开放态度",
        "category": "exploring",
    },
    "polyamory": {
        "name": "开放式关系",
        "description": "接受或寻找开放式关系",
        "category": "alternative",
    },
}

# 关系状态定义
RELATIONSHIP_STATUSES = {
    "single": {
        "name": "单身",
        "description": "目前单身",
    },
    "in_relationship": {
        "name": "恋爱中",
        "description": "正在恋爱中",
    },
    "married": {
        "name": "已婚",
        "description": "已婚",
    },
    "divorced": {
        "name": "离异",
        "description": "离异",
    },
    "widowed": {
        "name": "丧偶",
        "description": "丧偶",
    },
    "complicated": {
        "name": "复杂",
        "description": "情况比较复杂",
    },
}


class RelationshipPreferenceService:
    """关系类型标签服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的关系偏好"""
        pref = self.db.query(UserRelationshipPreferenceDB).filter(
            UserRelationshipPreferenceDB.user_id == user_id
        ).first()

        if not pref:
            return None

        # 解析关系类型标签
        relationship_types = json.loads(pref.relationship_types) if pref.relationship_types else []

        # 获取完整的类型信息
        types_with_info = []
        for type_key in relationship_types:
            if type_key in RELATIONSHIP_TYPES:
                types_with_info.append({
                    "key": type_key,
                    "name": RELATIONSHIP_TYPES[type_key]["name"],
                    "description": RELATIONSHIP_TYPES[type_key]["description"],
                    "category": RELATIONSHIP_TYPES[type_key]["category"],
                })

        return {
            "user_id": user_id,
            "relationship_types": types_with_info,
            "current_status": pref.current_status,
            "status_name": RELATIONSHIP_STATUSES.get(pref.current_status, {}).get("name") if pref.current_status else None,
            "expectation_description": pref.expectation_description,
            "created_at": pref.created_at.isoformat() if pref.created_at else None,
            "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
        }

    def update_preferences(self, user_id: str,
                           relationship_types: Optional[List[str]] = None,
                           current_status: Optional[str] = None,
                           expectation_description: Optional[str] = None) -> Dict[str, Any]:
        """更新用户的关系偏好"""
        # 验证关系类型
        if relationship_types:
            for type_key in relationship_types:
                if type_key not in RELATIONSHIP_TYPES:
                    raise ValueError(f"未知的关系类型：{type_key}")

        # 验证关系状态
        if current_status and current_status not in RELATIONSHIP_STATUSES:
            raise ValueError(f"未知的关系状态：{current_status}")

        # 获取或创建偏好记录
        pref = self.db.query(UserRelationshipPreferenceDB).filter(
            UserRelationshipPreferenceDB.user_id == user_id
        ).first()

        if not pref:
            pref = UserRelationshipPreferenceDB(
                id=str(uuid.uuid4()),
                user_id=user_id
            )
            self.db.add(pref)

        # 更新字段
        if relationship_types is not None:
            pref.relationship_types = json.dumps(relationship_types)

        if current_status is not None:
            pref.current_status = current_status

        if expectation_description is not None:
            pref.expectation_description = expectation_description

        self.db.commit()
        self.db.refresh(pref)

        return self.get_user_preferences(user_id)

    def get_all_relationship_types(self) -> List[Dict[str, Any]]:
        """获取所有可用的关系类型"""
        return [
            {
                "key": key,
                "name": info["name"],
                "description": info["description"],
                "category": info["category"],
            }
            for key, info in RELATIONSHIP_TYPES.items()
        ]

    def get_all_relationship_statuses(self) -> List[Dict[str, Any]]:
        """获取所有可用的关系状态"""
        return [
            {
                "key": key,
                "name": info["name"],
                "description": info["description"],
            }
            for key, info in RELATIONSHIP_STATUSES.items()
        ]

    def match_relationship_compatibility(self, user_id: str,
                                          target_user_id: str) -> Dict[str, Any]:
        """
        检查两个用户的关系类型兼容性

        返回兼容性评分和建议
        """
        user_pref = self.get_user_preferences(user_id)
        target_pref = self.get_user_preferences(target_user_id)

        if not user_pref or not target_pref:
            return {
                "compatible": False,
                "score": 0,
                "reason": "一方或双方未设置关系偏好",
                "details": [],
            }

        score = 0
        details = []
        max_score = 100

        # 关系类型匹配检查
        user_types = set(t["key"] for t in user_pref.get("relationship_types", []))
        target_types = set(t["key"] for t in target_pref.get("relationship_types", []))

        if user_types and target_types:
            # 检查是否有重叠
            common_types = user_types & target_types
            if common_types:
                score += 40
                details.append({
                    "type": "common_goals",
                    "message": f"你们有共同的关系期待：{', '.join([RELATIONSHIP_TYPES[t]['name'] for t in common_types])}",
                    "positive": True,
                })
            else:
                # 检查类别是否兼容
                user_categories = set(RELATIONSHIP_TYPES[t]["category"] for t in user_types if t in RELATIONSHIP_TYPES)
                target_categories = set(RELATIONSHIP_TYPES[t]["category"] for t in target_types if t in RELATIONSHIP_TYPES)

                if user_categories & target_categories:
                    score += 20
                    details.append({
                        "type": "similar_category",
                        "message": "你们的关系期待属于相似类别",
                        "positive": True,
                    })
                else:
                    details.append({
                        "type": "different_goals",
                        "message": "你们的关系期待可能存在差异，建议提前沟通",
                        "positive": False,
                    })

        # 关系状态检查
        if user_pref.get("current_status") == target_pref.get("current_status"):
            score += 20
            details.append({
                "type": "same_status",
                "message": "你们目前的关系状态相同",
                "positive": True,
            })

        # 检查敏感状态组合
        status_combinations = [
            ("single", "single"),
            ("divorced", "divorced"),
        ]
        status_pair = (user_pref.get("current_status"), target_pref.get("current_status"))
        if status_pair in status_combinations:
            score += 10

        # 自定义描述匹配（简单关键词匹配）
        if user_pref.get("expectation_description") and target_pref.get("expectation_description"):
            user_words = set(user_pref["expectation_description"].split())
            target_words = set(target_pref["expectation_description"].split())
            common_words = user_words & target_words
            if len(common_words) >= 2:
                score += 10
                details.append({
                    "type": "similar_expectations",
                    "message": "你们对关系的期待有相似之处",
                    "positive": True,
                })

        # 限制最高分
        score = min(score, max_score)

        # 兼容性判定
        compatible = score >= 50

        return {
            "compatible": compatible,
            "score": score,
            "max_score": max_score,
            "details": details,
            "recommendation": self._generate_recommendation(score, details),
        }

    def _generate_recommendation(self, score: int, details: List[Dict]) -> str:
        """生成匹配建议"""
        if score >= 80:
            return "你们的关系期待高度匹配，是个好的开始！"
        elif score >= 50:
            return "你们的关系期待基本 compatible，建议进一步沟通了解彼此期待。"
        elif score >= 30:
            return "你们的关系期待存在一定差异，开诚布公地沟通很重要。"
        else:
            return "你们的关系期待可能有较大差异，建议先明确彼此的想法。"

    def get_users_by_relationship_type(self, relationship_type: str,
                                        limit: int = 50) -> List[Dict[str, Any]]:
        """获取具有特定关系类型的用户列表"""
        prefs = self.db.query(UserRelationshipPreferenceDB).filter(
            UserRelationshipPreferenceDB.relationship_types.like(f'%"{relationship_type}"%')
        ).limit(limit).all()

        return [{"user_id": pref.user_id} for pref in prefs]

    def get_compatibility_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户的关系兼容性统计"""
        pref = self.get_user_preferences(user_id)

        if not pref or not pref.get("relationship_types"):
            return {
                "user_types": [],
                "potential_match_rate": 0,
                "message": "设置关系类型可以获得更精准的匹配",
            }

        # 统计平台用户关系类型分布
        all_prefs = self.db.query(UserRelationshipPreferenceDB).all()
        total_users = len(all_prefs)

        if total_users == 0:
            return {
                "user_types": pref["relationship_types"],
                "potential_match_rate": 0,
                "message": "平台用户数据不足",
            }

        # 计算潜在匹配率
        match_count = 0
        for p in all_prefs:
            if p.relationship_types:
                user_types = set(t["key"] for t in pref["relationship_types"])
                target_types = set(json.loads(p.relationship_types))
                if user_types & target_types:
                    match_count += 1

        match_rate = round(match_count / total_users * 100, 2)

        return {
            "user_types": pref["relationship_types"],
            "total_users_with_prefs": total_users,
            "potential_matches": match_count,
            "potential_match_rate": match_rate,
            "message": f"约 {match_rate}% 的用户与你有相似的关系期待",
        }