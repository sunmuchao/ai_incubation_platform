"""
AI Native 功能测试脚本

测试用例：
1. 自然语言发布任务
2. 智能匹配工人
3. 对话式交互
4. 审计日志记录
"""
import asyncio
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_intent_parsing():
    """测试意图解析"""
    print("\n=== 测试 1: 意图解析 ===")
    from agents.task_agent import task_agent

    test_cases = [
        "帮我发布一个线下采集任务，需要到北京现场拍照，报酬 200 元",
        "找一个会数据标注的工人，评分要高",
        "查询任务 task-123 的状态",
        "为任务匹配最合适的工人",
    ]

    for text in test_cases:
        print(f"\n输入：{text}")
        result = await task_agent.parse_intent(text)
        print(f"解析结果：技能={result.get('required_skills')}, 类型={result.get('interaction_type')}, "
              f"优先级={result.get('priority')}, 地点={result.get('location_hint')}")


async def test_task_tools():
    """测试任务工具"""
    print("\n=== 测试 2: 任务工具 ===")
    from tools.task_tools import post_task, get_task, search_tasks

    # 发布任务
    print("\n发布测试任务...")
    result = await post_task(
        ai_employer_id="test_ai_001",
        title="测试任务 - 数据标注",
        description="这是一个测试任务，需要进行数据标注工作",
        capability_gap="AI 无法准确判断某些边界情况，需要人工标注",
        interaction_type="digital",
        required_skills={"数据标注": "中级"},
        priority="medium",
        reward_amount=100.0
    )
    print(f"发布结果：{result}")

    task_id = result.get("task_id")
    if task_id:
        # 获取任务
        print(f"\n获取任务 {task_id}...")
        task_result = await get_task(task_id)
        print(f"任务详情：{task_result}")

        # 搜索任务
        print("\n搜索任务...")
        search_result = await search_tasks(keyword="数据标注")
        print(f"搜索结果：找到 {len(search_result.get('tasks', []))} 个任务")


async def test_worker_tools():
    """测试工人工具"""
    print("\n=== 测试 3: 工人工具 ===")
    from tools.worker_tools import search_workers, get_worker_stats

    # 搜索工人
    print("\n搜索工人...")
    result = await search_workers(
        skills="数据标注",
        min_rating=4.0,
        limit=5
    )
    print(f"找到 {len(result.get('workers', []))} 个工人")

    # 获取统计
    print("\n获取平台统计...")
    stats = await get_worker_stats()
    print(f"平台统计：{stats}")


async def test_matching():
    """测试匹配功能"""
    print("\n=== 测试 4: 智能匹配 ===")
    from tools.task_tools import search_tasks
    from tools.worker_tools import match_workers

    # 获取一个任务
    tasks_result = await search_tasks(limit=1)
    tasks = tasks_result.get("tasks", [])

    if tasks:
        task_id = tasks[0]["id"]
        print(f"\n为任务 {task_id} 匹配工人...")
        match_result = await match_workers(task_id=task_id, limit=5)
        print(f"匹配结果：{len(match_result.get('matches', []))} 个候选")

        for match in match_result.get("matches", [])[:3]:
            print(f"  - {match.get('worker_name')}: 匹配度 {match.get('confidence', 0)*100:.0f}%")


async def test_verification_tools():
    """测试验证工具"""
    print("\n=== 测试 5: 验证工具 ===")
    from tools.verification_tools import verify_delivery, get_quality_score

    # 模拟验证交付物
    print("\n验证交付物...")
    result = await verify_delivery(
        task_id="nonexistent",  # 使用不存在的任务 ID 测试错误处理
        content="这是交付内容"
    )
    print(f"验证结果：{result}")


async def test_workflow():
    """测试工作流"""
    print("\n=== 测试 6: 工作流 ===")
    from workflows.task_workflows import AutoPostAndMatchWorkflow

    workflow = AutoPostAndMatchWorkflow()

    print("\n执行自主发布和匹配工作流...")
    result = await workflow.execute(
        natural_language="发布一个紧急的线下采集任务，需要到上海现场",
        user_id="test_user_001"
    )
    print(f"工作流结果：{result}")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("AI Hires Human - AI Native 功能测试")
    print("=" * 60)

    try:
        await test_intent_parsing()
        await test_task_tools()
        await test_worker_tools()
        await test_matching()
        await test_verification_tools()
        # await test_workflow()  # 工作流测试可能需要数据库支持

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
