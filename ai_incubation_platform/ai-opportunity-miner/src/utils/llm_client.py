"""
LLM客户端工具
支持多种大模型API调用
"""
from typing import List, Dict, Optional
import json
import logging
from config.settings import settings
from utils.http_client import http_client

logger = logging.getLogger(__name__)

class LLMClient:
    """大语言模型客户端"""

    def __init__(self):
        self.api_key = settings.llm_api_key
        self.api_url = settings.llm_api_url
        self.model = settings.llm_model
        self.use_mock = not self.api_key  # 如果没有配置API密钥，使用模拟模式

    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天补全接口"""
        if self.use_mock:
            return self._mock_response(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }

        try:
            response = await http_client.async_post(self.api_url, json=payload, headers=headers)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM API call failed: {str(e)}")
            return self._mock_response(messages)

    def _json_dumps_safe(self, data) -> str:
        """json.dumps 的保护层：将 datetime/复杂对象转为可序列化字符串。"""
        return json.dumps(data, ensure_ascii=False, default=str)

    def _mock_response(self, messages: List[Dict[str, str]]) -> str:
        """模拟响应，用于演示和开发环境"""
        last_message = messages[-1]["content"]

        if "趋势分析" in last_message:
            return """
{
    "trend_score": 0.85,
    "growth_rate": 0.35,
    "summary": "该领域正处于快速增长阶段，政策支持和技术突破是主要驱动因素，预计未来3年将保持30%以上的复合增长率。",
    "key_drivers": ["政策支持", "技术成熟", "市场需求增长"],
    "challenges": ["技术壁垒高", "市场竞争激烈", "人才短缺"],
    "opportunities": ["细分领域创新", "传统行业渗透", "出海机会"]
}
            """
        elif "竞品分析" in last_message:
            return """
{
    "competitors": [
        {
            "name": "主要竞品A",
            "market_share": "35%",
            "strengths": ["技术领先", "品牌优势", "渠道完善"],
            "weaknesses": ["价格较高", "定制化能力不足"]
        },
        {
            "name": "主要竞品B",
            "market_share": "22%",
            "strengths": ["价格优势", "本地化服务好"],
            "weaknesses": ["技术更新慢", "高端市场渗透率低"]
        }
    ],
    "market_concentration": "中等",
    "entry_barrier": "中高",
    "competition_summary": "市场竞争格局正在形成，头部企业优势明显，但创新型企业仍有机会通过差异化产品切入细分市场。"
}
            """
        elif "商机摘要" in last_message:
            return """
{
    "summary": "该商机具有较高的投资价值，市场规模大，增长速度快，虽然存在一定竞争，但技术和渠道优势可以帮助企业获得可观的市场份额。",
    "investment_value": "高",
    "expected_return": "20-30%",
    "payback_period": "2-3年",
    "key_suggestions": [
        "优先布局核心技术研发，建立技术壁垒",
        "重点开拓头部客户，形成标杆案例",
        "与产业链上下游企业建立战略合作关系"
    ]
}
            """
        else:
            return json.dumps({
                "status": "success",
                "message": "模拟响应，配置真实LLM API密钥后可获得实际分析结果",
                "data": {}
            }, ensure_ascii=False, indent=2)

    async def analyze_trend(self, keyword: str, related_data: List[Dict]) -> Dict:
        """分析市场趋势"""
        prompt = f"""
请作为行业分析师，分析以下关键词的市场趋势：
关键词：{keyword}
相关数据：{self._json_dumps_safe(related_data)}

请返回JSON格式的分析结果，包含以下字段：
- trend_score: 趋势分数 0-1
- growth_rate: 年增长率 0-1
- summary: 趋势总结（200字以内）
- key_drivers: 主要驱动因素（数组）
- challenges: 面临的挑战（数组）
- opportunities: 潜在机会（数组）

只返回JSON，不要其他内容。
"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat_completion(messages, temperature=0.3)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response}")
            return {}

    async def analyze_competitors(self, industry: str, related_data: List[Dict]) -> Dict:
        """分析竞品情况"""
        prompt = f"""
请作为行业分析师，分析以下行业的竞品情况：
行业：{industry}
相关数据：{self._json_dumps_safe(related_data)}

请返回JSON格式的分析结果，包含以下字段：
- competitors: 竞品列表，每个包含name, market_share, strengths, weaknesses
- market_concentration: 市场集中度（高/中/低）
- entry_barrier: 进入壁垒（高/中/低）
- competition_summary: 竞争格局总结（200字以内）

只返回JSON，不要其他内容。
"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat_completion(messages, temperature=0.3)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response}")
            return {}

    async def generate_opportunity_summary(self, opportunity_data: Dict) -> Dict:
        """生成商机摘要和投资建议"""
        prompt = f"""
请作为投资分析师，分析以下商机：
商机信息：{json.dumps(opportunity_data, ensure_ascii=False)}

请返回JSON格式的分析结果，包含以下字段：
- summary: 商机摘要（150字以内）
- investment_value: 投资价值（高/中/低）
- expected_return: 预期回报率（如"20-30%"）
- payback_period: 投资回收期（如"2-3年"）
- key_suggestions: 关键建议（数组）

只返回JSON，不要其他内容。
"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat_completion(messages, temperature=0.4)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response}")
            return {}

llm_client = LLMClient()
