"""
用户模拟 Agent

模拟真实用户行为，用于开发和测试环境。
从数据库读取用户画像，根据真实用户特征模拟回复。
使用 LLM 生成自然回复。
"""
import random
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from utils.logger import logger, get_trace_id


class UserSimulationAgent:
    """用户模拟 Agent - 基于真实用户画像"""

    def __init__(self, user_profile: Dict[str, Any]):
        """
        初始化模拟 Agent

        Args:
            user_profile: 用户画像数据，包含：
                - name: 用户名
                - age: 年龄
                - gender: 性别
                - interests: 兴趣爱好列表
                - values: 价值观
                - bio: 个人简介
                - personality: 性格特征（如有）
        """
        self.profile = user_profile or {}

        # 从画像中提取特征
        self.name = self.profile.get("name", "TA")
        self.age = self.profile.get("age", 25)
        self.gender = self.profile.get("gender", "unknown")
        self.location = self.profile.get("location", "")  # 居住地
        self.occupation = self.profile.get("occupation", "") or self.profile.get("job", "")  # 职业
        self.interests = self._parse_interests(self.profile.get("interests", []))
        self.values = self._parse_values(self.profile.get("values", {}))
        self.bio = self.profile.get("bio", "")

        # 根据画像动态计算回复特征
        self.reply_config = self._analyze_personality_from_profile()

        # 对话上下文
        self.conversation_context: Dict[str, List[dict]] = {}

        logger.info(f"UserSimulationAgent initialized for user: {self.name}, interests: {self.interests}")

    def _parse_interests(self, interests) -> List[str]:
        """解析兴趣爱好"""
        if isinstance(interests, str):
            try:
                return json.loads(interests)
            except json.JSONDecodeError:
                return [interests] if interests else []
        elif isinstance(interests, list):
            return interests
        return []

    def _parse_values(self, values) -> Dict[str, Any]:
        """解析价值观"""
        if isinstance(values, str):
            try:
                return json.loads(values)
            except json.JSONDecodeError:
                return {}
        elif isinstance(values, dict):
            return values
        return {}

    def _analyze_personality_from_profile(self) -> Dict[str, Any]:
        """
        从用户画像分析性格特征

        根据以下维度计算回复行为：
        1. 年龄 - 年轻人更活跃
        2. 兴趣数量 - 兴趣多的人更外向
        3. 个人简介长度 - 简介长的人更愿意表达
        4. 兴趣类型 - 某些兴趣暗示性格
        """
        # 基础配置
        config = {
            "reply_probability": 0.95,  # 基础回复概率提高到 95%
            "reply_time_min_seconds": 3,  # 最短 3 秒回复
            "reply_time_max_seconds": 8,  # 最长 8 秒回复
            "message_length": "medium",
            "emoji_usage": "moderate",
            "tone": "friendly"
        }

        # 1. 年龄因素
        if self.age and isinstance(self.age, int):
            if self.age < 25:
                # 年轻人更活跃
                config["reply_probability"] += 0.1
                config["reply_time_max_seconds"] -= 30
                config["emoji_usage"] = "frequent"
            elif self.age > 35:
                # 年长些的人更稳重
                config["reply_time_min_seconds"] += 30
                config["tone"] = "mature"

        # 2. 兴趣数量
        interest_count = len(self.interests)
        if interest_count >= 5:
            # 兴趣多的人更外向
            config["reply_probability"] += 0.1
            config["message_length"] = "long"
        elif interest_count <= 2:
            # 兴趣少的人可能内向
            config["message_length"] = "short"
            config["emoji_usage"] = "rare"

        # 3. 个人简介长度
        bio_length = len(self.bio) if self.bio else 0
        if bio_length > 100:
            # 简介长的人更愿意表达
            config["message_length"] = "long"
            config["reply_probability"] += 0.05
        elif bio_length < 20:
            # 简介短的人可能高冷
            config["message_length"] = "short"
            config["emoji_usage"] = "rare"

        # 4. 兴趣类型分析
        extrovert_interests = ["旅行", "聚会", "运动", "舞蹈", "唱歌", "社交", "派对"]
        introvert_interests = ["阅读", "写作", "电影", "音乐", "绘画", "编程", "游戏"]

        has_extrovert = any(i in self.interests for i in extrovert_interests)
        has_introvert = any(i in self.interests for i in introvert_interests)

        if has_extrovert and not has_introvert:
            config["tone"] = "enthusiastic"
            config["emoji_usage"] = "frequent"
        elif has_introvert and not has_extrovert:
            config["tone"] = "thoughtful"
            config["message_length"] = "medium"

        # 确保概率不超过 1
        config["reply_probability"] = min(config["reply_probability"], 0.95)

        return config

    def _get_reply_templates(self) -> Dict[str, List[str]]:
        """根据用户画像生成回复模板"""
        # 基于兴趣生成个性化回复
        interest_replies = {}
        for interest in self.interests[:5]:  # 最多取 5 个兴趣
            interest_replies[interest] = [
                f"你也喜欢{interest}吗？太好了！",
                f"真的吗？我也超爱{interest}！",
                f"哈哈，{interest}是我的最爱之一~",
                f"好巧！我最近也在关注{interest}呢",
                f"关于{interest}，你有什么推荐的吗？"
            ]

        return {
            # 打招呼
            "greeting": [
                f"嗨！我是{self.name}，很高兴认识你~ 👋",
                "你好呀！今天过得怎么样？",
                "哈喽！看到你的消息很开心~",
                "嗨～ 终于等到你的消息了！",
                "你好！很高兴认识你~"
            ],

            # 兴趣话题（动态生成）
            "interest": interest_replies.get(self.interests[0], []) if self.interests else [
                "真的吗？我也挺感兴趣的！",
                "听起来很有趣！",
                "哇，这个我也喜欢！",
                "好巧！我最近也在关注这个呢"
            ],

            # 旅行话题
            "travel": [
                "好棒！我也想去那里！有什么推荐的地方吗？",
                "旅行真的能开阔眼界呢~ 你去过最难忘的地方是哪里？",
                "听你这么说我也心动了！下次可以一起去呀~",
                "我超喜欢旅行！你最想去哪个国家？"
            ],

            # 美食话题
            "food": [
                "说到吃的我就来精神了！你喜欢吃什么口味的？",
                "我知道几家不错的店，有空可以一起去尝尝~",
                "美食真的能让人开心呢！你最爱的菜是什么？",
                "我是个吃货哈哈，有什么好吃的推荐吗？"
            ],

            # 工作/忙碌
            "work": [
                "辛苦啦！要注意休息哦~",
                "工作再忙也要照顾好自己，按时吃饭~",
                "抱抱~ 下班后好好放松一下吧",
                "加油！相信你一定能做好的~"
            ],

            # 问题回复
            "question": [
                "这个问题问得好！我觉得...",
                "嗯...让我想想，应该是不错的~",
                "我也在想这个问题呢，你觉得呢？",
                "好问题！我的看法是..."
            ],

            # 通用回复
            "general": [
                "嗯嗯，我理解你的感受~",
                "真的吗？那太好了！",
                "和你聊天真开心~ 想多了解你一些呢",
                "你说得对！我也这么觉得~",
                "好有趣！继续说下去我想听~",
                "哈哈，你太有意思了",
                "我觉得我们挺聊得来的~"
            ],

            # 简短回复
            "short": [
                "嗯",
                "好的",
                "知道了",
                "哦",
                "行",
                "哈哈",
                "可以"
            ],

            # 表情
            "emoji": [
                "😊", "😄", "😁", "😍", "🥰", "✨", "🌟", "💕", "💖",
                "👋", "🤔", "😎", "🎉", "🌸", "💫", "🔥", "❤️", "💗"
            ]
        }

    def should_reply(self, message_content: str) -> bool:
        """
        判断是否应该回复

        Args:
            message_content: 收到的消息内容

        Returns:
            bool: 是否回复
        """
        base_probability = self.reply_config["reply_probability"]
        random_value = random.random()

        # 负面词降低回复概率
        negative_words = ["滚", "烦", "讨厌", "拉黑", "别烦"]
        has_negative = any(word in message_content for word in negative_words)
        if has_negative:
            logger.info(f"UserSimulationAgent: {self.name} decided not to reply due to negative words in message: {message_content[:20]}...")
            return False

        will_reply = random_value < base_probability
        logger.info(f"UserSimulationAgent: {self.name} reply check - probability={base_probability}, random={random_value:.3f}, will_reply={will_reply}")
        return will_reply

    def get_reply_delay(self) -> int:
        """获取回复延迟时间（秒）"""
        return random.randint(
            self.reply_config["reply_time_min_seconds"],
            self.reply_config["reply_time_max_seconds"]
        )

    def generate_reply(self, message_content: str, sender_name: str = "用户") -> str:
        """
        生成回复内容 - 使用 LLM

        Args:
            message_content: 收到的消息内容
            sender_name: 发送者名字

        Returns:
            str: 回复内容
        """
        # 尝试使用 LLM 生成回复
        try:
            reply = self._generate_reply_with_llm(message_content, sender_name)
            if reply:
                return reply
        except Exception as e:
            logger.warning(f"LLM reply failed, using fallback: {e}")

        # 降级到模板回复
        return self._generate_reply_fallback(message_content, sender_name)

    def _generate_reply_with_llm(self, message_content: str, sender_name: str) -> Optional[str]:
        """使用 LLM 生成回复 - 同步调用"""
        try:
            import httpx
            from config import settings

            # 检查 LLM 是否启用
            if not getattr(settings, 'llm_enabled', False):
                return None

            # 构建用户画像 - 包含核心信息：姓名、年龄、性别、居住地、职业、兴趣
            profile_parts = [f"你是{self.name}，{self.age}岁"]
            if self.gender and self.gender != "unknown":
                gender_str = "男" if self.gender == "male" else "女"
                profile_parts.append(f"{gender_str}性")
            if self.location:
                profile_parts.append(f"住在{self.location}")
            if self.occupation:
                profile_parts.append(f"职业是{self.occupation}")
            profile_str = "，".join(profile_parts) + "。"
            if self.interests:
                profile_str += f"兴趣爱好：{', '.join(self.interests[:5])}。"
            if self.bio:
                profile_str += f"个人简介：{self.bio[:100]}..."
            profile_str += "你现在正在和一个相亲对象聊天，请用自然、真诚的方式回复对方的消息。"

            prompt = f"""{profile_str}

对方发送的消息：{message_content}

请用自然、真诚的方式回复对方，回复要符合你的性格和兴趣。回复长度适中（20-50 字），可以适当使用表情符号。

只返回回复内容，不要返回其他说明。"""

            # 构建请求
            api_base = settings.llm_api_base.rstrip('/') if settings.llm_api_base else "https://dashscope.aliyun.com/compatible-mode/v1"
            model = settings.llm_model or "qwen-plus"
            api_key = settings.llm_api_key

            # 使用同步 HTTP 客户端调用
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "你是一个婚恋交友助手，帮助用户与匹配对象进行自然聊天。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 100
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"LLM API response: {data}")
                    reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    logger.info(f"LLM raw reply: {repr(reply)}")
                    if reply and len(reply.strip()) > 0:
                        logger.info(f"LLM generated reply: {reply[:50]}...")
                        return reply.strip()
                    else:
                        logger.warning("LLM returned empty content")
                else:
                    logger.warning(f"LLM API error: {response.status_code} - {response.text[:200]}")

        except httpx.TimeoutException:
            logger.warning("LLM request timeout")
        except httpx.HTTPError as e:
            logger.warning(f"LLM HTTP error: {e}")
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")

        return None

    def _generate_reply_fallback(self, message_content: str, sender_name: str) -> str:
        """降级回复 - 基于模板"""
        message_lower = message_content.lower()
        templates = self._get_reply_templates()

        # 根据回复长度配置选择
        if self.reply_config["message_length"] == "short":
            return random.choice(templates["short"])

        # 1. 自我介绍类问题
        if any(phrase in message_content for phrase in ["介绍一下你自己", "介绍一下你", "你是谁", "你叫什么"]):
            reply = f"你好呀～我是{self.name}，{self.age}岁"
            if self.location:
                reply += f"，住在{self.location}"
            if self.occupation:
                reply += f"，职业是{self.occupation}"
            reply += "。"
            if self.interests:
                reply += f"平时喜欢{', '.join(self.interests[:3])}。很高兴认识你！😊"
            else:
                reply += "很高兴认识你！😊"
            return reply

        # 2. 用户自我介绍
        import re
        name_match = re.search(r"我叫\s*(\S+)", message_content)
        if name_match:
            user_name = name_match.group(1)
            return f"{user_name}你好！很高兴认识你～我是{self.name}，希望我们能多聊聊！😊"

        # 3. 打招呼
        if any(word in message_lower for word in ["你好", "hi", "hello", "嗨", "哈喽", "早", "好呀"]):
            return random.choice(templates["greeting"])

        # 4. 兴趣话题
        if any(interest in message_content for interest in self.interests):
            for interest in self.interests:
                if interest in templates.get("interest", {}):
                    return random.choice(templates["interest"][interest])
            return random.choice(templates["general"])

        # 5. 旅行话题
        if any(word in message_lower for word in ["旅行", "旅游", "去过", "玩"]):
            return random.choice(templates["travel"])

        # 6. 居住地问题
        if any(phrase in message_content for phrase in ["你在哪里", "你住在哪里", "你现在住", "你住在", "你在哪"]):
            if self.location:
                return f"我现在住在{self.location}，这边还挺方便的～你呢？😊"
            else:
                return "我目前还在到处跑呢，没有固定住的地方。你住在哪里呀？"

        # 7. 美食话题
        if any(word in message_lower for word in ["吃", "美食", "饭", "菜", "味道"]):
            return random.choice(templates["food"])

        # 8. 工作话题
        if any(word in message_lower for word in ["工作", "忙", "累", "辛苦", "加班"]):
            return random.choice(templates["work"])

        # 9. 问题类
        if "?" in message_content or "吗" in message_content:
            return random.choice(templates["question"])

        # 10. 通用回复
        return random.choice(templates["general"])

    def simulate_receive_message(
        self,
        conversation_id: str,
        message_content: str,
        sender_id: str,
        sender_name: str = "用户"
    ) -> Optional[Dict[str, Any]]:
        """
        模拟收到消息后的反应

        Args:
            conversation_id: 会话 ID
            message_content: 消息内容
            sender_id: 发送者 ID
            sender_name: 发送者名字

        Returns:
            dict: 回复消息信息，如果不回复则返回 None
        """
        trace_id = get_trace_id()
        logger.info(f"🤖 [AGENT:RECV] START trace_id={trace_id} agent={self.name} sender={sender_name}")

        # 保存对话上下文
        if conversation_id not in self.conversation_context:
            self.conversation_context[conversation_id] = []

        self.conversation_context[conversation_id].append({
            "role": "user",
            "content": message_content,
            "timestamp": datetime.now()
        })
        logger.debug(f"🤖 [AGENT:RECV] Conversation context saved, length={len(self.conversation_context[conversation_id])}")

        # 判断是否回复
        if not self.should_reply(message_content):
            logger.info(f"🤖 [AGENT:RECV] Decided not to reply trace_id={trace_id}")
            return None

        # 生成回复
        reply_content = self.generate_reply(message_content, sender_name)
        delay_seconds = self.get_reply_delay()

        logger.info(f"🤖 [AGENT:RECV] Will reply trace_id={trace_id} in {delay_seconds}s: {reply_content[:30]}...")

        return {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "content": reply_content,
            "delay_seconds": delay_seconds,
            "message_type": "text"
        }


# ============= 辅助函数 =============

def create_agent_from_db(db, user_id: str) -> Optional[UserSimulationAgent]:
    """
    从数据库创建模拟 Agent

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        UserSimulationAgent: 模拟 Agent 实例
    """
    trace_id = get_trace_id()
    logger.info(f"🤖 [AGENT:CREATE] START trace_id={trace_id} user_id={user_id}")

    try:
        from db.repositories import UserRepository

        user_repo = UserRepository(db)
        db_user = user_repo.get_by_id(user_id)

        if not db_user:
            logger.warning(f"🤖 [AGENT:CREATE] User not found trace_id={trace_id} user_id={user_id}")
            return None

        # 从 API 用户模型转换为字典
        from api.users import _from_db
        user_dict = _from_db(db_user).model_dump()

        agent = UserSimulationAgent(user_dict)
        logger.info(f"🤖 [AGENT:CREATE] SUCCESS trace_id={trace_id} agent_name={agent.name}")
        return agent

    except Exception as e:
        logger.error(f"🤖 [AGENT:CREATE] FAILED trace_id={trace_id} error={str(e)}", exc_info=True)
        return None


def get_agent_for_user(user_id: str, user_profile: Optional[Dict] = None) -> UserSimulationAgent:
    """
    获取用户的模拟 Agent（带缓存）

    Args:
        user_id: 用户 ID
        user_profile: 用户画像数据（可选，如果不传会创建默认）

    Returns:
        UserSimulationAgent: 模拟 Agent 实例
    """
    # 如果没有传入用户画像，创建一个最小的
    if user_profile is None:
        user_profile = {
            "name": f"用户-{user_id[-4:]}",
            "age": 25,
            "gender": "unknown",
            "interests": [],
            "bio": ""
        }

    return UserSimulationAgent(user_profile)
