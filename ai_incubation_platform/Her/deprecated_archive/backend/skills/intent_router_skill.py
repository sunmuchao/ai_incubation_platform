"""
意图路由 Skill - 系统核心入口（问诊台）

@deprecated
此 Skill 已废弃，原因：
1. registry.py 已注释掉此 Skill 的注册（见第 168-175 行）
2. 新架构：用户消息 → DeerFlow Agent → her_tools
3. DeerFlow Agent 通过 SOUL.md 直接理解意图并调用工具
4. 不再需要中间的"传话员"层

替代方案：
- 前端调用 /api/deerflow/chat 直接与 DeerFlow Agent 交互
- DeerFlow Agent 通过 SOUL.md 理解用户意图
- 自动调用 her_tools 执行对应功能

归档日期：2026-04-15
预计删除：立即删除（已被替代）

---

职责：
1. 接收所有用户对话请求
2. 分析用户意图（匹配、咨询、偏好更新等）
3. 路由到对应的 DeerFlow 工具或 Skill 处理

【v3.1 简化版改动】
- 支持直接调用 DeerFlow 工具（deerflow_tool 配置项）
- 减少中间 Skill 层，降低出错概率
- 增加结构化日志，便于问题追踪

设计原则：
- 这是系统的"问诊台"，所有对话先到这里
- 不执行具体业务，只做意图识别和路由
- 返回结构化数据，供 DeerFlow Agent 继续决策

版本历史：
- v1.0.0: 初始版本，关键词匹配（硬编码）
- v2.0.0: 升级支持 DeerFlow 集成
- v3.0.0: 配置化重构，关键词/优先级/映射从 YAML 加载
- v3.1.0: 简化版，支持直接调用 DeerFlow 工具
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json
import re
import time

from agent.skills.base import BaseSkill
from agent.skills.registry import get_skill_registry
from intent_config.intent_config_loader import get_intent_config_loader
from utils.logger import logger


# ============= 意图类型枚举 =============

class IntentType(Enum):
    """意图类型枚举 - 15 种核心意图"""
    # 匹配相关
    MATCHING = "matching"
    DAILY_RECOMMEND = "daily_recommend"

    # 画像相关
    PROFILE_COLLECTION = "profile_collection"

    # 关系分析
    RELATIONSHIP_ANALYSIS = "relationship_analysis"

    # 对话辅助
    TOPIC_SUGGESTION = "topic_suggestion"
    ICEBREAKER = "icebreaker"

    # 约会相关
    DATING_SUGGESTION = "dating_suggestion"
    DATE_PLANNING = "date_planning"

    # 预沟通
    PRE_COMMUNICATION = "pre_communication"
    PRE_COMM_START = "pre_comm_start"

    # 本地处理（不调用 Skill）
    GREETING = "greeting"
    GRATITUDE = "gratitude"
    GOODBYE = "goodbye"
    CAPABILITY_INQUIRY = "capability_inquiry"

    # 兜底
    GENERAL = "general"


# ============= 意图识别结果 =============

@dataclass
class IntentResult:
    """意图识别结果"""
    type: IntentType
    confidence: float = 1.0
    raw_input: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


class IntentRouterSkill(BaseSkill):
    """
    意图路由 Skill - 系统问诊台

    作为系统的核心入口，分析用户意图并路由到正确的处理单元。

    支持两种模式：
    1. 关键词匹配（快速降级）- 使用 YAML 配置
    2. LLM 深度分析（可选）
    """

    name = "intent_router"
    description = "意图路由 - 分析用户意图并路由到正确的处理单元"
    version = "3.0.0"  # 配置化重构版本

    def __init__(self):
        super().__init__()
        # 配置加载器
        self._config_loader = get_intent_config_loader()

    async def execute(
        self,
        user_input: str,
        user_id: str = "",
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行意图路由

        Args:
            user_input: 用户输入消息
            user_id: 用户 ID
            context: 上下文信息

        Returns:
            {
                "success": true,
                "intent": {"type": "matching", "confidence": 0.9},
                "ai_message": "...",
                "generative_ui": {...},
                "skill_to_call": "skill_name" or None,
                "suggested_actions": [...],
                "skill_metadata": {...}
            }
        """
        start_time = time.time()

        logger.info(f"[IntentRouter] 分析用户输入: user_id={user_id}, input={user_input[:50]}...")
        logger.debug(f"[IntentRouter] 完整输入: {user_input}")

        # Step 0: 检查是否需要先收集用户画像
        if self._check_need_profile_collection(user_id):
            try:
                registry = get_skill_registry()
                skill_result = await registry.execute("profile_collection", user_id=user_id, trigger_reason="new_user")

                return self._build_response(
                    intent_type=IntentType.PROFILE_COLLECTION,
                    confidence=0.9,
                    ai_message=skill_result.get("ai_message", "请告诉我你的信息"),
                    generative_ui=skill_result.get("generative_ui", {"component_type": "ProfileQuestionCard", "props": {}}),
                    skill_to_call="profile_collection",
                    suggested_actions=skill_result.get("suggested_actions", []),
                    is_local=False,
                    start_time=start_time,
                )
            except Exception as e:
                logger.error(f"[IntentRouter] profile_collection 执行失败: {e}")
                return self._build_response(
                    intent_type=IntentType.PROFILE_COLLECTION,
                    confidence=0.9,
                    ai_message="请告诉我你的基本信息，比如年龄、所在地等",
                    generative_ui={"component_type": "ProfileQuestionCard", "props": {"question": "年龄"}},
                    skill_to_call="profile_collection",
                    suggested_actions=[],
                    is_local=False,
                    start_time=start_time,
                )

        # Step 1: 关键词匹配（使用配置）
        intent = self._classify_with_keywords(user_input)
        logger.info(f"[IntentRouter] 意图识别结果: intent={intent.type.value}, confidence={intent.confidence:.2f}, matched_keywords={intent.params.get('matched_keywords', [])}")

        # Step 2: 如果置信度低，尝试 LLM 分析（可选）
        if intent.confidence < 0.7:
            logger.info(f"[IntentRouter] 置信度低于 0.7，尝试 LLM 深度分析")
            intent = await self._classify_with_llm(user_input, context)
            logger.info(f"[IntentRouter] LLM 分析结果: intent={intent.type.value}, confidence={intent.confidence:.2f}")
            if intent.confidence < 0.5:
                intent = IntentResult(type=IntentType.GENERAL, confidence=0.3, raw_input=user_input)

        # Step 3: 处理意图
        intent_type = intent.type
        config = self._config_loader.get_config()

        # 本地意图：直接返回响应
        local_intents = config.get_local_intents()
        if intent_type.value in local_intents:
            if intent_type == IntentType.GENERAL:
                result = self._handle_general_intent(intent)
            else:
                result = self._handle_local_intent(intent)
            result["intent"] = {"type": intent_type.value, "confidence": intent.confidence}
            result["skill_to_call"] = None
            result["is_local"] = True
            result["skill_metadata"] = self._get_skill_metadata(start_time)
            return result

        # 需要调用 Skill：执行 Skill
        skill_mapping = config.get_skill_mapping()
        skill_to_call = skill_mapping.get(intent_type.value)

        # 【v3.1 新增】检查是否配置了 deerflow_tool（直接调用 DeerFlow 工具）
        deerflow_tool = None
        for intent_config in config.get_sorted_intents():
            if intent_config.name == intent_type.value:
                deerflow_tool = intent_config.deerflow_tool if hasattr(intent_config, 'deerflow_tool') else None
                break

        if deerflow_tool:
            # 直接调用 DeerFlow 工具（减少中间层）
            logger.info(f"[IntentRouter] 直接调用 DeerFlow 工具: {deerflow_tool}")
            try:
                # 通过 DeerFlow client 调用工具
                from agent.deerflow_client import get_deerflow_client
                client = get_deerflow_client()
                # 这里需要通过 DeerFlow 的 chat 接口传递工具调用意图
                # 实际工具调用由 DeerFlow Agent 执行
                result = await client.chat(
                    message=f"[系统触发] 用户意图={intent_type.value}, 请调用工具={deerflow_tool}",
                    thread_id=f"intent-{user_id}"
                )
                logger.info(f"[IntentRouter] DeerFlow 工具调用完成: tool={deerflow_tool}")

                return self._build_response(
                    intent_type=intent_type,
                    confidence=intent.confidence,
                    ai_message=result,
                    generative_ui={"component_type": "DeerFlowResult", "props": {"tool": deerflow_tool}},
                    skill_to_call=deerflow_tool,
                    suggested_actions=self._get_suggested_actions(intent_type),
                    is_local=False,
                    start_time=start_time,
                )
            except Exception as e:
                logger.error(f"[IntentRouter] DeerFlow 工具调用失败: {e}")
                # 降级：继续使用原有 Skill 路由

        if skill_to_call:
            logger.info(f"[IntentRouter] 调用 Skill: {skill_to_call}")
            try:
                registry = get_skill_registry()
                skill_result = await registry.execute(skill_to_call, user_id=user_id, user_input=user_input)

                return self._build_response(
                    intent_type=intent_type,
                    confidence=intent.confidence,
                    ai_message=skill_result.get("ai_message", self._generate_response(intent)),
                    generative_ui=skill_result.get("generative_ui", self._build_generative_ui(intent)),
                    skill_to_call=skill_to_call,
                    suggested_actions=skill_result.get("suggested_actions", self._get_suggested_actions(intent_type)),
                    is_local=False,
                    start_time=start_time,
                )
            except Exception as e:
                logger.error(f"[IntentRouter] Skill 执行失败: {e}")
                ai_message = self._generate_response(intent)
                return self._build_response(
                    intent_type=intent_type,
                    confidence=intent.confidence,
                    ai_message=ai_message,
                    generative_ui=self._build_generative_ui(intent),
                    skill_to_call=skill_to_call,
                    suggested_actions=self._get_suggested_actions(intent_type),
                    is_local=False,
                    start_time=start_time,
                )

        # 没有对应的 Skill：返回默认响应
        ai_message = self._generate_response(intent)
        return self._build_response(
            intent_type=intent_type,
            confidence=intent.confidence,
            ai_message=ai_message,
            generative_ui=self._build_generative_ui(intent),
            skill_to_call=None,
            suggested_actions=self._get_suggested_actions(intent_type),
            is_local=False,
            start_time=start_time,
        )

    def _get_skill_metadata(self, start_time: float) -> Dict[str, Any]:
        """获取 Skill 元数据"""
        execution_time_ms = int((time.time() - start_time) * 1000)
        return {
            "name": self.name,
            "version": self.version,
            "execution_time_ms": execution_time_ms,
            "config_version": self._config_loader.get_config().metadata.get("version", "unknown"),
        }

    def _build_response(
        self,
        intent_type: IntentType,
        confidence: float,
        ai_message: str,
        generative_ui: Dict[str, Any],
        skill_to_call: Optional[str],
        suggested_actions: List[Dict[str, Any]],
        is_local: bool,
        start_time: float,
    ) -> Dict[str, Any]:
        """构建统一响应格式"""
        return {
            "success": True,
            "intent": {"type": intent_type.value, "confidence": confidence},
            "ai_message": ai_message,
            "generative_ui": generative_ui,
            "skill_to_call": skill_to_call,
            "suggested_actions": suggested_actions,
            "is_local": is_local,
            "skill_metadata": self._get_skill_metadata(start_time),
        }

    def _classify_with_keywords(self, user_input: str) -> IntentResult:
        """基于关键词的意图识别（使用配置）"""
        user_input_lower = user_input.lower()
        config = self._config_loader.get_config()

        best_intent = IntentType.GENERAL
        best_confidence = 0.3
        matched_keywords = []

        # 按优先级顺序匹配（配置中已排序）
        for intent_config in config.get_sorted_intents():
            keywords = intent_config.keywords
            matches = [kw for kw in keywords if kw in user_input_lower]

            if matches:
                # 计算置信度：匹配关键词数量 + 关键词长度加权
                keyword_weight = sum(len(kw) for kw in matches) / 10
                confidence = 0.6 + 0.1 * len(matches) + keyword_weight * 0.1

                if confidence > best_confidence:
                    # 转换为 IntentType
                    try:
                        best_intent = IntentType(intent_config.name)
                    except ValueError:
                        # 配置中有新意图类型，使用 GENERAL 兜底
                        best_intent = IntentType.GENERAL

                    best_confidence = min(confidence, 0.95)
                    matched_keywords = matches

        return IntentResult(
            type=best_intent,
            confidence=best_confidence,
            raw_input=user_input,
            params={"matched_keywords": matched_keywords},
        )

    async def _classify_with_llm(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]]
    ) -> IntentResult:
        """基于 LLM 的深度意图分析（可选增强）"""
        try:
            from services.llm_semantic_service import get_llm_semantic_service
            llm_service = get_llm_semantic_service()

            # 获取配置中的意图类型列表
            config = self._config_loader.get_config()
            intent_types = list(config.intents.keys())

            prompt = f'''分析用户意图，返回 JSON：
{{"intent_type": "意图类型", "confidence": 0.0-1.0}}

意图类型可选值：
{", ".join(intent_types)}

用户输入："{user_input}"

只返回 JSON。'''

            response = await llm_service._call_llm(prompt)
            data = json.loads(response.strip())

            intent_type_str = data.get("intent_type", "general")
            confidence = data.get("confidence", 0.5)

            # 转换为 IntentType
            try:
                intent_type = IntentType(intent_type_str)
            except ValueError:
                intent_type = IntentType.GENERAL

            return IntentResult(
                type=intent_type,
                confidence=confidence,
                raw_input=user_input,
            )
        except Exception as e:
            logger.warning(f"[IntentRouter] LLM 分析失败: {e}")
            return IntentResult(
                type=IntentType.GENERAL,
                confidence=0.3,
                raw_input=user_input,
            )

    def _generate_response(self, intent: IntentResult) -> str:
        """生成 AI 响应消息（使用配置模板）"""
        config = self._config_loader.get_config()
        template = config.get_response_template(intent.type.value)

        if template:
            return template

        # 兜底模板
        response_templates = {
            IntentType.MATCHING: "好的，我来帮你找合适的对象~",
            IntentType.DAILY_RECOMMEND: "好的，让我看看今天有什么好推荐~",
            IntentType.PROFILE_COLLECTION: "好的，我来帮你完善资料~",
            IntentType.TOPIC_SUGGESTION: "好的，我来推荐一些话题帮你打开对话~",
            IntentType.ICEBREAKER: "好的，我来帮你想一个好的开场方式~",
            IntentType.GREETING: "你好呀！有什么可以帮你的吗？",
            IntentType.GRATITUDE: "不客气，很开心能帮到你！",
            IntentType.GOODBYE: "好的，下次见！有需要随时找我~",
            IntentType.CAPABILITY_INQUIRY: "我是 Her，我可以帮你找对象、推荐话题、策划约会、分析关系等等，你想了解哪个？",
            IntentType.GENERAL: "我在这里，有什么需要帮忙的吗？",
        }
        return response_templates.get(intent.type, "好的，我来帮你处理~")

    def _build_generative_ui(self, intent: IntentResult) -> Dict[str, Any]:
        """构建 Generative UI"""
        config = self._config_loader.get_config()
        local_intents = config.get_local_intents()

        # 只有需要 Skill 调用的意图才返回 UI
        if intent.type.value in local_intents:
            return {}

        return {
            "component_type": "IntentCard",
            "props": {
                "intent_type": intent.type.value,
                "confidence": intent.confidence,
                "action_hint": self._get_action_hint(intent.type),
            }
        }

    def _get_action_hint(self, intent_type: IntentType) -> str:
        """获取行动提示"""
        hints = {
            IntentType.MATCHING: "正在为你匹配...",
            IntentType.TOPIC_SUGGESTION: "正在生成话题...",
            IntentType.ICEBREAKER: "正在想开场白...",
            IntentType.DATE_PLANNING: "正在策划约会...",
        }
        return hints.get(intent_type, "")

    def _handle_local_intent(self, intent: IntentResult) -> Dict[str, Any]:
        """处理本地意图（不调用 Skill）"""
        ai_message = self._generate_response(intent)

        if intent.type == IntentType.CAPABILITY_INQUIRY:
            generative_ui = {
                "component_type": "CapabilityCard",
                "props": {
                    "intro": self._get_capability_intro(),
                    "features": self._get_feature_list(),
                }
            }
        else:
            generative_ui = {
                "component_type": "SimpleResponse",
                "props": {
                    "message": ai_message,
                }
            }

        return {
            "success": True,
            "ai_message": ai_message,
            "generative_ui": generative_ui,
            "suggested_actions": self._get_suggested_actions(intent.type),
        }

    def _handle_general_intent(self, intent: IntentResult) -> Dict[str, Any]:
        """处理一般意图"""
        return {
            "success": True,
            "ai_message": "我在这里，有什么需要帮忙的吗？",
            "generative_ui": {
                "component_type": "SimpleResponse",
                "props": {"message": "我在这里，有什么需要帮忙的吗？"}
            },
            "suggested_actions": self._get_suggested_actions(IntentType.GENERAL),
        }

    def _get_capability_intro(self) -> str:
        """获取能力介绍文本（使用配置）"""
        config = self._config_loader.get_config()
        return config.capability_intro or "我是 Her，你的智能社交助手。我可以帮你匹配对象、推荐话题、策划约会等。"

    def _get_feature_list(self) -> List[Dict[str, Any]]:
        """获取功能列表（使用配置）"""
        config = self._config_loader.get_config()
        return [
            {"name": f.name, "description": f.description}
            for f in config.feature_list
        ]

    def _get_suggested_actions(self, intent_type: IntentType) -> List[Dict[str, Any]]:
        """获取建议操作（使用配置）"""
        config = self._config_loader.get_config()
        actions = config.get_suggested_actions(intent_type.value)
        return actions if actions else []

    def _check_need_profile_collection(self, user_id: str) -> bool:
        """
        检查是否需要收集用户画像

        🔧 [简化] 只查数据库，测试用户通过测试框架预先入库

        这是**商业限制**（不完整用户不能匹配），属于"允许保留规则"：
        - 商业限制（付费、次数）
        - 数据校验（必填、格式）

        判断标准：
        - 缺少年龄、性别、所在地、关系目标中的任意一个 → 需要收集
        - 用户 ID 为空 → 不需要（匿名用户）

        Returns:
            True: 需要收集用户信息
            False: 用户信息完整，不需要收集
        """
        if not user_id:
            return False

        try:
            from utils.db_session_manager import db_session
            from db.models import UserDB

            with db_session() as db:
                user = db.query(UserDB).filter(UserDB.id == user_id).first()

                if not user:
                    return True

                required_fields = [
                    ('age', user.age),
                    ('gender', user.gender),
                    ('location', user.location),
                    ('relationship_goal', user.relationship_goal),
                ]

                for field_name, value in required_fields:
                    if not value:
                        logger.info(f"[IntentRouter] 用户 {user_id} 缺少字段 {field_name}，需要收集")
                        return True

                logger.info(f"[IntentRouter] 用户 {user_id} 信息完整，跳过收集")
                return False

        except Exception as e:
            logger.error(f"[IntentRouter] 检查用户画像失败: {e}")
            return False

    def get_input_schema(self) -> Dict[str, Any]:
        """返回输入 Schema"""
        return {
            "type": "object",
            "properties": {
                "user_input": {"type": "string", "description": "用户输入消息"},
                "user_id": {"type": "string", "description": "用户 ID"},
                "context": {"type": "object", "description": "上下文信息"},
            },
            "required": ["user_input", "user_id"],
        }

    def get_output_schema(self) -> Dict[str, Any]:
        """返回输出 Schema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "intent": {"type": "object"},
                "ai_message": {"type": "string"},
                "generative_ui": {"type": "object"},
                "skill_to_call": {"type": "string"},
            },
            "required": ["success", "intent", "ai_message"],
        }

    # ============= 配置管理 API =============

    def reload_config(self) -> bool:
        """
        热更新意图配置

        修改 intents.yaml 后调用此方法，
        无需重启服务即可生效。

        Returns:
            True: 更新成功
            False: 更新失败
        """
        return self._config_loader.reload()

    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息（用于调试）"""
        return self._config_loader.get_config_info()


# ============= 全局实例 =============

_intent_router_skill: Optional[IntentRouterSkill] = None


def get_intent_router_skill() -> IntentRouterSkill:
    """获取意图路由 Skill 单例"""
    global _intent_router_skill
    if _intent_router_skill is None:
        _intent_router_skill = IntentRouterSkill()
        logger.info("IntentRouterSkill initialized (v3.0.0 - config-driven)")
    return _intent_router_skill