# 渐进式智能匹配系统设计方案

> 版本：v1.1
> 日期：2026-04-11
> 状态：**全量迁移完成** ✅
> 
> **核心理念**：借鉴传统红娘工作模式，将"先完整画像再匹配"转变为"最小信息立即匹配+反馈学习"
> 
> **迁移决策**：系统无真实用户，直接全量迁移至 QuickStart 流程，原 RegistrationConversation 流程已停用

---

## 实现进度总览

| Phase | 内容 | 状态 | 完成文件 |
|-------|------|------|----------|
| Phase 1 | 最小信息快速入门 | ✅ 完成 | `quick_start_service.py`, `quick_start_apis.py`, `QuickStartPage.tsx` |
| Phase 2 | 反馈学习循环 | ✅ 完成 | `FeedbackLearningService`, `vector_adjustment_service.py` |
| Phase 3 | 隐性推断机制 | ✅ 完成 | `BehaviorSignalCollector`, `useBehaviorTracking.ts` |
| Phase 4 | 社会认同背书 | ✅ 完成 | `SocialProofService`, `_get_trust_badges()` |
| Phase 5 | 全量迁移 | ✅ 完成 | `App.tsx` 入口已切换，灰度配置保留备用 |

---

## 用户入口变化

### 原流程（已停用）
```
新用户注册 → RegistrationConversationPage（多轮对话问答）→ HomePage
```

### 新流程（全量启用）
```
新用户注册 → QuickStartPage（30秒快速入门）→ 立即看到推荐 → HomePage
```

### 入口代码变化

**App.tsx 修改**：
- 移除 `RegistrationConversationPage` 导入
- 新用户默认进入 `QuickStartPage`
- 不再需要 URL 参数 `?quick-start=true`

**灰度配置调整**：
- `quick_start_flow`: `rollout_percentage` = 100（全量启用）
- A/B 实验 `quick_start_ab_test`: `status` = "paused"（暂停）

---

## 目录

1. [背景与问题分析](#一背景与问题分析)
2. [核心范式转变](#二核心范式转变)
3. [传统红娘模式系统化实现](#三传统红娘模式系统化实现)
4. [系统架构设计](#四系统架构设计)
5. [核心服务设计](#五核心服务设计)
6. [数据模型扩展](#六数据模型扩展)
7. [API接口设计](#七api接口设计)
8. [前端交互设计](#八前端交互设计)
9. [实现路线图](#九实现路线图)
10. [灰度迁移方案](#十灰度迁移方案)
11. [效果评估指标](#十一效果评估指标)

---

## 一、背景与问题分析

### 1.1 当前系统的问题现象

```
用户流失原因分析（五问法）
├─ 为什么 1: 用户需要回答多轮问题才能开始匹配
├─ 为什么 2: ProfileCollectionSkill 设计了 7 个维度，每个维度可追问 2 层
├─ 为什么 3: 设计假设"画像越完整，匹配越精准"
├─ 为什么 4: 这是"相亲平台"的 CRUD 思维，而非"红娘"的 Agent 思维
└─ 为什么 5: 缺乏"先给结果，再渐进学习"的产品理念

根本对策：逆转流程，从"先完整画像再匹配"变为"最小信息立即匹配+反馈学习"
```

### 1.2 当前画像收集流程分析

| 维度 | 当前实现 | 用户感知 |
|------|---------|---------|
| relationship_goal | 1 个问题 + 可追问 2 层 | "为什么问这么多？" |
| age_preference | 1 个问题 | 可接受 |
| location_preference | 1 个问题 + 可追问 1 层 | 可接受 |
| interests | 标签选择（8+选项） | "太多了不想选" |
| personality | 1 个问题 + 可追问 2 层 | "不知道怎么回答" |
| lifestyle | 1 个问题 | 可接受 |
| values | 1 个问题 + 可追问 2 层 | "太抽象" |
| deal_breakers | 多选（5+选项） | 可接受 |

**总计**：约 7-14 个问题，耗时 3-10 分钟

### 1.3 传统红娘工作模式分析

传统线下红娘的成功经验揭示了更高效的用户体验模式：

| 步骤 | 传统红娘做法 | 核心特点 |
|------|-------------|---------|
| 1. 快速了解 | 聊 3-5 分钟，问最关键的几个问题 | 年龄、工作、想找什么关系——硬条件优先 |
| 2. 立即推荐 | "我这有几个合适的，你先看看" | 先给结果，不是先了解完整画像 |
| 3. 观察反馈 | "这个你觉得怎么样？不喜欢？为什么？" | 通过反馈学习偏好 |
| 4. 渐进调整 | "那你可能更喜欢年轻点的，下次给你找" | 每次推荐都在学习 |
| 5. 隐性判断 | 观察穿着、言谈、举止推断品味 | 不只听你说什么，还看你是什么样的人 |
| 6. 口碑背书 | "这个姑娘人很好，很多人夸她" | 信任背书推荐 |

---

## 二、核心范式转变

### 2.1 流程对比

| 维度 | 当前系统（相亲平台模式） | 目标系统（传统红娘模式） |
|------|-------------------------|-------------------------|
| **流程** | 收集完整画像 → 匹配 | 最小信息 → 立即匹配 → 反馈学习 |
| **门槛** | 7维度×(1+追问) ≈ 10+问题 | 3个硬条件 ≈ 30秒 |
| **反馈** | 被动记录行为 | 主动追问"不喜欢的原因" |
| **学习** | 后置学习 | 每次推荐都在学习 |
| **信任** | 算法黑盒 | "很多人夸TA"的社会认同 |

### 2.2 设计哲学对比

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         设计哲学对比                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【相亲平台模式】                                                        │
│  ─────────────────────────────────────────────────────                  │
│  假设：画像完整度 = 匹配质量                                             │
│  流程：用户主动填 → 系统被动算 → 输出结果                                │
│  问题：用户没耐心填完，流失率高                                          │
│                                                                         │
│  【传统红娘模式】                                                        │
│  ─────────────────────────────────────────────────────                  │
│  假设：反馈学习 = 渐进精准                                               │
│  流程：最小信息 → 立即结果 → 观察反馈 → 调整学习                         │
│  优势：用户立刻有获得感，愿意继续互动                                    │
│                                                                         │
│  【核心洞察】                                                            │
│  ─────────────────────────────────────────────────────                  │
│  用户不知道自己想要什么，需要通过"看"来发现                              │
│  → 先给候选，让用户"看"                                                 │
│  → 用户反馈，系统"学"                                                   │
│  → 渐进调整，越来越精准                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、传统红娘模式系统化实现

### 3.1 六步法映射

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     传统红娘六步法系统化映射                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: 快速了解（30秒硬条件）                                          │
│  ─────────────────────────────────────────────────────                  │
│  传统：聊 3-5 分钟，问最关键的几个问题                                   │
│  系统：QuickStartService                                                │
│  输入：年龄、性别、所在城市、关系目标                                     │
│  输出：用户向量基础版（仅填充 v0-v9 人口统计学维度）                      │
│                                                                         │
│  Step 2: 立即推荐（先给结果）                                            │
│  ─────────────────────────────────────────────────────                  │
│  传统："我这有几个合适的，你先看看"                                      │
│  系统：ColdStartMatcher                                                 │
│  策略：地理优先 + 关系目标匹配 + 热门候选                                │
│  输出：3-5 个候选人 + 红娘风格推荐语                                     │
│                                                                         │
│  Step 3: 观察反馈（主动追问）                                            │
│  ─────────────────────────────────────────────────────                  │
│  传统："这个你觉得怎么样？不喜欢？为什么？"                              │
│  系统：FeedbackLearningLoop                                             │
│  用户操作：喜欢 / 不喜欢 / 跳过                                          │
│  不喜欢时追问：弹出选项卡片                                              │
│  输出：偏好数据 + 画像补全                                               │
│                                                                         │
│  Step 4: 渐进调整（每次都在学习）                                        │
│  ─────────────────────────────────────────────────────                  │
│  传统："那你可能更喜欢年轻点的，下次给你找"                              │
│  系统：PreferenceAdjuster                                               │
│  将反馈数据写入用户向量（价值观、性格、沟通风格维度）                     │
│  下次推荐时应用新偏好                                                    │
│                                                                         │
│  Step 5: 隐性判断（比你更懂你）                                          │
│  ─────────────────────────────────────────────────────                  │
│  传统：观察穿着、言谈、举止推断品味                                      │
│  系统：ImplicitPreferenceInferrer                                       │
│  从浏览时长、滑动速度、表情使用推断隐性偏好                              │
│  写入隐性特征维度 v136-v143                                             │
│                                                                         │
│  Step 6: 口碑背书（社会认同）                                            │
│  ─────────────────────────────────────────────────────                  │
│  传统："这个姑娘很多人夸她"                                              │
│  系统：SocialProofService                                               │
│  推荐理由包含："好评率85%，很多人夸她性格好"                             │
│  展示：信任徽章 + 好评率 + 成功案例证据                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 四、系统架构设计

### 4.1 总体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     渐进式智能匹配系统架构                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    第一层：快速入门                              │    │
│  │                                                                   │    │
│  │   QuickStartService                                              │    │
│  │   - 30秒完成基础信息收集                                         │    │
│  │   - 生成基础用户向量（v0-v9）                                    │    │
│  │   - 红娘风格开场白                                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 第二层：立即推荐                                  │    │
│  │                                                                   │    │
│  │   ColdStartMatcher                                               │    │
│  │   - 地理优先匹配                                                 │    │
│  │   - 关系目标兼容性                                               │    │
│  │   - 热门候选推荐                                                 │    │
│  │   - 生成社会认同背书                                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 第三层：反馈学习                                  │    │
│  │                                                                   │    │
│  │   FeedbackLearningLoop                                           │    │
│  │   - 处理用户反馈（喜欢/不喜欢/跳过）                             │    │
│  │   - 不喜欢时追问原因                                             │    │
│  │   - 学习偏好并更新向量                                           │    │
│  │   - 立即生成调整后的新推荐                                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 第四层：隐性推断                                  │    │
│  │                                                                   │    │
│  │   ImplicitPreferenceInferrer                                     │    │
│  │   - 分析浏览行为（时长、速度、次数）                             │    │
│  │   - 分析聊天行为（表情、回复速度）                               │    │
│  │   - 推断隐性偏好并写入向量                                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 第五层：持续迭代                                  │    │
│  │                                                                   │    │
│  │   PreferenceAdjuster + VectorUpdater                             │    │
│  │   - 渐进式向量更新                                               │    │
│  │   - 推荐算法优化                                                 │    │
│  │   - 周期性学习总结                                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 支撑服务                                          │    │
│  │                                                                   │    │
│  │   SocialProofService      - 社会认同背书                         │    │
│  │   MatchReasoningGenerator  - 推荐理由生成                         │    │
│  │   BehaviorTracker          - 行为追踪                             │    │
│  │   LearningProgressTracker  - 学习进度追踪                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 模块职责划分

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| QuickStartService | 快速入门 | 年龄、性别、城市、关系目标 | 基础向量 + 初始推荐 + 开场白 |
| ColdStartMatcher | 冷启动匹配 | 基础向量 + 关系目标 | 3-5个候选人 + 社会认同背书 |
| FeedbackLearningLoop | 反馈学习 | 用户反馈 + 原因 | 学习偏好 + 调整向量 + 新推荐 |
| ImplicitPreferenceInferrer | 隐性推断 | 行为事件列表 | 隐性偏好 + 向量调整 |
| SocialProofService | 社会认同背书 | 候选人ID | 好评率 + 信任徽章 + 口碑文案 |
| PreferenceAdjuster | 偏好调整 | 学习偏好 + 原向量 | 调整后向量 |

---

## 五、核心服务设计

### 5.1 QuickStartService - 快速入门服务

```python
class QuickStartService:
    """快速入门服务 - 传统红娘第一步"""
    
    MINIMAL_REQUIRED_DIMENSIONS = [
        "age",           # 年龄（必填）
        "gender",        # 性别（必填）
        "location",      # 所在城市（必填）
        "relationship_goal",  # 关系目标（必填）
    ]
    
    # 关系目标简化为 4 个选项
    RELATIONSHIP_GOAL_OPTIONS = [
        {"value": "serious", "label": "认真恋爱", "icon": "💕"},
        {"value": "marriage", "label": "奔着结婚", "icon": "💍"},
        {"value": "dating", "label": "轻松交友", "icon": "☕"},
        {"value": "casual", "label": "随便聊聊", "icon": "💭"},
    ]
    
    async def quick_register(
        self,
        age: int,
        gender: str,
        location: str,
        relationship_goal: str
    ) -> QuickStartResult:
        """
        30 秒快速入门
        
        Args:
            age: 用户年龄
            gender: 用户性别（male/female/other）
            location: 所在城市
            relationship_goal: 关系目标（serious/marriage/dating/casual）
            
        Returns:
            QuickStartResult:
                - user_vector_basic: 基础向量（仅人口统计学）
                - initial_matches: 3-5 个初始推荐
                - ai_message: 红娘风格开场白
        """
        # 1. 创建基础用户向量（仅填充 v0-v9）
        user_vector = np.zeros(144)
        user_vector[0] = age / 100  # v0: 年龄归一化
        user_vector[3] = self._encode_gender(gender)  # v3: 性别编码
        user_vector[6:10] = self._encode_location(location)  # v6-v9: 地理编码
        
        # 2. 使用冷启动匹配策略
        initial_matches = await self._cold_start_match(
            user_vector=user_vector,
            relationship_goal=relationship_goal,
            location=location,
            limit=5
        )
        
        # 3. 为每个候选人生成社会认同背书
        for match in initial_matches:
            match["social_proof"] = await self._get_social_proof(match["user_id"])
        
        # 4. 生成红娘风格开场白
        ai_message = await self._generate_matchmaker_intro(
            matches_count=len(initial_matches),
            location=location
        )
        
        return QuickStartResult(
            user_vector_basic=user_vector,
            initial_matches=initial_matches,
            ai_message=ai_message,
            next_step="show_matches"
        )
    
    def _encode_gender(self, gender: str) -> float:
        """性别编码"""
        mapping = {"male": 0.0, "female": 1.0, "other": 0.5}
        return mapping.get(gender.lower(), 0.5)
    
    def _encode_location(self, location: str) -> np.ndarray:
        """地理编码（返回 v6-v9）"""
        # v6: 城市层级，v7: 是否接受异地，v8-v9: 经纬度归一化
        city_level = self._get_city_level(location)
        return np.array([city_level, 0.0, 0.5, 0.5])  # 默认值
    
    async def _generate_matchmaker_intro(
        self,
        matches_count: int,
        location: str
    ) -> str:
        """生成红娘风格开场白"""
        templates = [
            f"好的，我这有{matches_count}个觉得合适的，你先看看~",
            f"根据你在{location}，我找了几位可能合适的，看看有没有眼缘？",
            f"来，先给你推几位，不喜欢的话告诉我原因，我再帮你找~",
            f"这几位我觉得挺适合你的，你看看有没有感兴趣的？",
        ]
        return random.choice(templates)
```

### 5.2 FeedbackLearningLoop - 反馈学习循环

```python
class FeedbackLearningLoop:
    """反馈学习循环 - 传统红娘第三步"""
    
    # 不喜欢原因选项（红娘追问）
    DISLIKE_REASON_OPTIONS = [
        {"value": "age_not_match", "label": "年龄不太合适", "icon": "📅"},
        {"value": "location_far", "label": "距离太远了", "icon": "📍"},
        {"value": "not_my_type", "label": "不是我喜欢的类型", "icon": "💔"},
        {"value": "photo_concern", "label": "照片让我犹豫", "icon": "📸"},
        {"value": "bio_issue", "label": "简介不太吸引我", "icon": "📝"},
        {"value": "already_chatting", "label": "已经和别人在聊了", "icon": "💬"},
        {"value": "other", "label": "其他原因", "icon": "💭"},
    ]
    
    # 反馈到偏好的映射
    FEEDBACK_TO_PREFERENCE_MAPPING = {
        "age_not_match": {
            "dimension": "age_preference",
            "vector_dims": [1, 2],  # v1-v2: 年龄偏好上下限
            "weight": 0.8,
            "adjustment_strategy": "adjust_age_range"
        },
        "location_far": {
            "dimension": "location_preference",
            "vector_dims": [7],  # v7: 是否接受异地
            "weight": 0.9,
            "adjustment_strategy": "tighten_location"
        },
        "not_my_type": {
            "dimension": "personality_preference",
            "vector_dims": [32, 33, 34, 35],  # 大五人格维度
            "weight": 0.5,
            "adjustment_strategy": "infer_personality_preference"
        },
        "photo_concern": {
            "dimension": "visual_preference",
            "vector_dims": [137],  # v137: 实际偏好的性格类型
            "weight": 0.6,
            "adjustment_strategy": "infer_visual_preference"
        },
        "bio_issue": {
            "dimension": "content_preference",
            "vector_dims": [136],  # v136: 声明偏好 vs 实际行为差异度
            "weight": 0.5,
            "adjustment_strategy": "infer_content_preference"
        },
    }
    
    async def process_dislike_feedback(
        self,
        user_id: str,
        match_id: str,
        reason: str,
        optional_detail: str = None
    ) -> FeedbackLearningResult:
        """
        处理"不喜欢"反馈 - 红娘追问
        
        Args:
            user_id: 用户 ID
            match_id: 被拒绝的匹配对象 ID
            reason: 不喜欢的原因（从选项中选择）
            optional_detail: 详细说明（可选）
            
        Returns:
            FeedbackLearningResult:
                - learned_preference: 学习到的偏好
                - adjusted_vector: 调整后的向量
                - ai_response: 红娘风格回应
                - next_matches: 调整后的新推荐
        """
        # 1. 获取映射规则
        mapping = self.FEEDBACK_TO_PREFERENCE_MAPPING.get(reason, {
            "dimension": "general",
            "weight": 0.3
        })
        
        # 2. 从被拒绝对象推断"反向偏好"
        rejected_profile = await self._get_user_profile(match_id)
        inferred_preference = await self._infer_preference_from_rejection(
            reason=reason,
            rejected_profile=rejected_profile,
            mapping=mapping
        )
        
        # 3. 获取并调整用户向量
        user_vector = await self._get_user_vector(user_id)
        adjusted_vector = self._apply_preference_to_vector(
            user_vector=user_vector,
            preference=inferred_preference,
            mapping=mapping
        )
        
        # 4. 持久化学习结果
        await self._save_feedback_learning(
            user_id=user_id,
            match_id=match_id,
            reason=reason,
            learned_preference=inferred_preference,
            confidence=mapping["weight"]
        )
        
        # 5. 更新用户向量
        await self._update_user_vector(user_id, adjusted_vector)
        
        # 6. 生成红娘风格回应
        ai_response = await self._generate_matchmaker_followup(
            reason=reason,
            learned_preference=inferred_preference
        )
        
        # 7. 立即生成新的推荐
        next_matches = await self._generate_adjusted_matches(
            user_id=user_id,
            adjusted_vector=adjusted_vector,
            exclude_ids=[match_id],
            limit=3
        )
        
        return FeedbackLearningResult(
            learned_preference=inferred_preference,
            adjusted_vector=adjusted_vector,
            ai_response=ai_response,
            next_matches=next_matches
        )
    
    async def _infer_preference_from_rejection(
        self,
        reason: str,
        rejected_profile: dict,
        mapping: dict
    ) -> dict:
        """从拒绝对象推断反向偏好"""
        
        if reason == "age_not_match":
            # 拒绝了一个 35 岁的人 → 用户可能偏好更年轻/更年长的
            rejected_age = rejected_profile.get("age", 30)
            # 简单推断：如果被拒绝者比用户大，则调低上限；反之调高下限
            return {
                "preferred_age_adjustment": -3,  # 调低年龄上限
                "rejected_age": rejected_age,
                "confidence": mapping["weight"]
            }
        
        elif reason == "location_far":
            # 拒绝了异地的人 → 用户偏好同城
            return {
                "preferred_location_type": "same_city",
                "rejected_location": rejected_profile.get("location"),
                "confidence": mapping["weight"]
            }
        
        elif reason == "not_my_type":
            # 拒绝了某类型 → 需要更多信息来推断偏好
            # 这里可以让 LLM 分析被拒绝者的特征，推断用户偏好
            return {
                "rejected_personality_traits": await self._extract_personality_traits(rejected_profile),
                "confidence": mapping["weight"]
            }
        
        return {"dimension": mapping["dimension"], "confidence": mapping["weight"]}
    
    async def _generate_matchmaker_followup(
        self,
        reason: str,
        learned_preference: dict
    ) -> str:
        """生成红娘风格追问回应"""
        
        templates = {
            "age_not_match": [
                "好的，看来你更喜欢年轻一点的，下次给你找~",
                "明白了，年龄这块我记下了，帮你调整一下~",
                "懂了，下次给你推更符合你年龄偏好的~",
            ],
            "location_far": [
                "那下次给你找同城的，近距离更方便~",
                "了解，距离确实重要，我帮你筛同城的~",
                "好的，我记下了，下次优先推同城~",
            ],
            "not_my_type": [
                "每个人眼缘不一样，你觉得什么样的更吸引你？",
                "能说说你比较喜欢什么类型的吗？下次帮你精准找~",
                "好的，下次给你推不同类型的试试~",
            ],
            "photo_concern": [
                "照片确实很重要，下次帮你找照片更清晰自然的~",
                "明白，下次给你推照片更真实的~",
            ],
            "bio_issue": [
                "简介这块我记下了，下次给你找更有内容的~",
            ],
            "other": [
                "好的，我记下了，下次调整~",
            ],
        }
        
        return random.choice(templates.get(reason, ["好的，我记下了，下次调整~"]))
    
    async def process_like_feedback(
        self,
        user_id: str,
        match_id: str
    ) -> FeedbackLearningResult:
        """
        处理"喜欢"反馈
        
        从喜欢的对象推断正向偏好
        """
        liked_profile = await self._get_user_profile(match_id)
        
        # 从喜欢的对象提取特征，作为用户的正向偏好参考
        positive_preference = {
            "liked_age": liked_profile.get("age"),
            "liked_location": liked_profile.get("location"),
            "liked_interests": liked_profile.get("interests", []),
            "liked_traits": await self._extract_personality_traits(liked_profile),
            "confidence": 0.7  # 正向反馈置信度较高
        }
        
        # 更新用户向量（正向偏好）
        user_vector = await self._get_user_vector(user_id)
        adjusted_vector = await self._apply_positive_preference(user_vector, positive_preference)
        
        await self._save_feedback_learning(
            user_id=user_id,
            match_id=match_id,
            reason="like",
            learned_preference=positive_preference,
            confidence=0.7
        )
        
        ai_response = "好的，我记下了，下次给你找更多这类~"
        
        return FeedbackLearningResult(
            learned_preference=positive_preference,
            adjusted_vector=adjusted_vector,
            ai_response=ai_response,
            next_matches=[]  # 喜欢时不立即推新推荐，让用户先互动
        )
```

### 5.3 ImplicitPreferenceInferrer - 隐性偏好推断

```python
class ImplicitPreferenceInferrer:
    """隐性偏好推断 - 传统红娘第五步"""
    
    # 行为信号与偏好维度的映射
    BEHAVIOR_SIGNAL_MAPPING = {
        "browse_duration": {
            "description": "浏览时长",
            "long_signal": "感兴趣/认真",
            "short_signal": "快速判断/视觉导向",
            "inference_target": "decision_style"
        },
        "scroll_speed": {
            "description": "滑动速度",
            "fast_signal": "果断/明确偏好",
            "slow_signal": "犹豫/考虑多维度",
            "inference_target": "preference_certainty"
        },
        "photo_view_count": {
            "description": "照片查看次数",
            "high_signal": "重视外貌",
            "low_signal": "重视内容",
            "inference_target": "visual_preference"
        },
        "bio_read_duration": {
            "description": "简介阅读时长",
            "long_signal": "重视内容/内涵",
            "short_signal": "快速筛选",
            "inference_target": "content_preference"
        },
        "emoji_usage": {
            "description": "表情使用类型",
            "warm_emoji_signal": "偏好温暖型伴侣",
            "playful_emoji_signal": "偏好活泼型伴侣",
            "inference_target": "personality_preference"
        },
    }
    
    async def infer_from_behavior(
        self,
        user_id: str,
        behavior_events: List[BehaviorEvent]
    ) -> ImplicitInferenceResult:
        """
        从行为推断隐性偏好
        
        Args:
            user_id: 用户 ID
            behavior_events: 行为事件列表
            
        Returns:
            ImplicitInferenceResult:
                - inferred_dimensions: 推断的维度
                - confidence_scores: 各维度置信度
                - vector_adjustment: 向量调整建议
        """
        if len(behavior_events) < 10:
            return ImplicitInferenceResult(
                inferred_dimensions={},
                confidence_scores={},
                vector_adjustment={},
                status="insufficient_data"
            )
        
        # 1. 分析行为模式
        behavior_patterns = self._analyze_behavior_patterns(behavior_events)
        
        inferred = {}
        confidence = {}
        
        # 2. 从浏览时长推断决策风格
        avg_browse_duration = behavior_patterns.get("avg_browse_duration", 5)
        if avg_browse_duration > 10:
            inferred["decision_style"] = "thoughtful"  # 深思熟虑型
            confidence["decision_style"] = 0.6
        elif avg_browse_duration < 3:
            inferred["decision_style"] = "visual_first"  # 视觉优先型
            confidence["decision_style"] = 0.7
        
        # 3. 从照片查看次数推断视觉偏好
        avg_photo_views = behavior_patterns.get("avg_photo_views", 1)
        if avg_photo_views > 3:
            inferred["visual_preference"] = 0.8  # 高视觉偏好
            confidence["visual_preference"] = 0.6
        elif avg_photo_views < 1:
            inferred["visual_preference"] = 0.3  # 低视觉偏好
            confidence["visual_preference"] = 0.5
        
        # 4. 从简介阅读时长推断内容偏好
        avg_bio_duration = behavior_patterns.get("avg_bio_duration", 2)
        if avg_bio_duration > 5:
            inferred["content_preference"] = 0.8  # 重视内容
            confidence["content_preference"] = 0.6
        else:
            inferred["content_preference"] = 0.4  # 快速筛选
            confidence["content_preference"] = 0.5
        
        # 5. 从表情使用推断性格偏好
        emoji_analysis = self._analyze_emoji_usage(behavior_patterns.get("emoji_usage", []))
        if emoji_analysis["warm_emoji_ratio"] > 0.6:
            inferred["personality_preference"] = "gentle"  # 偏好温和型
            confidence["personality_preference"] = 0.5
        elif emoji_analysis["playful_emoji_ratio"] > 0.4:
            inferred["personality_preference"] = "playful"  # 偏好活泼型
            confidence["personality_preference"] = 0.5
        
        # 6. 计算总体置信度（基于样本量）
        sample_size = len(behavior_events)
        overall_confidence_boost = min(0.3, sample_size * 0.02)
        for key in confidence:
            confidence[key] = min(0.9, confidence[key] + overall_confidence_boost)
        
        # 7. 构建向量调整建议（写入 v136-v143）
        vector_adjustment = self._build_vector_adjustment(inferred, confidence)
        
        # 8. 持久化推断结果
        await self._save_implicit_inference(
            user_id=user_id,
            inferred=inferred,
            confidence=confidence,
            behavior_evidence=behavior_patterns
        )
        
        return ImplicitInferenceResult(
            inferred_dimensions=inferred,
            confidence_scores=confidence,
            vector_adjustment=vector_adjustment,
            status="success"
        )
    
    def _analyze_behavior_patterns(self, events: List[BehaviorEvent]) -> dict:
        """分析行为模式"""
        
        browse_durations = []
        photo_views = []
        bio_durations = []
        emoji_usage = []
        
        for event in events:
            if event.event_type == "profile_view":
                browse_durations.append(event.event_data.get("duration_seconds", 0))
                photo_views.append(event.event_data.get("photo_view_count", 0))
                bio_durations.append(event.event_data.get("bio_read_duration", 0))
            elif event.event_type == "chat_message":
                emoji_usage.extend(event.event_data.get("emojis_used", []))
        
        return {
            "avg_browse_duration": np.mean(browse_durations) if browse_durations else 5,
            "avg_photo_views": np.mean(photo_views) if photo_views else 1,
            "avg_bio_duration": np.mean(bio_durations) if bio_durations else 2,
            "emoji_usage": emoji_usage,
            "total_events": len(events),
        }
    
    def _analyze_emoji_usage(self, emojis: List[str]) -> dict:
        """分析表情使用"""
        
        warm_emojis = ["😊", "😄", "🥰", "💕", "❤️", "💖", "🌹", "☺️"]
        playful_emojis = ["😂", "🤣", "😜", "🤪", "😈", "🎉", "🔥", "✨"]
        
        warm_count = sum(1 for e in emojis if e in warm_emojis)
        playful_count = sum(1 for e in emojis if e in playful_emojis)
        total = len(emojis) if emojis else 1
        
        return {
            "warm_emoji_ratio": warm_count / total,
            "playful_emoji_ratio": playful_count / total,
        }
    
    def _build_vector_adjustment(self, inferred: dict, confidence: dict) -> dict:
        """构建向量调整建议"""
        
        # 隐性特征维度索引
        DIMENSION_MAPPING = {
            "visual_preference": 137,
            "content_preference": 136,
            "personality_preference": 138,
            "decision_style": 139,
        }
        
        adjustment = {}
        for key, value in inferred.items():
            dim_idx = DIMENSION_MAPPING.get(key)
            if dim_idx is not None:
                if isinstance(value, str):
                    # 字符串类型需要编码
                    value = self._encode_string_preference(value)
                adjustment[dim_idx] = {
                    "value": value,
                    "confidence": confidence.get(key, 0.5)
                }
        
        return adjustment
```

### 5.4 SocialProofService - 社会认同背书服务

```python
class SocialProofService:
    """社会认同服务 - 传统红娘第六步"""
    
    async def generate_social_proof_reasoning(
        self,
        match_candidate: MatchCandidate,
        user_context: dict
    ) -> SocialProofReasoning:
        """
        生成带口碑背书的推荐理由
        
        Args:
            match_candidate: 匹配候选人
            user_context: 用户上下文
            
        Returns:
            SocialProofReasoning:
                - main_reasoning: 主推荐理由
                - social_proof_elements: 社会认同元素
                - trust_badges: 信任徽章展示
        """
        # 1. 计算候选人的"口碑指标"
        social_metrics = await self._calculate_social_metrics(match_candidate.user_id)
        
        # 2. 构建社会认同元素
        social_proof_elements = []
        
        # 好评率背书
        if social_metrics["like_rate"] > 0.7:
            social_proof_elements.append(
                f"好评率{int(social_metrics['like_rate']*100)}%，很多人夸TA"
            )
        
        # 聊天活跃度背书
        if social_metrics["chat_response_rate"] > 0.8:
            social_proof_elements.append(
                "回复很积极，和她聊天的人都说体验不错"
            )
        
        # 成功案例背书（如果有）
        if social_metrics["success_match_count"] > 0:
            social_proof_elements.append(
                f"已有{social_metrics['success_match_count']}对通过TA成功匹配"
            )
        
        # 关系持续背书
        if social_metrics["avg_relationship_duration"] > 30:
            social_proof_elements.append(
                f"平均关系持续{int(social_metrics['avg_relationship_duration'])}天"
            )
        
        # 3. 获取信任徽章
        trust_badges = await self._get_user_trust_badges(match_candidate.user_id)
        
        # 4. 生成完整推荐理由
        main_reasoning = await self._generate_reasoning_with_proof(
            match_candidate=match_candidate,
            social_proof_elements=social_proof_elements,
            user_context=user_context
        )
        
        return SocialProofReasoning(
            main_reasoning=main_reasoning,
            social_proof_elements=social_proof_elements,
            trust_badges=trust_badges,
            confidence_level=self._calculate_confidence_level(social_metrics)
        )
    
    async def _calculate_social_metrics(self, user_id: str) -> dict:
        """计算社会认同指标"""
        
        # 从数据库获取用户的社会认同指标
        metrics = await self._get_social_metrics_from_db(user_id)
        
        if not metrics:
            # 如果没有数据，返回默认值
            return {
                "like_rate": 0.5,
                "chat_response_rate": 0.5,
                "success_match_count": 0,
                "avg_relationship_duration": 0,
            }
        
        return metrics
    
    async def _generate_reasoning_with_proof(
        self,
        match_candidate: MatchCandidate,
        social_proof_elements: List[str],
        user_context: dict
    ) -> str:
        """生成带社会认同的推荐理由"""
        
        # 基础匹配理由
        base_reasoning = await self._generate_base_reasoning(
            match_candidate, user_context
        )
        
        # 组合社会认同
        if social_proof_elements:
            proof_text = "，".join(social_proof_elements[:2])  # 最多取 2 个
            return f"{base_reasoning}。{proof_text}~"
        
        return base_reasoning
    
    def _calculate_confidence_level(self, social_metrics: dict) -> str:
        """计算置信度级别"""
        
        if social_metrics["like_rate"] > 0.8:
            return "high"
        elif social_metrics["like_rate"] > 0.6:
            return "medium"
        else:
            return "low"
```

---

## 六、数据模型扩展

### 6.1 用户反馈学习记录表

```python
class UserFeedbackLearningDB(Base):
    """用户反馈学习记录"""
    __tablename__ = "user_feedback_learning"
    
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # 反馈类型
    feedback_type = Column(String(20), nullable=False)  # like, dislike, skip
    
    # 反馈目标
    target_match_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # 反馈原因（dislike 时填写）
    dislike_reason = Column(String(50), nullable=True)  # age_not_match, location_far, etc.
    dislike_detail = Column(Text, nullable=True)  # 详细说明
    
    # 学习结果
    learned_preference_dimension = Column(String(50), nullable=True)
    learned_preference_value = Column(JSON, nullable=True)
    confidence_score = Column(Float, default=0.5)
    
    # 向量调整记录
    vector_dims_before = Column(Text, nullable=True)  # JSON，调整前的向量片段
    vector_dims_after = Column(Text, nullable=True)  # JSON，调整后的向量片段
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 6.2 隐性推断记录表

```python
class ImplicitInferenceDB(Base):
    """隐性偏好推断记录"""
    __tablename__ = "implicit_inferences"
    
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # 推断来源
    inference_source = Column(String(50), nullable=False)  # browse_duration, emoji_usage, etc.
    
    # 推断结果
    inferred_dimension = Column(String(50), nullable=False)
    inferred_value = Column(JSON, nullable=False)
    confidence = Column(Float, default=0.5)
    
    # 行为证据
    behavior_evidence = Column(Text, nullable=True)  # JSON，原始行为数据摘要
    
    # 向量调整
    vector_dim_index = Column(Integer, nullable=True)  # 调整的向量维度索引
    
    # 时间戳
    inferred_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 6.3 用户社会认同指标表

```python
class UserSocialMetricsDB(Base):
    """用户社会认同指标"""
    __tablename__ = "user_social_metrics"
    
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # 好评指标
    like_count = Column(Integer, default=0)  # 获得的喜欢数
    pass_count = Column(Integer, default=0)  # 获得的跳过数
    dislike_count = Column(Integer, default=0)  # 获得的不喜欢数
    like_rate = Column(Float, default=0.5)  # 好评率 = like / (like + dislike + pass)
    
    # 聊天指标
    chat_initiated_count = Column(Integer, default=0)
    chat_response_count = Column(Integer, default=0)
    chat_response_rate = Column(Float, default=0.5)
    avg_chat_duration_minutes = Column(Float, default=0.0)
    
    # 成功案例指标
    success_match_count = Column(Integer, default=0)  # 成功匹配数（关系持续 >30天）
    avg_relationship_duration = Column(Float, default=0.0)
    
    # 口碑评分
    reputation_score = Column(Float, default=0.5)  # 综合口碑评分（0-1）
    
    # 时间戳
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_calculated_at = Column(DateTime(timezone=True), nullable=True)
```

### 6.4 快速入门记录表

```python
class QuickStartRecordDB(Base):
    """快速入门记录"""
    __tablename__ = "quick_start_records"
    
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # 快速入门输入
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    location = Column(String(200), nullable=False)
    relationship_goal = Column(String(50), nullable=False)
    
    # 初始推荐结果
    initial_match_ids = Column(Text, default="")  # JSON，初始推荐的候选人 ID 列表
    initial_match_count = Column(Integer, default=0)
    
    # 用户响应
    viewed_count = Column(Integer, default=0)  # 查看了多少个
    liked_count = Column(Integer, default=0)  # 喜欢了多少个
    disliked_count = Column(Integer, default=0)  # 不喜欢了多少个
    
    # 转化结果
    first_like_at = Column(DateTime(timezone=True), nullable=True)  # 第一次喜欢的时间
    first_chat_at = Column(DateTime(timezone=True), nullable=True)  # 第一次聊天的时间
    completed_quick_start = Column(Boolean, default=False)  # 是否完成快速入门
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

---

## 七、API接口设计

### 7.1 快速入门接口

```python
# POST /api/quick-start/register
# 请求
{
    "age": 28,
    "gender": "male",
    "location": "北京",
    "relationship_goal": "serious"  # 仅 4 个选项：serious/marriage/dating/casual
}

# 响应
{
    "success": true,
    "data": {
        "user_id": "user_xxx",
        "initial_matches": [
            {
                "user_id": "match_1",
                "name": "小红",
                "age": 26,
                "location": "北京",
                "avatar_url": "...",
                "compatibility_preview": "同城，年龄合适",
                "social_proof": {
                    "like_rate": 85,
                    "elements": ["好评率85%", "很多人夸她性格好"],
                    "trust_badges": ["identity_verified", "active_user"]
                }
            },
            // ... 最多 5 个
        ],
        "ai_message": "好的，我这有几个觉得合适的，你先看看~",
        "next_step": "show_matches",
        "quick_start_completed": false
    }
}
```

### 7.2 反馈学习接口

```python
# POST /api/match/feedback
# 请求
{
    "user_id": "user_xxx",
    "match_id": "match_1",
    "feedback_type": "dislike",  # like, dislike, skip
    "reason": "age_not_match",  # 仅 dislike 时需要
    "optional_detail": "感觉年龄差距有点大"  # 可选
}

# 响应（dislike 时）
{
    "success": true,
    "data": {
        "learned_preference": {
            "dimension": "age_preference",
            "preferred_age_max": 26,
            "confidence": 0.8
        },
        "ai_response": "好的，看来你更喜欢年轻一点的，下次给你找~",
        "next_matches": [
            {
                "user_id": "match_2",
                "name": "小芳",
                "age": 24,
                "location": "北京",
                "social_proof": {...}
            },
            // ... 最多 3 个
        ],
        "vector_updated": true
    }
}

# 响应（like 时）
{
    "success": true,
    "data": {
        "learned_preference": {
            "dimension": "positive_preference",
            "liked_traits": {...}
        },
        "ai_response": "好的，我记下了，下次给你找更多这类~",
        "vector_updated": true,
        "can_start_chat": true  # 可以开始聊天
    }
}
```

### 7.3 隐性偏好查询接口

```python
# GET /api/user/{user_id}/implicit-preferences
# 响应
{
    "success": true,
    "data": {
        "implicit_preferences": [
            {
                "dimension": "visual_preference",
                "value": 0.7,
                "confidence": 0.6,
                "source": "photo_view_behavior",
                "evidence": "平均查看照片3.5次",
                "inferred_at": "2026-04-11T10:00:00Z"
            },
            {
                "dimension": "personality_preference",
                "value": "gentle",
                "confidence": 0.5,
                "source": "emoji_usage",
                "evidence": "温暖表情使用率68%"
            }
        ],
        "vector_dimensions_filled": [136, 137, 138, 139],
        "total_inferences": 5,
        "overall_confidence": 0.55
    }
}
```

### 7.4 学习进度查询接口

```python
# GET /api/user/{user_id}/learning-progress
# 响应
{
    "success": true,
    "data": {
        "learning_progress": {
            "feedback_count": 15,
            "like_count": 8,
            "dislike_count": 5,
            "skip_count": 2,
            "dimensions_learned": [
                "age_preference",
                "location_preference",
                "personality_preference"
            ],
            "implicit_inferences": 5,
            "vector_completeness": 0.35  # 向量完整度
        },
        "recommendation_quality": {
            "match_rate": 0.65,  # 匹配成功率
            "avg_compatibility_score": 0.72
        },
        "next_learning_targets": [
            "values_preference",
            "lifestyle_preference"
        ]
    }
}
```

---

## 八、前端交互设计

### 8.1 快速入门页面流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     快速入门页面交互流程                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: 欢迎引导                                                        │
│  ─────────────────────────────────────────────────────                  │
│  [Her 头像]                                                             │
│  "你好！我是 Her，帮你找对象的朋友。                                      │
│   先了解几个关键信息，马上给你推荐~"                                      │
│                                                                         │
│  Step 2: 年龄选择                                                        │
│  ─────────────────────────────────────────────────────                  │
│  [简单卡片]                                                              │
│  "你多大啦？"                                                            │
│  [18-25] [26-30] [31-35] [36-40] [40+]                                  │
│                                                                         │
│  Step 3: 性别选择                                                        │
│  ─────────────────────────────────────────────────────                  │
│  [简单卡片]                                                              │
│  "你是男生还是女生？"                                                     │
│  [男生 👨] [女生 👩]                                                     │
│                                                                         │
│  Step 4: 城市                                                            │
│  ─────────────────────────────────────────────────────                  │
│  [简单卡片]                                                              │
│  "你在哪个城市？"                                                         │
│  [输入框或热门城市标签]                                                   │
│                                                                         │
│  Step 5: 关系目标                                                        │
│  ─────────────────────────────────────────────────────                  │
│  [简单卡片]                                                              │
│  "想找什么样的关系？"                                                     │
│  [认真恋爱 💕] [奔着结婚 💍] [轻松交友 ☕] [随便聊聊 💭]                   │
│                                                                         │
│  Step 6: 立即推荐                                                        │
│  ─────────────────────────────────────────────────────                  │
│  [Her 头像]                                                             │
│  "好的，我这有几个觉得合适的，你先看看~"                                  │
│                                                                         │
│  [候选人卡片列表]                                                        │
│  ┌───────────────────────────────────────────────────┐                  │
│  │ [头像] 小红，26岁，北京                              │                  │
│  │ 好评率85%，很多人夸她性格好                          │                  │
│  │ [喜欢 ❤️] [不喜欢 👎] [跳过 ⏭️]                      │                  │
│  └───────────────────────────────────────────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 反馈追问交互设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     不喜欢追问交互                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  用户点击 [不喜欢 👎]                                                     │
│  ─────────────────────────────────────────────────────                  │
│                                                                         │
│  [弹出追问卡片]                                                          │
│  ┌───────────────────────────────────────────────────┐                  │
│  │ [Her 头像]                                         │                  │
│  │ "不喜欢的原因是什么？告诉我，下次帮你调整~"         │                  │
│  │                                                    │                  │
│  │ [年龄不太合适 📅]                                   │                  │
│  │ [距离太远了 📍]                                     │                  │
│  │ [不是我喜欢的类型 💔]                               │                  │
│  │ [照片让我犹豫 📸]                                   │                  │
│  │ [简介不太吸引我 📝]                                 │                  │
│  │ [其他原因 💭]                                       │                  │
│  └───────────────────────────────────────────────────┘                  │
│                                                                         │
│  用户选择 [年龄不太合适 📅]                                               │
│  ─────────────────────────────────────────────────────                  │
│                                                                         │
│  [Her 头像]                                                             │
│  "好的，看来你更喜欢年轻一点的，下次给你找~"                              │
│                                                                         │
│  [立即显示新推荐]                                                        │
│  ┌───────────────────────────────────────────────────┐                  │
│  │ [头像] 小芳，24岁，北京                              │                  │
│  │ 年龄更合适了~                                        │                  │
│  │ [喜欢 ❤️] [不喜欢 👎] [跳过 ⏭️]                      │                  │
│  └───────────────────────────────────────────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.3 渐进式补全设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     渐进式画像补全                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  场景：用户浏览了几轮推荐后                                               │
│  ─────────────────────────────────────────────────────                  │
│                                                                         │
│  [Her 头像]                                                             │
│  "看了一圈，我发现你可能喜欢活泼类型的~                                   │
│   能告诉我你平时喜欢做什么吗？这样我帮你找更精准~"                        │
│                                                                         │
│  [兴趣选择卡片（轻量版）]                                                 │
│  ┌───────────────────────────────────────────────────┐                  │
│  │ [旅行 ✈️] [美食 🍜] [音乐 🎵] [电影 🎬]             │                  │
│  │ [阅读 📚] [健身 💪] [游戏 🎮] [摄影 📷]             │                  │
│  │                                                    │                  │
│  │ [随便，都可以] [下次再说]                           │                  │
│  └───────────────────────────────────────────────────┘                  │
│                                                                         │
│  用户选择后：                                                            │
│  ─────────────────────────────────────────────────────                  │
│  [Her 头像]                                                             │
│  "记下了！下次给你推也喜欢旅行的~"                                       │
│                                                                         │
│  注意：                                                                  │
│  - 补全问题不强制回答                                                    │
│  - 可以"下次再说"                                                       │
│  - 补全时机：用户浏览 10+ 个推荐后                                       │
│  - 补全频率：每隔 20 个推荐弹出一次                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 九、实现路线图

### 9.1 阶段划分

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           实现路线图                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1: 最小信息快速入门（2天） ✅ 已完成                               │
│  ├── Day 1: QuickStartService 后端实现                                  │
│  │   - ✅ 数据模型创建（QuickStartRecordDB, UserFeedbackLearningDB）    │
│  │   - ✅ 快速入门 API（/api/quick-start/register）                      │
│  │   - ✅ 冷启动匹配逻辑                                                 │
│  ├── Day 2: 前端快速入门页面                                             │
│  │   - ✅ 4 步引导卡片组件                                               │
│  │   - ✅ 初始推荐展示                                                   │
│  │   - ✅ 红娘风格 UI                                                    │
│                                                                         │
│  Phase 2: 反馈学习循环（3天） ✅ 已完成                                   │
│  ├── Day 3: FeedbackLearningLoop 后端                                   │
│  │   - ✅ 反馈处理 API（/api/quick-start/feedback）                      │
│  │   - ✅ 原因选项映射                                                   │
│  │   - ✅ 偏好学习逻辑                                                   │
│  ├── Day 4: 前端反馈交互                                                 │
│  │   - ✅ 不喜欢追问卡片                                                 │
│  │   - ✅ 原因选择组件                                                   │
│  │   - ✅ 新推荐展示                                                     │
│  ├── Day 5: 向量更新逻辑                                                 │
│  │   - ✅ vector_adjustment_service.py                                  │
│  │   - ✅ FEEDBACK_TO_VECTOR_MAPPING                                    │
│  │   - ✅ 持久化学习结果                                                 │
│                                                                         │
│  Phase 3: 隐性推断机制（2天） ✅ 已完成                                   │
│  ├── Day 6: ImplicitPreferenceInferrer                                 │
│  │   - ✅ BehaviorSignalCollector                                       │
│  │   - ✅ BEHAVIOR_TO_VECTOR_MAPPING                                    │
│  ├── Day 7: 行为追踪集成                                                 │
│  │   - ✅ useBehaviorTracking.ts Hook                                   │
│  │   - ✅ /api/quick-start/behavior/* 端点                               │
│                                                                         │
│  Phase 4: 社会认同背书（1天） ✅ 已完成                                   │
│  ├── Day 8: SocialProofService                                         │
│  │   - ✅ 社会认同指标计算                                               │
│  │   - ✅ 推荐理由生成                                                   │
│  │   - ✅ 信任徽章集成（VerificationBadgeDB）                            │
│                                                                         │
│  Phase 5: 灰度配置系统（2天） ✅ 已完成                                   │
│  ├── Day 9: 灰度配置服务                                                │
│  │   - ✅ grayscale_config_service.py                                   │
│  │   - ✅ FeatureFlagDB, ABExperimentDB                                 │
│  │   - ✅ 用户分组策略                                                   │
│  ├── Day 10: 灰度配置 API + 前端集成                                     │
│  │   - ✅ /api/grayscale/* 端点                                         │
│  │   - ✅ A/B 测试框架                                                   │
│  │   - ✅ 默认配置初始化                                                 │
│                                                                         │
│  总计：约 10 天 ✅ 全部完成                                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 里程碑验收标准

| 阶段 | 里程碑 | 验收标准 | 状态 |
|------|--------|---------|------|
| Phase 1 | 快速入门上线 | 用户 30 秒内看到初始推荐 | ✅ 已验收 |
| Phase 2 | 反馈学习上线 | 用户不喜欢后能立即看到调整后的推荐 | ✅ 已验收 |
| Phase 3 | 隐性推断上线 | 系统能从行为推断偏好并展示 | ✅ 已验收 |
| Phase 4 | 社会认同上线 | 推荐理由包含口碑背书 + 信任徽章 | ✅ 已验收 |
| Phase 5 | 灰度配置上线 | A/B 测试框架可用，50%灰度运行 | ✅ 已验收 |

### 9.3 已实现的 API 端点

```
/api/quick-start/
├── GET  /options                     # 获取选项配置
├── POST /register                    # 30秒快速入门
├── POST /feedback                    # 处理用户反馈
├── POST /stats                       # 更新浏览统计
├── GET  /user/{user_id}/social-proof # 获取社会认同背书
├── GET  /user/{user_id}/learning-progress # 获取学习进度
├── POST /behavior/track              # 单行为事件追踪
├── POST /behavior/batch-track        # 批量行为追踪 + 推断
├── GET  /behavior/{user_id}/signals  # 获取行为信号统计
└── GET  /health                      # 健康检查

/api/grayscale/
├── POST /feature/check               # 检查功能开关
├── POST /experiment/variant          # 获取实验分组
├── GET  /quick-start/{user_id}/enabled # 快速入门灰度检查
├── POST /flags                       # 创建功能开关
├── GET  /flags                       # 获取功能开关列表
├── POST /experiments                 # 创建 A/B 实验
├── POST /init-defaults               # 初始化默认配置
└── GET  /health                      # 健康检查
```

---

## 十、灰度迁移方案

### 10.1 并行运行策略

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         灰度迁移方案                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Week 1: 并行运行                                                        │
│  ─────────────────────────────────────────────────────                  │
│  - 新用户 50% 走 QuickStart 流程（A 组）                                 │
│  - 新用户 50% 走原有 ProfileCollection 流程（B 组）                      │
│  - 老用户保持原有流程                                                    │
│                                                                         │
│  对比指标：                                                              │
│  - 完成率：完成入门流程的比例                                            │
│  - 首次匹配时间：从注册到看到第一个推荐的时间                             │
│  - 首次互动时间：从注册到第一次喜欢/聊天的时间                            │
│  - 用户满意度：首日留存率                                                │
│                                                                         │
│  Week 2: 效果评估                                                        │
│  ─────────────────────────────────────────────────────                  │
│  - 如果 A 组：                                                          │
│    - 完成率提升 > 30%                                                   │
│    - 首次匹配时间缩短 > 50%                                             │
│    - 首次互动时间缩短 > 20%                                             │
│  - 则决定全面切换到 QuickStart 流程                                      │
│  - 否则分析原因，优化 QuickStart 流程                                   │
│                                                                         │
│  Week 3: 全面切换                                                        │
│  ─────────────────────────────────────────────────────                  │
│  - 所有新用户默认走 QuickStart 流程                                      │
│  - ProfileCollectionSkill 降级为"渐进补全"用途                          │
│  - 在用户浏览推荐过程中，渐进式弹出补全问题                               │
│                                                                         │
│  Week 4: 迭代优化                                                        │
│  ─────────────────────────────────────────────────────                  │
│  - 根据反馈数据优化推荐算法                                              │
│  - 优化反馈学习循环的追问逻辑                                            │
│  - 增加更多隐性推断维度                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 回滚策略

如果 A/B 测试效果不佳，回滚方案：

1. **快速回滚**：切换新用户流量分配，100% 回到原有流程
2. **数据保留**：保留 A 组用户的反馈学习数据，用于后续优化
3. **问题分析**：分析 A 组效果不佳的原因（门槛太高？推荐质量？交互体验？）

---

## 十一、效果评估指标

### 11.1 核心指标

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          效果评估指标                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【入门效率指标】                                                        │
│  ├── 入门完成率：完成快速入门的比例                                      │
│  ├── 入门耗时：从开始到看到第一个推荐的秒数                              │
│  ├── 首次互动时间：从注册到第一次喜欢/聊天的时间                         │
│  └── 入门流失率：在入门阶段离开的比例                                    │
│                                                                         │
│  【匹配质量指标】                                                        │
│  ├── 喜欢率：用户对推荐对象的比例                                       │
│  ├── 双向匹配率：双方互相喜欢的比例                                      │
│  ├── 聊天转化率：喜欢后发起聊天的比例                                    │
│  └── 关系持续率：关系持续超过 30 天的比例                                │
│                                                                         │
│  【学习效果指标】                                                        │
│  ├── 偏好学习数：系统学习的偏好维度数量                                  │
│  ├── 向量完整度：用户向量的填充比例                                     │
│  ├── 推荐匹配度提升：随着学习，推荐质量提升幅度                          │
│  ├── 隐性推断准确率：隐性偏好推断与用户行为一致性                        │
│                                                                         │
│  【用户体验指标】                                                        │
│  ├── 首日留存率：注册后首日继续使用的比例                                │
│  ├── 推荐满意度：用户对推荐质量的评分                                   │
│  ├── 互动深度：聊天消息数、聊天时长                                     │
│  └────────────────────────────────────────────────────                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 对比指标

| 指标 | 目标值 | 当前值（预估） | 提升目标 |
|------|-------|---------------|---------|
| 入门完成率 | > 90% | ~60% | +30% |
| 入门耗时 | < 30s | ~180s | -83% |
| 首次互动时间 | < 2min | ~10min | -80% |
| 首日留存率 | > 40% | ~20% | +20% |
| 喜欢率 | > 30% | ~15% | +15% |

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| QuickStart | 快速入门流程，30秒完成基础信息收集 |
| FeedbackLearningLoop | 反馈学习循环，从用户反馈中学习偏好 |
| ImplicitPreference | 隐性偏好，从行为推断的偏好 |
| SocialProof | 社会认同背书，"很多人夸TA"的推荐方式 |
| ColdStartMatch | 冷启动匹配，基于最少信息的初始推荐 |
| VectorCompleteness | 向量完整度，用户画像向量的填充比例 |

### B. 参考资料

1. 传统婚恋机构工作流程研究
2. 用户行为分析与偏好推断研究
3. 社会认同理论（Social Proof Theory）
4. 渐进式画像构建方法论
5. 冷启动推荐算法研究

---

> 文档版本：v1.0
> 最后更新：2026-04-11
> 作者：AI Team
> 
> **核心理念**：借鉴传统红娘工作模式，让用户先"看到"，再"学到"，渐进精准。