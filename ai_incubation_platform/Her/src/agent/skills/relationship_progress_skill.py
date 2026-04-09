"""
关系进展追踪 Skill

AI 关系助手 - 关系进展记录、时间线追踪、健康度评估、可视化生成
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class RelationshipProgressSkill:
    """
    关系进展追踪 Skill - 帮助用户追踪和分析关系发展

    核心能力:
    - 关系进展记录：记录关键里程碑（第一次消息、约会等）
    - 时间线追踪：可视化展示关系发展历程
    - 健康度评估：多维度分析关系健康状况
    - 智能建议：基于数据生成关系发展建议

    自主触发:
    - 检测到重要互动（首次约会、交换联系方式）
    - 关系阶段变化时
    - 定期生成关系报告（每周/每月）
    - 互动频率显著下降时发出提醒
    """

    name = "relationship_progress"
    version = "1.0.0"
    description = """
    AI 关系助手，追踪和分析关系发展

    能力:
    - 关系进展记录：记录关键里程碑
    - 时间线追踪：可视化展示关系发展历程
    - 健康度评估：多维度分析关系健康状况
    - 智能建议：基于数据生成关系发展建议
    """

    # 关系阶段定义
    RELATIONSHIP_STAGES = {
        "matched": {"order": 1, "label": "已匹配", "description": "系统匹配成功"},
        "chatting": {"order": 2, "label": "聊天中", "description": "开始互动交流"},
        "exchanged_contact": {"order": 3, "label": "交换联系方式", "description": "交换微信/电话等"},
        "first_date": {"order": 4, "label": "首次约会", "description": "完成第一次线下见面"},
        "dating": {"order": 5, "label": "约会中", "description": "定期约会阶段"},
        "exclusive": {"order": 6, "label": "确定关系", "description": "确立排他性关系"},
        "in_relationship": {"order": 7, "label": "恋爱中", "description": "稳定恋爱关系"}
    }

    # 里程碑类型
    MILESTONE_TYPES = {
        "first_message": "第一条消息",
        "first_like": "第一次点赞",
        "deep_conversation": "深度对话",
        "contact_exchange": "交换联系方式",
        "first_date": "第一次约会",
        "anniversary": "纪念日",
        "relationship_milestone": "关系里程碑"
    }

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["record", "timeline", "health_score", "visualize", "analyze"],
                    "description": "操作类型"
                },
                "user_id_1": {
                    "type": "string",
                    "description": "用户 ID 1"
                },
                "user_id_2": {
                    "type": "string",
                    "description": "用户 ID 2"
                },
                "progress_type": {
                    "type": "string",
                    "description": "进展类型 (first_message, first_date, contact_exchange, etc.)"
                },
                "description": {
                    "type": "string",
                    "description": "进展描述"
                },
                "progress_score": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "进展评分 (1-10)"
                },
                "related_data": {
                    "type": "object",
                    "description": "相关数据"
                }
            },
            "required": ["operation", "user_id_1", "user_id_2"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "relationship_data": {
                    "type": "object",
                    "properties": {
                        "current_stage": {"type": "string"},
                        "health_score": {"type": "number"},
                        "milestones": {"type": "array"},
                        "timeline": {"type": "array"},
                        "suggestions": {"type": "array"}
                    }
                },
                "generative_ui": {
                    "type": "object",
                    "properties": {
                        "component_type": {"type": "string"},
                        "props": {"type": "object"}
                    }
                },
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "relationship_data"]
        }

    async def execute(
        self,
        operation: str,
        user_id_1: str,
        user_id_2: str,
        progress_type: Optional[str] = None,
        description: Optional[str] = None,
        progress_score: Optional[int] = None,
        related_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行关系进展 Skill

        Args:
            operation: 操作类型 (record, timeline, health_score, visualize, analyze)
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            progress_type: 进展类型
            description: 进展描述
            progress_score: 进展评分
            related_data: 相关数据
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"RelationshipProgressSkill: Executing operation={operation} for {user_id_1} & {user_id_2}")

        start_time = datetime.now()

        # 导入服务
        from services.relationship_progress_service import relationship_progress_service

        try:
            # 根据操作类型执行不同逻辑
            if operation == "record":
                result = self._record_progress(
                    relationship_progress_service,
                    user_id_1, user_id_2,
                    progress_type, description, progress_score, related_data
                )
            elif operation == "timeline":
                result = self._get_timeline(relationship_progress_service, user_id_1, user_id_2)
            elif operation == "health_score":
                result = self._get_health_score(relationship_progress_service, user_id_1, user_id_2)
            elif operation == "visualize":
                result = self._get_visualization(relationship_progress_service, user_id_1, user_id_2)
            elif operation == "analyze":
                result = self._analyze_relationship(relationship_progress_service, user_id_1, user_id_2)
            else:
                return {
                    "success": False,
                    "ai_message": f"未知操作类型：{operation}",
                    "error": f"Unknown operation: {operation}"
                }

            # 生成 AI 消息
            ai_message = self._generate_ai_message(result, operation)

            # 构建 Generative UI
            generative_ui = self._build_generative_ui(result, operation)

            # 生成建议操作
            suggested_actions = self._generate_actions(result, operation)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return {
                "success": True,
                "ai_message": ai_message,
                "relationship_data": result,
                "generative_ui": generative_ui,
                "suggested_actions": suggested_actions,
                "skill_metadata": {
                    "name": self.name,
                    "version": self.version,
                    "execution_time_ms": int(execution_time),
                    "operation": operation
                }
            }

        except Exception as e:
            logger.error(f"RelationshipProgressSkill: Execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "ai_message": "关系分析失败，请稍后重试",
                "error": str(e)
            }

    def _record_progress(
        self,
        service,
        user_id_1: str,
        user_id_2: str,
        progress_type: Optional[str],
        description: Optional[str],
        progress_score: Optional[int],
        related_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """记录关系进展"""
        if not progress_type:
            raise ValueError("progress_type is required for record operation")

        progress_id = service.record_progress(
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            progress_type=progress_type,
            description=description or self.MILESTONE_TYPES.get(progress_type, progress_type),
            progress_score=progress_score or 5,
            related_data=related_data or {}
        )

        return {
            "progress_id": progress_id,
            "progress_type": progress_type,
            "progress_type_label": self.MILESTONE_TYPES.get(progress_type, progress_type),
            "status": "recorded"
        }

    def _get_timeline(self, service, user_id_1: str, user_id_2: str) -> Dict[str, Any]:
        """获取关系时间线"""
        return service.get_progress_timeline(user_id_1, user_id_2)

    def _get_health_score(self, service, user_id_1: str, user_id_2: str) -> Dict[str, Any]:
        """获取关系健康度评分"""
        return service.get_relationship_health_score(user_id_1, user_id_2)

    def _get_visualization(self, service, user_id_1: str, user_id_2: str) -> Dict[str, Any]:
        """获取可视化数据"""
        return service.get_visualization_data(user_id_1, user_id_2)

    def _analyze_relationship(self, service, user_id_1: str, user_id_2: str) -> Dict[str, Any]:
        """综合分析关系状态"""
        timeline = service.get_progress_timeline(user_id_1, user_id_2)
        health = service.get_relationship_health_score(user_id_1, user_id_2)

        return {
            "timeline": timeline,
            "health_score": health,
            "summary": self._generate_relationship_summary(timeline, health)
        }

    def _generate_relationship_summary(self, timeline: Dict, health: Dict) -> str:
        """生成关系状态总结"""
        stage = timeline.get("current_stage_label", "未知")
        health_level = health.get("health_level", "unknown")
        score = health.get("overall_score", 0)
        milestone_count = timeline.get("total_milestones", 0)

        summary = f"你们的关系处于「{stage}」阶段，"
        summary += f"健康度{score:.1f}分（{self._get_health_label(health_level)}），"
        summary += f"已记录{milestone_count}个里程碑。"

        return summary

    def _get_health_label(self, health_level: str) -> str:
        """获取健康等级标签"""
        labels = {
            "excellent": "优秀",
            "good": "良好",
            "fair": "一般",
            "needs_attention": "需要关注",
            "no_data": "暂无数据"
        }
        return labels.get(health_level, "未知")

    def _generate_ai_message(self, result: Dict, operation: str) -> str:
        """生成 AI 自然语言消息"""
        if operation == "record":
            progress_type = result.get("progress_type_label", "进展")
            return f"已记录关系进展：{progress_type}。继续用心经营你们的关系吧~"

        elif operation == "timeline":
            stage = result.get("current_stage_label", "未知")
            milestone_count = result.get("total_milestones", 0)
            return f"你们的关系处于「{stage}」阶段，已共同走过{milestone_count}个里程碑。"

        elif operation == "health_score":
            score = result.get("overall_score", 0)
            level = result.get("health_level", "unknown")
            suggestions = result.get("suggestions", [])

            message = f"关系健康度评分：{score:.1f}分（{self._get_health_label(level)}）\n\n"
            if suggestions:
                message += "建议：\n"
                for i, sug in enumerate(suggestions[:3], 1):
                    message += f"{i}. {sug}\n"
            return message

        elif operation == "visualize":
            timeline = result.get("timeline", {})
            health = result.get("health_score", {})
            return self._generate_relationship_summary(timeline, health)

        elif operation == "analyze":
            summary = result.get("summary", "")
            return summary

        return "关系分析完成"

    def _build_generative_ui(self, result: Dict, operation: str) -> Dict[str, Any]:
        """构建 Generative UI 配置"""
        if operation == "record":
            return {
                "component_type": "milestone_card",
                "props": {
                    "type": result.get("progress_type_label", ""),
                    "status": "recorded",
                    "icon": "celebration"
                }
            }

        elif operation == "timeline":
            return {
                "component_type": "relationship_timeline",
                "props": {
                    "current_stage": result.get("current_stage_label", ""),
                    "milestones": result.get("timeline", []),
                    "show_progress_indicator": True
                }
            }

        elif operation == "health_score":
            score = result.get("overall_score", 0)
            level = result.get("health_level", "unknown")

            # 根据健康等级选择颜色和图标
            color_map = {
                "excellent": "green",
                "good": "blue",
                "fair": "yellow",
                "needs_attention": "orange",
                "no_data": "gray"
            }

            return {
                "component_type": "health_score_card",
                "props": {
                    "score": score,
                    "max_score": 10,
                    "level": level,
                    "color": color_map.get(level, "gray"),
                    "dimensions": result.get("dimensions", {}),
                    "suggestions": result.get("suggestions", [])
                }
            }

        elif operation == "visualize":
            chart_data = result.get("chart_data", {})
            return {
                "component_type": "relationship_chart",
                "props": {
                    "chart_type": "line",
                    "labels": chart_data.get("labels", []),
                    "activity_data": chart_data.get("activity_data", []),
                    "stage_changes": chart_data.get("stage_changes", [])
                }
            }

        elif operation == "analyze":
            return {
                "component_type": "relationship_dashboard",
                "props": {
                    "summary": result.get("summary", ""),
                    "timeline": result.get("timeline", {}),
                    "health_score": result.get("health_score", {})
                }
            }

        # 默认空状态
        return {
            "component_type": "empty_state",
            "props": {
                "message": "暂无数据",
                "description": "开始记录你们的关系里程碑吧"
            }
        }

    def _generate_actions(self, result: Dict, operation: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []

        if operation == "record":
            actions.append({
                "label": "查看时间线",
                "action_type": "view_timeline",
                "params": {}
            })
            actions.append({
                "label": "查看健康度",
                "action_type": "view_health_score",
                "params": {}
            })

        elif operation == "timeline":
            actions.append({
                "label": "记录新进展",
                "action_type": "record_progress",
                "params": {}
            })
            actions.append({
                "label": "查看健康度",
                "action_type": "view_health_score",
                "params": {}
            })

        elif operation == "health_score":
            suggestions = result.get("suggestions", [])
            if suggestions:
                actions.append({
                    "label": "查看改进建议",
                    "action_type": "view_suggestions",
                    "params": {}
                })
            actions.append({
                "label": "记录新进展",
                "action_type": "record_progress",
                "params": {}
            })

        elif operation == "visualize":
            actions.append({
                "label": "导出报告",
                "action_type": "export_report",
                "params": {}
            })
            actions.append({
                "label": "分享时间线",
                "action_type": "share_timeline",
                "params": {}
            })

        elif operation == "analyze":
            actions.append({
                "label": "查看详细分析",
                "action_type": "view_full_analysis",
                "params": {}
            })
            actions.append({
                "label": "制定关系计划",
                "action_type": "create_relationship_plan",
                "params": {}
            })

        return actions

    async def autonomous_trigger(
        self,
        user_id_1: str,
        user_id_2: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """
        自主触发关系分析

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            trigger_type: 触发类型 (milestone_detected, weekly_report, activity_drop)
            context: 上下文信息

        Returns:
            触发结果
        """
        logger.info(f"RelationshipProgressSkill: Autonomous trigger for {user_id_1} & {user_id_2}, type={trigger_type}")

        try:
            from services.relationship_progress_service import relationship_progress_service

            if trigger_type == "milestone_detected":
                # 检测到里程碑事件
                result = await self.execute(
                    operation="analyze",
                    user_id_1=user_id_1,
                    user_id_2=user_id_2
                )
                return {
                    "triggered": True,
                    "result": result,
                    "should_push": True,
                    "push_message": f"检测到你们关系的新进展！{result.get('ai_message', '')}"
                }

            elif trigger_type == "weekly_report":
                # 每周关系报告
                result = await self.execute(
                    operation="health_score",
                    user_id_1=user_id_1,
                    user_id_2=user_id_2
                )
                return {
                    "triggered": True,
                    "result": result,
                    "should_push": True,
                    "push_message": f"本周关系报告已生成：健康度{result.get('relationship_data', {}).get('overall_score', 0):.1f}分"
                }

            elif trigger_type == "activity_drop":
                # 互动频率下降提醒
                health = relationship_progress_service.get_relationship_health_score(user_id_1, user_id_2)
                suggestions = health.get("suggestions", [])

                return {
                    "triggered": True,
                    "result": {"health_score": health},
                    "should_push": True,
                    "push_message": f"注意到你们最近的互动减少了。{suggestions[0] if suggestions else '多联系彼此吧~'}"
                }

        except Exception as e:
            logger.error(f"RelationshipProgressSkill: Autonomous trigger failed: {e}")
            return {"triggered": False, "error": str(e)}

        return {"triggered": False, "reason": "unknown_trigger"}


# 全局 Skill 实例
_relationship_progress_skill_instance: Optional[RelationshipProgressSkill] = None


def get_relationship_progress_skill() -> RelationshipProgressSkill:
    """获取关系进展 Skill 单例实例"""
    global _relationship_progress_skill_instance
    if _relationship_progress_skill_instance is None:
        _relationship_progress_skill_instance = RelationshipProgressSkill()
    return _relationship_progress_skill_instance
