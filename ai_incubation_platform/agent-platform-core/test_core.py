"""
Agent Platform Core 测试套件

测试所有核心组件的功能
"""

import asyncio
import pytest
import time
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.deerflow.client import DeerFlowClient, ClientStatus, RetryConfig, DeerFlowResponse
from src.deerflow.workflow import WorkflowEngine, WorkflowStatus, WorkflowDefinition
from src.deerflow.fallback import FallbackMode, FallbackConfig, FallbackResult
from src.tools.base import BaseTool, ToolContext, ToolResult, ToolStatus
from src.tools.registry import ToolsRegistry
from src.audit.models import AuditLog, AuditLogStatus, AuditQuery
from src.audit.logger import AuditLogger, AuditConfig
from src.config.settings import Settings, ConfigLoader
from src.config.secrets import SecretsManager, SecretType
from src.utils.exceptions import (
    ValidationError, NotFoundError, AuthenticationError, ToolError
)


# ==================== DeerFlow Client 测试 ====================

class TestDeerFlowClient:
    """DeerFlow 客户端测试"""

    def test_init_without_api_key(self):
        """测试无 API 密钥初始化"""
        client = DeerFlowClient(api_key=None, fallback_enabled=True)
        assert client.status == ClientStatus.DEGRADED
        assert client.is_degraded is True

    def test_init_with_api_key(self):
        """测试有 API 密钥初始化（降级模式）"""
        client = DeerFlowClient(api_key="test_key", fallback_enabled=True)
        # 由于 deerflow 包不存在，应该进入降级模式
        assert client.is_degraded is True

    def test_register_tool(self):
        """测试注册工具"""
        client = DeerFlowClient(fallback_enabled=True)

        async def mock_handler(**kwargs):
            return {"result": "success"}

        client.register_tool("test_tool", mock_handler, description="Test tool")
        tools = client.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    def test_unregister_tool(self):
        """测试注销工具"""
        client = DeerFlowClient(fallback_enabled=True)

        async def mock_handler(**kwargs):
            return {"result": "success"}

        client.register_tool("test_tool", mock_handler)
        client.unregister_tool("test_tool")
        tools = client.list_tools()

        assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_run_local_workflow(self):
        """测试运行本地工作流（降级模式）"""
        client = DeerFlowClient(fallback_enabled=True)

        async def mock_workflow(**kwargs):
            return {"status": "completed", "data": kwargs}

        client.register_tool("test_workflow", mock_workflow)
        response = await client.run_workflow("test_workflow", param1="value1")

        assert response.success is True
        assert response.is_fallback is True
        assert response.trace_id is not None

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """测试执行工具"""
        client = DeerFlowClient(fallback_enabled=True)

        async def mock_tool(x: int, y: int):
            return x + y

        client.register_tool("add", mock_tool)
        response = await client.execute_tool("add", x=5, y=3)

        assert response.success is True
        assert response.data == 8


# ==================== Workflow Engine 测试 ====================

class TestWorkflowEngine:
    """工作流引擎测试"""

    def test_register_workflow(self):
        """测试注册工作流"""
        engine = WorkflowEngine()
        workflow = engine.register_workflow("test_wf", description="Test workflow")

        assert workflow.name == "test_wf"
        assert workflow.description == "Test workflow"

    def test_add_node(self):
        """测试添加节点"""
        engine = WorkflowEngine()
        workflow = engine.register_workflow("test_wf")

        async def handler(ctx):
            return {"result": "success"}

        node_id = workflow.add_node(
            name="step1",
            handler=handler,
            timeout=30.0
        )

        assert node_id is not None
        assert len(workflow.nodes) == 1

    def test_list_workflows(self):
        """测试列出工作流"""
        engine = WorkflowEngine()
        engine.register_workflow("wf1")
        engine.register_workflow("wf2")

        workflows = engine.list_workflows()

        assert len(workflows) == 2

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self):
        """测试执行简单工作流"""
        engine = WorkflowEngine()

        results = []

        async def step1(ctx):
            results.append("step1")
            return {"step": 1}

        async def step2(ctx):
            results.append("step2")
            return {"step": 2}

        workflow = engine.register_workflow("simple_chain")
        node1_id = workflow.add_node("step1", handler=step1)
        workflow.add_node("step2", handler=step2, dependencies=[node1_id])

        execution = await engine.execute("simple_chain")

        assert execution.status == WorkflowStatus.COMPLETED
        assert results == ["step1", "step2"]

    @pytest.mark.asyncio
    async def test_execute_parallel_workflow(self):
        """测试执行并行工作流"""
        engine = WorkflowEngine()
        results = []

        async def task1(ctx):
            await asyncio.sleep(0.1)
            results.append("task1")
            return {"task": 1}

        async def task2(ctx):
            await asyncio.sleep(0.05)
            results.append("task2")
            return {"task": 2}

        workflow = engine.register_workflow("parallel_wf")
        start_id = workflow.add_node("start")
        workflow.add_node("task1", handler=task1, dependencies=[start_id])
        workflow.add_node("task2", handler=task2, dependencies=[start_id])

        execution = await engine.execute("parallel_wf")

        assert execution.status == WorkflowStatus.COMPLETED
        assert len(results) == 2


# ==================== Fallback Mode 测试 ====================

class TestFallbackMode:
    """降级模式测试"""

    def test_init_default(self):
        """测试默认初始化"""
        fallback = FallbackMode()
        assert fallback.is_degraded is False

    def test_set_mode(self):
        """测试设置模式"""
        fallback = FallbackMode()
        fallback.mode = FallbackMode.LOCAL_ONLY
        assert fallback.is_degraded is True

    def test_should_fallback_disabled(self):
        """测试禁用降级"""
        config = FallbackConfig(mode=FallbackMode.DISABLED)
        fallback = FallbackMode(config)
        assert fallback.should_fallback() is False

    def test_should_fallback_local_only(self):
        """测试仅本地模式"""
        config = FallbackConfig(mode=FallbackMode.LOCAL_ONLY)
        fallback = FallbackMode(config)
        assert fallback.should_fallback() is True

    @pytest.mark.asyncio
    async def test_execute_with_fallback(self):
        """测试带降级执行"""
        fallback = FallbackMode()
        fallback.set_deerflow_availability(False)

        async def primary():
            raise Exception("DeerFlow unavailable")

        async def local():
            return {"result": "local"}

        result = await fallback.execute(primary, local)

        assert result.success is True
        assert result.is_fallback is True
        assert result.data == {"result": "local"}


# ==================== Tools 测试 ====================

class TestTools:
    """工具测试"""

    def test_tool_context(self):
        """测试工具上下文"""
        ctx = ToolContext(user_id="user123")
        ctx.set("key1", "value1")

        assert ctx.get("key1") == "value1"
        assert ctx.get("key2", "default") == "default"

    def test_tool_result_ok(self):
        """测试成功结果"""
        result = ToolResult.ok(data={"result": "success"}, execution_time_ms=10.5)

        assert result.success is True
        assert result.data == {"result": "success"}
        assert result.execution_time_ms == 10.5

    def test_tool_result_fail(self):
        """测试失败结果"""
        result = ToolResult.fail(error="Something went wrong", status=ToolStatus.FAILED)

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.status == ToolStatus.FAILED

    def test_base_tool_validation(self):
        """测试基础工具验证"""

        class TestTool(BaseTool):
            name = "test_tool"
            description = "Test tool"
            input_schema = {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }

            async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
                return ToolResult.ok(data={"name": kwargs.get("name")})

        tool = TestTool()
        is_valid, error = tool.validate_input({"name": "test"})
        assert is_valid is True

        is_valid, error = tool.validate_input({})
        assert is_valid is False
        assert "Missing required parameter" in error


# ==================== Tools Registry 测试 ====================

class TestToolsRegistry:
    """工具注册表测试"""

    def test_register_function(self):
        """测试注册函数"""
        registry = ToolsRegistry()

        async def my_tool(param1: str):
            return {"param1": param1}

        registry.register(
            name="my_tool",
            handler=my_tool,
            description="My tool",
            input_schema={
                "type": "object",
                "properties": {"param1": {"type": "string"}},
                "required": ["param1"]
            }
        )

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "my_tool"

    def test_search_tools(self):
        """测试搜索工具"""
        registry = ToolsRegistry()

        registry.register("search_users", handler=lambda: None, description="Search users", tags=["user", "search"])
        registry.register("create_user", handler=lambda: None, description="Create user", tags=["user"])

        results = registry.search_tools("search")
        assert len(results) >= 1
        assert results[0]["name"] == "search_users"

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """测试执行工具"""
        registry = ToolsRegistry()

        async def add_tool(x: int, y: int):
            return x + y

        registry.register(
            name="add",
            handler=add_tool,
            description="Add two numbers",
            input_schema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"}
                },
                "required": ["x", "y"]
            }
        )

        ctx = ToolContext()
        result = await registry.execute("add", ctx, x=5, y=3)

        assert result.success is True
        assert result.data == 8


# ==================== Audit 测试 ====================

class TestAudit:
    """审计测试"""

    def test_audit_log_creation(self):
        """测试审计日志创建"""
        log = AuditLog(
            actor="user123",
            action="create",
            resource="user",
            status=AuditLogStatus.SUCCESS
        )

        assert log.id is not None
        assert log.actor == "user123"
        assert log.status == AuditLogStatus.SUCCESS

    def test_audit_log_mark_success(self):
        """测试标记成功"""
        log = AuditLog(actor="user123", action="create", resource="user")
        log.mark_success(response={"id": "new_id"})

        assert log.status == AuditLogStatus.SUCCESS
        assert log.end_time is not None
        assert log.response == {"id": "new_id"}

    def test_audit_log_mark_failed(self):
        """测试标记失败"""
        log = AuditLog(actor="user123", action="create", resource="user")
        log.mark_failed(error="Database error", error_code="DB_ERROR")

        assert log.status == AuditLogStatus.FAILED
        assert log.error_message == "Database error"
        assert log.error_code == "DB_ERROR"

    @pytest.mark.asyncio
    async def test_audit_logger_log(self):
        """测试审计日志记录器"""
        logger = AuditLogger()

        log = await logger.log(
            actor="user123",
            action="execute_tool",
            resource="my_tool",
            request={"param": "value"},
            response={"result": "success"},
            status="success"
        )

        assert log is not None
        assert log.actor == "user123"

    @pytest.mark.asyncio
    async def test_audit_logger_query(self):
        """测试审计日志查询"""
        logger = AuditLogger()

        await logger.log(actor="user1", action="create", resource="doc1", status="success")
        await logger.log(actor="user2", action="delete", resource="doc2", status="failed")

        query = AuditQuery(actor="user1")
        results = await logger.query(query)

        assert len(results) == 1
        assert results[0].actor == "user1"


# ==================== Config 测试 ====================

class TestConfig:
    """配置测试"""

    def test_settings_default(self):
        """测试默认配置"""
        settings = Settings()

        assert settings.app_name == "agent-platform-core"
        assert settings.debug is False
        assert settings.port == 8000

    def test_settings_get_set(self):
        """测试获取设置配置"""
        settings = Settings()
        settings.set("debug", True)

        assert settings.get("debug") is True
        assert settings.get("nonexistent", "default") == "default"

    def test_settings_validate(self):
        """测试配置验证"""
        settings = Settings()
        errors = settings.validate()

        # 默认配置应该通过验证
        assert len(errors) == 0

    def test_settings_validate_invalid_port(self):
        """测试无效端口验证"""
        settings = Settings(port=99999)
        errors = settings.validate()

        assert len(errors) == 1
        assert "Invalid port" in errors[0]

    def test_config_loader(self):
        """测试配置加载器"""
        loader = ConfigLoader()
        settings = loader.load(
            env_prefix="TEST_",
            app_name="test_app",
            debug=True
        )

        assert settings.app_name == "test_app"
        assert settings.debug is True


# ==================== Secrets 测试 ====================

class TestSecrets:
    """密钥测试"""

    def test_secrets_manager_set_get(self):
        """测试设置获取密钥"""
        manager = SecretsManager()

        manager.set("api_key", "secret_value_123")
        value = manager.get("api_key")

        assert value == "secret_value_123"

    def test_secrets_manager_with_expiration(self):
        """测试带过期时间的密钥"""
        manager = SecretsManager()

        manager.set("temp_token", "token123", expires_in=1)
        value = manager.get("temp_token")
        assert value == "token123"

        # 等待过期
        time.sleep(1.1)
        value = manager.get("temp_token")
        assert value is None

    def test_secrets_manager_list(self):
        """测试列出密钥"""
        manager = SecretsManager()

        manager.set("key1", "value1", secret_type=SecretType.API_KEY, tags=["prod"])
        manager.set("key2", "value2", secret_type=SecretType.TOKEN, tags=["dev"])

        secrets = manager.list_secrets()
        assert len(secrets) == 2

        # 按类型过滤
        api_keys = manager.list_secrets(secret_type=SecretType.API_KEY)
        assert len(api_keys) == 1

    def test_secrets_manager_masked_value(self):
        """测试脱敏值"""
        manager = SecretsManager()
        manager.set("password", "my_secret_password")

        entry = manager.get_entry("password")
        masked = entry.masked_value

        assert masked != "my_secret_password"
        assert masked.startswith("my")
        assert masked.endswith("rd")

    def test_secrets_manager_rotation(self):
        """测试密钥轮换"""
        manager = SecretsManager()
        manager.set("db_password", "old_password")

        new_entry = manager.rotate("db_password", "new_password")

        assert manager.get("db_password") == "new_password"

    def test_secrets_manager_stats(self):
        """测试统计信息"""
        manager = SecretsManager()
        manager.set("key1", "value1", secret_type=SecretType.API_KEY)
        manager.set("key2", "value2", secret_type=SecretType.TOKEN)

        stats = manager.get_stats()

        assert stats["total_count"] == 2
        assert stats["by_type"]["api_key"] == 1
        assert stats["by_type"]["token"] == 1


# ==================== Exceptions 测试 ====================

class TestExceptions:
    """异常测试"""

    def test_validation_error(self):
        """测试验证错误"""
        error = ValidationError(
            message="Invalid email format",
            field="email",
            value="not_an_email"
        )

        assert error.code == "VALIDATION_ERROR"
        assert error.status_code == 400
        assert error.field == "email"

    def test_not_found_error(self):
        """测试未找到错误"""
        error = NotFoundError(
            resource_type="user",
            resource_id="12345"
        )

        assert error.code == "NOT_FOUND"
        assert error.status_code == 404
        assert error.context["resource_id"] == "12345"

    def test_authentication_error(self):
        """测试认证错误"""
        error = AuthenticationError(
            message="Invalid token",
            auth_type="jwt"
        )

        assert error.status_code == 401
        assert error.context["auth_type"] == "jwt"

    def test_error_to_dict(self):
        """测试错误转字典"""
        error = ValidationError(message="Required field", field="name")
        error_dict = error.to_dict()

        assert "error" in error_dict
        assert error_dict["error"]["code"] == "VALIDATION_ERROR"
        assert error_dict["error"]["message"] == "Required field"


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
