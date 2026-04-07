"""
Portal Agent AI Native 功能测试

测试 PortalAgent 的核心 AI Native 能力：
1. 意图识别
2. 路由分发
3. 跨项目工作流编排
4. 对话式交互
"""
import asyncio
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# 添加 src 到路径
import sys
sys.path.insert(0, "/Users/sunmuchao/Downloads/ai_incubation_platform/platform-portal/src")


async def test_intent_recognition():
    """测试意图识别功能"""
    print("\n" + "=" * 60)
    print("测试 1: 意图识别功能")
    print("=" * 60)

    from tools.intent_tools import identify_intent

    test_cases = [
        ("我想发布一个线下数据采集任务", "ai-hires-human"),
        ("帮我分析一下这个代码仓库的质量", "ai-code-understanding"),
        ("我们社区需要增加活跃度", "human-ai-community"),
        ("有什么好的创业机会推荐吗", "ai-opportunity-miner"),
        ("我想组织一个团购活动", "ai-community-buying"),
        ("帮我优化一下系统性能", "ai-runtime-optimizer"),
        ("不知道怎么创业，需要全方位帮助", "platform-portal"),  # 应该触发工作流
    ]

    for user_input, expected_project in test_cases:
        result = await identify_intent(user_input)
        detected = result.get("project", "unknown")
        confidence = result.get("confidence", 0)

        status = "PASS" if detected == expected_project or (expected_project == "platform-portal" and detected in ["platform-portal"]) else "FAIL"

        print(f"\n输入：{user_input}")
        print(f"期望：{expected_project}, 检测到：{detected} (置信度：{confidence:.2f}) - {status}")


async def test_portal_agent_chat():
    """测试 PortalAgent 对话功能"""
    print("\n" + "=" * 60)
    print("测试 2: PortalAgent 对话功能")
    print("=" * 60)

    from agents.portal_agent import PortalAgent

    agent = PortalAgent()

    test_messages = [
        "你好，我想了解一下这个平台都有哪些项目",
        "我需要找人做线下数据采集",
        "我想创业，有什么可以帮助我的",
        "帮我分析一下代码性能",
    ]

    for message in test_messages:
        print(f"\n用户：{message}")

        result = await agent.chat(
            message=message,
            user_id="test_user_001",
            session_id="test_session_001",
        )

        print(f"行动：{result.get('action')}")
        print(f"项目：{result.get('project')}")
        print(f"置信度：{result.get('confidence', 0):.2f}")
        print(f"响应类型：{result.get('response', {}).get('type', 'unknown')}")


async def test_cross_project_workflow():
    """测试跨项目工作流"""
    print("\n" + "=" * 60)
    print("测试 3: 跨项目工作流")
    print("=" * 60)

    from agents.portal_agent import WORKFLOW_TEMPLATES

    print("\n可用工作流模板:")
    for name, template in WORKFLOW_TEMPLATES.items():
        print(f"\n- {name}: {template.get('description', 'N/A')}")
        print(f"  参与项目：{', '.join(template.get('projects', []))}")
        print(f"  工作流步骤:")
        for step in template.get("workflow", []):
            print(f"    {step['step']}. {step['project']}: {step['action']}")


async def test_tools_registry():
    """测试工具注册表"""
    print("\n" + "=" * 60)
    print("测试 4: 工具注册表")
    print("=" * 60)

    from tools.registry import list_tools, get_tool, TOOLS_REGISTRY

    print("\n已注册工具:")
    tools = list_tools()
    for tool in tools:
        print(f"- {tool['name']}: {tool['description']}")

    # 测试获取工具详情
    print("\n工具详情示例 (identify_intent):")
    tool = get_tool("identify_intent")
    print(f"名称：{tool['name']}")
    print(f"描述：{tool['description']}")
    print(f"输入 Schema: {tool['input_schema']}")


async def test_routing_tools():
    """测试路由工具"""
    print("\n" + "=" * 60)
    print("测试 5: 路由工具")
    print("=" * 60)

    from tools.routing_tools import route_to_project, aggregate_results

    # 测试路由（模拟）
    print("\n测试路由到 ai-hires-human:")
    result = await route_to_project(
        project="ai-hires-human",
        payload={"message": "测试消息", "user_id": "test_user"},
    )
    print(f"结果：{result}")

    # 测试聚合
    print("\n测试结果聚合:")
    mock_results = [
        {"project": "ai-hires-human", "success": True, "data": {"task_id": "123"}},
        {"project": "ai-employee-platform", "success": True, "data": {"match_score": 0.9}},
        {"project": "unknown", "success": False, "error": "Project not found"},
    ]

    merged = await aggregate_results(mock_results, aggregation_mode="merge")
    print(f"合并模式：{merged}")

    selected = await aggregate_results(mock_results, aggregation_mode="select_best")
    print(f"选择最佳：{selected}")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("AI Incubation Platform - Portal Agent AI Native 测试")
    print(f"执行时间：{datetime.now().isoformat()}")
    print("=" * 60)

    try:
        await test_intent_recognition()
        await test_portal_agent_chat()
        await test_cross_project_workflow()
        await test_tools_registry()
        await test_routing_tools()

        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
