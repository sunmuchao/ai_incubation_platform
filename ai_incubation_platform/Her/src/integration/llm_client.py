"""
LLM 客户端
实现匹配话术生成、破冰建议等增强功能

降级方案：
1. LLM API 失败时自动切换到本地规则引擎
2. 支持语义缓存减少 API 调用
3. 多级降级：API → 缓存 → 本地规则 → Mock 数据
"""
from typing import Optional, List, Dict, Any
import json
import hashlib
from datetime import datetime, timedelta
from config import settings
from utils.logger import logger, get_trace_id
import httpx

from integration.llm_client_types import UserInfo, MatchContext


# ============= 语义缓存 =============

class SemanticCache:
    """语义缓存层 - 减少重复 LLM 调用"""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def _generate_key(self, prompt: str) -> str:
        """生成缓存键"""
        return hashlib.md5(prompt.encode()).hexdigest()

    def get(self, prompt: str) -> Optional[str]:
        """从缓存获取结果"""
        if not settings.llm_cache_enabled:
            return None

        key = self._generate_key(prompt)
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() - entry["timestamp"] < self._ttl:
                logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                return entry["response"]
            else:
                del self._cache[key]
        return None

    def set(self, prompt: str, response: str) -> None:
        """缓存结果"""
        if not settings.llm_cache_enabled:
            return

        key = self._generate_key(prompt)
        self._cache[key] = {
            "response": response,
            "timestamp": datetime.now()
        }
        logger.debug(f"Cached response for prompt: {prompt[:50]}...")

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()


# 全局缓存实例
_semantic_cache = SemanticCache(ttl_seconds=3600)


# ============= 本地规则引擎（降级方案） =============

class LocalRuleEngine:
    """本地规则引擎 - LLM 降级方案"""

    def __init__(self):
        # 破冰话术模板库
        self.icebreaker_templates = [
            "你好呀，看到你也喜欢{interest}，可以交流一下心得吗？",
            "嗨～你的{interest}看起来很专业，能分享一下经验吗？",
            "你好！发现我们都在{location}，有什么推荐的好去处吗？",
            "很高兴匹配到你！你的自我介绍很有意思，特别是关于{interest}的部分～",
            "哈喽～看资料我们有很多共同话题，从{interest}开始聊起如何？",
        ]

        # 话题模板库
        self.topic_templates = [
            "聊聊各自最近看过的一部电影或剧集",
            "分享一下周末最喜欢的活动",
            "聊聊未来一年的旅行计划",
            "分享一本最近读过的好书",
            "聊聊家乡的美食和文化",
            "讨论一下最近的热点新闻",
            "分享一下工作中的趣事",
            "聊聊各自的爱好和兴趣",
        ]

    def generate_icebreakers(
        self,
        user_info: UserInfo,
        matched_user_info: UserInfo,
        common_interests: List[str],
        **kwargs
    ) -> List[str]:
        """使用本地规则生成破冰话术"""
        suggestions = []

        # 基于共同兴趣生成
        if common_interests:
            for interest in common_interests[:3]:
                template = self.icebreaker_templates[0].format(interest=interest)
                suggestions.append(template)

        # 基于地点生成
        if user_info.get('location') == matched_user_info.get('location'):
            template = self.icebreaker_templates[2].format(location=user_info.get('location', '本地'))
            suggestions.append(template)

        # 基于个人简介生成
        bio = matched_user_info.get('bio', '')
        if bio and len(bio) > 10:
            template = self.icebreaker_templates[3].format(interest="你的介绍")
            suggestions.append(template)

        # 补充默认话术
        defaults = [
            "你好呀，很高兴匹配到你～",
            "看我们的匹配度还挺高的，来打个招呼吧！",
            "平时周末一般喜欢做什么呀？",
        ]

        while len(suggestions) < 5:
            if suggestions:
                suggestions.append(defaults[len(suggestions) % len(defaults)])
            else:
                suggestions.append(defaults[len(suggestions)])

        return suggestions[:5]

    def generate_topics(
        self,
        user_info: UserInfo,
        matched_user_info: UserInfo,
        **kwargs
    ) -> List[str]:
        """使用本地规则生成话题"""
        topics = []

        # 基于共同兴趣
        user_interests = set(user_info.get('interests', []))
        matched_interests = set(matched_user_info.get('interests', []))
        common = user_interests & matched_interests

        if common:
            topics.append(f"聊聊你们都喜欢的{list(common)[0]}")

        # 基于地点
        if user_info.get('location') == matched_user_info.get('location'):
            topics.append(f"聊聊{user_info.get('location')}的好吃的和好玩的")

        # 补充默认话题
        for topic in self.topic_templates:
            if len(topics) >= 5:
                break
            if topic not in topics:
                topics.append(topic)

        return topics[:5]


# 全局规则引擎实例
_rule_engine = LocalRuleEngine()


# ============= LLM 集成客户端 =============

class LLMIntegrationClient:
    """LLM 集成客户端"""

    def __init__(self):
        self.enabled = settings.llm_enabled
        self.provider = settings.llm_provider
        self.api_key = settings.llm_api_key
        self.api_base = settings.llm_api_base.rstrip('/') if settings.llm_api_base else ""
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.timeout = settings.llm_request_timeout
        self.retry_count = settings.llm_retry_count

        # 降级方案配置
        self.fallback_enabled = settings.llm_fallback_enabled
        self.fallback_mode = settings.llm_fallback_mode  # 'local' or 'mock'

        # HTTP 客户端
        self.client = None
        if self.enabled and self.api_key:
            self.client = httpx.AsyncClient(timeout=float(self.timeout))

        # 配置 API 端点
        if not self.api_base:
            if self.provider == "openai":
                self.api_base = "https://api.openai.com/v1"
            elif self.provider == "qwen":
                self.api_base = "https://dashscope.aliyuncs.com/api/v1"
            elif self.provider == "glm":
                self.api_base = "https://open.bigmodel.cn/api/paas/v4"

        logger.info(f"LLM Client initialized: enabled={self.enabled}, fallback={self.fallback_enabled}, mode={self.fallback_mode}")

    async def generate_icebreaker_suggestions(
        self,
        user_info: UserInfo,
        matched_user_info: UserInfo,
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
        :return: 破冰话术列表（3-5 条）
        """
        trace_id = get_trace_id()
        logger.info(f"🧠 [LLM:ICEBREAKER] START trace_id={trace_id} users={user_info.get('id')}->{matched_user_info.get('id')}")

        # 构建缓存键
        cache_key = f"icebreaker:{user_info.get('id')}:{matched_user_info.get('id')}:{','.join(common_interests)}"

        # 1. 尝试从缓存获取
        cached = _semantic_cache.get(cache_key)
        if cached:
            logger.info(f"🧠 [LLM:ICEBREAKER] CACHE HIT trace_id={trace_id}")
            try:
                return json.loads(cached)
            except:
                pass

        # 2. LLM 生成
        if self.enabled and self.api_key:
            try:
                prompt = self._build_icebreaker_prompt(
                    user_info, matched_user_info, common_interests,
                    compatibility_score, match_reasoning
                )

                response = await self._call_llm_with_retry(prompt)
                suggestions = self._parse_icebreaker_response(response)

                if suggestions:
                    _semantic_cache.set(cache_key, json.dumps(suggestions))
                    logger.info(f"🧠 [LLM:ICEBREAKER] SUCCESS trace_id={trace_id} count={len(suggestions)}")
                    return suggestions[:5]

            except Exception as e:
                logger.error(f"🧠 [LLM:ICEBREAKER] FAILED trace_id={trace_id} error={str(e)}, falling back to {self.fallback_mode} mode")

        # 3. 降级方案
        logger.info(f"🧠 [LLM:ICEBREAKER] Using fallback trace_id={trace_id}")
        return self._fallback_icebreakers(user_info, matched_user_info, common_interests)

    async def generate_conversation_topic(
        self,
        user_info: UserInfo,
        matched_user_info: UserInfo,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> List[str]:
        """生成对话话题建议"""
        # 构建缓存键
        cache_key = f"topic:{user_info.get('id')}:{matched_user_info.get('id')}"

        # 1. 尝试从缓存获取
        cached = _semantic_cache.get(cache_key)
        if cached:
            logger.info("Using cached conversation topics")
            try:
                return json.loads(cached)
            except:
                pass

        # 2. LLM 生成
        if self.enabled and self.api_key:
            try:
                prompt = self._build_topic_prompt(user_info, matched_user_info, chat_history)
                response = await self._call_llm_with_retry(prompt)
                topics = self._parse_topic_response(response)

                if topics:
                    _semantic_cache.set(cache_key, json.dumps(topics))
                    return topics[:5]

            except Exception as e:
                logger.error(f"LLM topic generation failed: {e}, falling back to {self.fallback_mode} mode")

        # 3. 降级方案
        return self._fallback_topics(user_info, matched_user_info)

    def _fallback_icebreakers(
        self,
        user_info: UserInfo,
        matched_user_info: UserInfo,
        common_interests: List[str]
    ) -> List[str]:
        """降级方案：生成破冰话术"""
        if self.fallback_enabled:
            if self.fallback_mode == "local":
                # 使用本地规则引擎
                return _rule_engine.generate_icebreakers(
                    user_info, matched_user_info, common_interests
                )
            else:
                # Mock 模式
                return self._get_default_icebreakers(common_interests)
        else:
            return self._get_default_icebreakers(common_interests)

    def _fallback_topics(
        self,
        user_info: UserInfo,
        matched_user_info: UserInfo
    ) -> List[str]:
        """降级方案：生成话题"""
        if self.fallback_enabled:
            if self.fallback_mode == "local":
                # 使用本地规则引擎
                return _rule_engine.generate_topics(user_info, matched_user_info)
            else:
                # Mock 模式
                return self._get_default_topics(user_info, matched_user_info)
        else:
            return self._get_default_topics(user_info, matched_user_info)

    def _build_icebreaker_prompt(
        self,
        user_info: UserInfo,
        matched_user_info: UserInfo,
        common_interests: List[str],
        compatibility_score: float,
        match_reasoning: str
    ) -> str:
        """构建破冰话术生成 Prompt"""
        common_interests_str = ",".join(common_interests) if common_interests else "暂无"

        return f"""
你是一个专业的婚恋顾问，请根据以下信息为用户生成 3-5 条自然、真诚的破冰开场白，要求：
1. 语气友好、不尴尬，避免土味情话和过于套路的内容
2. 可以结合共同兴趣、双方特点展开
3. 每条长度控制在 20-50 字之间
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

请直接返回 JSON 格式的结果，key 为"suggestions"，value 是字符串数组：
"""

    def _build_topic_prompt(
        self,
        user_info: UserInfo,
        matched_user_info: UserInfo,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """构建话题生成 Prompt"""
        chat_context = ""
        if chat_history:
            chat_context = "聊天历史：\n"
            for msg in chat_history[-5:]:
                chat_context += f"{msg['role']}: {msg['content']}\n"

        return f"""
你是一个专业的聊天助手，请根据两个用户的信息，生成 3-5 个适合他们的聊天话题，要求：
1. 话题要有趣，能够引发双方讨论
2. 结合双方的兴趣、背景和共同特点
3. 避免过于隐私或敏感的话题
4. 每个话题简洁明了，不超过 20 字

用户 A 信息：
- 兴趣：{user_info.get('interests', [])}
- 所在地：{user_info.get('location', '未知')}
- 年龄：{user_info.get('age', '未知')}

用户 B 信息：
- 兴趣：{matched_user_info.get('interests', [])}
- 所在地：{matched_user_info.get('location', '未知')}
- 年龄：{matched_user_info.get('age', '未知')}

{chat_context}

请直接返回 JSON 格式的结果，key 为"topics"，value 是字符串数组：
"""

    async def _call_llm_with_retry(self, prompt: str) -> str:
        """带重试的 LLM 调用"""
        last_error = None

        for attempt in range(self.retry_count + 1):
            try:
                return await self._call_llm(prompt)
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_count:
                    await httpx.sleep(1.0 * (attempt + 1))  # 指数退避

        raise last_error

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM API"""
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
        """获取默认破冰话术（Mock 模式）"""
        default_suggestions = [
            "你好呀，很高兴匹配到你～",
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

    def _get_default_topics(self, user_info: UserInfo, matched_user_info: UserInfo) -> List[str]:
        """获取默认话题（Mock 模式）"""
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

    async def generate_chat(self, prompt: str) -> Dict[str, Any]:
        """
        通用聊天生成方法

        :param prompt: 提示词
        :return: LLM 响应（JSON 格式）
        """
        # 1. 尝试 LLM 调用
        if self.enabled and self.api_key and self.client:
            try:
                response = await self._call_llm_with_retry(prompt)
                # 尝试解析为 JSON
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    # 如果不是 JSON，返回原始文本
                    return {"text": response}

            except Exception as e:
                logger.error(f"LLM chat failed: {e}, falling back to {self.fallback_mode}")

        # 2. 降级方案
        return self._fallback_chat(prompt)

    def _fallback_chat(self, prompt: str) -> Dict[str, Any]:
        """降级方案：返回模拟响应"""
        if self.fallback_mode == "mock":
            return {
                "message": "这是一个很有趣的话题！",
                "analysis": {
                    "intent": "response",
                    "tone": "friendly",
                    "topic": "general",
                    "emotion": "positive"
                }
            }
        else:
            # local 模式：基于简单规则
            return {
                "message": "你说得对，我也有同感。",
                "analysis": {
                    "intent": "agreement",
                    "tone": "neutral",
                    "topic": "general",
                    "emotion": "neutral"
                }
            }

    async def close(self):
        """关闭 HTTP 客户端"""
        if self.client:
            await self.client.aclose()


# 全局 LLM 客户端实例
llm_client = LLMIntegrationClient()
