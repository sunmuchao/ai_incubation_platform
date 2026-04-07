"""
价值评估工作流

实现对单个商机的深度价值评估
"""
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class OpportunityEvaluationWorkflow:
    """
    商机价值评估工作流

    流程：
    1. 获取商机详情
    2. 分析相关趋势
    3. 分析竞争格局
    4. 综合评估并生成建议
    """

    def __init__(self):
        self.workflow_id = f"evaluation_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    async def run(self, opp_id: str) -> Dict[str, Any]:
        """
        执行价值评估工作流

        Args:
            opp_id: 商机 ID

        Returns:
            评估报告
        """
        logger.info(f"Starting evaluation workflow: {self.workflow_id} for {opp_id}")

        # Step 1: 获取商机详情
        detail_result = await self._step_get_detail(opp_id)
        if not detail_result.get("success"):
            return {"success": False, "error": detail_result.get("error")}

        self.steps_executed = [("get_detail", detail_result)]

        # Step 2: 趋势分析
        trend_result = await self._step_analyze_trends(detail_result)
        self.steps_executed.append(("analyze_trends", trend_result))

        # Step 3: 竞争分析
        competition_result = await self._step_analyze_competition(detail_result)
        self.steps_executed.append(("analyze_competition", competition_result))

        # Step 4: 综合评估
        evaluation_result = await self._step_comprehensive_evaluate(
            detail_result, trend_result, competition_result
        )
        self.steps_executed.append(("comprehensive_evaluate", evaluation_result))

        return {
            "success": True,
            "workflow_id": self.workflow_id,
            "evaluation": evaluation_result,
            "timestamp": datetime.now().isoformat()
        }

    async def _step_get_detail(self, opp_id: str) -> Dict[str, Any]:
        """Step 1: 获取商机详情"""
        from tools import get_all_tools
        tools_map = {t["name"]: t for t in get_all_tools()}

        get_tool = tools_map.get("get_opportunity")
        if not get_tool:
            return {"success": False, "error": "Tool not available"}

        import inspect
        if inspect.iscoroutinefunction(get_tool["handler"]):
            result = await get_tool["handler"](opp_id=opp_id)
        else:
            result = get_tool["handler"](opp_id=opp_id)

        return result

    async def _step_analyze_trends(self, detail_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: 分析相关趋势"""
        opp = detail_result.get("opportunity", {})
        tags = opp.get("tags", [])[:3]  # 最多分析 3 个标签

        from tools import get_all_tools
        tools_map = {t["name"]: t for t in get_all_tools()}

        trend_tool = tools_map.get("analyze_trend")
        if not trend_tool:
            return {"trends": []}

        trend_results = []
        for tag in tags:
            import inspect
            if inspect.iscoroutinefunction(trend_tool["handler"]):
                result = await trend_tool["handler"](keyword=tag, days=30)
            else:
                result = trend_tool["handler"](keyword=tag, days=30)

            if result.get("success"):
                trend_results.append(result.get("trend", {}))

        return {"trends": trend_results}

    async def _step_analyze_competition(self, detail_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: 分析竞争格局"""
        opp = detail_result.get("opportunity", {})
        industry = opp.get("type", "general")

        from tools import get_all_tools
        tools_map = {t["name"]: t for t in get_all_tools()}

        competition_tool = tools_map.get("analyze_competition")
        if not competition_tool:
            return {"competition": {}}

        import inspect
        if inspect.iscoroutinefunction(competition_tool["handler"]):
            result = await competition_tool["handler"](industry=industry, days=60)
        else:
            result = competition_tool["handler"](industry=industry, days=60)

        return {"competition": result.get("analysis", {})}

    async def _step_comprehensive_evaluate(
        self,
        detail_result: Dict[str, Any],
        trend_result: Dict[str, Any],
        competition_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 4: 综合评估"""
        opp = detail_result.get("opportunity", {})
        trends = trend_result.get("trends", [])
        competition = competition_result.get("competition", {})

        # 计算综合评分
        base_confidence = opp.get("confidence_score", 0)
        avg_trend_score = sum(t.get("trend_score", 0) for t in trends) / len(trends) if trends else 0.5

        # 综合评分 = 基础置信度 * 0.5 + 趋势评分 * 0.3 + 竞争因素 * 0.2
        competition_factor = 0.5  # 默认中等竞争
        if competition:
            companies = competition.get("companies", [])
            if len(companies) > 10:
                competition_factor = 0.3  # 竞争激烈
            elif len(companies) > 5:
                competition_factor = 0.5
            else:
                competition_factor = 0.7  # 竞争较小

        comprehensive_score = (
            base_confidence * 0.5 +
            avg_trend_score * 0.3 +
            competition_factor * 0.2
        )

        # 生成 AI 建议
        recommendation = self._generate_recommendation(
            opp, comprehensive_score, trends, competition
        )

        return {
            "opportunity_id": opp.get("id"),
            "title": opp.get("title"),
            "base_confidence": base_confidence,
            "trend_score": avg_trend_score,
            "competition_factor": competition_factor,
            "comprehensive_score": comprehensive_score,
            "trends_analyzed": trends,
            "competition_landscape": competition,
            "recommendation": recommendation
        }

    def _generate_recommendation(
        self,
        opp: Dict,
        score: float,
        trends: List,
        competition: Dict
    ) -> Dict:
        """生成 AI 推荐建议"""
        value = opp.get("potential_value", 0)

        recommendation = {
            "action": "monitor",
            "priority": "medium",
            "confidence": "medium",
            "reasoning": []
        }

        if score >= 0.8 and value >= 5000000:
            recommendation["action"] = "pursue_immediately"
            recommendation["priority"] = "critical"
            recommendation["confidence"] = "high"
            recommendation["reasoning"].append("综合评分极高且价值巨大，建议立即推进")
        elif score >= 0.7:
            recommendation["action"] = "pursue"
            recommendation["priority"] = "high"
            recommendation["confidence"] = "high"
            recommendation["reasoning"].append("综合评分高，建议积极推进")
        elif score >= 0.5:
            recommendation["action"] = "monitor"
            recommendation["priority"] = "medium"
            recommendation["confidence"] = "medium"
            recommendation["reasoning"].append("评分中等，需要持续观察")
        else:
            recommendation["action"] = "skip"
            recommendation["priority"] = "low"
            recommendation["confidence"] = "low"
            recommendation["reasoning"].append("评分较低，暂不建议投入资源")

        return recommendation


# 全局工作流实例
opportunity_evaluation_workflow = OpportunityEvaluationWorkflow
