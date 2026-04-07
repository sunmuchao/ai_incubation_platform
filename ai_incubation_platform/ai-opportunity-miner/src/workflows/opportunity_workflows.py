"""
商机发现工作流

实现 AI 自主商机发现的多步工作流编排
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class OpportunityDiscoveryWorkflow:
    """
    商机发现工作流

    流程：
    1. 采集多源数据（新闻、报告）
    2. AI 分析提取商机信号
    3. 评估置信度和潜在价值
    4. 优先级排序
    5. 生成汇总报告
    """

    def __init__(self):
        self.steps_executed = []
        self.workflow_id = f"discovery_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    async def run(
        self,
        keywords: Optional[List[str]] = None,
        industry: Optional[str] = None,
        days: int = 30,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        执行商机发现工作流

        Args:
            keywords: 关键词列表
            industry: 行业名称
            days: 分析天数
            min_confidence: 最低置信度阈值

        Returns:
            工作流执行结果
        """
        logger.info(f"Starting workflow: {self.workflow_id}")

        # Step 1: 数据采集
        step1_result = await self._step_collect_data(keywords, industry, days)
        self.steps_executed.append(("collect_data", step1_result))

        # Step 2: 商机发现
        step2_result = await self._step_discover_opportunities(keywords, industry, days)
        self.steps_executed.append(("discover_opportunities", step2_result))

        # Step 3: 价值评估
        step3_result = await self._step_evaluate_opportunities(step2_result, min_confidence)
        self.steps_executed.append(("evaluate_opportunities", step3_result))

        # Step 4: 优先级排序
        step4_result = await self._step_prioritize(step3_result)
        self.steps_executed.append(("prioritize", step4_result))

        # Step 5: 生成报告
        step5_result = await self._step_generate_report(step4_result)
        self.steps_executed.append(("generate_report", step5_result))

        return {
            "workflow_id": self.workflow_id,
            "workflow_type": "opportunity_discovery",
            "status": "completed",
            "result": step5_result,
            "steps_executed": len(self.steps_executed),
            "timestamp": datetime.now().isoformat()
        }

    async def _step_collect_data(
        self,
        keywords: Optional[List[str]],
        industry: Optional[str],
        days: int
    ) -> Dict[str, Any]:
        """Step 1: 采集多源数据"""
        logger.info("Step 1: Collecting data from multiple sources")

        from tools import get_all_tools
        tools_map = {t["name"]: t for t in get_all_tools()}

        fetch_keywords = keywords or [industry] if industry else ["人工智能", "数字经济"]

        # 获取新闻
        news_tool = tools_map.get("fetch_news")
        news_result = {"count": 0, "articles": []}
        if news_tool:
            import inspect
            if inspect.iscoroutinefunction(news_tool["handler"]):
                news_result = await news_tool["handler"](keywords=fetch_keywords, days=days)
            else:
                news_result = news_tool["handler"](keywords=fetch_keywords, days=days)

        # 获取报告
        reports_tool = tools_map.get("fetch_reports")
        reports_result = {"count": 0, "reports": []}
        if reports_tool:
            import inspect
            if inspect.iscoroutinefunction(reports_tool["handler"]):
                reports_result = await reports_tool["handler"](keywords=fetch_keywords)
            else:
                reports_result = reports_tool["handler"](keywords=fetch_keywords)

        return {
            "news_count": news_result.get("count", 0),
            "reports_count": reports_result.get("count", 0),
            "data_sources": ["news", "reports"]
        }

    async def _step_discover_opportunities(
        self,
        keywords: Optional[List[str]],
        industry: Optional[str],
        days: int
    ) -> Dict[str, Any]:
        """Step 2: 发现商机"""
        logger.info("Step 2: Discovering opportunities")

        from tools import get_all_tools
        tools_map = {t["name"]: t for t in get_all_tools()}

        discover_tool = tools_map.get("discover_opportunities")
        if not discover_tool:
            return {"opportunities": [], "count": 0}

        kwargs = {"days": days}
        if industry:
            kwargs["industry"] = industry
        elif keywords:
            kwargs["keywords"] = keywords
        else:
            kwargs["keywords"] = ["人工智能", "数字经济"]

        import inspect
        if inspect.iscoroutinefunction(discover_tool["handler"]):
            result = await discover_tool["handler"](**kwargs)
        else:
            result = discover_tool["handler"](**kwargs)

        return {
            "opportunities": result.get("opportunities", []),
            "count": result.get("count", 0)
        }

    async def _step_evaluate_opportunities(
        self,
        discovery_result: Dict[str, Any],
        min_confidence: float
    ) -> Dict[str, Any]:
        """Step 3: 评估商机价值"""
        logger.info("Step 3: Evaluating opportunities")

        opportunities = discovery_result.get("opportunities", [])
        evaluated = []

        for opp in opportunities:
            confidence = opp.get("confidence_score", 0)
            if confidence >= min_confidence:
                evaluated.append({
                    **opp,
                    "evaluation": "qualified",
                    "confidence_level": "high" if confidence >= 0.8 else "medium"
                })

        return {
            "evaluated_opportunities": evaluated,
            "qualified_count": len(evaluated),
            "total_count": len(opportunities),
            "min_confidence_threshold": min_confidence
        }

    async def _step_prioritize(self, evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: 优先级排序"""
        logger.info("Step 4: Prioritizing opportunities")

        opportunities = evaluation_result.get("evaluated_opportunities", [])

        # 按置信度和潜在价值排序
        sorted_opps = sorted(
            opportunities,
            key=lambda x: (x.get("confidence_score", 0) * 0.6 +
                          (x.get("potential_value", 0) / 10000000 * 0.4)),
            reverse=True
        )

        # 分配优先级
        for i, opp in enumerate(sorted_opps):
            if i < 3:
                opp["priority"] = "high"
            elif i < 10:
                opp["priority"] = "medium"
            else:
                opp["priority"] = "low"

        return {
            "prioritized_opportunities": sorted_opps,
            "high_priority_count": sum(1 for o in sorted_opps if o.get("priority") == "high"),
            "medium_priority_count": sum(1 for o in sorted_opps if o.get("priority") == "medium"),
            "low_priority_count": sum(1 for o in sorted_opps if o.get("priority") == "low")
        }

    async def _step_generate_report(self, priority_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 5: 生成汇总报告"""
        logger.info("Step 5: Generating summary report")

        opportunities = priority_result.get("prioritized_opportunities", [])

        # 生成 Top 10 商机摘要
        top_opportunities = []
        for opp in opportunities[:10]:
            top_opportunities.append({
                "id": opp.get("id"),
                "title": opp.get("title"),
                "type": opp.get("type"),
                "confidence_score": opp.get("confidence_score"),
                "potential_value": opp.get("potential_value"),
                "priority": opp.get("priority")
            })

        return {
            "summary": {
                "total_discovered": priority_result.get("qualified_count", 0),
                "high_priority": priority_result.get("high_priority_count", 0),
                "medium_priority": priority_result.get("medium_priority_count", 0),
                "low_priority": priority_result.get("low_priority_count", 0),
            },
            "top_opportunities": top_opportunities,
            "report_generated_at": datetime.now().isoformat()
        }


# 全局工作流实例
opportunity_discovery_workflow = OpportunityDiscoveryWorkflow
