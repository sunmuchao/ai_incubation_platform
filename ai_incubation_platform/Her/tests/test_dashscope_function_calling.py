"""测试 DashScope GLM-5 是否支持 OpenAI function calling"""

import os
import json
import requests

# 从环境变量获取 API key
api_key = os.environ.get('OPENAI_API_KEY', '')
if not api_key:
    print('ERROR: OPENAI_API_KEY not set')
    exit(1)

# 定义一个简单的工具
tool_definition = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如北京、上海"
                }
            },
            "required": ["city"]
        }
    }
}

# 构建请求
url = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "glm-5",
    "messages": [
        {"role": "user", "content": "北京今天天气怎么样？请使用工具查询。"}
    ],
    "tools": [tool_definition],
    "tool_choice": "auto"
}

print("=" * 60)
print("测试 DashScope GLM-5 Function Calling 支持")
print("=" * 60)
print(f"URL: {url}")
print(f"Model: glm-5")
print(f"Tools: {json.dumps(tool_definition, indent=2, ensure_ascii=False)}")
print()

# 发送请求
try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("Response JSON:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 检查是否有 tool_calls
        message = result.get("choices", [{}])[0].get("message", {})
        tool_calls = message.get("tool_calls")

        print()
        print("=" * 60)
        if tool_calls:
            print("✅ GLM-5 支持 Function Calling!")
            print(f"Tool calls: {json.dumps(tool_calls, indent=2, ensure_ascii=False)}")
        else:
            print("❌ GLM-5 未调用工具（可能不支持 function calling 或工具参数被忽略）")
            print(f"Message content: {message.get('content', '')[:200]}")
    else:
        print(f"Error Response: {response.text}")

except Exception as e:
    print(f"Request failed: {type(e).__name__}: {e}")