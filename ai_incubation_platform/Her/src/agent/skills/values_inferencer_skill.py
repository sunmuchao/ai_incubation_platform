"""
价值观行为推断 Skill

Identity 功能：基于用户行为推断真实价值观，与声明价值观对比检测偏移
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class ValuesInferencerSkill:
    """
    价值观行为推断 Skill

    核心能力:
    - 基于行为推断价值观
    - 声明 vs 实际对比
    - 价值观偏移检测
    - 偏移影响分析
    - 调整建议生成

    自主触发条件:
    - 用户行为数据积累到阈值
    - 匹配质量下降时
    - 定期 (每月) 价值观更新
    """

    name = "values_inferencer"
    version = "1.0.0"
    description = """
    价值观行为推断专家

    能力:
    - 从行为数据推断真实价值观 (6 维度)
    - 声明价值观 vs 实际价值观对比
    - 价值观偏移检测和量化
    - 对匹配策略的影响分析
    - 个性化的价值观整合建议
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "analysis_window_days": {
                    "type": "integer",
                    "description": "分析窗口天数",
                    "default": 30
                },
                "include_drift_analysis": {
                    "type": "boolean",
                    "description": "是否包含偏移分析"
                },
                "update_weights": {
                    "type": "boolean",
                    "description": "是否更新匹配权重"
                }
            },
            "required": ["user_id"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "declared_values": {"type": "array"},
                "inferred_values": {"type": "array"},
                "drift_analysis": {"type": "object"},
                "weight_adjustments": {"type": "object"},
                "suggestions": {"type": "array"}
            }
        }

    async def execute(
        self,
        user_id: str,
        analysis_window_days: int = 30,
        include_drift_analysis: bool = True,
        update_weights: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行价值观推断

        Args:
            user_id: 用户 ID
            analysis_window_days: 分析窗口天数
            include_drift_analysis: 是否包含偏移分析
            update_weights: 是否更新匹配权重

        Returns:
            分析结果
        """
        logger.info(f"ValuesInferencer: Inferring values for user={user_id}, window={analysis_window_days}d")

        try:
            # 获取声明的价值观
            declared_values = self._get_declared_values(user_id)

            # 从行为推断价值观
            inferred_values = self._infer_from_behavior(user_id, analysis_window_days)

            # 计算偏移
            drift_analysis = None
            if include_drift_analysis and declared_values:
                drift_analysis = self._calculate_drift(declared_values, inferred_values)

            # 更新权重 (可选)
            weight_adjustment = None
            if update_weights and drift_analysis and drift_analysis.get("significant"):
                weight_adjustment = self._adjust_weights(user_id, drift_analysis)

            # 生成建议
            suggestions = self._generate_suggestions(
                declared_values, inferred_values, drift_analysis
            )

            # 构建响应
            return self._build_response(
                declared_values,
                inferred_values,
                drift_analysis,
                weight_adjustment,
                suggestions
            )

        except Exception as e:
            logger.error(f"ValuesInferencer execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "价值观推断失败，请稍后再试"
            }

    def _get_declared_values(self, user_id: str) -> List[Dict]:
        """获取用户声明的价值观"""
        from utils.db_session_manager import db_session
        from models.values_models import DeclaredValuesDB

        with db_session() as db:
            declared = db.query(DeclaredValuesDB).filter(
                DeclaredValuesDB.user_id == user_id
            ).order_by(DeclaredValuesDB.created_at.desc()).first()

            if declared:
                return [
                    {"dimension": "family", "value": declared.family_value, "weight": declared.family_weight},
                    {"dimension": "career", "value": declared.career_value, "weight": declared.career_weight},
                    {"dimension": "lifestyle", "value": declared.lifestyle_value, "weight": declared.lifestyle_weight},
                    {"dimension": "finance", "value": declared.finance_value, "weight": declared.finance_weight},
                    {"dimension": "growth", "value": declared.growth_value, "weight": declared.growth_weight},
                    {"dimension": "relationship", "value": declared.relationship_value, "weight": declared.relationship_weight},
                ]
            return []

    def _infer_from_behavior(
        self,
        user_id: str,
        window_days: int
    ) -> List[Dict]:
        """从行为推断价值观"""
        from services.values_evolution_service import values_evolution_service

        # 调用服务的推断方法
        inferred = values_evolution_service.infer_values_from_behavior(
            user_id,
            days=window_days
        )

        # 转换为标准格式
        result = []
        dimension_map = {
            "family": "家庭观念",
            "career": "事业追求",
            "lifestyle": "生活方式",
            "finance": "消费观念",
            "growth": "成长意愿",
            "relationship": "关系期待",
        }

        for dim_key, dim_name in dimension_map.items():
            value_data = inferred.get(dim_key, {})
            result.append({
                "dimension": dim_key,
                "dimension_name": dim_name,
                "inferred_value": value_data.get("value", "unknown"),
                "confidence": value_data.get("confidence", 0.5),
                "evidence_count": value_data.get("evidence_count", 0),
            })

        return result

    def _calculate_drift(
        self,
        declared: List[Dict],
        inferred: List[Dict]
    ) -> Dict:
        """计算价值观偏移"""
        from services.values_evolution_service import values_evolution_service

        # 构建维度映射
        declared_map = {d["dimension"]: d for d in declared}
        inferred_map = {d["dimension"]: d for d in inferred}

        drifts = []
        total_drift = 0.0
        significant_dimensions = []

        for dim in ["family", "career", "lifestyle", "finance", "growth", "relationship"]:
            dec = declared_map.get(dim, {})
            inf = inferred_map.get(dim, {})

            declared_val = dec.get("value", "")
            inferred_val = inf.get("inferred_value", "")

            # 计算偏移
            if declared_val and inferred_val:
                is_different = declared_val != inferred_val
                drift_score = 1.0 if is_different else 0.0

                if is_different:
                    drifts.append({
                        "dimension": dim,
                        "declared_value": declared_val,
                        "inferred_value": inferred_val,
                        "drift_score": drift_score,
                        "description": self._get_drift_description(dim, declared_val, inferred_val),
                    })
                    significant_dimensions.append(dim)

                total_drift += drift_score

        avg_drift = total_drift / 6.0 if declared else 0.0

        return {
            "has_drift": len(drifts) > 0,
            "significant": len(significant_dimensions) >= 2,
            "drift_dimensions": significant_dimensions,
            "drift_details": drifts,
            "overall_drift_score": avg_drift,
            "drift_level": self._get_drift_level(avg_drift),
        }

    def _adjust_weights(
        self,
        user_id: str,
        drift_analysis: Dict
    ) -> Dict:
        """调整匹配权重"""
        from services.values_evolution_service import values_evolution_service
        from utils.db_session_manager import db_session
        from models.values_models import DeclaredValuesDB

        with db_session() as db:
            declared = db.query(DeclaredValuesDB).filter(
                DeclaredValuesDB.user_id == user_id
            ).first()

            if not declared:
                return {}

            # 获取当前权重
            before_weights = {
                "family": declared.family_weight,
                "career": declared.career_weight,
                "lifestyle": declared.lifestyle_weight,
                "finance": declared.finance_weight,
                "growth": declared.growth_weight,
                "relationship": declared.relationship_weight,
            }

            # 根据偏移调整权重
            after_weights = before_weights.copy()
            for dim in drift_analysis.get("drift_dimensions", []):
                # 增加推断价值观的权重
                after_weights[dim] = min(100, before_weights.get(dim, 20) + 10)

            # 调用服务记录调整
            success, message, adjustment = values_evolution_service.adjust_matching_weights(
                user_id=user_id,
                before_weights=before_weights,
                after_weights=after_weights,
                adjustment_reason="values_drift_detected",
                ai_reasoning=f"检测到{len(drift_analysis.get('drift_dimensions', []))}个维度存在价值观偏移",
            )

            return {
                "success": success,
                "before": before_weights,
                "after": after_weights,
                "adjustment_id": adjustment.id if adjustment else None,
            }

    def _generate_suggestions(
        self,
        declared: List[Dict],
        inferred: List[Dict],
        drift_analysis: Optional[Dict]
    ) -> List[Dict]:
        """生成建议"""
        suggestions = []

        # 基于偏移的建议
        if drift_analysis and drift_analysis.get("has_drift"):
            for drift in drift_analysis.get("drift_details", []):
                suggestions.append({
                    "type": "drift_awareness",
                    "priority": "high",
                    "dimension": drift["dimension"],
                    "message": f"AI 发现您的{self._get_dimension_name(drift['dimension'])}可能存在变化",
                    "description": drift["description"],
                    "action": "review_values",
                })

        # 基于置信度的建议
        for inf in inferred:
            if inf.get("confidence", 0) < 0.4 and inf.get("evidence_count", 0) < 5:
                suggestions.append({
                    "type": "more_data",
                    "priority": "low",
                    "dimension": inf["dimension"],
                    "message": f"多参与相关活动，帮助 AI 更好了解您的{self._get_dimension_name(inf['dimension'])}",
                    "action": "engage_more",
                })

        # 基于显著偏移的匹配策略建议
        if drift_analysis and drift_analysis.get("significant"):
            suggestions.append({
                "type": "matching_update",
                "priority": "medium",
                "message": "您的择偶偏好可能已变化，AI 将调整推荐策略",
                "action": "update_preferences",
            })

        return suggestions[:5]

    def _build_response(
        self,
        declared: List[Dict],
        inferred: List[Dict],
        drift_analysis: Optional[Dict],
        weight_adjustment: Optional[Dict],
        suggestions: List[Dict]
    ) -> Dict[str, Any]:
        """构建响应"""
        ai_message = self._generate_ai_message(declared, inferred, drift_analysis)
        if suggestions:
            ai_message += f"\n\n{len(suggestions)}条建议供您参考~"

        return {
            "success": True,
            "data": {
                "declared_values": declared,
                "inferred_values": inferred,
                "drift_analysis": drift_analysis,
                "weight_adjustment": weight_adjustment,
                "suggestions": suggestions,
            },
            "ai_message": ai_message,
        }

    def _generate_ai_message(
        self,
        declared: List[Dict],
        inferred: List[Dict],
        drift_analysis: Optional[Dict]
    ) -> str:
        """生成 AI 消息"""
        if not declared:
            return "请先完成价值观声明，以便 AI 进行对比分析~"

        lines = ["价值观分析结果：", ""]

        if drift_analysis and drift_analysis.get("has_drift"):
            lines.append(f"⚠️ 发现{len(drift_analysis.get('drift_details', []))}个维度存在价值观偏移")
            for drift in drift_analysis.get("drift_details", [])[:2]:
                lines.append(f"   • {self._get_dimension_name(drift['dimension'])}: {drift['description']}")
            lines.append("")
        else:
            lines.append("✅ 您的声明价值观与行为表现一致")
            lines.append("")

        lines.append("基于行为推断的价值观：")
        for inf in inferred[:3]:
            lines.append(f"   • {inf['dimension_name']}: {inf['inferred_value']}")

        return "\n".join(lines)

    # ========== 辅助函数 ==========

    def _get_dimension_name(self, dim: str) -> str:
        """获取维度名称"""
        names = {
            "family": "家庭观念",
            "career": "事业追求",
            "lifestyle": "生活方式",
            "finance": "消费观念",
            "growth": "成长意愿",
            "relationship": "关系期待",
        }
        return names.get(dim, dim)

    def _get_drift_description(
        self,
        dim: str,
        declared_val: str,
        inferred_val: str
    ) -> str:
        """获取偏移描述"""
        return f'从"{declared_val}"转变为"{inferred_val}"'

    def _get_drift_level(self, score: float) -> str:
        """获取偏移等级"""
        if score >= 0.5:
            return "显著"
        elif score >= 0.3:
            return "中等"
        elif score >= 0.1:
            return "轻微"
        else:
            return "无"


# 全局单例获取函数
_skill_instance: Optional[ValuesInferencerSkill] = None


def get_values_inferencer_skill() -> ValuesInferencerSkill:
    """获取价值观行为推断 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = ValuesInferencerSkill()
    return _skill_instance
