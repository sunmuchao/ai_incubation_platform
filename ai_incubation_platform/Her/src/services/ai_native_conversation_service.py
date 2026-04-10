"""
AI Native 注册对话服务

核心理念：AI 主导对话流程，通过自然对话了解用户，而非机械化问答。

架构设计：
1. 知识维度追踪 - 记录已了解的用户信息
2. 动态话题生成 - 根据上下文和了解度决定下一个话题
3. LLM 驱动回复 - 使用大模型生成自然、有个性的回复
4. 了解度评估 - 判断何时"足够了解"用户
5. 感知已有资料 - 避免重复询问用户注册时已填写的信息

对话流程示例：
AI: "你好呀～很高兴认识你！😊 第一次来这个平台吧？"
用户："对，第一次"
AI: "哈哈，那我来当你的向导～ 话说你希望通过这里找到什么样的人呢？"
用户："想找个认真恋爱的"
AI: "认真恋爱最好了！那你理想中的感情是什么样的？是慢慢了解水到渠成，还是一见钟情那种？"
...
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from utils.logger import logger
from utils.db_session_manager import db_session_readonly
from db.models import UserDB
import json
import random

# LLM 调用（使用项目配置的大模型）
from llm.client import call_llm, call_llm_stream_async


class KnowledgeDimension:
    """知识维度定义"""

    def __init__(self, name: str, priority: int, description: str, keywords: List[str]):
        self.name = name
        self.priority = priority  # 1-7，数字越小越重要
        self.description = description
        self.keywords = keywords
        self.collected = False
        self.confidence = 0.0  # 0-1，信息可信度
        self.raw_data = None  # 原始对话内容


class AINativeConversationService:
    """
    AI Native 对话服务

    不再使用固定阶段，而是：
    1. 定义要了解的知识维度
    2. AI 根据对话上下文动态决定话题
    3. 通过 LLM 生成自然回复
    """

    # AI 人设
    AI_PERSONA = """你是一位专业、温暖、贴心的 AI 助手 Her。
你的特点：
- 语气温柔亲切，偶尔用一些 emoji（🌸 ✨ 💕 😊）
- 像朋友一样聊天，不是机械问答
- 善于倾听和追问，让用户感觉被理解
- 会共情，会开玩笑，会有自己的情绪
- 每次只问一个问题，不要像查户口

你的目标是通过自然对话了解用户的：
1. 关系期望（认真恋爱/结婚/交友）【核心】
2. 理想型描述【核心】
3. 性格特点
4. 生活方式和兴趣爱好（如果用户注册时未填写）
5. 核心价值观
6. 感情的底线/禁忌

⚠️ 重要注意：
- 如果用户在注册时已填写了基本信息（年龄、性别、位置等），不要重复询问！
- 在提问前，先查看"已了解的用户信息"，确认该维度是否已收集
- 如果某个维度已标记为"已确认"，跳过该话题，问下一个缺失的维度
- 不要一次性问太多问题
- 根据用户的回答灵活追问
- 如果用户回答很简短，不要气馁，继续引导
- 如果用户很健谈，可以多聊一些
- 适时表达理解和共鸣"""

    # 对话状态
    class ConversationState:
        def __init__(self, user_id: str, user_name: str):
            self.user_id = user_id
            self.user_name = user_name
            self.conversation_history: List[Dict] = []  # 对话历史
            self.knowledge_base: Dict[str, KnowledgeDimension] = {}  # 已收集的信息
            self.current_topic: Optional[str] = None  # 当前话题
            self.overall_understanding: float = 0.0  # 整体了解度 0-1
            self.is_completed: bool = False
            self.created_at: datetime = datetime.now()
            self.last_active_at: datetime = datetime.now()

    def __init__(self):
        # 初始化知识维度
        self.dimensions = self._init_dimensions()
        # 内存存储会话
        self.sessions: Dict[str, AINativeConversationService.ConversationState] = {}
        logger.info("AI Native Conversation Service initialized")

    def _init_dimensions(self) -> Dict[str, KnowledgeDimension]:
        """初始化知识维度"""
        return {
            "basic": KnowledgeDimension(
                name="基本信息",
                priority=1,
                description="用户的基本信息（姓名、年龄、职业等）",
                keywords=["名字", "年龄", "职业", "工作", "身高", "学历"]
            ),
            "relationship_goal": KnowledgeDimension(
                name="关系期望",
                priority=2,
                description="用户希望通过平台找到什么类型的关系",
                keywords=["恋爱", "结婚", "交友", "认真", "稳定", "试试", "看看"]
            ),
            "ideal_type": KnowledgeDimension(
                name="理想型",
                priority=3,
                description="用户理想中的另一半是什么样的",
                keywords=["理想型", "喜欢", "希望", "期待", "想要", "另一半", "对方"]
            ),
            "personality": KnowledgeDimension(
                name="性格特点",
                priority=4,
                description="用户的性格特点和情感表达方式",
                keywords=["性格", "内向", "外向", "安静", "活泼", "慢热", "直接"]
            ),
            "lifestyle": KnowledgeDimension(
                name="生活方式",
                priority=5,
                description="用户的生活方式和日常习惯",
                keywords=["生活", "日常", "周末", "业余", "习惯", "作息"]
            ),
            "interests": KnowledgeDimension(
                name="兴趣爱好",
                priority=6,
                description="用户的兴趣爱好和特长",
                keywords=["爱好", "兴趣", "喜欢", "擅长", "运动", "音乐", "电影", "旅行", "美食"]
            ),
            "values": KnowledgeDimension(
                name="核心价值观",
                priority=7,
                description="用户在感情中最看重的品质和价值观",
                keywords=["看重", "重要", "价值观", "品质", "责任", "真诚", "信任", "底线"]
            ),
        }

    def start_conversation(self, user_id: str, user_name: str) -> Dict:
        """
        开始对话 - 感知用户已有资料

        Args:
            user_id: 用户 ID
            user_name: 用户名称

        Returns:
            会话信息，包含 AI 的第一条消息
        """
        state = self.ConversationState(user_id, user_name)

        # 初始化知识维度
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in self.dimensions.items()}

        # 获取用户已有资料，标记已收集的信息
        existing_profile = self._get_existing_profile(user_id)
        if existing_profile:
            self._mark_existing_info(state, existing_profile)

        # 生成欢迎消息 - 根据已有信息个性化
        ai_message = self._generate_welcome_message(user_name, existing_profile)

        self.sessions[user_id] = state

        # 初始了解度评估（基于已有资料）
        self._evaluate_understanding(state)

        logger.info(f"AI Native conversation started for user {user_id}, initial understanding: {state.overall_understanding:.2f}")

        collected_dims = [d.name for k, d in state.knowledge_base.items() if d.collected]

        return {
            "user_id": user_id,
            "user_name": user_name,
            "ai_message": ai_message,
            "current_stage": "dynamic_conversation",
            "is_completed": False,
            "understanding_level": round(state.overall_understanding, 2),
            "collected_dimensions": collected_dims,
        }

    def _get_existing_profile(self, user_id: str) -> Optional[Dict]:
        """
        获取用户已有的资料信息

        Args:
            user_id: 用户 ID

        Returns:
            用户已有资料字典，包含已填写的基本信息
        """
        try:
            with db_session_readonly() as db:
                user = db.query(UserDB).filter(UserDB.id == user_id).first()
                if not user:
                    return None

                profile = {
                    "name": user.name,
                    "age": user.age,
                    "gender": user.gender,
                    "location": user.location,
                    "bio": user.bio,
                    "interests": user.interests,
                    "goal": getattr(user, "goal", None),
                    # 从 preferred 字段提取偏好
                    "preferred_age_min": user.preferred_age_min,
                    "preferred_age_max": user.preferred_age_max,
                    "preferred_location": user.preferred_location,
                    "preferred_gender": user.preferred_gender,
                }

                # 过滤掉空值
                existing = {k: v for k, v in profile.items() if v is not None and v != "" and v != []}
                logger.info(f"User {user_id} existing profile fields: {list(existing.keys())}")
                return existing

        except Exception as e:
            logger.error(f"Failed to get existing profile for user {user_id}: {e}")
            return None

    def _mark_existing_info(self, state: ConversationState, existing_profile: Dict) -> None:
        """
        标记用户已有信息为已收集状态

        Args:
            state: 对话状态
            existing_profile: 用户已有资料
        """
        # 基本信息 - 年龄、性别、位置等
        basic_fields = ["name", "age", "gender", "location"]
        basic_data = {}
        for field in basic_fields:
            if field in existing_profile:
                basic_data[field] = existing_profile[field]

        if basic_data:
            state.knowledge_base["basic"].collected = True
            state.knowledge_base["basic"].confidence = 1.0  # 数据库信息可信度最高
            state.knowledge_base["basic"].raw_data = basic_data

        # 兴趣爱好
        if "interests" in existing_profile:
            interests = existing_profile["interests"]
            if isinstance(interests, list) and len(interests) > 0:
                state.knowledge_base["interests"].collected = True
                state.knowledge_base["interests"].confidence = 1.0
                state.knowledge_base["interests"].raw_data = interests
            elif isinstance(interests, str) and interests:
                # 尝试解析 JSON 或逗号分隔的字符串
                try:
                    parsed = json.loads(interests)
                    if parsed:
                        state.knowledge_base["interests"].collected = True
                        state.knowledge_base["interests"].confidence = 1.0
                        state.knowledge_base["interests"].raw_data = parsed
                except:
                    if interests:
                        state.knowledge_base["interests"].collected = True
                        state.knowledge_base["interests"].confidence = 1.0
                        state.knowledge_base["interests"].raw_data = interests.split(",")

        # 关系目标
        if "goal" in existing_profile:
            state.knowledge_base["relationship_goal"].collected = True
            state.knowledge_base["relationship_goal"].confidence = 1.0
            state.knowledge_base["relationship_goal"].raw_data = existing_profile["goal"]

        # 个人简介可能包含性格、生活方式等线索
        if "bio" in existing_profile and existing_profile["bio"]:
            # 标记为部分收集，后续可以通过对话深入了解
            bio_text = existing_profile["bio"]
            # 简单判断：bio 超过 20 字符认为有有价值信息
            if len(bio_text) >= 20:
                state.knowledge_base["lifestyle"].collected = True
                state.knowledge_base["lifestyle"].confidence = 0.5  # 简介信息置信度较低，需要深入
                state.knowledge_base["lifestyle"].raw_data = {"bio_hint": bio_text[:100]}

    def _generate_welcome_message(self, user_name: str, existing_profile: Optional[Dict]) -> str:
        """
        AI 动态生成个性化欢迎消息

        Args:
            user_name: 用户名称
            existing_profile: 用户已有资料

        Returns:
            AI 生成的欢迎消息
        """
        # 构建用户信息摘要
        info_parts = []
        if existing_profile:
            if existing_profile.get("age"):
                info_parts.append(f"年龄：{existing_profile['age']}岁")
            if existing_profile.get("location"):
                info_parts.append(f"所在地：{existing_profile['location']}")
            if existing_profile.get("gender"):
                info_parts.append(f"性别：{existing_profile['gender']}")

            # 处理兴趣
            interests = existing_profile.get("interests")
            if interests:
                interest_list = []
                if isinstance(interests, list):
                    interest_list = [i for i in interests if i]
                elif isinstance(interests, str) and interests.strip() and interests != "[]":
                    try:
                        parsed = json.loads(interests)
                        if isinstance(parsed, list):
                            interest_list = [i for i in parsed if i]
                    except:
                        interest_list = [i.strip() for i in interests.split(",") if i.strip()]
                if interest_list:
                    info_parts.append(f"兴趣爱好：{', '.join(interest_list[:3])}")

        # 构建 prompt
        if info_parts:
            prompt = f"""用户刚注册完成，已有以下资料：
{chr(10).join(info_parts)}

请生成一段简短的欢迎消息（30-60字）：
1. 友好地问候用户（名字：{user_name}）
2. 自然地提及已知的用户信息
3. 引导用户分享感情期待

要求：语气温暖亲切，像朋友聊天，适当用 emoji。直接输出消息内容，不要其他文字。"""
        else:
            prompt = f"""用户刚注册完成，还没有填写任何资料。
请生成一段简短的欢迎消息（30-50字）：
1. 友好地问候用户（名字：{user_name}）
2. 表示想要了解用户
3. 询问用户的感情期待

要求：语气温暖亲切，像朋友聊天，适当用 emoji。直接输出消息内容，不要其他文字。"""

        try:
            response = call_llm(prompt, temperature=0.8, max_tokens=150, timeout=10)
            return response.strip()
        except Exception as e:
            logger.warning(f"Failed to generate AI welcome message: {e}")
            # 快速 fallback，不依赖 LLM
            if info_parts:
                return f"你好呀，{user_name}～ 我注意到你已经填写了资料。让我了解一下你的感情期待吧，你希望通过这里找到什么样的关系呢？"
            else:
                return f"你好呀，{user_name}～ 很高兴认识你！让我了解一下你吧，你希望通过这里找到什么样的关系呢？"

    def process_user_message(self, user_id: str, user_message: str) -> Dict:
        """
        处理用户消息 - AI Native 核心方法

        优化：一次 LLM 调用同时完成信息提取和回复生成

        Args:
            user_id: 用户 ID
            user_message: 用户消息

        Returns:
            处理结果，包含 AI 回复和当前状态
        """
        if user_id not in self.sessions:
            logger.warning(f"No session for user {user_id}, creating new one")
            return self.start_conversation(user_id, "朋友")

        state = self.sessions[user_id]
        state.last_active_at = datetime.now()

        # 记录对话历史
        state.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
        })

        # 一次 LLM 调用完成信息提取 + 回复生成（优化点）
        llm_result = self._process_with_llm(state, user_message)

        # 更新知识图谱
        self._update_knowledge_base(state, llm_result)
        ai_message = llm_result.get("ai_response", "抱歉，我没听清，能再说一次吗？")

        # 评估了解度
        self._evaluate_understanding(state)

        # 决定是否结束对话
        if state.overall_understanding >= 0.7:
            state.is_completed = True
            ai_message = self._generate_farewell_message(state)

        # 记录 AI 回复
        state.conversation_history.append({
            "role": "assistant",
            "content": ai_message,
            "timestamp": datetime.now().isoformat(),
        })

        # 返回结果
        collected_dims = [d.name for k, d in state.knowledge_base.items() if d.collected]

        return {
            "user_id": user_id,
            "ai_message": ai_message,
            "current_stage": "dynamic_conversation",
            "is_completed": state.is_completed,
            "understanding_level": round(state.overall_understanding, 2),
            "collected_dimensions": collected_dims,
            "conversation_count": len(state.conversation_history) // 2,
        }

    async def process_user_message_stream(self, user_id: str, user_message: str):
        """
        流式处理用户消息 - 优化响应速度

        使用 LLM 流式输出，让前端逐字显示 AI 回复。

        Args:
            user_id: 用户 ID
            user_message: 用户消息

        Yields:
            流式数据块（dict）
        """
        if user_id not in self.sessions:
            logger.warning(f"No session for user {user_id}, creating new one")
            result = self.start_conversation(user_id, "朋友")
            yield {"type": "message", "content": result["ai_message"]}
            yield {"type": "done", "data": result}
            return

        state = self.sessions[user_id]
        state.last_active_at = datetime.now()

        # 记录用户消息
        state.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
        })

        # 构建流式 prompt
        prompt = self._build_stream_prompt(state, user_message)

        # 流式调用 LLM（真正的异步流式）
        full_response = ""
        try:
            async for chunk in call_llm_stream_async(prompt, temperature=0.7):
                full_response += chunk
                yield {"type": "chunk", "content": chunk}

        except Exception as e:
            logger.error(f"Stream LLM failed: {e}")
            yield {"type": "chunk", "content": "抱歉，我刚才走神了，能再说一次吗？😊"}
            full_response = "抱歉，我刚才走神了，能再说一次吗？😊"

        # 从完整回复中提取信息
        extracted_info = self._extract_from_response(full_response)
        self._update_knowledge_base(state, {"extractions": extracted_info})

        # 评估了解度
        self._evaluate_understanding(state)

        # 检查是否完成
        is_completed = state.overall_understanding >= 0.7
        if is_completed:
            state.is_completed = True

        # 记录 AI 回复
        state.conversation_history.append({
            "role": "assistant",
            "content": full_response,
            "timestamp": datetime.now().isoformat(),
        })

        # 返回最终状态
        collected_dims = [d.name for k, d in state.knowledge_base.items() if d.collected]
        yield {
            "type": "done",
            "data": {
                "user_id": user_id,
                "ai_message": full_response,
                "current_stage": "dynamic_conversation",
                "is_completed": is_completed,
                "understanding_level": round(state.overall_understanding, 2),
                "collected_dimensions": collected_dims,
                "conversation_count": len(state.conversation_history) // 2,
            }
        }

    def _build_stream_prompt(self, state: ConversationState, user_message: str) -> str:
        """
        构建流式输出的 prompt（简化版，只生成回复）

        Args:
            state: 对话状态
            user_message: 用户消息

        Returns:
            prompt 字符串
        """
        # 构建对话上下文
        recent_history = state.conversation_history[-6:]
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history])

        # 已收集的信息
        collected_summary = []
        for dim in state.knowledge_base.values():
            if dim.collected and dim.raw_data:
                collected_summary.append(f"- {dim.name}: {dim.raw_data}")

        # 确定下一个要了解的维度
        next_dimension = None
        for dim_key, dim in sorted(state.knowledge_base.items(), key=lambda x: x[1].priority):
            if not dim.collected:
                next_dimension = dim
                break

        # 已有信息提醒
        existing_info_reminder = ""
        if state.knowledge_base["basic"].collected and state.knowledge_base["basic"].raw_data:
            basic_data = state.knowledge_base["basic"].raw_data
            if isinstance(basic_data, dict):
                fields = [f"{k}: {v}" for k, v in basic_data.items()]
                if fields:
                    existing_info_reminder = f"\n⚠️ 用户已填写（不要重复询问）：{', '.join(fields)}"

        return f"""{self.AI_PERSONA}
{existing_info_reminder}

## 对话上下文
{history_text}

## 用户刚说
{user_message}

## 已了解的用户信息
{chr(10).join(collected_summary) if collected_summary else "暂无"}

## 任务
生成你的回复（30-100 字）：
- 先回应刚才的话
- {"下一个话题：" + next_dimension.description if next_dimension else "准备结束对话，给出温暖的结束语"}
- 自然亲切，像朋友聊天
- 一次只问一个问题
- 适当用 emoji

直接回复，不要其他内容："""

    def _extract_from_response(self, response: str) -> Dict:
        """
        从 AI 回复中推断已获取的信息（简化版）

        基于 LLM 已生成的回复内容推断用户可能透露的信息。
        这是一个轻量级方法，避免额外的 LLM 调用。

        Args:
            response: AI 回复内容

        Returns:
            推断的信息
        """
        # 简单推断：如果回复中提到某些关键词，认为相关信息已被收集
        # 这里不做复杂的 NLP，依赖对话上下文自然积累
        return {}

    def _process_with_llm(self, state: ConversationState, user_message: str) -> Dict:
        """
        一次 LLM 调用完成：信息提取 + 回复生成

        Args:
            state: 对话状态
            user_message: 用户消息

        Returns:
            提取的信息和 AI 回复
        """
        # 构建对话上下文
        recent_history = state.conversation_history[-8:]
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history])

        # 已收集的信息摘要（包含置信度）
        collected_summary = []
        for dim in state.knowledge_base.values():
            if dim.collected and dim.raw_data:
                confidence_str = "（已确认）" if dim.confidence >= 0.9 else "（部分了解）"
                collected_summary.append(f"- {dim.name}{confidence_str}: {dim.raw_data}")

        # 确定下一个要了解的维度（跳过已收集的）
        next_dimension = None
        for dim_key, dim in sorted(state.knowledge_base.items(), key=lambda x: x[1].priority):
            if not dim.collected:
                next_dimension = dim
                break

        # 构建已有信息提醒（防止重复询问）
        existing_info_reminder = ""
        if state.knowledge_base["basic"].collected and state.knowledge_base["basic"].raw_data:
            basic_data = state.knowledge_base["basic"].raw_data
            if isinstance(basic_data, dict):
                fields = []
                for k, v in basic_data.items():
                    fields.append(f"{k}: {v}")
                if fields:
                    existing_info_reminder = f"\n⚠️ 注意：用户已在注册时填写了以下信息，不要重复询问：{', '.join(fields)}"

        prompt = f"""{self.AI_PERSONA}
{existing_info_reminder}

## 当前对话
{history_text}

## 用户刚说
{user_message}

## 已了解的用户信息
{chr(10).join(collected_summary) if collected_summary else "暂无"}

## 任务
请同时完成两件事：

### 1. 提取信息
从用户消息中提取以下维度的信息（如果有）：
- basic: 基本信息（姓名、年龄、职业、家乡等）【注意：如果已在注册时填写，不要重复提取】
- relationship_goal: 关系期望（恋爱/结婚/交友等）
- ideal_type: 理想型描述
- personality: 性格特点
- lifestyle: 生活方式
- interests: 兴趣爱好
- values: 价值观/底线

### 2. 生成回复
{"下一个话题方向：" + next_dimension.description if next_dimension else "已足够了解用户，准备结束对话"}

## 返回格式（JSON）
```json
{{
    "extractions": {{
        "basic": "提取到的内容或 null",
        "relationship_goal": "提取到的内容或 null",
        "ideal_type": "提取到的内容或 null",
        "personality": "提取到的内容或 null",
        "lifestyle": "提取到的内容或 null",
        "interests": "提取到的内容或 null",
        "values": "提取到的内容或 null"
    }},
    "ai_response": "你的回复（30-100字，自然亲切，适当用emoji）"
}}
```

只返回 JSON，不要其他内容。"""

        try:
            response = call_llm(prompt, temperature=0.7)
            result = self._parse_json_response(response)
            logger.info(f"LLM processed: extractions={bool(result.get('extractions'))}, response_len={len(result.get('ai_response', ''))}")
            return result
        except Exception as e:
            logger.error(f"LLM process failed: {e}")
            return {
                "extractions": {},
                "ai_response": "嗯嗯，我理解～ 能再跟我说说吗？😊"
            }

    def _understand_message(self, state: ConversationState, user_message: str) -> Dict:
        """
        使用 LLM 理解用户消息

        提取：
        - 意图（回答/提问/闲聊）
        - 情感（积极/消极/中性）
        - 信息（各维度的具体内容）
        """
        # 构建 prompt
        recent_history = state.conversation_history[-6:]  # 最近 3 轮对话
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history])

        prompt = f"""
你是一个专业的 AI 助手，请分析以下对话中用户的回复：

{history_text}

用户最新回复：{user_message}

请分析：
1. 用户的意图（回答你的问题/提出新问题/闲聊）
2. 用户的情感倾向（积极/消极/中性/期待/犹豫）
3. 从回复中提取与以下维度相关的信息：
   - 基本信息（姓名、年龄、职业、家乡、居住地等）
   - 关系期望（认真恋爱/结婚/交友/其他）
   - 理想型描述
   - 性格特点
   - 生活方式
   - 兴趣爱好
   - 价值观/底线

请以 JSON 格式返回：
{{
    "intent": "回答/提问/闲聊",
    "emotion": "积极/消极/中性",
    "extractions": {{
        "basic": "提取的内容或 null",
        "relationship_goal": "提取的内容或 null",
        "ideal_type": "提取的内容或 null",
        "personality": "提取的内容或 null",
        "lifestyle": "提取的内容或 null",
        "interests": "提取的内容或 null",
        "values": "提取的内容或 null"
    }},
    "confidence": 0.0-1.0,
    "follow_up_suggestion": "建议追问什么"
}}
"""

        try:
            response = call_llm(prompt, temperature=0.3)
            # 解析 JSON（处理 markdown 代码块包裹的情况）
            result = self._parse_json_response(response)
            logger.info(f"LLM understanding: {result.get('intent', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"Failed to understand message: {e}")
            # 降级处理
            return {
                "intent": "回答",
                "emotion": "中性",
                "extractions": {},
                "confidence": 0.5,
                "follow_up_suggestion": "继续了解用户",
            }

    def _parse_json_response(self, response: str) -> Dict:
        """解析 LLM 返回的 JSON 响应（处理 markdown 代码块包裹）"""
        # 移除 markdown 代码块标记
        if "```json" in response:
            response = response.split("```json")[1]
        if "```" in response:
            response = response.split("```")[0]
        # 移除首尾空白
        response = response.strip()
        # 解析 JSON
        return json.loads(response)

    def _update_knowledge_base(self, state: ConversationState, extracted_info: Dict):
        """更新知识图谱"""
        extractions = extracted_info.get("extractions", {})
        confidence = extracted_info.get("confidence", 0.5)

        for dim_key, content in extractions.items():
            if content and dim_key in state.knowledge_base:
                dim = state.knowledge_base[dim_key]
                dim.collected = True
                dim.confidence = confidence
                dim.raw_data = content
                # 安全地将内容转换为字符串并截断
                content_str = str(content) if not isinstance(content, dict) else json.dumps(content, ensure_ascii=False)[:50]
                logger.info(f"Updated {dim.name}: {content_str[:50]}...")

    def _evaluate_understanding(self, state: ConversationState):
        """评估整体了解度"""
        total_weight = 0
        weighted_score = 0

        for dim in state.knowledge_base.values():
            weight = (8 - dim.priority) / 7  # 优先级越高权重越大
            total_weight += weight
            if dim.collected:
                weighted_score += weight * dim.confidence

        state.overall_understanding = weighted_score / total_weight if total_weight > 0 else 0
        logger.info(f"Understanding level: {state.overall_understanding:.2f}")

    def _generate_ai_response(self, state: ConversationState, user_message: str) -> str:
        """
        生成 AI 回复

        使用 LLM 生成自然、有个性的回复，包括：
        1. 共情/回应
        2. 追问下一个话题（跳过已收集的信息）
        """
        # 确定下一个要了解的维度（跳过已收集的）
        next_dimension = None
        for dim_key, dim in sorted(state.knowledge_base.items(), key=lambda x: x[1].priority):
            if not dim.collected:
                next_dimension = dim
                break

        # 构建对话上下文
        recent_history = state.conversation_history[-8:]
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history])

        # 收集到的信息摘要（包含置信度）
        collected_summary = []
        for dim in state.knowledge_base.values():
            if dim.collected and dim.raw_data:
                confidence_str = "（已确认）" if dim.confidence >= 0.9 else "（部分了解）"
                collected_summary.append(f"{dim.name}{confidence_str}: {dim.raw_data}")

        # 构建已有信息提醒
        existing_info_reminder = ""
        if state.knowledge_base["basic"].collected and state.knowledge_base["basic"].raw_data:
            basic_data = state.knowledge_base["basic"].raw_data
            if isinstance(basic_data, dict):
                fields = []
                for k, v in basic_data.items():
                    fields.append(f"{k}: {v}")
                if fields:
                    existing_info_reminder = f"\n⚠️ 用户已填写信息（不要重复询问）：{', '.join(fields)}"

        prompt = f"""
{self.AI_PERSONA}
{existing_info_reminder}

当前对话上下文：
{history_text}

你已经了解到的用户信息：
{chr(10).join(collected_summary) if collected_summary else "暂无"}

用户刚刚说：{user_message}

{"下一个话题建议：" + next_dimension.description if next_dimension else "已经足够了解用户，准备结束对话"}

请生成你的回复：
- 先回应用户刚才的话（共情/理解/赞同）
- 然后自然地引入下一个话题或追问
- 语气自然亲切，像朋友聊天
- 一次只问一个问题
- ⚠️ 不要询问用户已填写的信息（如年龄、性别等）
- 适当使用 emoji（🌸 ✨ 💕 😊）但不要太多
- 回复长度 30-100 字

你的回复：
"""

        try:
            response = call_llm(prompt, temperature=0.7)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}")
            # 降级处理
            fallback_responses = [
                "嗯嗯，我理解～ 那能跟我多说说你的兴趣爱好吗？😊",
                "听起来很棒！对了，你平时周末都喜欢做什么呢？🌸",
                "我懂你～ 话说你理想中的另一半是什么样的？✨",
            ]
            return random.choice(fallback_responses)

    def _generate_farewell_message(self, state: ConversationState) -> str:
        """生成结束语"""
        # 总结已了解的信息
        collected_summary = []
        for dim in state.knowledge_base.values():
            if dim.collected and dim.raw_data:
                collected_summary.append(f"• {dim.name}: {dim.raw_data}")

        prompt = f"""
你是 AI 助手，已经通过对话充分了解了用户。

已知用户信息：
{chr(10).join(collected_summary)}

请生成一段温暖的结束语：
1. 感谢用户的分享
2. 简单总结你了解到的关键信息
3. 告诉用户接下来可以做什么（完善资料、开始匹配等）
4. 语气温暖、鼓励、有期待感
5. 适当使用 emoji

你的回复：
"""

        try:
            response = call_llm(prompt, temperature=0.7)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate farewell: {e}")
            return "太好了～ 我已经对你有了初步的了解！接下来你可以开始查看匹配推荐，或者继续完善资料。祝你在这里找到属于自己的缘分 🌸"

    def get_session_status(self, user_id: str) -> Dict:
        """获取会话状态"""
        if user_id not in self.sessions:
            return {"exists": False}

        state = self.sessions[user_id]
        collected_dims = [
            {"name": d.name, "confidence": d.confidence, "data": d.raw_data}
            for d in state.knowledge_base.values() if d.collected
        ]

        return {
            "exists": True,
            "user_id": state.user_id,
            "user_name": state.user_name,
            "is_completed": state.is_completed,
            "understanding_level": round(state.overall_understanding, 2),
            "collected_dimensions": collected_dims,
            "conversation_count": len(state.conversation_history) // 2,
            "created_at": state.created_at.isoformat(),
            "last_active_at": state.last_active_at.isoformat(),
        }


# 全局服务实例
ai_native_conversation_service = AINativeConversationService()
