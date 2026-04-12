"""
价值观偏移检测 Skill

Values 功能：检测用户价值观随时间的变化，生成偏移报告和趋势分析
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class ValuesDriftDetectorSkill:
    """
    价值观偏移检测 Skill

    核心能力:
    - 多时间点价值观对比
    - 偏移趋势分析
    - 偏移原因推断
    - 影响评估
    - 预警通知生成

    自主触发条件:
    - 月度/周期性检测
    - 用户行为显著变化时
    - 匹配质量持续下降
    """

    name = "values_drift_detector"
    version = "1.0.0"
    description = """
    价值观偏移检测专家

    能力:
    - 多时间点价值观对比分析
    - 6 维度偏移趋势追踪
    - 基于行为的偏移原因推断
    - 对匹配策略的影响评估
    - 阈值预警和通知生成
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
                "comparison_period_days": {
                    "type": "integer",
                    "description": "对比周期天数",
                    "default": 30
                },
                "drift_threshold": {
                    "type": "number",
                    "description": "偏移阈值 (0-1)",
                    "default": 0.3
                },
                "include_trend": {
                    "type": "boolean",
                    "description": "是否包含趋势分析"
                },
                "trigger_alert": {
                    "type": "boolean",
                    "description": "是否触发预警通知"
                }
            },
            "required": ["user_id"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "has_significant_drift": {"type": "boolean"},
                "drift_score": {"type": "number"},
                "drift_dimensions": {"type": "array"},
                "trend_analysis": {"type": "object"},
                "impact_assessment": {"type": "object"},
                "alert_triggered": {"type": "boolean"}
            }
        }

    async def execute(
        self,
        user_id: str,
        comparison_period_days: int = 30,
        drift_threshold: float = 0.3,
        include_trend: bool = True,
        trigger_alert: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行价值观偏移检测

        Args:
            user_id: 用户 ID
            comparison_period_days: 对比周期天数
            drift_threshold: 偏移阈值
            include_trend: 是否包含趋势
            trigger_alert: 是否触发预警

        Returns:
            检测结果
        """
        logger.info(f"ValuesDriftDetector: Detecting drift for user={user_id}, period={comparison_period_days}d")

        try:
            # 获取历史价值观记录
            history = self._get_values_history(user_id, comparison_period_days)

            # 如果没有足够历史数据
            if len(history) < 2:
                return self._build_insufficient_data_response(history)

            # 对比分析
            drift_result = self._analyze_drift(history, drift_threshold)

            # 趋势分析
            trend_analysis = None
            if include_trend and len(history) >= 3:
                trend_analysis = self._analyze_trend(history)

            # 影响评估
            impact_assessment = self._assess_impact(drift_result, user_id)

            # 触发预警 (如需要)
            alert_triggered = False
            if trigger_alert and drift_result.get("significant"):
                alert_triggered = self._trigger_alert(user_id, drift_result)

            # 构建响应
            return self._build_response(
                drift_result, trend_analysis, impact_assessment, alert_triggered
            )

        except Exception as e:
            logger.error(f"ValuesDriftDetector execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "价值观偏移检测失败，请稍后再试"
            }

    def _get_values_history(
        self,
        user_id: str,
        period_days: int
    ) -> List[Dict]:
        """获取价值观历史"""
        from utils.db_session_manager import db_session
        from models.values_models import DeclaredValuesDB, InferredValuesDB

        cutoff_date = datetime.now() - timedelta(days=period_days)

        with db_session() as db:
            # 获取声明价值观历史
            declared_history = db.query(DeclaredValuesDB).filter(
                DeclaredValuesDB.user_id == user_id,
                DeclaredValuesDB.created_at >= cutoff_date
            ).order_by(DeclaredValuesDB.created_at.desc()).all()

            history = []
            for d in declared_history:
                history.append({
                    "type": "declared",
                    "timestamp": d.created_at.isoformat(),
                    "values": {
                        "family": {"value": d.family_value, "weight": d.family_weight},
                        "career": {"value": d.career_value, "weight": d.career_weight},
                        "lifestyle": {"value": d.lifestyle_value, "weight": d.lifestyle_weight},
                        "finance": {"value": d.finance_value, "weight": d.finance_weight},
                        "growth": {"value": d.growth_value, "weight": d.growth_weight},
                        "relationship": {"value": d.relationship_value, "weight": d.relationship_weight},
                    }
                })

            # 获取推断价值观历史
            inferred_history = db.query(InferredValuesDB).filter(
                InferredValuesDB.user_id == user_id,
                InferredValuesDB.created_at >= cutoff_date
            ).order_by(InferredValuesDB.created_at.desc()).all()

            for i in inferred_history:
                history.append({
                    "type": "inferred",
                    "timestamp": i.created_at.isoformat(),
                    "values": {
                        "family": {"value": i.family_value, "confidence": i.confidence_score},
                        "career": {"value": i.career_value, "confidence": i.confidence_score},
                        "lifestyle": {"value": i.lifestyle_value, "confidence": i.confidence_score},
                        "finance": {"value": i.finance_value, "confidence": i.confidence_score},
                        "growth": {"value": i.growth_value, "confidence": i.confidence_score},
                        "relationship": {"value": i.relationship_value, "confidence": i.confidence_score},
                    }
                })

            # 按时间排序
            history.sort(key=lambda x: x["timestamp"], reverse=True)
            return history

    def _analyze_drift(
        self,
        history: List[Dict],
        threshold: float
    ) -> Dict:
        """分析偏移"""
        if len(history) < 2:
            return {"has_drift": False, "dimensions": []}

        # 取最新和最早的记录对比
        latest = history[0]
        earliest = history[-1]

        dimensions = ["family", "career", "lifestyle", "finance", "growth", "relationship"]
        drift_details = []
        total_drift = 0.0

        for dim in dimensions:
            latest_val = latest["values"].get(dim, {}).get("value", "")
            earliest_val = earliest["values"].get(dim, {}).get("value", "")

            if latest_val and earliest_val and latest_val != earliest_val:
                drift_score = 1.0
                drift_details.append({
                    "dimension": dim,
                    "dimension_name": self._get_dimension_name(dim),
                    "from_value": earliest_val,
                    "to_value": latest_val,
                    "drift_score": drift_score,
                    "change_type": self._get_change_type(dim, earliest_val, latest_val),
                })
                total_drift += drift_score

        avg_drift = total_drift / len(dimensions) if dimensions else 0.0

        return {
            "has_drift": len(drift_details) > 0,
            "significant": avg_drift >= threshold,
            "overall_drift_score": round(avg_drift, 2),
            "drift_dimensions": [d["dimension"] for d in drift_details],
            "drift_details": drift_details,
            "comparison_period": {
                "from": earliest["timestamp"],
                "to": latest["timestamp"],
            },
        }

    def _analyze_trend(self, history: List[Dict]) -> Dict:
        """分析趋势"""
        # 按时间正序排列
        sorted_history = sorted(history, key=lambda x: x["timestamp"])

        dimensions = ["family", "career", "lifestyle", "finance", "growth", "relationship"]
        trends = {}

        for dim in dimensions:
            values = []
            for record in sorted_history:
                val = record["values"].get(dim, {}).get("value")
                if val:
                    values.append(val)

            if len(values) >= 2:
                # 简化趋势分析：判断是否稳定
                unique_values = set(values)
                if len(unique_values) == 1:
                    trends[dim] = {"trend": "stable", "value": values[-1]}
                elif len(unique_values) == len(values):
                    trends[dim] = {"trend": "changing", "value_changes": len(values)}
                else:
                    trends[dim] = {"trend": "fluctuating", "unique_values": list(unique_values)}

        return {
            "dimension_trends": trends,
            "stability_score": self._calculate_stability_score(trends),
        }

    def _calculate_stability_score(self, trends: Dict) -> float:
        """计算稳定性分数"""
        if not trends:
            return 1.0

        stable_count = sum(1 for t in trends.values() if t.get("trend") == "stable")
        return round(stable_count / len(trends), 2)

    def _assess_impact(
        self,
        drift_result: Dict,
        user_id: str
    ) -> Dict:
        """评估影响"""
        impact = {
            "matching_impact": "none",
            "recommendation_changes": [],
            "priority_level": "low",
        }

        if drift_result.get("significant"):
            # 显著偏移，需要调整匹配策略
            impact["matching_impact"] = "adjust_weights"
            impact["priority_level"] = "high"

            for dim in drift_result.get("drift_dimensions", []):
                impact["recommendation_changes"].append({
                    "dimension": dim,
                    "action": "increase_weight",
                    "reason": f"用户{self._get_dimension_name(dim)}发生变化",
                })

            # 评估是否需要重新匹配
            if len(drift_result.get("drift_dimensions", [])) >= 3:
                impact["matching_impact"] = "re-evaluate_matches"
                impact["priority_level"] = "critical"

        elif drift_result.get("has_drift"):
            # 轻微偏移，持续观察
            impact["matching_impact"] = "monitor"
            impact["priority_level"] = "medium"

        return impact

    def _trigger_alert(
        self,
        user_id: str,
        drift_result: Dict
    ) -> bool:
        """触发预警"""
        from utils.logger import logger

        drift_score = drift_result.get("overall_drift_score", 0)
        dimension_count = len(drift_result.get("drift_dimensions", []))

        # 生成预警消息
        alert_message = (
            f"用户{user_id}检测到价值观偏移，"
            f"偏移分数{drift_score:.2f}，"
            f"涉及{dimension_count}个维度"
        )

        logger.info(f"VALUES_DRIFT_ALERT: {alert_message}")

        # 这里可以集成实际的通知系统
        # 如推送通知、邮件、短信等

        return True

    def _build_insufficient_data_response(
        self,
        history: List[Dict]
    ) -> Dict[str, Any]:
        """构建数据不足响应"""
        return {
            "success": True,
            "data": {
                "has_significant_drift": False,
                "drift_score": 0,
                "drift_dimensions": [],
                "message": "数据不足，无法进行偏移分析",
                "current_records": len(history),
                "required_records": 2,
            },
            "ai_message": "暂无足够的历史数据进行价值观偏移分析，请继续使用应用积累数据~",
        }

    def _build_response(
        self,
        drift_result: Dict,
        trend_analysis: Optional[Dict],
        impact_assessment: Dict,
        alert_triggered: bool
    ) -> Dict[str, Any]:
        """构建响应"""
        ai_message = self._generate_ai_message(drift_result, trend_analysis)

        data = {
            "has_significant_drift": drift_result.get("significant", False),
            "has_drift": drift_result.get("has_drift", False),
            "drift_score": drift_result.get("overall_drift_score", 0),
            "drift_dimensions": drift_result.get("drift_dimensions", []),
            "drift_details": drift_result.get("drift_details", []),
            "trend_analysis": trend_analysis,
            "impact_assessment": impact_assessment,
            "alert_triggered": alert_triggered,
        }

        return {
            "success": True,
            "data": data,
            "ai_message": ai_message,
        }

    def _generate_ai_message(
        self,
        drift_result: Dict,
        trend_analysis: Optional[Dict]
    ) -> str:
        """生成 AI 消息"""
        if not drift_result.get("has_drift"):
            return "您的价值观保持稳定，未发现显著偏移~"

        lines = ["价值观偏移检测结果：", ""]

        if drift_result.get("significant"):
            lines.append("⚠️ 检测到显著价值观偏移")
        else:
            lines.append("📊 检测到轻微价值观变化")

        lines.append("")
        lines.append(f"偏移分数：{drift_result.get('overall_drift_score', 0) * 100:.0f}分")
        lines.append(f"涉及维度：{len(drift_result.get('drift_dimensions', []))}个")

        for detail in drift_result.get("drift_details", [])[:3]:
            lines.append(
                f"   • {detail['dimension_name']}: "
                f"从\"{detail['from_value']}\"变为\"{detail['to_value']}\""
            )

        if trend_analysis:
            lines.append("")
            stability = trend_analysis.get("stability_score", 0) * 100
            lines.append(f"价值观稳定性：{stability:.0f}%")

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

    def _get_change_type(
        self,
        dim: str,
        from_val: str,
        to_val: str
    ) -> str:
        """获取变化类型"""
        # 简化实现
        return f"{from_val} → {to_val}"


# 全局单例获取函数
_skill_instance: Optional[ValuesDriftDetectorSkill] = None


def get_values_drift_detector_skill() -> ValuesDriftDetectorSkill:
    """获取价值观偏移检测 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = ValuesDriftDetectorSkill()
    return _skill_instance
