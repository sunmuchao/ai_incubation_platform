"""
解释生成工具

用于生成匹配结果的详细解释说明。
架构说明：新架构使用 HerAdvisorService (AI) 生成解释，详见 HER_ADVISOR_ARCHITECTURE.md
"""
from typing import Dict, Any, Optional, List
from utils.logger import logger


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
            score: 匹配度分数（可选，不传则由 AI 判断）
            breakdown: 各维度分数（可选）
            include_suggestions: 是否包含破冰建议

        Returns:
            匹配解释说明
        """
        logger.info(f"ReasoningTool: Generating reasoning for {user_id} -> {target_user_id}")

        try:
            # 注：matchmaker 已废弃，使用数据库 + HerAdvisorService (AI)
            from db.repositories import UserRepository
            from db.database import get_db
            from services.her_advisor_service import get_her_advisor_service
            from services.user_profile_service import get_user_profile_service

            db = next(get_db())
            user_repo = UserRepository(db)

            # 从数据库获取用户
            db_user = user_repo.get_by_id(user_id)
            db_target = user_repo.get_by_id(target_user_id)

            if not db_user or not db_target:
                return {"error": "User data not found in database"}

            # 使用 UserProfileService 获取画像
            profile_service = get_user_profile_service()
            her_advisor = get_her_advisor_service()

            # 获取用户画像（异步调用）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            self_a, desire_a = loop.run_until_complete(
                profile_service.get_or_create_profile(user_id)
            )
            self_b, desire_b = loop.run_until_complete(
                profile_service.get_or_create_profile(target_user_id)
            )

            # 使用 AI 判断匹配度（如果未提供分数）
            if score is None:
                advice = loop.run_until_complete(
                    her_advisor.generate_match_advice(
                        user_id, (self_a, desire_a),
                        target_user_id, (self_b, desire_b)
                    )
                )
                score = advice.compatibility_score
                breakdown = {
                    "interests": advice.interest_alignment,
                    "values": advice.value_alignment,
                    "lifestyle": advice.lifestyle_fit,
                }

            # 从画像获取共同兴趣
            user_interests = set(self_a.interests or [])
            target_interests = set(self_b.interests or [])
            common_interests = list(user_interests & target_interests)

            result = {
                "reasoning": f"AI 分析：{score:.1%} 匹配度。基于兴趣、价值观、生活方式的综合评估。",
                "compatibility_score": score,
                "score_breakdown": breakdown or {},
                "common_interests": common_interests,
                "match_dimensions": breakdown or {}
            }

            # 可选：添加破冰建议
            if include_suggestions:
                from integration.llm_client import llm_client
                try:
                    icebreakers = llm_client._get_default_icebreakers(common_interests)
                    result["icebreaker_suggestions"] = icebreakers[:3]
                except Exception as e:
                    logger.warning(f"ReasoningTool: Failed to generate icebreakers: {e}")
                    result["icebreaker_suggestions"] = []

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
