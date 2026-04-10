"""
LLM 客户端模块

封装大模型调用，支持多种 LLM 后端（OpenAI、DashScope、DeepSeek 等）
支持流式响应和同步调用
"""
import os
import json
import asyncio
from typing import Optional, Dict, Any, Generator, AsyncGenerator

from utils.logger import logger

# 尝试导入 OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK not available")


def get_llm_config() -> Dict[str, Any]:
    """获取 LLM 配置"""
    # 优先使用 LLM_* 环境变量（项目统一配置）
    api_key = os.getenv("LLM_API_KEY", "")
    api_base = os.getenv("LLM_API_BASE", "")
    model = os.getenv("LLM_MODEL", "kimi-k2.5")

    # 降级：使用 OPENAI_* 环境变量（兼容旧配置）
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_base:
        api_base = os.getenv("OPENAI_API_BASE", "")
    if not model or model == "kimi-k2.5":
        model = os.getenv("OPENAI_MODEL", model)

    return {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
    }


def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: int = 30,
    **kwargs
) -> str:
    """
    调用 LLM 生成回复

    Args:
        prompt: 用户提示
        system_prompt: 系统提示（可选）
        temperature: 温度参数（0-1）
        max_tokens: 最大 token 数
        timeout: 超时时间（秒）
        **kwargs: 其他参数

    Returns:
        LLM 生成的文本回复
    """
    config = get_llm_config()

    if not config["api_key"]:
        logger.error("LLM API key not configured")
        return "抱歉，我现在无法思考，请稍后再试～"

    # 构建消息
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    # 调用 LLM
    try:
        if OPENAI_AVAILABLE and config["api_base"]:
            # 使用 OpenAI SDK（兼容 DashScope 等）
            client = OpenAI(
                api_key=config["api_key"],
                base_url=config["api_base"],
                timeout=timeout,
            )

            response = client.chat.completions.create(
                model=config["model"],
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            content = response.choices[0].message.content
            logger.debug(f"LLM response: {content[:100]}...")
            return content.strip()
        else:
            # 降级：使用 requests 直接调用
            import requests

            headers = {
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": config["model"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            resp = requests.post(
                f"{config['api_base']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            logger.debug(f"LLM response: {content[:100]}...")
            return content.strip()

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise RuntimeError(f"LLM call failed: {e}") from e


def call_llm_stream(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    **kwargs
) -> Generator[str, None, None]:
    """
    调用 LLM 流式生成回复

    Args:
        prompt: 用户提示
        system_prompt: 系统提示（可选）
        temperature: 温度参数（0-1）
        max_tokens: 最大 token 数
        **kwargs: 其他参数

    Yields:
        LLM 生成的文本片段（逐字输出）
    """
    config = get_llm_config()

    if not config["api_key"]:
        logger.error("LLM API key not configured")
        yield "抱歉，我现在无法思考，请稍后再试～"
        return

    # 构建消息
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    # 调用 LLM（流式）
    try:
        if OPENAI_AVAILABLE and config["api_base"]:
            client = OpenAI(
                api_key=config["api_key"],
                base_url=config["api_base"],
            )

            response = client.chat.completions.create(
                model=config["model"],
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        else:
            # 降级：使用 requests 直接调用（不支持流式，直接返回完整内容）
            import requests

            headers = {
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": config["model"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            resp = requests.post(
                f"{config['api_base']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            yield content.strip()

    except Exception as e:
        logger.error(f"LLM stream call failed: {e}")
        yield "抱歉，我刚才走神了，你能再说一遍吗？😊"


async def call_llm_stream_async(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    异步流式调用 LLM（逐字输出）

    Args:
        prompt: 用户提示
        system_prompt: 系统提示（可选）
        temperature: 温度参数（0-1）
        max_tokens: 最大 token 数
        **kwargs: 其他参数

    Yields:
        LLM 生成的单个字符
    """
    config = get_llm_config()

    if not config["api_key"]:
        logger.error("LLM API key not configured")
        yield "抱歉，我现在无法思考，请稍后再试～"
        return

    # 构建消息
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        if OPENAI_AVAILABLE and config["api_base"]:
            import httpx

            headers = {
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": config["model"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{config['api_base']}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    # 使用 aiter_bytes 读取原始字节流，避免按行缓冲
                    buffer = ""
                    async for byte_chunk in response.aiter_bytes():
                        # 将字节转换为文本并累积
                        buffer += byte_chunk.decode("utf-8", errors="ignore")
                        # 处理 SSE 格式：每个事件以 \n\n 结尾
                        while "\n\n" in buffer:
                            event, buffer = buffer.split("\n\n", 1)
                            for line in event.split("\n"):
                                if line.startswith("data: "):
                                    data_str = line[6:]
                                    if data_str == "[DONE]":
                                        return
                                    try:
                                        data = json.loads(data_str)
                                        if data.get("choices") and data["choices"][0].get("delta", {}).get("content"):
                                            content = data["choices"][0]["delta"]["content"]
                                            # 逐字符 yield，实现真正的流式效果
                                            for char in content:
                                                yield char
                                    except json.JSONDecodeError:
                                        continue
        else:
            # 降级：同步调用后逐字输出
            result = call_llm(prompt, system_prompt, temperature, max_tokens, **kwargs)
            for char in result:
                yield char

    except Exception as e:
        logger.error(f"LLM async stream call failed: {e}")
        yield "抱歉，我刚才走神了，你能再说一遍吗？😊"


def analyze_text(
    text: str,
    analysis_type: str = "emotion",
    **kwargs
) -> Dict[str, Any]:
    """
    分析文本（情感/意图/关键词等）

    Args:
        text: 待分析文本
        analysis_type: 分析类型（emotion/intent/keywords）
        **kwargs: 其他参数

    Returns:
        分析结果字典
    """
    prompts = {
        "emotion": "请分析以下文本的情感倾向（积极/消极/中性），并给出 0-1 的置信度。返回 JSON: {\"emotion\": \"积极/消极/中性\", \"confidence\": 0.0}",
        "intent": "请分析以下文本的意图（陈述/疑问/请求/闲聊），返回 JSON: {\"intent\": \"类型\", \"confidence\": 0.0}",
        "keywords": "请从以下文本中提取 3-5 个关键词，返回 JSON: {\"keywords\": [\"词 1\", \"词 2\"]}",
    }

    system_prompt = prompts.get(analysis_type, "请分析以下文本：")

    try:
        response = call_llm(
            prompt=f"待分析文本：{text}",
            system_prompt=system_prompt,
            temperature=0.1,  # 分析任务用低温
        )

        # 尝试解析 JSON
        result = json.loads(response)
        return result
    except Exception as e:
        logger.error(f"Text analysis failed: {e}")
        return {"error": str(e)}


# 测试函数
if __name__ == "__main__":
    # 简单测试
    print("Testing LLM client...")
    response = call_llm("你好，请做一个简单的自我介绍。")
    print(f"Response: {response}")
