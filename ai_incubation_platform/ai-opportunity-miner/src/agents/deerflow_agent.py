"""
DeerFlow 2.0 Agent 编排模块

实现商机挖掘的多步 Agent 工作流，遵循孵化器 Agent 标准：
- 业务动作封装为可调工具
- 敏感操作在工具层强校验与审计
- 多步编排通过 DeerFlow 2.0 统一管理
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class OpportunityMinerAgent:
    """
    商机挖掘 Agent

    使用 DeerFlow 2.0 作为运行时，编排以下多步工作流：
    1. 数据采集（新闻、报告）
    2. 商机发现与分析
    3. 趋势/竞品分析
    4. 报告生成与导出
    """

    def __init__(self):
        self.deerflow_client = None
        self.tools_registry = {}
        self.audit_logs = []
        self._init_tools()
        self._init_deerflow()

    def _init_tools(self):
        """初始化工具注册表"""
        from tools import get_all_tools

        all_tools = get_all_tools()
        for tool in all_tools:
            self.tools_registry[tool["name"]] = tool
            logger.info(f"Registered tool: {tool['name']}")

    def _init_deerflow(self):
        """初始化 DeerFlow 客户端"""
        try:
            from deerflow_integration import get_deerflow_client, is_deerflow_available

            if is_deerflow_available():
                self.deerflow_client = get_deerflow_client()
                logger.info("DeerFlow client initialized successfully")
            else:
                logger.warning("DeerFlow not available, running in fallback mode")
                self.deerflow_client = None
        except ImportError as e:
            logger.warning(f"Failed to import DeerFlow: {e}, running in fallback mode")
            self.deerflow_client = None

    def _log_audit(self, tool_name: str, input_data: Dict, result: Dict, timestamp: datetime = None):
        """审计日志 - 敏感操作记录"""
        audit_entry = {
            "timestamp": (timestamp or datetime.now()).isoformat(),
            "tool_name": tool_name,
            "input": input_data,
            "result_summary": self._summarize_result(result),
        }
        self.audit_logs.append(audit_entry)
        logger.info(f"Audit log: {audit_entry}")

    def _summarize_result(self, result: Dict) -> Dict:
        """简化结果用于审计日志（避免记录过多敏感数据）"""
        summary = {}
        if "success" in result:
            summary["success"] = result["success"]
        if "count" in result:
            summary["count"] = result["count"]
        if "error" in result:
            summary["error"] = result["error"]
        if "message" in result:
            summary["message"] = result["message"]
        if "opportunities" in result:
            summary["opportunities_count"] = len(result["opportunities"])
        return summary

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        tool = self.tools_registry.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        # 敏感操作审计
        require_audit = tool.get("audit_log", False)
        if require_audit:
            logger.info(f"Executing tool with audit: {tool_name}")

        try:
            handler = tool["handler"]

            # 判断是否是异步函数
            import inspect
            if inspect.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)

            if require_audit:
                self._log_audit(tool_name, kwargs, result)

            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {str(e)}")
            if require_audit:
                self._log_audit(tool_name, kwargs, {"success": False, "error": str(e)})
            return {"success": False, "error": str(e)}

    async def discover_opportunities_workflow(self, keywords: List[str], industry: str = None) -> Dict[str, Any]:
        """
        商机发现多步工作流

        步骤：
        1. 获取相关新闻数据
        2. 获取相关行业报告
        3. 基于数据发现商机
        4. 对发现的商机进行趋势分析
        5. 返回汇总结果
        """
        workflow_id = f"discover_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Starting opportunity discovery workflow: {workflow_id}")

        # Step 1: 获取新闻数据
        news_result = await self.execute_tool("fetch_news", keywords=keywords, days=7)

        # Step 2: 获取行业报告
        reports_result = await self.execute_tool("fetch_reports", keywords=keywords)

        # Step 3: 发现商机
        if industry:
            discover_result = await self.execute_tool("discover_opportunities", industry=industry, days=60)
        else:
            discover_result = await self.execute_tool("discover_opportunities", keywords=keywords, days=30)

        # Step 4: 趋势分析（如果有发现商机）
        trend_result = None
        if discover_result.get("success") and discover_result.get("count", 0) > 0:
            trend_result = await self.execute_tool("analyze_trend", keyword=keywords[0], days=30)

        # Step 5: 汇总结果
        workflow_result = {
            "workflow_id": workflow_id,
            "workflow_type": "opportunity_discovery",
            "status": "completed",
            "steps": {
                "news_fetch": news_result,
                "reports_fetch": reports_result,
                "opportunity_discovery": discover_result,
                "trend_analysis": trend_result,
            },
            "summary": {
                "news_count": news_result.get("count", 0),
                "reports_count": reports_result.get("count", 0),
                "opportunities_found": discover_result.get("count", 0),
                "trend_analyzed": trend_result is not None,
            },
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Workflow completed: {workflow_id}")
        return workflow_result

    async def analyze_industry_workflow(self, industry: str) -> Dict[str, Any]:
        """
        行业分析多步工作流

        步骤：
        1. 获取行业新闻
        2. 获取行业报告
        3. 进行竞争格局分析
        4. 进行趋势分析
        5. 返回综合分析报告
        """
        workflow_id = f"industry_analysis_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Starting industry analysis workflow: {workflow_id}")

        # Step 1: 获取行业新闻
        news_result = await self.execute_tool("fetch_news", keywords=[industry, f"{industry}发展"], days=30)

        # Step 2: 获取行业报告
        reports_result = await self.execute_tool("fetch_reports", keywords=[industry])

        # Step 3: 竞争格局分析
        competition_result = await self.execute_tool("analyze_competition", industry=industry, days=60)

        # Step 4: 趋势分析
        trend_result = await self.execute_tool("analyze_trend", keyword=industry, days=60)

        # Step 5: 汇总结果
        workflow_result = {
            "workflow_id": workflow_id,
            "workflow_type": "industry_analysis",
            "status": "completed",
            "steps": {
                "news_fetch": news_result,
                "reports_fetch": reports_result,
                "competition_analysis": competition_result,
                "trend_analysis": trend_result,
            },
            "summary": {
                "industry": industry,
                "news_count": news_result.get("count", 0),
                "reports_count": reports_result.get("count", 0),
                "companies_identified": len(competition_result.get("analysis", {}).get("companies", [])),
                "trend_score": trend_result.get("trend", {}).get("trend_score") if trend_result else None,
            },
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Workflow completed: {workflow_id}")
        return workflow_result

    async def export_report_workflow(self, opp_id: str, format: str = "markdown") -> Dict[str, Any]:
        """
        报告导出工作流

        步骤：
        1. 获取商机详情
        2. 导出报告
        3. 记录审计日志
        """
        workflow_id = f"export_report_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Starting report export workflow: {workflow_id}")

        # Step 1: 获取商机详情
        detail_result = await self.execute_tool("get_opportunity", opp_id=opp_id)

        if not detail_result.get("success"):
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": "Failed to get opportunity details",
            }

        # Step 2: 导出报告
        export_result = await self.execute_tool("export_opportunity", opp_id=opp_id, format=format)

        workflow_result = {
            "workflow_id": workflow_id,
            "workflow_type": "report_export",
            "status": "completed" if export_result.get("success") else "failed",
            "steps": {
                "get_detail": detail_result,
                "export_report": export_result,
            },
            "summary": {
                "opportunity_title": detail_result.get("opportunity", {}).get("title"),
                "export_format": format,
                "export_path": export_result.get("file_path"),
            },
            "timestamp": datetime.now().isoformat(),
        }

        return workflow_result

    def get_audit_logs(self, tool_name: str = None) -> List[Dict]:
        """获取审计日志"""
        if tool_name:
            return [log for log in self.audit_logs if log.get("tool_name") == tool_name]
        return self.audit_logs

    def get_tools_schema(self) -> List[Dict]:
        """获取所有工具的 schema（用于 DeerFlow 配置）"""
        schemas = []
        for tool in self.tools_registry.values():
            schemas.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            })
        return schemas


# 全局 Agent 实例
opportunity_agent = OpportunityMinerAgent()
