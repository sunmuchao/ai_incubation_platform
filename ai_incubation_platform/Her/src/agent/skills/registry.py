"""
Agent Skill 注册中心

统一管理所有 Agent Skill 的注册、查询和执行。
"""
from typing import Dict, List, Optional, Any, Callable
from utils.logger import logger


class SkillRegistry:
    """
    Skill 注册表单例类

    用法:
        registry = SkillRegistry.get_instance()
        registry.register(skill)
        result = await registry.execute("skill_name", param1=1, param2=2)
    """

    _instance: Optional["SkillRegistry"] = None

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
            cls._instance._metadata = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        """获取单例实例"""
        return cls()

    def register(
        self,
        skill_instance: Any,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        注册 Skill

        Args:
            skill_instance: Skill 实例
            name: Skill 名称（可选，不传则使用实例的 name 属性）
            tags: Skill 标签列表
        """
        skill_name = name or getattr(skill_instance, "name", None)
        if not skill_name:
            raise ValueError("Skill must have a name")

        if skill_name in self._skills:
            logger.warning(f"Skill already registered, overwriting: {skill_name}")

        self._skills[skill_name] = skill_instance
        self._metadata[skill_name] = {
            "description": getattr(skill_instance, "description", ""),
            "version": getattr(skill_instance, "version", "1.0.0"),
            "tags": tags or [],
            "input_schema": skill_instance.get_input_schema() if hasattr(skill_instance, "get_input_schema") else {},
            "output_schema": skill_instance.get_output_schema() if hasattr(skill_instance, "get_output_schema") else {}
        }
        logger.info(f"Skill registered: {skill_name}")

    def get(self, name: str) -> Optional[Any]:
        """获取 Skill 实例"""
        return self._skills.get(name)

    def get_metadata(self, name: str) -> Optional[dict]:
        """获取 Skill 元数据"""
        return self._metadata.get(name)

    def list_skills(self, tag: Optional[str] = None) -> List[dict]:
        """
        获取 Skill 列表

        Args:
            tag: 按标签过滤

        Returns:
            Skill 信息列表
        """
        result = []
        for name, metadata in self._metadata.items():
            if tag and tag not in metadata.get("tags", []):
                continue
            result.append({
                "name": name,
                "description": metadata["description"],
                "version": metadata["version"],
                "tags": metadata["tags"]
            })
        return result

    async def execute(self, name: str, **kwargs) -> dict:
        """
        执行 Skill

        Args:
            name: Skill 名称
            **kwargs: Skill 参数

        Returns:
            执行结果 {"success": bool, "data/error": any}
        """
        skill = self.get(name)

        if not skill:
            logger.warning(f"Skill not found: {name}")
            return {"success": False, "error": f"Skill not found: {name}"}

        try:
            logger.info(f"Executing skill: {name}, params: {kwargs.keys()}")

            # 判断是否为异步函数
            import inspect
            execute_method = getattr(skill, "execute", None)
            if not execute_method:
                return {"success": False, "error": f"Skill {name} has no execute method"}

            if inspect.iscoroutinefunction(execute_method):
                result = await execute_method(**kwargs)
            else:
                result = execute_method(**kwargs)

            logger.info(f"Skill execution completed: {name}")
            return result

        except Exception as e:
            logger.error(f"Skill execution failed: {name}, error: {e}")
            return {"success": False, "error": str(e)}

    def clear(self) -> None:
        """清空所有注册的 Skill（用于测试）"""
        self._skills.clear()
        self._metadata.clear()
        logger.info("Skill registry cleared")


# 全局注册表实例
_registry_instance: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """获取 Skill 注册表单例实例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = SkillRegistry.get_instance()
    return _registry_instance


def initialize_default_skills() -> SkillRegistry:
    """
    初始化默认 Skill 注册表

    注册所有内置的 Agent Skill
    """
    registry = get_skill_registry()

    # Core Skills - 核心 AI Native 能力
    # 注：matchmaking_skill 已废弃，匹配功能使用 ConversationMatchService + DeerFlow her_find_matches_tool
    from agent.skills.precommunication_skill import get_precommunication_skill
    from agent.skills.omniscient_insight_skill import get_omniscient_insight_skill

    registry.register(get_precommunication_skill(), tags=["core", "communication", "core"])
    registry.register(get_omniscient_insight_skill(), tags=["core", "awareness", "core"])

    # ===== [已废弃] 意图路由 Skill =====
    # IntentRouterSkill 已废弃（见 DEPRECATED.md）
    # 新架构：用户消息 → DeerFlow Agent → her_tools
    # DeerFlow Agent 通过 SOUL.md 直接理解意图并调用工具
    # 不再需要中间的"传话员"层
    #
    # from agent.skills.intent_router_skill import get_intent_router_skill
    # registry.register(get_intent_router_skill(), tags=["core", "intent_router", "entry_point"])

    # Enhancement Skills - 增强 AI 自主性
    from agent.skills.relationship_coach_skill import get_relationship_coach_skill
    from agent.skills.date_planning_skill import get_date_planning_skill

    registry.register(get_relationship_coach_skill(), tags=["enhancement", "relationship"])
    registry.register(get_date_planning_skill(), tags=["enhancement", "dating"])

    # External Skills - 外部服务集成
    from agent.skills.bill_analysis_skill import get_bill_analysis_skill
    from agent.skills.gift_suggestion_skill import get_gift_suggestion_skill

    registry.register(get_bill_analysis_skill(), tags=["external", "external_service", "consumption"])
    registry.register(get_gift_suggestion_skill(), tags=["values", "gift", "suggestion", "core"])

    # 注：geo_location 已删除，改用 REST API
    # /api/activities/locations/* 和 /api/gifts/*

    # ===== 新增：API 改造 Skill (Core 优先级) =====

    # Emotion - 感官洞察
    from agent.skills.emotion_analysis_skill import get_emotion_analysis_skill
    from agent.skills.safety_guardian_skill import get_safety_guardian_skill

    registry.register(get_emotion_analysis_skill(), tags=["emotion", "emotion", "analysis", "core"])
    registry.register(get_safety_guardian_skill(), tags=["emotion", "safety", "guardian", "core"])

    # Behavior - 行为实验室
    from agent.skills.silence_breaker_skill import get_silence_breaker_skill
    from agent.skills.emotion_mediator_skill import get_emotion_mediator_skill

    registry.register(get_silence_breaker_skill(), tags=["behavior", "silence", "icebreaker", "core"])
    registry.register(get_emotion_mediator_skill(), tags=["behavior", "emotion", "mediation", "core"])

    # LoveLanguage - 情感调解增强
    from agent.skills.love_language_translator_skill import get_love_language_translator_skill
    from agent.skills.relationship_prophet_skill import get_relationship_prophet_skill

    registry.register(get_love_language_translator_skill(), tags=["love_language", "love_language", "translation", "core"])
    registry.register(get_relationship_prophet_skill(), tags=["love_language", "relationship", "prediction", "core"])

    # Dating - 实战演习
    # 注：date_coach_skill 和 date_assistant_skill 已废弃，功能已整合到 DeerFlow Agent

    # Integration - 终极关系
    from agent.skills.relationship_curator_skill import get_relationship_curator_skill

    registry.register(get_relationship_curator_skill(), tags=["integration", "relationship", "curator", "core"])

    # ===== 新增：Enterprise/Social/Relationship 技能 =====

    # Enterprise - 智能风控与绩效管理
    from agent.skills.risk_control_skill import get_risk_control_skill

    registry.register(get_risk_control_skill(), tags=["enterprise", "risk_control", "dashboard", "core"])

    # Social - 分享增长引擎
    from agent.skills.share_growth_skill import get_share_growth_skill

    registry.register(get_share_growth_skill(), tags=["social", "share", "growth", "core"])

    # Relationship - 关系绩效教练
    from agent.skills.performance_coach_skill import get_performance_coach_skill

    registry.register(get_performance_coach_skill(), tags=["relationship", "performance", "coach", "core"])

    # Relationship - 活动导演
    from agent.skills.activity_director_skill import get_activity_director_skill

    registry.register(get_activity_director_skill(), tags=["relationship", "activity", "director", "core"])

    # Relationship - 视频约会教练
    from agent.skills.video_date_coach_skill import get_video_date_coach_skill

    registry.register(get_video_date_coach_skill(), tags=["relationship", "video_date", "coach", "core"])

    # 注：conversation_matchmaker_skill 已废弃，匹配功能使用 ConversationMatchService + DeerFlow her_tools

    # ===== 新增：API 转 Skill (Core/Enhancement/Experience 优先级) =====

    # Core - 核心能力增强
    from agent.skills.trust_analyzer_skill import get_trust_analyzer_skill
    from agent.skills.subconscious_analyzer_skill import get_subconscious_analyzer_skill
    from agent.skills.values_inferencer_skill import get_values_inferencer_skill

    registry.register(get_trust_analyzer_skill(), tags=["core", "trust", "analysis", "core"])
    registry.register(get_subconscious_analyzer_skill(), tags=["core", "subconscious", "analysis", "core"])
    registry.register(get_values_inferencer_skill(), tags=["core", "values", "inference", "core"])

    # Enhancement - 差异化功能
    from agent.skills.conflict_compatibility_analyzer_skill import get_conflict_compatibility_analyzer_skill
    from agent.skills.values_drift_detector_skill import get_values_drift_detector_skill
    from agent.skills.twin_simulator_skill import get_twin_simulator_skill

    registry.register(get_conflict_compatibility_analyzer_skill(), tags=["enhancement", "conflict", "compatibility", "core"])
    registry.register(get_values_drift_detector_skill(), tags=["enhancement", "values", "drift", "core"])
    registry.register(get_twin_simulator_skill(), tags=["enhancement", "twin", "simulation", "core"])

    # Experience - 增强体验
    from agent.skills.context_detector_skill import get_context_detector_skill
    from agent.skills.ui_renderer_skill import get_ui_renderer_skill
    from agent.skills.preference_learner_skill import get_preference_learner_skill
    from agent.skills.pattern_learner_skill import get_pattern_learner_skill

    registry.register(get_context_detector_skill(), tags=["experience", "context", "awareness", "enhancement"])
    registry.register(get_ui_renderer_skill(), tags=["experience", "ui", "rendering", "enhancement"])
    registry.register(get_preference_learner_skill(), tags=["experience", "preference", "learning", "enhancement"])
    registry.register(get_pattern_learner_skill(), tags=["experience", "pattern", "learning", "enhancement"])

    # ===== Profile Collection - 用户信息收集 =====
    from agent.skills.profile_collection_skill import get_profile_collection_skill

    registry.register(get_profile_collection_skill(), tags=["core", "profile", "collection", "entry_point"])

    # ===== 新增：API 改造 Skill (从 REST API 升级) =====

    # 注：relationship_progress 已删除，改用 REST API /api/relationship/*
    # Emotion - 紧急求助扩展 (SafetyGuardianSkill 已注册，此处添加功能扩展说明)
    # SafetyGuardianSkill 已在上注册，新增 trigger_emergency 和 notify_emergency_contact 方法

    # 聊天助手 - 聊天 API 改造
    from agent.skills.chat_assistant_skill import get_chat_assistant_skill

    registry.register(get_chat_assistant_skill(), tags=["chat", "messaging", "assistant", "core"])

    logger.info(f"Initialized {len(registry.list_skills())} default skills")

    return registry
