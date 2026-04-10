"""
约会助手 Skill - 约会实战辅助

⚠️ DEPRECATED: 此 Skill 已废弃，请使用 DateCoachSkill 替代。
DateCoachSkill 已整合所有功能，包括新增的 realtime_help 服务类型。

迁移指南:
- DateAssistantSkill.outfit → DateCoachSkill.outfit_recommendation
- DateAssistantSkill.venue → DateCoachSkill.venue_strategy
- DateAssistantSkill.topics → DateCoachSkill.topic_kit
- DateAssistantSkill.realtime_help → DateCoachSkill.realtime_help

将在下一个版本移除。
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class DateAssistantSkill:
    """
    AI 约会助手 Skill - 约会实战中的贴身顾问

    核心能力:
    - 穿搭推荐：根据场合、天气、对方喜好推荐着装
    - 场所策略：推荐适合的约会地点
    - 话题锦囊：提供话题、破冰句、应对策略
    - 实时指导：约会中的悄悄话建议

    自主触发:
    - 约会前 1 小时提醒
    - 检测到约会邀请
    - 约会中主动提供支持
    """

    name = "date_assistant"
    version = "1.0.0"
    description = """
    AI 约会助手，约会实战中的贴身顾问

    能力:
    - 穿搭推荐：根据场合、天气推荐着装
    - 场所策略：推荐适合的约会地点
    - 话题锦囊：提供破冰话题、深度交流问题
    - 实时指导：约会中的悄悄话建议
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID"},
                "service_type": {
                    "type": "string",
                    "enum": ["outfit", "venue", "topics", "realtime_help"],
                    "description": "服务类型"
                },
                "date_context": {
                    "type": "object",
                    "properties": {
                        "date_type": {"type": "string"},
                        "weather": {"type": "string"},
                        "venue_type": {"type": "string"},
                        "relationship_stage": {"type": "string"}
                    }
                }
            },
            "required": ["user_id", "service_type"]
        }

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "assistant_result": {
                    "type": "object",
                    "properties": {
                        "service_type": {"type": "string"},
                        "recommendations": {"type": "array"},
                        "tips": {"type": "array"}
                    }
                },
                "generative_ui": {"type": "object"},
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "assistant_result"]
        }

    async def execute(
        self,
        user_id: str,
        service_type: str,
        date_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        logger.info(f"DateAssistantSkill: Executing for user={user_id}, type={service_type}")

        start_time = datetime.now()

        # 根据服务类型提供支持
        result = self._provide_assistance(service_type, date_context, user_id)

        ai_message = self._generate_message(result, service_type)
        generative_ui = self._build_ui(result, service_type)
        suggested_actions = self._generate_actions(service_type)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "assistant_result": result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time)
            }
        }

    def _provide_assistance(
        self,
        service_type: str,
        date_context: Optional[Dict],
        user_id: str
    ) -> Dict[str, Any]:
        """提供约会协助"""
        result = {
            "service_type": service_type,
            "recommendations": [],
            "tips": []
        }

        if service_type == "outfit":
            result["recommendations"] = self._recommend_outfit(date_context)
            result["tips"] = ["保持整洁最重要", "舒适自信是关键"]

        elif service_type == "venue":
            result["recommendations"] = self._recommend_venues(date_context)
            result["tips"] = ["提前踩点", "准备备选方案"]

        elif service_type == "topics":
            result["recommendations"] = self._generate_topics(date_context)
            result["tips"] = ["多问开放性问题", "积极倾听"]

        elif service_type == "realtime_help":
            result["tips"] = ["放松，做真实的自己", "享受当下"]

        return result

    def _recommend_outfit(self, date_context: Optional[Dict]) -> List[Dict]:
        """推荐穿搭"""
        return [
            {"type": "style", "suggestion": "Smart Casual 风格"},
            {"type": "color", "suggestion": "深色系显稳重"},
            {"type": "shoes", "suggestion": "干净的运动鞋或皮鞋"}
        ]

    def _recommend_venues(self, date_context: Optional[Dict]) -> List[Dict]:
        """推荐场所"""
        return [
            {"type": "coffee", "name": "安静咖啡馆", "reason": "方便交流"},
            {"type": "park", "name": "公园散步", "reason": "轻松自然"}
        ]

    def _generate_topics(self, date_context: Optional[Dict]) -> List[Dict]:
        """生成话题"""
        return [
            {"type": "icebreaker", "topic": "今天怎么过来的？"},
            {"type": "hobby", "topic": "平时喜欢做什么？"},
            {"type": "travel", "topic": "去过哪些地方？"}
        ]

    def _generate_message(self, result: Dict, service_type: str) -> str:
        """生成自然语言建议"""
        message = f"💡 约会{self._get_service_name(service_type)}建议\n\n"

        for rec in result.get("recommendations", [])[:3]:
            message += f"- {rec.get('type', '建议')}: {rec.get('suggestion', rec.get('name', ''))}\n"

        if result.get("tips"):
            message += f"\n小贴士：\n"
            for tip in result["tips"][:3]:
                message += f"- {tip}\n"

        return message

    def _get_service_name(self, service_type: str) -> str:
        """获取服务名称"""
        names = {
            "outfit": "穿搭",
            "venue": "场所",
            "topics": "话题",
            "realtime_help": "实时协助"
        }
        return names.get(service_type, "协助")

    def _build_ui(self, result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        return {
            "component_type": "date_assistant_card",
            "props": {
                "service_type": service_type,
                "recommendations": result.get("recommendations", []),
                "tips": result.get("tips", [])
            }
        }

    def _generate_actions(self, service_type: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        return [
            {"label": "获取更多建议", "action_type": "get_more_tips", "params": {}},
            {"label": "切换服务类型", "action_type": "switch_service", "params": {}}
        ]

    async def autonomous_trigger(
        self,
        user_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """自主触发"""
        logger.info(f"DateAssistantSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        if trigger_type == "pre_date_reminder":
            result = await self.execute(
                user_id=user_id,
                service_type="outfit",
                date_context=context
            )
            return {"triggered": True, "result": result, "should_push": True}

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_date_assistant_skill_instance: Optional[DateAssistantSkill] = None


def get_date_assistant_skill() -> DateAssistantSkill:
    """获取约会助手 Skill 单例实例"""
    global _date_assistant_skill_instance
    if _date_assistant_skill_instance is None:
        _date_assistant_skill_instance = DateAssistantSkill()
    return _date_assistant_skill_instance
