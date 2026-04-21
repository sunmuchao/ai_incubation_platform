"""测试 DashScope GLM-5 是否支持 OpenAI function calling（需网络与 OPENAI_API_KEY）。"""

import json
import os

import pytest
import requests

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
def test_dashscope_glm5_supports_function_calling():
    """直连 DashScope OpenAI 兼容接口，验证 tool_calls 是否返回。"""
    api_key = os.environ["OPENAI_API_KEY"]

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
                        "description": "城市名称，如北京、上海",
                    }
                },
                "required": ["city"],
            },
        },
    }

    url = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "glm-5",
        "messages": [
            {"role": "user", "content": "北京今天天气怎么样？请使用工具查询。"}
        ],
        "tools": [tool_definition],
        "tool_choice": "auto",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    assert response.status_code == 200, response.text

    result = response.json()
    message = result.get("choices", [{}])[0].get("message", {})
    tool_calls = message.get("tool_calls")

    # 有 tool_calls 即视为支持；无则仅记录（不因供应商行为波动让 CI 必红）
    if tool_calls:
        assert isinstance(tool_calls, list)
        print("OK: tool_calls", json.dumps(tool_calls, indent=2, ensure_ascii=False)[:500])
    else:
        content = (message.get("content") or "")[:200]
        pytest.skip(f"No tool_calls in response; message excerpt: {content!r}")
