"""
修复验证测试脚本

验证三个修复点：
1. 意图预分类层已关闭
2. her_create_profile 工具可用
3. SOUL.md 包含用户不存在时的处理策略
"""
import sys
import os

# 添加路径（从 Her 根目录运行）
her_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(her_root, 'src'))
sys.path.insert(0, os.path.join(her_root, 'deerflow', 'backend', 'packages', 'harness'))

def test_intent_router_disabled():
    """验证意图预分类层已删除"""
    print("\n=== 测试 1: 意图预分类层状态 ===")

    # 检查 ENABLE_INTENT_ROUTER 是否存在
    try:
        from api.deerflow import ENABLE_INTENT_ROUTER
        print(f"ENABLE_INTENT_ROUTER = {ENABLE_INTENT_ROUTER}")
        print("❌ 失败: ENABLE_INTENT_ROUTER 配置仍然存在")
        return False
    except ImportError:
        print("✅ ENABLE_INTENT_ROUTER 已删除")

    # 检查 _classify_intent_for_tool_routing 是否存在
    try:
        from api.deerflow import _classify_intent_for_tool_routing
        print("❌ 失败: _classify_intent_for_tool_routing 函数仍然存在")
        return False
    except ImportError:
        print("✅ _classify_intent_for_tool_routing 已删除")

    # 检查 _apply_intent_router 是否存在
    try:
        from api.deerflow import _apply_intent_router
        print("❌ 失败: _apply_intent_router 函数仍然存在")
        return False
    except ImportError:
        print("✅ _apply_intent_router 已删除")

    print("✅ 成功: 意图预分类层所有代码已删除（符合 Agent Native 原则）")
    return True


def test_her_create_profile_tool():
    """验证 her_create_profile 工具可用"""
    from deerflow.community.her_tools import HER_TOOLS, her_create_profile_tool

    print("\n=== 测试 2: her_create_profile 工具 ===")

    # 检查工具列表
    tool_names = [t.name for t in HER_TOOLS]
    print(f"工具列表: {tool_names}")

    if 'her_create_profile' not in tool_names:
        print("❌ 失败: her_create_profile 不在工具列表中")
        return False

    # 检查工具实例
    print(f"工具名称: {her_create_profile_tool.name}")
    print(f"工具描述: {her_create_profile_tool.description[:100]}...")

    print("✅ 成功: her_create_profile 工具可用")
    return True


def test_soul_md_content():
    """验证 SOUL.md 包含用户不存在时的处理策略"""
    soul_md_path = os.path.join(her_root, 'deerflow', 'backend', '.deer-flow', 'SOUL.md')

    print("\n=== 测试 3: SOUL.md 内容 ===")
    print(f"路径: {soul_md_path}")

    if not os.path.exists(soul_md_path):
        print("❌ 失败: SOUL.md 文件不存在")
        return False

    with open(soul_md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查关键内容
    checks = [
        ("用户不存在时的处理策略", "用户不存在" in content),
        ("工具使用指南", "her_get_profile" in content),
        ("安全边界", "安全边界" in content),
    ]

    all_passed = True
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}: {check_result}")
        if not check_result:
            all_passed = False

    if all_passed:
        print("✅ 成功: SOUL.md 包含所有必要内容")
        return True
    else:
        print("❌ 失败: SOUL.md 缺少必要内容")
        return False


def test_config_yaml():
    """验证 config.yaml 包含 her_create_profile 工具配置"""
    config_path = os.path.join(her_root, 'deerflow', 'config.yaml')

    print("\n=== 测试 4: config.yaml 工具配置 ===")
    print(f"路径: {config_path}")

    if not os.path.exists(config_path):
        print("❌ 失败: config.yaml 文件不存在")
        return False

    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查工具配置
    if 'her_create_profile' in content:
        print("✅ 成功: config.yaml 包含 her_create_profile 工具配置")
        return True
    else:
        print("❌ 失败: config.yaml 不包含 her_create_profile 工具配置")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("修复验证测试")
    print("=" * 60)

    results = []
    results.append(("意图预分类层已关闭", test_intent_router_disabled()))
    results.append(("her_create_profile 工具可用", test_her_create_profile_tool()))
    results.append(("SOUL.md 包含必要内容", test_soul_md_content()))
    results.append(("config.yaml 包含工具配置", test_config_yaml()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有修复验证通过！")
        return 0
    else:
        print("\n⚠️ 部分修复验证失败，请检查")
        return 1


if __name__ == "__main__":
    exit(main())