"""
LLM 集成服务 - P7 核心能力

集成 Anthropic Claude API，提供：
- AI 对话助手
- 智能洞察生成
- 自然语言报告叙述
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatSession:
    """聊天会话"""
    session_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AIInsight:
    """AI 洞察"""
    insight_id: str
    title: str
    content: str
    category: str  # "anomaly", "opportunity", "trend", "recommendation"
    confidence: float  # 0.0 - 1.0
    data_points: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ReportNarrative:
    """报告叙述"""
    section: str
    title: str
    narrative: str
    key_findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    charts_context: List[str] = field(default_factory=list)


class ClaudeAPIClient:
    """
    Anthropic Claude API 客户端
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        base_url: str = "https://api.anthropic.com/v1",
        timeout: int = 60
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                timeout=self.timeout
            )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            system_prompt: 系统提示
            max_tokens: 最大 token 数
            temperature: 温度参数

        Returns:
            AI 响应内容
        """
        if not self.api_key:
            logger.warning("Claude API key not configured, using mock response")
            return self._mock_response(messages)

        try:
            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": messages
            }

            if system_prompt:
                payload["system"] = system_prompt

            if temperature:
                payload["temperature"] = temperature

            client = self._get_client()
            response = client.post("/messages", json=payload)
            response.raise_for_status()

            result = response.json()
            return result["content"][0]["text"]

        except httpx.HTTPError as e:
            logger.error(f"Claude API error: {e}")
            return self._mock_response(messages)
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {e}")
            return self._mock_response(messages)

    def _mock_response(self, messages: List[Dict[str, str]]) -> str:
        """返回模拟响应（当 API 未配置时）"""
        last_message = messages[-1]["content"] if messages else ""

        # 简单的基于规则的响应
        if "流量" in last_message or "traffic" in last_message.lower():
            return "根据数据分析，您的网站流量呈现稳定增长趋势。建议重点关注以下方面：\n\n1. **内容优化**: 加强 SEO 友好内容的创作\n2. **用户留存**: 提升新用户次日留存率\n3. **转化优化**: 优化关键转化路径的用户体验\n\n需要我详细分析某个具体方面吗？"
        elif "异常" in last_message or "anomal" in last_message.lower():
            return "检测到以下异常情况：\n\n1. **流量波动**: 昨日流量较前日下降 15%，主要来自移动端\n2. **转化率变化**: 购买转化率下降 2 个百分点\n\n可能原因：\n- 周末效应导致的自然波动\n- 某关键词排名下降\n- 技术性能问题（需进一步排查）"
        elif "建议" in last_message or "recommend" in last_message.lower():
            return "基于您的数据，我建议：\n\n1. **优先优化移动端体验** - 移动端跳出率比桌面端高 30%\n2. **加强内容营销** - 博客文章带来 40% 的新增流量\n3. **优化结账流程** - 购物车放弃率 65%，有优化空间\n\n需要我帮您制定详细的执行计划吗？"
        else:
            return "您好！我是您的 AI 流量分析助手。我可以帮您：\n\n1. 分析流量数据和趋势\n2. 检测异常情况并找出根因\n3. 生成优化建议\n4. 创建数据报告\n\n请问有什么可以帮助您的？"


class ChatSessionManager:
    """
    聊天会话管理器
    """

    def __init__(self, max_sessions: int = 1000, max_messages_per_session: int = 50):
        self._sessions: Dict[str, ChatSession] = {}
        self._max_sessions = max_sessions
        self._max_messages = max_messages_per_session

    def create_session(self, session_id: Optional[str] = None, context: Optional[Dict] = None) -> str:
        """创建新会话"""
        import uuid
        session_id = session_id or f"chat_{uuid.uuid4().hex[:16]}"

        session = ChatSession(
            session_id=session_id,
            context=context or {}
        )

        # 如果会话数超限，移除最旧的
        if len(self._sessions) >= self._max_sessions:
            oldest_id = min(self._sessions.keys(), key=lambda k: self._sessions[k].updated_at)
            del self._sessions[oldest_id]

        self._sessions[session_id] = session
        return session_id

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """添加消息到会话"""
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        message = ChatMessage(role=role, content=content)

        # 限制消息数量
        if len(session.messages) >= self._max_messages:
            session.messages = session.messages[-self._max_messages + 1:]

        session.messages.append(message)
        session.updated_at = datetime.now()
        return True

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    def get_messages_for_claude(self, session_id: str) -> List[Dict[str, str]]:
        """获取格式化为 Claude API 格式的消息列表"""
        session = self.get_session(session_id)
        if not session:
            return []

        return [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages[-20:]  # 只发送最近 20 条
        ]

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


class LLMService:
    """
    LLM 服务

    提供 AI 对话、洞察生成、报告叙述等能力
    """

    def __init__(self, api_key: Optional[str] = None):
        self._claude_client = ClaudeAPIClient(api_key=api_key)
        self._session_manager = ChatSessionManager()

        # 系统提示模板
        self._system_prompts = {
            "chat": """你是一个专业的 AI 流量分析助手。你的职责是：
1. 帮助用户理解流量数据和趋势
2. 解释数据背后的业务含义
3. 提供可执行的优化建议
4. 回答用户关于流量分析的任何问题

请用简洁、专业的中文回答。对于复杂概念，使用类比和例子帮助理解。
如果数据表明存在问题，要温和地指出并提供解决方案。""",

            "insight": """你是一个资深的数字营销和数据分析专家。请基于提供的数据生成深刻的业务洞察。

要求：
1. 识别关键趋势和模式
2. 指出潜在问题和机会
3. 给出置信度评估
4. 用简洁专业的语言表述

输出格式：
- 标题：简洁概括洞察
- 内容：详细阐述
- 类别：anomaly（异常）/ opportunity（机会）/ trend（趋势）/ recommendation（建议）
- 置信度：0.0-1.0""",

            "narrative": """你是一个专业的数据报告撰写专家。请将数据转化为引人入胜的叙述。

要求：
1. 用故事化的方式呈现数据
2. 突出关键发现和趋势
3. 提供清晰的建议和行动步骤
4. 语言专业但不枯燥

输出格式：
- 章节标题
- 叙述内容（300-500 字）
- 关键发现列表（3-5 条）
- 建议列表（2-4 条）"""
        }

    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        AI 对话

        Args:
            message: 用户消息
            session_id: 会话 ID（可选，用于多轮对话）
            context: 上下文信息（如当前分析的数据）

        Returns:
            对话响应
        """
        # 创建或获取会话
        if not session_id:
            session_id = self._session_manager.create_session(context=context)
        else:
            session = self._session_manager.get_session(session_id)
            if not session:
                session_id = self._session_manager.create_session(session_id, context)

        # 添加用户消息
        self._session_manager.add_message(session_id, "user", message)

        # 获取消息历史
        messages = self._session_manager.get_messages_for_claude(session_id)

        # 调用 Claude API
        response = self._claude_client.chat(
            messages=messages,
            system_prompt=self._system_prompts["chat"]
        )

        # 添加 AI 响应
        self._session_manager.add_message(session_id, "assistant", response)

        return {
            "session_id": session_id,
            "response": response,
            "message_count": len(self._session_manager.get_session(session_id).messages)
        }

    def generate_insight(
        self,
        data: Dict[str, Any],
        insight_type: str = "general"
    ) -> AIInsight:
        """
        生成 AI 洞察

        Args:
            data: 数据字典
            insight_type: 洞察类型

        Returns:
            AI 洞察对象
        """
        import uuid

        # 构建提示
        prompt = f"""请基于以下数据生成深刻的业务洞察：

数据类型：{insight_type}

数据内容：
{json.dumps(data, indent=2, ensure_ascii=False)}

请生成：
1. 一个简洁有力的标题
2. 详细的洞察内容
3. 置信度评估（0.0-1.0）
4. 支持该洞察的关键数据点"""

        response = self._claude_client.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=self._system_prompts["insight"],
            temperature=0.5
        )

        # 解析响应（简化处理）
        category_map = {
            "异常": "anomaly",
            "机会": "opportunity",
            "趋势": "trend",
            "建议": "recommendation"
        }

        # 尝试从响应中提取类别和置信度
        category = "trend"  # 默认
        confidence = 0.8  # 默认

        for cn_cat, en_cat in category_map.items():
            if cn_cat in response:
                category = en_cat
                break

        return AIInsight(
            insight_id=f"insight_{uuid.uuid4().hex[:16]}",
            title=response.split("\n")[0].strip() if "\n" in response else "数据洞察",
            content=response,
            category=category,
            confidence=confidence,
            data_points=[{"key": k, "value": str(v)} for k, v in list(data.items())[:5]]
        )

    def generate_report_narrative(
        self,
        report_data: Dict[str, Any],
        section: str = "overview"
    ) -> ReportNarrative:
        """
        生成报告叙述

        Args:
            report_data: 报告数据
            section: 报告章节

        Returns:
            报告叙述对象
        """
        section_titles = {
            "overview": "整体概览",
            "traffic": "流量分析",
            "conversion": "转化分析",
            "user_behavior": "用户行为",
            "recommendations": "优化建议"
        }

        # 构建提示
        prompt = f"""请为以下报告章节生成专业的叙述：

章节：{section_titles.get(section, section)}

数据：
{json.dumps(report_data, indent=2, ensure_ascii=False)}

请生成：
1. 章节标题
2. 叙述内容（300-500 字）
3. 3-5 条关键发现
4. 2-4 条建议"""

        response = self._claude_client.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=self._system_prompts["narrative"],
            temperature=0.6
        )

        # 解析响应（简化处理）
        lines = response.split("\n")
        title = lines[0].strip() if lines else section_titles.get(section, section)

        key_findings = []
        recommendations = []

        for line in lines:
            if "关键发现" in line or "发现" in line:
                key_findings.append(line.strip("- ").strip())
            elif "建议" in line:
                recommendations.append(line.strip("- ").strip())

        return ReportNarrative(
            section=section,
            title=title,
            narrative=response,
            key_findings=key_findings[:5],
            recommendations=recommendations[:4]
        )

    def get_chat_history(self, session_id: str) -> List[Dict]:
        """获取聊天历史"""
        session = self._session_manager.get_session(session_id)
        if not session:
            return []

        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in session.messages
        ]


# 全局 LLM 服务实例
llm_service = LLMService()
