"""
匹配工作流

编排匹配流程：画像读取 -> 匹配计算 -> 解释生成 -> 结果留痕
"""
from typing import Dict, List, Optional, Any
from utils.logger import logger
from agent.tools.profile_tool import ProfileTool
from agent.tools.match_tool import MatchTool
from agent.tools.reasoning_tool import ReasoningTool
from agent.tools.logging_tool import LoggingTool


class MatchWorkflow:
    """
    匹配工作流

    执行步骤：
    1. 读取用户画像
    2. 执行匹配计算
    3. 为每个匹配生成解释
    4. 记录匹配历史
    """

    def __init__(self):
        self.tools = {
            "profile": ProfileTool,
            "match": MatchTool,
            "reasoning": ReasoningTool,
            "logging": LoggingTool
        }

    def execute(
        self,
        user_id: str,
        limit: int = 10,
        min_score: float = 0.0,
        include_reasoning: bool = True,
        include_history: bool = True
    ) -> dict:
        """
        执行匹配工作流

        Args:
            user_id: 用户 ID
            limit: 返回匹配数量上限
            min_score: 最低匹配度阈值
            include_reasoning: 是否生成匹配解释
            include_history: 是否记录匹配历史

        Returns:
            完整匹配结果
        """
        logger.info(f"MatchWorkflow: Starting for user {user_id}")
        result = {
            "user_id": user_id,
            "workflow": "match",
            "steps": {},
            "matches": [],
            "errors": []
        }

        # 步骤 1: 读取用户画像
        logger.info("MatchWorkflow: Step 1 - Reading profile")
        profile_result = ProfileTool.handle(user_id=user_id)
        result["steps"]["profile_read"] = profile_result

        if "error" in profile_result:
            result["errors"].append(f"Profile read failed: {profile_result['error']}")
            return result

        # 步骤 2: 执行匹配计算
        logger.info("MatchWorkflow: Step 2 - Computing matches")
        match_result = MatchTool.handle(
            user_id=user_id,
            limit=limit,
            min_score=min_score
        )
        result["steps"]["match_compute"] = match_result

        if "error" in match_result:
            result["errors"].append(f"Match compute failed: {match_result['error']}")
            return result

        # 步骤 3: 为每个匹配生成解释
        if include_reasoning:
            logger.info(f"MatchWorkflow: Step 3 - Generating reasoning for {len(match_result.get('matches', []))} matches")
            matches_with_reasoning = []
            for match in match_result.get("matches", []):
                reasoning_result = ReasoningTool.handle(
                    user_id=user_id,
                    target_user_id=match["user_id"],
                    score=match.get("score"),
                    breakdown=match.get("breakdown")
                )
                if "error" not in reasoning_result:
                    match["reasoning"] = reasoning_result.get("reasoning", "")
                    match["common_interests"] = reasoning_result.get("common_interests", [])
                    match["match_dimensions"] = reasoning_result.get("match_dimensions", {})
                matches_with_reasoning.append(match)
            result["matches"] = matches_with_reasoning
            result["steps"]["reasoning_generate"] = {"processed": len(matches_with_reasoning)}
        else:
            result["matches"] = match_result.get("matches", [])

        # 步骤 4: 记录匹配历史
        if include_history and result["matches"]:
            logger.info("MatchWorkflow: Step 4 - Recording history")
            logged_count = 0
            for match in result["matches"][:5]:  # 只记录前 5 个匹配的历史
                log_result = LoggingTool.handle(
                    user_id=user_id,
                    action="match",
                    target_user_id=match["user_id"],
                    score=match.get("score", 0)
                )
                if "error" not in log_result:
                    logged_count += 1
            result["steps"]["log_record"] = {"logged_count": logged_count}

        logger.info(f"MatchWorkflow: Completed, found {len(result['matches'])} matches")
        return result

    def get_workflow_schema(self) -> dict:
        """获取工作流 Schema"""
        return {
            "name": "match_workflow",
            "description": "匹配工作流：画像读取 -> 匹配计算 -> 解释生成 -> 结果留痕",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "用户 ID"},
                    "limit": {"type": "integer", "description": "返回数量上限", "default": 10},
                    "min_score": {"type": "number", "description": "最低匹配度阈值", "default": 0.0},
                    "include_reasoning": {"type": "boolean", "description": "是否生成解释", "default": True},
                    "include_history": {"type": "boolean", "description": "是否记录历史", "default": True}
                },
                "required": ["user_id"]
            },
            "steps": [
                {"name": "profile_read", "tool": "ProfileTool"},
                {"name": "match_compute", "tool": "MatchTool"},
                {"name": "reasoning_generate", "tool": "ReasoningTool", "optional": True},
                {"name": "log_record", "tool": "LoggingTool", "optional": True}
            ]
        }
