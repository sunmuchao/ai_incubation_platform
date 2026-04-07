#!/usr/bin/env python3
"""
Agent Platform Core 简单测试脚本

验证核心组件的基本功能
"""

import asyncio
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """测试导入"""
    print("=" * 50)
    print("测试导入...")

    from deerflow.client import DeerFlowClient, ClientStatus
    from deerflow.workflow import WorkflowEngine
    from deerflow.fallback import FallbackMode, FallbackConfig, FallbackModeManager
    from tools.base import BaseTool, ToolContext, ToolResult
    from tools.registry import ToolsRegistry
    from audit.models import AuditLog, AuditLogStatus
    from audit.logger import AuditLogger
    from config.settings import Settings, ConfigLoader
    from config.secrets import SecretsManager, SecretType
    from utils.exceptions import ValidationError, NotFoundError

    print("  [OK] 所有模块导入成功")
    return True


def test_settings():
    """测试配置"""
    print("=" * 50)
    print("测试配置管理...")

    from config.settings import Settings

    settings = Settings()
    assert settings.app_name == "agent-platform-core"
    assert settings.port == 8000
    assert settings.debug is False

    settings.set("debug", True)
    assert settings.get("debug") is True

    errors = settings.validate()
    assert len(errors) == 0

    print("  [OK] 配置管理测试通过")
    return True


def test_secrets():
    """测试密钥管理"""
    print("=" * 50)
    print("测试密钥管理...")

    from config.secrets import SecretsManager, SecretType

    manager = SecretsManager()

    # 设置密钥
    manager.set("api_key", "secret_123", secret_type=SecretType.API_KEY)
    assert manager.get("api_key") == "secret_123"

    # 测试脱敏
    entry = manager.get_entry("api_key")
    assert entry.masked_value != "secret_123"

    # 列出密钥
    secrets = manager.list_secrets()
    assert len(secrets) == 1

    print("  [OK] 密钥管理测试通过")
    return True


def test_audit():
    """测试审计日志"""
    print("=" * 50)
    print("测试审计日志...")

    from audit.models import AuditLog, AuditLogStatus, AuditQuery
    from audit.logger import AuditLogger

    # 测试日志模型
    log = AuditLog(
        actor="user123",
        action="create",
        resource="document",
        status=AuditLogStatus.SUCCESS
    )
    assert log.id is not None
    assert log.actor == "user123"

    # 测试日志记录器
    logger = AuditLogger()

    async def run_test():
        await logger.log(
            actor="user123",
            action="execute_tool",
            resource="my_tool",
            request={"param": "value"},
            response={"result": "success"},
            status="success"
        )

        results = await logger.query(AuditQuery(actor="user123"))
        assert len(results) == 1

    asyncio.run(run_test())

    print("  [OK] 审计日志测试通过")
    return True


def test_tools():
    """测试工具系统"""
    print("=" * 50)
    print("测试工具系统...")

    from tools.base import BaseTool, ToolContext, ToolResult
    from tools.registry import ToolsRegistry

    # 测试工具结果
    result_ok = ToolResult.ok(data={"key": "value"})
    assert result_ok.success is True
    assert result_ok.data == {"key": "value"}

    result_fail = ToolResult.fail(error="Something wrong")
    assert result_fail.success is False

    # 测试自定义工具
    class AddTool(BaseTool):
        name = "add"
        description = "Add two numbers"
        input_schema = {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"}
            },
            "required": ["x", "y"]
        }

        async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
            x = kwargs.get("x", 0)
            y = kwargs.get("y", 0)
            return ToolResult.ok(data=x + y)

    tool = AddTool()
    is_valid, error = tool.validate_input({"x": 1, "y": 2})
    assert is_valid is True

    is_valid, error = tool.validate_input({})
    assert is_valid is False

    # 测试注册表
    registry = ToolsRegistry()

    async def multiply(x: int, y: int):
        return x * y

    registry.register(
        name="multiply",
        handler=multiply,
        description="Multiply two numbers",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"}
            },
            "required": ["x", "y"]
        }
    )

    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "multiply"

    async def run_test():
        ctx = ToolContext()
        result = await registry.execute("multiply", ctx, x=3, y=4)
        assert result.success is True
        assert result.data == 12

    asyncio.run(run_test())

    print("  [OK] 工具系统测试通过")
    return True


def test_workflow():
    """测试工作流引擎"""
    print("=" * 50)
    print("测试工作流引擎...")

    from deerflow.workflow import WorkflowEngine, WorkflowStatus

    engine = WorkflowEngine()

    # 注册工作流
    workflow = engine.register_workflow("test_chain", description="Test chain workflow")

    results = []

    async def step1(ctx):
        results.append("step1")
        return {"step": 1}

    async def step2(ctx):
        results.append("step2")
        return {"step": 2}

    async def step3(ctx):
        results.append("step3")
        return {"step": 3}

    # 添加节点
    node1_id = workflow.add_node("step1", handler=step1)
    node2_id = workflow.add_node("step2", handler=step2, dependencies=[node1_id])
    node3_id = workflow.add_node("step3", handler=step3, dependencies=[node2_id])

    # 执行
    async def run_test():
        execution = await engine.execute("test_chain")
        assert execution.status == WorkflowStatus.COMPLETED
        assert results == ["step1", "step2", "step3"]

    asyncio.run(run_test())

    print("  [OK] 工作流引擎测试通过")
    return True


def test_fallback_mode():
    """测试降级模式"""
    print("=" * 50)
    print("测试降级模式...")

    from deerflow.fallback import FallbackMode, FallbackConfig, FallbackModeManager

    # 测试配置
    config = FallbackConfig()
    assert config.mode == FallbackMode.HYBRID
    assert config.max_retries == 3

    # 测试管理器
    manager = FallbackModeManager(config)
    assert manager.is_degraded is False

    # 设置 DeerFlow 不可用
    manager.set_deerflow_availability(False)
    assert manager.is_degraded is True
    assert manager.should_fallback() is True

    # 测试本地模式
    config_local = FallbackConfig(mode=FallbackMode.LOCAL_ONLY)
    manager_local = FallbackModeManager(config_local)
    assert manager_local.should_fallback() is True

    # 测试禁用模式
    config_disabled = FallbackConfig(mode=FallbackMode.DISABLED)
    manager_disabled = FallbackModeManager(config_disabled)
    manager_disabled.set_deerflow_availability(False)
    assert manager_disabled.should_fallback() is False

    print("  [OK] 降级模式测试通过")
    return True


def test_deerflow_client():
    """测试 DeerFlow 客户端"""
    print("=" * 50)
    print("测试 DeerFlow 客户端...")

    from deerflow.client import DeerFlowClient, ClientStatus

    # 无 API 密钥
    client = DeerFlowClient(api_key=None, fallback_enabled=True)
    assert client.status == ClientStatus.DEGRADED
    assert client.is_degraded is True

    # 注册工具
    async def mock_tool(**kwargs):
        return {"status": "ok", "params": kwargs}

    client.register_tool("test_tool", mock_tool, description="Test tool")
    tools = client.list_tools()
    assert len(tools) == 1

    # 执行工具
    async def run_test():
        response = await client.execute_tool("test_tool", param1="value1")
        assert response.success is True
        assert response.is_fallback is True

    asyncio.run(run_test())

    print("  [OK] DeerFlow 客户端测试通过")
    return True


def test_exceptions():
    """测试异常处理"""
    print("=" * 50)
    print("测试异常处理...")

    from utils.exceptions import (
        ValidationError, NotFoundError, AuthenticationError,
        ToolError, WorkflowError, handle_exception
    )

    # 验证错误
    try:
        raise ValidationError(message="Invalid format", field_name="email", value="bad")
    except ValidationError as e:
        assert e.code == "VALIDATION_ERROR"
        assert e.status_code == 400
        assert e.field == "email"

    # 未找到错误
    try:
        raise NotFoundError(resource_type="user", resource_id="123")
    except NotFoundError as e:
        assert e.code == "NOT_FOUND"
        assert e.status_code == 404

    # 认证错误
    try:
        raise AuthenticationError(message="Invalid token")
    except AuthenticationError as e:
        assert e.status_code == 401

    # 错误转字典
    error = ValidationError(message="Test error")
    error_dict = error.to_dict()
    assert "error" in error_dict
    assert error_dict["error"]["code"] == "VALIDATION_ERROR"

    print("  [OK] 异常处理测试通过")
    return True


def main():
    """运行所有测试"""
    print("\n")
    print("*" * 50)
    print("Agent Platform Core 测试套件")
    print("*" * 50)
    print()

    tests = [
        ("导入测试", test_imports),
        ("配置管理", test_settings),
        ("密钥管理", test_secrets),
        ("审计日志", test_audit),
        ("工具系统", test_tools),
        ("工作流引擎", test_workflow),
        ("降级模式", test_fallback_mode),
        ("DeerFlow 客户端", test_deerflow_client),
        ("异常处理", test_exceptions),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    print()
    print("=" * 50)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
