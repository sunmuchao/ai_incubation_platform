"""
对话式匹配服务 - 编排层

重构说明：
- 原 1100 行拆分为 6 个组件
- 此文件为编排层，约 200 行
- 各组件职责清晰，便于维护

组件分布：
- IntentAnalyzer（约 150 行）→ 此文件
- QueryQualityChecker（约 220 行）→ 此文件
- MatchExecutor（约 150 行）→ match_executor.py
- AdviceGenerator（约 150 行）→ advice_generator.py
- UIBuilder（约 100 行）→ ui_builder.py
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

from utils.logger import logger
from services.llm_semantic_service import get_llm_semantic_service
from services.her_advisor_service import (
    HerAdvisorService,
    CognitiveBiasDetector,
    MatchAdvisor,
    ProactiveSuggestionGenerator,
    CognitiveBiasAnalysis,
    MatchAdvice,
    ProactiveSuggestion,
)
from services.profile_dataclasses import DesireProfile, SelfProfile
from services.user_profile_service import (
    UserProfileService,
    ProfileUpdateEngine,
    get_user_profile_service,
    get_profile_update_engine,
)
from services.conversation_match.match_executor import get_match_executor
from services.conversation_match.advice_generator import get_advice_generator
from services.conversation_match.ui_builder import get_ui_builder


# ============= 数据结构定义 =============

@dataclass
class UserIntent:
    """用户意图分析结果"""
    intent_type: str = ""
    extracted_conditions: Dict[str, Any] = field(default_factory=dict)
    preference_mentioned: str = ""
    emotional_state: str = ""
    confidence: float = 0.0


@dataclass
class QueryQualityCheckResult:
    """查询质量校验结果"""
    is_clear: bool = True
    is_complete: bool = True
    overall_passed: bool = True
    clarity_issues: List[str] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class MatchResultWithAdvice:
    """带 Her 建议的匹配结果"""
    candidate_id: str
    candidate_name: str
    candidate_profile: Dict[str, Any]
    compatibility_score: float
    score_breakdown: Dict[str, float]
    her_advice: Optional[MatchAdvice] = None
    match_reasoning: str = ""
    risk_warnings: List[str] = field(default_factory=list)


@dataclass
class ConversationMatchResponse:
    """对话匹配响应"""
    ai_message: str
    intent_type: str
    matches: List[MatchResultWithAdvice] = field(default_factory=list)
    bias_analysis: Optional[CognitiveBiasAnalysis] = None
    proactive_suggestion: Optional[ProactiveSuggestion] = None
    generative_ui: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[Dict[str, str]] = field(default_factory=list)


# ============= IntentAnalyzer - 意图分析器 =============

class IntentAnalyzer:
    """意图分析器 - 使用 LLM 理解用户自然语言意图"""

    def __init__(self):
        self._llm_service = get_llm_semantic_service()

    async def analyze_intent(
        self,
        message: str,
        context: Optional[List[Dict[str, str]]] = None,
    ) -> UserIntent:
        """分析用户意图"""
        logger.info(f"[IntentAnalyzer] 分析消息: {message[:50]}...")

        prompt = self._build_intent_prompt(message, context)

        try:
            llm_response = await self._llm_service._call_llm(prompt)
            intent = self._parse_intent_response(llm_response)

            logger.info(f"[IntentAnalyzer] 意图: {intent.intent_type}, confidence={intent.confidence}")
            return intent

        except Exception as e:
            logger.error(f"[IntentAnalyzer] 分析失败: {e}")
            return self._fallback_intent_analysis(message)

    def _build_intent_prompt(self, message: str, context: Optional[List[Dict[str, str]]]) -> str:
        """构建意图分析 Prompt"""
        context_str = ""
        if context:
            context_str = "对话历史：\n"
            for msg in context[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_str += f"{role}: {content}\n"
            context_str += "\n"

        return f'''你是一位专业的婚恋顾问 Her，需要分析用户的消息意图。

{context_str}
用户消息：
"{message}"

【意图分类】
- match_request: 匹配请求（用户想找人）
- preference_update: 偏好更新（用户表达想要什么样的）
- inquiry: 咨询问题（用户问问题）
- feedback: 匹配反馈（用户对某个匹配对象的反馈）
- conversation: 一般对话

【extracted_conditions 字段说明】
从用户消息中提取匹配条件：
- interests: 用户指定的兴趣偏好（如"喜欢户外运动的人"则interests为户外运动列表）
- age_range: 年龄范围（如"25-30岁"则age_range为25到30）
- location: 地点偏好（如"在北京"则location为北京）
- gender: 性别偏好（如"女生"则gender为female）
- relationship_goal: 关系目标（如"认真谈恋爱"则relationship_goal为serious）

【输出格式】
返回 JSON 格式：
请返回一个JSON对象，包含intent_type、extracted_conditions（其中interests为兴趣列表、age_range为年龄范围数组、location为地点）、preference_mentioned、emotional_state、confidence字段。

只返回 JSON。'''

    def _parse_intent_response(self, response: str) -> UserIntent:
        """解析意图分析响应"""
        try:
            response = response.strip()
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]

            data = json.loads(response.strip())

            return UserIntent(
                intent_type=data.get("intent_type", "conversation"),
                extracted_conditions=data.get("extracted_conditions", {}),
                preference_mentioned=data.get("preference_mentioned", ""),
                emotional_state=data.get("emotional_state", "neutral"),
                confidence=data.get("confidence", 0.5),
            )

        except json.JSONDecodeError:
            return UserIntent(intent_type="conversation", confidence=0.0)

    def _fallback_intent_analysis(self, message: str) -> UserIntent:
        """降级意图分析（关键词匹配）"""
        message_lower = message.lower()
        extracted_conditions = {}

        # ===== 匹配请求关键词（扩展）=====
        # 包含"找对象"、"帮我找"、"找人"等常见表达
        match_keywords = [
            "找对象", "找人", "帮我找", "推荐", "匹配",
            "看看", "有没有", "想找", "找女朋友", "找男朋友",
            "帮我介绍", "介绍对象", "合适的人"
        ]
        if any(kw in message_lower for kw in match_keywords):
            logger.info(f"[IntentAnalyzer] 降级识别为 match_request: 关键词匹配")

            # 提取兴趣（如"喜欢户外运动的人"）
            import re
            # 匹配 "喜欢XX的人" 或 "爱XX的人"
            interest_match = re.search(r"喜欢(\w+)的人|爱(\w+)的人", message_lower)
            if interest_match:
                interest = interest_match.group(1) or interest_match.group(2)
                if interest:
                    extracted_conditions["interests"] = [interest]

            return UserIntent(
                intent_type="match_request",
                extracted_conditions=extracted_conditions,
                confidence=0.6
            )

        inquiry_keywords = ["怎么样", "什么是", "如何", "能不能"]
        if any(kw in message_lower for kw in inquiry_keywords):
            return UserIntent(intent_type="inquiry", confidence=0.6)

        feedback_keywords = ["不喜欢", "还行", "不太合适", "挺好的"]
        if any(kw in message_lower for kw in feedback_keywords):
            return UserIntent(intent_type="feedback", confidence=0.6)

        logger.info(f"[IntentAnalyzer] 降级识别为 conversation: 无关键词匹配")
        return UserIntent(intent_type="conversation", confidence=0.5)


# ============= QueryQualityChecker - 查询质量校验器 =============

class QueryQualityChecker:
    """查询质量校验器 - 在执行匹配前校验输入质量"""

    CRITICAL_FIELDS = ["age_range", "location", "relationship_goal"]
    RECOMMENDED_FIELDS = ["personality_type", "interests"]

    def __init__(self):
        self._llm_service = get_llm_semantic_service()

    async def check_query_quality(
        self,
        intent: UserIntent,
        user_profile: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[List[Dict[str, str]]] = None,
    ) -> QueryQualityCheckResult:
        """校验查询质量"""
        logger.info(f"[QueryQualityChecker] 校验查询质量, intent_type={intent.intent_type}")

        if intent.intent_type != "match_request":
            return QueryQualityCheckResult(overall_passed=True, confidence=1.0)

        prompt = self._build_quality_check_prompt(intent, user_profile, conversation_context)

        try:
            llm_response = await self._llm_service._call_llm(prompt)
            result = self._parse_quality_check_response(llm_response)

            logger.info(f"[QueryQualityChecker] 校验结果: passed={result.overall_passed}")
            return result

        except Exception as e:
            logger.error(f"[QueryQualityChecker] AI 校验失败: {e}")
            return self._fallback_quality_check(intent, user_profile)

    def _build_quality_check_prompt(
        self,
        intent: UserIntent,
        user_profile: Optional[Dict[str, Any]],
        conversation_context: Optional[List[Dict[str, str]]],
    ) -> str:
        """构建查询质量校验 Prompt"""
        profile_info = ""
        if user_profile:
            profile_info = f"用户已有画像：年龄={user_profile.get('age')}, 地点={user_profile.get('location')}, 目标={user_profile.get('relationship_goal')}"

        conditions_str = "提取的匹配条件：" + str(intent.extracted_conditions)

        return f'''你是一位专业的婚恋顾问，判断匹配查询是否足够清晰和完整。

{profile_info}
{conditions_str}

【输出格式】
返回 JSON：请返回包含is_clear、is_complete、overall_passed、clarity_issues数组、missing_info数组、follow_up_questions数组、confidence字段的JSON对象。

只返回 JSON。'''

    def _parse_quality_check_response(self, response: str) -> QueryQualityCheckResult:
        """解析校验响应"""
        try:
            response = response.strip()
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]

            data = json.loads(response.strip())

            return QueryQualityCheckResult(
                is_clear=data.get("is_clear", True),
                is_complete=data.get("is_complete", True),
                overall_passed=data.get("overall_passed", True),
                clarity_issues=data.get("clarity_issues", []),
                missing_info=data.get("missing_info", []),
                follow_up_questions=data.get("follow_up_questions", []),
                confidence=data.get("confidence", 0.8),
            )

        except json.JSONDecodeError:
            return QueryQualityCheckResult(overall_passed=True, confidence=0.5)

    def _fallback_quality_check(
        self,
        intent: UserIntent,
        user_profile: Optional[Dict[str, Any]],
    ) -> QueryQualityCheckResult:
        """降级校验（基于规则）"""
        missing_info = []
        follow_up_questions = []

        conditions = intent.extracted_conditions

        if not conditions.get("age_range") and not (user_profile and user_profile.get("age")):
            missing_info.append("年龄范围")
            follow_up_questions.append("你希望找多大年龄范围的对象呢？")

        if not conditions.get("location") and not (user_profile and user_profile.get("location")):
            missing_info.append("地点/城市")
            follow_up_questions.append("你在哪个城市？")

        if not conditions.get("relationship_goal") and not (user_profile and user_profile.get("relationship_goal")):
            missing_info.append("关系目标")
            follow_up_questions.append("你希望找什么样的关系？")

        is_complete = len(missing_info) == 0
        overall_passed = is_complete and intent.confidence > 0.5

        return QueryQualityCheckResult(
            is_clear=intent.confidence > 0.5,
            is_complete=is_complete,
            overall_passed=overall_passed,
            clarity_issues=[] if intent.confidence > 0.5 else ["意图不够明确"],
            missing_info=missing_info,
            follow_up_questions=follow_up_questions,
            confidence=0.6,
        )


# ============= ConversationMatchService - 编排层 =============

class ConversationMatchService:
    """
    对话式匹配服务 - 编排层

    职责：
    1. 接收用户消息
    2. 编排各组件执行
    3. 返回统一响应

    不再直接执行具体业务，而是协调各组件：
    - IntentAnalyzer → 意图分析
    - QueryQualityChecker → 质量校验
    - MatchExecutor → 匹配执行
    - AdviceGenerator → 建议生成
    - UIBuilder → UI 构建
    """

    def __init__(self):
        # 意图分析器（保留在此文件）
        self._intent_analyzer = IntentAnalyzer()
        self._query_quality_checker = QueryQualityChecker()

        # 外部服务
        self._profile_service = get_user_profile_service()
        self._profile_update_engine = get_profile_update_engine()
        self._her_advisor = HerAdvisorService()

        # 拆分后的组件
        self._match_executor = get_match_executor()
        self._advice_generator = get_advice_generator()
        self._ui_builder = get_ui_builder()

    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ConversationMatchResponse:
        """处理用户消息 - 统一入口"""
        logger.info(f"[ConversationMatch] 处理用户 {user_id} 的消息")

        # Step 1: 意图理解
        intent = await self._intent_analyzer.analyze_intent(message, conversation_history)

        # Step 2: 获取用户画像
        self_profile, desire_profile = await self._profile_service.get_or_create_profile(user_id)

        # Step 3: 如果用户表达了偏好，更新 DesireProfile
        if intent.preference_mentioned:
            await self._profile_update_engine.process_conversation_analysis(
                user_id,
                intent.preference_mentioned,
                {"stated_preference": intent.preference_mentioned, "extracted_conditions": intent.extracted_conditions}
            )

        # Step 4: 根据意图类型分发处理
        if intent.intent_type == "match_request":
            return await self._handle_match_request(
                user_id, self_profile, desire_profile, intent, message, conversation_history
            )

        if intent.intent_type == "preference_update":
            response_data = self._ui_builder.build_preference_update_response(intent.preference_mentioned)
            return ConversationMatchResponse(**response_data)

        # 一般对话
        response_data = self._ui_builder.build_general_conversation_response()
        return ConversationMatchResponse(**response_data)

    async def _handle_match_request(
        self,
        user_id: str,
        self_profile: SelfProfile,
        desire_profile: DesireProfile,
        intent: UserIntent,
        original_message: str,
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> ConversationMatchResponse:
        """处理匹配请求"""
        logger.info(f"[ConversationMatch] 执行匹配流程 for user {user_id}")

        # Step 0: 查询质量校验
        quality_check = await self._query_quality_checker.check_query_quality(
            intent,
            user_profile=self_profile.to_dict() if self_profile else None,
            conversation_context=conversation_history,
        )

        # 校验不通过 → 返回追问
        if not quality_check.overall_passed:
            response_data = self._ui_builder.build_quality_check_followup_response(
                intent, quality_check, original_message
            )
            return ConversationMatchResponse(**response_data)

        # Step 1: 认知偏差识别
        bias_analysis = await self._her_advisor.analyze_user_bias(
            user_id, self_profile, desire_profile
        )

        # Step 2: 执行匹配（使用 MatchExecutor）
        matches = await self._match_executor.execute_matching(
            user_id, self_profile, desire_profile, intent.extracted_conditions
        )

        # Step 3: 生成建议（使用 AdviceGenerator）
        matches_with_advice = await self._advice_generator.generate_match_advices(
            user_id, self_profile, desire_profile, matches
        )

        # Step 4: 生成主动建议
        proactive_suggestion = await self._her_advisor.generate_proactive_suggestions(
            user_id,
            (self_profile, desire_profile),
            bias_analysis,
            [{"candidate_id": m["user_id"], "score": m["score"]} for m in matches],
        )

        # Step 5: 生成响应消息
        ai_message = await self._advice_generator.generate_response_message(
            intent, matches_with_advice, bias_analysis, proactive_suggestion
        )

        # Step 6: 构建 UI（使用 UIBuilder）
        generative_ui = self._ui_builder.build_generative_ui(matches_with_advice, intent)
        suggested_actions = self._ui_builder.build_suggested_actions(matches_with_advice, bias_analysis)

        return ConversationMatchResponse(
            ai_message=ai_message,
            intent_type=intent.intent_type,
            matches=matches_with_advice,
            bias_analysis=bias_analysis,
            proactive_suggestion=proactive_suggestion,
            generative_ui=generative_ui,
            suggested_actions=suggested_actions,
        )


# ============= 全局服务实例 =============

_conversation_match_service: Optional[ConversationMatchService] = None


def get_conversation_match_service() -> ConversationMatchService:
    """获取对话匹配服务单例"""
    global _conversation_match_service
    if _conversation_match_service is None:
        _conversation_match_service = ConversationMatchService()
        logger.info("ConversationMatchService initialized (refactored)")
    return _conversation_match_service