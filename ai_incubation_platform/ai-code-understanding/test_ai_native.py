"""
AI Native 集成测试

测试 DeerFlow 2.0 集成、对话式 API 和 Generative UI
"""
import asyncio
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_agents():
    """测试 Agent 层"""
    print("\n" + "=" * 60)
    print("测试 Agents 层")
    print("=" * 60)

    try:
        from agents import CodeUnderstandingAgent, get_code_agent
        from agents.deerflow_client import DeerFlowClient, is_deerflow_available

        print("[OK] Agent 模块导入成功")

        # 测试 DeerFlow 客户端
        client = DeerFlowClient()
        available = client.is_available()
        print(f"  - DeerFlow 可用性：{available}")

        # 测试 Agent 实例化
        agent = get_code_agent(project_name="test_project")
        print(f"  - Agent 实例化成功：{agent.__class__.__name__}")
        print(f"  - 默认项目：{agent.default_project}")

        return True
    except Exception as e:
        print(f"[FAIL] Agents 层测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_tools():
    """测试 Tools 层"""
    print("\n" + "=" * 60)
    print("测试 Tools 层")
    print("=" * 60)

    try:
        from tools import TOOLS_REGISTRY, CodeTools
        from tools.code_tools import get_tools, bind_handlers

        print("[OK] Tools 模块导入成功")

        # 测试工具注册表
        print(f"  - 注册工具数量：{len(TOOLS_REGISTRY)}")
        for tool_name, tool_info in TOOLS_REGISTRY.items():
            print(f"    * {tool_name}: {tool_info.get('description', '')[:50]}...")

        # 测试工具实例
        tools = get_tools()
        print(f"  - 工具实例：{tools.__class__.__name__}")

        return True
    except Exception as e:
        print(f"[FAIL] Tools 层测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflows():
    """测试 Workflows 层"""
    print("\n" + "=" * 60)
    print("测试 Workflows 层")
    print("=" * 60)

    try:
        from workflows import (
            CodeUnderstandingWorkflow,
            CodeExplorationWorkflow,
            ImpactAnalysisWorkflow,
        )

        print("[OK] Workflows 模块导入成功")

        # 测试工作流实例化
        workflows = [
            CodeUnderstandingWorkflow(),
            CodeExplorationWorkflow(),
            ImpactAnalysisWorkflow(),
        ]

        for wf in workflows:
            print(f"  - {wf.workflow_name}: {wf.workflow_description}")

        return True
    except Exception as e:
        print(f"[FAIL] Workflows 层测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


async def test_workflow_execution():
    """测试工作流执行"""
    print("\n" + "=" * 60)
    print("测试工作流执行")
    print("=" * 60)

    try:
        from workflows.code_workflows import CodeUnderstandingWorkflow

        workflow = CodeUnderstandingWorkflow()

        # 测试简单意图
        input_data = {
            "message": "解释这段代码的功能",
            "context": {
                "selected_code": "def hello(): return 'world'",
            },
            "project_name": "test",
        }

        print("执行代码理解工作流...")
        result = await workflow.execute(input_data)

        print(f"  - 工作流状态：{result.get('status')}")
        print(f"  - 意图：{result.get('intent')}")
        print(f"  - 置信度：{result.get('confidence')}")
        print(f"  - 思考步骤：{len(result.get('thinking_trace', []))}")
        print(f"  - 解释长度：{len(result.get('explanation', ''))}")

        return True
    except Exception as e:
        print(f"[FAIL] 工作流执行测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_routes():
    """测试 API 路由"""
    print("\n" + "=" * 60)
    print("测试 API 路由")
    print("=" * 60)

    try:
        from api.chat import router as chat_router
        from api.generative_ui import router as generative_ui_router

        print("[OK] API 路由导入成功")
        print(f"  - Chat router: {chat_router.prefix}")
        print(f"  - Generative UI router: {generative_ui_router.prefix}")

        return True
    except Exception as e:
        print(f"[FAIL] API 路由测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_generative_ui_engine():
    """测试 Generative UI 引擎"""
    print("\n" + "=" * 60)
    print("测试 Generative UI 引擎")
    print("=" * 60)

    try:
        from api.generative_ui import GenerativeUIEngine

        engine = GenerativeUIEngine()

        # 测试不同意图和数据类型的组合
        test_cases = [
            ("explore", "dependency"),
            ("understand", "flow"),
            ("modify", "dependency"),
            ("debug", "call"),
        ]

        for intent, data_type in test_cases:
            config = engine.generate_view_config(
                intent=intent,
                data_type=data_type,
                context={"project_name": "test"}
            )
            print(f"  - {intent} + {data_type} => {config['view_type']}")

        return True
    except Exception as e:
        print(f"[FAIL] Generative UI 引擎测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_deerflow_integration():
    """测试 DeerFlow 集成"""
    print("\n" + "=" * 60)
    print("测试 DeerFlow 集成")
    print("=" * 60)

    try:
        from agents.deerflow_client import DEERFLOW_VERSION, get_deerflow_client

        print(f"  - DeerFlow 版本：{DEERFLOW_VERSION}")

        client = get_deerflow_client()
        available = client.is_available()

        if available:
            print("  - DeerFlow 服务：可用")
        else:
            print("  - DeerFlow 服务：不可用 (将使用本地降级模式)")

        return True
    except Exception as e:
        print(f"[FAIL] DeerFlow 集成测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


async def run_async_tests():
    """运行异步测试"""
    print("\n" + "=" * 60)
    print("运行异步测试")
    print("=" * 60)

    results = []
    results.append(("工作流执行", await test_workflow_execution()))

    return results


def main():
    """运行所有测试"""
    print("\n" + "#" * 60)
    print("# AI Code Understanding - AI Native 集成测试")
    print("# " + "-" * 56)
    print("# 测试 DeerFlow 2.0 架构集成")
    print("#" * 60)

    results = []

    # 同步测试
    results.append(("Agents 层", test_agents()))
    results.append(("Tools 层", test_tools()))
    results.append(("Workflows 层", test_workflows()))
    results.append(("API 路由", test_api_routes()))
    results.append(("Generative UI", test_generative_ui_engine()))
    results.append(("DeerFlow 集成", test_deerflow_integration()))

    # 异步测试
    async_results = asyncio.run(run_async_tests())
    results.extend(async_results)

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\n总计：{passed}/{total} 测试通过")

    if passed == total:
        print("\n[SUCCESS] AI Native 集成测试全部通过!")
        print("\nAI Native 转型完成，核心能力:")
        print("  1. DeerFlow 2.0 Agent 框架集成")
        print("  2. Tools 注册表与工作流编排")
        print("  3. 对话式 API (支持流式输出)")
        print("  4. Generative UI 动态视图生成")
        print("  5. 本地降级模式支持")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
