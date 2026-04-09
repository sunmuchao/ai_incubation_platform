"""
P1: 感知层服务 - 用户向量表示和数字潜意识引擎

功能包括：
- 用户向量计算和更新
- 向量相似度计算
- 数字潜意识画像分析
- 行为 - 向量映射
- 向量偏移追踪
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import json
import uuid
import math

from models.p1_perception_models import (
    UserVectorDB,
    VectorUpdateHistoryDB,
    VectorSimilarityCacheDB,
    DigitalSubconsciousProfileDB,
    BehaviorVectorMappingDB,
    VECTOR_DIMENSIONS,
    SUBCONSCIOUS_TRAITS_LIBRARY,
    ATTACHMENT_STYLE_DESCRIPTIONS,
)
from db.models import BehaviorEventDB
from models.p1_values_models import DeclaredValuesDB, InferredValuesDB


class PerceptionLayerService:
    """感知层服务 - 用户向量表示和数字潜意识引擎"""

    def __init__(self, db: Session):
        self.db = db

    # ============= 用户向量管理 =============

    def get_or_create_user_vector(self, user_id: str) -> UserVectorDB:
        """获取或创建用户向量"""
        vector = self.db.query(UserVectorDB).filter(
            UserVectorDB.user_id == user_id
        ).first()

        if not vector:
            # 创建默认向量
            vector = self._create_default_user_vector(user_id)

        return vector

    def _create_default_user_vector(self, user_id: str) -> UserVectorDB:
        """创建默认用户向量"""
        vector = UserVectorDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            values_vector=json.dumps(self._generate_zero_vector(VECTOR_DIMENSIONS["values"])),
            interests_vector=json.dumps(self._generate_zero_vector(VECTOR_DIMENSIONS["interests"])),
            communication_style_vector=json.dumps(self._generate_zero_vector(VECTOR_DIMENSIONS["communication_style"])),
            behavior_pattern_vector=json.dumps(self._generate_zero_vector(VECTOR_DIMENSIONS["behavior_pattern"])),
            vector_version=1,
            vector_source="static",
        )
        self.db.add(vector)
        self.db.commit()
        self.db.refresh(vector)
        return vector

    def _generate_zero_vector(self, dimension: int) -> List[float]:
        """生成零向量"""
        return [0.0] * dimension

    def _generate_random_vector(self, dimension: int) -> List[float]:
        """生成随机向量（归一化）"""
        import random
        vector = [random.gauss(0, 1) for _ in range(dimension)]
        # 归一化
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        return vector

    def update_user_vectors(
        self,
        user_id: str,
        vector_type: str,
        new_vector: List[float],
        update_reason: str = "behavior_event",
        trigger_event_id: Optional[str] = None,
    ) -> UserVectorDB:
        """
        更新用户向量

        Args:
            user_id: 用户 ID
            vector_type: 向量类型 (values/interests/communication_style/behavior_pattern)
            new_vector: 新向量
            update_reason: 更新原因
            trigger_event_id: 触发事件 ID

        Returns:
            UserVectorDB: 更新后的用户向量
        """
        vector = self.get_or_create_user_vector(user_id)

        # 获取旧向量
        old_vector_json = self._get_vector_by_type(vector, vector_type)
        old_vector = json.loads(old_vector_json) if old_vector_json else None

        # 计算向量变化量
        vector_drift = self._calculate_vector_drift(
            old_vector or self._generate_zero_vector(VECTOR_DIMENSIONS.get(vector_type, 64)),
            new_vector
        )

        # 记录更新历史
        self._record_vector_update(
            user_id=user_id,
            vector_type=vector_type,
            previous_vector=old_vector,
            new_vector=new_vector,
            vector_drift=vector_drift,
            update_reason=update_reason,
            trigger_event_id=trigger_event_id,
        )

        # 更新向量
        self._set_vector_by_type(vector, vector_type, new_vector)
        vector.vector_version += 1
        vector.last_computed_at = datetime.now()
        vector.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(vector)
        return vector

    def _get_vector_by_type(self, vector: UserVectorDB, vector_type: str) -> Optional[str]:
        """根据类型获取向量"""
        type_mapping = {
            "values": "values_vector",
            "interests": "interests_vector",
            "communication_style": "communication_style_vector",
            "behavior_pattern": "behavior_pattern_vector",
        }
        attr_name = type_mapping.get(vector_type)
        if attr_name:
            return getattr(vector, attr_name)
        return None

    def _set_vector_by_type(self, vector: UserVectorDB, vector_type: str, value: List[float]):
        """根据类型设置向量"""
        type_mapping = {
            "values": "values_vector",
            "interests": "interests_vector",
            "communication_style": "communication_style_vector",
            "behavior_pattern": "behavior_pattern_vector",
        }
        attr_name = type_mapping.get(vector_type)
        if attr_name:
            setattr(vector, attr_name, json.dumps(value))

    def _calculate_vector_drift(
        self,
        old_vector: List[float],
        new_vector: List[float]
    ) -> float:
        """计算向量漂移（欧几里得距离）"""
        if len(old_vector) != len(new_vector):
            return 0.0

        squared_diff = sum((a - b) ** 2 for a, b in zip(old_vector, new_vector))
        return math.sqrt(squared_diff)

    def _record_vector_update(
        self,
        user_id: str,
        vector_type: str,
        previous_vector: Optional[List[float]],
        new_vector: List[float],
        vector_drift: float,
        update_reason: str,
        trigger_event_id: Optional[str] = None,
    ):
        """记录向量更新历史"""
        record = VectorUpdateHistoryDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            vector_type=vector_type,
            previous_vector=json.dumps(previous_vector) if previous_vector else None,
            new_vector=json.dumps(new_vector),
            vector_drift=vector_drift,
            update_reason=update_reason,
            trigger_event_id=trigger_event_id,
            update_details=json.dumps({
                "timestamp": datetime.now().isoformat(),
                "drift_magnitude": vector_drift,
            }),
        )
        self.db.add(record)
        return record

    def get_user_vector(self, user_id: str, vector_type: Optional[str] = None) -> Dict[str, Any]:
        """
        获取用户向量

        Args:
            user_id: 用户 ID
            vector_type: 向量类型，如果为 None 则返回所有向量

        Returns:
            向量数据字典
        """
        vector = self.get_or_create_user_vector(user_id)

        if vector_type:
            vector_json = self._get_vector_by_type(vector, vector_type)
            return {
                "user_id": user_id,
                "vector_type": vector_type,
                "vector": json.loads(vector_json) if vector_json else None,
                "dimension": VECTOR_DIMENSIONS.get(vector_type, 64),
                "version": vector.vector_version,
                "last_computed_at": vector.last_computed_at.isoformat() if vector.last_computed_at else None,
            }
        else:
            return {
                "user_id": user_id,
                "vectors": {
                    "values": json.loads(vector.values_vector) if vector.values_vector else None,
                    "interests": json.loads(vector.interests_vector) if vector.interests_vector else None,
                    "communication_style": json.loads(vector.communication_style_vector) if vector.communication_style_vector else None,
                    "behavior_pattern": json.loads(vector.behavior_pattern_vector) if vector.behavior_pattern_vector else None,
                },
                "version": vector.vector_version,
                "last_computed_at": vector.last_computed_at.isoformat() if vector.last_computed_at else None,
            }

    # ============= 向量相似度计算 =============

    def calculate_vector_similarity(
        self,
        user_a_id: str,
        user_b_id: str,
        vector_type: str,
    ) -> float:
        """
        计算两个用户的向量相似度

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            vector_type: 向量类型

        Returns:
            相似度分数 (0-1)
        """
        # 获取双方向量
        vector_a = self.get_or_create_user_vector(user_a_id)
        vector_b = self.get_or_create_user_vector(user_b_id)

        # 获取对应向量
        vector_a_json = self._get_vector_by_type(vector_a, vector_type)
        vector_b_json = self._get_vector_by_type(vector_b, vector_type)

        if not vector_a_json or not vector_b_json:
            return 0.5  # 默认相似度

        vector_a_data = json.loads(vector_a_json)
        vector_b_data = json.loads(vector_b_json)

        # 计算余弦相似度
        return self._cosine_similarity(vector_a_data, vector_b_data)

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        if len(v1) != len(v2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_v1 = math.sqrt(sum(x * x for x in v1))
        norm_v2 = math.sqrt(sum(x * x for x in v2))

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0

        return dot_product / (norm_v1 * norm_v2)

    def get_overall_compatibility(
        self,
        user_a_id: str,
        user_b_id: str,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        计算综合兼容性

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            weights: 各向量类型权重，默认均等

        Returns:
            综合兼容性分数 (0-1)
        """
        default_weights = {
            "values": 0.35,
            "interests": 0.30,
            "communication_style": 0.20,
            "behavior_pattern": 0.15,
        }

        actual_weights = weights or default_weights

        total_similarity = 0.0
        total_weight = 0.0

        for vector_type, weight in actual_weights.items():
            similarity = self.calculate_vector_similarity(
                user_a_id, user_b_id, vector_type
            )
            total_similarity += similarity * weight
            total_weight += weight

        return total_similarity / total_weight if total_weight > 0 else 0.0

    def get_or_compute_similarity_cache(
        self,
        user_a_id: str,
        user_b_id: str,
        vector_type: str,
        ttl_hours: int = 24,
    ) -> float:
        """获取或计算相似度缓存"""
        # 尝试从缓存获取
        cache = self.db.query(VectorSimilarityCacheDB).filter(
            and_(
                VectorSimilarityCacheDB.user_a_id == user_a_id,
                VectorSimilarityCacheDB.user_b_id == user_b_id,
                VectorSimilarityCacheDB.similarity_type == vector_type,
                and_(
                    VectorSimilarityCacheDB.expires_at == None,
                    VectorSimilarityCacheDB.expires_at > datetime.now(),
                ),
            )
        ).first()

        if cache:
            return cache.similarity_score

        # 计算并缓存
        similarity = self.calculate_vector_similarity(user_a_id, user_b_id, vector_type)

        # 确保 user_a_id < user_b_id 以保证唯一性
        if user_a_id > user_b_id:
            user_a_id, user_b_id = user_b_id, user_a_id

        cache_record = VectorSimilarityCacheDB(
            id=str(uuid.uuid4()),
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            similarity_type=vector_type,
            similarity_score=similarity,
            expires_at=datetime.now() + timedelta(hours=ttl_hours),
            calculation_details=json.dumps({
                "computed_at": datetime.now().isoformat(),
            }),
        )
        self.db.add(cache_record)
        self.db.commit()

        return similarity

    # ============= 数字潜意识画像 =============

    def analyze_digital_subconscious(self, user_id: str) -> DigitalSubconsciousProfileDB:
        """
        分析用户数字潜意识画像

        Args:
            user_id: 用户 ID

        Returns:
            DigitalSubconsciousProfileDB: 潜意识画像
        """
        # 获取用户向量
        vector = self.get_or_create_user_vector(user_id)

        # 获取用户价值观
        declared_values = self.db.query(DeclaredValuesDB).filter(
            DeclaredValuesDB.user_id == user_id
        ).first()

        # 获取用户行为统计
        behavior_stats = self._analyze_user_behaviors(user_id)

        # 推断潜意识特征
        subconscious_traits = self._infer_subconscious_traits(vector, behavior_stats)

        # 推断隐性需求
        hidden_needs = self._infer_hidden_needs(vector, declared_values, behavior_stats)

        # 推断依恋风格
        attachment_style = self._infer_attachment_style(vector, behavior_stats)

        # 识别关系模式
        relationship_patterns = self._identify_relationship_patterns(behavior_stats)

        # 生成成长建议
        growth_suggestions = self._generate_growth_suggestions(
            subconscious_traits, hidden_needs, attachment_style
        )

        # 计算置信度
        confidence_score = self._calculate_confidence_score(vector, behavior_stats)

        # 创建或更新画像
        existing = self.db.query(DigitalSubconsciousProfileDB).filter(
            DigitalSubconsciousProfileDB.user_id == user_id
        ).first()

        if existing:
            existing.subconscious_traits = json.dumps(subconscious_traits)
            existing.hidden_needs = json.dumps(hidden_needs)
            existing.emotional_tendency = self._determine_emotional_tendency(vector)
            existing.attachment_style = attachment_style
            existing.relationship_patterns = json.dumps(relationship_patterns)
            existing.growth_suggestions = json.dumps(growth_suggestions)
            existing.confidence_score = confidence_score
            existing.last_analyzed_at = datetime.now()
            existing.updated_at = datetime.now()
            profile = existing
        else:
            profile = DigitalSubconsciousProfileDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                subconscious_traits=json.dumps(subconscious_traits),
                hidden_needs=json.dumps(hidden_needs),
                emotional_tendency=self._determine_emotional_tendency(vector),
                attachment_style=attachment_style,
                relationship_patterns=json.dumps(relationship_patterns),
                growth_suggestions=json.dumps(growth_suggestions),
                confidence_score=confidence_score,
            )
            self.db.add(profile)

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def _analyze_user_behaviors(self, user_id: str) -> Dict[str, Any]:
        """分析用户行为统计"""
        # 获取过去 30 天的行为
        thirty_days_ago = datetime.now() - timedelta(days=30)

        behaviors = self.db.query(BehaviorEventDB).filter(
            and_(
                BehaviorEventDB.user_id == user_id,
                BehaviorEventDB.created_at >= thirty_days_ago,
            )
        ).all()

        # 统计行为类型
        event_type_counts = {}
        for behavior in behaviors:
            event_type = behavior.event_type
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

        return {
            "total_behaviors": len(behaviors),
            "event_type_counts": event_type_counts,
            "active_level": "high" if len(behaviors) > 50 else "medium" if len(behaviors) > 20 else "low",
        }

    def _infer_subconscious_traits(
        self,
        vector: UserVectorDB,
        behavior_stats: Dict[str, Any]
    ) -> List[str]:
        """推断潜意识特征"""
        traits = []

        # 基于行为模式推断
        event_counts = behavior_stats.get("event_type_counts", {})

        # 频繁主动发起聊天 -> connection_seeking
        if event_counts.get("chat_initiated", 0) > 10:
            traits.append("connection_seeking")

        # 频繁浏览资料 -> security_seeking 或 novelty_seeking
        if event_counts.get("viewed_profile", 0) > 20:
            traits.append("security_seeking")

        # 频繁约会 -> novelty_seeking
        if event_counts.get("date_completed", 0) > 5:
            traits.append("novelty_seeking")

        # 基于向量推断（简化实现）
        if vector.values_vector:
            values = json.loads(vector.values_vector)
            # 检查特定维度的值
            if sum(values[:16]) / 16 > 0.5:  # 前 16 维代表成就相关
                traits.append("achievement_oriented")

        return traits

    def _infer_hidden_needs(
        self,
        vector: UserVectorDB,
        declared_values: Optional[DeclaredValuesDB],
        behavior_stats: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """推断隐性需求"""
        needs = []

        # 基于行为与声明的差异推断
        if declared_values:
            declared = json.loads(declared_values.values_data)
            # 如果声明"家庭优先"但行为显示高频社交活动
            if declared.get("career_view") == "family_focused":
                if behavior_stats.get("event_type_counts", {}).get("social_activity", 0) > 10:
                    needs.append({
                        "need": "social_validation",
                        "description": "可能需要更多社交认可",
                        "confidence": 0.7,
                    })

        return needs

    def _infer_attachment_style(
        self,
        vector: UserVectorDB,
        behavior_stats: Dict[str, Any]
    ) -> str:
        """推断依恋风格"""
        event_counts = behavior_stats.get("event_type_counts", {})

        # 简化推断逻辑
        chat_frequency = event_counts.get("chat_initiated", 0) + event_counts.get("chat_replied", 0)
        response_rate = event_counts.get("chat_replied", 0) / max(chat_frequency, 1)

        if response_rate > 0.8 and chat_frequency > 20:
            return "secure"
        elif response_rate < 0.3:
            return "avoidant"
        elif chat_frequency > 30 and response_rate > 0.9:
            return "anxious"
        else:
            return "secure"  # 默认

    def _identify_relationship_patterns(
        self,
        behavior_stats: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """识别关系模式"""
        patterns = []

        event_counts = behavior_stats.get("event_type_counts", {})

        # 检查是否有频繁开始但很少完成约会
        dates_initiated = event_counts.get("date_suggested", 0)
        dates_completed = event_counts.get("date_completed", 0)

        if dates_initiated > 5 and dates_completed < 2:
            patterns.append({
                "pattern": "initiation_without_completion",
                "description": "倾向于发起约会但很少完成",
                "possible_reason": "可能是选择困难或期望过高",
            })

        return patterns

    def _determine_emotional_tendency(self, vector: UserVectorDB) -> str:
        """确定情感倾向"""
        # 简化实现：基于向量平均值
        if vector.communication_style_vector:
            comm = json.loads(vector.communication_style_vector)
            avg = sum(comm) / len(comm) if comm else 0

            if avg > 0.3:
                return "positive"
            elif avg < -0.3:
                return "negative"
            else:
                return "neutral"

        return "neutral"

    def _generate_growth_suggestions(
        self,
        subconscious_traits: List[str],
        hidden_needs: List[Dict],
        attachment_style: str,
    ) -> List[Dict[str, str]]:
        """生成成长建议"""
        suggestions = []

        # 基于依恋风格的建议
        if attachment_style == "anxious":
            suggestions.append({
                "category": "attachment",
                "suggestion": "尝试建立自我价值感，减少对他人的过度依赖",
                "priority": "high",
            })
        elif attachment_style == "avoidant":
            suggestions.append({
                "category": "attachment",
                "suggestion": "尝试逐步开放自己，接受适度的亲密关系",
                "priority": "high",
            })

        # 基于潜意识特征的建议
        if "validation_seeking" in subconscious_traits:
            suggestions.append({
                "category": "self_esteem",
                "suggestion": "建立内在价值感，减少对外部认可的依赖",
                "priority": "medium",
            })

        return suggestions

    def _calculate_confidence_score(
        self,
        vector: UserVectorDB,
        behavior_stats: Dict[str, Any]
    ) -> float:
        """计算置信度分数"""
        score = 0.5  # 基础分数

        # 基于行为数量增加置信度
        behavior_count = behavior_stats.get("total_behaviors", 0)
        score += min(0.3, behavior_count / 100)

        # 基于向量完整度
        vector_fields = [vector.values_vector, vector.interests_vector,
                        vector.communication_style_vector, vector.behavior_pattern_vector]
        complete_vectors = sum(1 for v in vector_fields if v is not None)
        score += (complete_vectors / 4) * 0.2

        return min(1.0, score)

    def get_digital_subconscious_profile(
        self, user_id: str
    ) -> Optional[DigitalSubconsciousProfileDB]:
        """获取用户数字潜意识画像"""
        return self.db.query(DigitalSubconsciousProfileDB).filter(
            DigitalSubconsciousProfileDB.user_id == user_id
        ).first()

    # ============= 行为 - 向量映射 =============

    def get_behavior_mapping(self, behavior_type: str) -> Optional[BehaviorVectorMappingDB]:
        """获取行为 - 向量映射规则"""
        return self.db.query(BehaviorVectorMappingDB).filter(
            BehaviorVectorMappingDB.behavior_type == behavior_type,
            BehaviorVectorMappingDB.is_active == True,
        ).first()

    def register_behavior_mapping(
        self,
        behavior_type: str,
        affected_vector_types: List[str],
        mapping_rules: Dict[str, Any],
        impact_weights: Optional[Dict[str, float]] = None,
    ) -> BehaviorVectorMappingDB:
        """注册行为 - 向量映射规则"""
        existing = self.db.query(BehaviorVectorMappingDB).filter(
            BehaviorVectorMappingDB.behavior_type == behavior_type
        ).first()

        if existing:
            existing.affected_vector_types = json.dumps(affected_vector_types)
            existing.mapping_rules = json.dumps(mapping_rules)
            existing.impact_weights = json.dumps(impact_weights or {})
            existing.updated_at = datetime.now()
            record = existing
        else:
            record = BehaviorVectorMappingDB(
                id=str(uuid.uuid4()),
                behavior_type=behavior_type,
                affected_vector_types=json.dumps(affected_vector_types),
                mapping_rules=json.dumps(mapping_rules),
                impact_weights=json.dumps(impact_weights or {}),
            )
            self.db.add(record)

        self.db.commit()
        self.db.refresh(record)
        return record


# ============================================
# 工具函数
# ============================================

def get_vector_dimension_name(vector_type: str) -> str:
    """获取向量类型中文名称"""
    names = {
        "values": "价值观向量",
        "interests": "兴趣偏好向量",
        "communication_style": "沟通风格向量",
        "behavior_pattern": "行为模式向量",
    }
    return names.get(vector_type, vector_type)


def get_subconscious_trait_description(trait: str) -> str:
    """获取潜意识特征描述"""
    return SUBCONSCIOUS_TRAITS_LIBRARY.get(trait, "未知特征")


def get_attachment_style_description(style: str) -> str:
    """获取依恋风格描述"""
    return ATTACHMENT_STYLE_DESCRIPTIONS.get(style, "未知风格")
