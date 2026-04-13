# Her 顾问匹配系统架构设计

> **核心理念**：Her 是一位拥有20年经验的专业婚恋顾问，具备心理学、社会学、人际关系学专业知识，能够自主识别认知偏差，给出专业建议。

## 一、问题定义与目标

### 1.1 当前系统的问题

**五问法根因分析**：

```
问题现象：匹配逻辑分散，画像静态存储，搜索无主动建议
├─ 为什么 1: 存在多个匹配入口（IntentRouter/DeerFlow/双引擎），意图理解逻辑分散
├─ 为什么 2: 各入口各自实现意图解析，没有统一的"对话→匹配"语义层
├─ 为什么 3: 用户画像只是数据库静态存储，没有"行为→画像更新→匹配调整"闭环
├─ 为什么 4: 缺少统一的 User Profiling Service 聚合基础数据 + 行为数据 + 搜索历史
└─ 为什么 5: 架构设计时把"匹配"当成独立功能模块，而非"AI驱动的核心决策引擎"

根本对策：重构为真正的 AI Native 架构
```

### 1.2 目标架构

| 目标 | 说明 |
|------|------|
| **对话为唯一入口** | 用户通过自然语言描述需求，AI 理解意图并返回精准结果 |
| **双向动态画像** | "这个人是什么样的" + "这个人想要什么" 双向画像，持续更新 |
| **Her 专业判断** | Her（LLM）自主识别认知偏差，给出专业建议 |
| **主动建议系统** | 搜索时 AI 主动给出意见，而非被动返回结果 |

---

## 二、核心架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          用户交互层（对话式入口）                              │
│  前端 ChatInterface → 用户自然语言描述需求                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Her 顾问服务（核心决策层）                            │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ IntentAnalyzer  │  │ CognitiveBias   │  │ MatchAdvisor    │              │
│  │ (意图理解)       │  │ Detector        │  │ (匹配建议)       │              │
│  │ LLM驱动         │  │ (偏差识别)       │  │ LLM驱动         │              │
│  │                 │  │ LLM自主判断      │  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│                                                                              │
│  Her = 20年经验婚恋顾问 + 心理学知识 + 社会学知识 + 人际关系学知识            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          用户画像系统（双向动态画像）                          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         UserProfileService                               ││
│  │                                                                         ││
│  │  ┌───────────────────┐        ┌───────────────────┐                    ││
│  │  │ SelfProfile       │        │ DesireProfile     │                    ││
│  │  │ (这个人是什么样的)  │        │ (这个人想要什么)   │                    ││
│  │  │                   │        │                   │                    ││
│  │  │ 来源：             │        │ 来源：             │                    ││
│  │  │ - 基础数据填写     │        │ - 对话描述         │                    ││
│  │  │ - 行为分析         │        │ - 搜索历史         │                    ││
│  │  │ - 别人反馈         │        │ - 点击偏好         │                    ││
│  │  │ - 沟通风格分析     │        │ - 匹配反馈         │                    ││
│  │  │                   │        │                   │                    ││
│  │  │ 用于：别人匹配你时  │        │ 用于：给你推荐对象  │                    ││
│  │  └───────────────────┘        └───────────────────┘                    ││
│  │                                                                         ││
│  │  ┌───────────────────────────────────────────────────────────────────┐ ││
│  │  │ ProfileUpdateEngine (画像更新引擎)                                  │ ││
│  │  │ - 行为事件 → 画像维度更新                                           │ ││
│  │  │ - 对话分析 → DesireProfile 更新                                    │ ││
│  │  │ - 别人反馈 → SelfProfile 更新                                      │ ││
│  │  │ - 持续学习，动态调整                                                │ ││
│  │  └───────────────────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          匹配执行层                                           │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ CandidatePool   │  │ Compatibility   │  │ ResultFormatter │              │
│  │ Service         │  │ Calculator      │  │ (结果格式化)     │              │
│  │ (候选人筛选)     │  │ (适配度计算)     │  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          数据持久层                                           │
│  UserDB, UserProfileDB, BehaviorEventDB, MatchFeedbackDB, etc.              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心组件设计

### 3.1 Her 顾问服务（HerAdvisorService）

**职责**：Her 的核心大脑，具备专业婚恋顾问的知识和判断能力。

**关键原则**：
- **认知偏差识别不硬编码**：由 LLM 自主判断
- **专业知识驱动**：心理学、社会学、人际关系学知识框架
- **案例推理能力**：基于典型案例给出建议

#### 3.1.1 Her 的知识框架

```python
HER_KNOWLEDGE_FRAMEWORK = {
    "心理学": {
        "依恋理论": ["安全型", "焦虑型", "回避型", "混乱型"],
        "人格类型": ["MBTI", "大五人格", "九型人格"],
        "权力动态": ["控制型", "顺从型", "平等型", "竞争型"],
        "情感需求": ["需要被照顾", "需要被尊重", "需要被理解", "需要被认可"],
    },
    "社会学": {
        "社会阶层": ["收入匹配", "教育匹配", "职业匹配"],
        "文化背景": ["价值观差异", "生活习惯差异", "家庭观念差异"],
        "人生阶段": ["单身期", "恋爱期", "婚姻期", "育儿期"],
    },
    "人际关系学": {
        "沟通风格": ["直接型", "间接型", "情感型", "逻辑型"],
        "冲突处理": ["回避型", "竞争型", "妥协型", "合作型"],
        "相处节奏": ["快节奏", "慢节奏", "同步型", "异步型"],
    },
    "婚恋经验": {
        "典型案例": [
            "双强势 → 持续冲突",
            "双内向 → 缺乏火花",
            "焦虑型+回避型 → 持续痛苦",
            "控制型+独立型 → 权力斗争",
            "需要照顾+独立型 → 需求错配",
        ],
        "成功模式": [
            "强势+温和有主见 → 平衡互补",
            "内向+温暖外向 → 相互带动",
            "焦虑型+安全型 → 稳定陪伴",
        ],
    },
}
```

#### 3.1.2 认知偏差识别（LLM 自主判断）

**核心设计**：不硬编码规则，让 Her（LLM）自主分析用户画像，识别"想要的 ≠ 适合的"。

```python
class CognitiveBiasDetector:
    """
    认知偏差识别器
    
    关键设计：不硬编码规则，由 LLM 自主判断
    """
    
    async def detect_cognitive_bias(
        self,
        self_profile: SelfProfile,      # 这个用户是什么样的
        desire_profile: DesireProfile,   # 这个用户想要什么
    ) -> CognitiveBiasAnalysis:
        """
        让 Her 自主分析认知偏差
        
        LLM Prompt 框架：
        - 告知用户画像（SelfProfile + DesireProfile）
        - 告知 Her 的专业知识框架
        - 让 Her 自主判断是否存在偏差
        """
        
        prompt = self._build_bias_analysis_prompt(self_profile, desire_profile)
        
        # 调用 LLM，让 Her 自主分析
        llm_response = await self._call_llm(prompt)
        
        # 解析 LLM 返回的结构化分析结果
        bias_analysis = self._parse_bias_analysis(llm_response)
        
        return bias_analysis
    
    def _build_bias_analysis_prompt(
        self,
        self_profile: SelfProfile,
        desire_profile: DesireProfile,
    ) -> str:
        """构建认知偏差分析 Prompt"""
        
        return f'''你是一位拥有20年经验的专业婚恋顾问 Her。

【你的专业知识】
- 心理学：依恋理论（安全型/焦虑型/回避型）、人格类型、权力动态、情感需求
- 社会学：社会阶层匹配、文化背景差异、人生阶段匹配
- 人际关系学：沟通风格、冲突处理方式、相处节奏
- 婚恋经验：典型案例（双强势→冲突、双内向→无火花、焦虑型+回避型→痛苦）

【用户画像 - 这个人是什么样的】
{json.dumps(self_profile.to_dict(), ensure_ascii=False, indent=2)}

关键维度：
- 实际性格：{self_profile.actual_personality}（基于行为分析，而非用户自称）
- 沟通风格：{self_profile.communication_style}
- 情感需求：{self_profile.emotional_needs}
- 权力倾向：{self_profile.power_dynamic}
- 依恋类型：{self_profile.attachment_style}

【用户偏好 - 这个人想要什么】
{json.dumps(desire_profile.to_dict(), ensure_ascii=False, indent=2)}

关键维度：
- 表面偏好：{desire_profile.surface_preference}（用户自称想要的）
- 实际偏好：{desire_profile.actual_preference}（基于搜索/点击行为推断）
- 理想型描述：{desire_profile.ideal_type_description}

【任务】
请自主分析这个用户是否存在"认知偏差"：
1. 用户想要的类型，和用户实际适合的类型是否一致？
2. 如果不一致，原因是什么？（用心理学知识解释）
3. 用户实际适合什么类型的人？
4. 如果用户坚持当前偏好，可能遇到什么问题？

【输出格式】
返回 JSON 格式：
{{
    "has_bias": true/false,
    "bias_type": "偏差类型（如：双强势偏差、依恋错配、需求错配等）",
    "bias_description": "偏差的心理学解释",
    "actual_suitable_type": "用户实际适合的类型描述",
    "potential_risks": ["如果坚持当前偏好可能遇到的问题"],
    "adjustment_suggestion": "Her 的调整建议",
    "confidence": 0.0-1.0
}}

只返回 JSON，不要其他文字。'''
```

#### 3.1.3 匹配建议生成

```python
class MatchAdvisor:
    """
    匹配建议生成器
    
    四层匹配架构：
    1. 意向匹配（双向）
    2. 认知偏差识别（Her 专业判断）
    3. 双向适配度分析
    4. Her 专业建议
    """
    
    async def generate_match_advice(
        self,
        user_a: UserProfile,      # 用户A的完整画像
        user_b: UserProfile,      # 用户B的完整画像
        compatibility_score: float,  # 基础匹配分数
    ) -> MatchAdvice:
        """
        让 Her 生成匹配建议
        
        四种情况：
        ① 双向意向匹配 + 双向实际适合 → "很合适，推荐"
        ② 双向意向匹配 + 单/双向不适合 → "表面匹配但有隐患，建议..."
        ③ 单向意向匹配 → "对方可能更适合你，但意向不对称，建议..."
        ④ 意向不匹配但实际适合 → "你们实际很合适，建议调整期待..."
        """
        
        # Step 1: 检查双向意向匹配
        intent_match = self._check_intent_match(user_a, user_b)
        
        # Step 2: Her 自主分析认知偏差
        bias_a = await self._bias_detector.detect_cognitive_bias(
            user_a.self_profile, user_a.desire_profile
        )
        bias_b = await self._bias_detector.detect_cognitive_bias(
            user_b.self_profile, user_b.desire_profile
        )
        
        # Step 3: Her 分析双向适配度
        compatibility_analysis = await self._analyze_compatibility(
            user_a, user_b, bias_a, bias_b
        )
        
        # Step 4: Her 生成专业建议
        advice = await self._generate_professional_advice(
            intent_match, bias_a, bias_b, compatibility_analysis
        )
        
        return advice
```

---

### 3.2 用户画像系统（UserProfileService）

#### 3.2.1 双向画像数据结构

```python
@dataclass
class SelfProfile:
    """
    自身画像：这个人是什么样的
    
    用于：别人匹配你时使用
    """
    # ===== 基础属性（主动填写，行为无法推断）=====
    age: int
    gender: str
    location: str
    income_range: Optional[Tuple[int, int]]  # 收入范围（万）
    occupation: Optional[str]                 # 职业
    education: Optional[str]                  # 学历
    relationship_goal: str                    # 关系目标
    
    # ===== 动态画像（行为分析推断）=====
    # 性格维度
    actual_personality: PersonalityAnalysis   # 实际性格（基于行为）
    claimed_personality: Optional[str]        # 自称性格
    personality_gap: Optional[str]            # 性格认知偏差
    
    # 沟通风格
    communication_style: CommunicationStyle   # 沟通方式
    response_pattern: ResponsePattern         # 回复模式
    emoji_usage: EmojiPattern                 # 表情使用习惯
    
    # 情感需求
    emotional_needs: List[EmotionalNeed]      # 情感需求类型
    attachment_style: AttachmentStyle         # 依恋类型
    
    # 权力动态
    power_dynamic: PowerDynamic               # 权力倾向
    decision_style: DecisionStyle             # 决策方式
    
    # ===== 社会反馈维度 =====
    reputation_score: float                   # 口碑评分
    like_rate: float                          # 好评率
    feedback_summary: Optional[str]           # 别人反馈摘要
    
    # ===== 画像置信度 =====
    profile_confidence: float                 # 整体置信度
    dimension_confidences: Dict[str, float]   # 各维度置信度
    last_updated_at: datetime


@dataclass
class DesireProfile:
    """
    意愿画像：这个人想要什么
    
    用于：给你推荐对象时使用
    """
    # ===== 表面偏好（用户自称）=====
    surface_preference: str                   # 用户自称想要的类型
    ideal_type_description: Optional[str]     # 理想型描述
    deal_breakers: List[str]                  # 底线禁忌
    
    # ===== 实际偏好（行为推断）=====
    actual_preference: str                    # 实际想要的类型（基于行为）
    preference_source: PreferenceSource       # 偏好来源
    
    # ===== 搜索偏好 =====
    search_patterns: List[SearchPattern]      # 搜索历史分析
    clicked_types: List[ClickedType]          # 点击偏好类型
    swipe_patterns: SwipePattern              # 滑动偏好
    
    # ===== 匹配反馈 =====
    like_feedback: List[MatchFeedback]        # 喜欢的匹配反馈
    dislike_feedback: List[MatchFeedback]     # 不喜欢的匹配反馈
    skip_feedback: List[MatchFeedback]        # 跳过的匹配反馈
    
    # ===== 偏好差距 =====
    preference_gap: Optional[str]             # 表面偏好 vs 实际偏好差距
    
    # ===== 置信度 =====
    preference_confidence: float              # 偏好置信度
    last_updated_at: datetime
```

#### 3.2.2 画像更新引擎

```python
class ProfileUpdateEngine:
    """
    画像更新引擎
    
    核心职责：
    - 行为事件 → 画像维度更新
    - 对话分析 → DesireProfile 更新
    - 别人反馈 → SelfProfile 更新
    - 持续学习，动态调整
    """
    
    # 事件 → 维度映射
    EVENT_TO_DIMENSION_MAP = {
        # ===== SelfProfile 更新事件 =====
        "message_sent": "communication_style",
        "response_time": "response_pattern",
        "emoji_usage": "emoji_usage",
        "topic_initiation": "power_dynamic",
        "conflict_handling": "decision_style",
        "received_feedback": "reputation_score",
        "received_like": "like_rate",
        
        # ===== DesireProfile 更新事件 =====
        "search_query": "search_patterns",
        "profile_view": "clicked_types",
        "swipe_like": "swipe_patterns",
        "swipe_pass": "swipe_patterns",
        "match_like": "like_feedback",
        "match_dislike": "dislike_feedback",
        "match_skip": "skip_feedback",
        "conversation_topic": "actual_preference",
    }
    
    async def process_behavior_event(
        self,
        user_id: str,
        event: BehaviorEvent,
    ) -> ProfileUpdateResult:
        """
        处理行为事件，更新画像
        
        流程：
        1. 识别事件类型
        2. 确定影响的画像维度
        3. 计算更新值
        4. 更新画像并记录变更
        """
        
        dimension = self.EVENT_TO_DIMENSION_MAP.get(event.event_type)
        if not dimension:
            return ProfileUpdateResult(no_update=True)
        
        # 根据事件类型，计算维度更新
        update_value = await self._calculate_dimension_update(
            user_id, event, dimension
        )
        
        # 应用更新
        profile = await self._user_profile_service.get_profile(user_id)
        
        if dimension in SelfProfile.__dataclass_fields__:
            # 更新 SelfProfile
            profile.self_profile = self._update_self_profile(
                profile.self_profile, dimension, update_value, event
            )
        else:
            # 更新 DesireProfile
            profile.desire_profile = self._update_desire_profile(
                profile.desire_profile, dimension, update_value, event
            )
        
        # 记录更新历史
        await self._record_profile_update(user_id, dimension, update_value, event)
        
        return ProfileUpdateResult(
            updated=True,
            dimension=dimension,
            old_value=...,  # 原值
            new_value=update_value,
            confidence=event.confidence,
        )
    
    async def process_conversation_analysis(
        self,
        user_id: str,
        conversation: ConversationAnalysis,
    ) -> ProfileUpdateResult:
        """
        处理对话分析结果，更新 DesireProfile
        
        从对话中推断：
        - 用户想要什么类型的人
        - 用户看重什么维度
        - 用户的底线禁忌
        """
        
        # LLM 分析对话内容，提取偏好信息
        preference_update = await self._extract_preference_from_conversation(
            conversation
        )
        
        # 更新 DesireProfile
        profile = await self._user_profile_service.get_profile(user_id)
        
        # 如果用户在对话中描述的理想型与实际行为不一致，记录 preference_gap
        if preference_update.stated_preference:
            profile.desire_profile.surface_preference = preference_update.stated_preference
        
        # 更新实际偏好（基于行为）
        if preference_update.inferred_preference:
            profile.desire_profile.actual_preference = preference_update.inferred_preference
        
        # 更新偏好差距
        if profile.desire_profile.surface_preference != profile.desire_profile.actual_preference:
            profile.desire_profile.preference_gap = self._describe_preference_gap(
                profile.desire_profile.surface_preference,
                profile.desire_profile.actual_preference
            )
        
        return ProfileUpdateResult(updated=True, ...)
```

---

### 3.3 数据模型设计

#### 3.3.1 新增数据库表

```python
class UserProfileDB(Base):
    """用户完整画像 - 双向画像存储"""
    __tablename__ = "user_profiles"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)

    # ===== SelfProfile JSON 存储 =====
    self_profile_json = Column(Text, nullable=False)  # SelfProfile 完整 JSON

    # ===== DesireProfile JSON 存储 =====
    desire_profile_json = Column(Text, nullable=False)  # DesireProfile 完整 JSON

    # ===== 画像元数据 =====
    self_profile_confidence = Column(Float, default=0.0)
    desire_profile_confidence = Column(Float, default=0.0)
    
    # ===== 画像完整度 =====
    self_profile_completeness = Column(Float, default=0.0)  # SelfProfile 完整度
    desire_profile_completeness = Column(Float, default=0.0)  # DesireProfile 完整度
    
    # ===== 画像版本 =====
    profile_version = Column(Integer, default=1)
    
    # ===== 时间戳 =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_behavior_analysis_at = Column(DateTime(timezone=True), nullable=True)
    last_conversation_analysis_at = Column(DateTime(timezone=True), nullable=True)


class ProfileUpdateHistoryDB(Base):
    """画像更新历史记录"""
    __tablename__ = "profile_update_history"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # ===== 更新信息 =====
    profile_type = Column(String(20), nullable=False)  # self_profile, desire_profile
    dimension = Column(String(50), nullable=False)  # 更新的维度
    old_value = Column(Text, nullable=True)  # JSON 格式
    new_value = Column(Text, nullable=False)  # JSON 格式
    
    # ===== 更新来源 =====
    update_source = Column(String(50), nullable=False)
    # 来源类型：
    # - behavior_event: 行为事件
    # - conversation_analysis: 对话分析
    # - match_feedback: 匹配反馈
    # - received_feedback: 收到的反馈
    # - manual_update: 手动更新
    
    # ===== 关联事件 =====
    related_event_id = Column(String(36), nullable=True)  # 关联的事件 ID
    
    # ===== 置信度 =====
    update_confidence = Column(Float, default=1.0)
    
    # ===== 时间戳 =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CognitiveBiasAnalysisDB(Base):
    """认知偏差分析记录"""
    __tablename__ = "cognitive_bias_analyses"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # ===== 分析结果 =====
    has_bias = Column(Boolean, default=False)
    bias_type = Column(String(100), nullable=True)
    bias_description = Column(Text, nullable=True)
    
    # ===== Her 建议 =====
    actual_suitable_type = Column(Text, nullable=True)
    potential_risks = Column(Text, nullable=True)  # JSON 数组
    adjustment_suggestion = Column(Text, nullable=True)
    
    # ===== 分析置信度 =====
    confidence = Column(Float, default=0.0)
    
    # ===== LLM 信息 =====
    llm_model = Column(String(100), nullable=True)
    llm_tokens_used = Column(Integer, nullable=True)
    
    # ===== 时间戳 =====
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    profile_snapshot = Column(Text, nullable=True)  # 分析时的画像快照


class MatchAdviceDB(Base):
    """匹配建议记录"""
    __tablename__ = "match_advices"

    id = Column(String(36), primary_key=True)
    
    # ===== 匹配双方 =====
    user_id_a = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_b = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # ===== 意向匹配状态 =====
    intent_match_status = Column(String(50), nullable=False)
    # 状态类型：
    # - bidirectional_match: 双向意向匹配
    # - unidirectional_match: 单向意向匹配
    # - no_intent_match: 意向不匹配
    
    # ===== 认知偏差 =====
    user_a_bias_id = Column(String(36), nullable=True)
    user_b_bias_id = Column(String(36), nullable=True)
    
    # ===== 适配度分析 =====
    compatibility_score = Column(Float, default=0.0)
    compatibility_analysis = Column(Text, nullable=True)  # JSON 格式
    
    # ===== Her 建议 =====
    advice_type = Column(String(50), nullable=False)
    # 建议类型：
    # - strongly_recommend: 强烈推荐
    # - recommend_with_caution: 谨慎推荐
    # - not_recommended: 不推荐
    # - suggest_adjustment: 建议调整期待
    
    advice_content = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    
    # ===== 时间戳 =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserBehaviorEventDB(Base):
    """用户行为事件（增强版）"""
    __tablename__ = "user_behavior_events"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # ===== 事件类型 =====
    event_type = Column(String(50), nullable=False, index=True)
    # 事件类型扩展：
    # SelfProfile 相关：
    # - message_sent, response_time, emoji_usage, topic_initiation
    # - conflict_handling, received_feedback, received_like
    # DesireProfile 相关：
    # - search_query, profile_view, swipe_like, swipe_pass
    # - match_like, match_dislike, match_skip, conversation_topic
    
    # ===== 事件目标 =====
    target_user_id = Column(String(36), nullable=True, index=True)
    
    # ===== 事件详情 =====
    event_data = Column(JSON, nullable=True)
    
    # ===== 事件置信度 =====
    event_confidence = Column(Float, default=1.0)
    
    # ===== 时间戳 =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

### 3.4 对话式匹配入口设计

#### 3.4.1 统一的对话处理流程

```python
class ConversationMatchService:
    """
    对话式匹配服务
    
    对话为唯一入口，统一处理用户自然语言需求
    """
    
    async def process_conversation_message(
        self,
        user_id: str,
        message: str,
        context: ConversationContext,
    ) -> ConversationMatchResponse:
        """
        处理对话消息
        
        流程：
        1. 意图理解（LLM 驱动）
        2. 画像获取与更新
        3. 认知偏差识别
        4. 匹配执行
        5. Her 建议生成
        6. 主动建议补充
        """
        
        # Step 1: 意图理解
        intent = await self._intent_analyzer.analyze(message, context)
        
        # Step 2: 获取用户画像
        profile = await self._user_profile_service.get_or_create_profile(user_id)
        
        # Step 3: 从对话中更新 DesireProfile
        profile = await self._profile_update_engine.process_conversation_analysis(
            user_id, ConversationAnalysis(message=message, intent=intent)
        )
        
        # Step 4: 认知偏差识别（Her 自主判断）
        bias_analysis = await self._bias_detector.detect_cognitive_bias(
            profile.self_profile, profile.desire_profile
        )
        
        # Step 5: 执行匹配
        if intent.intent_type == "match_request":
            matches = await self._execute_match(
                user_id, profile, intent, bias_analysis
            )
            
            # Step 6: 为每个匹配生成 Her 建议
            for match in matches:
                match.advice = await self._match_advisor.generate_match_advice(
                    profile, match.target_profile, match.compatibility_score
                )
            
            # Step 7: 生成主动建议
            proactive_suggestion = await self._generate_proactive_suggestion(
                profile, bias_analysis, matches
            )
            
            return ConversationMatchResponse(
                ai_message=self._generate_response_message(intent, matches, bias_analysis),
                matches=matches,
                bias_analysis=bias_analysis,
                proactive_suggestion=proactive_suggestion,
                generative_ui=self._build_generative_ui(matches, intent),
            )
        
        # 其他意图类型处理...
```

#### 3.4.2 主动建议生成

```python
class ProactiveSuggestionGenerator:
    """
    主动建议生成器
    
    在用户搜索时给出专业意见，而非被动返回结果
    """
    
    async def generate_proactive_suggestion(
        self,
        profile: UserProfile,
        bias_analysis: CognitiveBiasAnalysis,
        matches: List[MatchResult],
    ) -> ProactiveSuggestion:
        """
        生成主动建议
        
        建议类型：
        1. 认知偏差提醒："你想要的和你适合的可能不一致"
        2. 搜索范围建议："北京25-30岁女生只有120人，建议放宽条件"
        3. 行为模式提醒："你说喜欢内向的，但最近看了3个户外活动的人"
        4. 匹配质量提醒："当前匹配池质量较低，建议等待更多候选人"
        """
        
        suggestions = []
        
        # 1. 认知偏差提醒
        if bias_analysis.has_bias:
            suggestions.append({
                "type": "cognitive_bias_reminder",
                "message": f"Her 发现：{bias_analysis.bias_description}",
                "suggestion": bias_analysis.adjustment_suggestion,
                "importance": "high",
            })
        
        # 2. 搜索范围建议
        if matches and len(matches) < 3:
            pool_analysis = await self._analyze_match_pool(profile)
            if pool_analysis.pool_size < 50:
                suggestions.append({
                    "type": "search_range_suggestion",
                    "message": f"当前条件下匹配池只有{pool_analysis.pool_size}人",
                    "suggestion": pool_analysis.expansion_suggestion,
                    "importance": "medium",
                })
        
        # 3. 行为模式提醒
        preference_gap = profile.desire_profile.preference_gap
        if preference_gap:
            suggestions.append({
                "type": "behavior_pattern_reminder",
                "message": f"你说想要{profile.desire_profile.surface_preference}，但最近的行为显示你更倾向{profile.desire_profile.actual_preference}",
                "suggestion": "要不要试试这类人？",
                "importance": "medium",
            })
        
        # 4. 匹配质量提醒
        avg_score = sum(m.compatibility_score for m in matches) / len(matches) if matches else 0
        if avg_score < 0.6:
            suggestions.append({
                "type": "match_quality_reminder",
                "message": "当前匹配对象的平均匹配度较低",
                "suggestion": "建议稍后再来，或者调整一下你的期待",
                "importance": "low",
            })
        
        return ProactiveSuggestion(
            suggestions=suggestions,
            has_critical_suggestion=bias_analysis.has_bias,
        )
```

---

## 四、Her 顾问判断逻辑示例

### 4.1 认知偏差识别示例

**场景：双强势偏差**

```
用户画像：
- SelfProfile.actual_personality: "强势、控制欲强、喜欢主导决策"
- SelfProfile.power_dynamic: "控制型"
- DesireProfile.surface_preference: "强势、独立、有主见的女生"
- DesireProfile.actual_preference: "温和但有主见"（基于点击行为推断）

Her 分析（LLM 自主判断）：
{
    "has_bias": true,
    "bias_type": "双强势偏差",
    "bias_description": "用户自身就很强势，控制欲强，但想要找强势独立的伴侣。两个强势的人在一起容易产生权力斗争，持续冲突。",
    "actual_suitable_type": "温和但有主见的人——既能和用户平等对话，又能中和用户的强势倾向",
    "potential_risks": [
        "权力斗争：双方都想主导，容易产生冲突",
        "沟通困难：强势的人倾向于表达而非倾听",
        "关系疲惫：持续的权力博弈会让双方都很累"
    ],
    "adjustment_suggestion": "建议尝试温和但有主见的人。这类人能和你平等对话，不会完全顺从也不会和你对抗，关系更长久和谐。如果你坚持找强势的，需要学会妥协和倾听。"
}
```

### 4.2 匹配建议示例

**场景：表面匹配但深层冲突**

```
用户A画像：
- 想要：温柔贤惠的女生
- 实际性格：强势、控制型、需要被认可

用户B画像：
- 自称：温柔贤惠
- 实际性格：独立、需要被尊重而非被照顾

Her 分析：
{
    "intent_match_status": "bidirectional_match",
    "advice_type": "recommend_with_caution",
    "advice_content": "表面匹配，但有潜在冲突",
    "reasoning": "A想要温柔的女生，B自称温柔贤惠，表面匹配。但深层分析：A的控制欲与B的独立需求可能产生冲突。B的温柔可能是表象，实际内心独立，渴望被尊重而非被照顾。",
    "suggestions": [
        "建议先进行几次深度沟通，观察相处模式",
        "A需要学会倾听和尊重B的想法",
        "B需要明确表达自己的边界",
        "如果双方愿意调整相处模式，有发展潜力"
    ],
    "compatibility_score": 0.65,
    "potential_issues": [
        "A的控制欲可能让B感到被压抑",
        "B的独立需求可能与A的期待冲突"
    ]
}
```

---

## 五、实施路线

### 5.1 分阶段实施

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| **Phase 1** | 双向画像数据模型 + UserProfileService | P0 |
| **Phase 2** | ProfileUpdateEngine（行为→画像更新） | P0 |
| **Phase 3** | HerAdvisorService + CognitiveBiasDetector（LLM驱动） | P0 |
| **Phase 4** | ConversationMatchService（对话为唯一入口） | P1 |
| **Phase 5** | ProactiveSuggestionGenerator（主动建议） | P1 |
| **Phase 6** | 统一 IntentRouter 和 DeerFlow 入口 | P2 |

### 5.2 关键设计决策

| 决策点 | 方案 | 原因 |
|--------|------|------|
| 认知偏差识别 | LLM 自主判断，不硬编码 | Her 的专业能力来源于 LLM 知识，而非规则 |
| 双向画像分离 | SelfProfile + DesireProfile 分离 | "是什么样的"和"想要什么"用途不同 |
| 画像更新来源 | 行为事件 + 对话分析 + 别人反馈 | 多来源确保画像准确性 |
| 匹配入口统一 | 对话为唯一入口 | 符合 AI Native 原则 |
| 主动建议时机 | 搜索时立即给出 | 专业顾问不会等用户问才说话 |

---

## 六、与现有系统集成

### 6.1 现有组件迁移策略

| 现有组件 | 迁移策略 |
|----------|----------|
| IntentRouterService | 合并到 ConversationMatchService，规则匹配降级为快速路由 |
| DeerFlow Agent | 保留，作为复杂意图的补充处理器 |
| MatchmakerAlgorithm | 保留，作为 CompatibilityCalculator 的核心算法 |
| 双引擎架构 | 简化，Her 建议层替代付费引擎的差异化逻辑 |

### 6.2 数据迁移

| 现有数据表 | 新数据表 | 迁移方式 |
|------------|----------|----------|
| UserDB | UserProfileDB | 初始化 SelfProfile 和 DesireProfile |
| BehaviorEventDB | UserBehaviorEventDB（增强版） | 扩展事件类型 |
| UserProfileUpdateDB | ProfileUpdateHistoryDB | 统一更新历史记录 |

---

## 七、总结

**核心创新点**：

1. **Her 专业顾问定位**：不是匹配执行者，而是有专业判断能力的顾问
2. **认知偏差自主识别**：LLM 驱动，不硬编码规则
3. **双向动态画像**："是什么样的" + "想要什么" 分离且持续更新
4. **主动建议系统**：搜索时给出专业意见，而非被动返回结果
5. **对话为唯一入口**：符合 AI Native 架构原则