"""
UIBuilder - UI 构建器

职责：
- 构建 Generative UI
- 构建建议操作
- 构建追问响应

从 ConversationMatchService 提取的方法：
- _build_generative_ui
- _build_suggested_actions
- _build_quality_check_followup_response
"""
from typing import Dict, Any, List, Optional

from utils.logger import logger


class UIBuilder:
    """
    UI 构建器

    负责构建前端展示所需的 UI 结构和建议操作
    """

    def build_generative_ui(
        self,
        matches: List[Any],
        intent: Any,
    ) -> Dict[str, Any]:
        """构建 Generative UI"""
        if not matches:
            return {
                "component_type": "EmptyState",
                "props": {
                    "message": "没有找到匹配对象",
                    "suggestion": "试试放宽条件",
                }
            }

        # 构建匹配卡片列表
        match_cards = []
        for match in matches:
            card = {
                "id": match.get("candidate_id"),
                "name": match.get("candidate_name"),
                "score": match.get("compatibility_score"),
                "reasoning": match.get("match_reasoning"),
                "her_advice": match.get("her_advice").to_dict() if hasattr(match.get("her_advice"), 'to_dict') else None,
                "risk_warnings": match.get("risk_warnings"),
                "vector_match_highlights": match.get("vector_match_highlights", {}),
                "candidate_profile": match.get("candidate_profile", {}),
            }
            match_cards.append(card)

        return {
            "component_type": "MatchCardList",
            "props": {
                "matches": match_cards,
                "loading": False,
                "show_her_advice": True,
            }
        }

    def build_suggested_actions(
        self,
        matches: List[Any],
        bias_analysis: Any,
    ) -> List[Dict[str, str]]:
        """构建建议操作"""
        actions = []

        if matches:
            actions.append({
                "label": "查看第一个",
                "action": f"view_{matches[0].get('candidate_id')}",
            })
            actions.append({
                "label": "查看更多",
                "action": "show_more_matches",
            })

        if bias_analysis and hasattr(bias_analysis, 'has_bias') and bias_analysis.has_bias:
            actions.append({
                "label": "听听 Her 的建议",
                "action": "show_her_analysis",
            })

        actions.append({
            "label": "调整条件",
            "action": "adjust_conditions",
        })

        return actions

    def build_quality_check_followup_response(
        self,
        intent: Any,
        quality_check: Any,
        original_message: str,
    ) -> Dict[str, Any]:
        """
        构建查询质量校验未通过时的追问响应

        【Agent Native 改进】
        追问不再用编号列表，而是返回缺失信息供 Agent 自然表达。
        Agent 应根据这些信息，用对话风格追问用户。

        返回数据而非固定文案，让 Agent 自己生成个性化追问。
        """
        # 构建缺失信息摘要（供 Agent 解读）
        missing_info_summary = {
            "missing_basic_info": quality_check.missing_info,
            "missing_preferences": quality_check.missing_preferences if hasattr(quality_check, 'missing_preferences') else [],
            "clarity_issues": quality_check.clarity_issues,
        }

        # 构建建议操作（引导用户回答）
        suggested_actions = []
        if quality_check.missing_info:
            for info in quality_check.missing_info[:3]:
                suggested_actions.append({
                    "label": f"补充{info}",
                    "action": f"provide_{info}",
                })
        suggested_actions.append({
            "label": "跳过，直接推荐",
            "action": "skip_quality_check",
        })

        # 构建 Generative UI（追问卡片）
        # 返回缺失信息，不生成固定文案
        generative_ui = {
            "component_type": "QualityCheckFollowUp",
            "props": {
                "missing_info_summary": missing_info_summary,
                "hint": "Agent 应根据缺失信息，用自然对话风格追问用户。禁止用编号列表（如'1. xxx 2. xxx'），应该像真人聊天一样提问。",
                "example_correct_style": "你多大呀？我看你年龄设得挺宽的，帮你缩小一下？",
                "example_wrong_style": "1. 你希望对方什么年龄范围？",
            }
        }

        logger.info(f"[UIBuilder] 构建追问响应: 缺失信息 {len(quality_check.missing_info)} 项")

        # 不生成固定文案，让 Agent 自己生成
        return {
            "ai_message": "",  # Agent 应自己生成追问
            "intent_type": "quality_check_followup",
            "suggested_actions": suggested_actions,
            "generative_ui": generative_ui,
            "missing_info_summary": missing_info_summary,  # 供 Agent 使用
        }

    def build_preference_update_response(
        self,
        preference_mentioned: str,
    ) -> Dict[str, Any]:
        """构建偏好更新响应"""
        return {
            "ai_message": f"好的，我会记住你喜欢{preference_mentioned}的人。下次给你推荐时会更精准！",
            "intent_type": "preference_update",
            "suggested_actions": [
                {"label": "现在找人", "action": "开始匹配"},
            ],
            "generative_ui": {
                "component_type": "SimpleResponse",
                "props": {"message": f"好的，我会记住你喜欢{preference_mentioned}的人。"},
            },
        }

    def build_general_conversation_response(self) -> Dict[str, Any]:
        """构建一般对话响应"""
        return {
            "ai_message": "我在这里随时帮你找人、分析关系、或者聊聊你的想法。有什么需要吗？",
            "intent_type": "conversation",
            "suggested_actions": [
                {"label": "帮我找人", "action": "开始匹配"},
                {"label": "调整偏好", "action": "更新偏好"},
            ],
            "generative_ui": {
                "component_type": "SimpleResponse",
                "props": {"message": "我在这里随时帮你找人、分析关系、或者聊聊你的想法。"},
            },
        }


# 全局实例
_ui_builder: Optional[UIBuilder] = None


def get_ui_builder() -> UIBuilder:
    """获取 UI 构建器单例"""
    global _ui_builder
    if _ui_builder is None:
        _ui_builder = UIBuilder()
        logger.info("UIBuilder initialized")
    return _ui_builder