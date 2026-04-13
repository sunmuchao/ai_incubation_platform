"""
AdviceGenerator - 建议生成器

职责：
- 为每个匹配生成 Her 建议
- 生成 AI 响应消息

从 ConversationMatchService 提取的方法：
- _generate_match_advices
- _generate_response_message
"""
from typing import Dict, Any, List, Optional
import asyncio

from utils.logger import logger
from services.user_profile_service import get_user_profile_service
from services.her_advisor_service import (
    HerAdvisorService,
    SelfProfile,
    DesireProfile,
    MatchAdvice,
)


class AdviceGenerator:
    """
    建议生成器

    为匹配结果生成专业建议和响应消息
    """

    def __init__(
        self,
        profile_service=None,
        her_advisor=None,
    ):
        self._profile_service = profile_service or get_user_profile_service()
        self._her_advisor = her_advisor or HerAdvisorService()

    async def generate_match_advices(
        self,
        user_id: str,
        self_profile: SelfProfile,
        desire_profile: DesireProfile,
        matches: List[Dict[str, Any]],
    ) -> List[Any]:
        """
        为每个匹配生成 Her 建议

        如果 matches 中已有 her_advice，直接使用；
        否则调用 HerAdvisorService 生成。
        """
        logger.info(f"[AdviceGenerator] 生成匹配建议")

        if not matches:
            return []

        # 批量获取候选人画像（优化 N+1 查询）
        candidate_ids = [match.get("user_id") for match in matches]
        candidate_profiles = await self._profile_service.get_profiles_batch(candidate_ids)

        # 并行生成建议
        async def process_single_match(match: Dict[str, Any]):
            candidate_id = match.get("user_id")
            candidate_self, candidate_desire = candidate_profiles.get(
                candidate_id, (SelfProfile(), DesireProfile())
            )

            # 如果已有 AI 判断结果，直接使用
            existing_advice = match.get("her_advice")
            if existing_advice:
                advice = existing_advice
            else:
                # 否则重新生成
                advice = await self._her_advisor.generate_match_advice(
                    user_id,
                    (self_profile, desire_profile),
                    candidate_id,
                    (candidate_self, candidate_desire),
                    match.get("score", 0.5),
                )

            return {
                "candidate_id": candidate_id,
                "candidate_name": candidate_self.name or candidate_self.gender or "TA",
                "candidate_profile": candidate_self.to_dict(),
                "compatibility_score": match.get("score", 0.5),
                "score_breakdown": {},
                "her_advice": advice,
                "match_reasoning": advice.advice_content if advice else "初步匹配",
                "risk_warnings": advice.potential_issues if advice else [],
            }

        # 并行处理所有匹配
        results = await asyncio.gather(
            *[process_single_match(match) for match in matches],
            return_exceptions=True
        )

        # 过滤异常结果
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"[AdviceGenerator] 处理匹配 {matches[i].get('user_id')} 失败: {result}")
            else:
                valid_results.append(result)

        return valid_results

    async def generate_response_message(
        self,
        intent: Any,
        matches: List[Any],
        bias_analysis: Any,
        proactive_suggestion: Any,
    ) -> str:
        """
        生成 AI 响应消息

        整合匹配结果、认知偏差、主动建议
        """
        # 基础响应
        if not matches:
            return "目前没有找到符合你条件的匹配对象。要不调整一下条件试试？"

        # 有匹配结果
        match_count = len(matches)
        avg_score = sum(m.get("compatibility_score", 0.5) for m in matches) / match_count

        response_parts = [f"为你找到了 {match_count} 个匹配对象，平均匹配度 {avg_score:.0%}。"]

        # 如果有认知偏差，添加提醒
        if bias_analysis and hasattr(bias_analysis, 'has_bias') and bias_analysis.has_bias:
            response_parts.append(
                f"\n\nHer 发现：{bias_analysis.bias_description}\n"
                f"{bias_analysis.adjustment_suggestion}"
            )

        # 如果有高置信度匹配
        if matches[0].get("compatibility_score", 0) > 0.8:
            response_parts.append("\n\n第一个匹配对象很适合你，建议优先了解！")

        return "".join(response_parts)


# 全局实例
_advice_generator: Optional[AdviceGenerator] = None


def get_advice_generator() -> AdviceGenerator:
    """获取建议生成器单例"""
    global _advice_generator
    if _advice_generator is None:
        _advice_generator = AdviceGenerator()
        logger.info("AdviceGenerator initialized")
    return _advice_generator