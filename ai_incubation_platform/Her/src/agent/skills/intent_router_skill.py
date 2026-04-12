"""
IntentRouter Skill - 意图路由层（问诊台）

核心职责：
1. 统一识别用户输入的意图
2. 根据意图调用对应的 Skill
3. 返回标准化的 Generative UI 格式

AI Native 设计原则：
- 前端只需发送用户输入，无需判断意图
- 后端统一处理所有意图识别
- Generative UI 由后端决定，前端只负责渲染

DeerFlow 集成：
- DeerFlow 作为核心 Agent 运行时，负责意图识别和工具调用编排
- Her Skills 注册为 DeerFlow Tools
- IntentRouter 作为适配层，连接 Her 前端和 DeerFlow 后端
"""
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import json
import asyncio

from agent.skills.base import BaseSkill
from agent.skills.registry import get_skill_registry
from utils.logger import logger

# DeerFlow 集成
try:
    from deerflow_integration import (
        get_deerflow_client,
        is_deerflow_available,
        get_deerflow_status
    )
    DEERFLOW_INTEGRATION_AVAILABLE = True
except ImportError:
    logger.warning("IntentRouter: deerflow_integration 未安装，使用本地模式")
    DEERFLOW_INTEGRATION_AVAILABLE = False
    get_deerflow_client = None
    is_deerflow_available = lambda: False
    get_deerflow_status = lambda: {"available": False}


class IntentType(Enum):
    """
    用户意图类型枚举

    每个意图对应一个或多个 Skill 的调用
    """
    # ===== 核心业务意图 =====
    MATCHING = "matching"                       # 匹配：找对象、谈恋爱
    DAILY_RECOMMEND = "daily_recommend"         # 每日推荐：今日推荐
    PROFILE_COLLECTION = "profile_collection"   # 信息收集：新用户补充资料

    # ===== 关系相关意图 =====
    RELATIONSHIP_ANALYSIS = "relationship_analysis"  # 关系分析：我和TA怎么样
    TOPIC_SUGGESTION = "topic_suggestion"       # 话题推荐：聊什么
    ICEBREAKER = "icebreaker"                   # 破冰建议：怎么开场

    # ===== 约会相关意图 =====
    DATING_SUGGESTION = "dating_suggestion"     # 约会建议：去哪里约会
    DATE_PLANNING = "date_planning"             # 约会策划：帮我安排约会

    # ===== AI 预沟通 =====
    PRE_COMMUNICATION = "pre_communication"     # AI替身聊天：启动预沟通
    PRE_COMM_START = "pre_comm_start"           # 启动预沟通会话

    # ===== 系统交互意图（本地处理） =====
    GREETING = "greeting"                       # 问候：你好、早上好
    GRATITUDE = "gratitude"                     # 感谢：谢谢
    GOODBYE = "goodbye"                         # 告别：再见
    CAPABILITY_INQUIRY = "capability_inquiry"   # 能力询问：你能干嘛

    # ===== 兜底 =====
    GENERAL = "general"                         # 一般对话：其他情况


@dataclass
class IntentResult:
    """意图识别结果"""
    type: IntentType
    confidence: float = 1.0
    raw_input: str = ""
    params: Dict[str, Any] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


# 意图 → Skill 映射表
INTENT_SKILL_MAPPING: Dict[IntentType, Optional[str]] = {
    # 核心业务
    IntentType.MATCHING: "conversation_matchmaker",
    IntentType.DAILY_RECOMMEND: "conversation_matchmaker",
    IntentType.PROFILE_COLLECTION: "profile_collection",

    # 关系相关
    IntentType.RELATIONSHIP_ANALYSIS: "relationship_coach",
    IntentType.TOPIC_SUGGESTION: "conversation_matchmaker",
    IntentType.ICEBREAKER: "silence_breaker",

    # 约会相关
    IntentType.DATING_SUGGESTION: "date_planning",
    IntentType.DATE_PLANNING: "date_planning",

    # AI 预沟通
    IntentType.PRE_COMMUNICATION: "pre_communication",
    IntentType.PRE_COMM_START: "pre_communication",

    # 系统交互（本地处理）
    IntentType.GREETING: None,
    IntentType.GRATITUDE: None,
    IntentType.GOODBYE: None,
    IntentType.CAPABILITY_INQUIRY: None,

    # 兜底
    IntentType.GENERAL: "conversation_matchmaker",
}

# 本地处理的意图集合
LOCAL_INTENTS = {
    IntentType.GREETING,
    IntentType.GRATITUDE,
    IntentType.GOODBYE,
    IntentType.CAPABILITY_INQUIRY,
}


class IntentRouterSkill(BaseSkill):
    """
    意图路由 Skill - 统一的"问诊台"

    核心能力：
    1. DeerFlow 优先处理（AI Native 模式）
    2. 本地降级处理（DeerFlow 不可用时）
    3. 统一 Generative UI 返回格式

    DeerFlow 集成模式：
    - DeerFlow 负责意图识别、工具调用编排、状态管理
    - IntentRouter 作为适配层，连接前端和 DeerFlow
    - Her Skills 注册为 DeerFlow Tools（见 skills/ 目录）
    """

    name = "intent_router"
    version = "2.0.0"  # 升级版本，支持 DeerFlow
    description = """
    意图路由 Skill - 统一的对话入口（DeerFlow 集成）

    核心能力：
    - DeerFlow 优先：使用 DeerFlow Agent 进行智能意图识别和工具调用
    - 本地降级：DeerFlow 不可用时使用关键词匹配
    - 统一输出：标准化 Generative UI 格式

    这是系统的核心入口，所有对话都通过此 Skill 处理。
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_input": {"type": "string", "description": "用户输入内容"},
                "user_id": {"type": "string", "description": "用户 ID"},
                "context": {
                    "type": "object",
                    "description": "额外上下文信息",
                    "properties": {
                        "match_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                        "user_state": {"type": "string"},
                        "thread_id": {"type": "string"},  # DeerFlow thread ID
                    }
                }
            },
            "required": ["user_input", "user_id"]
        }

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "intent": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "confidence": {"type": "number"}
                    }
                },
                "ai_message": {"type": "string"},
                "generative_ui": {
                    "type": "object",
                    "properties": {
                        "component_type": {"type": "string"},
                        "props": {"type": "object"}
                    }
                },
                "suggested_actions": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "deerflow_used": {"type": "boolean"}  # 新增：是否使用了 DeerFlow
            },
            "required": ["success", "intent", "ai_message"]
        }

    async def execute(
        self,
        user_input: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行意图路由

        流程：
        1. 检查 DeerFlow 可用性
        2. DeerFlow 可用时：调用 DeerFlow Agent 处理
        3. DeerFlow 不可用时：降级到本地处理
        4. 返回统一格式结果
        """
        logger.info(f"IntentRouter: Processing input from user={user_id}")

        start_time = datetime.now()

        # Step 1: 尝试使用 DeerFlow
        if is_deerflow_available():
            logger.info("IntentRouter: Using DeerFlow for intent processing")
            result = await self._process_with_deerflow(user_input, user_id, context)
            if result:
                result["deerflow_used"] = True
                result["skill_metadata"] = {
                    "name": self.name,
                    "version": self.version,
                    "execution_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                    "engine": "deerflow"
                }
                return result
            else:
                logger.warning("IntentRouter: DeerFlow processing failed, falling back to local")

        # Step 2: 降级到本地处理
        logger.info("IntentRouter: Using local processing (DeerFlow not available or failed)")
        result = await self._process_local(user_input, user_id, context)
        result["deerflow_used"] = False
        result["skill_metadata"] = {
            "name": self.name,
            "version": self.version,
            "execution_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
            "engine": "local"
        }

        return result

    async def _process_with_deerflow(
        self,
        user_input: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[dict]:
        """
        使用 DeerFlow 处理用户输入

        DeerFlow 负责：
        - 意图识别（基于 LLM）
        - 工具调用编排（Her Skills 作为 Tools）
        - 状态管理（对话历史）
        - Generative UI 决策
        """
        try:
            client = get_deerflow_client()
            if not client:
                logger.warning("IntentRouter: DeerFlow client not available")
                return None

            # 构建 DeerFlow thread_id（用于对话历史追踪）
            thread_id = (context or {}).get("thread_id") or f"her-{user_id}"

            # 构建 DeerFlow prompt（包含 Her 上下文）
            deerflow_prompt = self._build_deerflow_prompt(user_input, user_id, context)

            logger.info(f"IntentRouter: Calling DeerFlow.chat with thread_id={thread_id}")

            # 调用 DeerFlow
            response = client.chat(deerflow_prompt, thread_id=thread_id)

            if not response:
                logger.warning("IntentRouter: DeerFlow returned empty response")
                return None

            # 解析 DeerFlow 响应，转换为 Her 格式
            result = self._parse_deerflow_response(response, user_input)

            logger.info(f"IntentRouter: DeerFlow response parsed, intent={result.get('intent', {}).get('type')}")

            return result

        except Exception as e:
            logger.error(f"IntentRouter: DeerFlow processing error: {e}")
            return None

    def _build_deerflow_prompt(
        self,
        user_input: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建 DeerFlow prompt

        包含：
        - 用户输入
        - 用户 ID（用于个性化）
        - 上下文信息
        - Her 业务上下文（匹配、约会、关系等）
        """
        context_str = ""
        if context:
            context_str = f"""
【上下文信息】
- 用户 ID: {user_id}
- 匹配 ID: {context.get('match_id', '无')}
- 对话 ID: {context.get('conversation_id', '无')}
- 用户状态: {context.get('user_state', '正常')}
"""

        return f"""
你是一个 AI 情感顾问 Her，帮助用户处理婚恋匹配、约会策划、关系分析等问题。

{context_str}

【用户输入】
{user_input}

请根据用户的输入，分析意图并调用相应的工具处理：
- 如果用户想找对象/匹配，调用 her_matchmaking 工具
- 如果用户要今日推荐，调用 her_daily_recommend 工具
- 如果用户询问关系分析，调用 her_relationship_analysis 工具
- 如果用户要话题建议，调用 her_topic_suggestion 工具
- 如果用户要约会策划，调用 her_date_planning 工具
- 如果用户要破冰建议，调用 her_icebreaker 工具

如果不需要调用工具，直接回复用户即可。
回复时请用中文，风格温暖、自然、友好。
"""

    def _parse_deerflow_response(self, response: str, user_input: str) -> dict:
        """
        解析 DeerFlow 响应，转换为 Her 格式

        DeerFlow 返回的是文本响应，需要解析提取意图和 Generative UI 信息
        """
        # 尝试从响应中提取结构化信息
        # DeerFlow 可能返回 JSON 格式或纯文本

        # 默认意图
        intent_type = IntentType.GENERAL.value
        confidence = 0.8

        # 尝试解析 JSON（如果 DeerFlow 返回了结构化数据）
        try:
            # 检查是否包含 JSON 标记
            if "```json" in response or response.strip().startswith("{"):
                # 提取 JSON
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    parsed = json.loads(json_str)
                    intent_type = parsed.get("intent_type", intent_type)
                    confidence = parsed.get("confidence", confidence)
        except (json.JSONDecodeError, ValueError):
            pass

        # 根据响应内容推断意图
        if any(keyword in response.lower() for keyword in ["匹配", "推荐", "小美", "小雨", "小雪"]):
            intent_type = IntentType.MATCHING.value
        elif any(keyword in response.lower() for keyword in ["话题", "聊什么"]):
            intent_type = IntentType.TOPIC_SUGGESTION.value
        elif any(keyword in response.lower() for keyword in ["约会", "去哪里"]):
            intent_type = IntentType.DATING_SUGGESTION.value
        elif any(keyword in response.lower() for keyword in ["关系", "健康度"]):
            intent_type = IntentType.RELATIONSHIP_ANALYSIS.value

        # 构建 Generative UI
        generative_ui = self._build_generative_ui_from_response(response, intent_type)

        return {
            "success": True,
            "intent": {
                "type": intent_type,
                "confidence": confidence
            },
            "ai_message": response,
            "generative_ui": generative_ui,
            "suggested_actions": self._get_suggested_actions_from_intent(intent_type)
        }

    def _build_generative_ui_from_response(self, response: str, intent_type: str) -> dict:
        """
        根据响应内容构建 Generative UI

        DeerFlow 的响应可能包含匹配结果、约会建议等，需要转换为对应的 UI 组件
        """
        # 匹配相关响应
        if intent_type in ["matching", "daily_recommend"]:
            # 尝试从响应中提取匹配结果
            if any(name in response for name in ["小美", "小雨", "小雪", "小雅", "小文"]):
                return {
                    "component_type": "MatchCardList",
                    "props": {"matches": self._extract_matches_from_response(response)}
                }

        # 约会建议响应
        elif intent_type in ["dating_suggestion", "date_planning"]:
            return {
                "component_type": "DateSuggestionCard",
                "props": {"suggestions": self._extract_date_suggestions_from_response(response)}
            }

        # 关系分析响应
        elif intent_type == "relationship_analysis":
            return {
                "component_type": "RelationshipReportCard",
                "props": {"report": self._extract_relationship_report_from_response(response)}
            }

        # 默认：简单文本响应
        return {
            "component_type": "AIResponseCard",
            "props": {"content": response}
        }

    def _extract_matches_from_response(self, response: str) -> List[Dict]:
        """
        从响应中提取匹配结果（简化实现）
        """
        # 这里是简化实现，实际应该从 DeerFlow 的工具调用结果中提取
        matches = []

        # 尝试解析结构化数据
        if "匹配度" in response:
            # 模拟提取匹配对象
            match_names = ["小美", "小雨", "小雪"]
            for name in match_names:
                if name in response:
                    matches.append({
                        "name": name,
                        "score": 0.9 - matches.__len__() * 0.05,
                        "reason": f"智能匹配推荐"
                    })

        return matches

    def _extract_date_suggestions_from_response(self, response: str) -> List[Dict]:
        """从响应中提取约会建议"""
        return [{"suggestion": response}]

    def _extract_relationship_report_from_response(self, response: str) -> Dict:
        """从响应中提取关系报告"""
        return {"summary": response, "health_score": 0.75}

    def _get_suggested_actions_from_intent(self, intent_type: str) -> List[Dict]:
        """根据意图类型获取建议操作"""
        actions_map = {
            "matching": [
                {"label": "查看详情", "action": "view_details"},
                {"label": "联系TA", "action": "contact"},
            ],
            "daily_recommend": [
                {"label": "查看更多", "action": "view_more"},
            ],
            "dating_suggestion": [
                {"label": "开始策划", "action": "start_planning"},
            ],
            "relationship_analysis": [
                {"label": "获取建议", "action": "get_advice"},
            ],
        }
        return actions_map.get(intent_type, [])

    async def _process_local(
        self,
        user_input: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        本地处理（降级方案）

        当 DeerFlow 不可用时，使用原有的关键词匹配和 Skill 调用
        """
        # 检查是否需要信息收集（新用户）
        if self._check_need_profile_collection(user_id):
            intent = IntentResult(
                type=IntentType.PROFILE_COLLECTION,
                confidence=1.0,
                raw_input=user_input,
                params={"reason": "new_user"}
            )
        else:
            # 尝试 LLM 意图识别（使用 Her 本地的 LLM 服务）
            try:
                llm_result = await self._classify_with_llm(user_input)
                if llm_result and llm_result.get("confidence", 0) >= 0.7:
                    intent = IntentResult(
                        type=IntentType(llm_result["intent_type"]),
                        confidence=llm_result["confidence"],
                        raw_input=user_input,
                        params=llm_result.get("params", {})
                    )
                else:
                    # 降级到关键词匹配
                    intent = self._classify_with_keywords(user_input)
            except Exception as e:
                logger.warning(f"IntentRouter: Local LLM classification failed: {e}")
                intent = self._classify_with_keywords(user_input)

        logger.info(f"IntentRouter: Local classified intent={intent.type.value}, confidence={intent.confidence}")

        # 根据意图处理
        if intent.type in LOCAL_INTENTS:
            result = self._handle_local_intent(intent)
        else:
            skill_name = INTENT_SKILL_MAPPING.get(intent.type)
            if skill_name:
                result = await self._call_skill(skill_name, user_id, intent, context)
            else:
                result = self._handle_general_intent(intent)

        # 确保返回格式统一
        result["intent"] = {
            "type": intent.type.value,
            "confidence": intent.confidence
        }

        return result

    def _check_need_profile_collection(self, user_id: str) -> bool:
        """
        检查是否需要信息收集

        新用户或信息不完整时，优先进入信息收集流程
        """
        try:
            from db.repositories import UserRepository
            from utils.db_session_manager import db_session

            with db_session() as db:
                user_repo = UserRepository(db)
                user = user_repo.get_by_username(user_id)

                if not user:
                    return True  # 新用户

                # 检查关键信息是否完整
                required_fields = ["age", "gender", "location"]
                for field in required_fields:
                    if not getattr(user, field, None):
                        return True

                return False
        except Exception as e:
            logger.warning(f"IntentRouter: Failed to check user profile: {e}")
            return False  # 出错时不阻塞流程

    async def _classify_with_llm(self, user_input: str) -> Optional[Dict]:
        """
        LLM 意图识别（本地降级）

        使用 Her 本地的 LLM 服务进行意图识别
        """
        try:
            from services.llm_semantic_service import get_llm_semantic_service

            llm_service = get_llm_semantic_service()

            prompt = self._build_intent_prompt(user_input)

            # 异步调用 LLM（添加超时保护）
            llm_response = await asyncio.wait_for(
                llm_service._call_llm(prompt),
                timeout=5.0  # 5秒超时，快速响应
            )

            # 解析 JSON
            result = json.loads(llm_response)

            # 验证意图类型
            valid_intents = [e.value for e in IntentType]
            if result.get("intent_type") not in valid_intents:
                result["intent_type"] = "general"
                result["confidence"] = 0.5

            return result

        except asyncio.TimeoutError:
            logger.warning("IntentRouter: Local LLM timeout")
            return None
        except json.JSONDecodeError:
            logger.warning("IntentRouter: Local LLM response not valid JSON")
            return None
        except Exception as e:
            logger.warning(f"IntentRouter: Local LLM error: {e}")
            return None

    def _build_intent_prompt(self, user_input: str) -> str:
        """构建意图识别 Prompt"""
        return f"""
你是一个意图识别专家。分析用户的输入，判断用户的真实意图。

用户输入："{user_input}"

请返回严格的 JSON 格式（不要有任何其他文字）：
{
    "intent_type": "matching/daily_recommend/profile_collection/relationship_analysis/topic_suggestion/icebreaker/dating_suggestion/date_planning/pre_communication/pre_comm_start/greeting/gratitude/goodbye/capability_inquiry/general",
    "confidence": 0.95,
    "params": {{
        "limit": 5,
        "location": "北京",
        "match_id": "xxx"
    }}
}

意图类型说明：
- matching: 用户想找对象、谈恋爱、匹配、介绍对象
- daily_recommend: 用户要看今日推荐、每日推荐
- profile_collection: 需要补充个人资料（一般不需要，系统自动判断）
- relationship_analysis: 分析和某人的关系状态、我和TA怎么样
- topic_suggestion: 想知道聊什么话题、有什么话题
- icebreaker: 破冰开场建议、怎么开口、怎么开场
- dating_suggestion: 约会地点/活动建议、去哪里约会
- date_planning: 帮我策划约会、安排约会
- pre_communication: AI替身聊天/预沟通相关咨询
- pre_comm_start: 启动预沟通会话、帮我代聊
- greeting: 打招呼、你好、hi、hello
- gratitude: 感谢、谢谢
- goodbye: 告别、再见
- capability_inquiry: 问你能做什么、你有什么功能、介绍你自己
- general: 其他一般对话

注意：
- 只返回 JSON，不要有任何其他文字
- confidence 范围 0.0-1.0
- params 根据实际需求填写，可以为空对象
"""

    def _classify_with_keywords(self, user_input: str) -> IntentResult:
        """
        关键词意图识别（降级方案）

        当 LLM 不可用时，使用关键词匹配
        """
        input_lower = user_input.lower().strip()

        # "开始" 关键词 - 新用户信息收集触发
        if input_lower in ["开始", "start", "开始吧"]:
            return IntentResult(type=IntentType.PROFILE_COLLECTION, raw_input=user_input, confidence=0.9)

        # 问候
        if any(w in input_lower for w in ["你好", "hi", "hello", "早上好", "晚上好", "嗨", "哈喽", "hey"]):
            return IntentResult(type=IntentType.GREETING, raw_input=user_input)

        # 感谢
        if any(w in input_lower for w in ["谢谢", "感谢", "thank", "thx"]):
            return IntentResult(type=IntentType.GRATITUDE, raw_input=user_input)

        # 告别
        if any(w in input_lower for w in ["再见", "拜拜", "bye", "回见"]):
            return IntentResult(type=IntentType.GOODBYE, raw_input=user_input)

        # 能力询问
        if any(w in input_lower for w in ["你能干", "你能做", "你有什么功能", "你是谁", "介绍你自己", "介绍一下你"]):
            return IntentResult(type=IntentType.CAPABILITY_INQUIRY, raw_input=user_input)

        # 匹配意图
        if any(w in input_lower for w in ["找对象", "谈恋爱", "帮我找", "匹配", "介绍对象", "想找个"]):
            return IntentResult(type=IntentType.MATCHING, raw_input=user_input)

        # 每日推荐
        if any(w in input_lower for w in ["今日推荐", "每日推荐", "每天推荐", "今天的推荐"]):
            return IntentResult(type=IntentType.DAILY_RECOMMEND, raw_input=user_input)

        # 预沟通启动
        if any(w in input_lower for w in ["启动预沟通", "ai替身", "代聊", "帮我聊"]):
            return IntentResult(type=IntentType.PRE_COMM_START, raw_input=user_input)

        # 预沟通咨询
        if any(w in input_lower for w in ["预沟通", "预沟通"]):
            return IntentResult(type=IntentType.PRE_COMMUNICATION, raw_input=user_input)

        # 关系分析
        if any(w in input_lower for w in ["关系", "我和ta", "分析关系", "关系怎么样", "进展"]):
            return IntentResult(type=IntentType.RELATIONSHIP_ANALYSIS, raw_input=user_input)

        # 话题推荐
        if any(w in input_lower for w in ["话题", "聊什么", "有什么话题", "推荐话题"]):
            return IntentResult(type=IntentType.TOPIC_SUGGESTION, raw_input=user_input)

        # 破冰建议
        if any(w in input_lower for w in ["破冰", "怎么开口", "怎么开场", "怎么开始", "开场白"]):
            return IntentResult(type=IntentType.ICEBREAKER, raw_input=user_input)

        # 约会建议
        if any(w in input_lower for w in ["约会", "去哪里", "约会地点", "约会去"]):
            return IntentResult(type=IntentType.DATING_SUGGESTION, raw_input=user_input)

        # 约会策划
        if any(w in input_lower for w in ["帮我安排", "策划约会", "安排约会", "约会计划"]):
            return IntentResult(type=IntentType.DATE_PLANNING, raw_input=user_input)

        # 默认：一般对话，交给 matchmaker 处理
        return IntentResult(
            type=IntentType.GENERAL,
            confidence=0.6,
            raw_input=user_input
        )

    def _handle_local_intent(self, intent: IntentResult) -> dict:
        """
        本地处理简单意图（问候、感谢等）

        这些意图不需要调用其他 Skill，直接返回固定响应
        """
        responses = {
            IntentType.GREETING: {
                "ai_message": "你好呀 🤍 我是 Her，你的情感顾问~\n\n我可以帮你：\n• 💕 读懂你和 TA 的匹配度\n• 💬 给你最懂你的破冰建议\n• 🎯 遇见为你挑选的人\n\n说说看，今天想聊什么？",
                "generative_ui": {"component_type": "SimpleResponse", "props": {}}
            },
            IntentType.GRATITUDE: {
                "ai_message": "能帮到你，我很开心 🤍",
                "generative_ui": {"component_type": "SimpleResponse", "props": {}}
            },
            IntentType.GOODBYE: {
                "ai_message": "下次见。愿你可以遇见属于自己的那份懂得 🤍",
                "generative_ui": {"component_type": "SimpleResponse", "props": {}}
            },
            IntentType.CAPABILITY_INQUIRY: {
                "ai_message": self._get_capability_intro(),
                "generative_ui": {"component_type": "CapabilityCard", "props": {"features": self._get_feature_list()}}
            },
        }

        response = responses.get(intent.type, {
            "ai_message": "收到~",
            "generative_ui": {"component_type": "SimpleResponse", "props": {}}
        })

        return {
            "success": True,
            "ai_message": response["ai_message"],
            "generative_ui": response["generative_ui"],
            "suggested_actions": self._get_suggested_actions(intent.type)
        }

    def _get_capability_intro(self) -> str:
        """获取能力介绍"""
        return """我是 Her 🤍 你的 AI 情感顾问

我可以帮你：

**💕 匹配与推荐**
- 根据你的需求帮你找对象
- 每日精选推荐

**💬 沟通支持**
- AI 预沟通：帮你先聊聊，看看是否合拍
- 破冰话题推荐：教你怎么开场
- 智能话题生成：聊什么不尴尬

**📊 关系分析**
- 关系健康度诊断
- 爱之语解读
- 关系趋势预测

**📅 约会策划**
- 约会地点推荐
- 约会活动策划
- 约会穿搭建议

和我说说你的需求，我来帮你~"""

    def _get_feature_list(self) -> List[Dict]:
        """获取功能列表"""
        return [
            {"name": "智能匹配", "icon": "💕", "trigger": "帮我找对象"},
            {"name": "每日推荐", "icon": "🌟", "trigger": "今日推荐"},
            {"name": "AI 预沟通", "icon": "🤖", "trigger": "启动预沟通"},
            {"name": "关系分析", "icon": "📊", "trigger": "分析我的关系"},
            {"name": "话题推荐", "icon": "💬", "trigger": "有什么话题"},
            {"name": "约会策划", "icon": "📅", "trigger": "约会去哪里"},
        ]

    async def _call_skill(
        self,
        skill_name: str,
        user_id: str,
        intent: IntentResult,
        context: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        调用对应的 Skill

        根据意图类型构建参数，调用 Skill 执行
        """
        registry = get_skill_registry()

        # 构建 Skill 参数
        skill_params = {
            "user_id": user_id,
            "context": {
                "user_input": intent.raw_input,
                "intent_type": intent.type.value,
                **(intent.params or {}),
                **(context or {})
            }
        }

        # 根据意图类型添加特定参数
        if intent.type == IntentType.MATCHING:
            skill_params["service_type"] = "intent_matching"
            skill_params["context"]["user_intent"] = intent.raw_input
        elif intent.type == IntentType.DAILY_RECOMMEND:
            skill_params["service_type"] = "daily_recommend"
        elif intent.type == IntentType.TOPIC_SUGGESTION:
            skill_params["service_type"] = "topic_suggestion"
            if intent.params.get("match_id"):
                skill_params["context"]["match_id"] = intent.params["match_id"]
        elif intent.type == IntentType.RELATIONSHIP_ANALYSIS:
            skill_params["service_type"] = "relationship_analysis"
        elif intent.type == IntentType.PRE_COMMUNICATION:
            skill_params["action"] = "list_sessions"
        elif intent.type == IntentType.PRE_COMM_START:
            skill_params["action"] = "start_session"
        elif intent.type == IntentType.DATING_SUGGESTION:
            skill_params["action"] = "suggest_date_spots"
        elif intent.type == IntentType.DATE_PLANNING:
            skill_params["action"] = "plan_date"

        logger.info(f"IntentRouter: Calling skill={skill_name}, params_keys={list(skill_params.keys())}")

        # 执行 Skill
        try:
            result = await registry.execute(skill_name, **skill_params)

            # 标准化返回格式
            return {
                "success": result.get("success", True),
                "ai_message": result.get("ai_message", ""),
                "generative_ui": result.get("generative_ui", {
                    "component_type": "AIResponseCard",
                    "props": {"data": result.get("matchmaker_result", result)}
                }),
                "suggested_actions": result.get("suggested_actions", [])
            }
        except Exception as e:
            logger.error(f"IntentRouter: Skill execution failed: {e}")
            return {
                "success": False,
                "ai_message": f"抱歉，处理时出现了一些问题，请稍后再试~",
                "generative_ui": {"component_type": "SimpleResponse", "props": {}},
                "suggested_actions": []
            }

    def _handle_general_intent(self, intent: IntentResult) -> dict:
        """处理一般意图（兜底）"""
        return {
            "success": True,
            "ai_message": '我收到了你的消息。如果你想找对象，可以说"帮我找对象"；如果想知道我能做什么，可以问"你能干嘛"~',
            "generative_ui": {"component_type": "SimpleResponse", "props": {}},
            "suggested_actions": [
                {"label": "帮我找对象", "action": "matching"},
                {"label": "今日推荐", "action": "daily_recommend"},
                {"label": "你能干嘛", "action": "capability_inquiry"},
            ]
        }

    def _get_suggested_actions(self, intent_type: IntentType) -> List[Dict]:
        """根据意图类型获取建议操作"""
        actions_map = {
            IntentType.GREETING: [
                {"label": "帮我找对象", "action": "matching"},
                {"label": "今日推荐", "action": "daily_recommend"},
                {"label": "你能干嘛", "action": "capability_inquiry"},
            ],
            IntentType.CAPABILITY_INQUIRY: [
                {"label": "帮我找对象", "action": "matching"},
                {"label": "今日推荐", "action": "daily_recommend"},
                {"label": "启动预沟通", "action": "pre_comm_start"},
            ],
        }
        return actions_map.get(intent_type, [])


# 全局 Skill 实例
_intent_router_instance: Optional[IntentRouterSkill] = None


def get_intent_router_skill() -> IntentRouterSkill:
    """获取 IntentRouter Skill 单例实例"""
    global _intent_router_instance
    if _intent_router_instance is None:
        _intent_router_instance = IntentRouterSkill()
    return _intent_router_instance