"""
OpportunityAgent - 商机发现智能体

基于 DeerFlow 2.0 的商机挖掘 Agent，实现：
- AI 主动发现商机并推送
- AI 自主评估机会价值
- 对话式交互
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from agents.deerflow_client import DeerFlowClient, get_deerflow_client, is_deerflow_available

logger = logging.getLogger(__name__)


class OpportunityAgent:
    """
    商机发现智能体

    核心能力：
    1. 主动监控多源数据，发现商机信号
    2. 自主评估商机价值（置信度 + 潜在价值）
    3. 高置信度时主动推送警报
    4. 支持对话式交互
    """

    def __init__(self):
        self.df_client: Optional[DeerFlowClient] = None
        self.tools_registry = {}
        self.push_callbacks = []
        self._audit_logs = []

        self._init_deerflow()
        self._init_tools()

    def _init_deerflow(self):
        """初始化 DeerFlow 客户端"""
        try:
            if is_deerflow_available():
                self.df_client = get_deerflow_client()
                logger.info("DeerFlow client initialized")
            else:
                logger.warning("DeerFlow not available, running in fallback mode")
                self.df_client = None
        except Exception as e:
            logger.warning(f"Failed to init DeerFlow: {e}, running in fallback mode")
            self.df_client = None

    def _init_tools(self):
        """初始化工具注册表"""
        try:
            from tools import get_all_tools
            all_tools = get_all_tools()
            for tool in all_tools:
                self.tools_registry[tool["name"]] = tool
                logger.debug(f"Registered tool: {tool['name']}")
            logger.info(f"Initialized {len(all_tools)} tools")
        except Exception as e:
            logger.error(f"Failed to init tools: {e}")

    def register_push_callback(self, callback):
        """
        注册推送回调函数

        Args:
            callback: 回调函数，签名为 callback(opportunity, alert_type, priority)
        """
        self.push_callbacks.append(callback)
        logger.info(f"Registered push callback: {callback.__name__}")

    def _log_audit(self, action: str, data: Dict, result: Dict):
        """审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "data": data,
            "result": result
        }
        self._audit_logs.append(entry)
        logger.info(f"Audit: {action}")

    async def _send_alert(self, opportunity: Dict, alert_type: str = "new_opportunity", priority: str = "medium"):
        """
        发送警报通知

        Args:
            opportunity: 商机数据
            alert_type: 警报类型 (new_opportunity, high_value, trend_change)
            priority: 优先级 (low, medium, high, critical)
        """
        alert = {
            "alert_id": f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "alert_type": alert_type,
            "priority": priority,
            "opportunity": opportunity,
            "timestamp": datetime.now().isoformat(),
            "message": self._generate_alert_message(opportunity, alert_type, priority)
        }

        logger.info(f"Sending alert: {alert['alert_id']} - {alert['message']}")

        # 调用所有注册的推送回调
        for callback in self.push_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Push callback failed: {e}")

        return alert

    def _generate_alert_message(self, opportunity: Dict, alert_type: str, priority: str) -> str:
        """生成警报消息"""
        title = opportunity.get("title", "未知商机")
        score = opportunity.get("confidence_score", 0)
        value = opportunity.get("potential_value", 0)

        if alert_type == "new_opportunity":
            return f"[新商机] {title} - 置信度 {score:.1f}%, 潜在价值 {value:,}"
        elif alert_type == "high_value":
            return f"[高价值] {title} - 潜在价值 {value:,}，建议优先处理！"
        elif alert_type == "trend_change":
            return f"[趋势变化] {title} - 趋势评分显著提升，建议关注"
        else:
            return f"[{alert_type}] {title}"

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

        try:
            handler = tool["handler"]
            import inspect
            if inspect.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)

            self._log_audit(f"tool_call:{tool_name}", kwargs, result)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {e}")
            return {"success": False, "error": str(e)}

    async def proactive_discovery(self, keywords: List[str] = None, industries: List[str] = None) -> Dict[str, Any]:
        """
        主动商机发现

        AI 自主执行的多步工作流：
        1. 监控数据源
        2. 发现商机信号
        3. 评估价值和置信度
        4. 高价值商机主动推送

        Args:
            keywords: 监控关键词列表
            industries: 监控行业列表

        Returns:
            发现结果汇总
        """
        workflow_id = f"proactive_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Starting proactive discovery workflow: {workflow_id}")

        # 默认监控关键词
        if not keywords:
            keywords = ["人工智能", "数字经济", "智能制造", "新能源", "生物医药"]
        if not industries:
            industries = ["人工智能", "新能源", "半导体"]

        # Step 1: 获取最新数据
        all_opportunities = []

        for keyword in keywords:
            news_result = await self.execute_tool("fetch_news", keywords=[keyword], days=7)
            if news_result.get("success"):
                logger.info(f"Fetched {news_result.get('count', 0)} news for '{keyword}'")

        # Step 2: 发现商机
        discover_result = await self.execute_tool("discover_opportunities", keywords=keywords, days=30)

        if discover_result.get("success"):
            all_opportunities = discover_result.get("opportunities", [])
            logger.info(f"Discovered {len(all_opportunities)} opportunities")

        # Step 3: 评估价值并推送高价值商机
        high_value_count = 0
        for opp in all_opportunities:
            confidence = opp.get("confidence_score", 0)
            value = opp.get("potential_value", 0)

            # 高置信度且高价值的商机主动推送
            if confidence >= 0.7 and value >= 1000000:
                await self._send_alert(opp, alert_type="high_value", priority="high")
                high_value_count += 1
            elif confidence >= 0.8:
                await self._send_alert(opp, alert_type="new_opportunity", priority="medium")

        # Step 4: 行业趋势分析
        trend_summaries = []
        for industry in industries:
            trend_result = await self.execute_tool("analyze_trend", keyword=industry, days=30)
            if trend_result.get("success"):
                trend_data = trend_result.get("trend", {})
                trend_score = trend_data.get("trend_score", 0)
                if trend_score >= 0.7:
                    await self._send_alert(
                        {"title": f"{industry}趋势", "confidence_score": trend_score, "potential_value": 0},
                        alert_type="trend_change",
                        priority="medium"
                    )
                trend_summaries.append({
                    "industry": industry,
                    "trend_score": trend_score,
                    "growth_rate": trend_data.get("growth_rate", 0)
                })

        result = {
            "workflow_id": workflow_id,
            "status": "completed",
            "opportunities_found": len(all_opportunities),
            "high_value_alerts_sent": high_value_count,
            "industries_analyzed": len(trend_summaries),
            "trend_summaries": trend_summaries,
            "timestamp": datetime.now().isoformat()
        }

        self._log_audit("proactive_discovery", {"keywords": keywords, "industries": industries}, result)
        logger.info(f"Proactive discovery completed: {result}")
        return result

    async def evaluate_opportunity(self, opp_id: str) -> Dict[str, Any]:
        """
        深度评估单个商机价值

        Args:
            opp_id: 商机 ID

        Returns:
            评估报告
        """
        logger.info(f"Starting opportunity evaluation: {opp_id}")

        # Step 1: 获取商机详情
        detail_result = await self.execute_tool("get_opportunity", opp_id=opp_id)
        if not detail_result.get("success"):
            return {"success": False, "error": "Failed to get opportunity details"}

        opp = detail_result.get("opportunity", {})

        # Step 2: 相关趋势分析
        tags = opp.get("tags", [])
        trend_analyses = []
        for tag in tags[:3]:  # 最多分析 3 个标签
            trend_result = await self.execute_tool("analyze_trend", keyword=tag, days=30)
            if trend_result.get("success"):
                trend_analyses.append(trend_result.get("trend", {}))

        # Step 3: 竞争格局分析
        industry = opp.get("type", "general")
        competition_result = await self.execute_tool("analyze_competition", industry=industry, days=60)

        # Step 4: 综合评估
        evaluation = {
            "opportunity_id": opp_id,
            "title": opp.get("title"),
            "original_confidence": opp.get("confidence_score", 0),
            "original_value": opp.get("potential_value", 0),
            "trend_analysis": trend_analyses,
            "competition_landscape": competition_result.get("analysis", {}),
            "ai_recommendation": self._generate_recommendation(opp, trend_analyses, competition_result),
            "evaluation_timestamp": datetime.now().isoformat()
        }

        self._log_audit("evaluate_opportunity", {"opp_id": opp_id}, evaluation)
        logger.info(f"Opportunity evaluation completed: {opp_id}")
        return {"success": True, "evaluation": evaluation}

    def _generate_recommendation(self, opp: Dict, trends: List, competition: Dict) -> Dict:
        """生成 AI 推荐建议"""
        confidence = opp.get("confidence_score", 0)
        value = opp.get("potential_value", 0)

        # 基于趋势和竞争情况生成推荐
        avg_trend_score = sum(t.get("trend_score", 0) for t in trends) / len(trends) if trends else 0.5

        recommendation = {
            "action": "monitor",  # monitor, pursue, skip
            "priority": "medium",
            "reasoning": []
        }

        if confidence >= 0.8 and value >= 5000000:
            recommendation["action"] = "pursue"
            recommendation["priority"] = "high"
            recommendation["reasoning"].append("高置信度且高价值，建议优先推进")
        elif confidence >= 0.7 and avg_trend_score >= 0.7:
            recommendation["action"] = "pursue"
            recommendation["priority"] = "medium"
            recommendation["reasoning"].append("趋势向好，建议跟进")
        elif confidence < 0.5:
            recommendation["action"] = "monitor"
            recommendation["reasoning"].append("置信度较低，需要更多数据验证")

        return recommendation

    async def chat_query(self, query: str) -> Dict[str, Any]:
        """
        对话式查询接口

        Args:
            query: 自然语言查询，如"帮我找最近人工智能领域的高价值商机"

        Returns:
            对话响应
        """
        logger.info(f"Processing chat query: {query}")

        # 简单的意图识别（实际应该使用 LLM）
        response = {
            "query": query,
            "intent": "unknown",
            "response": "",
            "data": None
        }

        # 意图识别规则
        query_lower = query.lower()
        if "商机" in query or "机会" in query:
            response["intent"] = "discover_opportunities"
            if "人工智能" in query:
                result = await self.execute_tool("discover_opportunities", keywords=["人工智能"], days=30)
                response["data"] = result
                response["response"] = f"发现 {result.get('count', 0)} 条人工智能相关商机"
            else:
                result = await self.execute_tool("list_opportunities")
                response["data"] = result
                response["response"] = f"当前共有 {result.get('count', 0)} 条商机"

        elif "趋势" in query or "分析" in query:
            response["intent"] = "analyze_trend"
            if "人工智能" in query:
                result = await self.execute_tool("analyze_trend", keyword="人工智能", days=30)
                response["data"] = result
                response["response"] = f"人工智能趋势分析完成，趋势评分：{result.get('trend', {}).get('trend_score', 0):.2f}"
            else:
                response["response"] = "请指定要分析的行业或关键词"

        elif "推送" in query or "警报" in query:
            response["intent"] = "enable_alerts"
            response["response"] = "已启用主动推送模式，高价值商机将自动通知"
            # 触发一次主动发现
            await self.proactive_discovery()

        else:
            response["response"] = "我可以帮您：1) 发现商机 2) 分析趋势 3) 评估机会价值 4) 启用主动推送"

        self._log_audit("chat_query", {"query": query}, response)
        return response

    def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        """获取审计日志"""
        return self._audit_logs[-limit:]

    def get_tools_schema(self) -> List[Dict]:
        """获取工具 schema"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }
            for tool in self.tools_registry.values()
        ]


# 全局 Agent 实例
opportunity_agent = OpportunityAgent()


def get_opportunity_agent() -> OpportunityAgent:
    """获取全局 OpportunityAgent 实例"""
    return opportunity_agent
