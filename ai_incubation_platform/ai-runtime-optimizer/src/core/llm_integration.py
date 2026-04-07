"""
LLM 集成模块：支持可选的大模型增强分析与代码生成
支持提供商：Mock, OpenAI, Claude (Anthropic)
"""
from typing import Any, Dict, List, Optional
import json
import time
from abc import ABC, abstractmethod

from core.audit import audit_logger, AuditEventType, AuditStatus


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    def analyze(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """执行分析请求"""
        pass

    @abstractmethod
    def generate_code(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """执行代码生成请求"""
        pass


class MockLLMClient(BaseLLMClient):
    """Mock LLM 客户端，用于演示和测试"""

    def analyze(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Mock 分析响应"""
        return (
            "基于提供的指标和使用数据，分析结论：\n"
            "1. 系统当前存在性能瓶颈，主要集中在热点路由\n"
            "2. 错误率升高可能与最近的版本发布有关\n"
            "3. 建议优先优化高流量路由的缓存策略\n"
        )

    def generate_code(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Mock 代码生成响应"""
        return (
            "# 自动生成的优化代码示例\n"
            "# 基于分析结果：热点路由缓存优化\n"
            "@cache(ttl=60)\n"
            "async def get_order_details(order_id: str):\n"
            "    # 优先从缓存获取\n"
            "    cached = await redis.get(f\"order:{order_id}\")\n"
            "    if cached:\n"
            "        return json.loads(cached)\n"
            "    \n"
            "    # 回源查询数据库\n"
            "    result = await db.query(\"SELECT * FROM orders WHERE id = :id\", {\"id\": order_id})\n"
            "    \n"
            "    # 写入缓存\n"
            "    await redis.setex(f\"order:{order_id}\", 60, json.dumps(result))\n"
            "    \n"
            "    return result\n"
        )


class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM 客户端实现"""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            raise RuntimeError("openai package is required for OpenAI integration")

    def analyze(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """使用 OpenAI 执行分析"""
        messages = [
            {"role": "system", "content": "你是一个专业的系统性能分析专家，需要根据提供的运行时指标和用户使用数据给出可执行的优化建议。"},
            {"role": "user", "content": prompt}
        ]

        if context:
            messages.append({
                "role": "user",
                "content": f"上下文数据：{json.dumps(context, ensure_ascii=False, indent=2)}"
            })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3
        )

        return response.choices[0].message.content or ""

    def generate_code(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """使用 OpenAI 生成代码"""
        messages = [
            {"role": "system", "content": "你是一个资深的软件工程师，需要根据性能分析结果生成高质量的优化代码。代码需要符合最佳实践，带有必要的注释。"},
            {"role": "user", "content": prompt}
        ]

        if context:
            messages.append({
                "role": "user",
                "content": f"上下文数据：{json.dumps(context, ensure_ascii=False, indent=2)}"
            })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2
        )

        return response.choices[0].message.content or ""


class ClaudeLLMClient(BaseLLMClient):
    """Claude (Anthropic) LLM 客户端实现"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
        except ImportError:
            raise RuntimeError("anthropic package is required for Claude integration")

    def analyze(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """使用 Claude 执行分析"""
        system_prompt = "你是一个专业的系统性能分析专家，需要根据提供的运行时指标和用户使用数据给出可执行的优化建议。请用简洁、结构化的方式输出分析结果。"

        user_message = prompt
        if context:
            user_message += f"\n\n上下文数据：{json.dumps(context, ensure_ascii=False, indent=2)}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        return response.content[0].text if response.content else ""

    def generate_code(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """使用 Claude 生成代码"""
        system_prompt = "你是一个资深的软件工程师，需要根据性能分析结果生成高质量的优化代码。代码需要符合最佳实践，带有必要的注释。只输出代码，不要多余的说明。"

        user_message = prompt
        if context:
            user_message += f"\n\n上下文数据：{json.dumps(context, ensure_ascii=False, indent=2)}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        return response.content[0].text if response.content else ""


class LLMIntegration:
    """LLM 集成管理器"""

    def __init__(self):
        self._client: Optional[BaseLLMClient] = None
        self._enabled = False
        self._config: Dict[str, Any] = {}

    def configure(self, provider: str = "mock", **kwargs) -> None:
        """配置 LLM 客户端

        Args:
            provider: LLM 提供商，支持 "mock", "openai", "claude"
            kwargs: 提供商特定参数，如 api_key, model 等
        """
        self._config = {"provider": provider, **kwargs}

        if provider == "mock":
            self._client = MockLLMClient()
        elif provider == "openai":
            api_key = kwargs.get("api_key")
            model = kwargs.get("model", "gpt-4")
            if not api_key:
                raise ValueError("OpenAI API key is required")
            self._client = OpenAILLMClient(api_key, model)
        elif provider == "claude":
            api_key = kwargs.get("api_key")
            model = kwargs.get("model", "claude-sonnet-4-20250514")
            if not api_key:
                raise ValueError("Claude API key is required")
            self._client = ClaudeLLMClient(api_key, model)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        self._enabled = True

    @property
    def enabled(self) -> bool:
        """LLM 是否已启用"""
        return self._enabled and self._client is not None

    def enhance_analysis(self, snapshot: Dict[str, Any], usage: Optional[Dict[str, Any]] = None,
                        suggestions: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """使用 LLM 增强分析结果"""
        if not self.enabled:
            return None

        prompt = "请基于以下系统运行数据进行深入分析，并给出可执行的优化建议：\n"
        prompt += f"运行时指标：{json.dumps(snapshot, ensure_ascii=False, indent=2)}\n"

        if usage:
            prompt += f"\n用户使用数据：{json.dumps(usage, ensure_ascii=False, indent=2)}\n"

        if suggestions:
            prompt += f"\n已有的规则分析建议：{json.dumps(suggestions, ensure_ascii=False, indent=2)}\n"

        prompt += "\n请给出更深入的根因分析和针对性的优化建议。"

        try:
            return self._client.analyze(prompt, context={"snapshot": snapshot, "usage": usage, "suggestions": suggestions})
        except Exception as e:
            # LLM 调用失败时不影响主流程
            return f"LLM 分析失败：{str(e)}"

    def generate_code_patch(self, suggestion: Dict[str, Any], context: Dict[str, Any]) -> Optional[str]:
        """使用 LLM 生成代码补丁"""
        if not self.enabled:
            return None

        prompt = f"请根据以下优化建议生成对应的代码补丁：\n"
        prompt += f"建议类型：{suggestion.get('type')}\n"
        prompt += f"建议内容：{suggestion.get('action')}\n"
        prompt += f"证据数据：{json.dumps(suggestion.get('evidence', {}), ensure_ascii=False, indent=2)}\n"
        prompt += f"上下文信息：{json.dumps(context, ensure_ascii=False, indent=2)}\n"
        prompt += "\n请生成可直接使用的代码片段，包含必要的注释和说明。"

        try:
            return self._client.generate_code(prompt, context={"suggestion": suggestion, **context})
        except Exception as e:
            return f"代码生成失败：{str(e)}"


# 全局 LLM 集成实例
llm_integration = LLMIntegration()
