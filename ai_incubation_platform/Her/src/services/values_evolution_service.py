"""
Values: 价值观演化追踪服务

从"静态标签匹配"转向"动态共鸣演算法"的核心服务。

功能包括：
- 价值观声明管理
- 从行为推断价值观
- 价值观偏移计算
- 匹配权重调整
- 用户通知生成
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import json
import uuid
import math

from models.values_models import (
    DeclaredValuesDB,
    InferredValuesDB,
    ValuesDriftDB,
    ValuesEvolutionHistoryDB,
    MatchingWeightAdjustmentDB,
    VALUES_DIMENSIONS,
    VALUES_OPTIONS,
    DRIFT_SEVERITY_THRESHOLDS,
    DRIFT_DIRECTION_RULES,
    SUGGESTED_ACTION_RULES,
)
from db.models import BehaviorEventDB
from services.base_service import BaseService


# ============= 价值观推断规则 =============

# 浏览行为推断规则
BROWSE_BEHAVIOR_RULES = {
    "viewed_profile_with_tag": {
        "tag": "career_focused",
        "inference": {"career_view": "career_focused", "weight": 0.1},
    },
    "viewed_profile_with_tag": {
        "tag": "family_oriented",
        "inference": {"career_view": "family_focused", "weight": 0.1},
    },
    "viewed_profile_with_income_range": {
        "range": "high",
        "inference": {"consumption_view": "generous", "weight": 0.15},
    },
    "viewed_profile_with_income_range": {
        "range": "low",
        "inference": {"consumption_view": "frugal", "weight": 0.15},
    },
}

# 互动行为推断规则
INTERACTION_BEHAVIOR_RULES = {
    "chat_frequency_high": {"social_view": "extroverted", "weight": 0.2},
    "chat_frequency_low": {"social_view": "introverted", "weight": 0.2},
    "chat_topic_preference": {
        "topic": "career",
        "inference": {"career_view": "career_focused", "weight": 0.15},
    },
    "chat_topic_preference": {
        "topic": "family",
        "inference": {"career_view": "family_focused", "weight": 0.15},
    },
}

# 约会行为推断规则
DATE_BEHAVIOR_RULES = {
    "date_location_type": {
        "type": "adventure",
        "inference": {"risk_preference": "risk_seeking", "weight": 0.2},
    },
    "date_location_type": {
        "type": "relaxed",
        "inference": {"life_pace": "slow", "weight": 0.2},
    },
    "date_activity_preference": {
        "type": "social_gathering",
        "inference": {"social_view": "extroverted", "weight": 0.2},
    },
    "date_activity_preference": {
        "type": "quiet_time",
        "inference": {"social_view": "introverted", "weight": 0.2},
    },
}


class ValuesEvolutionService(BaseService):
    """价值观演化追踪服务"""

    def __init__(self, db: Session):
        super().__init__(db)

    # ============= 价值观声明管理 =============

    def set_declared_values(
        self,
        user_id: str,
        values_data: Dict[str, str],
        source: str = "questionnaire",
    ) -> DeclaredValuesDB:
        """
        设置用户声明的价值观

        Args:
            user_id: 用户 ID
            values_data: 价值观数据，如 {"family_view": "traditional", "career_view": "balanced"}
            source: 来源 (questionnaire/interview/ai_inferred)

        Returns:
            DeclaredValuesDB: 创建的记录
        """
        # 验证价值观数据
        self._validate_values_data(values_data)

        # 检查是否已存在
        existing = self.db.query(DeclaredValuesDB).filter(
            DeclaredValuesDB.user_id == user_id
        ).first()

        if existing:
            # 记录演化历史
            self._record_evolution(
                user_id=user_id,
                evolution_type="values_updated",
                before_state=json.loads(existing.values_data),
                after_state=values_data,
                evolution_reason="用户更新价值观声明",
            )

            # 更新现有记录
            existing.values_data = json.dumps(values_data)
            existing.source = source
            existing.updated_at = datetime.now()
            existing.last_assessed_at = datetime.now()
            record = existing
        else:
            # 创建新记录
            record = DeclaredValuesDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                values_data=json.dumps(values_data),
                source=source,
                confidence_score=0.8 if source == "questionnaire" else 0.5,
                last_assessed_at=datetime.now(),
            )
            self.db.add(record)

        self.db.commit()
        self.db.refresh(record)
        return record

    def get_declared_values(self, user_id: str) -> Optional[Dict[str, str]]:
        """获取用户声明的价值观"""
        record = self.db.query(DeclaredValuesDB).filter(
            DeclaredValuesDB.user_id == user_id
        ).first()

        if not record:
            return None

        return json.loads(record.values_data)

    def _validate_values_data(self, values_data: Dict[str, str]):
        """验证价值观数据"""
        for dimension, value in values_data.items():
            if dimension not in VALUES_DIMENSIONS:
                raise ValueError(f"Invalid values dimension: {dimension}")
            if value not in VALUES_OPTIONS.get(dimension, []):
                raise ValueError(f"Invalid value '{value}' for dimension '{dimension}'")

    # ============= 从行为推断价值观 =============

    def infer_values_from_behavior(
        self,
        user_id: str,
        days: int = 30,
    ) -> InferredValuesDB:
        """
        从用户行为推断价值观

        Args:
            user_id: 用户 ID
            days: 分析周期（天数）

        Returns:
            InferredValuesDB: 推断结果
        """
        # 获取近期行为
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        behaviors = self.db.query(BehaviorEventDB).filter(
            and_(
                BehaviorEventDB.user_id == user_id,
                BehaviorEventDB.created_at >= start_date,
                BehaviorEventDB.created_at <= end_date,
            )
        ).all()

        if not behaviors:
            # 无行为数据，返回默认推断
            return self._create_default_inferred_values(user_id, start_date, end_date)

        # 分析行为，推断价值观
        inferred_scores = self._analyze_behaviors(behaviors)

        # 转换为价值观选项
        inferred_values = self._scores_to_values(inferred_scores)

        # 生成行为证据
        behavior_evidence = self._extract_behavior_evidence(behaviors)

        # 计算置信度
        confidence_score = min(0.9, 0.3 + (len(behaviors) / 100) * 0.6)

        # 创建记录
        record = InferredValuesDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            values_data=json.dumps(inferred_values),
            behavior_evidence=json.dumps(behavior_evidence),
            confidence_score=confidence_score,
            analysis_start_date=start_date,
            analysis_end_date=end_date,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        return record

    def _create_default_inferred_values(
        self, user_id: str, start_date: datetime, end_date: datetime
    ) -> InferredValuesDB:
        """创建默认推断值（无行为数据时）"""
        default_values = {
            dim: VALUES_OPTIONS[dim][1]  # 默认选择中间值
            for dim in VALUES_DIMENSIONS
        }

        record = InferredValuesDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            values_data=json.dumps(default_values),
            behavior_evidence=json.dumps({"note": "无足够行为数据"}),
            confidence_score=0.2,
            analysis_start_date=start_date,
            analysis_end_date=end_date,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def _analyze_behaviors(
        self, behaviors: List[BehaviorEventDB]
    ) -> Dict[str, Dict[str, float]]:
        """
        分析行为，计算各价值观维度的得分

        Returns:
            Dict: 各维度各选项的得分，如 {"career_view": {"career_focused": 0.6, "family_focused": 0.4}}
        """
        # 初始化得分
        scores = {
            dim: {opt: 0.0 for opt in OPTIONS}
            for dim, OPTIONS in VALUES_OPTIONS.items()
        }

        total_weight = 0.0

        for behavior in behaviors:
            event_type = behavior.event_type
            event_data = json.loads(behavior.event_data or "{}")

            # 根据行为类型和数据进行推断
            if event_type == "viewed_profile":
                # 浏览行为
                profile_tags = event_data.get("profile_tags", [])
                for tag in profile_tags:
                    if "career" in tag.lower():
                        scores["career_view"]["career_focused"] += 0.1
                        total_weight += 0.1
                    elif "family" in tag.lower():
                        scores["career_view"]["family_focused"] += 0.1
                        total_weight += 0.1

            elif event_type == "chat_initiated":
                # 主动发起聊天
                scores["social_view"]["extroverted"] += 0.05
                total_weight += 0.05

            elif event_type == "date_completed":
                # 约会完成
                date_type = event_data.get("date_type", "")
                if date_type in ["adventure", "outdoor"]:
                    scores["risk_preference"]["risk_seeking"] += 0.15
                    total_weight += 0.15
                elif date_type in ["quiet", "home"]:
                    scores["life_pace"]["slow"] += 0.15
                    scores["social_view"]["introverted"] += 0.1
                    total_weight += 0.25

            elif event_type == "gift_sent":
                # 发送礼物
                gift_value = event_data.get("gift_value", 0)
                if gift_value > 500:
                    scores["consumption_view"]["generous"] += 0.2
                    total_weight += 0.2
                elif gift_value < 100:
                    scores["consumption_view"]["frugal"] += 0.2
                    total_weight += 0.2

        # 归一化得分
        if total_weight > 0:
            for dim in scores:
                dim_total = sum(scores[dim].values())
                if dim_total > 0:
                    for opt in scores[dim]:
                        scores[dim][opt] /= dim_total

        return scores

    def _scores_to_values(
        self, scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, str]:
        """将得分转换为价值观选项"""
        values = {}

        for dim, opt_scores in scores.items():
            # 选择得分最高的选项
            best_option = max(opt_scores, key=opt_scores.get)
            values[dim] = best_option

        return values

    def _extract_behavior_evidence(
        self, behaviors: List[BehaviorEventDB]
    ) -> Dict[str, Any]:
        """提取行为证据"""
        evidence = {
            "total_behaviors": len(behaviors),
            "event_type_counts": {},
            "sample_events": [],
        }

        # 统计事件类型
        for behavior in behaviors:
            event_type = behavior.event_type
            evidence["event_type_counts"][event_type] = \
                evidence["event_type_counts"].get(event_type, 0) + 1

            # 保留样本事件
            if len(evidence["sample_events"]) < 5:
                evidence["sample_events"].append({
                    "event_type": behavior.event_type,
                    "created_at": behavior.created_at.isoformat() if behavior.created_at else None,
                })

        return evidence

    def get_inferred_values(self, user_id: str) -> Optional[Dict[str, str]]:
        """获取用户推断的价值观"""
        record = self.db.query(InferredValuesDB).filter(
            InferredValuesDB.user_id == user_id
        ).order_by(desc(InferredValuesDB.created_at)).first()

        if not record:
            return None

        return json.loads(record.values_data)

    # ============= 价值观偏移计算 =============

    def calculate_values_drift(self, user_id: str) -> List[ValuesDriftDB]:
        """
        计算用户价值观偏移

        Args:
            user_id: 用户 ID

        Returns:
            List[ValuesDriftDB]: 偏移记录列表
        """
        # 获取声明的价值观
        declared = self.get_declared_values(user_id)
        if not declared:
            return []

        # 获取推断的价值观
        inferred = self.get_inferred_values(user_id)
        if not inferred:
            return []

        drift_records = []

        for dimension in VALUES_DIMENSIONS:
            declared_value = declared.get(dimension)
            inferred_value = inferred.get(dimension)

            if not declared_value or not inferred_value:
                continue

            # 计算偏移分数
            drift_score = self._calculate_dimension_drift(
                dimension, declared_value, inferred_value
            )

            # 判定偏移方向
            drift_direction = self._determine_drift_direction(
                dimension, declared_value, inferred_value
            )

            # 判定偏移严重程度
            drift_severity = self._determine_drift_severity(drift_score)

            # 建议操作
            suggested_action = SUGGESTED_ACTION_RULES.get(drift_severity, "none")

            # 生成描述
            drift_description = self._generate_drift_description(
                dimension, declared_value, inferred_value, drift_score
            )

            # 创建或更新偏移记录
            existing = self.db.query(ValuesDriftDB).filter(
                and_(
                    ValuesDriftDB.user_id == user_id,
                    ValuesDriftDB.drift_dimension == dimension,
                )
            ).first()

            if existing:
                existing.drift_score = drift_score
                existing.current_value = inferred_value
                existing.drift_direction = drift_direction
                existing.drift_severity = drift_severity
                existing.drift_description = drift_description
                existing.suggested_action = suggested_action
                existing.updated_at = datetime.now()
                drift_records.append(existing)
            else:
                record = ValuesDriftDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    drift_dimension=dimension,
                    original_value=declared_value,
                    current_value=inferred_value,
                    drift_score=drift_score,
                    drift_direction=drift_direction,
                    drift_severity=drift_severity,
                    drift_description=drift_description,
                    suggested_action=suggested_action,
                )
                self.db.add(record)
                drift_records.append(record)

        self.db.commit()
        return drift_records

    def _calculate_dimension_drift(
        self, dimension: str, declared_value: str, inferred_value: str
    ) -> float:
        """
        计算单个维度的偏移分数

        同一维度内不同选项之间的距离：
        - 相同选项：0.0
        - 相邻选项：0.5
        - 相对选项：1.0
        """
        if declared_value == inferred_value:
            return 0.0

        options = VALUES_OPTIONS.get(dimension, [])
        if not options:
            return 0.5

        try:
            declared_idx = options.index(declared_value)
            inferred_idx = options.index(inferred_value)

            # 计算索引距离（归一化到 0-1）
            max_distance = len(options) - 1
            distance = abs(declared_idx - inferred_idx)

            return distance / max_distance if max_distance > 0 else 1.0
        except ValueError:
            return 0.5  # 无法解析时返回默认值

    def _determine_drift_direction(
        self, dimension: str, declared_value: str, inferred_value: str
    ) -> str:
        """判定偏移方向"""
        key = (declared_value, inferred_value)
        return DRIFT_DIRECTION_RULES.get(key, "neutral")

    def _determine_drift_severity(self, drift_score: float) -> str:
        """判定偏移严重程度"""
        for severity, (min_score, max_score) in DRIFT_SEVERITY_THRESHOLDS.items():
            if min_score <= drift_score < max_score:
                return severity
        return "slight"

    def _generate_drift_description(
        self, dimension: str, declared_value: str, inferred_value: str, drift_score: float
    ) -> str:
        """生成偏移描述"""
        dimension_names = {
            "family_view": "家庭观念",
            "career_view": "事业观念",
            "consumption_view": "消费观念",
            "social_view": "社交观念",
            "life_pace": "生活节奏",
            "risk_preference": "风险偏好",
        }

        value_names = {
            "traditional": "传统型",
            "liberal": "开放型",
            "balanced": "平衡型",
            "career_focused": "事业优先",
            "family_focused": "家庭优先",
            "frugal": "节俭型",
            "generous": "享受型",
            "moderate": "适度型",
            "introverted": "内向型",
            "extroverted": "外向型",
            "ambivert": "中间型",
            "slow": "慢节奏",
            "fast": "快节奏",
            "risk_averse": "风险规避",
            "risk_seeking": "风险偏好",
        }

        dim_name = dimension_names.get(dimension, dimension)
        declared_name = value_names.get(declared_value, declared_value)
        inferred_name = value_names.get(inferred_value, inferred_value)

        return f'您的{dim_name}从"{declared_name}"转变为"{inferred_name}"，偏移程度为{drift_score:.2f}'

    def get_user_drifts(self, user_id: str) -> List[ValuesDriftDB]:
        """获取用户的价值观偏移记录"""
        return self.db.query(ValuesDriftDB).filter(
            ValuesDriftDB.user_id == user_id
        ).order_by(desc(ValuesDriftDB.drift_score)).all()

    # ============= 演化历史记录 =============

    def _record_evolution(
        self,
        user_id: str,
        evolution_type: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        evolution_reason: str,
        evolution_details: Optional[Dict[str, Any]] = None,
    ):
        """记录价值观演化历史"""
        record = ValuesEvolutionHistoryDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            evolution_type=evolution_type,
            before_state=json.dumps(before_state),
            after_state=json.dumps(after_state),
            evolution_reason=evolution_reason,
            evolution_details=json.dumps(evolution_details or {}),
        )
        self.db.add(record)
        self.db.commit()
        return record

    def get_evolution_history(
        self, user_id: str, limit: int = 20
    ) -> List[ValuesEvolutionHistoryDB]:
        """获取用户价值观演化历史"""
        return self.db.query(ValuesEvolutionHistoryDB).filter(
            ValuesEvolutionHistoryDB.user_id == user_id
        ).order_by(desc(ValuesEvolutionHistoryDB.created_at)).limit(limit).all()

    # ============= 匹配权重调整 =============

    def adjust_matching_weights(
        self,
        user_id: str,
        drift_records: List[ValuesDriftDB],
        adjustment_reason: str = "values_drift",
    ) -> Optional[MatchingWeightAdjustmentDB]:
        """
        根据价值观偏移调整匹配权重

        Args:
            user_id: 用户 ID
            drift_records: 偏移记录列表
            adjustment_reason: 调整原因

        Returns:
            MatchingWeightAdjustmentDB: 调整记录
        """
        # 获取显著及以上级别的偏移
        significant_drifts = [
            d for d in drift_records
            if d.drift_severity in ["significant", "severe"]
        ]

        if not significant_drifts:
            return None

        # 构建新的权重配置
        # 默认权重
        new_weights = {
            "family_view": 0.15,
            "career_view": 0.15,
            "consumption_view": 0.1,
            "social_view": 0.15,
            "life_pace": 0.1,
            "risk_preference": 0.1,
            "interests": 0.15,
            "demographics": 0.1,
        }

        # 根据偏移调整权重
        adjustment_details = {"adjusted_dimensions": []}

        for drift in significant_drifts:
            dim = drift.drift_dimension
            if dim in new_weights:
                # 增加该维度的权重（因为用户实际行为显示这很重要）
                old_weight = new_weights[dim]
                new_weights[dim] = min(0.3, old_weight * 1.5)  # 增加 50%，上限 30%
                adjustment_details["adjusted_dimensions"].append({
                    "dimension": dim,
                    "old_weight": old_weight,
                    "new_weight": new_weights[dim],
                    "reason": f"检测到{dim}显著偏移",
                })

        # 获取旧权重（从现有记录）
        existing = self.db.query(MatchingWeightAdjustmentDB).filter(
            MatchingWeightAdjustmentDB.user_id == user_id
        ).order_by(desc(MatchingWeightAdjustmentDB.created_at)).first()

        previous_weights = json.loads(existing.new_weights) if existing else {
            "family_view": 0.15,
            "career_view": 0.15,
            "consumption_view": 0.1,
            "social_view": 0.15,
            "life_pace": 0.1,
            "risk_preference": 0.1,
            "interests": 0.15,
            "demographics": 0.1,
        }

        # 创建调整记录
        record = MatchingWeightAdjustmentDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            adjustment_reason=adjustment_reason,
            previous_weights=json.dumps(previous_weights),
            new_weights=json.dumps(new_weights),
            adjustment_details=json.dumps(adjustment_details),
            is_active=True,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        return record

    def get_current_matching_weights(self, user_id: str) -> Dict[str, float]:
        """获取用户当前的匹配权重"""
        record = self.db.query(MatchingWeightAdjustmentDB).filter(
            and_(
                MatchingWeightAdjustmentDB.user_id == user_id,
                MatchingWeightAdjustmentDB.is_active == True,
            )
        ).order_by(desc(MatchingWeightAdjustmentDB.created_at)).first()

        if record:
            return json.loads(record.new_weights)

        # 返回默认权重
        return {
            "family_view": 0.15,
            "career_view": 0.15,
            "consumption_view": 0.1,
            "social_view": 0.15,
            "life_pace": 0.1,
            "risk_preference": 0.1,
            "interests": 0.15,
            "demographics": 0.1,
        }

    # ============= 综合追踪 =============

    def track_values_evolution(self, user_id: str) -> Dict[str, Any]:
        """
        执行完整的价值观演化追踪流程

        Args:
            user_id: 用户 ID

        Returns:
            Dict: 追踪结果
        """
        # 1. 从行为推断价值观
        inferred = self.infer_values_from_behavior(user_id, days=30)

        # 2. 计算价值观偏移
        drift_records = self.calculate_values_drift(user_id)

        # 3. 调整匹配权重
        weight_adjustment = self.adjust_matching_weights(user_id, drift_records)

        # 4. 生成通知
        notifications = self._generate_notifications(drift_records)

        return {
            "inferred_values": json.loads(inferred.values_data),
            "drift_records": [
                {
                    "dimension": d.drift_dimension,
                    "drift_score": d.drift_score,
                    "drift_severity": d.drift_severity,
                    "suggested_action": d.suggested_action,
                }
                for d in drift_records
            ],
            "weight_adjustment": json.loads(weight_adjustment.adjustment_details) if weight_adjustment else None,
            "notifications": notifications,
        }

    def _generate_notifications(
        self, drift_records: List[ValuesDriftDB]
    ) -> List[Dict[str, Any]]:
        """生成用户通知"""
        notifications = []

        for drift in drift_records:
            if drift.suggested_action in ["notify_user", "adjust_recommendation", "review"]:
                notifications.append({
                    "type": "values_shift_detected",
                    "dimension": drift.drift_dimension,
                    "message": drift.drift_description,
                    "action_required": drift.suggested_action == "review",
                })

        return notifications


# ============================================
# 工具函数
# ============================================

def get_dimension_name(dimension: str) -> str:
    """获取维度中文名称"""
    names = {
        "family_view": "家庭观念",
        "career_view": "事业观念",
        "consumption_view": "消费观念",
        "social_view": "社交观念",
        "life_pace": "生活节奏",
        "risk_preference": "风险偏好",
    }
    return names.get(dimension, dimension)


def get_value_name(value: str) -> str:
    """获取价值观选项中文名称"""
    names = {
        "traditional": "传统型",
        "liberal": "开放型",
        "balanced": "平衡型",
        "career_focused": "事业优先",
        "family_focused": "家庭优先",
        "frugal": "节俭型",
        "generous": "享受型",
        "moderate": "适度型",
        "introverted": "内向型",
        "extroverted": "外向型",
        "ambivert": "中间型",
        "slow": "慢节奏",
        "fast": "快节奏",
        "risk_averse": "风险规避",
        "risk_seeking": "风险偏好",
    }
    return names.get(value, value)
