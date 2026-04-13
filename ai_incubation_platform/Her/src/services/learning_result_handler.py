"""
DeerFlow 学习结果回传服务

设计原则：
- 单向同步为主：Her → DeerFlow
- 学习结果回传为可选：DeerFlow → Her（仅当明确识别到新偏好时）
- 回传需要用户确认：不自动写入，只提示用户"是否更新"

回传场景：
- Agent 从对话中识别了用户的新偏好（如"我喜欢户外运动"）
- Agent 推断了用户的隐性特征（如"你可能是内向型性格"）
- Agent 发现了用户的价值观倾向（如"你重视家庭"）

回传流程：
1. DeerFlow Agent 在响应中附带 `learned_insights` 字段
2. 前端展示"是否将这些信息添加到你的画像？"
3. 用户点击确认 → 调用 Her API 更新画像
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

from utils.logger import logger
from services.user_profile_service import get_user_profile_service, get_profile_update_engine


@dataclass
class LearnedInsight:
    """
    DeerFlow 学习到的洞察

    Agent 在对话中识别的用户信息
    """
    dimension: str  # 画像维度（如 interests, personality, values）
    content: str  # 具体内容（如 "喜欢户外运动"）
    confidence: float = 0.8  # 置信度
    source: str = "conversation"  # 来源类型
    suggestion_type: str = "add"  # 建议类型：add（添加）/ update（更新）/ infer（推断）
    raw_evidence: str = ""  # 原始对话证据（用于用户确认）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "suggestion_type": self.suggestion_type,
            "raw_evidence": self.raw_evidence,
        }


@dataclass
class LearningResult:
    """
    DeerFlow 学习结果

    包含多个洞察和建议操作
    """
    insights: List[LearnedInsight] = field(default_factory=list)
    has_high_confidence_insight: bool = False  # 是否有高置信度洞察（>0.9）
    suggested_actions: List[str] = field(default_factory=list)  # 建议操作

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insights": [i.to_dict() for i in self.insights],
            "has_high_confidence_insight": self.has_high_confidence_insight,
            "suggested_actions": self.suggested_actions,
        }


class LearningResultHandler:
    """
    学习结果处理器

    处理 DeerFlow Agent 返回的学习结果

    使用方式：
        handler = LearningResultHandler()

        # 解析 DeerFlow 响应中的学习结果
        learning_result = handler.parse_learning_result(response_data)

        # 如果有高置信度洞察，提示用户确认
        if learning_result.has_high_confidence_insight:
            # 前端展示确认卡片
            ...

        # 用户确认后，应用学习结果
        handler.apply_learning_result(user_id, confirmed_insights)
    """

    # 可学习的维度映射
    LEARNABLE_DIMENSIONS = {
        "interests": {
            "db_field": "interests",
            "display_name": "兴趣爱好",
            "merge_strategy": "append",  # 添加到现有列表
        },
        "personality": {
            "db_field": "personality",
            "display_name": "性格特点",
            "merge_strategy": "update",  # 更新现有字段
        },
        "values": {
            "db_field": "values",
            "display_name": "价值观",
            "merge_strategy": "append",
        },
        "relationship_goal": {
            "db_field": "relationship_goal",
            "display_name": "关系目标",
            "merge_strategy": "update",
        },
        "deal_breakers": {
            "db_field": "deal_breakers",
            "display_name": "底线禁忌",
            "merge_strategy": "append",
        },
        "lifestyle": {
            "db_field": "lifestyle",
            "display_name": "生活方式",
            "merge_strategy": "update",
        },
    }

    def __init__(self):
        self._profile_service = get_user_profile_service()
        self._profile_update_engine = get_profile_update_engine()

    def parse_learning_result(self, response_data: Dict[str, Any]) -> LearningResult:
        """
        解析 DeerFlow 响应中的学习结果

        Args:
            response_data: DeerFlow 返回的响应数据

        Returns:
            LearningResult: 解析后的学习结果
        """
        insights = []

        # 从 tool_result 中提取学习结果
        tool_result = response_data.get("tool_result", {})
        data = tool_result.get("data", {})

        # 提取学习洞察
        learned_insights = data.get("learned_insights", [])
        for insight_data in learned_insights:
            try:
                insight = LearnedInsight(
                    dimension=insight_data.get("dimension", ""),
                    content=insight_data.get("content", ""),
                    confidence=insight_data.get("confidence", 0.8),
                    source=insight_data.get("source", "conversation"),
                    suggestion_type=insight_data.get("suggestion_type", "add"),
                    raw_evidence=insight_data.get("raw_evidence", ""),
                )
                insights.append(insight)
            except Exception as e:
                logger.warning(f"[LearningResult] 解析洞察失败: {e}")

        # 判断是否有高置信度洞察
        has_high_confidence = any(i.confidence >= 0.9 for i in insights)

        # 生成建议操作
        suggested_actions = self._generate_suggested_actions(insights)

        return LearningResult(
            insights=insights,
            has_high_confidence_insight=has_high_confidence,
            suggested_actions=suggested_actions,
        )

    def _generate_suggested_actions(self, insights: List[LearnedInsight]) -> List[str]:
        """生成建议操作"""
        actions = []

        if not insights:
            return actions

        # 高置信度洞察 → 建议直接应用
        high_confidence_insights = [i for i in insights if i.confidence >= 0.9]
        if high_confidence_insights:
            dimensions = [self.LEARNABLE_DIMENSIONS.get(i.dimension, {}).get("display_name", i.dimension)
                          for i in high_confidence_insights]
            actions.append(f"将这些信息添加到画像：{', '.join(dimensions)}")

        # 中置信度洞察 → 建议用户确认
        medium_confidence_insights = [i for i in insights if 0.7 <= i.confidence < 0.9]
        if medium_confidence_insights:
            actions.append("确认一下这些信息是否准确")

        return actions

    async def apply_learning_result(
        self,
        user_id: str,
        confirmed_insights: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        应用学习结果（用户确认后）

        Args:
            user_id: 用户 ID
            confirmed_insights: 用户确认的洞察列表

        Returns:
            更新结果
        """
        logger.info(f"[LearningResult] 用户 {user_id} 确认了 {len(confirmed_insights)} 个洞察")

        applied_count = 0
        failed_count = 0
        applied_dimensions = []

        for insight_data in confirmed_insights:
            dimension = insight_data.get("dimension")
            content = insight_data.get("content")

            if not dimension or not content:
                continue

            # 检查维度是否可学习
            dimension_config = self.LEARNABLE_DIMENSIONS.get(dimension)
            if not dimension_config:
                logger.warning(f"[LearningResult] 不可学习的维度: {dimension}")
                failed_count += 1
                continue

            try:
                # 应用到画像
                await self._apply_insight(user_id, dimension, content, dimension_config)
                applied_count += 1
                applied_dimensions.append(dimension_config["display_name"])
            except Exception as e:
                logger.error(f"[LearningResult] 应用洞察失败: {e}")
                failed_count += 1

        return {
            "success": True,
            "applied_count": applied_count,
            "failed_count": failed_count,
            "applied_dimensions": applied_dimensions,
            "message": f"已更新 {applied_count} 个画像维度",
        }

    async def _apply_insight(
        self,
        user_id: str,
        dimension: str,
        content: str,
        dimension_config: Dict[str, Any],
    ) -> None:
        """
        应用单个洞察到画像

        Args:
            user_id: 用户 ID
            dimension: 维度
            content: 内容
            dimension_config: 维度配置
        """
        db_field = dimension_config["db_field"]
        merge_strategy = dimension_config["merge_strategy"]

        # 获取当前画像
        self_profile, desire_profile = await self._profile_service.get_or_create_profile(user_id)

        # 根据 merge_strategy 应用
        if merge_strategy == "append":
            # 添加到列表（如 interests）
            current_value = getattr(self_profile, db_field, [])
            if isinstance(current_value, str):
                current_value = json.loads(current_value) if current_value else []
            if content not in current_value:
                current_value.append(content)
            new_value = current_value
        elif merge_strategy == "update":
            # 更新字段（如 personality）
            new_value = content
        else:
            new_value = content

        # 调用 ProfileUpdateEngine 更新
        await self._profile_update_engine.process_conversation_analysis(
            user_id,
            content,
            {
                "stated_preference": content,
                "dimension": dimension,
                "source": "deerflow_learning",
                "confidence": 0.9,
            }
        )

        logger.info(f"[LearningResult] 已更新用户 {user_id} 的 {dimension}: {content}")

    def build_learning_confirmation_ui(
        self,
        learning_result: LearningResult,
    ) -> Dict[str, Any]:
        """
        构建学习确认 UI

        前端根据这个数据渲染确认卡片

        Args:
            learning_result: 学习结果

        Returns:
            Generative UI 数据
        """
        if not learning_result.insights:
            return {}

        # 构建确认卡片
        return {
            "component_type": "LearningConfirmationCard",
            "props": {
                "insights": [i.to_dict() for i in learning_result.insights],
                "has_high_confidence": learning_result.has_high_confidence_insight,
                "suggested_actions": learning_result.suggested_actions,
                "message": "AI 发现了一些关于你的信息，是否添加到画像？",
            },
        }


# ==================== 全局实例 ====================

_learning_result_handler: Optional[LearningResultHandler] = None


def get_learning_result_handler() -> LearningResultHandler:
    """获取学习结果处理器单例"""
    global _learning_result_handler
    if _learning_result_handler is None:
        _learning_result_handler = LearningResultHandler()
        logger.info("LearningResultHandler initialized")
    return _learning_result_handler


__all__ = [
    "LearningResultHandler",
    "LearnedInsight",
    "LearningResult",
    "get_learning_result_handler",
]