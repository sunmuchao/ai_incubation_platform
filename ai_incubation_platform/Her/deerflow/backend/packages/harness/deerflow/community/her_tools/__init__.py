"""
Her Tools - DeerFlow Tools for Her Project

提供 Her 项目的业务工具，注册到 DeerFlow Agent 运行时。

工具列表：
- her_find_matches: 查找匹配对象
- her_daily_recommend: 每日推荐
- her_analyze_compatibility: 兼容性分析
- her_analyze_relationship: 关系分析
- her_suggest_topics: 话题推荐
- her_get_icebreaker: 破冰建议
- her_plan_date: 约会策划

设计原则（AI Native）：
- 所有工具返回结构化数据（JSON），不是纯文本
- Agent 可以根据返回数据继续决策（多工具协作）
- 支持 Generative UI：前端根据数据动态渲染
"""

import logging
import json
from typing import Optional, Type, Dict, Any, List
from pydantic import BaseModel, Field

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


# ==================== Output Schemas ====================
# 结构化输出，Agent 可以继续处理

class MatchResult(BaseModel):
    """单个匹配结果"""
    user_id: str = Field(description="用户 ID")
    name: str = Field(description="姓名")
    age: int = Field(default=0, description="年龄")
    location: str = Field(default="", description="所在地")
    score: float = Field(default=0.0, description="匹配度 0-1")
    interests: List[str] = Field(default_factory=list, description="兴趣爱好")
    reason: str = Field(default="", description="推荐理由")


class ToolResult(BaseModel):
    """工具统一返回格式"""
    success: bool = Field(description="是否成功")
    data: Dict[str, Any] = Field(default_factory=dict, description="结构化数据")
    summary: str = Field(default="", description="一句话总结，用于 Agent 理解")
    error: str = Field(default="", description="错误信息")


# ==================== Input Schemas ====================

class HerFindMatchesInput(BaseModel):
    """查找匹配对象的输入参数"""
    user_id: str = Field(description="用户 ID")
    intent: str = Field(default="", description="用户意图描述，如'帮我找个爱旅行的'")
    limit: int = Field(default=5, description="返回数量")


class HerDailyRecommendInput(BaseModel):
    """每日推荐的输入参数"""
    user_id: str = Field(description="用户 ID")


class HerAnalyzeCompatibilityInput(BaseModel):
    """兼容性分析的输入参数"""
    user_id: str = Field(description="用户 ID")
    target_user_id: str = Field(description="目标用户 ID")


class HerAnalyzeRelationshipInput(BaseModel):
    """关系分析的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(description="匹配记录 ID")


class HerSuggestTopicsInput(BaseModel):
    """话题推荐的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(default="", description="匹配记录 ID（可选）")
    context: str = Field(default="", description="对话上下文（可选）")


class HerGetIcebreakerInput(BaseModel):
    """破冰建议的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(description="匹配记录 ID 或目标用户 ID")
    target_name: str = Field(default="TA", description="目标用户姓名")


class HerPlanDateInput(BaseModel):
    """约会策划的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(default="", description="匹配记录 ID（可选）")
    target_name: str = Field(default="TA", description="约会对象姓名")
    location: str = Field(default="", description="约会地点（可选）")
    preferences: str = Field(default="", description="偏好设置（可选）")


# ==================== Helper Functions ====================

def get_her_root() -> str:
    """获取 Her 项目根目录"""
    import os
    return os.environ.get("HER_PROJECT_ROOT", os.getcwd())


def ensure_her_in_path():
    """确保 Her 项目在 Python 路径中"""
    import sys
    her_root = get_her_root()
    if her_root not in sys.path:
        sys.path.insert(0, her_root)


# ==================== Tools ====================

class HerFindMatchesTool(BaseTool):
    """Her 匹配工具 - 查找合适的对象

    返回结构化匹配数据，Agent 可以：
    1. 展示匹配结果给用户
    2. 继续调用 her_analyze_compatibility 分析某个对象
    3. 继续调用 her_get_icebreaker 生成破冰建议
    """

    name: str = "her_find_matches"
    description: str = """
查找匹配对象。根据用户需求（如"找个爱旅行的"、"找个北京的"）进行智能匹配。

参数：
- user_id: 用户 ID
- intent: 用户意图描述（可选）
- limit: 返回数量（默认 5）

返回：结构化匹配数据 { matches: [...], total: N }
每个匹配包含：user_id, name, age, location, score, interests, reason
Agent 可以根据这些数据继续调用其他工具。
"""
    args_schema: Type[BaseModel] = HerFindMatchesInput

    def _run(self, user_id: str, intent: str = "", limit: int = 5) -> str:
        """同步执行（兼容旧代码）"""
        import asyncio
        result = asyncio.run(self._arun(user_id, intent, limit))
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(
        self,
        user_id: str,
        intent: str = "",
        limit: int = 5
    ) -> ToolResult:
        """异步执行 - 返回结构化数据"""
        logger.info(f"HerFindMatchesTool: user_id={user_id}, intent={intent}, limit={limit}")

        try:
            ensure_her_in_path()
            from src.agent.skills.matchmaking_skill import get_matchmaking_skill

            skill = get_matchmaking_skill()
            params = {
                "user_id": user_id,
                "intent": intent or "帮我找对象",
                "limit": limit,
                "min_score": 0.6
            }

            result = await skill.execute(**params)
            raw_matches = result.get("matches", [])

            # 转换为结构化数据
            matches: List[MatchResult] = []
            for match in raw_matches[:limit]:
                user = match.get("user", {})
                matches.append(MatchResult(
                    user_id=user.get("id", match.get("user_id", "")),
                    name=user.get("name", "TA"),
                    age=user.get("age", 0),
                    location=user.get("location", ""),
                    score=match.get("score", 0.0),
                    interests=user.get("interests", [])[:5],
                    reason=match.get("reason", "")
                ))

            if not matches:
                return ToolResult(
                    success=True,
                    data={"matches": [], "total": 0},
                    summary="暂时没有找到合适的匹配对象"
                )

            return ToolResult(
                success=True,
                data={
                    "matches": [m.model_dump() for m in matches],
                    "total": len(matches)
                },
                summary=f"找到 {len(matches)} 位匹配对象，最高匹配度 {matches[0].score*100:.0f}%"
            )

        except Exception as e:
            logger.error(f"HerFindMatchesTool failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                summary=f"匹配查找出错：{str(e)}"
            )


class HerDailyRecommendTool(BaseTool):
    """Her 每日推荐工具

    返回结构化推荐数据，Agent 可以继续处理。
    """

    name: str = "her_daily_recommend"
    description: str = """
获取每日精选推荐。每天为你推荐高质量匹配对象。

参数：
- user_id: 用户 ID

返回：结构化推荐数据 { recommendations: [...], total: N }
"""
    args_schema: Type[BaseModel] = HerDailyRecommendInput

    def _run(self, user_id: str) -> str:
        import asyncio
        result = asyncio.run(self._arun(user_id))
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str) -> ToolResult:
        """异步执行 - 返回结构化数据"""
        logger.info(f"HerDailyRecommendTool: user_id={user_id}")

        try:
            ensure_her_in_path()
            from src.agent.skills.matchmaking_skill import get_matchmaking_skill

            skill = get_matchmaking_skill()
            params = {
                "user_id": user_id,
                "service_type": "daily_recommend"
            }

            result = await skill.execute(**params)
            raw_matches = result.get("matches", [])

            recommendations: List[MatchResult] = []
            for match in raw_matches[:3]:
                recommendations.append(MatchResult(
                    user_id=match.get("user_id", ""),
                    name=match.get("name", "TA"),
                    age=match.get("age", 0),
                    location=match.get("location", ""),
                    score=match.get("score", 0.0),
                    interests=match.get("interests", [])[:5],
                    reason=match.get("daily_reason", "今日精选推荐")
                ))

            if not recommendations:
                return ToolResult(
                    success=True,
                    data={"recommendations": [], "total": 0},
                    summary="今日暂无推荐"
                )

            return ToolResult(
                success=True,
                data={
                    "recommendations": [r.model_dump() for r in recommendations],
                    "total": len(recommendations)
                },
                summary=f"今日精选 {len(recommendations)} 位优质对象"
            )

        except Exception as e:
            logger.error(f"HerDailyRecommendTool failed: {e}")
            return ToolResult(success=False, error=str(e), summary=f"每日推荐出错")


class HerAnalyzeCompatibilityTool(BaseTool):
    """Her 兼容性分析工具

    分析两个用户的匹配度，返回结构化报告。
    Agent 可以根据分析结果决定是否推荐约会策划。
    """

    name: str = "her_analyze_compatibility"
    description: str = """
分析两个用户之间的兼容性（匹配度）。

参数：
- user_id: 用户 ID
- target_user_id: 目标用户 ID

返回：结构化分析报告 { overall_score, dimensions, conflicts, strengths }
Agent 可以根据 overall_score 判断是否值得进一步发展。
"""
    args_schema: Type[BaseModel] = HerAnalyzeCompatibilityInput

    def _run(self, user_id: str, target_user_id: str) -> str:
        import asyncio
        result = asyncio.run(self._arun(user_id, target_user_id))
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, target_user_id: str) -> ToolResult:
        """异步执行 - 返回结构化数据"""
        logger.info(f"HerAnalyzeCompatibilityTool: user_id={user_id}, target={target_user_id}")

        try:
            ensure_her_in_path()
            # 使用正确的 Skill：conflict_compatibility_analyzer_skill
            from src.agent.skills.conflict_compatibility_analyzer_skill import get_conflict_compatibility_analyzer_skill

            skill = get_conflict_compatibility_analyzer_skill()
            result = await skill.execute(
                user_a_id=user_id,
                user_b_id=target_user_id,
                analysis_type="compatibility"
            )

            if not result.get("compatibility_score"):
                return ToolResult(success=False, error="分析失败", summary="分析失败")

            # 结构化维度分析
            dimensions = []
            # conflict_compatibility_analyzer 返回的数据结构不同，需要适配
            compatibility_score = result.get("compatibility_score", 0)
            compatibility_level = result.get("compatibility_level", "中等")

            # 构建维度数据
            user_a_style = result.get("user_a_style", {})
            user_b_style = result.get("user_b_style", {})
            if user_a_style and user_b_style:
                dimensions.append({
                    "name": "冲突风格",
                    "score": compatibility_score,
                    "description": f"风格兼容性：{compatibility_level}"
                })

            return ToolResult(
                success=True,
                data={
                    "overall_score": compatibility_score,
                    "dimensions": dimensions,
                    "conflicts": result.get("potential_conflicts", [])[:3],
                    "strengths": result.get("suggestions", [])[:3],
                    "recommendation": "值得尝试" if compatibility_score > 0.7 else "需要努力"
                },
                summary=f"匹配度 {compatibility_score*100:.0f}%"
            )

        except Exception as e:
            logger.error(f"HerAnalyzeCompatibilityTool failed: {e}")
            return ToolResult(success=False, error=str(e), summary="兼容性分析出错")


class HerAnalyzeRelationshipTool(BaseTool):
    """Her 关系分析工具

    分析用户与匹配对象的关系健康度。
    """

    name: str = "her_analyze_relationship"
    description: str = """
分析用户与匹配对象的关系状态和健康度。

参数：
- user_id: 用户 ID
- match_id: 匹配记录 ID

返回：结构化关系报告 { health_score, strengths, issues, suggestions }
"""
    args_schema: Type[BaseModel] = HerAnalyzeRelationshipInput

    def _run(self, user_id: str, match_id: str) -> str:
        import asyncio
        result = asyncio.run(self._arun(user_id, match_id))
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str) -> ToolResult:
        """异步执行"""
        logger.info(f"HerAnalyzeRelationshipTool: user_id={user_id}, match_id={match_id}")

        try:
            ensure_her_in_path()
            from src.agent.skills.relationship_coach_skill import get_relationship_coach_skill

            skill = get_relationship_coach_skill()
            params = {
                "user_id": user_id,
                "match_id": match_id,
                "action": "health_check"
            }

            result = await skill.execute(**params)
            report = result.get("relationship_report", {})

            return ToolResult(
                success=True,
                data={
                    "health_score": report.get("health_score", 0),
                    "strengths": report.get("strengths", [])[:5],
                    "issues": report.get("potential_issues", [])[:3],
                    "suggestions": report.get("suggestions", [])[:3]
                },
                summary=f"关系健康度 {report.get('health_score', 0)*100:.0f}%"
            )

        except Exception as e:
            logger.error(f"HerAnalyzeRelationshipTool failed: {e}")
            return ToolResult(success=False, error=str(e), summary="关系分析出错")


class HerSuggestTopicsTool(BaseTool):
    """Her 话题推荐工具

    推荐聊天话题，帮助打破沉默。
    """

    name: str = "her_suggest_topics"
    description: str = """
推荐聊天话题，帮助打破沉默。

参数：
- user_id: 用户 ID
- match_id: 匹配记录 ID（可选）
- context: 对话上下文（可选）

返回：结构化话题列表 { topics: [...], total: N }
"""
    args_schema: Type[BaseModel] = HerSuggestTopicsInput

    def _run(self, user_id: str, match_id: str = "", context: str = "") -> str:
        import asyncio
        result = asyncio.run(self._arun(user_id, match_id, context))
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(
        self,
        user_id: str,
        match_id: str = "",
        context: str = ""
    ) -> ToolResult:
        """异步执行"""
        logger.info(f"HerSuggestTopicsTool: user_id={user_id}, match_id={match_id}")

        try:
            ensure_her_in_path()
            from src.agent.skills.silence_breaker_skill import get_silence_breaker_skill

            skill = get_silence_breaker_skill()
            params = {
                "user_id": user_id,
                "partner_id": match_id,
                "action": "generate_topics"
            }

            result = await skill.execute(**params)
            raw_topics = result.get("topics", [])

            topics = []
            for t in raw_topics[:5]:
                topics.append({
                    "content": t.get("content") or t.get("topic", ""),
                    "category": t.get("category", "general"),
                    "difficulty": t.get("difficulty", "easy")
                })

            if not topics:
                return ToolResult(
                    success=True,
                    data={"topics": [], "total": 0},
                    summary="暂无话题推荐"
                )

            return ToolResult(
                success=True,
                data={"topics": topics, "total": len(topics)},
                summary=f"推荐 {len(topics)} 个聊天话题"
            )

        except Exception as e:
            logger.error(f"HerSuggestTopicsTool failed: {e}")
            return ToolResult(success=False, error=str(e), summary="话题推荐出错")


class HerGetIcebreakerTool(BaseTool):
    """Her 破冰建议工具

    生成破冰开场白，帮助用户开始对话。
    """

    name: str = "her_get_icebreaker"
    description: str = """
获取破冰开场建议，帮助开始第一次对话。

参数：
- user_id: 用户 ID
- match_id: 匹配记录 ID 或目标用户 ID
- target_name: 目标用户姓名（可选，用于个性化建议）

返回：结构化破冰建议 { icebreakers: [...], best_pick: "...", tips: [...] }
"""
    args_schema: Type[BaseModel] = HerGetIcebreakerInput

    def _run(self, user_id: str, match_id: str, target_name: str = "TA") -> str:
        import asyncio
        result = asyncio.run(self._arun(user_id, match_id, target_name))
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(
        self,
        user_id: str,
        match_id: str,
        target_name: str = "TA"
    ) -> ToolResult:
        """异步执行"""
        logger.info(f"HerGetIcebreakerTool: user_id={user_id}, match_id={match_id}")

        try:
            ensure_her_in_path()
            from src.agent.tools.icebreaker_tool import IcebreakerTool

            result = IcebreakerTool.handle(
                match_id=match_id,
                context="first_chat"
            )

            icebreakers = []
            for ib in result.get("icebreakers", [])[:5]:
                icebreakers.append({
                    "text": ib.get("text") or ib.get("content", ""),
                    "style": ib.get("style", "friendly"),
                    "confidence": ib.get("confidence", 0.8)
                })

            if not icebreakers:
                # 默认破冰建议
                default_icebreakers = [
                    {"text": f"Hi {target_name}，看了你的资料，觉得我们可能有共同兴趣~", "style": "friendly", "confidence": 0.9},
                    {"text": f"你好呀，{target_name}！最近有什么有趣的事吗？", "style": "casual", "confidence": 0.8},
                    {"text": f"{target_name}，你平时喜欢做什么呀？", "style": "direct", "confidence": 0.7}
                ]
                return ToolResult(
                    success=True,
                    data={
                        "icebreakers": default_icebreakers,
                        "best_pick": default_icebreakers[0]["text"],
                        "tips": ["保持真诚", "从共同兴趣开始"]
                    },
                    summary=f"为 {target_name} 生成了 3 个破冰建议"
                )

            return ToolResult(
                success=True,
                data={
                    "icebreakers": icebreakers,
                    "best_pick": icebreakers[0]["text"] if icebreakers else "",
                    "tips": result.get("tips", ["保持真诚", "自然开场"])
                },
                summary=f"为 {target_name} 生成了 {len(icebreakers)} 个破冰建议"
            )

        except Exception as e:
            logger.error(f"HerGetIcebreakerTool failed: {e}")
            return ToolResult(success=False, error=str(e), summary="破冰建议出错")


class HerPlanDateTool(BaseTool):
    """Her 约会策划工具

    策划约会方案，根据用户偏好和地点推荐活动。
    """

    name: str = "her_plan_date"
    description: str = """
策划约会方案。

参数：
- user_id: 用户 ID
- match_id: 匹配记录 ID（可选）
- target_name: 约会对象姓名（可选）
- location: 约会地点（可选）
- preferences: 偏好设置（可选，如"安静"、"户外"、"浪漫"）

返回：结构化约会方案 { plans: [...], best_pick: {...}, tips: [...] }
"""
    args_schema: Type[BaseModel] = HerPlanDateInput

    def _run(
        self,
        user_id: str,
        match_id: str = "",
        target_name: str = "TA",
        location: str = "",
        preferences: str = ""
    ) -> str:
        import asyncio
        result = asyncio.run(self._arun(user_id, match_id, target_name, location, preferences))
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(
        self,
        user_id: str,
        match_id: str = "",
        target_name: str = "TA",
        location: str = "",
        preferences: str = ""
    ) -> ToolResult:
        """异步执行"""
        logger.info(f"HerPlanDateTool: user_id={user_id}, location={location}")

        try:
            ensure_her_in_path()
            from src.agent.skills.date_planning_skill import get_date_planning_skill

            skill = get_date_planning_skill()
            params = {
                "user_id": user_id,
                "match_id": match_id,
                "action": "plan",
                "preferences": {
                    "location": location,
                    "date_type": "first_date",
                    "style": preferences
                }
            }

            result = await skill.execute(**params)
            raw_suggestions = result.get("suggestions", [])

            plans = []
            for s in raw_suggestions[:3]:
                plans.append({
                    "name": s.get("name", ""),
                    "description": s.get("description", ""),
                    "location": s.get("location", location),
                    "estimated_cost": s.get("estimated_cost", "适中"),
                    "duration": s.get("duration", "2-3小时"),
                    "tips": s.get("tips", [])
                })

            if not plans:
                # 默认约会方案
                default_plans = [
                    {
                        "name": "咖啡厅聊天",
                        "description": f"和 {target_name} 在安静的咖啡厅轻松聊天",
                        "location": location or "附近咖啡厅",
                        "estimated_cost": "50-100元",
                        "duration": "1-2小时",
                        "tips": ["选择安静的位置", "准备一些话题"]
                    },
                    {
                        "name": "公园散步",
                        "description": f"和 {target_name} 在公园散步，自然放松",
                        "location": location or "附近公园",
                        "estimated_cost": "免费",
                        "duration": "1-2小时",
                        "tips": ["注意天气", "带上水"]
                    }
                ]
                return ToolResult(
                    success=True,
                    data={
                        "plans": default_plans,
                        "best_pick": default_plans[0],
                        "tips": ["第一次约会保持轻松", "选择熟悉的地方"]
                    },
                    summary=f"为 {target_name} 生成了 2 个约会方案"
                )

            return ToolResult(
                success=True,
                data={
                    "plans": plans,
                    "best_pick": plans[0] if plans else {},
                    "tips": result.get("tips", ["保持轻松", "真诚交流"])
                },
                summary=f"为 {target_name} 生成了 {len(plans)} 个约会方案"
            )

        except Exception as e:
            logger.error(f"HerPlanDateTool failed: {e}")
            return ToolResult(success=False, error=str(e), summary="约会策划出错")


# ==================== Export ====================

__all__ = [
    "HerFindMatchesTool",
    "HerDailyRecommendTool",
    "HerAnalyzeCompatibilityTool",
    "HerAnalyzeRelationshipTool",
    "HerSuggestTopicsTool",
    "HerGetIcebreakerTool",
    "HerPlanDateTool",
    "ToolResult",
    "MatchResult",
]

# Tool instances for registration
her_find_matches_tool = HerFindMatchesTool()
her_daily_recommend_tool = HerDailyRecommendTool()
her_analyze_compatibility_tool = HerAnalyzeCompatibilityTool()
her_analyze_relationship_tool = HerAnalyzeRelationshipTool()
her_suggest_topics_tool = HerSuggestTopicsTool()
her_get_icebreaker_tool = HerGetIcebreakerTool()
her_plan_date_tool = HerPlanDateTool()