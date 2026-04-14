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
    """
    获取 LLM 配置

    🔧 [统一配置] 优先从 DeerFlow config.yaml 读取，实现单一真相来源。
    这样只需维护 deerflow/.env + deerflow/config.yaml 一处配置。
    """
    # 方式1：从 DeerFlow config.yaml 读取（优先）
    try:
        import os
        import yaml
        her_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        deerflow_config_path = os.path.join(her_root, "deerflow", "config.yaml")

        if os.path.exists(deerflow_config_path):
            with open(deerflow_config_path, "r") as f:
                config = yaml.safe_load(f)

            # 获取第一个模型配置（默认模型）
            models = config.get("models", [])
            if models:
                model_config = models[0]
                # 解析环境变量引用（如 $OPENAI_API_KEY）
                api_key = model_config.get("api_key", "")
                if api_key.startswith("$"):
                    env_var = api_key[1:]
                    api_key = os.getenv(env_var, "")

                base_url = model_config.get("base_url", "")
                if base_url.startswith("$"):
                    env_var = base_url[1:]
                    base_url = os.getenv(env_var, "")

                return {
                    "api_key": api_key,
                    "api_base": base_url,
                    "model": model_config.get("model", ""),
                    "provider": "dashscope" if "dashscope" in base_url else "volces" if "volces" in base_url else "openai",
                    "max_completion_tokens": model_config.get("max_tokens", 4096),
                    "reasoning_effort": model_config.get("extra_body", {}).get("reasoning_effort", "medium"),
                    "temperature": model_config.get("temperature", 0.7),
                    "max_tokens": model_config.get("max_tokens", 4096),
                }
    except Exception as e:
        logger.warning(f"[LLM Config] Failed to read DeerFlow config: {e}")

    # 方式2：从 config.py settings 读取（降级）
    try:
        from config import settings
        return {
            "api_key": settings.llm_api_key,
            "api_base": settings.llm_api_base,
            "model": settings.llm_model,
            "provider": settings.llm_provider,
            "max_completion_tokens": settings.llm_max_completion_tokens,
            "reasoning_effort": settings.llm_reasoning_effort,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }
    except ImportError:
        pass

    # 方式3：直接读取环境变量（最终降级）
    api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("LLM_API_KEY", "")
    api_base = os.getenv("OPENAI_API_BASE", "") or os.getenv("LLM_API_BASE", "")
    model = os.getenv("OPENAI_MODEL", "") or os.getenv("LLM_MODEL", "doubao-1-5-pro-32k-250115")
    provider = os.getenv("LLM_PROVIDER", "volces")

    return {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
        "provider": provider,
        "max_completion_tokens": int(os.getenv("LLM_MAX_COMPLETION_TOKENS", "65535")),
        "reasoning_effort": os.getenv("LLM_REASONING_EFFORT", "medium"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1000")),
    }


def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: int = 60,  # 🔧 [修复] 默认超时从 30 秒增加到 60 秒，适配深度推理模型
    **kwargs
) -> str:
    """
    调用 LLM 生成回复

    Args:
        prompt: 用户提示
        system_prompt: 系统提示（可选）
        temperature: 温度参数（0-1）
        max_tokens: 最大 token 数
        timeout: 超时时间（秒）- 默认 60 秒，推理模型建议 90-120 秒
        **kwargs: 其他参数

    Returns:
        LLM 生成的文本回复
    """
    config = get_llm_config()

    if not config["api_key"]:
        logger.error("LLM API key not configured")
        return "抱歉，我现在无法思考，请稍后再试～"

    # 🔧 [新增] 根据模型类型调整超时时间
    # 深度推理模型（doubao-seed、Kimi K2.5）需要更长超时
    model_name = config.get("model", "")
    if "seed" in model_name or "kimi" in model_name.lower():
        timeout = max(timeout, 90)  # 推理模型至少 90 秒
        logger.debug(f"[LLM] Using extended timeout={timeout}s for reasoning model: {model_name}")

    # 构建消息
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    # 调用 LLM
    try:
        if OPENAI_AVAILABLE and config["api_base"]:
            # 使用 OpenAI SDK（兼容 DashScope、火山引擎等）
            client = OpenAI(
                api_key=config["api_key"],
                base_url=config["api_base"],
                timeout=timeout,
            )

            # 根据 provider 构建不同的参数
            payload_kwargs = {
                "model": config["model"],
                "messages": messages,
                "temperature": temperature,
            }

            # 火山引擎豆包模型使用特殊参数
            if config.get("provider") == "volces" or "doubao" in config["model"]:
                payload_kwargs["max_completion_tokens"] = config.get("max_completion_tokens", max_tokens)
                payload_kwargs["reasoning_effort"] = config.get("reasoning_effort", "medium")
            else:
                payload_kwargs["max_tokens"] = max_tokens

            # 合并额外参数
            payload_kwargs.update(kwargs)

            response = client.chat.completions.create(**payload_kwargs)

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
            }

            # 火山引擎豆包模型使用特殊参数
            if config.get("provider") == "volces" or "doubao" in config["model"]:
                payload["max_completion_tokens"] = config.get("max_completion_tokens", max_tokens)
                payload["reasoning_effort"] = config.get("reasoning_effort", "medium")
            else:
                payload["max_tokens"] = max_tokens

            resp = requests.post(
                f"{config['api_base']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,  # 🔧 [修复] 使用函数参数中的 timeout（已根据模型类型调整）
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

            # 根据 provider 构建不同的参数
            payload_kwargs = {
                "model": config["model"],
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }

            # 火山引擎豆包模型使用特殊参数
            if config.get("provider") == "volces" or "doubao" in config["model"]:
                payload_kwargs["max_completion_tokens"] = config.get("max_completion_tokens", max_tokens)
                payload_kwargs["reasoning_effort"] = config.get("reasoning_effort", "medium")
            else:
                payload_kwargs["max_tokens"] = max_tokens

            payload_kwargs.update(kwargs)

            response = client.chat.completions.create(**payload_kwargs)

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
            }

            # 火山引擎豆包模型使用特殊参数
            if config.get("provider") == "volces" or "doubao" in config["model"]:
                payload["max_completion_tokens"] = config.get("max_completion_tokens", max_tokens)
                payload["reasoning_effort"] = config.get("reasoning_effort", "medium")
            else:
                payload["max_tokens"] = max_tokens

            resp = requests.post(
                f"{config['api_base']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,  # 🔧 [修复] 使用函数参数中的 timeout（已根据模型类型调整）
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
                "stream": True,
            }

            # 火山引擎豆包模型使用特殊参数
            if config.get("provider") == "volces" or "doubao" in config["model"]:
                payload["max_completion_tokens"] = config.get("max_completion_tokens", max_tokens)
                payload["reasoning_effort"] = config.get("reasoning_effort", "medium")
            else:
                payload["max_tokens"] = max_tokens

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
    logger.info("Testing LLM client...")
    response = call_llm("你好，请做一个简单的自我介绍。")
    logger.info(f"Response: {response}")
