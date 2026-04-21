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
import json

from utils.logger import logger
from services.user_profile_service import get_user_profile_service
from services.her_advisor_service import HerAdvisorService, MatchAdvice
from services.profile_dataclasses import DesireProfile, SelfProfile


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
            candidate_profile = match.get("candidate_profile") or candidate_self.to_dict()
            vector_match_highlights = match.get("vector_match_highlights") or candidate_profile.get("vector_match_highlights", {})
            candidate_name = (
                candidate_profile.get("name")
                or candidate_profile.get("basic", {}).get("name")
                or candidate_self.gender
                or "TA"
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
                "candidate_name": candidate_name,
                "candidate_profile": candidate_profile,
                "compatibility_score": match.get("score", 0.5),
                "score_breakdown": {},
                "her_advice": advice,
                "match_reasoning": advice.advice_content if advice else "初步匹配",
                "risk_warnings": advice.potential_issues if advice else [],
                "vector_match_highlights": vector_match_highlights,
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

        【Agent Native 改进】
        此方法不再生成模板化响应，而是返回数据摘要。
        Agent（DeerFlow）应根据这些数据自主生成个性化响应。

        返回数据摘要，让 Agent 自己解读并生成自然对话。
        """
        # 没有匹配结果
        if not matches:
            # 返回 JSON 格式的数据摘要，让 Agent 自己生成文案
            return json.dumps({
                "match_count": 0,
                "hint": "Agent 应告诉用户没有找到匹配对象，建议调整条件。",
                "example_style": "目前没有找到符合你条件的匹配对象。要不调整一下条件试试？",
            }, ensure_ascii=False)

        # 有匹配结果，返回数据摘要
        match_count = len(matches)

        # 提取置信度信息
        confidence_levels = [m.get("confidence_level", "medium") for m in matches]
        high_confidence_count = sum(1 for c in confidence_levels if c in ["very_high", "high"])

        # 提取匹配分数
        scores = [m.get("compatibility_score", 0.5) for m in matches]
        avg_score = sum(scores) / match_count if match_count > 0 else 0.5

        # 提取置信度最高的匹配
        best_match = matches[0] if matches else None

        # 构建数据摘要
        summary_data = {
            "match_count": match_count,
            "avg_score": round(avg_score, 2),
            "high_confidence_count": high_confidence_count,
            "best_match": {
                "name": best_match.get("candidate_name", "TA") if best_match else None,
                "confidence_level": best_match.get("confidence_level", "medium") if best_match else None,
                "confidence_icon": best_match.get("confidence_icon", "✓") if best_match else None,
                "score": best_match.get("compatibility_score", 0.5) if best_match else None,
            } if best_match else None,
            "bias_analysis": {
                "has_bias": bias_analysis.has_bias if bias_analysis and hasattr(bias_analysis, 'has_bias') else False,
                "bias_description": bias_analysis.bias_description if bias_analysis and hasattr(bias_analysis, 'bias_description') else None,
            } if bias_analysis else None,
            "hint": "Agent 应根据数据自主生成个性化响应。要自然对话风格，禁止模板化。每个候选人介绍要因用户而异。"
            "排版：段落之间必须空一行；列举多位时用 Markdown 列表，每人一条单独成行（- **姓名**（年龄）- 要点）。",
            "key_points": [
                f"找到 {match_count} 个匹配对象",
                f"其中 {high_confidence_count} 个高置信度用户（可信度高）",
                f"平均匹配度 {avg_score:.0%}",
            ],
        }

        # 返回 JSON 格式的数据摘要
        return json.dumps(summary_data, ensure_ascii=False)


# 全局实例
_advice_generator: Optional[AdviceGenerator] = None


def get_advice_generator() -> AdviceGenerator:
    """获取建议生成器单例"""
    global _advice_generator
    if _advice_generator is None:
        _advice_generator = AdviceGenerator()
        logger.info("AdviceGenerator initialized")
    return _advice_generator