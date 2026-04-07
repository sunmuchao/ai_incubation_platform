"""
AI Native 功能测试

测试 DeerFlow 2.0 集成的 AI Native 功能：
1. Agent 自主分析
2. 工作流编排
3. 对话式交互
"""
import asyncio
import pytest
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agents.deerflow_client import DeerFlowClient, get_deerflow_client, init_deerflow_client
from agents.traffic_agent import TrafficAgent, get_traffic_agent, AgentContext, AgentResponse, init_traffic_agent
from tools.traffic_tools import TrafficTools, get_traffic_tools
from workflows.traffic_workflows import TrafficWorkflows, get_traffic_workflows, init_traffic_workflows
from workflows.strategy_workflows import StrategyWorkflows, get_strategy_workflows, init_strategy_workflows


class TestDeerFlowClient:
    """测试 DeerFlow 客户端"""

    def test_client_initialization(self):
        """测试客户端初始化"""
        client = DeerFlowClient()
        assert client is not None
        # 在没有 API key 的情况下应该处于降级模式
        assert client.status in [client.status.FALLBACK, client.status.UNAVAILABLE, client.status.AVAILABLE]

    def test_fallback_mode(self):
        """测试降级模式"""
        client = DeerFlowClient()
        # 降级模式应该启用
        assert client.fallback_enabled is True

    def test_get_global_client(self):
        """测试全局客户端获取"""
        client = get_deerflow_client()
        assert client is not None
        assert isinstance(client, DeerFlowClient)


class TestTrafficAgent:
    """测试 Traffic Agent"""

    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        agent = TrafficAgent()
        assert agent is not None
        assert agent.df_client is not None

    def test_agent_context(self):
        """测试 Agent 上下文"""
        context = AgentContext(
            user_id="user_123",
            session_id="session_456",
            trace_id="trace_789"
        )
        assert context.user_id == "user_123"
        assert context.session_id == "session_456"

    def test_intent_classification(self):
        """测试意图分类"""
        agent = get_traffic_agent()

        # 分析类意图
        assert agent._classify_intent("为什么流量下跌") == "analyze"
        assert agent._classify_intent("analyze traffic trend") == "analyze"

        # 优化类意图
        assert agent._classify_intent("发现增长机会") == "optimize"
        assert agent._classify_intent("find optimization opportunities") == "optimize"

        # 执行类意图（优先级最高）
        assert agent._classify_intent("执行优化策略") == "execute"
        assert agent._classify_intent("run strategy") == "execute"

        # 通用意图
        assert agent._classify_intent("你好") == "general"

    @pytest.mark.asyncio
    async def test_chat_greeting(self):
        """测试聊天问候"""
        agent = get_traffic_agent()
        response = await agent.chat("你好")

        assert isinstance(response, AgentResponse)
        assert response.message is not None
        assert len(response.suggestions) > 0

    @pytest.mark.asyncio
    async def test_chat_analyze_request(self):
        """测试分析请求"""
        agent = get_traffic_agent()
        context = AgentContext(
            user_id="test_user",
            trace_id="test_trace"
        )
        agent.set_context(context)

        response = await agent.chat("分析上周流量为什么下跌")
        assert response.action_taken == "analysis_started"


class TestTrafficTools:
    """测试 Traffic 工具集"""

    def test_tools_initialization(self):
        """测试工具集初始化"""
        tools = TrafficTools()
        assert tools is not None
        assert len(tools.tools) > 0

    def test_get_tool_schema(self):
        """测试获取工具 Schema"""
        tools = get_traffic_tools()

        # 测试获取单个工具 Schema
        schema = tools.get_tool_schema("get_traffic_data")
        assert schema is not None
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema

    def test_all_tools_schema(self):
        """测试获取所有工具 Schema"""
        tools = get_traffic_tools()
        schemas = tools.get_all_tools_schema()

        assert isinstance(schemas, list)
        assert len(schemas) > 0

        # 验证每个 Schema 的结构
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "input_schema" in schema

    @pytest.mark.asyncio
    async def test_get_traffic_data(self):
        """测试获取流量数据"""
        tools = get_traffic_tools()

        result = await tools.get_traffic_data(
            start_date="2026-04-01",
            end_date="2026-04-07",
            metrics=["sessions", "pv", "uv"]
        )

        assert result["status"] == "success"
        assert "data" in result

    @pytest.mark.asyncio
    async def test_detect_anomaly(self):
        """测试异常检测"""
        tools = get_traffic_tools()

        result = await tools.detect_anomaly(
            data_source="primary",
            metric="sessions",
            sensitivity="medium"
        )

        assert result["status"] == "success"
        assert "anomalies" in result

    @pytest.mark.asyncio
    async def test_get_opportunities(self):
        """测试获取增长机会"""
        tools = get_traffic_tools()

        result = await tools.get_opportunities(
            limit=10,
            min_roi=0.1
        )

        assert result["status"] == "success"
        assert "opportunities" in result


class TestTrafficWorkflows:
    """测试 Traffic 工作流"""

    def test_workflows_initialization(self):
        """测试工作流初始化"""
        workflows = TrafficWorkflows()
        assert workflows is not None
        assert workflows.df_client is not None
        assert workflows.traffic_tools is not None

    def test_workflows_registered(self):
        """测试工作流注册"""
        workflows = get_traffic_workflows()

        # 检查工作流是否已注册到 DeerFlow 客户端
        assert "auto_diagnosis" in workflows.df_client.workflows
        assert "opportunity_discovery" in workflows.df_client.workflows
        assert "strategy_execution" in workflows.df_client.workflows

    @pytest.mark.asyncio
    async def test_auto_diagnosis_workflow(self):
        """测试自动诊断工作流"""
        workflows = get_traffic_workflows()

        result = await workflows.run_auto_diagnosis(
            trace_id="test_trace",
            user_id="test_user",
            date_range={"start": "2026-04-01", "end": "2026-04-07"},
            metrics=["sessions", "pv"]
        )

        assert result["status"] == "success"
        assert result["workflow"] == "auto_diagnosis"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_opportunity_discovery_workflow(self):
        """测试机会发现工作流"""
        workflows = get_traffic_workflows()

        result = await workflows.run_opportunity_discovery(
            trace_id="test_trace",
            user_id="test_user"
        )

        assert result["status"] == "success"
        assert result["workflow"] == "opportunity_discovery"
        assert "result" in result


class TestStrategyWorkflows:
    """测试 Strategy 工作流"""

    def test_workflows_initialization(self):
        """测试策略工作流初始化"""
        workflows = StrategyWorkflows()
        assert workflows is not None

    def test_workflows_registered(self):
        """测试策略工作流注册"""
        workflows = get_strategy_workflows()

        assert "create_strategy" in workflows.df_client.workflows
        assert "evaluate_strategy" in workflows.df_client.workflows
        assert "optimize_strategy" in workflows.df_client.workflows

    @pytest.mark.asyncio
    async def test_create_strategy_workflow(self):
        """测试创建策略工作流"""
        workflows = get_strategy_workflows()

        result = await workflows.run_create_strategy(
            trace_id="test_trace",
            user_id="test_user",
            problem_description="流量下跌 15%",
            goal="恢复流量到正常水平",
            strategy_type="seo"
        )

        assert result["status"] == "success"
        assert result["workflow"] == "create_strategy"


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_agent_workflow(self):
        """测试完整的 Agent 工作流"""
        # 1. 初始化组件
        client = init_deerflow_client()
        agent = init_traffic_agent(client)
        traffic_workflows = init_traffic_workflows(client)
        strategy_workflows = init_strategy_workflows(client)

        # 2. 设置上下文
        context = AgentContext(
            user_id="integration_test",
            session_id="session_123",
            trace_id="trace_456"
        )
        agent.set_context(context)

        # 3. 执行对话
        response = await agent.chat("分析最近流量趋势")
        assert response is not None

        # 4. 运行诊断工作流
        workflow_result = await traffic_workflows.run_auto_diagnosis(
            trace_id=context.trace_id,
            user_id=context.user_id
        )
        assert workflow_result["status"] == "success"

        # 5. 运行机会发现工作流
        opportunity_result = await traffic_workflows.run_opportunity_discovery(
            trace_id=context.trace_id,
            user_id=context.user_id
        )
        assert opportunity_result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
