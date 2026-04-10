"""
Agentic 匹配引擎（许愿模式）

继承 MatchEngine 基类，实现用户主导、AI 顾问辅助的匹配模式。
定位：增值服务，付费，服务有更高需求的用户。

核心特点：
- 用户主导：用户按自己意愿描述需求
- AI 顾问：帮助分析、给建议、告知风险
- 自然语言：支持抽象概念（书卷气、上进心）
- 迭代优化：不满意可调整需求继续寻找
- 付费服务：按次/订阅收费

⚠️ 责任边界：
AI只负责帮你找和分析利弊
最终能不能聊得来，AI不负责
感情需要双方经营
"""

import time
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from matching.engine_base import (
    MatchEngine,
    MatchRequest,
    MatchResult,
    MatchCandidate,
    EngineMetrics,
    EngineType,
    RiskLevel,
    RiskAnalysis,
    WishAnalysis,
)
from matching.rule_engine import RuleMatchEngine, get_rule_engine
from services.llm_semantic_service import get_llm_semantic_service
from utils.logger import logger


@dataclass
class WishModeSession:
    """
    许愿模式会话

    记录一次完整的许愿会话过程
    """
    session_id: str
    user_id: str
    started_at: datetime
    original_wish: str  # 用户原始愿望描述

    # 分析结果
    wish_analysis: Optional[WishAnalysis] = None

    # 迭代历史
    iterations: List[Dict[str, Any]] = field(default_factory=list)
    current_iteration: int = 0

    # 最终结果
    final_candidates: List[MatchCandidate] = field(default_factory=list)
    is_completed: bool = False

    # 统计
    total_latency_ms: float = 0.0


class WishModeAdvisor:
    """
    许愿模式 AI 顾问

    职责：
    1. 理解用户需求
    2. 分析需求合理性
    3. 告知潜在风险
    4. 给出专业建议
    5. 迭代推荐
    """

    def __init__(self):
        """初始化 AI 顾问"""
        self._llm_service = get_llm_semantic_service()
        logger.info("WishModeAdvisor initialized")

    async def analyze_user_wish(
        self,
        user_wish: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> WishAnalysis:
        """
        分析用户愿望

        Args:
            user_wish: 用户愿望描述
            user_profile: 用户画像（可选）

        Returns:
            WishAnalysis: 愿望分析结果
        """
        if not self._llm_service.enabled:
            return self._fallback_wish_analysis(user_wish)

        try:
            prompt = self._build_wish_analysis_prompt(user_wish, user_profile)
            response = await self._llm_service._call_llm(prompt)
            result = self._parse_wish_analysis_response(response, user_wish)
            return result

        except Exception as e:
            logger.error(f"WishModeAdvisor: Wish analysis failed: {e}")
            return self._fallback_wish_analysis(user_wish)

    def _build_wish_analysis_prompt(
        self,
        user_wish: str,
        user_profile: Optional[Dict[str, Any]]
    ) -> str:
        """构建愿望分析 Prompt"""
        profile_str = ""
        if user_profile:
            profile_str = f"""
【用户画像】
{json.dumps(user_profile, ensure_ascii=False, indent=2)}
"""

        return f"""
你是一位专业的婚恋顾问 AI，需要分析用户对理想伴侣的描述。

{profile_str}

【用户愿望】
"{user_wish}"

请分析：

1. **需求拆解**
   - 提取用户的核心需求
   - 区分硬性条件（必须满足）和软性偏好（可以放宽）
   - 识别抽象概念（如"书卷气"、"上进心"）

2. **风险分析**
   - 多个条件叠加对匹配池的影响
   - 市场竞争情况
   - 潜在的匹配风险
   - 评估风险等级：low/medium/high/extreme

3. **专业建议**
   - 哪些条件可以适当放宽
   - 可能错过的优质人群
   - 建议的调整方向

4. **免责声明**
   AI只负责帮你找和分析利弊
   最终能否聊得来取决于你们双方
   感情需要经营

【输出格式】请返回 JSON 格式：
{
    "core_needs": ["核心需求 1", "核心需求 2"],
    "hard_conditions": ["硬性条件 1", "硬性条件 2"],
    "soft_preferences": ["软性偏好 1", "软性偏好 2"],
    "risk_analysis": {
        "level": "low/medium/high/extreme",
        "description": "风险描述",
        "warning": "警告信息（如有）",
        "pool_size_estimate": 100,
        "competition_level": "low/medium/high/extreme",
        "potential_risks": ["风险 1", "风险 2"]
    },
    "suggestions": ["建议 1", "建议 2"],
    "disclaimer": "AI只负责帮你找和分析，最终能否聊得来取决于你们双方。感情需要经营。"
}
"""

    def _parse_wish_analysis_response(
        self,
        response: str,
        original_wish: str
    ) -> WishAnalysis:
        """解析愿望分析响应"""
        try:
            data = json.loads(response)

            # 解析风险分析
            risk_data = data.get("risk_analysis", {})
            risk_level = RiskLevel(risk_data.get("level", "medium"))

            risk_analysis = RiskAnalysis(
                level=risk_level,
                description=risk_data.get("description", ""),
                warning=risk_data.get("warning"),
                pool_size_estimate=risk_data.get("pool_size_estimate"),
                competition_level=risk_data.get("competition_level"),
                potential_risks=risk_data.get("potential_risks", []),
                suggestions=data.get("suggestions", []),
                disclaimer=data.get("disclaimer", "AI只负责帮你找和分析，最终能否聊得来取决于你们双方。感情需要经营。")
            )

            return WishAnalysis(
                core_needs=data.get("core_needs", []),
                hard_conditions=data.get("hard_conditions", []),
                soft_preferences=data.get("soft_preferences", []),
                risk_analysis=risk_analysis,
                suggestions=data.get("suggestions", []),
                disclaimer=data.get("disclaimer", "")
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"WishModeAdvisor: Failed to parse wish analysis: {e}")
            return self._fallback_wish_analysis(original_wish)

    def _fallback_wish_analysis(self, user_wish: str) -> WishAnalysis:
        """降级愿望分析"""
        # 简单拆分关键词
        keywords = user_wish.split()
        return WishAnalysis(
            core_needs=keywords[:3] if keywords else ["未分析"],
            hard_conditions=[],
            soft_preferences=keywords[3:5] if len(keywords) > 3 else [],
            risk_analysis=RiskAnalysis(
                level=RiskLevel.MEDIUM,
                description="LLM 服务不可用，无法进行深度分析",
                disclaimer="AI只负责帮你找和分析，最终能否聊得来取决于你们双方。感情需要经营。"
            ),
            suggestions=["建议详细描述你的期望"],
            disclaimer="AI只负责帮你找和分析，最终能否聊得来取决于你们双方。感情需要经营。"
        )

    async def generate_candidate_risk_warning(
        self,
        candidate: MatchCandidate,
        user_wish: str,
        wish_analysis: WishAnalysis
    ) -> List[str]:
        """
        为单个候选人生成风险提示

        Args:
            candidate: 候选人
            user_wish: 用户愿望
            wish_analysis: 愿望分析

        Returns:
            风险提示列表
        """
        if not self._llm_service.enabled:
            return self._fallback_candidate_warning(candidate, user_wish)

        try:
            prompt = self._build_candidate_warning_prompt(candidate, user_wish, wish_analysis)
            response = await self._llm_service._call_llm(prompt)
            result = self._parse_candidate_warning_response(response)
            return result

        except Exception as e:
            logger.error(f"WishModeAdvisor: Candidate warning failed: {e}")
            return self._fallback_candidate_warning(candidate, user_wish)

    def _build_candidate_warning_prompt(
        self,
        candidate: MatchCandidate,
        user_wish: str,
        wish_analysis: WishAnalysis
    ) -> str:
        """构建候选人风险提示 Prompt"""
        candidate_info = {
            "name": candidate.name,
            "age": candidate.age,
            "location": candidate.location,
            "interests": candidate.interests[:5],
            "bio": candidate.bio[:100] if candidate.bio else None,
            "score": round(candidate.score * 100),
        }

        return f"""
你是一位专业的婚恋顾问 AI，需要为匹配候选人生成风险提示。

【用户愿望】
"{user_wish}"

【愿望分析】
- 硬性条件：{wish_analysis.hard_conditions}
- 软性偏好：{wish_analysis.soft_preferences}
- 风险等级：{wish_analysis.risk_analysis.level.value}

【候选人信息】
{json.dumps(candidate_info, ensure_ascii=False, indent=2)}

请分析：
1. 这个候选人满足了哪些条件
2. 哪些条件没有满足，差距多大
3. 可能的风险点
4. 需要注意的地方
5. 建议的沟通方向

【输出格式】请返回 JSON 格式：
{
    "match_points": ["匹配点 1", "匹配点 2"],
    "attention_points": ["注意事项 1", "注意事项 2"],
    "risk_warnings": ["风险 1", "风险 2"],
    "communication_suggestions": ["沟通建议 1", "沟通建议 2"]
}
"""

    def _parse_candidate_warning_response(self, response: str) -> List[str]:
        """解析候选人风险提示响应"""
        try:
            data = json.loads(response)
            return data.get("risk_warnings", [])

        except json.JSONDecodeError:
            return ["无法生成详细风险提示"]

    def _fallback_candidate_warning(
        self,
        candidate: MatchCandidate,
        user_wish: str
    ) -> List[str]:
        """降级候选人风险提示"""
        warnings = []

        # 简单匹配度判断
        if candidate.score < 0.5:
            warnings.append("匹配度较低，建议更多了解")

        # 基于用户愿望关键词的简单检查
        wish_keywords = user_wish.lower().split()
        candidate_keywords = " ".join(candidate.interests).lower()

        for kw in wish_keywords[:3]:
            if kw not in candidate_keywords:
                warnings.append(f"可能不完全符合'{kw}'的期望")

        return warnings if warnings else ["无明显风险提示"]


class AgenticMatchEngine(MatchEngine):
    """
    Agentic 匹配引擎（许愿模式）

    用户主导的匹配引擎，AI顾问辅助分析和推荐。
    """

    engine_type = EngineType.AGENTIC

    def __init__(self):
        """初始化 Agentic 引擎"""
        self._advisor = WishModeAdvisor()
        self._rule_engine = get_rule_engine()
        self.metrics = EngineMetrics(engine_type=EngineType.AGENTIC)
        self._sessions: Dict[str, WishModeSession] = {}  # 会话缓存
        logger.info("AgenticMatchEngine initialized")

    async def match(self, request: MatchRequest) -> MatchResult:
        """
        执行 Agentic 匹配

        Args:
            request: 匹配请求（需包含 wish_description）

        Returns:
            MatchResult: 匹配结果
        """
        start_time = time.time()

        # 验证请求
        validation_error = self._validate_agentic_request(request)
        if validation_error:
            return MatchResult(
                success=False,
                error=validation_error,
                error_code="INVALID_REQUEST",
                engine_type=EngineType.AGENTIC,
            )

        try:
            # 获取用户画像
            user_profile = self._get_user_profile(request.user_id)

            # Step 1: AI 分析用户愿望
            wish_analysis = await self._advisor.analyze_user_wish(
                request.wish_description,
                user_profile
            )

            # Step 2: 将愿望转化为查询条件
            query_conditions = self._wish_to_query_conditions(
                request.wish_description,
                wish_analysis
            )

            # Step 3: 使用规则引擎进行基础匹配
            rule_request = MatchRequest(
                user_id=request.user_id,
                limit=request.limit * 2,  # 获取更多候选
                filters=query_conditions
            )
            base_result = await self._rule_engine.match(rule_request)

            if not base_result.success:
                return MatchResult(
                    success=False,
                    error="基础匹配失败",
                    error_code="BASE_MATCH_FAILED",
                    engine_type=EngineType.AGENTIC,
                )

            # Step 4: AI 为每个候选人生成风险提示
            enhanced_candidates = []
            for candidate in base_result.candidates[:request.limit]:
                risk_warnings = await self._advisor.generate_candidate_risk_warning(
                    candidate,
                    request.wish_description,
                    wish_analysis
                )
                candidate.risk_warnings = risk_warnings

                # AI 生成匹配点
                match_points = self._generate_match_points(candidate, wish_analysis)
                candidate.match_points = match_points

                enhanced_candidates.append(candidate)

            # Step 5: 构建结果
            latency_ms = (time.time() - start_time) * 1000

            result = MatchResult(
                success=True,
                candidates=enhanced_candidates,
                total_count=len(enhanced_candidates),
                wish_analysis=wish_analysis,
                disclaimer=wish_analysis.disclaimer,
                engine_type=EngineType.AGENTIC,
                latency_ms=latency_ms,
                timestamp=datetime.now(),
            )

            # 记录指标
            self.metrics.record_request(
                success=True,
                latency_ms=latency_ms,
                iterations=1,
                candidates_count=len(enhanced_candidates)
            )

            logger.info(
                f"AgenticMatchEngine: matched {len(enhanced_candidates)} candidates "
                f"for user {request.user_id} in {latency_ms:.2f}ms"
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"AgenticMatchEngine error: {e}")

            self.metrics.record_request(
                success=False,
                latency_ms=latency_ms
            )

            return MatchResult(
                success=False,
                error=str(e),
                error_code="ENGINE_ERROR",
                engine_type=EngineType.AGENTIC,
                latency_ms=latency_ms,
            )

    def _validate_agentic_request(self, request: MatchRequest) -> Optional[str]:
        """验证许愿模式请求"""
        # 基础验证
        base_error = self.validate_request(request)
        if base_error:
            return base_error

        # 许愿模式必须有愿望描述
        if not request.wish_description:
            return "wish_description is required for Agentic engine"

        if len(request.wish_description) < 10:
            return "wish_description must be at least 10 characters"

        if len(request.wish_description) > 1000:
            return "wish_description must be less than 1000 characters"

        return None

    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户画像"""
        # 从规则引擎获取用户信息
        user = self._rule_engine.get_registered_users().get(user_id, {})
        return user

    def _wish_to_query_conditions(
        self,
        wish_description: str,
        wish_analysis: WishAnalysis
    ) -> Dict[str, Any]:
        """
        将愿望转化为查询条件

        Args:
            wish_description: 用户愿望描述
            wish_analysis: AI 分析结果

        Returns:
            查询条件字典
        """
        conditions = {}

        # 从硬性条件提取可量化的条件
        # 例如：年龄、地点等
        for condition in wish_analysis.hard_conditions:
            # 年龄条件
            if "岁" in condition or "年龄" in condition:
                # 尝试提取年龄范围
                import re
                age_match = re.search(r'(\d+)[-~到](\d+)', condition)
                if age_match:
                    conditions['age_min'] = int(age_match.group(1))
                    conditions['age_max'] = int(age_match.group(2))
                else:
                    single_age = re.search(r'(\d+)', condition)
                    if single_age:
                        age = int(single_age.group(1))
                        conditions['age_min'] = age - 3
                        conditions['age_max'] = age + 3

            # 地点条件
            if "在" in condition and ("市" in condition or "省" in condition or "区" in condition):
                location_match = re.search(r'在(.+市|.+省|.+区)', condition)
                if location_match:
                    conditions['location'] = location_match.group(1)

        return conditions

    def _generate_match_points(
        self,
        candidate: MatchCandidate,
        wish_analysis: WishAnalysis
    ) -> List[str]:
        """
        生成匹配点

        Args:
            candidate: 候选人
            wish_analysis: 愿望分析

        Returns:
            匹配点列表
        """
        match_points = []

        # 检查兴趣匹配
        candidate_interests = set(candidate.interests)
        for preference in wish_analysis.soft_preferences:
            if preference in candidate_interests:
                match_points.append(f"都喜欢{preference}")

        # 检查硬性条件匹配
        # 年龄匹配
        if wish_analysis.risk_analysis.pool_size_estimate:
            if candidate.score > 0.7:
                match_points.append("整体匹配度高")

        # 地点匹配
        # 从规则引擎获取用户地点
        user_location = None  # 需要从用户画像获取

        return match_points if match_points else ["待进一步了解"]

    def get_metrics(self) -> EngineMetrics:
        """获取引擎指标"""
        return self.metrics

    def reset_metrics(self) -> None:
        """重置指标"""
        self.metrics = EngineMetrics(engine_type=EngineType.AGENTIC)
        logger.info("AgenticMatchEngine metrics reset")

    # ============ 会话管理 ============

    def create_session(
        self,
        user_id: str,
        wish_description: str
    ) -> WishModeSession:
        """
        创建许愿会话

        Args:
            user_id: 用户 ID
            wish_description: 愿望描述

        Returns:
            WishModeSession: 会话对象
        """
        session_id = f"wish-{user_id}-{datetime.now().timestamp()}"
        session = WishModeSession(
            session_id=session_id,
            user_id=user_id,
            started_at=datetime.now(),
            original_wish=wish_description,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[WishModeSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        """关闭会话"""
        if session_id in self._sessions:
            self._sessions[session_id].is_completed = True


# 全局引擎实例
_agentic_engine_instance: Optional[AgenticMatchEngine] = None


def get_agentic_engine() -> AgenticMatchEngine:
    """
    获取 Agentic 引擎实例

    Returns:
        AgenticMatchEngine: 全局 Agentic 引擎实例
    """
    global _agentic_engine_instance
    if _agentic_engine_instance is None:
        _agentic_engine_instance = AgenticMatchEngine()
    return _agentic_engine_instance


def get_advisor() -> WishModeAdvisor:
    """
    获取 AI 顾问实例

    Returns:
        WishModeAdvisor: AI 顾问实例
    """
    return get_agentic_engine()._advisor