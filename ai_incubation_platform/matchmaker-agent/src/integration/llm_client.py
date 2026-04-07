"""
LLM客户端
实现匹配话术生成、破冰建议等增强功能
"""
from typing import Optional, List, Dict, Any
import json
from config import settings
from utils.logger import logger
import httpx


class LLMIntegrationClient:
    """LLM集成客户端"""

    def __init__(self):
        self.enabled = settings.llm_enabled
        self.provider = settings.llm_provider
        self.api_key = settings.llm_api_key
        self.api_base = settings.llm_api_base.rstrip('/') if settings.llm_api_base else ""
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.client = httpx.AsyncClient(timeout=30.0) if self.enabled else None

        # 配置API端点
        if not self.api_base:
            if self.provider == "openai":
                self.api_base = "https://api.openai.com/v1"
            elif self.provider == "qwen":
                self.api_base = "https://dashscope.aliyuncs.com/api/v1"
            elif self.provider == "glm":
                self.api_base = "https://open.bigmodel.cn/api/paas/v4"

    async def generate_icebreaker_suggestions(
        self,
        user_info: Dict[str, Any],
        matched_user_info: Dict[str, Any],
        common_interests: List[str],
        compatibility_score: float,
        match_reasoning: str
    ) -> List[str]:
        """
        生成破冰建议
        :param user_info: 当前用户信息
        :param matched_user_info: 匹配对象信息
        :param common_interests: 共同兴趣列表
        :param compatibility_score: 匹配度分数
        :param match_reasoning: 匹配解释
        :return: 破冰话术列表（3-5条）
        """
        if not self.enabled:
            return self._get_default_icebreakers(common_interests)

        try:
            prompt = self._build_icebreaker_prompt(
                user_info, matched_user_info, common_interests,
                compatibility_score, match_reasoning
            )

            response = await self._call_llm(prompt)
            suggestions = self._parse_icebreaker_response(response)

            if not suggestions:
                return self._get_default_icebreakers(common_interests)

            return suggestions[:5]  # 最多返回5条

        except Exception as e:
            logger.error(f"Failed to generate icebreaker suggestions: {str(e)}")
            return self._get_default_icebreakers(common_interests)

    async def generate_conversation_topic(
        self,
        user_info: Dict[str, Any],
        matched_user_info: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> List[str]:
        """生成对话话题建议"""
        if not self.enabled:
            return self._get_default_topics(user_info, matched_user_info)

        try:
            prompt = self._build_topic_prompt(user_info, matched_user_info, chat_history)
            response = await self._call_llm(prompt)
            topics = self._parse_topic_response(response)

            if not topics:
                return self._get_default_topics(user_info, matched_user_info)

            return topics[:3]

        except Exception as e:
            logger.error(f"Failed to generate conversation topics: {str(e)}")
            return self._get_default_topics(user_info, matched_user_info)

    def _build_icebreaker_prompt(
        self,
        user_info: Dict[str, Any],
        matched_user_info: Dict[str, Any],
        common_interests: List[str],
        compatibility_score: float,
        match_reasoning: str
    ) -> str:
        """构建破冰话术生成Prompt"""
        common_interests_str = "、".join(common_interests) if common_interests else "暂无"

        return f"""
你是一个专业的婚恋顾问，请根据以下信息为用户生成3-5条自然、真诚的破冰开场白，要求：
1. 语气友好、不尴尬，避免土味情话和过于套路的内容
2. 可以结合共同兴趣、双方特点展开
3. 每条长度控制在20-50字之间
4. 风格要自然，像真人说的话，不要太生硬

当前用户信息：
- 姓名：{user_info.get('name', '未知')}
- 年龄：{user_info.get('age', '未知')}
- 兴趣：{user_info.get('interests', [])}
- 所在地：{user_info.get('location', '未知')}

匹配对象信息：
- 姓名：{matched_user_info.get('name', '未知')}
- 年龄：{matched_user_info.get('age', '未知')}
- 兴趣：{matched_user_info.get('interests', [])}
- 所在地：{matched_user_info.get('location', '未知')}
- 个人简介：{matched_user_info.get('bio', '暂无')}

匹配信息：
- 共同兴趣：{common_interests_str}
- 匹配度：{compatibility_score:.1%}
- 匹配理由：{match_reasoning}

请直接返回JSON格式的结果，key为"suggestions"，value是字符串数组：
"""

    def _build_topic_prompt(
        self,
        user_info: Dict[str, Any],
        matched_user_info: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """构建话题生成Prompt"""
        chat_context = ""
        if chat_history:
            chat_context = "聊天历史：\n"
            for msg in chat_history[-5:]:  # 只取最近5条消息
                chat_context += f"{msg['role']}: {msg['content']}\n"

        return f"""
你是一个专业的聊天助手，请根据两个用户的信息，生成3个适合他们的聊天话题，要求：
1. 话题要有趣，能够引发双方讨论
2. 结合双方的兴趣、背景和共同特点
3. 避免过于隐私或敏感的话题
4. 每个话题简洁明了，不超过20字

用户A信息：
- 兴趣：{user_info.get('interests', [])}
- 所在地：{user_info.get('location', '未知')}
- 年龄：{user_info.get('age', '未知')}

用户B信息：
- 兴趣：{matched_user_info.get('interests', [])}
- 所在地：{matched_user_info.get('location', '未知')}
- 年龄：{matched_user_info.get('age', '未知')}

{chat_context}

请直接返回JSON格式的结果，key为"topics"，value是字符串数组：
"""

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}
        }

        response = await self.client.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _parse_icebreaker_response(self, response: str) -> List[str]:
        """解析破冰话术返回结果"""
        try:
            data = json.loads(response)
            return data.get("suggestions", [])
        except json.JSONDecodeError:
            # 尝试从文本中提取
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            return [line.lstrip('0123456789.、- ').strip() for line in lines if line]

    def _parse_topic_response(self, response: str) -> List[str]:
        """解析话题返回结果"""
        try:
            data = json.loads(response)
            return data.get("topics", [])
        except json.JSONDecodeError:
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            return [line.lstrip('0123456789.、- ').strip() for line in lines if line]

    def _get_default_icebreakers(self, common_interests: List[str]) -> List[str]:
        """获取默认破冰话术（当LLM不可用时）"""
        default_suggestions = [
            "你好呀，很高兴匹配到你😊",
            "看我们的匹配度还挺高的，来打个招呼~"
        ]

        if common_interests:
            interest = common_interests[0]
            default_suggestions.append(f"听说你也喜欢{interest}，可以交流一下呀~")
            default_suggestions.append(f"关于{interest}，你最近有什么新发现吗？")

        default_suggestions.extend([
            "平时周末一般喜欢做什么呀？",
            "最近有没有遇到什么有趣的事情呀？"
        ])

        return default_suggestions[:5]

    def _get_default_topics(self, user_info: Dict[str, Any], matched_user_info: Dict[str, Any]) -> List[str]:
        """获取默认话题（当LLM不可用时）"""
        user_interests = set(user_info.get('interests', []))
        matched_interests = set(matched_user_info.get('interests', []))
        common = user_interests & matched_interests

        topics = []
        if common:
            topics.append(f"聊聊你们都喜欢的{list(common)[0]}")

        if user_info.get('location') == matched_user_info.get('location'):
            topics.append(f"聊聊{user_info.get('location')}的好吃的")

        topics.extend([
            "聊聊最近看过的电影/书籍",
            "聊聊周末一般怎么安排",
            "聊聊未来的旅行计划"
        ])

        return topics[:3]

    async def close(self):
        """关闭HTTP客户端"""
        if self.client:
            await self.client.aclose()


# 全局LLM客户端实例
llm_client = LLMIntegrationClient()
