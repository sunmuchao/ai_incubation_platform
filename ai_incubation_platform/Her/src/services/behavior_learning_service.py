"""
P6 行为学习推荐服务

基于用户行为数据的深度学习推荐系统。
使用协同过滤和特征工程实现个性化推荐。
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import json
import math
import uuid
from collections import defaultdict

from db.models import (
    UserBehaviorFeatureDB, MatchInteractionDB, UserDB,
    MatchHistoryDB, SwipeActionDB, BehaviorEventDB
)
from services.base_service import BaseService


class BehaviorLearningService(BaseService):
    """行为学习推荐服务"""

    def __init__(self, db: Session):
        super().__init__(db)

        # 推荐配置
        self.config = {
            "min_interactions": 5,  # 最小交互次数用于推荐
            "similarity_threshold": 0.3,  # 相似度阈值
            "decay_factor": 0.95,  # 时间衰减因子（每天）
            "max_candidates": 100,  # 最大候选用户数
        }

    def record_interaction(self, user_id: str, target_user_id: str,
                           interaction_type: str,
                           dwell_time_seconds: int = 0) -> MatchInteractionDB:
        """记录用户交互行为"""
        # 确定信号方向和强度
        positive_signal, signal_strength = self._calculate_signal(
            interaction_type, dwell_time_seconds
        )

        interaction = MatchInteractionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            target_user_id=target_user_id,
            interaction_type=interaction_type,
            dwell_time_seconds=dwell_time_seconds,
            positive_signal=positive_signal,
            signal_strength=signal_strength,
        )

        self.db.add(interaction)
        self.db.commit()
        self.db.refresh(interaction)

        # 触发特征更新
        self._update_user_features(user_id)

        return interaction

    def _calculate_signal(self, interaction_type: str,
                          dwell_time_seconds: int) -> Tuple[bool, float]:
        """计算交互信号的方向和强度"""
        # 正向信号类型
        positive_types = {"viewed", "liked", "messaged", "replied", "super_liked"}
        # 负向信号类型
        negative_types = {"passed", "blocked", "reported"}

        if interaction_type in positive_types:
            positive = True
            # 根据交互深度计算强度
            strength_map = {
                "viewed": 0.1,
                "liked": 0.5,
                "super_liked": 0.8,
                "messaged": 0.6,
                "replied": 0.7,
            }
            base_strength = strength_map.get(interaction_type, 0.3)

            # 浏览时长加成
            if dwell_time_seconds > 60:
                base_strength += 0.1
            if dwell_time_seconds > 180:
                base_strength += 0.1

            strength = min(1.0, base_strength)
        else:
            positive = False
            strength_map = {
                "passed": 0.5,
                "blocked": 1.0,
                "reported": 1.0,
            }
            strength = strength_map.get(interaction_type, 0.5)

        return positive, strength

    def _update_user_features(self, user_id: str) -> UserBehaviorFeatureDB:
        """更新用户行为特征"""
        # 获取用户所有交互
        interactions = self.db.query(MatchInteractionDB).filter(
            MatchInteractionDB.user_id == user_id
        ).all()

        if len(interactions) < self.config["min_interactions"]:
            # 交互数据不足，使用默认特征
            return self._get_or_create_default_features(user_id)

        # 计算特征向量
        features = self._compute_feature_vector(interactions)

        # 获取或创建特征记录
        feature_record = self.db.query(UserBehaviorFeatureDB).filter(
            UserBehaviorFeatureDB.user_id == user_id
        ).first()

        if not feature_record:
            feature_record = UserBehaviorFeatureDB(
                id=str(uuid.uuid4()),
                user_id=user_id
            )
            self.db.add(feature_record)

        feature_record.feature_vector = json.dumps(features)
        feature_record.updated_at = datetime.utcnow()
        feature_record.last_trained_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(feature_record)

        return feature_record

    def _compute_feature_vector(self, interactions: List[MatchInteractionDB]) -> Dict[str, Any]:
        """计算用户特征向量"""
        features = {
            "version": "v1",
            "computed_at": datetime.utcnow().isoformat(),
            "preferences": {},
            "behavior_patterns": {},
            "interaction_stats": {},
        }

        # 交互统计
        total_interactions = len(interactions)
        positive_count = sum(1 for i in interactions if i.positive_signal)
        negative_count = total_interactions - positive_count

        features["interaction_stats"] = {
            "total": total_interactions,
            "positive": positive_count,
            "negative": negative_count,
            "positive_rate": positive_count / total_interactions if total_interactions > 0 else 0,
        }

        # 计算平均浏览时长
        avg_dwell_time = sum(i.dwell_time_seconds for i in interactions) / total_interactions
        features["behavior_patterns"]["avg_dwell_time"] = avg_dwell_time

        # 分析交互类型分布
        type_counts = defaultdict(int)
        for i in interactions:
            type_counts[i.interaction_type] += 1
        features["behavior_patterns"]["interaction_type_distribution"] = dict(type_counts)

        # 计算目标用户特征偏好
        target_users = [i.target_user_id for i in interactions if i.positive_signal]
        if target_users:
            target_profiles = self.db.query(UserDB).filter(
                UserDB.id.in_(target_users[:50])  # 限制查询数量
            ).all()

            if target_profiles:
                # 年龄偏好
                ages = [p.age for p in target_profiles if p.age]
                if ages:
                    features["preferences"]["preferred_age_avg"] = sum(ages) / len(ages)
                    features["preferences"]["preferred_age_range"] = [min(ages), max(ages)]

                # 性别偏好
                genders = [p.gender for p in target_profiles if p.gender]
                if genders:
                    gender_counts = defaultdict(int)
                    for g in genders:
                        gender_counts[g] += 1
                    features["preferences"]["preferred_gender"] = max(gender_counts, key=gender_counts.get)

                # 位置偏好（简化）
                locations = [p.location for p in target_profiles if p.location]
                if locations:
                    location_counts = defaultdict(int)
                    for loc in locations:
                        # 简化：取城市部分
                        city = loc.split(",")[0] if "," in loc else loc
                        location_counts[city] += 1
                    top_location = max(location_counts, key=location_counts.get)
                    features["preferences"]["preferred_location"] = top_location

        return features

    def _get_or_create_default_features(self, user_id: str) -> UserBehaviorFeatureDB:
        """获取或创建默认特征"""
        feature_record = self.db.query(UserBehaviorFeatureDB).filter(
            UserBehaviorFeatureDB.user_id == user_id
        ).first()

        if not feature_record:
            default_features = {
                "version": "v1",
                "computed_at": datetime.utcnow().isoformat(),
                "preferences": {},
                "behavior_patterns": {},
                "interaction_stats": {"total": 0, "positive": 0, "negative": 0},
            }
            feature_record = UserBehaviorFeatureDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                feature_vector=json.dumps(default_features),
            )
            self.db.add(feature_record)
            self.db.commit()

        return feature_record

    def get_user_features(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户行为特征"""
        feature_record = self.db.query(UserBehaviorFeatureDB).filter(
            UserBehaviorFeatureDB.user_id == user_id
        ).first()

        if not feature_record:
            return None

        return json.loads(feature_record.feature_vector) if feature_record.feature_vector else None

    def get_similar_users(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取相似用户（基于协同过滤）"""
        # 获取目标用户的特征
        target_features = self.get_user_features(user_id)
        if not target_features:
            return []

        # 获取所有其他用户的特征
        all_features = self.db.query(UserBehaviorFeatureDB).filter(
            UserBehaviorFeatureDB.user_id != user_id,
            UserBehaviorFeatureDB.feature_vector != ""
        ).limit(100).all()

        if not all_features:
            return []

        # 计算相似度
        similarities = []
        for feature_record in all_features:
            other_features = json.loads(feature_record.feature_vector)
            similarity = self._compute_similarity(target_features, other_features)

            if similarity >= self.config["similarity_threshold"]:
                similarities.append({
                    "user_id": feature_record.user_id,
                    "similarity": similarity,
                })

        # 按相似度排序
        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        return similarities[:limit]

    def _compute_similarity(self, features1: Dict, features2: Dict) -> float:
        """计算两个用户特征的相似度"""
        similarity_scores = []

        # 年龄偏好相似度
        pref1 = features1.get("preferences", {})
        pref2 = features2.get("preferences", {})

        if "preferred_age_avg" in pref1 and "preferred_age_avg" in pref2:
            age_diff = abs(pref1["preferred_age_avg"] - pref2["preferred_age_avg"])
            age_sim = max(0, 1 - age_diff / 20)  # 20 岁差异内线性衰减
            similarity_scores.append(age_sim)

        # 性别偏好相似度
        if pref1.get("preferred_gender") and pref2.get("preferred_gender"):
            if pref1["preferred_gender"] == pref2["preferred_gender"]:
                similarity_scores.append(1.0)
            else:
                similarity_scores.append(0.0)

        # 交互模式相似度
        stats1 = features1.get("interaction_stats", {})
        stats2 = features2.get("interaction_stats", {})

        if stats1.get("positive_rate") is not None and stats2.get("positive_rate") is not None:
            rate_diff = abs(stats1["positive_rate"] - stats2["positive_rate"])
            rate_sim = 1 - rate_diff
            similarity_scores.append(rate_sim)

        if not similarity_scores:
            return 0.0

        return sum(similarity_scores) / len(similarity_scores)

    def get_recommendations(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取个性化推荐

        基于行为学习的推荐流程：
        1. 获取用户特征
        2. 找到相似用户
        3. 推荐相似用户喜欢的用户
        """
        user_features = self.get_user_features(user_id)

        if not user_features or user_features.get("interaction_stats", {}).get("total", 0) < self.config["min_interactions"]:
            # 数据不足，返回热门用户或新用户
            return self._get_cold_start_recommendations(user_id, limit)

        # 获取相似用户
        similar_users = self.get_similar_users(user_id, limit=50)

        if not similar_users:
            return self._get_cold_start_recommendations(user_id, limit)

        # 收集相似用户喜欢的用户
        candidate_scores = defaultdict(float)

        for similar_user in similar_users:
            sim_user_id = similar_user["user_id"]
            similarity = similar_user["similarity"]

            # 获取相似用户的正向交互
            positive_interactions = self.db.query(MatchInteractionDB).filter(
                MatchInteractionDB.user_id == sim_user_id,
                MatchInteractionDB.positive_signal == True
            ).limit(50).all()

            for interaction in positive_interactions:
                target_id = interaction.target_user_id

                # 排除已交互的用户
                if self._has_interaction(user_id, target_id):
                    continue

                # 累加分数（相似度加权）
                candidate_scores[target_id] += similarity * interaction.signal_strength

        # 应用时间衰减
        candidate_scores = self._apply_decay(candidate_scores)

        # 排序并返回
        sorted_candidates = sorted(
            candidate_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {
                "user_id": candidate_id,
                "score": score,
                "reason": "与你兴趣相似的用户也喜欢",
            }
            for candidate_id, score in sorted_candidates
        ]

    def _apply_decay(self, candidate_scores: Dict[str, float],
                     user_id: str) -> Dict[str, float]:
        """应用时间衰减"""
        # 获取用户最近的交互
        recent_interactions = self.db.query(MatchInteractionDB).filter(
            MatchInteractionDB.user_id == user_id
        ).order_by(MatchInteractionDB.created_at.desc()).limit(100).all()

        if not recent_interactions:
            return candidate_scores

        # 计算平均交互时间
        now = datetime.utcnow()
        total_decay = 0
        count = 0

        for interaction in recent_interactions:
            days_old = (now - interaction.created_at).days
            decay = self.config["decay_factor"] ** days_old
            total_decay += decay
            count += 1

        avg_decay = total_decay / count if count > 0 else 1

        # 应用衰减
        decayed_scores = {}
        for candidate_id, score in candidate_scores.items():
            decayed_scores[candidate_id] = score * avg_decay

        return decayed_scores

    def _has_interaction(self, user_id: str, target_id: str) -> bool:
        """检查是否已有交互"""
        count = self.db.query(MatchInteractionDB).filter(
            MatchInteractionDB.user_id == user_id,
            MatchInteractionDB.target_user_id == target_id
        ).count()
        return count > 0

    def _get_cold_start_recommendations(self, user_id: str,
                                         limit: int = 20) -> List[Dict[str, Any]]:
        """冷启动推荐"""
        # 获取活跃用户
        active_users = self.db.query(UserDB).filter(
            UserDB.id != user_id,
            UserDB.is_active == True
        ).order_by(UserDB.created_at.desc()).limit(limit).all()

        return [
            {
                "user_id": user.id,
                "score": 0.5,  # 默认分数
                "reason": "新用户推荐",
            }
            for user in active_users
        ]

    def get_learning_stats(self, user_id: str) -> Dict[str, Any]:
        """获取学习统计"""
        total_interactions = self.db.query(MatchInteractionDB).filter(
            MatchInteractionDB.user_id == user_id
        ).count()

        positive_interactions = self.db.query(MatchInteractionDB).filter(
            MatchInteractionDB.user_id == user_id,
            MatchInteractionDB.positive_signal == True
        ).count()

        features = self.get_user_features(user_id)

        return {
            "total_interactions": total_interactions,
            "positive_interactions": positive_interactions,
            "negative_interactions": total_interactions - positive_interactions,
            "positive_rate": positive_interactions / total_interactions if total_interactions > 0 else 0,
            "has_features": features is not None,
            "features_version": features.get("version") if features else None,
        }

    def retrain_all_features(self) -> int:
        """批量重新训练所有用户特征"""
        users = self.db.query(UserDB).all()
        updated_count = 0

        for user in users:
            try:
                self._update_user_features(user.id)
                updated_count += 1
            except Exception as e:
                # 记录错误但继续处理
                pass

        return updated_count