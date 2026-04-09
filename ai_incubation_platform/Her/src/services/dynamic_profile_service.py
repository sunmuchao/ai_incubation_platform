"""
动态用户画像服务 - P3

基于用户行为和对话分析，动态更新用户画像：
- 兴趣标签演化
- 沟通风格画像
- 偏好变化趋势
- 隐性偏好发现

遵循隐私保护原则：
- 用户可关闭「用于改进匹配的个性化数据」
- 支持数据导出和删除
- 优先保留摘要和特征，不长期存储原文

P20 增强:
- 使用统一的数据库会话管理器
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from db.database import SessionLocal
from db.models import UserProfileUpdateDB, UserDB, BehaviorEventDB, ConversationDB
from services.behavior_tracking_service import behavior_service
from services.conversation_analysis_service import conversation_analyzer
from utils.logger import logger
from utils.db_session_manager import db_session, db_session_readonly


class DynamicUserProfileService:
    """动态用户画像服务"""

    def __init__(self):
        self._update_threshold = 0.6  # 更新阈值
        self._min_confidence = 0.5  # 最低置信度

    def analyze_and_update_profile(self, user_id: str) -> Dict[str, Any]:
        """
        分析用户数据并更新画像

        Args:
            user_id: 用户 ID

        Returns:
            更新结果
        """
        # P20 增强：使用统一的数据库会话管理器
        with db_session() as db:
            # 1. 从对话分析获取建议
            conversation_suggestions = conversation_analyzer.generate_profile_update_suggestions(user_id)

            # 2. 从行为分析获取建议
            behavior_suggestions = self._analyze_behavior_for_profile(user_id)

            # 3. 合并建议
            all_suggestions = conversation_suggestions + behavior_suggestions

            # 4. 过滤高置信度建议
            high_confidence_suggestions = [
                s for s in all_suggestions
                if s.get("confidence", 0) >= self._min_confidence
            ]

            # 5. 应用更新
            applied_updates = []
            for suggestion in high_confidence_suggestions:
                update_result = self._apply_profile_update(user_id, suggestion, db)
                if update_result.get("applied"):
                    applied_updates.append(update_result)

            return {
                "user_id": user_id,
                "suggestions_count": len(all_suggestions),
                "applied_updates": applied_updates,
                "high_confidence_count": len(high_confidence_suggestions)
            }

    def _analyze_behavior_for_profile(self, user_id: str) -> List[Dict[str, Any]]:
        """基于行为分析生成画像建议"""
        suggestions = []

        # 获取行为摘要
        behavior_summary = behavior_service.get_user_behavior_summary(user_id, days=14)

        if behavior_summary.get("total_events", 0) < 10:
            return suggestions  # 数据不足

        # 分析最常查看的用户类型
        top_viewed = behavior_summary.get("top_viewed_profiles", [])
        if top_viewed:
            suggestions.append({
                "update_type": "behavior_pattern",
                "pattern": "frequently_viewed_profiles",
                "data": top_viewed,
                "confidence": min(0.8, len(top_viewed) / 10),
                "source": "behavior_analysis"
            })

        # 分析活跃时段
        peak_hours = behavior_summary.get("peak_activity_hours", [])
        if peak_hours:
            suggestions.append({
                "update_type": "behavior_pattern",
                "pattern": "active_hours",
                "data": {"hours": peak_hours},
                "confidence": 0.7,
                "source": "behavior_analysis"
            })

        # 分析选择倾向
        event_counts = behavior_summary.get("event_counts", {})
        likes = event_counts.get("like", 0)
        passes = event_counts.get("pass", 0)

        if likes + passes > 20:
            like_rate = likes / (likes + passes)
            suggestions.append({
                "update_type": "behavior_pattern",
                "pattern": "selection_tendency",
                "data": {"like_rate": like_rate},
                "confidence": min(0.9, (likes + passes) / 50),
                "source": "behavior_analysis"
            })

        return suggestions

    def _apply_profile_update(
        self,
        user_id: str,
        suggestion: Dict[str, Any],
        db
    ) -> Dict[str, Any]:
        """应用画像更新"""
        update_id = str(__import__('uuid').uuid4())

        try:
            # 获取当前用户数据
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return {"applied": False, "reason": "user_not_found"}

            # 根据更新类型应用
            if suggestion["update_type"] == "interest_from_conversation":
                # 从对话提取的兴趣
                current_interests = json.loads(user.interests) if user.interests else []
                suggested_interests = suggestion.get("suggested_interests", [])

                # 添加新兴趣
                new_interests = [i for i in suggested_interests if i not in current_interests]
                if new_interests:
                    updated_interests = current_interests + new_interests
                    old_value = json.dumps(current_interests)
                    new_value = json.dumps(updated_interests)

                    user.interests = new_value
                    db.commit()

                    # 记录更新
                    update_record = UserProfileUpdateDB(
                        id=update_id,
                        user_id=user_id,
                        update_type=suggestion["update_type"],
                        old_value=old_value,
                        new_value=new_value,
                        source=suggestion.get("source", "unknown"),
                        confidence=suggestion.get("confidence", 0.5),
                        applied=True
                    )
                    db.add(update_record)
                    db.commit()

                    logger.info(f"Updated user {user_id} interests: added {new_interests}")

                    return {
                        "applied": True,
                        "update_type": suggestion["update_type"],
                        "changes": {"added": new_interests}
                    }

            elif suggestion["update_type"] == "behavior_pattern":
                # 行为模式更新（记录但不直接修改用户表）
                update_record = UserProfileUpdateDB(
                    id=update_id,
                    user_id=user_id,
                    update_type=suggestion["update_type"],
                    old_value=None,
                    new_value=json.dumps(suggestion.get("data", {})),
                    source=suggestion.get("source", "unknown"),
                    confidence=suggestion.get("confidence", 0.5),
                    applied=True
                )
                db.add(update_record)
                db.commit()

                return {
                    "applied": True,
                    "update_type": suggestion["update_type"],
                    "pattern": suggestion.get("pattern"),
                    "data": suggestion.get("data")
                }

            return {"applied": False, "reason": "unknown_update_type"}

        except Exception as e:
            db.rollback()
            logger.error(f"Error applying profile update: {e}")
            return {"applied": False, "reason": str(e)}

    def get_profile_evolution(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取用户画像演化历史

        Args:
            user_id: 用户 ID
            days: 天数

        Returns:
            演化历史
        """
        # P20 增强：使用统一的数据库会话管理器
        with db_session_readonly() as db:
            since = datetime.now() - timedelta(days=days)

            updates = db.query(UserProfileUpdateDB).filter(
                UserProfileUpdateDB.user_id == user_id,
                UserProfileUpdateDB.created_at >= since
            ).order_by(UserProfileUpdateDB.created_at).all()

            evolution = []
            for update in updates:
                evolution.append({
                    "timestamp": update.created_at.isoformat(),
                    "type": update.update_type,
                    "source": update.source,
                    "confidence": update.confidence,
                    "applied": update.applied
                })

            return {
                "user_id": user_id,
                "period_days": days,
                "updates": evolution,
                "total_updates": len(evolution)
            }

    def get_enhanced_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        获取增强版用户画像（静态 + 动态）

        Args:
            user_id: 用户 ID

        Returns:
            增强画像
        """
        # P20 增强：使用统一的数据库会话管理器
        with db_session_readonly() as db:
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return {"error": "user_not_found"}

            # 基础静态信息
            interests = json.loads(user.interests) if user.interests else []
            values = json.loads(user.values) if user.values else {}

            profile = {
                "user_id": user_id,
                "static_profile": {
                    "name": user.name,
                    "age": user.age,
                    "gender": user.gender,
                    "location": user.location,
                    "interests": interests,
                    "values": values,
                    "bio": user.bio,
                    "preferences": {
                        "age_range": [user.preferred_age_min, user.preferred_age_max],
                        "preferred_gender": user.preferred_gender
                    }
                }
            }

            # 动态行为画像
            behavior_summary = behavior_service.get_user_behavior_summary(user_id, days=14)
            profile["dynamic_profile"] = {
                "behavior_summary": behavior_summary,
                "topic_profile": conversation_analyzer.get_user_topic_profile(user_id),
                "preference_shift": behavior_service.analyze_preference_shift(user_id, days=30)
            }

            return profile

    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        导出用户数据（隐私合规）

        Args:
            user_id: 用户 ID

        Returns:
            用户数据
        """
        with db_session_readonly() as db:
            # 用户基本信息
            user = db.query(UserDB).filter(UserDB.id == user_id).first()

            # 行为数据
            behaviors = db.query(BehaviorEventDB).filter(
                BehaviorEventDB.user_id == user_id
            ).all()

            # 对话数据
            conversations = db.query(ConversationDB).filter(
                (ConversationDB.user_id_1 == user_id) |
                (ConversationDB.user_id_2 == user_id)
            ).all()

            # 画像更新记录
            updates = db.query(UserProfileUpdateDB).filter(
                UserProfileUpdateDB.user_id == user_id
            ).all()

            return {
                "user_info": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                },
                "profile_data": {
                    "interests": json.loads(user.interests) if user.interests else [],
                    "values": json.loads(user.values) if user.values else {},
                    "preferences": {
                        "age_range": [user.preferred_age_min, user.preferred_age_max],
                        "preferred_gender": user.preferred_gender,
                        "preferred_location": user.preferred_location
                    }
                },
                "behavior_events": [
                    {
                        "type": b.event_type,
                        "target_id": b.target_id,
                        "timestamp": b.created_at.isoformat()
                    }
                    for b in behaviors
                ],
                "conversations_count": len(conversations),
                "profile_updates": [
                    {
                        "type": u.update_type,
                        "source": u.source,
                        "applied": u.applied,
                        "timestamp": u.created_at.isoformat()
                    }
                    for u in updates
                ],
                "export_timestamp": datetime.now().isoformat()
            }


# 全局服务实例
dynamic_profile_service = DynamicUserProfileService()
