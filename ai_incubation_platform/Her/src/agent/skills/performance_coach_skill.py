"""
Performance Coach Skill - 关系绩效教练

AI 关系教练核心 Skill - 里程碑追踪、约会建议、互动游戏分析
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class PerformanceCoachSkill:
    """
    AI 关系教练 Skill - 关系绩效与互动指导

    核心能力:
    - 里程碑追踪：记录和分析关系重要时刻
    - 约会建议：生成个性化约会方案
    - 互动游戏分析：分析游戏结果提供关系洞察
    - 关系绩效评估：综合评估关系健康度

    自主触发:
    - 重要里程碑即将到来的提醒
    - 关系进入新阶段的庆祝
    - 互动游戏完成后的洞察推送
    - 定期关系绩效评估
    """

    name = "performance_coach"
    version = "1.0.0"
    description = """
    AI 关系教练，关系绩效与互动指导

    能力:
    - 里程碑追踪：记录和分析关系重要时刻
    - 约会建议：生成个性化约会方案
    - 互动游戏分析：分析游戏结果提供关系洞察
    - 关系绩效评估：综合评估关系健康度
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_a_id": {"type": "string", "description": "用户 A ID"},
                "user_b_id": {"type": "string", "description": "用户 B ID"},
                "service_type": {
                    "type": "string",
                    "enum": ["milestone_tracking", "date_suggestion", "game_analysis", "relationship_assessment"],
                    "description": "服务类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "relationship_stage": {"type": "string"},
                        "days_together": {"type": "number"},
                        "game_id": {"type": "string"},
                        "date_type": {"type": "string"}
                    }
                }
            },
            "required": ["user_a_id", "user_b_id", "service_type"]
        }

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "coach_result": {
                    "type": "object",
                    "properties": {
                        "service_type": {"type": "string"},
                        "milestones": {"type": "array"},
                        "suggestions": {"type": "array"},
                        "game_insights": {"type": "object"},
                        "assessment": {"type": "object"},
                        "recommendations": {"type": "array"}
                    }
                },
                "generative_ui": {"type": "object"},
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "coach_result"]
        }

    async def execute(
        self,
        user_a_id: str,
        user_b_id: str,
        service_type: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        logger.info(f"PerformanceCoachSkill: Executing for users={user_a_id},{user_b_id}, type={service_type}")

        start_time = datetime.now()

        # 根据服务类型提供分析
        result = self._analyze_relationship(service_type, user_a_id, user_b_id, context)

        ai_message = self._generate_message(result, service_type)
        generative_ui = self._build_ui(result, service_type)
        suggested_actions = self._generate_actions(service_type)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "coach_result": result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time)
            }
        }

    def _analyze_relationship(
        self,
        service_type: str,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """分析关系数据"""
        result = {
            "service_type": service_type,
            "milestones": [],
            "suggestions": [],
            "game_insights": {},
            "assessment": {},
            "recommendations": []
        }

        if service_type == "milestone_tracking":
            result["milestones"] = self._track_milestones(user_a_id, user_b_id, context)
            result["recommendations"] = self._generate_milestone_recommendations(result["milestones"])

        elif service_type == "date_suggestion":
            result["suggestions"] = self._generate_date_suggestions(user_a_id, user_b_id, context)
            result["recommendations"] = self._generate_date_recommendations(result["suggestions"])

        elif service_type == "game_analysis":
            result["game_insights"] = self._analyze_game_results(user_a_id, user_b_id, context)
            result["recommendations"] = self._generate_game_recommendations(result["game_insights"])

        elif service_type == "relationship_assessment":
            result["assessment"] = self._assess_relationship(user_a_id, user_b_id, context)
            result["recommendations"] = self._generate_assessment_recommendations(result["assessment"])

        return result

    def _track_milestones(
        self,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict]
    ) -> List[Dict]:
        """追踪里程碑"""
        days_together = (context or {}).get("days_together", 30)
        relationship_stage = (context or {}).get("relationship_stage", "dating")

        # 基于关系阶段生成里程碑
        milestones = [
            {
                "type": "first_contact",
                "title": "初次相遇",
                "description": "你们的第一次交流",
                "completed": True,
                "significance": 0.8
            },
            {
                "type": "first_date",
                "title": "第一次约会",
                "description": "线下的第一次见面",
                "completed": days_together >= 7,
                "significance": 0.9
            },
            {
                "type": "confession",
                "title": "表白",
                "description": "正式确立关系的表白",
                "completed": relationship_stage in ["exclusive", "committed"],
                "significance": 1.0
            },
            {
                "type": "100_days",
                "title": "百日纪念",
                "description": "在一起 100 天",
                "completed": days_together >= 100,
                "significance": 0.7
            },
            {
                "type": "first_trip",
                "title": "第一次旅行",
                "description": "一起出行",
                "completed": False,
                "significance": 0.75
            },
            {
                "type": "meet_friends",
                "title": "见朋友",
                "description": "介绍给彼此的朋友",
                "completed": relationship_stage in ["deepening", "committed"],
                "significance": 0.6
            }
        ]

        return milestones

    def _generate_date_suggestions(
        self,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict]
    ) -> List[Dict]:
        """生成约会建议"""
        date_type = (context or {}).get("date_type", "casual")
        relationship_stage = (context or {}).get("relationship_stage", "dating")

        suggestions = {
            "first_date": [
                {
                    "type": "coffee",
                    "title": "咖啡馆闲聊",
                    "description": "安静的咖啡馆，轻松交流",
                    "duration": "1-2 小时",
                    "budget": "¥50-100",
                    "suitability": 0.9
                },
                {
                    "type": "museum",
                    "title": "艺术展览",
                    "description": "一起欣赏艺术，寻找共同话题",
                    "duration": "2-3 小时",
                    "budget": "¥100-200",
                    "suitability": 0.8
                }
            ],
            "casual": [
                {
                    "type": "park_walk",
                    "title": "公园散步",
                    "description": "自然风光中轻松漫步",
                    "duration": "1-2 小时",
                    "budget": "免费",
                    "suitability": 0.85
                },
                {
                    "type": "food_market",
                    "title": "美食市集",
                    "description": "一起品尝各种小吃",
                    "duration": "2-3 小时",
                    "budget": "¥100-150",
                    "suitability": 0.8
                }
            ],
            "romantic": [
                {
                    "type": "sunset_view",
                    "title": "观景台看日落",
                    "description": "浪漫日落时分",
                    "duration": "2-3 小时",
                    "budget": "¥100-200",
                    "suitability": 0.95
                },
                {
                    "type": "fine_dining",
                    "title": "精致晚餐",
                    "description": "高级餐厅的浪漫晚餐",
                    "duration": "2-3 小时",
                    "budget": "¥500+",
                    "suitability": 0.9
                }
            ],
            "adventure": [
                {
                    "type": "escape_room",
                    "title": "密室逃脱",
                    "description": "考验默契的密室挑战",
                    "duration": "1-2 小时",
                    "budget": "¥200-300",
                    "suitability": 0.85
                },
                {
                    "type": "hiking",
                    "title": "登山徒步",
                    "description": "一起征服山峰",
                    "duration": "4-6 小时",
                    "budget": "¥100-200",
                    "suitability": 0.8
                }
            ]
        }

        return suggestions.get(date_type, suggestions["casual"])

    def _analyze_game_results(
        self,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """分析游戏结果"""
        game_id = (context or {}).get("game_id")

        return {
            "game_id": game_id or "demo_game",
            "game_type": "qna_mutual",
            "completion_rate": 0.85,
            "compatibility_analysis": {
                "overall": 0.82,
                "values": 0.88,
                "interests": 0.75,
                "communication": 0.85,
                "lifestyle": 0.80
            },
            "strengths": [
                "价值观高度一致",
                "沟通方式匹配",
                "对未来的规划相似"
            ],
            "growth_areas": [
                "兴趣爱好可以更多探索",
                "生活习惯需要更多磨合"
            ],
            "ai_insights": "你们在核心价值观上表现出高度一致性，这是长久关系的重要基础。在兴趣爱好方面，虽然目前重叠不多，但这正是互相探索、共同成长的机会。",
            "recommended_activities": [
                "一起尝试新的爱好",
                "参加双人互动课程",
                "制定共同的小目标"
            ]
        }

    def _assess_relationship(
        self,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """评估关系健康度"""
        days_together = (context or {}).get("days_together", 30)
        relationship_stage = (context or {}).get("relationship_stage", "dating")

        # 关系健康度评估
        assessment = {
            "overall_health_score": 0.78,
            "health_level": "良好",
            "dimensions": {
                "communication": {
                    "score": 0.82,
                    "level": "良好",
                    "description": "沟通频率和质量都不错"
                },
                "trust": {
                    "score": 0.85,
                    "level": "优秀",
                    "description": "彼此信任度高"
                },
                "intimacy": {
                    "score": 0.72,
                    "level": "良好",
                    "description": "亲密度稳步提升"
                },
                "shared_values": {
                    "score": 0.80,
                    "level": "良好",
                    "description": "价值观较为一致"
                },
                "conflict_resolution": {
                    "score": 0.68,
                    "level": "需关注",
                    "description": "处理冲突的方式可以改进"
                }
            },
            "relationship_stage": relationship_stage,
            "days_together": days_together,
            "milestone_progress": 0.65,
            "trend": "upward",
            "strengths": [
                "信任基础牢固",
                "沟通开放诚实",
                "价值观高度一致"
            ],
            "growth_opportunities": [
                "学习更有效的冲突解决技巧",
                "增加深度交流的时间",
                "培养共同爱好"
            ]
        }

        return assessment

    def _generate_milestone_recommendations(self, milestones: List[Dict]) -> List[Dict]:
        """生成里程碑建议"""
        recommendations = []

        # 检查即将达成的里程碑
        upcoming = [m for m in milestones if not m.get("completed")]
        if upcoming:
            next_milestone = upcoming[0]
            recommendations.append({
                "type": "milestone_preparation",
                "priority": "high",
                "title": f"准备达成「{next_milestone['title']}」",
                "suggestion": f"{next_milestone['description']}，建议提前规划",
                "action": "plan_milestone"
            })

        # 检查已完成的里程碑是否需要庆祝
        completed = [m for m in milestones if m.get("completed")]
        if completed and not completed[-1].get("celebrated"):
            recommendations.append({
                "type": "celebration",
                "priority": "medium",
                "title": f"庆祝「{completed[-1]['title']}」",
                "suggestion": "一起纪念这个重要时刻",
                "action": "celebrate"
            })

        return recommendations

    def _generate_date_recommendations(self, suggestions: List[Dict]) -> List[Dict]:
        """生成约会建议"""
        recommendations = []

        if suggestions:
            best_suggestion = max(suggestions, key=lambda x: x.get("suitability", 0))
            recommendations.append({
                "type": "date_recommendation",
                "priority": "medium",
                "title": f"推荐约会：{best_suggestion['title']}",
                "suggestion": f"{best_suggestion['description']}，适合度 {best_suggestion.get('suitability', 0)*100:.0f}%",
                "action": "plan_date"
            })

        recommendations.append({
            "type": "preparation",
            "priority": "low",
            "title": "约会准备",
            "suggestion": "提前规划路线，准备话题",
            "action": "prepare"
        })

        return recommendations

    def _generate_game_recommendations(self, game_insights: Dict) -> List[Dict]:
        """生成游戏建议"""
        recommendations = []

        compatibility = game_insights.get("compatibility_analysis", {})
        overall = compatibility.get("overall", 0)

        if overall >= 0.8:
            recommendations.append({
                "type": "encouragement",
                "priority": "medium",
                "title": "兼容性优秀",
                "suggestion": f"你们的综合兼容性为{overall*100:.0f}%，继续保持深度交流",
                "action": "continue_engaging"
            })
        elif overall >= 0.6:
            recommendations.append({
                "type": "improvement",
                "priority": "medium",
                "title": "兼容性良好",
                "suggestion": f"兼容性{overall*100:.0f}%，有提升空间",
                "action": "improve_connection"
            })
        else:
            recommendations.append({
                "type": "attention",
                "priority": "high",
                "title": "需要关注",
                "suggestion": "建议增加沟通，了解彼此差异",
                "action": "communicate_more"
            })

        # 基于优势的建议
        for strength in game_insights.get("strengths", [])[:2]:
            recommendations.append({
                "type": "strength_reinforcement",
                "priority": "low",
                "title": "发挥优势",
                "suggestion": strength,
                "action": "reinforce"
            })

        return recommendations

    def _generate_assessment_recommendations(self, assessment: Dict) -> List[Dict]:
        """生成评估建议"""
        recommendations = []

        # 基于整体健康度
        health_score = assessment.get("overall_health_score", 0)
        if health_score >= 0.8:
            recommendations.append({
                "type": "maintenance",
                "priority": "low",
                "title": "关系健康",
                "suggestion": "关系状态良好，继续保持当前的互动模式",
                "action": "maintain"
            })
        elif health_score >= 0.6:
            recommendations.append({
                "type": "improvement",
                "priority": "medium",
                "title": "稳步提升",
                "suggestion": "关系整体健康，某些方面可以进一步优化",
                "action": "improve"
            })
        else:
            recommendations.append({
                "type": "attention_needed",
                "priority": "high",
                "title": "需要关注",
                "suggestion": "建议增加沟通，必要时寻求专业指导",
                "action": "seek_help"
            })

        # 基于维度的建议
        dimensions = assessment.get("dimensions", {})
        for dim_name, dim_data in dimensions.items():
            if dim_data.get("score", 1) < 0.7:
                recommendations.append({
                    "type": "dimension_improvement",
                    "priority": "high",
                    "title": f"提升{self._get_dimension_name(dim_name)}",
                    "suggestion": dim_data.get("description", ""),
                    "action": f"improve_{dim_name}"
                })

        return recommendations

    def _get_dimension_name(self, dim_key: str) -> str:
        """获取维度中文名称"""
        names = {
            "communication": "沟通",
            "trust": "信任",
            "intimacy": "亲密",
            "shared_values": "价值观",
            "conflict_resolution": "冲突处理"
        }
        return names.get(dim_key, dim_key)

    def _generate_message(self, result: Dict, service_type: str) -> str:
        """生成自然语言解读"""
        if service_type == "milestone_tracking":
            milestones = result.get("milestones", [])
            completed = sum(1 for m in milestones if m.get("completed"))

            message = f"🎯 关系里程碑追踪\n\n"
            message += f"已完成：{completed}/{len(milestones)} 个里程碑\n\n"

            for milestone in milestones[:5]:
                icon = "✓" if milestone.get("completed") else "○"
                message += f"{icon} {milestone['title']}: {milestone['description']}\n"

            return message

        elif service_type == "date_suggestion":
            suggestions = result.get("suggestions", [])
            message = "💕 约会建议\n\n"

            for suggestion in suggestions[:3]:
                message += f"【{suggestion['title']}】\n"
                message += f"{suggestion['description']}\n"
                message += f"时长：{suggestion.get('duration', '未知')} | 预算：{suggestion.get('budget', '未知')}\n\n"

            return message

        elif service_type == "game_analysis":
            insights = result.get("game_insights", {})
            compatibility = insights.get("compatibility_analysis", {})

            message = "🎮 游戏分析结果\n\n"
            message += f"综合兼容性：{compatibility.get('overall', 0)*100:.0f}%\n\n"

            message += "优势：\n"
            for strength in insights.get("strengths", [])[:3]:
                message += f"✓ {strength}\n"

            message += "\n成长空间：\n"
            for area in insights.get("growth_areas", [])[:3]:
                message += f"○ {area}\n"

            return message

        elif service_type == "relationship_assessment":
            assessment = result.get("assessment", {})

            message = f"📊 关系健康度评估\n\n"
            message += f"整体评分：{assessment.get('overall_health_score', 0)*100:.0f} 分 ({assessment.get('health_level', '未知')})\n\n"

            message += "各维度评分：\n"
            for dim_name, dim_data in assessment.get("dimensions", {}).items():
                cn_name = self._get_dimension_name(dim_name)
                message += f"• {cn_name}: {dim_data.get('score', 0)*100:.0f}分 ({dim_data.get('level', '未知')})\n"

            return message

        return "关系分析已完成"

    def _build_ui(self, result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        return {
            "component_type": "performance_coach_dashboard",
            "props": {
                "service_type": service_type,
                "data": result
            }
        }

    def _generate_actions(self, service_type: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = [
            {"label": "查看详细报告", "action_type": "view_full_report", "params": {}},
            {"label": "保存分析结果", "action_type": "save_analysis", "params": {}}
        ]

        if service_type == "milestone_tracking":
            actions.append({"label": "创建里程碑", "action_type": "create_milestone", "params": {}})
        elif service_type == "date_suggestion":
            actions.append({"label": "计划约会", "action_type": "plan_date", "params": {}})
        elif service_type == "game_analysis":
            actions.append({"label": "开始新游戏", "action_type": "start_game", "params": {}})

        return actions

    async def autonomous_trigger(
        self,
        user_a_id: str,
        user_b_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """自主触发"""
        logger.info(f"PerformanceCoachSkill: Autonomous trigger for users={user_a_id},{user_b_id}, type={trigger_type}")

        if trigger_type == "milestone_reminder":
            result = await self.execute(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                service_type="milestone_tracking",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": True}

        elif trigger_type == "game_completed":
            result = await self.execute(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                service_type="game_analysis",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": True}

        elif trigger_type == "weekly_assessment":
            result = await self.execute(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                service_type="relationship_assessment",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": False}

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_performance_coach_skill_instance: Optional[PerformanceCoachSkill] = None


def get_performance_coach_skill() -> PerformanceCoachSkill:
    """获取关系绩效教练 Skill 单例实例"""
    global _performance_coach_skill_instance
    if _performance_coach_skill_instance is None:
        _performance_coach_skill_instance = PerformanceCoachSkill()
    return _performance_coach_skill_instance
