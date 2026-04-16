"""
测试 GLM-5 的 Function Calling 能力

验证：
1. GLM-5 是否支持 OpenAI 格式的 tools 参数
2. GLM-5 是否能正确返回 tool_calls
"""
import os
import json
import sys

# 设置工作目录
os.chdir("/Users/sunmuchao/Downloads/ai_incubation_platform/Her")

# 加载环境变量（deerflow/.env）
deerflow_env_path = os.path.join(os.getcwd(), "deerflow", ".env")
if os.path.exists(deerflow_env_path):
    with open(deerflow_env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value  # 强制设置，不检查是否已存在
    print(f"✅ 已加载环境变量: {deerflow_env_path}")
    print(f"   OPENAI_API_KEY: {os.environ.get('OPENAI_API_KEY', '')[:20]}...")
    print(f"   OPENAI_API_BASE: {os.environ.get('OPENAI_API_BASE', '')}")
else:
    print(f"❌ 未找到环境变量文件: {deerflow_env_path}")

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "deerflow", "backend", "packages", "harness"))

# 测试 OpenAI 客户端直接调用 GLM-5
def test_glm5_function_calling():
    """测试 GLM-5 是否支持 function calling"""
    print("\n" + "="*60)
    print("测试 1: GLM-5 Function Calling 能力")
    print("="*60)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_API_BASE", "https://coding.dashscope.aliyuncs.com/v1"),
        )

        # 定义一个简单的工具
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定城市的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名称"
                            }
                        },
                        "required": ["city"]
                    }
                }
            }
        ]

        # 测试调用
        response = client.chat.completions.create(
            model="glm-5",  # GLM-5
            messages=[
                {"role": "user", "content": "北京今天天气怎么样？"}
            ],
            tools=tools,
            tool_choice="auto"
        )

        # 检查响应
        message = response.choices[0].message

        print(f"\n模型响应:")
        print(f"  content: {message.content}")
        print(f"  tool_calls: {message.tool_calls}")

        if message.tool_calls:
            print(f"\n✅ GLM-5 支持 Function Calling!")
            print(f"  调用的工具: {message.tool_calls[0].function.name}")
            print(f"  参数: {message.tool_calls[0].function.arguments}")
            return True
        else:
            print(f"\n❌ GLM-5 没有返回 tool_calls，只返回了文本")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {type(e).__name__}: {e}")
        return False


# 测试 DeerFlow 工具加载
def test_deerflow_tools_loading():
    """测试 DeerFlow 是否正确加载 her_tools"""
    print("\n" + "="*60)
    print("测试 2: DeerFlow 工具加载")
    print("="*60)

    try:
        from deerflow.config.app_config import reload_app_config
        from deerflow.tools import get_available_tools

        # 加载配置
        config_path = os.path.join(os.getcwd(), "deerflow", "config.yaml")
        reload_app_config(config_path)

        # 获取工具
        tools = get_available_tools()

        print(f"\n加载的工具数量: {len(tools)}")
        print(f"\n工具列表:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:50] if tool.description else 'N/A'}...")

        # 检查 her_tools 是否存在
        her_tools = [t for t in tools if t.name.startswith("her_")]
        print(f"\nHer Tools 数量: {len(her_tools)}")

        if her_tools:
            print(f"✅ Her Tools 已正确加载")
            return True
        else:
            print(f"❌ Her Tools 未加载")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


# 测试 DeerFlow Agent 调用
def test_deerflow_agent_chat():
    """测试 DeerFlow Agent 是否能调用工具"""
    print("\n" + "="*60)
    print("测试 3: DeerFlow Agent 工具调用")
    print("="*60)

    try:
        from deerflow.client import DeerFlowClient
        from deerflow.config.app_config import reload_app_config

        # 加载配置
        config_path = os.path.join(os.getcwd(), "deerflow", "config.yaml")
        reload_app_config(config_path)

        # 创建客户端
        client = DeerFlowClient(config_path=config_path)

        # 测试调用
        print(f"\n发送消息: '帮我找一个合适的对象'")
        response = client.chat("帮我找一个合适的对象", thread_id="test-thread-debug")

        print(f"\nAgent 响应 (前 1000 字):")
        print(f"  {response[:1000]}")

        # 检查是否包含匹配结果（说明工具被调用）
        success_indicators = ["找到", "匹配", "候选", "推荐", "岁", "城市", "兴趣"]
        matched = [ind for ind in success_indicators if ind in response]

        if matched:
            print(f"\n✅ Agent 可能调用了工具（响应包含: {matched}）")
            return True
        else:
            print(f"\n❌ Agent 可能没有调用工具（响应是纯文本，无匹配关键词）")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 测试 1: GLM-5 Function Calling
    glm5_supports_fc = test_glm5_function_calling()

    # 测试 2: DeerFlow 工具加载
    tools_loaded = test_deerflow_tools_loading()

    # 测试 3: DeerFlow Agent 调用
    if glm5_supports_fc and tools_loaded:
        agent_ok = test_deerflow_agent_chat()
    else:
        print("\n跳过测试 3（前置测试失败）")
        agent_ok = False

    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"GLM-5 Function Calling: {'✅ 支持' if glm5_supports_fc else '❌ 不支持'}")
    print(f"DeerFlow 工具加载: {'✅ 成功' if tools_loaded else '❌ 失败'}")
    print(f"DeerFlow Agent 工具调用: {'✅ 成功' if agent_ok else '❌ 失败'}")
    print("="*60)