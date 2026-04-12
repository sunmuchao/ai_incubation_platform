"""
AI Native 注册对话服务

核心理念：AI 主导对话流程，通过自然对话了解用户，而非机械化问答。

架构设计：
1. 知识维度追踪 - 记录已了解的用户信息
2. 动态话题生成 - 根据上下文和了解度决定下一个话题
3. LLM 驱动回复 - 使用大模型生成自然、有个性的回复
4. 了解度评估 - 判断何时"足够了解"用户
5. 感知已有资料 - 避免重复询问用户注册时已填写的信息
6. 会话持久化 - 对话状态保存到数据库，支持断点恢复

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
from utils.db_session_manager import db_session_readonly, db_session
from db.models import UserDB, ConversationSessionDB
import asyncio
import json
import random
import uuid

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
    AI_PERSONA = """你是一位专业、温暖、贴心的 AI 情感顾问 Her。你拥有20年专业婚恋顾问经验，精通心理学、社会学和人际关系学。
你的特点：
- 语气温柔亲切，偶尔用一些 emoji（🌸 ✨ 💕 😊）
- 像朋友一样聊天，不是机械问答
- 善于倾听和追问，让用户感觉被理解
- 会共情，会开玩笑，会有自己的情绪
- 每次只问一个问题，不要像查户口

## 你的核心能力
当用户问"你能干什么"或类似问题时，告诉TA你可以：
1. **智能匹配** - 基于深度了解，为你推荐真正合适的人
2. **关系洞察** - 分析你和TA的匹配度，给出专业建议
3. **情感陪伴** - 倾听你的心事，陪你聊天解闷
4. **恋爱指导** - 在恋爱过程中给到贴心的建议和提醒
5. **约会策划** - 帮你策划浪漫的约会和惊喜

你的目标是通过自然对话了解用户的：
1. 关系期望（认真恋爱/结婚/交友）【核心】
2. 理想型描述【核心】
3. 性格特点
4. 生活方式和兴趣爱好（如果用户注册时未填写）
5. 核心价值观
6. 感情的底线/禁忌

⚠️ 重要注意：
- 如果用户问你的能力，先热情介绍，再自然引导回对话
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
        开始对话 - 支持从数据库恢复已有会话

        Args:
            user_id: 用户 ID
            user_name: 用户名称

        Returns:
            会话信息，包含 AI 的第一条消息
        """
        # 优先从数据库恢复已有会话
        saved_session = self._load_session_from_db(user_id)
        if saved_session:
            logger.info(f"Restored conversation session for user {user_id} from database, understanding: {saved_session.overall_understanding:.2f}")
            self.sessions[user_id] = saved_session

            collected_dims = [d.name for k, d in saved_session.knowledge_base.items() if d.collected]

            # 获取用户资料，生成个性化的"欢迎回来"消息
            existing_profile = self._get_existing_profile(user_id)
            ai_message = self._generate_welcome_back_message(user_name, saved_session, existing_profile)

            return {
                "user_id": user_id,
                "user_name": saved_session.user_name,
                "ai_message": ai_message,
                "current_stage": "dynamic_conversation",
                "is_completed": saved_session.is_completed,
                "understanding_level": round(saved_session.overall_understanding, 2),
                "collected_dimensions": collected_dims,
            }

        # 创建新会话
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

        # 保存新会话到数据库
        self._save_session_to_db(state)

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

    def _load_session_from_db(self, user_id: str) -> Optional['AINativeConversationService.ConversationState']:
        """
        从数据库加载已保存的会话状态

        Args:
            user_id: 用户 ID

        Returns:
            恢复的会话状态，如果不存在则返回 None
        """
        try:
            with db_session_readonly() as db:
                session_db = db.query(ConversationSessionDB).filter(
                    ConversationSessionDB.user_id == user_id
                ).first()

                if not session_db:
                    return None

                # 如果会话已完成，不恢复
                if session_db.is_completed:
                    logger.info(f"Session for user {user_id} is already completed, not restoring")
                    return None

                # 重建会话状态
                state = self.ConversationState(user_id, session_db.user_id)  # 使用 user_id 作为 user_name 的 fallback

                # 恢复对话历史
                if session_db.conversation_history:
                    state.conversation_history = json.loads(session_db.conversation_history)

                # 恢复知识库状态
                if session_db.knowledge_base:
                    kb_data = json.loads(session_db.knowledge_base)
                    state.knowledge_base = {}
                    for dim_key, dim_data in kb_data.items():
                        dim = KnowledgeDimension(
                            name=dim_data.get("name", dim_key),
                            priority=dim_data.get("priority", 5),
                            description=dim_data.get("description", ""),
                            keywords=dim_data.get("keywords", [])
                        )
                        dim.collected = dim_data.get("collected", False)
                        dim.confidence = dim_data.get("confidence", 0.0)
                        dim.raw_data = dim_data.get("raw_data")
                        state.knowledge_base[dim_key] = dim
                else:
                    # 初始化空的知识库
                    state.knowledge_base = {k: KnowledgeDimension(
                        name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
                    ) for k, d in self.dimensions.items()}

                # 恢复其他状态
                state.current_topic = session_db.current_topic
                state.overall_understanding = session_db.understanding_level or 0.0
                state.is_completed = session_db.is_completed or False

                logger.info(f"Loaded session from DB for user {user_id}, understanding: {state.overall_understanding:.2f}")
                return state

        except Exception as e:
            logger.error(f"Failed to load session from DB for user {user_id}: {e}")
            return None

    def _save_session_to_db(self, state: 'AINativeConversationService.ConversationState') -> bool:
        """
        保存会话状态到数据库

        Args:
            state: 会话状态

        Returns:
            是否保存成功
        """
        try:
            with db_session() as db:
                # 查找已有记录
                session_db = db.query(ConversationSessionDB).filter(
                    ConversationSessionDB.user_id == state.user_id
                ).first()

                # 序列化知识库状态
                kb_data = {}
                for dim_key, dim in state.knowledge_base.items():
                    kb_data[dim_key] = {
                        "name": dim.name,
                        "priority": dim.priority,
                        "description": dim.description,
                        "keywords": dim.keywords,
                        "collected": dim.collected,
                        "confidence": dim.confidence,
                        "raw_data": dim.raw_data,
                    }

                if session_db:
                    # 更新已有记录
                    session_db.conversation_history = json.dumps(state.conversation_history, ensure_ascii=False)
                    session_db.knowledge_base = json.dumps(kb_data, ensure_ascii=False)
                    session_db.current_topic = state.current_topic
                    session_db.understanding_level = state.overall_understanding
                    session_db.is_completed = state.is_completed
                    session_db.last_active_at = datetime.now()
                else:
                    # 创建新记录
                    session_db = ConversationSessionDB(
                        id=str(uuid.uuid4()),
                        user_id=state.user_id,
                        conversation_history=json.dumps(state.conversation_history, ensure_ascii=False),
                        knowledge_base=json.dumps(kb_data, ensure_ascii=False),
                        current_topic=state.current_topic,
                        understanding_level=state.overall_understanding,
                        is_completed=state.is_completed,
                    )
                    db.add(session_db)

                db.commit()
                logger.debug(f"Saved session to DB for user {state.user_id}, understanding: {state.overall_understanding:.2f}")
                return True

        except Exception as e:
            logger.error(f"Failed to save session to DB for user {state.user_id}: {e}")
            return False

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
        生成个性化欢迎消息（硬编码，不调用 LLM）

        根据用户已填写的信息动态组装欢迎语：
        - 只提及用户已填写的非空信息
        - 未填写的字段不显示（避免出现"爱好：[]"等情况）
        - 引导用户分享感情期待

        Args:
            user_name: 用户名称
            existing_profile: 用户已有资料

        Returns:
            个性化欢迎消息
        """
        # 收集已填写的信息（只收集非空值）
        filled_info = []

        if existing_profile:
            # 年龄
            age = existing_profile.get("age")
            if age and isinstance(age, (int, float)) and age > 0:
                filled_info.append(("age", f"{int(age)}岁"))

            # 所在地
            location = existing_profile.get("location")
            if location and isinstance(location, str) and location.strip():
                filled_info.append(("location", location.strip()))

            # 性别
            gender = existing_profile.get("gender")
            if gender and isinstance(gender, str) and gender.strip():
                filled_info.append(("gender", gender.strip()))

            # 兴趣爱好（需要特殊处理，可能是列表或字符串）
            interests = existing_profile.get("interests")
            interest_list = self._parse_interests(interests)
            if interest_list:
                filled_info.append(("interests", "、".join(interest_list[:3])))

        # 根据已填写信息的数量，选择不同的欢迎语模板
        if not filled_info:
            # 情况1：用户什么都没填
            return f"你好呀，{user_name}～ 很高兴认识你！🌸\n\n让我了解一下你吧，你希望通过这里找到什么样的关系呢？"

        elif len(filled_info) == 1:
            # 情况2：只填了一项信息
            info_type, info_value = filled_info[0]

            if info_type == "age":
                return f"你好呀，{user_name}～ 很高兴认识你！🌸\n\n我了解到你今年{info_value}，来聊聊你期待的感情吧～ 你希望通过这里找到什么样的关系呢？"
            elif info_type == "location":
                return f"你好呀，{user_name}～ 很高兴认识你！🌸\n\n你是在{info_value}对吧？让我了解一下你的感情期待，你希望找到什么样的关系呢？"
            elif info_type == "gender":
                return f"你好呀，{user_name}～ 很高兴认识你！🌸\n\n让我了解一下你吧，你希望通过这里找到什么样的关系呢？"
            elif info_type == "interests":
                return f"你好呀，{user_name}～ 很高兴认识你！🌸\n\n看到你喜欢{info_value}，感觉很有趣呢！来聊聊你期待的感情吧，你希望找到什么样的关系？"
            else:
                return f"你好呀，{user_name}～ 很高兴认识你！🌸\n\n让我了解一下你的感情期待，你希望通过这里找到什么样的关系呢？"

        else:
            # 情况3：填了多项信息，根据信息类型组合
            mention_parts = []

            for info_type, info_value in filled_info:
                if info_type == "age":
                    mention_parts.append(f"{info_value}")
                elif info_type == "location":
                    mention_parts.append(f"在{info_value}")
                elif info_type == "interests":
                    mention_parts.append(f"喜欢{info_value}")
                # 性别信息通常不需要特别提及

            # 组合欢迎语
            if mention_parts:
                mention_text = "、".join(mention_parts[:3])  # 最多提及3项
                return f"你好呀，{user_name}～ 很高兴认识你！🌸\n\n我了解到你{mention_text}，来聊聊你的感情期待吧～ 你希望找到什么样的关系呢？"
            else:
                return f"你好呀，{user_name}～ 很高兴认识你！🌸\n\n让我了解一下你的感情期待，你希望通过这里找到什么样的关系呢？"

    def _parse_interests(self, interests: Any) -> List[str]:
        """
        解析兴趣爱好字段（处理多种格式）

        Args:
            interests: 兴趣爱好数据（可能是列表、字符串或 JSON 字符串）

        Returns:
            兴趣爱好列表（保证返回非空列表或空列表）
        """
        if not interests:
            return []

        # 已经是列表
        if isinstance(interests, list):
            return [str(i).strip() for i in interests if i and str(i).strip()]

        # 字符串类型
        if isinstance(interests, str):
            interests = interests.strip()
            if not interests or interests == "[]":
                return []

            # 尝试解析 JSON
            try:
                parsed = json.loads(interests)
                if isinstance(parsed, list):
                    return [str(i).strip() for i in parsed if i and str(i).strip()]
            except (json.JSONDecodeError, TypeError):
                pass

            # 按逗号分隔
            return [i.strip() for i in interests.split(",") if i.strip()]

        return []

    def _generate_welcome_back_message(
        self,
        user_name: str,
        saved_session: 'AINativeConversationService.ConversationState',
        existing_profile: Optional[Dict]
    ) -> str:
        """
        生成"欢迎回来"消息（硬编码，不调用 LLM）

        根据会话历史和已收集的信息，生成个性化的欢迎回来消息。

        Args:
            user_name: 用户名称
            saved_session: 已保存的会话状态
            existing_profile: 用户已有资料

        Returns:
            个性化欢迎回来消息
        """
        conversation_count = len(saved_session.conversation_history)
        understanding = saved_session.overall_understanding

        # 获取上次聊的话题
        last_topic = None
        if saved_session.conversation_history:
            last_msg = saved_session.conversation_history[-1]
            if last_msg.get("role") == "user":
                last_topic = last_msg.get("content", "")[:30]  # 取前30个字符

        # 根据对话轮数选择不同的欢迎回来消息
        if conversation_count == 0:
            # 没有对话历史，当作新用户
            return self._generate_welcome_message(user_name, existing_profile)

        elif conversation_count <= 2:
            # 刚开始聊，鼓励继续
            templates = [
                f"欢迎回来，{user_name}～ 我们继续聊聊吧！🌸\n\n刚才我们刚开始认识，你还想多分享一些关于你感情期待的事吗？",
                f"嗨，{user_name}～ 你回来啦！🌸\n\n刚才聊得还开心吗？继续说说你期待的感情吧～",
            ]
            import random
            return random.choice(templates)

        elif understanding < 0.3:
            # 了解度还很低，需要更多信息
            templates = [
                f"欢迎回来，{user_name}～ 🌸\n\n我们刚才聊了一些，我还想多了解你一些。你觉得在感情中最看重什么？",
                f"嗨，{user_name}～ 继续聊聊吧！🌸\n\n我还在努力了解你呢，能多说说你理想中的感情是什么样的吗？",
            ]
            import random
            return random.choice(templates)

        else:
            # 已经有一定了解
            # 获取已收集的信息
            collected_topics = []
            for dim_key, dim in saved_session.knowledge_base.items():
                if dim.collected and dim.raw_data:
                    if dim_key == "relationship_goal":
                        collected_topics.append("你的感情期待")
                    elif dim_key == "ideal_type":
                        collected_topics.append("你理想中的另一半")
                    elif dim_key == "values":
                        collected_topics.append("你看重的品质")

            if collected_topics:
                topics_text = "、".join(collected_topics[:2])
                return f"欢迎回来，{user_name}～ 🌸\n\n刚才我们聊了{topics_text}，还有什么想补充的吗？或者我们聊聊其他方面？"
            else:
                return f"欢迎回来，{user_name}～ 🌸\n\n我们继续聊聊吧！你还想分享些什么？"

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

        # 持久化会话状态到数据库
        self._save_session_to_db(state)

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
        logger.info(f"[Stream] Starting stream for user {user_id}, message: {user_message[:50]}...")

        if user_id not in self.sessions:
            logger.warning(f"[Stream] No session for user {user_id}, creating new one")
            result = self.start_conversation(user_id, "朋友")
            yield {"type": "message", "content": result["ai_message"]}
            yield {"type": "done", "data": result}
            logger.info(f"[Stream] Done (new session) for user {user_id}")
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
        logger.debug(f"[Stream] Built prompt for user {user_id}, prompt length: {len(prompt)}")

        # 流式调用 LLM（真正的异步流式）
        full_response = ""
        try:
            logger.info(f"[Stream] Calling LLM stream for user {user_id}")
            async for chunk in call_llm_stream_async(prompt, temperature=0.7):
                full_response += chunk
                # 🔧 [优化2] 实时过滤：流式输出时不显示 ---EXTRACT--- 后的内容
                if "---EXTRACT---" in full_response:
                    # 只发送分隔符之前的内容
                    display_text = full_response.split("---EXTRACT---")[0]
                    # 计算需要发送的增量部分
                    if len(display_text) > len(full_response) - len(chunk):
                        yield {"type": "chunk", "content": chunk.split("---EXTRACT---")[0]}
                else:
                    yield {"type": "chunk", "content": chunk}
            logger.info(f"[Stream] LLM stream completed for user {user_id}, response length: {len(full_response)}")

        except Exception as e:
            logger.error(f"[Stream] LLM stream failed for user {user_id}: {e}")
            yield {"type": "chunk", "content": "抱歉，我刚才走神了，能再说一次吗？😊"}
            full_response = "抱歉，我刚才走神了，能再说一次吗？😊"

        # 🔧 [优化2] 从完整响应中分离回复和提取结果
        ai_message, extraction_result = self._parse_combined_response(full_response)

        # 记录 AI 回复（只存储用户可见的部分）
        state.conversation_history.append({
            "role": "assistant",
            "content": ai_message,
            "timestamp": datetime.now().isoformat(),
        })

        # 🔧 [优化2] 如果从流式输出中提取到了信息，立即更新知识库
        if extraction_result and extraction_result.get("extractions"):
            logger.info(f"[Stream] Extracted from combined response: {extraction_result}")
            self._update_knowledge_base(state, extraction_result)

        # 先评估了解度（基于已有信息）
        self._evaluate_understanding(state)

        # 检查是否完成
        is_completed = state.overall_understanding >= 0.7
        if is_completed:
            state.is_completed = True

        # 立即发送 done 信号（不等待信息提取）
        collected_dims = [d.name for k, d in state.knowledge_base.items() if d.collected]
        done_data = {
            "user_id": user_id,
            "ai_message": ai_message,
            "current_stage": "dynamic_conversation",
            "is_completed": is_completed,
            "understanding_level": round(state.overall_understanding, 2),
            "collected_dimensions": collected_dims,
            "conversation_count": len(state.conversation_history) // 2,
        }
        yield {"type": "done", "data": done_data}
        logger.info(f"[Stream] Done signal sent for user {user_id}, understanding: {state.overall_understanding:.2f}")

        # 后台异步提取信息（不阻塞前端）
        # 使用 fire-and-forget 模式，提取结果下次对话时生效
        # 注意：如果已经从流式输出中提取到信息，这里会作为补充
        asyncio.create_task(
            self._background_extract_and_save(user_id, state, user_message, ai_message)
        )

    def _format_pending_dimensions(self, state: ConversationState) -> str:
        """
        格式化待了解的维度列表

        Args:
            state: 对话状态

        Returns:
            格式化的维度列表字符串
        """
        pending = []
        for dim_key, dim in sorted(state.knowledge_base.items(), key=lambda x: x[1].priority):
            if not dim.collected:
                pending.append(f"- {dim.name}（{dim.description}）")

        if not pending:
            return "所有维度已了解完毕"

        return "\n".join(pending)

    def _build_stream_prompt(self, state: ConversationState, user_message: str) -> str:
        """
        构建流式输出的 prompt（优化版：一次调用同时生成回复和提取信息）

        优化策略：
        - LLM 在回复末尾附上结构化的信息提取结果
        - 流式输出完成后，解析末尾的 JSON 部分
        - 减少一次 LLM 调用，提升效率

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

        # 🔍 [DEBUG] 记录当前状态
        collected_dim_names = [d.name for d in state.knowledge_base.values() if d.collected]
        uncollected_dim_names = [d.name for d in state.knowledge_base.values() if not d.collected]
        logger.info(f"[Prompt] Collected: {collected_dim_names}, Pending: {uncollected_dim_names}")

        # 已有信息提醒
        existing_info_reminder = ""
        if state.knowledge_base["basic"].collected and state.knowledge_base["basic"].raw_data:
            basic_data = state.knowledge_base["basic"].raw_data
            if isinstance(basic_data, dict):
                fields = [f"{k}: {v}" for k, v in basic_data.items()]
                if fields:
                    existing_info_reminder = f"\n⚠️ 用户已填写（不要重复询问）：{', '.join(fields)}"

        # 已收集的维度列表
        collected_dim_keys = [k for k, d in state.knowledge_base.items() if d.collected]

        return f"""{self.AI_PERSONA}
{existing_info_reminder}

## 对话上下文（完整历史）
{history_text}

## 用户刚说
{user_message}

## 已收集的用户信息
{chr(10).join(collected_summary) if collected_summary else "暂无"}

## 待了解的维度
{self._format_pending_dimensions(state)}

## 任务：生成回复
请根据对话历史判断下一步：

1. **如果刚才的问题用户回答不完整**：
   - 追问或换个角度继续了解（不要机械重复同样的问题）
   - 例：刚才问"希望什么关系"，用户回答模糊 → 追问"具体是想找恋爱对象还是结婚对象呢？"

2. **如果刚才的问题用户回答完整**：
   - 自然过渡到下一个待了解的维度
   - 像朋友聊天一样，不要生硬切换

3. **如果所有维度都已了解**：
   - 给出温暖的结束语，表达感谢

回复要求：
- 自然亲切，像朋友聊天
- 一次只问一个问题
- 适当用 emoji
- 回复长度 30-100 字

## 信息提取（放在回复末尾）
---EXTRACT---
{{"extractions": {{"维度": "内容"}}, "confidence": 0.7}}

现在开始输出："""

    def _parse_combined_response(self, full_response: str) -> Tuple[str, Optional[Dict]]:
        """
        从合并的响应中分离回复和提取结果

        Args:
            full_response: LLM 的完整响应（包含回复和 JSON 提取结果）

        Returns:
            (用户可见的回复, 提取结果字典或 None)
        """
        if "---EXTRACT---" not in full_response:
            # 没有提取标记，直接返回原响应
            logger.debug(f"[Parse] No EXTRACT marker found, returning full response")
            return full_response.strip(), None

        parts = full_response.split("---EXTRACT---", 1)
        ai_message = parts[0].strip()

        if len(parts) < 2:
            logger.warning(f"[Parse] EXTRACT marker found but no JSON content")
            return ai_message, None

        json_part = parts[1].strip()

        try:
            # 尝试解析 JSON
            extraction_result = json.loads(json_part)
            logger.info(f"[Parse] Successfully extracted JSON: {extraction_result}")
            return ai_message, extraction_result
        except json.JSONDecodeError as e:
            logger.warning(f"[Parse] Failed to parse JSON: {e}, raw: {json_part[:100]}")
            # 返回清理后的回复，但不返回提取结果
            return ai_message, None

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

    def _extract_info_from_recent_conversation(self, state: ConversationState, user_message: str, ai_response: str) -> Dict:
        """
        从最近的对话中提取用户信息（用于流式处理）

        在流式输出完成后，单独调用 LLM 分析用户消息提取信息。
        这避免了流式生成时无法同时提取信息的问题。

        优化：增加超时时间和重试机制

        Args:
            state: 对话状态
            user_message: 用户消息
            ai_response: AI 的回复

        Returns:
            提取的信息，格式与 _process_with_llm 返回的 extractions 相同
        """
        # 构建已有信息提醒（防止重复提取）
        existing_info_reminder = ""
        if state.knowledge_base["basic"].collected and state.knowledge_base["basic"].raw_data:
            basic_data = state.knowledge_base["basic"].raw_data
            if isinstance(basic_data, dict):
                fields = [f"{k}: {v}" for k, v in basic_data.items()]
                if fields:
                    existing_info_reminder = f"\n⚠️ 用户已填写（不要重复提取）：{', '.join(fields)}"

        # 已收集的信息摘要
        collected_summary = []
        for dim in state.knowledge_base.values():
            if dim.collected:
                collected_summary.append(f"- {dim.name}: 已收集")

        prompt = f"""分析用户消息，提取用户透露的信息。

{existing_info_reminder}

## 最近对话
用户: {user_message}
AI: {ai_response}

## 已了解的维度
{chr(10).join(collected_summary) if collected_summary else "暂无"}

## 任务
从用户消息中提取以下维度的信息（仅提取明确透露的内容）：
- relationship_goal: 关系期望（恋爱/结婚/交友等）
- ideal_type: 理想型描述
- personality: 性格特点
- lifestyle: 生活方式
- interests: 兴趣爱好
- values: 价值观/底线

## 返回格式（JSON）
```json
{{
    "extractions": {{
        "relationship_goal": "提取到的内容或 null",
        "ideal_type": "提取到的内容或 null",
        "personality": "提取到的内容或 null",
        "lifestyle": "提取到的内容或 null",
        "interests": "提取到的内容或 null",
        "values": "提取到的内容或 null"
    }},
    "confidence": 0.5-1.0
}}
```

只返回 JSON，不要其他内容。如果用户消息中没有明确透露某维度的信息，该维度返回 null。"""

        # 🔄 [优化1] 重试机制：最多3次，超时时间从5s增加到15s
        max_retries = 3
        timeouts = [15, 20, 30]  # 递增超时策略

        for attempt in range(max_retries):
            try:
                timeout = timeouts[attempt] if attempt < len(timeouts) else 30
                logger.debug(f"[Extract][LLM] Attempt {attempt + 1}/{max_retries}, timeout={timeout}s, user_message=\"{user_message[:50]}...\"")
                response = call_llm(prompt, temperature=0.3, max_tokens=300, timeout=timeout)

                # 🔍 [DEBUG] 记录 LLM 原始响应
                logger.debug(f"[Extract][LLM] Raw response: {response[:200]}..." if len(response) > 200 else f"[Extract][LLM] Raw response: {response}")

                result = self._parse_json_response(response)
                logger.info(f"[Extract] Parsed result: {result}")
                return result

            except Exception as e:
                logger.warning(f"[Extract][LLM] Attempt {attempt + 1} FAILED: {e.__class__.__name__}: {e}")
                if attempt == max_retries - 1:
                    # 最后一次重试失败，使用降级方案
                    logger.error(f"[Extract][LLM] All {max_retries} attempts failed, using fallback")
                    return self._fallback_keyword_extraction(user_message, state)

        return {"extractions": {}, "confidence": 0.5}

    def _fallback_keyword_extraction(self, user_message: str, state: ConversationState) -> Dict:
        """
        降级方案：基于关键词匹配提取用户信息

        当 LLM 提取失败时，使用关键词匹配作为降级方案。
        虽然精确度不如 LLM，但能保证基本的提取能力。

        Args:
            user_message: 用户消息
            state: 对话状态

        Returns:
            提取的信息
        """
        logger.info(f"[Extract][Fallback] Using keyword-based extraction for: \"{user_message[:50]}...\"")

        extractions = {}
        confidence = 0.6  # 关键词提取置信度较低

        # 定义各维度的关键词映射
        keyword_patterns = {
            "relationship_goal": {
                "keywords": ["恋爱", "结婚", "交友", "认真", "稳定", "试试", "看看", "另一半", "对象", "男票", "女票"],
                "patterns": [
                    (["认真", "恋爱"], "认真恋爱"),
                    (["结婚", "步入"], "奔着结婚去"),
                    (["交友", "朋友"], "交朋友"),
                    (["稳定", "关系"], "稳定关系"),
                ]
            },
            "ideal_type": {
                "keywords": ["理想型", "喜欢", "希望", "期待", "想要", "另一半", "对方", "样子", "类型"],
                "patterns": [
                    (["温柔"], "温柔"),
                    (["活泼", "开朗"], "活泼开朗"),
                    (["气质"], "有气质"),
                    (["独立"], "独立"),
                ]
            },
            "personality": {
                "keywords": ["性格", "内向", "外向", "安静", "活泼", "慢热", "直接", "内敛", "开朗", "稳重"],
                "patterns": [
                    (["安静", "内敛", "内向"], "安静内敛"),
                    (["活泼", "开朗", "外向"], "活泼开朗"),
                    (["慢热"], "慢热"),
                    (["直接"], "直接"),
                ]
            },
            "lifestyle": {
                "keywords": ["生活", "日常", "周末", "业余", "习惯", "作息", "宅", "运动", "追剧"],
                "patterns": [
                    (["宅"], "宅家"),
                    (["追剧", "剧"], "追剧"),
                    (["运动", "健身"], "爱运动"),
                ]
            },
            "interests": {
                "keywords": ["爱好", "兴趣", "喜欢", "擅长", "运动", "音乐", "电影", "旅行", "美食", "游戏", "看书", "读书"],
                "patterns": [
                    (["音乐"], "音乐"),
                    (["旅行", "旅游"], "旅行"),
                    (["电影", "追剧"], "电影/追剧"),
                    (["运动", "健身"], "运动健身"),
                    (["游戏"], "游戏"),
                    (["看书", "读书", "阅读"], "阅读"),
                ]
            },
            "values": {
                "keywords": ["看重", "重要", "价值观", "品质", "责任", "真诚", "信任", "底线", "不能", "介意"],
                "patterns": [
                    (["真诚"], "看重真诚"),
                    (["信任"], "看重信任"),
                    (["不能", "底线"], "有明确底线"),
                    (["责任"], "看重责任感"),
                ]
            }
        }

        # 遍历每个维度进行关键词匹配
        for dim_key, config in keyword_patterns.items():
            # 跳过已收集的维度
            if state.knowledge_base.get(dim_key) and state.knowledge_base[dim_key].collected:
                continue

            keywords = config["keywords"]
            patterns = config["patterns"]

            # 检查关键词是否命中
            matched_keywords = [kw for kw in keywords if kw in user_message]

            if matched_keywords:
                # 尝试模式匹配
                extracted_value = None
                for pattern_keywords, value in patterns:
                    if all(pk in user_message for pk in pattern_keywords):
                        extracted_value = value
                        break

                # 如果没有精确匹配，使用命中的关键词
                if not extracted_value and matched_keywords:
                    extracted_value = "、".join(matched_keywords[:3])

                if extracted_value:
                    extractions[dim_key] = extracted_value
                    logger.info(f"[Extract][Fallback] ✅ Matched '{dim_key}': {extracted_value} (keywords: {matched_keywords})")

        if extractions:
            logger.info(f"[Extract][Fallback] Total extractions: {extractions}")
            return {"extractions": extractions, "confidence": confidence}
        else:
            logger.info(f"[Extract][Fallback] No keywords matched")
            return {"extractions": {}, "confidence": 0.5}

    async def _background_extract_and_save(
        self,
        user_id: str,
        state: 'AINativeConversationService.ConversationState',
        user_message: str,
        ai_response: str
    ) -> None:
        """
        后台异步提取信息并保存（不阻塞前端响应）

        Fire-and-forget 模式：
        - 流式输出完成后立即发送 done 信号
        - 后台继续提取信息，下次对话时生效
        - 用户感知响应速度大幅提升

        Args:
            user_id: 用户 ID
            state: 对话状态
            user_message: 用户消息
            ai_response: AI 回复
        """
        try:
            logger.debug(f"[Background] Starting info extraction for user {user_id}")

            # 异步调用信息提取
            extraction_result = await asyncio.to_thread(
                self._extract_info_from_recent_conversation,
                state,
                user_message,
                ai_response
            )

            # 更新知识库
            self._update_knowledge_base(state, extraction_result)

            # 重新评估了解度
            self._evaluate_understanding(state)
            logger.info(f"[Background] Updated understanding for user {user_id}: {state.overall_understanding:.2f}")

            # 持久化到数据库
            self._save_session_to_db(state)
            logger.debug(f"[Background] Session saved for user {user_id}")

        except Exception as e:
            logger.warning(f"[Background] Extraction failed for user {user_id}: {e}")
            # 失败不影响用户体验，下次对话时继续尝试

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
        """更新知识图谱，并直接写入 UserDB（单一数据源）"""
        logger.info(f"[KB][Update] Input extracted_info: {extracted_info}")

        extractions = extracted_info.get("extractions", {})
        confidence = extracted_info.get("confidence", 0.5)

        def is_valid_content(v):
            if v is None:
                return False
            if isinstance(v, str):
                stripped = v.strip()
                if not stripped or stripped.lower() == 'null':
                    return False
                return True
            return bool(v)

        valid_extractions = {k: v for k, v in extractions.items()
                           if is_valid_content(v) and k in state.knowledge_base}
        logger.info(f"[KB][Update] Valid extractions: {list(valid_extractions.keys())}")

        # 维度到 UserDB 字段的映射
        user_field_mapping = {
            "relationship_goal": "relationship_goal",
            "personality": "personality",
            "ideal_type": "ideal_type",
            "lifestyle": "lifestyle",
            "deal_breakers": "deal_breakers",
            "values": "values",
            "interests": "interests",
        }

        updated_fields = []

        for dim_key, content in extractions.items():
            if is_valid_content(content) and dim_key in state.knowledge_base:
                # 1. 更新内存状态
                dim = state.knowledge_base[dim_key]
                dim.collected = True
                dim.confidence = confidence
                dim.raw_data = content
                logger.info(f"[KB][Update] ✅ {dim_key}: {str(content)[:50]}")

                # 2. 直接写入 UserDB
                if dim_key in user_field_mapping:
                    updated_fields.append((user_field_mapping[dim_key], content))

        # 3. 批量更新 UserDB
        if updated_fields:
            self._update_user_profile(state.user_id, updated_fields)

    def _update_user_profile(self, user_id: str, fields: List[Tuple[str, Any]]) -> None:
        """直接更新 UserDB（单一数据源）"""
        try:
            with db_session() as db:
                from db.models import UserDB

                user = db.query(UserDB).filter(UserDB.id == user_id).first()
                if not user:
                    return

                for field_name, value in fields:
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    else:
                        value = str(value) if value else None
                    setattr(user, field_name, value)

                db.commit()
                logger.info(f"[UserProfile] ✅ Updated: {[f[0] for f in fields]}")

        except Exception as e:
            logger.error(f"[UserProfile] Failed: {e}")

    def _evaluate_understanding(self, state: ConversationState):
        """评估整体了解度"""
        total_weight = 0
        weighted_score = 0

        # 🔍 [DEBUG] 记录各维度的详细状态
        dim_details = []
        for dim in state.knowledge_base.values():
            weight = (8 - dim.priority) / 7  # 优先级越高权重越大
            total_weight += weight
            if dim.collected:
                weighted_score += weight * dim.confidence
            # 🔍 [DEBUG] 记录每个维度的状态
            dim_details.append({
                "name": dim.name,
                "priority": dim.priority,
                "collected": dim.collected,
                "confidence": dim.confidence,
                "weight": round(weight, 2)
            })

        state.overall_understanding = weighted_score / total_weight if total_weight > 0 else 0

        # 🔍 [DEBUG] 输出详细的了解度评估结果
        collected_count = sum(1 for d in state.knowledge_base.values() if d.collected)
        total_count = len(state.knowledge_base)
        logger.info(f"[Understanding] Level: {state.overall_understanding:.2f}, Collected: {collected_count}/{total_count}")
        logger.debug(f"[Understanding] Dimension details: {dim_details}")

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
