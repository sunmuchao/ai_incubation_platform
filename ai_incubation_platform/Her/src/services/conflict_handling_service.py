"""
P1: 冲突处理服务

从"静态标签匹配"转向"动态共鸣演算法"的核心服务。

功能包括：
- 冲突处理风格评估
- 冲突兼容性计算
- 冲突化解建议生成
- 沟通模式分析
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import json
import uuid

from models.p1_conflict_models import (
    ConflictStyleDB,
    ConflictHistoryDB,
    ConflictCompatibilityDB,
    ConflictResolutionTipDB,
    CommunicationPatternDB,
)
from models.p17_models import TrustScoreDB


# ============= 冲突处理风格兼容性矩阵 =============
# 基于"从静态标签匹配转向动态共鸣演算法"设计理念

COMPATIBILITY_MATRIX = {
    # 回避型 vs 其他
    ("avoiding", "avoiding"): 0.4,      # 问题累积，双方都不愿面对
    ("avoiding", "competing"): 0.3,     # 矛盾升级，一方逃避一方进攻
    ("avoiding", "accommodating"): 0.6, # 可调和，迁就型会主动沟通
    ("avoiding", "compromising"): 0.65, # 可调和，妥协型会引导
    ("avoiding", "collaborating"): 0.7, # 可调和，协商型会耐心引导

    # 对抗型 vs 其他
    ("competing", "avoiding"): 0.3,     # 矛盾升级
    ("competing", "competing"): 0.2,    # 激烈冲突，双方都不让步
    ("competing", "accommodating"): 0.5, # 迁就型会忍让但容易积累不满
    ("competing", "compromising"): 0.55, # 妥协型会尝试调和
    ("competing", "collaborating"): 0.6, # 协商型会尝试理解对抗背后的需求

    # 迁就型 vs 其他
    ("accommodating", "avoiding"): 0.6,
    ("accommodating", "competing"): 0.5,
    ("accommodating", "accommodating"): 0.7, # 双方都让步，但可能缺乏深度交流
    ("accommodating", "compromising"): 0.75, # 良好的组合
    ("accommodating", "collaborating"): 0.8, # 协商型能帮助迁就型表达真实需求

    # 妥协型 vs 其他
    ("compromising", "avoiding"): 0.65,
    ("compromising", "competing"): 0.55,
    ("compromising", "accommodating"): 0.75,
    ("compromising", "compromising"): 0.8,   # 双方都愿意折中
    ("compromising", "collaborating"): 0.85, # 很好的组合

    # 协商型 vs 其他
    ("collaborating", "avoiding"): 0.7,
    ("collaborating", "competing"): 0.6,
    ("collaborating", "accommodating"): 0.8,
    ("collaborating", "compromising"): 0.85,
    ("collaborating", "collaborating"): 0.9, # 理想组合，共同解决问题
}

# 冲突处理风格中文名称
STYLE_NAMES = {
    "avoiding": "回避型",
    "competing": "对抗型",
    "accommodating": "迁就型",
    "compromising": "妥协型",
    "collaborating": "协商型",
}

# 各风格的详细描述
STYLE_DESCRIPTIONS = {
    "avoiding": "倾向于避免正面冲突，可能会压抑自己的想法和感受，等待问题自行消失。优点是能保持表面和谐，缺点是问题可能累积。",
    "competing": "倾向于坚持己见，视冲突为竞争，力求获胜。优点是能明确表达立场，缺点是可能伤害关系。",
    "accommodating": "倾向于迁就对方，将对方需求置于自己之上。优点是体现关爱，缺点是可能积累不满。",
    "compromising": "倾向于寻找中间地带，双方各让一步。优点是快速解决，缺点是可能双方都不完全满意。",
    "collaborating": "倾向于深入探讨问题根源，寻求双赢解决方案。优点是彻底解决问题，缺点是需要较多时间和精力。",
}


class ConflictHandlingService:
    """冲突处理服务"""

    def __init__(self, db: Session):
        self.db = db

    # ============= 冲突处理风格评估 =============

    def assess_conflict_style(
        self,
        user_id: str,
        avoiding_score: int = 0,
        competing_score: int = 0,
        accommodating_score: int = 0,
        compromising_score: int = 0,
        collaborating_score: int = 0,
        conflict_triggers: Optional[List[str]] = None,
        assessment_method: str = "questionnaire"
    ) -> ConflictStyleDB:
        """
        评估用户冲突处理风格

        Args:
            user_id: 用户 ID
            avoiding_score: 回避型得分 (0-100)
            competing_score: 对抗型得分 (0-100)
            accommodating_score: 迁就型得分 (0-100)
            compromising_score: 妥协型得分 (0-100)
            collaborating_score: 协商型得分 (0-100)
            conflict_triggers: 冲突触发点列表
            assessment_method: 评估方式 (questionnaire/behavior_analysis/ai_assessment)

        Returns:
            ConflictStyleDB: 创建的风格记录
        """
        # 计算主要风格
        scores = {
            "avoiding": avoiding_score,
            "competing": competing_score,
            "accommodating": accommodating_score,
            "compromising": compromising_score,
            "collaborating": collaborating_score,
        }
        primary_style = max(scores, key=scores.get)

        # 生成风格描述
        style_description = self._generate_style_description(
            primary_style, scores
        )

        # 创建或更新记录
        existing = self.db.query(ConflictStyleDB).filter(
            ConflictStyleDB.user_id == user_id
        ).first()

        if existing:
            # 更新现有记录
            existing.primary_style = primary_style
            existing.avoiding_score = avoiding_score
            existing.competing_score = competing_score
            existing.accommodating_score = accommodating_score
            existing.compromising_score = compromising_score
            existing.collaborating_score = collaborating_score
            existing.style_description = style_description
            existing.conflict_triggers = json.dumps(conflict_triggers or [])
            existing.assessment_method = assessment_method
            existing.updated_at = datetime.now()
            existing.last_assessed_at = datetime.now()
            record = existing
        else:
            # 创建新记录
            record = ConflictStyleDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                primary_style=primary_style,
                avoiding_score=avoiding_score,
                competing_score=competing_score,
                accommodating_score=accommodating_score,
                compromising_score=compromising_score,
                collaborating_score=collaborating_score,
                style_description=style_description,
                conflict_triggers=json.dumps(conflict_triggers or []),
                assessment_method=assessment_method,
                last_assessed_at=datetime.now(),
            )
            self.db.add(record)

        self.db.commit()
        self.db.refresh(record)
        return record

    def _generate_style_description(
        self, primary_style: str, scores: Dict[str, int]
    ) -> str:
        """生成风格描述"""
        # 排序得分
        sorted_styles = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # 构建描述
        desc_parts = []
        for style, score in sorted_styles[:3]:  # 只显示前 3 个
            if score > 30:  # 只显示显著的风格
                style_name = STYLE_NAMES[style]
                desc_parts.append(f"{style_name}({score}分)")

        base_desc = STYLE_DESCRIPTIONS[primary_style]
        return f"主要风格：{STYLE_NAMES[primary_style]}。次要倾向：{', '.join(desc_parts[1:]) if len(desc_parts) > 1 else '无明显次要倾向'}。{base_desc}"

    def get_user_conflict_style(self, user_id: str) -> Optional[ConflictStyleDB]:
        """获取用户冲突处理风格"""
        return self.db.query(ConflictStyleDB).filter(
            ConflictStyleDB.user_id == user_id
        ).first()

    # ============= 冲突兼容性评估 =============

    def calculate_conflict_compatibility(
        self,
        user_a_id: str,
        user_b_id: str,
    ) -> ConflictCompatibilityDB:
        """
        计算双方冲突兼容性

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID

        Returns:
            ConflictCompatibilityDB: 兼容性评估记录
        """
        # 获取双方冲突风格
        style_a = self.get_user_conflict_style(user_a_id)
        style_b = self.get_user_conflict_style(user_b_id)

        if not style_a or not style_b:
            # 如果一方没有评估结果，返回默认兼容性
            return self._create_default_compatibility(user_a_id, user_b_id)

        # 计算风格兼容性
        style_key = (style_a.primary_style, style_b.primary_style)
        style_compatibility = COMPATIBILITY_MATRIX.get(style_key, 0.5)

        # 计算触发点兼容性
        triggers_a = json.loads(style_a.conflict_triggers or "[]")
        triggers_b = json.loads(style_b.conflict_triggers or "[]")
        trigger_compatibility = self._calculate_trigger_compatibility(
            triggers_a, triggers_b
        )

        # 计算解决方式兼容性（基于历史冲突处理效果）
        resolution_compatibility = self._calculate_resolution_compatibility(
            user_a_id, user_b_id
        )

        # 计算总体兼容性
        overall_compatibility = (
            style_compatibility * 0.5 +  # 风格兼容性占 50%
            trigger_compatibility * 0.3 +  # 触发点兼容性占 30%
            resolution_compatibility * 0.2  # 解决方式兼容性占 20%
        )

        # 生成兼容性详情
        compatibility_details = {
            "style_a": STYLE_NAMES[style_a.primary_style],
            "style_b": STYLE_NAMES[style_b.primary_style],
            "style_compatibility": round(style_compatibility, 2),
            "trigger_compatibility": round(trigger_compatibility, 2),
            "resolution_compatibility": round(resolution_compatibility, 2),
        }

        # 识别风险因素
        risk_factors = self._identify_risk_factors(
            style_a.primary_style, style_b.primary_style, triggers_a, triggers_b
        )

        # 生成建议
        suggestions = self._generate_compatibility_suggestions(
            style_a.primary_style, style_b.primary_style
        )

        # 创建或更新记录
        existing = self.db.query(ConflictCompatibilityDB).filter(
            and_(
                ConflictCompatibilityDB.user_a_id == user_a_id,
                ConflictCompatibilityDB.user_b_id == user_b_id
            )
        ).first()

        if existing:
            existing.compatibility_score = overall_compatibility
            existing.style_compatibility = style_compatibility
            existing.trigger_compatibility = trigger_compatibility
            existing.resolution_compatibility = resolution_compatibility
            existing.compatibility_details = json.dumps(compatibility_details)
            existing.risk_factors = json.dumps(risk_factors)
            existing.suggestions = json.dumps(suggestions)
            existing.updated_at = datetime.now()
            record = existing
        else:
            # 注意：user_a_id 和 user_b_id 需要排序以保证唯一性
            if user_a_id > user_b_id:
                user_a_id, user_b_id = user_b_id, user_a_id

            record = ConflictCompatibilityDB(
                id=str(uuid.uuid4()),
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                compatibility_score=overall_compatibility,
                style_compatibility=style_compatibility,
                trigger_compatibility=trigger_compatibility,
                resolution_compatibility=resolution_compatibility,
                compatibility_details=json.dumps(compatibility_details),
                risk_factors=json.dumps(risk_factors),
                suggestions=json.dumps(suggestions),
            )
            self.db.add(record)

        self.db.commit()
        self.db.refresh(record)
        return record

    def _create_default_compatibility(
        self, user_a_id: str, user_b_id: str
    ) -> ConflictCompatibilityDB:
        """创建默认兼容性记录（当一方无评估结果时）"""
        if user_a_id > user_b_id:
            user_a_id, user_b_id = user_b_id, user_a_id

        record = ConflictCompatibilityDB(
            id=str(uuid.uuid4()),
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            compatibility_score=0.5,
            style_compatibility=0.5,
            trigger_compatibility=0.5,
            resolution_compatibility=0.5,
            compatibility_details=json.dumps({"note": "等待双方完成冲突风格评估"}),
            risk_factors=json.dumps(["需要完成冲突风格评估"]),
            suggestions=json.dumps([
                "建议双方完成冲突处理风格评估以获取更准确的兼容性分析"
            ]),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def _calculate_trigger_compatibility(
        self, triggers_a: List[str], triggers_b: List[str]
    ) -> float:
        """计算触发点兼容性"""
        if not triggers_a or not triggers_b:
            return 0.5  # 无数据时返回默认值

        # 计算重叠的触发点
        overlap = set(triggers_a) & set(triggers_b)

        if len(overlap) == 0:
            # 无重叠触发点，兼容性较高
            return 0.8
        elif len(overlap) <= 1:
            # 少量重叠，兼容性中等
            return 0.6
        else:
            # 多个重叠触发点，兼容性较低
            return 0.4

    def _calculate_resolution_compatibility(
        self, user_a_id: str, user_b_id: str
    ) -> float:
        """计算解决方式兼容性（基于历史冲突处理效果）"""
        # 查询双方的冲突历史
        histories_a = self.db.query(ConflictHistoryDB).filter(
            ConflictHistoryDB.user_id == user_a_id
        ).order_by(ConflictHistoryDB.created_at.desc()).limit(10).all()

        histories_b = self.db.query(ConflictHistoryDB).filter(
            ConflictHistoryDB.user_id == user_b_id
        ).order_by(ConflictHistoryDB.created_at.desc()).limit(10).all()

        if not histories_a and not histories_b:
            return 0.5  # 无历史数据

        # 计算平均处理效果
        all_histories = histories_a + histories_b
        if not all_histories:
            return 0.5

        avg_effectiveness = sum(
            h.handling_effectiveness or 5 for h in all_histories
        ) / len(all_histories)

        # 转换为 0-1 的分数
        return avg_effectiveness / 10.0

    def _identify_risk_factors(
        self,
        style_a: str,
        style_b: str,
        triggers_a: List[str],
        triggers_b: List[str]
    ) -> List[Dict[str, Any]]:
        """识别风险因素"""
        risk_factors = []

        # 风格组合风险
        if (style_a, style_b) in [("avoiding", "avoiding"), ("competing", "competing")]:
            risk_factors.append({
                "type": "style_mismatch",
                "level": "high" if style_a == "competing" else "medium",
                "description": f"双方都是{STYLE_NAMES[style_a]}，可能导致问题累积或冲突升级",
            })

        if (style_a, style_b) == ("avoiding", "competing") or \
           (style_a, style_b) == ("competing", "avoiding"):
            risk_factors.append({
                "type": "style_mismatch",
                "level": "high",
                "description": "回避型与对抗型的组合可能导致矛盾升级",
            })

        # 触发点重叠风险
        overlap = set(triggers_a) & set(triggers_b)
        if overlap:
            risk_factors.append({
                "type": "trigger_overlap",
                "level": "medium",
                "description": f"双方在以下话题上容易引发冲突：{', '.join(overlap)}",
            })

        return risk_factors

    def _generate_compatibility_suggestions(
        self, style_a: str, style_b: str
    ) -> List[Dict[str, Any]]:
        """生成兼容性建议"""
        suggestions = []

        # 根据风格组合生成建议
        if style_a == "collaborating" and style_b == "collaborating":
            suggestions.append({
                "type": "strength",
                "content": "双方都倾向于协商解决，这是理想组合。继续保持开放沟通的习惯。",
            })
        elif style_a == "avoiding" and style_b == "collaborating":
            suggestions.append({
                "type": "growth",
                "content": "协商型的一方可以帮助回避型的一方逐步表达真实想法，不要急于求成。",
            })
        elif style_a == "competing" and style_b == "competing":
            suggestions.append({
                "type": "warning",
                "content": "双方都倾向于对抗，建议约定'冷静期'机制，在情绪激动时暂停讨论。",
            })
        elif (style_a == "avoiding" and style_b == "avoiding"):
            suggestions.append({
                "type": "warning",
                "content": "双方都回避冲突可能导致问题累积。建议定期进行'关系检查'，主动讨论潜在问题。",
            })

        # 通用建议
        suggestions.append({
            "type": "general",
            "content": "了解彼此的冲突处理风格是改善关系的第一步。风格没有对错，关键是相互理解和适应。",
        })

        return suggestions

    def get_conflict_compatibility(
        self, user_a_id: str, user_b_id: str
    ) -> Optional[ConflictCompatibilityDB]:
        """获取双方冲突兼容性"""
        # 尝试两种顺序
        result = self.db.query(ConflictCompatibilityDB).filter(
            and_(
                ConflictCompatibilityDB.user_a_id == user_a_id,
                ConflictCompatibilityDB.user_b_id == user_b_id
            )
        ).first()

        if not result:
            result = self.db.query(ConflictCompatibilityDB).filter(
                and_(
                    ConflictCompatibilityDB.user_a_id == user_b_id,
                    ConflictCompatibilityDB.user_b_id == user_a_id
                )
            ).first()

        return result

    # ============= 冲突历史追踪 =============

    def record_conflict(
        self,
        user_id: str,
        conflict_type: str,
        conflict_topic: Optional[str] = None,
        conflict_description: Optional[str] = None,
        partner_user_id: Optional[str] = None,
        handling_style: Optional[str] = None,
    ) -> ConflictHistoryDB:
        """
        记录冲突事件

        Args:
            user_id: 用户 ID
            conflict_type: 冲突类型
            conflict_topic: 冲突主题
            conflict_description: 冲突描述
            partner_user_id: 对方用户 ID（如果有）
            handling_style: 处理方式

        Returns:
            ConflictHistoryDB: 创建的冲突记录
        """
        record = ConflictHistoryDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            partner_user_id=partner_user_id,
            conflict_type=conflict_type,
            conflict_topic=conflict_topic,
            conflict_description=conflict_description,
            handling_style=handling_style,
            resolution_status="unresolved",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution_description: str,
        handling_effectiveness: int,
        relationship_impact: int,
        lessons_learned: Optional[str] = None,
    ) -> ConflictHistoryDB:
        """
        标记冲突为已解决

        Args:
            conflict_id: 冲突记录 ID
            resolution_description: 解决结果描述
            handling_effectiveness: 处理效果评分 (1-10)
            relationship_impact: 对关系的影响 (-10 到 +10)
            lessons_learned: 经验教训

        Returns:
            ConflictHistoryDB: 更新后的冲突记录
        """
        record = self.db.query(ConflictHistoryDB).filter(
            ConflictHistoryDB.id == conflict_id
        ).first()

        if not record:
            raise ValueError(f"Conflict record {conflict_id} not found")

        record.resolution_status = "resolved"
        record.resolved_at = datetime.now()
        record.resolution_description = resolution_description
        record.handling_effectiveness = handling_effectiveness
        record.relationship_impact = relationship_impact
        record.lessons_learned = lessons_learned

        self.db.commit()
        self.db.refresh(record)
        return record

    def get_user_conflict_history(
        self, user_id: str, limit: int = 20
    ) -> List[ConflictHistoryDB]:
        """获取用户冲突历史"""
        return self.db.query(ConflictHistoryDB).filter(
            ConflictHistoryDB.user_id == user_id
        ).order_by(ConflictHistoryDB.created_at.desc()).limit(limit).all()

    # ============= 冲突化解建议 =============

    def get_resolution_tips(
        self,
        conflict_type: str,
        style_a: Optional[str] = None,
        style_b: Optional[str] = None,
        tip_type: Optional[str] = None,
    ) -> List[ConflictResolutionTipDB]:
        """
        获取冲突化解建议

        Args:
            conflict_type: 冲突类型
            style_a: 用户 A 的风格
            style_b: 用户 B 的风格
            tip_type: 建议类型

        Returns:
            List[ConflictResolutionTipDB]: 建议列表
        """
        query = self.db.query(ConflictResolutionTipDB).filter(
            and_(
                ConflictResolutionTipDB.conflict_type == conflict_type,
                ConflictResolutionTipDB.is_active == True
            )
        )

        if style_a and style_b:
            style_combination = f"{style_a}_vs_{style_b}"
            query = query.filter(
                ConflictResolutionTipDB.style_combination == style_combination
            )

        if tip_type:
            query = query.filter(ConflictResolutionTipDB.tip_type == tip_type)

        return query.order_by(
            ConflictResolutionTipDB.effectiveness_rating.desc()
        ).limit(10).all()

    def add_resolution_tip(
        self,
        conflict_type: str,
        tip_title: str,
        tip_content: str,
        style_combination: Optional[str] = None,
        tip_type: str = "general",
        psychological_basis: Optional[str] = None,
    ) -> ConflictResolutionTipDB:
        """添加冲突化解建议"""
        record = ConflictResolutionTipDB(
            id=str(uuid.uuid4()),
            conflict_type=conflict_type,
            style_combination=style_combination,
            tip_title=tip_title,
            tip_content=tip_content,
            tip_type=tip_type,
            psychological_basis=psychological_basis,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def rate_tip_effectiveness(
        self, tip_id: str, rating: float
    ) -> ConflictResolutionTipDB:
        """
        评分建议有效性

        Args:
            tip_id: 建议 ID
            rating: 评分 (1-5)
        """
        record = self.db.query(ConflictResolutionTipDB).filter(
            ConflictResolutionTipDB.id == tip_id
        ).first()

        if not record:
            raise ValueError(f"Tip {tip_id} not found")

        # 更新平均评分
        total_rating = record.effectiveness_rating * record.effectiveness_count
        record.effectiveness_count += 1
        record.effectiveness_rating = (total_rating + rating) / record.effectiveness_count

        self.db.commit()
        self.db.refresh(record)
        return record

    # ============= 沟通模式分析 =============

    def assess_communication_pattern(
        self,
        user_id: str,
        communication_style: Optional[str] = None,
        preferred_frequency: Optional[str] = None,
        preferred_channels: Optional[List[str]] = None,
        preferred_time: Optional[str] = None,
        response_pattern: Optional[str] = None,
        depth_preference: Optional[str] = None,
    ) -> CommunicationPatternDB:
        """
        评估用户沟通模式

        Args:
            user_id: 用户 ID
            communication_style: 沟通风格
            preferred_frequency: 沟通频率偏好
            preferred_channels: 沟通渠道偏好
            preferred_time: 沟通时间偏好
            response_pattern: 响应模式
            depth_preference: 沟通深度偏好

        Returns:
            CommunicationPatternDB: 创建的模式记录
        """
        existing = self.db.query(CommunicationPatternDB).filter(
            CommunicationPatternDB.user_id == user_id
        ).first()

        if existing:
            existing.communication_style = communication_style
            existing.preferred_frequency = preferred_frequency
            existing.preferred_channels = json.dumps(preferred_channels or [])
            existing.preferred_time = preferred_time
            existing.response_pattern = response_pattern
            existing.depth_preference = depth_preference
            existing.updated_at = datetime.now()
            record = existing
        else:
            record = CommunicationPatternDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                communication_style=communication_style,
                preferred_frequency=preferred_frequency,
                preferred_channels=json.dumps(preferred_channels or []),
                preferred_time=preferred_time,
                response_pattern=response_pattern,
                depth_preference=depth_preference,
            )
            self.db.add(record)

        self.db.commit()
        self.db.refresh(record)
        return record

    def get_user_communication_pattern(
        self, user_id: str
    ) -> Optional[CommunicationPatternDB]:
        """获取用户沟通模式"""
        return self.db.query(CommunicationPatternDB).filter(
            CommunicationPatternDB.user_id == user_id
        ).first()

    def get_compatibility_suggestions(
        self, user_a_id: str, user_b_id: str
    ) -> Dict[str, Any]:
        """
        获取双方兼容性建议（综合冲突风格和沟通模式）

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID

        Returns:
            Dict: 兼容性建议综合报告
        """
        # 获取双方风格
        style_a = self.get_user_conflict_style(user_a_id)
        style_b = self.get_user_conflict_style(user_b_id)
        pattern_a = self.get_user_communication_pattern(user_a_id)
        pattern_b = self.get_user_communication_pattern(user_b_id)

        suggestions = {
            "conflict_compatibility": None,
            "communication_compatibility": None,
            "overall_suggestions": [],
        }

        # 冲突兼容性
        if style_a and style_b:
            compatibility = self.calculate_conflict_compatibility(user_a_id, user_b_id)
            suggestions["conflict_compatibility"] = {
                "score": compatibility.compatibility_score,
                "style_a": STYLE_NAMES.get(style_a.primary_style, "未知"),
                "style_b": STYLE_NAMES.get(style_b.primary_style, "未知"),
                "risk_factors": json.loads(compatibility.risk_factors),
                "suggestions": json.loads(compatibility.suggestions),
            }

        # 沟通模式兼容性
        if pattern_a and pattern_b:
            comm_compatibility = self._analyze_communication_compatibility(
                pattern_a, pattern_b
            )
            suggestions["communication_compatibility"] = comm_compatibility

        # 综合建议
        suggestions["overall_suggestions"] = self._generate_overall_suggestions(
            suggestions
        )

        return suggestions

    def _analyze_communication_compatibility(
        self, pattern_a: CommunicationPatternDB, pattern_b: CommunicationPatternDB
    ) -> Dict[str, Any]:
        """分析沟通模式兼容性"""
        compatibility = {
            "score": 0.5,
            "factors": [],
            "suggestions": [],
        }

        # 沟通风格兼容性
        style_pairs = [
            ("direct", "direct"),
            ("indirect", "indirect"),
            ("analytical", "emotional"),
        ]
        style_match = (pattern_a.communication_style, pattern_b.communication_style) in style_pairs

        # 频率兼容性
        freq_map = {"daily": 4, "several_times_week": 3, "weekly": 2, "as_needed": 1}
        freq_a = freq_map.get(pattern_a.preferred_frequency, 2)
        freq_b = freq_map.get(pattern_b.preferred_frequency, 2)
        freq_diff = abs(freq_a - freq_b)

        # 响应模式兼容性
        response_pairs = [("immediate", "immediate"), ("delayed", "delayed"), ("batch", "batch")]
        response_match = (pattern_a.response_pattern, pattern_b.response_pattern) in response_pairs

        # 计算兼容性
        score = 0.5
        if style_match:
            score += 0.2
            compatibility["factors"].append("沟通风格相似")
        if freq_diff <= 1:
            score += 0.2
            compatibility["factors"].append("沟通频率相近")
        elif freq_diff >= 2:
            score -= 0.1
            compatibility["factors"].append("沟通频率差异较大")
        if response_match:
            score += 0.1
            compatibility["factors"].append("响应模式一致")

        compatibility["score"] = min(1.0, max(0.0, score))

        # 生成建议
        if freq_diff >= 2:
            compatibility["suggestions"].append(
                "双方沟通频率偏好差异较大，建议找到一个平衡点，既不过度打扰也不过于冷淡。"
            )
        if not style_match:
            compatibility["suggestions"].append(
                "沟通风格不同可能导致误解，建议明确表达自己的沟通偏好并尊重对方的方式。"
            )

        return compatibility

    def _generate_overall_suggestions(
        self, suggestions: Dict[str, Any]
    ) -> List[str]:
        """生成综合建议"""
        overall = []

        conflict_compat = suggestions.get("conflict_compatibility")
        comm_compat = suggestions.get("communication_compatibility")

        if conflict_compat and comm_compat:
            avg_score = (conflict_compat["score"] + comm_compat["score"]) / 2
            if avg_score >= 0.8:
                overall.append("你们在冲突处理和沟通模式上都有很好的兼容性，继续保持开放和诚实的交流！")
            elif avg_score >= 0.6:
                overall.append("你们在某些方面有较好的兼容性，在一些差异点上需要相互理解和适应。")
            else:
                overall.append("你们在冲突处理和沟通模式上存在一些差异，建议主动沟通彼此的期望和需求。")

        # 添加具体建议
        if conflict_compat:
            overall.extend([s["content"] for s in conflict_compat.get("suggestions", []) if s.get("content")])
        if comm_compat:
            overall.extend(comm_compat.get("suggestions", []))

        return overall


# ============================================
# 工具函数
# ============================================

def get_style_name(style: str) -> str:
    """获取风格中文名称"""
    return STYLE_NAMES.get(style, "未知")


def get_style_description(style: str) -> str:
    """获取风格描述"""
    return STYLE_DESCRIPTIONS.get(style, "")
