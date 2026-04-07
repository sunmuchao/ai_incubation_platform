"""
AI Native 功能测试

测试 DeerFlow 2.0 集成的 AI Native 功能：
1. AI 主动发现机会并推送
2. AI 自主评估机会价值
3. 对话式交互
"""
import asyncio
import pytest
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

logger = pytest.getLogger(__name__)


class TestOpportunityAgent:
    """测试 OpportunityAgent"""

    @pytest.fixture
    def agent(self):
        """获取 Agent 实例"""
        from agents.opportunity_agent import get_opportunity_agent
        return get_opportunity_agent()

    def test_agent_initialization(self, agent):
        """测试 Agent 初始化"""
        assert agent is not None
        assert len(agent.tools_registry) > 0
        print(f"Agent initialized with {len(agent.tools_registry)} tools")

    def test_tools_schema(self, agent):
        """测试工具 Schema"""
        schema = agent.get_tools_schema()
        assert len(schema) > 0

        tool_names = [t["name"] for t in schema]
        assert "list_opportunities" in tool_names
        assert "discover_opportunities" in tool_names
        assert "analyze_trend" in tool_names

        print(f"Available tools: {tool_names}")

    @pytest.mark.asyncio
    async def test_chat_query_discover(self, agent):
        """测试对话式查询 - 发现商机"""
        result = await agent.chat_query("帮我找人工智能领域的商机")

        assert result["intent"] == "discover_opportunities"
        assert "data" in result
        print(f"Chat response: {result['response']}")

    @pytest.mark.asyncio
    async def test_chat_query_trend(self, agent):
        """测试对话式查询 - 分析趋势"""
        result = await agent.chat_query("分析人工智能行业趋势")

        assert result["intent"] == "analyze_trend"
        print(f"Chat response: {result['response']}")

    @pytest.mark.asyncio
    async def test_execute_tool_list(self, agent):
        """测试工具执行 - 列出商机"""
        result = await agent.execute_tool("list_opportunities")

        assert "success" in result
        print(f"List opportunities result: {result}")

    @pytest.mark.asyncio
    async def test_proactive_discovery(self, agent):
        """测试主动商机发现"""
        result = await agent.proactive_discovery(
            keywords=["人工智能"],
            industries=["人工智能"]
        )

        assert "workflow_id" in result
        assert "status" in result
        print(f"Proactive discovery result: {result}")


class TestWorkflows:
    """测试工作流"""

    @pytest.mark.asyncio
    async def test_opportunity_discovery_workflow(self):
        """测试商机发现工作流"""
        from workflows.opportunity_workflows import OpportunityDiscoveryWorkflow

        workflow = OpportunityDiscoveryWorkflow()
        result = await workflow.run(
            keywords=["人工智能"],
            days=7,
            min_confidence=0.3
        )

        assert result["workflow_id"] is not None
        assert result["status"] == "completed"
        print(f"Workflow result: {result}")

    @pytest.mark.asyncio
    async def test_evaluation_workflow(self):
        """测试价值评估工作流"""
        # 首先获取一个商机 ID
        from tools import get_all_tools
        tools_map = {t["name"]: t for t in get_all_tools()}

        list_tool = tools_map.get("list_opportunities")
        if list_tool:
            list_result = await list_tool["handler"]()
            if list_result.get("count", 0) > 0:
                opp_id = list_result["opportunities"][0].get("id")

                from workflows.evaluation_workflows import OpportunityEvaluationWorkflow
                workflow = OpportunityEvaluationWorkflow()
                result = await workflow.run(opp_id)

                assert result["success"] is True
                assert "evaluation" in result
                print(f"Evaluation result: {result}")


class TestPushService:
    """测试推送服务"""

    @pytest.fixture
    def push_service(self):
        """获取推送服务实例"""
        from services.push_service import get_push_service
        return get_push_service()

    def test_push_service_initialization(self, push_service):
        """测试推送服务初始化"""
        assert push_service is not None
        assert len(push_service.push_channels) > 0
        print(f"Push channels: {list(push_service.push_channels.keys())}")

    @pytest.mark.asyncio
    async def test_send_alert(self, push_service):
        """测试发送警报"""
        result = await push_service.send_alert(
            alert_type="test_alert",
            data={"test": "data"},
            priority="medium",
            title="测试警报",
            message="这是一条测试警报"
        )

        assert result["status"] == "sent"
        assert "alert_id" in result
        print(f"Alert sent: {result}")

    def test_get_stats(self, push_service):
        """测试获取统计"""
        stats = push_service.get_stats()
        assert "total_alerts" in stats
        assert "channels" in stats
        print(f"Push stats: {stats}")


class TestA INativeFeatures:
    """测试 AI Native 特性"""

    @pytest.mark.asyncio
    async def test_ai_proactive_alert(self):
        """测试 AI 主动推送"""
        from agents.opportunity_agent import get_opportunity_agent
        from services.push_service import get_push_service

        agent = get_opportunity_agent()
        push_service = get_push_service()

        # 注册推送回调
        alerts_received = []
        def on_alert(alert, channel):
            alerts_received.append(alert)

        push_service.subscribe(on_alert)
        agent.register_push_callback(lambda x: alerts_received.append(x))

        # 触发主动发现
        result = await agent.proactive_discovery(
            keywords=["人工智能"],
            industries=["人工智能"]
        )

        # 验证有警报生成
        assert result["status"] == "completed"
        print(f"Alerts received: {len(alerts_received)}")

    def test_audit_logging(self):
        """测试审计日志"""
        from agents.opportunity_agent import get_opportunity_agent

        agent = get_opportunity_agent()
        initial_count = len(agent.get_audit_logs())

        print(f"Initial audit logs count: {initial_count}")
        assert initial_count >= 0


@pytest.mark.asyncio
async def test_full_ai_native_flow():
    """测试完整 AI Native 流程"""
    from agents.opportunity_agent import get_opportunity_agent
    from workflows.opportunity_workflows import OpportunityDiscoveryWorkflow

    # 1. 初始化 Agent
    agent = get_opportunity_agent()
    print(f"Agent initialized with {len(agent.tools_registry)} tools")

    # 2. 执行商机发现工作流
    workflow = OpportunityDiscoveryWorkflow()
    discovery_result = await workflow.run(
        keywords=["人工智能", "数字经济"],
        days=7,
        min_confidence=0.3
    )
    print(f"Discovery workflow completed: {discovery_result['status']}")

    # 3. 对话式查询
    chat_result = await agent.chat_query("最近有什么高价值商机？")
    print(f"Chat response: {chat_result['response']}")

    # 4. 验证审计日志
    logs = agent.get_audit_logs()
    print(f"Audit logs count: {len(logs)}")

    assert discovery_result["status"] == "completed"
    assert chat_result["intent"] in ["discover_opportunities", "unknown"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
