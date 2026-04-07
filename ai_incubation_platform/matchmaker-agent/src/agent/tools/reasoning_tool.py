"""
解释生成工具

用于生成匹配结果的详细解释说明。
"""
from typing import Dict, Any, Optional, List
from utils.logger import logger
from matching.matcher import matchmaker


class ReasoningTool:
    """
    解释生成工具

    功能：
    - 生成单个匹配结果的解释
    - 批量生成匹配列表的解释
    - 支持自定义解释维度
    """

    name = "reasoning_generate"
    description = "生成匹配结果的可解释说明"
    tags = ["reasoning", "explanation", "match"]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "当前用户 ID"
                },
                "target_user_id": {
                    "type": "string",
                    "description": "匹配对象用户 ID"
                },
                "score": {
                    "type": "number",
                    "description": "匹配度分数",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "breakdown": {
                    "type": "object",
                    "description": "各维度分数",
                    "properties": {
                        "interests": {"type": "number"},
                        "values": {"type": "number"},
                        "age": {"type": "number"},
                        "location": {"type": "number"}
                    }
                },
                "include_suggestions": {
                    "type": "boolean",
                    "description": "是否包含破冰建议",
                    "default": False
                }
            },
            "required": ["user_id", "target_user_id"]
        }

    @staticmethod
    def handle(
        user_id: str,
        target_user_id: str,
        score: Optional[float] = None,
        breakdown: Optional[dict] = None,
        include_suggestions: bool = False
    ) -> dict:
        """
        处理解释生成请求

        Args:
            user_id: 当前用户 ID
            target_user_id: 匹配对象 ID
            score: 匹配度分数（可选，不传则自动计算）
            breakdown: 各维度分数（可选）
            include_suggestions: 是否包含破冰建议

        Returns:
            匹配解释说明
        """
        logger.info(f"ReasoningTool: Generating reasoning for {user_id} -> {target_user_id}")

        try:
            # 获取用户信息
            user_data = matchmaker._users.get(user_id)
            target_data = matchmaker._users.get(target_user_id)

            if not user_data or not target_data:
                return {"error": "User data not found in matching system"}

            # 如果未提供分数，自动计算
            if score is None or breakdown is None:
                score, breakdown = matchmaker._calculate_compatibility(user_data, target_data)

            # 生成匹配解释
            reasoning = matchmaker.generate_match_reasoning(
                user_data,
                target_data,
                score,
                breakdown
            )

            # 计算共同兴趣
            user_interests = set(user_data.get('interests', []))
            target_interests = set(target_data.get('interests', []))
            common_interests = list(user_interests & target_interests)

            result = {
                "reasoning": reasoning,
                "compatibility_score": score,
                "score_breakdown": breakdown,
                "common_interests": common_interests,
                "match_dimensions": {
                    "interests": breakdown.get('interests', 0),
                    "values": breakdown.get('values', 0),
                    "age": breakdown.get('age', 0),
                    "location": breakdown.get('location', 0)
                }
            }

            # 可选：添加破冰建议
            if include_suggestions:
                from integration.llm_client import llm_client
                import asyncio

                try:
                    # 注意：这里可能在同步上下文中调用异步函数
                    icebreakers = llm_client._get_default_icebreakers(common_interests)
                    result["icebreaker_suggestions"] = icebreakers[:3]
                except Exception as e:
                    logger.warning(f"ReasoningTool: Failed to generate icebreakers: {e}")
                    result["icebreaker_suggestions"] = llm_client._get_default_icebreakers(common_interests)[:3]

            logger.info(f"ReasoningTool: Reasoning generated successfully")

            return result

        except Exception as e:
            logger.error(f"ReasoningTool: Failed to generate reasoning: {e}")
            return {"error": str(e)}

    @staticmethod
    def generate_batch_reasoning(user_id: str, matches: List[dict]) -> List[dict]:
        """
        批量生成匹配解释

        Args:
            user_id: 当前用户 ID
            matches: 匹配结果列表（包含 user_id, score, breakdown）

        Returns:
            带解释的匹配结果列表
        """
        results = []
        for match in matches:
            reasoning_result = ReasoningTool.handle(
                user_id=user_id,
                target_user_id=match["user_id"],
                score=match.get("score"),
                breakdown=match.get("breakdown")
            )
            if "error" not in reasoning_result:
                match["reasoning"] = reasoning_result.get("reasoning", "")
                match["common_interests"] = reasoning_result.get("common_interests", [])
            results.append(match)
        return results
