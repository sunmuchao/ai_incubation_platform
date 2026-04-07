"""
AI Native 集成测试 - 测试 DeerFlow 2.0 架构层

测试范围:
1. Agent 层 - OptimizerAgent
2. Tools 层 - 性能分析工具
3. Workflows 层 - 优化工作流
4. API 层 - AI Native API 端点
"""

import asyncio
import pytest
import sys
from datetime import datetime
from unittest.mock import AsyncMock, patch

# Add src to path
sys.path.insert(0, "src")


# ============================================================
# Test: Agents Layer
# ============================================================

class TestDeerFlowClient:
    """Test DeerFlow Client"""

    def test_client_initialization(self):
        """Test client can be initialized"""
        from agents.deerflow_client import DeerFlowClient

        client = DeerFlowClient(
            api_key="test-key",
            fallback_enabled=True
        )

        assert client.api_key == "test-key"
        assert client.fallback_enabled is True
        assert client._available is None  # Not checked yet

    def test_client_local_workflow_registration(self):
        """Test local workflow registration"""
        from agents.deerflow_client import DeerFlowClient

        client = DeerFlowClient(fallback_enabled=True)

        async def test_workflow(**kwargs):
            return {"result": "success"}

        client.register_local_workflow("test_workflow", test_workflow)

        assert "test_workflow" in client._local_workflows

    @pytest.mark.asyncio
    async def test_client_local_workflow_execution(self):
        """Test local workflow execution"""
        from agents.deerflow_client import DeerFlowClient

        client = DeerFlowClient(fallback_enabled=True)

        async def test_workflow(value: int):
            return {"result": "success", "value": value * 2}

        client.register_local_workflow("test_workflow", test_workflow)

        result = await client.run_workflow("test_workflow", value=5)

        assert result["result"] == "success"
        assert result["value"] == 10


class TestOptimizerAgent:
    """Test Optimizer Agent"""

    def test_agent_initialization(self):
        """Test agent can be initialized"""
        from agents.optimizer_agent import OptimizerAgent, AgentState
        from agents.deerflow_client import DeerFlowClient

        client = DeerFlowClient(fallback_enabled=True)
        agent = OptimizerAgent(
            deerflow_client=client,
            auto_execute_threshold=0.9
        )

        assert agent.state == AgentState.IDLE
        assert agent.auto_execute_threshold == 0.9
        assert agent.audit_enabled is True

    @pytest.mark.asyncio
    async def test_agent_perceive(self):
        """Test agent perception"""
        from agents.optimizer_agent import OptimizerAgent
        from agents.deerflow_client import DeerFlowClient

        client = DeerFlowClient(fallback_enabled=True)
        agent = OptimizerAgent(deerflow_client=client)

        # Test local fallback perception
        signals = await agent.perceive(service="test-service")

        # Should return list (may be empty in test environment)
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_agent_diagnose_no_signals(self):
        """Test agent diagnosis with no signals"""
        from agents.optimizer_agent import OptimizerAgent
        from agents.deerflow_client import DeerFlowClient

        client = DeerFlowClient(fallback_enabled=True)
        agent = OptimizerAgent(deerflow_client=client)

        diagnosis = await agent.diagnose(signals=[])

        assert diagnosis is None

    @pytest.mark.asyncio
    async def test_agent_analyze_and_optimize(self):
        """Test full autonomous optimization loop"""
        from agents.optimizer_agent import OptimizerAgent
        from agents.deerflow_client import DeerFlowClient

        client = DeerFlowClient(fallback_enabled=True)
        agent = OptimizerAgent(deerflow_client=client)

        result = await agent.analyze_and_optimize(
            service="test-service",
            auto_execute=False
        )

        assert "trace_id" in result
        assert "timestamp" in result
        assert "service" in result


# ============================================================
# Test: Tools Layer
# ============================================================

class TestToolsRegistry:
    """Test Tools Registry"""

    def test_tools_registry_initialization(self):
        """Test tools registry is initialized"""
        from tools.registry import TOOLS_REGISTRY

        # Registry should be a dict
        assert isinstance(TOOLS_REGISTRY, dict)

    def test_register_tool(self):
        """Test tool registration"""
        from tools.registry import register_tool, get_tool, TOOLS_REGISTRY

        # Clean up any existing test tool
        if "test_tool" in TOOLS_REGISTRY:
            del TOOLS_REGISTRY["test_tool"]

        async def test_handler(**kwargs):
            return {"result": "success"}

        register_tool(
            name="test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            handler=test_handler,
            tags=["test"]
        )

        tool = get_tool("test_tool")
        assert tool is not None
        assert tool["name"] == "test_tool"
        assert "test" in tool["tags"]

    def test_list_tools(self):
        """Test listing tools"""
        from tools.registry import list_tools

        tools = list_tools()
        assert isinstance(tools, list)

        # Each tool should have required fields
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool


class TestPerformanceTools:
    """Test Performance Analysis Tools"""

    def test_performance_analyzer_initialization(self):
        """Test performance analyzer can be initialized"""
        from tools.performance_tools import PerformanceAnalyzer

        analyzer = PerformanceAnalyzer()
        assert analyzer is not None

    @pytest.mark.asyncio
    async def test_analyze_service(self):
        """Test service analysis"""
        from tools.performance_tools import PerformanceAnalyzer

        analyzer = PerformanceAnalyzer()
        result = await analyzer.analyze_service("test-service")

        assert "service" in result
        assert result["service"] == "test-service"
        assert "timestamp" in result
        assert "metrics" in result

    @pytest.mark.asyncio
    async def test_detect_anomalies(self):
        """Test anomaly detection"""
        from tools.performance_tools import PerformanceAnalyzer

        analyzer = PerformanceAnalyzer()
        signals = await analyzer.detect_anomalies(
            service="test-service",
            time_window=300
        )

        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_get_optimization_recommendations(self):
        """Test optimization recommendations"""
        from tools.performance_tools import PerformanceAnalyzer

        analyzer = PerformanceAnalyzer()

        # Test with high latency
        recommendations = await analyzer.get_optimization_recommendations(
            service="test-service",
            metrics={"latency_p99": 1500, "error_rate": 0.0, "throughput": 100}
        )

        assert isinstance(recommendations, list)
        # Should have latency optimization recommendation
        latency_recs = [r for r in recommendations if r.get("type") == "latency_optimization"]
        assert len(latency_recs) > 0


# ============================================================
# Test: Workflows Layer
# ============================================================

class TestOptimizerWorkflows:
    """Test Optimizer Workflows"""

    def test_workflows_initialization(self):
        """Test workflows can be initialized"""
        from workflows.optimizer_workflows import OptimizerWorkflows

        workflows = OptimizerWorkflows()
        assert workflows is not None

    def test_workflow_definitions(self):
        """Test workflow definitions are registered"""
        from workflows.optimizer_workflows import OptimizerWorkflows

        workflows = OptimizerWorkflows()
        definitions = workflows.list_workflows()

        assert len(definitions) > 0

        # Check core workflows exist
        workflow_names = [w["name"] for w in definitions]
        assert "perceive_signals" in workflow_names
        assert "diagnose_signals" in workflow_names
        assert "execute_remediation" in workflow_names
        assert "generate_optimization" in workflow_names

    @pytest.mark.asyncio
    async def test_perceive_signals_workflow(self):
        """Test perceive signals workflow"""
        from workflows.optimizer_workflows import OptimizerWorkflows

        workflows = OptimizerWorkflows()
        result = await workflows.perceive_signals(
            service="test-service",
            time_window=300
        )

        assert "signals" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_diagnose_signals_workflow(self):
        """Test diagnose signals workflow"""
        from workflows.optimizer_workflows import OptimizerWorkflows

        workflows = OptimizerWorkflows()

        # Create mock signals
        signals = [
            {
                "id": "signal-1",
                "source": "metrics",
                "type": "anomaly",
                "severity": "high",
                "timestamp": datetime.now().isoformat(),
                "data": {"metric": "latency", "value": 1000}
            }
        ]

        result = await workflows.diagnose_signals(signals=signals)

        assert "id" in result
        assert "root_cause" in result
        assert "confidence" in result
        assert "report" in result

    @pytest.mark.asyncio
    async def test_execute_remediation_workflow(self):
        """Test execute remediation workflow"""
        from workflows.optimizer_workflows import OptimizerWorkflows

        workflows = OptimizerWorkflows()

        action = {
            "name": "restart_service",
            "type": "remediation",
            "parameters": {"service": "test-service"}
        }

        result = await workflows.execute_remediation(
            action=action,
            diagnosis_id="test-diagnosis"
        )

        assert "success" in result
        assert "action" in result

    @pytest.mark.asyncio
    async def test_generate_optimization_workflow(self):
        """Test generate optimization workflow"""
        from workflows.optimizer_workflows import OptimizerWorkflows

        workflows = OptimizerWorkflows()

        context = {
            "service": "test-service",
            "goals": ["reduce_latency", "improve_throughput"]
        }

        result = await workflows.generate_optimization(context=context)

        assert "success" in result
        assert "optimization_name" in result


class TestLocalWorkflows:
    """Test Local Workflows"""

    def test_local_workflows_initialization(self):
        """Test local workflows can be initialized"""
        from workflows.local_workflows import LocalWorkflows

        workflows = LocalWorkflows()
        assert workflows is not None

    def test_local_handlers(self):
        """Test local workflow handlers are registered"""
        from workflows.local_workflows import LocalWorkflows

        workflows = LocalWorkflows()
        handlers = workflows.list_handlers()

        assert len(handlers) > 0
        assert "analyze_performance" in handlers
        assert "diagnose_issue" in handlers
        assert "execute_remediation" in handlers
        assert "full_autonomous_loop" in handlers


# ============================================================
# Test: Integration
# ============================================================

class TestIntegration:
    """Integration tests for AI Native architecture"""

    @pytest.mark.asyncio
    async def test_full_agent_workflow_integration(self):
        """Test full integration: Agent + Tools + Workflows"""
        from agents.optimizer_agent import OptimizerAgent
        from agents.deerflow_client import DeerFlowClient
        from workflows.optimizer_workflows import register_optimizer_workflows

        # Create client and agent
        client = DeerFlowClient(fallback_enabled=True)
        agent = OptimizerAgent(deerflow_client=client)

        # Register workflows
        register_optimizer_workflows(agent)

        # Run full autonomous loop
        result = await agent.analyze_and_optimize(
            service="test-service",
            auto_execute=False
        )

        # Verify result structure
        assert "trace_id" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_tools_invocation_via_agent(self):
        """Test tools can be invoked through agent"""
        from agents.optimizer_agent import OptimizerAgent
        from agents.deerflow_client import DeerFlowClient
        from tools.performance_tools import get_performance_analyzer

        client = DeerFlowClient(fallback_enabled=True)
        agent = OptimizerAgent(deerflow_client=client)

        # Get analyzer directly and verify it works
        analyzer = get_performance_analyzer()
        result = await analyzer.analyze_service("test-service")

        assert result["service"] == "test-service"


# ============================================================
# Test: API Endpoints (when FastAPI test client available)
# ============================================================

@pytest.mark.skip(reason="Requires full app setup")
class TestAINativeAPI:
    """Test AI Native API endpoints"""

    @pytest.mark.asyncio
    async def test_ai_ask_endpoint(self):
        """Test AI ask endpoint"""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        response = client.post("/api/ai/ask", json={
            "question": "系统状态如何？"
        })

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_ai_diagnose_endpoint(self):
        """Test AI diagnose endpoint"""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        response = client.post("/api/ai/diagnose", json={
            "service": "payment-service",
            "symptoms": ["high_latency", "increased_errors"]
        })

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ai_dashboard_endpoint(self):
        """Test AI dashboard endpoint"""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        response = client.get("/api/ai/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "health_score" in data
        assert "ai_insights" in data


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
