"""
Skill 工具集

将 AI Native Skill 封装为工具，供工作流调用。
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import logger

# 导入所有 Skill
from agent.skills.registry import get_skill_registry


class SkillTool:
    """
    通用 Skill 工具封装器

    功能：
    - 执行任意已注册的 Skill
    - 统一的输入输出处理
    - 错误处理和日志记录
    """

    name = "skill_executor"
    description = "执行任意已注册的 AI Native Skill"
    tags = ["skill", "executor", "ai_native"]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Skill 名称"
                },
                "params": {
                    "type": "object",
                    "description": "Skill 执行参数"
                }
            },
            "required": ["skill_name", "params"]
        }

    @staticmethod
    def execute(
        skill_name: str,
        params: Dict[str, Any]
    ) -> dict:
        """
        执行 Skill

        Args:
            skill_name: Skill 名称
            params: Skill 执行参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"SkillTool: Executing skill={skill_name}, params={list(params.keys())}")

        try:
            registry = get_skill_registry()
            result = registry.execute(skill_name, **params)

            # 如果是协程，需要 await
            import inspect
            if inspect.iscoroutine(result):
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(result)

            logger.info(f"SkillTool: Skill {skill_name} executed successfully")
            return result

        except Exception as e:
            logger.error(f"SkillTool: Execution failed: {e}")
            return {"success": False, "error": str(e)}


class EmotionAnalysisTool:
    """情感分析工具 - 封装 EmotionAnalysisSkill"""

    name = "emotion_analysis"
    description = "分析用户情感状态，检测情绪波动"
    tags = ["emotion", "analysis"]

    @staticmethod
    def get_input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "会话 ID"},
                "analysis_type": {"type": "string", "enum": ["micro_expression", "voice_emotion", "combined"]},
                "facial_data": {"type": "object", "description": "面部数据"},
                "voice_data": {"type": "object", "description": "语音数据"},
                "context": {"type": "object", "description": "上下文信息"}
            },
            "required": ["session_id"]
        }

    @staticmethod
    def execute(
        session_id: str,
        analysis_type: str = "combined",
        facial_data: Optional[Dict] = None,
        voice_data: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> dict:
        """执行情感分析"""
        logger.info(f"EmotionAnalysisTool: Analyzing session={session_id}")

        params = {
            "session_id": session_id,
            "analysis_type": analysis_type,
            "facial_data": facial_data or {},
            "voice_data": voice_data or {},
            "context": context or {}
        }

        return SkillTool.execute("emotion_translator", params)


class SafetyGuardianTool:
    """安全守护工具 - 封装 SafetyGuardianSkill"""

    name = "safety_guardian"
    description = "检测安全风险，提供分级响应"
    tags = ["safety", "guardian"]

    @staticmethod
    def execute(
        user_id: str,
        check_type: str = "location",
        location_data: Optional[Dict] = None,
        voice_data: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> dict:
        """执行安全检查"""
        logger.info(f"SafetyGuardianTool: Checking user={user_id}, type={check_type}")

        params = {
            "user_id": user_id,
            "check_type": check_type,
            "location_data": location_data,
            "voice_data": voice_data,
            "context": context
        }

        return SkillTool.execute("safety_guardian", params)


class SilenceBreakerTool:
    """沉默破冰工具 - 封装 SilenceBreakerSkill"""

    name = "silence_breaker"
    description = "检测对话沉默，生成破冰话题"
    tags = ["silence", "icebreaker"]

    @staticmethod
    def execute(
        conversation_id: str,
        user_a_id: str,
        user_b_id: str,
        silence_duration: float,
        context: Optional[Dict] = None
    ) -> dict:
        """执行沉默检测和破冰"""
        logger.info(f"SilenceBreakerTool: Checking conversation={conversation_id}")

        params = {
            "conversation_id": conversation_id,
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "silence_duration": silence_duration,
            "context": context or {}
        }

        return SkillTool.execute("silence_breaker", params)


class EmotionMediatorTool:
    """情感调解工具 - 封装 EmotionMediatorSkill"""

    name = "emotion_mediator"
    description = "检测争吵，提供调解建议"
    tags = ["emotion", "mediation"]

    @staticmethod
    def execute(
        conversation_id: str,
        user_a_id: str,
        user_b_id: str,
        service_type: str = "conflict_detection",
        context: Optional[Dict] = None
    ) -> dict:
        """执行情感调解"""
        logger.info(f"EmotionMediatorTool: Mediating conversation={conversation_id}")

        params = {
            "conversation_id": conversation_id,
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "service_type": service_type,
            "context": context or {}
        }

        return SkillTool.execute("emotion_mediator", params)


class LoveLanguageTranslatorTool:
    """爱之语翻译工具 - 封装 LoveLanguageTranslatorSkill"""

    name = "love_language_translator"
    description = "解读表面话语背后的真实需求"
    tags = ["love_language", "translation"]

    @staticmethod
    def execute(
        user_id: str,
        expression: str,
        context: Optional[Dict] = None
    ) -> dict:
        """翻译爱之语"""
        logger.info(f"LoveLanguageTranslatorTool: Translating for user={user_id}")

        params = {
            "user_id": user_id,
            "expression": expression,
            "context": context or {}
        }

        return SkillTool.execute("love_language_translator", params)


class RelationshipProphetTool:
    """关系预测工具 - 封装 RelationshipProphetSkill"""

    name = "relationship_prophet"
    description = "预测关系发展趋势"
    tags = ["relationship", "prediction"]

    @staticmethod
    def execute(
        user_a_id: str,
        user_b_id: str,
        analysis_type: str = "trend_prediction",
        context: Optional[Dict] = None
    ) -> dict:
        """执行关系预测"""
        logger.info(f"RelationshipProphetTool: Predicting for users={user_a_id},{user_b_id}")

        params = {
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "analysis_type": analysis_type,
            "context": context or {}
        }

        return SkillTool.execute("relationship_prophet", params)


class DateCoachTool:
    """约会教练工具 - 封装 DateCoachSkill"""

    name = "date_coach"
    description = "提供约会指导和策略"
    tags = ["dating", "coach"]

    @staticmethod
    def execute(
        user_id: str,
        service_type: str = "outfit_recommendation",
        date_context: Optional[Dict] = None
    ) -> dict:
        """执行约会指导"""
        logger.info(f"DateCoachTool: Coaching user={user_id}, type={service_type}")

        params = {
            "user_id": user_id,
            "service_type": service_type,
            "date_context": date_context or {}
        }

        return SkillTool.execute("date_coach", params)


class DateAssistantTool:
    """约会助手工具 - 封装 DateAssistantSkill"""

    name = "date_assistant"
    description = "约会实时协助"
    tags = ["dating", "assistant"]

    @staticmethod
    def execute(
        user_id: str,
        service_type: str = "outfit",
        date_context: Optional[Dict] = None
    ) -> dict:
        """执行约会协助"""
        logger.info(f"DateAssistantTool: Assisting user={user_id}, type={service_type}")

        params = {
            "user_id": user_id,
            "service_type": service_type,
            "date_context": date_context or {}
        }

        return SkillTool.execute("date_assistant", params)


class RelationshipCuratorTool:
    """关系策展工具 - 封装 RelationshipCuratorSkill"""

    name = "relationship_curator"
    description = "策划关系纪念和里程碑"
    tags = ["relationship", "curator"]

    @staticmethod
    def execute(
        user_a_id: str,
        user_b_id: str,
        service_type: str = "memory_collection",
        context: Optional[Dict] = None
    ) -> dict:
        """执行关系策展"""
        logger.info(f"RelationshipCuratorTool: Curating for users={user_a_id},{user_b_id}")

        params = {
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "service_type": service_type,
            "context": context or {}
        }

        return SkillTool.execute("relationship_curator", params)


class RiskControlTool:
    """风控工具 - 封装 RiskControlSkill"""

    name = "risk_control"
    description = "企业数据看板与绩效分析"
    tags = ["risk_control", "dashboard"]

    @staticmethod
    def execute(
        user_id: str,
        service_type: str = "dashboard_overview",
        context: Optional[Dict] = None
    ) -> dict:
        """执行风控分析"""
        logger.info(f"RiskControlTool: Analyzing user={user_id}, type={service_type}")

        params = {
            "user_id": user_id,
            "service_type": service_type,
            "context": context or {}
        }

        return SkillTool.execute("risk_control", params)


class ShareGrowthTool:
    """分享增长工具 - 封装 ShareGrowthSkill"""

    name = "share_growth"
    description = "分享策略与增长分析"
    tags = ["share", "growth"]

    @staticmethod
    def execute(
        user_id: str,
        service_type: str = "notification_analysis",
        context: Optional[Dict] = None
    ) -> dict:
        """执行增长分析"""
        logger.info(f"ShareGrowthTool: Analyzing user={user_id}, type={service_type}")

        params = {
            "user_id": user_id,
            "service_type": service_type,
            "context": context or {}
        }

        return SkillTool.execute("share_growth", params)


class PerformanceCoachTool:
    """绩效教练工具 - 封装 PerformanceCoachSkill"""

    name = "performance_coach"
    description = "关系绩效与里程碑追踪"
    tags = ["performance", "coach"]

    @staticmethod
    def execute(
        user_a_id: str,
        user_b_id: str,
        service_type: str = "milestone_tracking",
        context: Optional[Dict] = None
    ) -> dict:
        """执行绩效教练"""
        logger.info(f"PerformanceCoachTool: Coaching users={user_a_id},{user_b_id}")

        params = {
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "service_type": service_type,
            "context": context or {}
        }

        return SkillTool.execute("performance_coach", params)


class ActivityDirectorTool:
    """活动导演工具 - 封装 ActivityDirectorSkill"""

    name = "activity_director"
    description = "活动策划与地点推荐"
    tags = ["activity", "director"]

    @staticmethod
    def execute(
        user_id: str,
        service_type: str = "location_recommendation",
        context: Optional[Dict] = None
    ) -> dict:
        """执行活动策划"""
        logger.info(f"ActivityDirectorTool: Planning for user={user_id}, type={service_type}")

        params = {
            "user_id": user_id,
            "service_type": service_type,
            "context": context or {}
        }

        return SkillTool.execute("activity_director", params)


class VideoDateCoachTool:
    """视频约会教练工具 - 封装 VideoDateCoachSkill"""

    name = "video_date_coach"
    description = "视频约会全流程指导"
    tags = ["video_date", "coach"]

    @staticmethod
    def execute(
        user_id: str,
        service_type: str = "date_management",
        context: Optional[Dict] = None
    ) -> dict:
        """执行视频约会指导"""
        logger.info(f"VideoDateCoachTool: Coaching user={user_id}, type={service_type}")

        params = {
            "user_id": user_id,
            "service_type": service_type,
            "context": context or {}
        }

        return SkillTool.execute("video_date_coach", params)


class ConversationMatchmakerTool:
    """对话式匹配工具 - 封装 ConversationMatchmakerSkill"""

    name = "conversation_matchmaker"
    description = "对话式匹配与关系分析"
    tags = ["conversation", "matching"]

    @staticmethod
    def execute(
        user_id: str,
        service_type: str = "intent_matching",
        context: Optional[Dict] = None
    ) -> dict:
        """执行匹配服务"""
        logger.info(f"ConversationMatchmakerTool: Matching user={user_id}, type={service_type}")

        params = {
            "user_id": user_id,
            "service_type": service_type,
            "context": context or {}
        }

        return SkillTool.execute("conversation_matchmaker", params)


# 工具注册函数
def register_skill_tools(registry) -> None:
    """
    注册所有 Skill 工具到工具注册表

    Args:
        registry: ToolRegistry 实例
    """
    tools = [
        ("skill_executor", SkillTool),
        ("emotion_analysis", EmotionAnalysisTool),
        ("safety_guardian", SafetyGuardianTool),
        ("silence_breaker", SilenceBreakerTool),
        ("emotion_mediator", EmotionMediatorTool),
        ("love_language_translator", LoveLanguageTranslatorTool),
        ("relationship_prophet", RelationshipProphetTool),
        ("date_coach", DateCoachTool),
        ("date_assistant", DateAssistantTool),
        ("relationship_curator", RelationshipCuratorTool),
        ("risk_control", RiskControlTool),
        ("share_growth", ShareGrowthTool),
        ("performance_coach", PerformanceCoachTool),
        ("activity_director", ActivityDirectorTool),
        ("video_date_coach", VideoDateCoachTool),
        ("conversation_matchmaker", ConversationMatchmakerTool),
    ]

    for name, tool_class in tools:
        registry.register(
            name=name,
            handler=tool_class.execute,
            description=tool_class.description,
            input_schema=tool_class.get_input_schema() if hasattr(tool_class, "get_input_schema") else None,
            tags=tool_class.tags
        )

    logger.info(f"Registered {len(tools)} Skill tools")
