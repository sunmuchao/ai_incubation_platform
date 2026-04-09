"""
关系预测 Skill - AI 关系预言家

AI 关系分析师核心 Skill - 关系趋势预测、风险预警、发展建议
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger
import json
import math


class RelationshipProphetSkill(BaseSkill):
    """
    AI 关系预言家 Skill - 预测关系发展趋势，提前预警风险

    核心能力:
    - 关系趋势分析：基于历史数据预测发展方向
    - 风险评估：识别可能导致分手的风险因素
    - 发展建议：提供关系升温的具体行动
    - 里程碑预测：预测关系进阶时机

    自主触发:
    - 定期关系健康检查（每周/每月）
    - 检测到关系降温趋势
    - 重要纪念日前提醒
    """

    name = "relationship_prophet"
    version = "1.0.0"
    description = """
    AI 关系预言家，预测关系发展趋势，提前预警风险

    能力:
    - 关系趋势分析：预测关系发展方向（升温/稳定/降温）
    - 风险评估：识别分手风险、沟通问题、兼容性挑战
    - 发展建议：提供关系升温的具体行动方案
    - 里程碑预测：预测表白、同居、见家长等进阶时机
    """

    # 关系阶段
    RELATIONSHIP_STAGES = {
        "initial": {"name": "初识阶段", "order": 1},
        "getting_to_know": {"name": "了解阶段", "order": 2},
        "attraction": {"name": "暧昧阶段", "order": 3},
        "dating": {"name": "约会阶段", "order": 4},
        "exclusive": {"name": "确定关系", "order": 5},
        "deepening": {"name": "关系深入", "order": 6},
        "commitment": {"name": "承诺阶段", "order": 7},
        "long_term": {"name": "长期关系", "order": 8}
    }

    # 关系天气类型
    RELATIONSHIP_WEATHER = {
        "sunny": {"name": "晴朗", "score_min": 80},
        "partly_cloudy": {"name": "多云", "score_min": 60},
        "cloudy": {"name": "阴天", "score_min": 40},
        "rainy": {"name": "小雨", "score_min": 20},
        "stormy": {"name": "暴风雨", "score_min": 0}
    }

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_a_id": {
                    "type": "string",
                    "description": "用户 A ID"
                },
                "user_b_id": {
                    "type": "string",
                    "description": "用户 B ID"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["trend_prediction", "risk_assessment", "milestone_prediction", "relationship_weather"],
                    "description": "分析类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "relationship_start_date": {"type": "string"},
                        "current_stage": {"type": "string"},
                        "interaction_frequency": {"type": "string"},
                        "recent_conflicts": {"type": "number"}
                    }
                },
                "history_data": {
                    "type": "object",
                    "properties": {
                        "conversation_stats": {"type": "object"},
                        "date_history": {"type": "array"},
                        "conflict_history": {"type": "array"},
                        "milestone_history": {"type": "array"}
                    }
                }
            },
            "required": ["user_a_id", "user_b_id", "analysis_type"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "prediction_result": {
                    "type": "object",
                    "properties": {
                        "relationship_score": {"type": "number"},
                        "weather": {"type": "string"},
                        "trend": {"type": "string"},
                        "trend_direction": {"type": "string"},
                        "confidence": {"type": "number"},
                        "risk_factors": {"type": "array"},
                        "milestone_predictions": {"type": "array"},
                        "action_recommendations": {"type": "array"}
                    }
                },
                "generative_ui": {
                    "type": "object",
                    "properties": {
                        "component_type": {"type": "string"},
                        "props": {"type": "object"}
                    }
                },
                "suggested_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "action_type": {"type": "string"},
                            "params": {"type": "object"}
                        }
                    }
                }
            },
            "required": ["success", "ai_message", "prediction_result"]
        }

    async def execute(
        self,
        user_a_id: str,
        user_b_id: str,
        analysis_type: str,
        context: Optional[Dict[str, Any]] = None,
        history_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行关系预测 Skill

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            analysis_type: 分析类型
            context: 上下文信息
            history_data: 历史数据
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"RelationshipProphetSkill: Executing for users={user_a_id},{user_b_id}, type={analysis_type}")

        start_time = datetime.now()

        # Step 1: 根据分析类型执行预测
        prediction_result = await self._perform_prediction(
            analysis_type=analysis_type,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            context=context,
            history_data=history_data
        )

        # Step 2: 生成自然语言解读
        ai_message = self._generate_message(prediction_result, analysis_type)

        # Step 3: 构建 Generative UI
        generative_ui = self._build_ui(prediction_result, analysis_type)

        # Step 4: 生成建议操作
        suggested_actions = self._generate_actions(prediction_result)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "prediction_result": prediction_result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time),
                "analysis_type": analysis_type
            }
        }

    async def _perform_prediction(
        self,
        analysis_type: str,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict],
        history_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """执行关系预测"""
        from db.database import SessionLocal

        db = SessionLocal()
        result = {
            "relationship_score": 50,
            "weather": "cloudy",
            "trend": "stable",
            "trend_direction": "horizontal",
            "confidence": 0.5,
            "risk_factors": [],
            "milestone_predictions": [],
            "action_recommendations": []
        }

        try:
            if analysis_type == "trend_prediction":
                # 趋势预测
                trend_info = self._predict_trend(context, history_data)
                result.update(trend_info)

            elif analysis_type == "risk_assessment":
                # 风险评估
                risk_info = self._assess_risk(context, history_data)
                result.update(risk_info)

            elif analysis_type == "milestone_prediction":
                # 里程碑预测
                milestone_info = self._predict_milestones(context, history_data)
                result.update(milestone_info)

            elif analysis_type == "relationship_weather":
                # 关系天气
                weather_info = self._calculate_relationship_weather(context, history_data)
                result.update(weather_info)

            # 生成行动建议
            result["action_recommendations"] = self._generate_action_recommendations(result)

            return result

        except Exception as e:
            logger.error(f"RelationshipProphetSkill: Prediction failed: {e}")
            return result
        finally:
            db.close()

    def _predict_trend(self, context: Optional[Dict], history_data: Optional[Dict]) -> Dict[str, Any]:
        """预测关系趋势"""
        # 从历史数据分析趋势
        if not history_data:
            return {
                "trend": "stable",
                "trend_direction": "horizontal",
                "confidence": 0.5,
                "prediction_summary": "关系发展平稳，继续保持良好互动"
            }

        # 分析互动频率变化
        conversation_stats = history_data.get("conversation_stats", {})
        recent_frequency = conversation_stats.get("recent_frequency", 50)
        previous_frequency = conversation_stats.get("previous_frequency", 50)

        # 计算趋势
        if recent_frequency > previous_frequency * 1.2:
            trend = "rising"
            trend_direction = "up"
            trend_description = "关系正在升温"
        elif recent_frequency < previous_frequency * 0.8:
            trend = "declining"
            trend_direction = "down"
            trend_description = "关系有所降温"
        else:
            trend = "stable"
            trend_direction = "horizontal"
            trend_description = "关系发展稳定"

        # 计算关系分数
        relationship_score = min(100, max(0, 50 + (recent_frequency - previous_frequency) / 10))

        # 确定置信度
        confidence = min(0.9, 0.5 + len(history_data.get("date_history", [])) * 0.1)

        return {
            "trend": trend,
            "trend_direction": trend_direction,
            "trend_description": trend_description,
            "relationship_score": round(relationship_score, 1),
            "confidence": round(confidence, 2)
        }

    def _assess_risk(self, context: Optional[Dict], history_data: Optional[Dict]) -> Dict[str, Any]:
        """评估关系风险"""
        risk_factors = []
        risk_score = 0

        # 检查冲突历史
        if history_data:
            conflict_history = history_data.get("conflict_history", [])
            recent_conflicts = len([c for c in conflict_history if self._is_recent(c.get("date", ""))])

            if recent_conflicts >= 3:
                risk_factors.append({
                    "type": "frequent_conflicts",
                    "name": "频繁冲突",
                    "severity": "high",
                    "description": f"最近发生{recent_conflicts}次冲突，建议加强沟通"
                })
                risk_score += 30
            elif recent_conflicts >= 1:
                risk_factors.append({
                    "type": "recent_conflict",
                    "name": "近期冲突",
                    "severity": "medium",
                    "description": "近期有未解决的冲突，建议及时沟通"
                })
                risk_score += 15

            # 检查互动质量
            conversation_stats = history_data.get("conversation_stats", {})
            avg_message_length = conversation_stats.get("avg_message_length", 50)

            if avg_message_length < 20:
                risk_factors.append({
                    "type": "shallow_communication",
                    "name": "交流浅层化",
                    "severity": "medium",
                    "description": "对话内容趋于简短，可能缺乏深度交流"
                })
                risk_score += 20

        # 检查关系阶段匹配
        if context:
            current_stage = context.get("current_stage", "getting_to_know")
            relationship_start = context.get("relationship_start_date")

            if relationship_start:
                days_together = self._days_since(relationship_start)
                stage_mismatch = self._check_stage_mismatch(current_stage, days_together)

                if stage_mismatch:
                    risk_factors.append({
                        "type": "stage_mismatch",
                        "name": "关系阶段不匹配",
                        "severity": "low",
                        "description": f"交往{days_together}天，当前阶段{current_stage}，发展速度可能偏慢"
                    })
                    risk_score += 10

        # 计算风险等级
        if risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        elif risk_score > 0:
            risk_level = "low"
        else:
            risk_level = "none"

        return {
            "risk_factors": risk_factors,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "overall_assessment": self._get_risk_assessment(risk_level)
        }

    def _predict_milestones(self, context: Optional[Dict], history_data: Optional[Dict]) -> Dict[str, Any]:
        """预测关系里程碑"""
        milestone_predictions = []

        # 获取当前阶段
        current_stage = context.get("current_stage", "getting_to_know") if context else "getting_to_know"
        relationship_start = context.get("relationship_start_date") if context else None

        if relationship_start:
            days_together = self._days_since(relationship_start)

            # 预测下一个里程碑
            next_milestones = self._get_next_milestones(current_stage, days_together)
            milestone_predictions = next_milestones

        # 获取历史里程碑
        if history_data:
            milestone_history = history_data.get("milestone_history", [])
            completed_milestones = [
                {"name": m.get("name"), "date": m.get("date"), "significance": m.get("significance")}
                for m in milestone_history
            ]
        else:
            completed_milestones = []

        return {
            "milestone_predictions": milestone_predictions,
            "completed_milestones": completed_milestones,
            "relationship_timeline": self._generate_timeline(completed_milestones, milestone_predictions)
        }

    def _calculate_relationship_weather(self, context: Optional[Dict], history_data: Optional[Dict]) -> Dict[str, Any]:
        """计算关系天气"""
        # 基础分数
        score = 50

        # 根据互动频率调整
        if history_data:
            conversation_stats = history_data.get("conversation_stats", {})
            message_frequency = conversation_stats.get("recent_frequency", 50)
            score += min(25, message_frequency / 4)

            # 根据冲突调整
            conflict_history = history_data.get("conflict_history", [])
            recent_conflicts = len([c for c in conflict_history if self._is_recent(c.get("date", ""))])
            score -= recent_conflicts * 10

        # 根据上下文调整
        if context:
            interaction_quality = context.get("interaction_quality", "normal")
            if interaction_quality == "high":
                score += 15
            elif interaction_quality == "low":
                score -= 15

        # 限制分数范围
        score = min(100, max(0, score))

        # 确定天气类型
        weather = "cloudy"
        for weather_type, info in self.RELATIONSHIP_WEATHER.items():
            if score >= info["score_min"]:
                weather = weather_type
                break

        # 确定趋势
        trend = "stable"
        if score >= 70:
            trend = "rising"
        elif score < 40:
            trend = "declining"

        return {
            "relationship_score": round(score, 1),
            "weather": weather,
            "weather_name": self.RELATIONSHIP_WEATHER.get(weather, {}).get("name", "未知"),
            "trend": trend,
            "temperature": score  # 温度隐喻
        }

    def _generate_action_recommendations(self, prediction_result: Dict) -> List[Dict[str, Any]]:
        """生成行动建议"""
        recommendations = []

        weather = prediction_result.get("weather", "cloudy")
        trend = prediction_result.get("trend", "stable")
        risk_factors = prediction_result.get("risk_factors", [])

        # 根据天气给出建议
        if weather == "stormy" or weather == "rainy":
            recommendations.append({
                "type": "communication",
                "priority": "high",
                "title": "加强沟通",
                "description": "当前关系状态不佳，建议主动沟通，了解对方感受",
                "action": "安排一次深度对话，倾听对方的想法和感受"
            })

        if weather == "sunny":
            recommendations.append({
                "type": "celebration",
                "priority": "medium",
                "title": "庆祝美好时刻",
                "description": "关系状态很好，一起创造美好回忆吧",
                "action": "计划一次特别的约会，记录这个美好时刻"
            })

        # 根据趋势给出建议
        if trend == "declining":
            recommendations.append({
                "type": "reconnection",
                "priority": "high",
                "title": "重新连接",
                "description": "关系有降温趋势，需要主动经营",
                "action": "回顾美好回忆，安排一次重温初次的约会"
            })

        if trend == "rising":
            recommendations.append({
                "type": "momentum",
                "priority": "low",
                "title": "保持势头",
                "description": "关系正在升温，继续保持良好互动",
                "action": "维持当前的互动频率，适时推进关系"
            })

        # 根据风险因素给出建议
        for risk in risk_factors:
            if risk.get("type") == "frequent_conflicts":
                recommendations.append({
                    "type": "conflict_resolution",
                    "priority": "high",
                    "title": "解决冲突",
                    "description": "频繁冲突影响关系健康",
                    "action": "学习非暴力沟通技巧，寻求第三方调解"
                })

        return recommendations[:5]

    def _generate_message(self, prediction_result: Dict, analysis_type: str) -> str:
        """生成自然语言解读"""
        if analysis_type == "trend_prediction":
            trend = prediction_result.get("trend", "stable")
            trend_description = prediction_result.get("trend_description", "关系发展稳定")
            confidence = prediction_result.get("confidence", 0) * 100

            message = f"📈 关系趋势分析\n\n"
            message += f"当前趋势：{trend_description}\n"
            message += f"预测置信度：{confidence:.0f}%\n\n"

            if trend == "rising":
                message += "你们的关系正在升温，继续保持这样的互动节奏，关系会越来越好！"
            elif trend == "declining":
                message += "注意到你们的关系有些降温，建议主动沟通，找出问题所在。"
            else:
                message += "你们的关系发展平稳，这是健康关系的标志。"

        elif analysis_type == "risk_assessment":
            risk_level = prediction_result.get("risk_level", "none")
            risk_factors = prediction_result.get("risk_factors", [])
            risk_score = prediction_result.get("risk_score", 0)

            message = f"🔍 关系风险评估\n\n"
            message += f"风险等级：{self._translate_risk_level(risk_level)} (风险分：{risk_score})\n\n"

            if risk_factors:
                message += "检测到的风险因素：\n"
                for factor in risk_factors[:3]:
                    message += f"- {factor.get('name')}: {factor.get('description')}\n"
            else:
                message += "目前未检测到明显风险因素，继续保持！"

            message += f"\n\n整体评估：{prediction_result.get('overall_assessment', '关系健康状况良好')}"

        elif analysis_type == "milestone_prediction":
            predictions = prediction_result.get("milestone_predictions", [])
            completed = prediction_result.get("completed_milestones", [])

            message = f"🎯 关系里程碑预测\n\n"

            if completed:
                message += f"已完成的里程碑：{len(completed)}个\n"

            if predictions:
                message += "\n预计即将到来的里程碑：\n"
                for pred in predictions[:3]:
                    message += f"- {pred.get('name')}: {pred.get('timeframe', '未来几周内')}\n"
                    message += f"  建议：{pred.get('suggestion', '顺其自然')}\n"
            else:
                message += "关系发展自然，暂无特定里程碑预测"

        elif analysis_type == "relationship_weather":
            weather_name = prediction_result.get("weather_name", "未知")
            score = prediction_result.get("relationship_score", 50)
            trend = prediction_result.get("trend", "stable")

            message = f"🌤️ 关系气象报告\n\n"
            message += f"当前天气：{weather_name}\n"
            message += f"关系温度：{score:.1f}°C\n"
            message += f"发展趋势：{self._translate_trend(trend)}\n\n"

            if weather_name == "晴朗":
                message += "你们的关系阳光明媚，是享受恋爱美好的好时机！"
            elif weather_name == "多云":
                message += "关系总体良好，偶有些小云朵，但不会影响整体。"
            elif weather_name == "阴天":
                message += "关系有些沉闷，可能需要一些阳光来驱散阴霾。"
            elif weather_name == "小雨":
                message += "关系遇到一些小困扰，及时沟通能让雨过天晴。"
            else:
                message += "关系面临较大挑战，建议认真沟通或寻求专业帮助。"

        return message

    def _translate_risk_level(self, level: str) -> str:
        """翻译风险等级"""
        translation = {
            "none": "无风险",
            "low": "低风险",
            "medium": "中风险",
            "high": "高风险"
        }
        return translation.get(level, level)

    def _translate_trend(self, trend: str) -> str:
        """翻译趋势"""
        translation = {
            "rising": "升温↑",
            "declining": "降温↓",
            "stable": "稳定→"
        }
        return translation.get(trend, trend)

    def _build_ui(self, prediction_result: Dict, analysis_type: str) -> Dict[str, Any]:
        """构建 UI"""
        if analysis_type == "relationship_weather":
            return {
                "component_type": "relationship_weather_report",
                "props": {
                    "weather": prediction_result.get("weather", "cloudy"),
                    "weather_name": prediction_result.get("weather_name", "阴天"),
                    "temperature": prediction_result.get("relationship_score", 50),
                    "trend": prediction_result.get("trend", "stable"),
                    "recommendations": prediction_result.get("action_recommendations", [])[:3]
                }
            }

        elif analysis_type == "trend_prediction":
            return {
                "component_type": "relationship_trend_chart",
                "props": {
                    "trend": prediction_result.get("trend", "stable"),
                    "trend_direction": prediction_result.get("trend_direction", "horizontal"),
                    "score": prediction_result.get("relationship_score", 50),
                    "confidence": prediction_result.get("confidence", 0.5)
                }
            }

        elif analysis_type == "risk_assessment":
            return {
                "component_type": "risk_assessment_dashboard",
                "props": {
                    "risk_level": prediction_result.get("risk_level", "none"),
                    "risk_score": prediction_result.get("risk_score", 0),
                    "risk_factors": prediction_result.get("risk_factors", [])
                }
            }

        elif analysis_type == "milestone_prediction":
            return {
                "component_type": "milestone_timeline",
                "props": {
                    "completed": prediction_result.get("completed_milestones", []),
                    "predicted": prediction_result.get("milestone_predictions", []),
                    "timeline": prediction_result.get("relationship_timeline", [])
                }
            }

        return {"component_type": "prediction_empty", "props": {"message": "暂无预测数据"}}

    def _generate_actions(self, prediction_result: Dict) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []

        recommendations = prediction_result.get("action_recommendations", [])

        for rec in recommendations[:3]:
            actions.append({
                "label": rec.get("title", "建议"),
                "action_type": f"action_{rec.get('type', 'general')}",
                "params": {
                    "description": rec.get("description", ""),
                    "suggestion": rec.get("action", "")
                }
            })

        # 通用操作
        actions.append({
            "label": "查看详细报告",
            "action_type": "view_full_report",
            "params": {}
        })

        actions.append({
            "label": "获取专业建议",
            "action_type": "request_coach_help",
            "params": {}
        })

        return actions

    # ========== 辅助方法 ==========

    def _is_recent(self, date_str: str, days: int = 14) -> bool:
        """判断日期是否近期"""
        if not date_str:
            return False
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return (datetime.now() - date.replace(tzinfo=None)).days <= days
        except Exception:
            return False

    def _days_since(self, date_str: str) -> int:
        """计算距今天数"""
        if not date_str:
            return 0
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return (datetime.now() - date.replace(tzinfo=None)).days
        except Exception:
            return 0

    def _check_stage_mismatch(self, current_stage: str, days_together: int) -> bool:
        """检查关系阶段是否匹配"""
        # 简化实现：假设每个阶段有合理的时间范围
        stage_days = {
            "initial": (0, 7),
            "getting_to_know": (7, 30),
            "attraction": (30, 60),
            "dating": (60, 180),
            "exclusive": (180, 365),
            "deepening": (365, 730),
            "commitment": (730, 1460),
            "long_term": (1460, float('inf'))
        }

        expected_range = stage_days.get(current_stage, (0, float('inf')))
        return days_together < expected_range[0] or days_together > expected_range[1] * 2

    def _get_next_milestones(self, current_stage: str, days_together: int) -> List[Dict[str, Any]]:
        """获取下一个里程碑"""
        stage_order = list(self.RELATIONSHIP_STAGES.keys())

        if current_stage not in stage_order:
            return []

        current_index = stage_order.index(current_stage)
        next_stages = stage_order[current_index + 1:current_index + 3]  # 接下来 2 个阶段

        predictions = []
        for i, stage in enumerate(next_stages):
            predictions.append({
                "name": f"进入{self.RELATIONSHIP_STAGES[stage]['name']}",
                "stage": stage,
                "timeframe": f"未来{(i + 1) * 30}天内",
                "suggestion": f"为{self.RELATIONSHIP_STAGES[stage]['name']}做准备",
                "readiness": "calculating..."
            })

        return predictions

    def _generate_timeline(self, completed: List[Dict], predicted: List[Dict]) -> List[Dict]:
        """生成关系时间线"""
        timeline = []

        # 添加已完成的里程碑
        for milestone in completed:
            timeline.append({
                "type": "completed",
                "name": milestone.get("name"),
                "date": milestone.get("date"),
                "significance": milestone.get("significance")
            })

        # 添加预测的里程碑
        for milestone in predicted:
            timeline.append({
                "type": "predicted",
                "name": milestone.get("name"),
                "timeframe": milestone.get("timeframe"),
                "suggestion": milestone.get("suggestion")
            })

        return sorted(timeline, key=lambda x: x.get("date", x.get("timeframe", "")))

    def _get_risk_assessment(self, risk_level: str) -> str:
        """获取风险评估总结"""
        assessments = {
            "none": "关系健康状况良好，继续保持！",
            "low": "关系整体健康，注意小问题即可",
            "medium": "关系存在一些风险因素，建议主动改善",
            "high": "关系面临较大挑战，建议认真沟通或寻求专业帮助"
        }
        return assessments.get(risk_level, "无法评估")

    async def autonomous_trigger(
        self,
        user_a_id: str,
        user_b_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """
        自主触发关系预测

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            trigger_type: 触发类型 (weekly_checkin, cooling_detected, anniversary_reminder)
            context: 上下文信息

        Returns:
            触发结果
        """
        logger.info(f"RelationshipProphetSkill: Autonomous trigger for users={user_a_id},{user_b_id}, type={trigger_type}")

        # 判断是否需要触发
        should_trigger = False
        analysis_type = "relationship_weather"

        if trigger_type == "weekly_checkin":
            # 每周关系检查
            should_trigger = True
            analysis_type = "relationship_weather"
        elif trigger_type == "cooling_detected":
            # 检测到关系降温
            should_trigger = True
            analysis_type = "trend_prediction"
        elif trigger_type == "anniversary_reminder":
            # 纪念日提醒
            should_trigger = True
            analysis_type = "milestone_prediction"

        if should_trigger:
            result = await self.execute(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                analysis_type=analysis_type,
                context=context
            )
            return {
                "triggered": True,
                "result": result,
                "should_push": True
            }

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_relationship_prophet_skill_instance: Optional[RelationshipProphetSkill] = None


def get_relationship_prophet_skill() -> RelationshipProphetSkill:
    """获取关系预测 Skill 单例实例"""
    global _relationship_prophet_skill_instance
    if _relationship_prophet_skill_instance is None:
        _relationship_prophet_skill_instance = RelationshipProphetSkill()
    return _relationship_prophet_skill_instance
