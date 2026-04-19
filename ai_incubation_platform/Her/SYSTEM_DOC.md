# Her 系统文档

> **AI Native 婚恋匹配平台** - Agent Native 架构实践
> 
> 文档版本：2.0 | 更新日期：2026-04-19

---

## 目录

1. [愿景与背景](#愿景与背景)
2. [系统架构](#系统架构)
3. [核心功能模块](#核心功能模块)
4. [技术栈概览](#技术栈概览)
5. [数据模型设计](#数据模型设计)
6. [Agent Native 架构详解](#agent-native-架构详解)
7. [前端架构](#前端架构)
8. [API 层设计](#api-层设计)
9. [匹配系统设计](#匹配系统设计)
10. [产品规划建议](#产品规划建议)

---

## 愿景与背景

### 核心愿景

**Her** 是一个 **AI Native 婚恋匹配平台**，以 AI Agent 作为核心决策引擎，实现从"被动工具"到"主动顾问"的范式跃迁。

核心理念：**AI 是决策大脑，不是规则执行器**。

### 解决的核心痛点

| 痛点 | 传统解决方案 | Her 的解决方案 |
|------|-------------|---------------|
| **用户不知道自己想要什么** | 让用户填写问卷，依赖规则匹配 | Her 顾问服务：认知偏差识别，帮助用户发现真实需求 |
| **表面偏好 ≠ 实际适合** | 简单的关键词匹配 | SelfProfile + DesireProfile 双画像系统，行为推断实际偏好 |
| **匹配结果缺乏解释** | 只展示分数，无建议 | MatchAdvice：每条匹配都有专业建议和风险提示 |
| **交互门槛高** | 表单 + 列表，功能分散 | Chat-first 设计：一切通过对话，Generative UI 动态生成界面 |
| **信息收集枯燥** | 长问卷，用户放弃 | QuickStart：对话式逐步收集，AI 自主感知缺失字段 |

### 目标用户

- **核心用户**：25-40 岁单身人群，寻求认真恋爱关系
- **价值主张**：专业婚恋顾问 Her 全程陪伴，从画像收集到匹配建议到关系经营
- **差异化**：AI 作为决策引擎而非工具，主动感知、主动建议、主动推送

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端层 (React + TypeScript)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ ChatInterface│  │ HomePage    │  │ SwipeMatch   │  │ Generative UI    │  │
│  │ (对话入口)   │  │ (主页面)    │  │ (滑动匹配)   │  │ (动态组件渲染)   │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓ HTTP/SSE (DeerFlow API)
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DeerFlow Agent Runtime (LangGraph)                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Lead Agent      │  │  SOUL.md         │  │  her_tools (7 Tools)     │  │
│  │  (决策引擎)      │  │  (角色定义)      │  │  (纯数据查询)            │  │
│  │  - 意图理解      │  │  - 核心原则      │  │  - her_get_profile       │  │
│  │  - 工具编排      │  │  - 安全边界      │  │  - her_find_candidates   │  │
│  │  - 输出决策      │  │  - 工具指南      │  │  - her_update_preference │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Memory System (用户画像持久化)                                        │   │
│  │  - 用户独立 memory 文件：{user_id}/memory.json                         │   │
│  │  - 对话历史持久化：checkpointer                                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓ 数据访问
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Her Backend (FastAPI + SQLAlchemy)                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  REST API 层     │  │  Service 层      │  │  Skills (30+)            │  │
│  │  - /api/deerflow │  │  - HerAdvisor    │  │  - date_coach_skill      │  │
│  │  - /api/matching │  │  - UserProfile   │  │  - relationship_coach    │  │
│  │  - /api/chat     │  │  - Conversation  │  │  - preference_learner    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  ConversationMatchService (降级路径)                                   │   │
│  │  - IntentAnalyzer: 意图理解                                            │   │
│  │  - QueryQualityChecker: 查询质量校验                                   │   │
│  │  - MatchExecutor: 匹配执行                                             │   │
│  │  - AdviceGenerator: 建议生成                                           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓ 数据存储
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据层 (SQLite + 向量存储)                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  UserDB          │  │  Matching Models │  │  Profile Models          │  │
│  │  (125 字段)      │  │  - MatchHistory  │  │  - UserVectorProfile     │  │
│  │  - 基础信息      │  │  - SwipeAction   │  │  - ProfileConfidence     │  │
│  │  - 偏好设置      │  │  - UserPreference│  │  - ImplicitInference     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Extended Models (高级功能)                                            │   │
│  │  - VideoDateDB: 视频约会                                               │   │
│  │  - AICompanionSessionDB: AI 预沟通                                     │   │
│  │  - RelationshipProgressDB: 关系进展                                    │   │
│  │  - SafetyZoneDB: 安全区域                                              │   │
│  └──────────────────────────────────────────────────────────────────────┐   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 技术栈概览

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| **前端** | React 18 + TypeScript + Vite + Ant Design | SPA 应用，Generative UI 动态渲染 |
| **Agent Runtime** | DeerFlow (LangGraph) | Agent 执行引擎，工具编排，状态管理 |
| **后端** | FastAPI + SQLAlchemy + Pydantic | REST API + 服务层 |
| **数据库** | SQLite (开发) / PostgreSQL (生产) | 关系型数据库，125+ 字段用户模型 |
| **向量存储** | Qdrant (计划中) | 语义匹配，相似度计算 |
| **缓存** | Redis | 会话缓存，用户画像缓存 |
| **LLM** | Claude / GLM-5 (可配置) | 意图理解，匹配建议，对话生成 |

---

## 核心功能模块

### 1. 对话式匹配入口（Chat-first）

**核心文件**: `frontend/src/components/ChatInterface.tsx`

**功能描述**:
- 纯对话式交互，无固定菜单
- 用户消息 → DeerFlow Agent → 工具调用 → Generative UI 渲染
- 支持流式输出（SSE），实时进度提示
- QuickStart 信息收集流程：对话式逐步收集用户画像

**交互流程**:
```
用户输入 "帮我找对象"
    ↓
DeerFlow Agent 意图理解
    ↓
调用 her_find_candidates 工具
    ↓
返回候选人数据（30+ 位）
    ↓
Agent 筛选推荐 1-3 位
    ↓
输出 GENERATIVE_UI 标签
    ↓
前端渲染 UserProfileCard 组件
```

### 2. 智能匹配系统

**核心文件**:
- `deerflow/community/her_tools/match_tools.py` - 候选人查询工具
- `src/services/her_advisor_service.py` - 顾问建议服务

**匹配流程**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     硬约束过滤（代码执行）                        │
│  - 性别过滤（异性恋/同性恋/双性恋）                               │
│  - 地点过滤（不接受异地 → 只查同城）                              │
│  - 安全边界（排除封禁用户、测试账号）                              │
│  - 最大扫描上限：30 位候选人                                      │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     软约束筛选（Agent 决策）                      │
│  - 年龄范围匹配                                                   │
│  - 关系目标匹配                                                   │
│  - 置信度排序                                                     │
│  - Agent 根据上下文自主判断                                       │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Her 建议生成（LLM 分析）                      │
│  - CognitiveBiasDetector: 认知偏差识别                            │
│  - MatchAdvisor: 匹配建议生成                                     │
│  - ProactiveSuggestionGenerator: 主动建议                         │
└─────────────────────────────────────────────────────────────────┘
```

**返回数据结构**:
```json
{
  "success": true,
  "data": {
    "candidates": [
      {
        "display_id": "candidate_001",
        "user_id": "uuid-xxx",
        "name": "李雪",
        "age": 26,
        "location": "上海",
        "interests": ["阅读", "瑜伽"],
        "confidence_score": 85,
        "avatar_url": "https://..."
      }
    ],
    "user_preferences": {
      "preferred_age_min": 25,
      "preferred_age_max": 30,
      "accept_remote": "yes"
    },
    "missing_fields": [],
    "missing_preferences": []
  }
}
```

### 3. 用户画像系统

**核心文件**: `src/services/user_profile_service.py`

**双画像架构**:

| 画像类型 | 用途 | 数据来源 |
|---------|------|---------|
| **SelfProfile** | "这个人是什么样的" | 注册表单 + QuickStart + 行为推断 |
| **DesireProfile** | "这个人想要什么" | 用户表达 + 点击行为 + 匹配反馈 |

**SelfProfile 维度**:
- 基础属性：年龄、性别、地点、收入、职业、学历
- 动态画像：实际性格 vs 自称性格（性格认知偏差）
- 情感需求：依恋类型、情感需求列表
- 权力动态：控制型/顺从型/平等型
- 置信度：整体置信度 + 各维度置信度

**DesireProfile 维度**:
- 表面偏好：用户自称想要的
- 实际偏好：行为推断（点击、搜索、匹配反馈）
- 偏好差距：surface_preference vs actual_preference
- 一票否决：deal_breakers 列表

### 4. QuickStart 信息收集

**核心文件**: `frontend/src/components/ChatInterface.tsx` (generateQuickStartQuestionCard)

**收集字段**:

| 类别 | 字段 | 收集方式 |
|------|------|---------|
| **注册基础** | 姓名、年龄、性别、所在地 | 输入/单选 |
| **属性字段** | 身高、学历、职业、收入、房产、车 | 单选 |
| **一票否决** | 生育意愿、消费观念 | 单选（提示重要性） |
| **核心价值观** | 家庭重要度、工作生活平衡 | 单选 |
| **迁移能力** | 迁移意愿、异地接受度 | 单选 |
| **生活方式** | 作息类型 | 单选 |

**流程设计**:
- 检查缺失字段 → 生成问题卡片 → 用户选择 → 写入画像 → 继续下一字段
- 完成后同步到 DeerFlow Memory

### 5. Generative UI 系统

**核心文件**:
- `frontend/src/types/generativeUI.ts` - 组件映射
- `backend/src/generative_ui_schema.py` - 后端 Schema

**已注册组件**:

| 组件类型 | 前端渲染 | 用途 |
|---------|---------|------|
| `UserProfileCard` | UserProfileCard | 单个候选人详情卡片 |
| `MatchCardList` | MatchCardList | 候选人列表 |
| `ProfileQuestionCard` | ProfileQuestionCard | 信息收集问题卡片 |
| `ChatInitiationCard` | ChatInitiationCard | 发起聊天确认卡片 |
| `DatePlanCard` | DatePlanCard | 约会方案推荐 |
| `IcebreakerCard` | IcebreakerCard | 破冰建议卡片 |
| `CompatibilityChart` | CompatibilityChart | 兼容性分析图表 |
| `TopicsCard` | TopicsCard | 话题推荐卡片 |
| `RelationshipHealthCard` | RelationshipHealthCard | 关系健康度卡片 |
| `SimpleResponse` | 纯文本 | 无卡片，纯文字回复 |

**输出格式**:
```
[GENERATIVE_UI]
{"component_type": "UserProfileCard", "props": {"name": "李雪", "age": 26, ...}}
[/GENERATIVE_UI]
```

### 6. 滑动匹配页面

**核心文件**: `frontend/src/pages/SwipeMatchPage.tsx`

**功能**:
- Tinder 风格滑动匹配
- 支持 SuperLike（超级喜欢）
- 每日匹配限制（会员功能）
- 匹配成功后直接进入聊天室

### 7. 视频约会系统

**核心文件**: `src/api/video_date.py`

**功能**:
- 视频约会预约
- 约会报告生成
- 破冰问题库（IcebreakerQuestionDB）
- 虚拟背景支持

### 8. AI 预沟通

**核心文件**: `src/models/precomm.py`

**功能**:
- AI 代表用户与候选人预沟通
- 分析对话内容，提取关键信息
- 生成对话摘要，供用户决策

### 9. 关系进展追踪

**核心文件**: `src/db/models/relationship.py`

**功能**:
- 记录关系进展里程碑
- 关系健康度评估
- 冲突事件记录
- 关系建议推送

### 10. 安全与认证

**核心文件**:
- `src/api/identity_verification.py` - 身份认证
- `src/api/verification_badges.py` - 认证徽章
- `src/db/models/safety.py` - 安全模型

**功能**:
- 人脸认证（FaceVerificationPage）
- 学历认证、职业认证
- 安全区域（SafetyZone）
- 信任联系人（TrustedContact）
- 用户举报与封禁

---

## Agent Native 架构详解

### 三层分离架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     System Prompt Layer (SOUL.md)               │
│                                                                 │
│  ✅ 职责：                                                      │
│  - 角色定义：智能红娘助手                                        │
│  - 核心原则：理解意图、诚实原则、主动补齐、自主处理              │
│  - 安全边界：拒绝违规请求                                        │
│  - 工具使用指南：何时调用、如何处理                              │
│                                                                 │
│  ❌ 不应包含：                                                   │
│  - 触发词映射表（关键词 → 工具）                                 │
│  - 输出格式规则（由 Agent 自主决定）                             │
│  - 流程步骤（由 Agent 自主判断）                                 │
│  - 业务逻辑规则（在 Prompt 中表达，而非硬编码）                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           ↓ 调用
┌─────────────────────────────────────────────────────────────────┐
│                     Tools Layer (her_tools)                     │
│                                                                 │
│  ✅ 职责（7 个工具）：                                           │
│  - her_get_profile: 获取用户画像                                │
│  - her_find_candidates: 查询候选匹配对象池                       │
│  - her_get_conversation_history: 获取对话历史                   │
│  - her_update_preference: 更新用户偏好                          │
│  - her_create_profile: 创建用户档案                             │
│  - her_record_feedback: 记录用户反馈                            │
│  - her_get_feedback_history: 获取反馈历史                       │
│                                                                 │
│  ✅ 设计原则：                                                   │
│  - 只做硬约束过滤（安全边界）                                    │
│  - 只返回原始数据（JSON）                                        │
│  - 不包含业务逻辑（筛选、排序、评分）                            │
│  - 不返回 instruction/output_hint                               │
│                                                                 │
│  ❌ 禁止行为：                                                   │
│  - if-else 业务判断                                              │
│  - 预设模板列表直接返回                                          │
│  - 置信度计算、匹配度计算                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           ↓ 依赖
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer                                   │
│                                                                 │
│  ✅ 职责：                                                      │
│  - 数据存储（SQLite/PostgreSQL）                                │
│  - 基础查询（无业务逻辑）                                        │
│                                                                 │
│  ❌ 不应包含：                                                   │
│  - 任何业务逻辑                                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 执行循环

```
用户消息 → Agent 思考(LLM) → 选择工具 → 执行工具(纯数据) → 返回数据
                                                        ↓
                         Agent 再思考(LLM) ← 解读数据决定下一步
                                                        ↓
                         继续执行 或 输出回复 → 完成
```

### 硬约束 vs 软约束分层

| 类型 | 执行位置 | 示例 |
|------|---------|------|
| **硬约束（代码）** | Tool 层 | 安全边界、封禁用户过滤、性别过滤 |
| **软约束（Prompt）** | Agent 层 | 年龄范围筛选、同城优先、置信度排序 |

### DeerFlow 配置

**核心配置文件**: `deerflow/extensions_config.json`

```json
{
  "skills": {
    "her_matchmaking": { "enabled": true },
    "her_relationship_coach": { "enabled": true },
    "her_date_planning": { "enabled": true },
    "her_chat_assistant": { "enabled": true },
    "her_matching_flow": { "enabled": true },
    "autonomous_test": { "enabled": true }
  }
}
```

---

## 数据模型设计

### 核心用户模型（UserDB）

**文件**: `src/db/models/user.py`

**字段分类**:

| 类别 | 字段 | 说明 |
|------|------|------|
| **基础信息** | id, name, age, gender, location | 注册表单收集 |
| **偏好设置** | preferred_age_min/max, preferred_location, accept_remote | QuickStart 收集 |
| **生活方式** | want_children, spending_style, sleep_type | 一票否决维度 |
| **价值观** | family_importance, work_life_balance, migration_willingness | 核心价值观 |
| **动态画像** | actual_personality, claimed_personality, personality_gap | 行为推断 |
| **情感需求** | attachment_style, emotional_needs | 行为推断 |
| **安全状态** | is_active, is_permanently_banned, verification_status | 安全控制 |

### 匹配相关模型

| 模型 | 用途 |
|------|------|
| `MatchHistoryDB` | 匹配历史记录 |
| `SwipeActionDB` | 滑动行为记录 |
| `UserPreferenceDB` | 用户偏好存储 |
| `MatchInteractionDB` | 匹配互动记录 |
| `ImplicitInferenceDB` | 隐性推断结果 |

### 对话相关模型

| 模型 | 用途 |
|------|------|
| `ConversationDB` | 对话历史 |
| `BehaviorEventDB` | 行为事件 |
| `ConversationSessionDB` | 对话会话 |
| `ChatMessageDB` | 实时聊天消息 |
| `AIPreCommunicationSessionDB` | AI 预沟通会话 |

### 画像与置信度模型

| 模型 | 用途 |
|------|------|
| `UserVectorProfileDB` | 用户向量画像 |
| `ProfileConfidenceDetailDB` | 置信度详情 |
| `ProfileInferenceRecordDB` | 推断记录 |

### 安全与认证模型

| 模型 | 用途 |
|------|------|
| `IdentityVerificationDB` | 身份认证 |
| `VerificationBadgeDB` | 认证徽章 |
| `SafetyZoneDB` | 安全区域 |
| `UserBlockDB` | 用户屏蔽 |
| `UserReportDB` | 用户举报 |

---

## 前端架构

### 组件层级

```
App.tsx (入口)
    ↓
HomePage.tsx (主页面)
    ├── ChatInterface.tsx (对话界面)
    │   ├── MessageList (消息列表)
    │   ├── GenerativeUI (动态组件渲染)
    │   │   ├── UserProfileCard
    │   │   ├── MatchCardList
    │   │   ├── ProfileQuestionCard
    │   │   ├── ChatInitiationCard
    │   │   └── ...
    │   └── InputArea (输入区域)
    ├── SwipeMatchPage.tsx (滑动匹配)
    ├── WhoLikesMePage.tsx (谁喜欢我)
    ├── ConfidenceManagementPage.tsx (置信度管理)
    ├── FaceVerificationPage.tsx (人脸认证)
    └── ChatRoom.tsx (聊天室)
```

### Generative UI 渲染流程

```
Agent 输出 [GENERATIVE_UI] 标签
    ↓
ChatInterface 解析标签
    ↓
提取 component_type 和 props
    ↓
mapComponentTypeToGenerativeCard 映射
    ↓
Suspense 懒加载对应组件
    ↓
渲染组件（传递 props）
```

### 懒加载优化

```tsx
// 大型组件懒加载
const MatchCard = lazy(() => import('./MatchCard'))
const MatchCardList = lazy(() => import('./generative-ui/MatchComponents'))
const UserProfileCard = lazy(() => import('./UserProfileCard'))

// Suspense 包裹 + 骨架屏 fallback
<Suspense fallback={<SkeletonComponents.matchCard />}>
  <UserProfileCard {...props} />
</Suspense>
```

### 国际化支持

**文件**: `frontend/src/locales/`

支持语言：
- 中文（zh）
- 英文（en）
- 日文（ja）
- 韩文（ko）

---

## API 层设计

### DeerFlow API（核心入口）

**文件**: `src/api/deerflow.py`

| 路由 | 用途 |
|------|------|
| `POST /api/deerflow/chat` | 发送消息（唯一入口） |
| `POST /api/deerflow/stream` | 流式发送消息（SSE） |
| `GET /api/deerflow/status` | DeerFlow 状态 |
| `POST /api/deerflow/memory/sync` | 同步用户画像到 Memory |
| `POST /api/deerflow/reset` | 重置 DeerFlow 客户端 |

### 其他 API 路由

| 文件 | 路由 | 用途 |
|------|------|------|
| `activities.py` | `/api/activities` | 活动推荐 |
| `ai_companion.py` | `/api/ai-companion` | AI 陪伴 |
| `digital_twin.py` | `/api/digital-twin` | 数字孪生 |
| `gift_integration.py` | `/api/gift` | 礼物集成 |
| `milestone_apis.py` | `/api/milestone` | 里程碑 |
| `payment.py` | `/api/payment` | 会员支付 |
| `relationship.py` | `/api/relationship` | 关系管理 |
| `video_date.py` | `/api/video-date` | 视频约会 |
| `identity_verification.py` | `/api/verification` | 身份认证 |

---

## 匹配系统设计

### 匹配执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     IntentAnalyzer                               │
│  分析用户意图：match_request / preference_update / inquiry       │
│  提取匹配条件：interests, age_range, location, gender            │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     QueryQualityChecker                          │
│  校验查询质量：是否清晰、是否完整                                 │
│  生成追问：缺失信息时生成 follow_up_questions                     │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     HerAdvisorService                            │
│  CognitiveBiasDetector: 识别认知偏差                              │
│  MatchAdvisor: 生成匹配建议                                       │
│  ProactiveSuggestionGenerator: 生成主动建议                       │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     MatchExecutor                                │
│  执行数据库查询                                                   │
│  应用硬约束过滤                                                   │
│  返回原始候选池                                                   │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     AdviceGenerator                              │
│  为每个匹配生成专业建议                                           │
│  生成风险提示                                                     │
│  生成回复消息                                                     │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     UIBuilder                                    │
│  构建 Generative UI                                              │
│  构建建议操作按钮                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Her 知识框架

```python
HER_KNOWLEDGE_FRAMEWORK = {
    "心理学": {
        "依恋理论": ["安全型", "焦虑型", "回避型", "混乱型"],
        "人格类型": ["外向/内向", "理性/感性", "控制/顺从"],
        "权力动态": ["控制型", "顺从型", "平等型", "竞争型"],
        "情感需求": ["需要被照顾", "需要被尊重", "需要被理解"]
    },
    "社会学": {
        "人生阶段": ["单身探索期", "稳定恋爱期", "婚姻准备期", "育儿期"],
        "价值观差异": ["家庭观念", "金钱观念", "事业观念"]
    },
    "人际关系学": {
        "沟通风格": ["直接型", "间接型", "情感型", "逻辑型"],
        "冲突处理": ["回避型", "竞争型", "妥协型", "合作型"]
    }
}
```

---

## 产品规划建议

### 当前代码成熟度评估

| 模块 | 成熟度 | 说明 |
|------|--------|------|
| **Agent Native 架构** | ⭐⭐⭐⭐ | 三层分离清晰，工具职责明确 |
| **对话式匹配** | ⭐⭐⭐⭐ | 流式输出 + Generative UI 完整实现 |
| **用户画像系统** | ⭐⭐⭐ | 双画像设计完善，行为推断待加强 |
| **匹配算法** | ⭐⭐⭐ | 硬约束过滤完整，软约束依赖 Agent |
| **前端交互** | ⭐⭐⭐⭐ | 懒加载 + 骨架屏 + 国际化完善 |
| **安全认证** | ⭐⭐⭐ | 人脸认证、身份认证基础完成 |
| **视频约会** | ⭐⭐ | 基础框架完成，功能待完善 |
| **AI 预沟通** | ⭐⭐ | 基础模型完成，流程待完善 |

### 未来 3-6 个月迭代方向

#### Phase 1: 基础能力完善（1-2 个月）

| 任务 | 优先级 | 说明 |
|------|--------|------|
| **向量匹配增强** | P0 | 引入 Qdrant，实现语义相似度匹配 |
| **行为推断强化** | P0 | 点击行为、搜索行为、匹配反馈 → DesireProfile |
| **置信度系统完善** | P1 | 各维度置信度计算 + 置信度可视化 |
| **视频约会流程完善** | P1 | 预约、提醒、报告生成完整流程 |
| **AI 预沟通上线** | P2 | AI 代表用户预沟通，生成摘要 |

#### Phase 2: 智能化提升（2-3 个月）

| 任务 | 优先级 | 说明 |
|------|--------|------|
| **认知偏差识别增强** | P0 | 更多心理学模型，更精准的偏差识别 |
| **关系进展追踪** | P1 | 里程碑追踪、关系健康度评估 |
| **主动推送系统** | P1 | 事件驱动推送（新人匹配、沉默提醒） |
| **智能约会策划** | P2 | 根据双方画像生成约会方案 |
| **关系教练上线** | P2 | 冲突调解、沟通建议 |

#### Phase 3: 生态扩展（3-6 个月）

| 任务 | 优先级 | 说明 |
|------|--------|------|
| **会员体系完善** | P1 | 分级会员、权益差异化 |
| **社交功能** | P2 | 用户动态、社交圈子 |
| **线下活动** | P2 | 活动匹配、活动报名 |
| **第三方认证集成** | P3 | 学历认证、职业认证第三方对接 |

### 技术优化建议

| 方向 | 建议 |
|------|------|
| **性能优化** | Memory 同步异步化（已实现）、用户画像缓存（已实现）、候选人批量查询优化（已实现） |
| **架构优化** | 保持 Agent Native 设计原则，避免回退到硬编码规则 |
| **测试覆盖** | 增加 Agent 行为测试、匹配流程测试、端到端测试 |
| **监控告警** | 关键路径耗时监控、Agent 决策日志、匹配成功率追踪 |

---

## 附录

### A. 文件结构索引

```
Her/
├── deerflow/
│   ├── backend/
│   │   ├── .deer-flow/
│   │   │   └── SOUL.md          # Agent System Prompt
│   │   └── packages/harness/deerflow/community/her_tools/
│   │       ├── __init__.py      # 工具注册
│   │       ├── match_tools.py   # 匹配工具
│   │       ├── profile_tools.py # 画像工具
│   │       ├── user_tools.py    # 用户工具
│   │       └── schemas.py       # 数据结构
│   └── extensions_config.json   # Skills 配置
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ChatInterface.tsx    # 对话界面
│       │   ├── generative-ui/       # Generative UI 组件
│       │   └── skeletons.tsx        # 骨架屏
│       ├── pages/
│       │   ├── HomePage.tsx         # 主页面
│       │   ├── SwipeMatchPage.tsx   # 滑动匹配
│       │   └── ChatRoom.tsx         # 聊天室
│       └── api/
│           └── deerflowClient.ts    # DeerFlow API 客户端
├── src/
│   ├── api/
│   │   ├── deerflow.py          # DeerFlow API
│   │   └── matching.py          # 匹配 API
│   ├── services/
│   │   ├── her_advisor_service.py       # Her 顾问服务
│   │   ├── conversation_match_service.py # 对话匹配服务
│   │   └ user_profile_service.py        # 用户画像服务
│   ├── agent/
│   │   └ skills/                # 30+ Skills
│   │   └── deerflow_client.py   # DeerFlow 客户端封装
│   └── db/
│       └ models/                # 数据模型（15+ 文件）
│       └ database.py            # 数据库连接
└── tests/
    ├── eval/                    # 评估测试
    └── agent/                   # Agent 测试
```

### B. 关键日志追踪点

| 日志标签 | 用途 |
|---------|------|
| `[DEERFLOW_TRACE]` | DeerFlow API 调用追踪 |
| `[HER_SERVICE_TRACE]` | Her Service 降级处理追踪 |
| `[her_find_candidates]` | 候选人查询耗时 |
| `[IntentAnalyzer]` | 意图分析结果 |
| `[QueryQualityChecker]` | 查询质量校验 |
| `[Memory同步]` | 用户画像同步到 DeerFlow |

---

> **文档维护说明**
> 
> 本文档基于代码扫描生成，不依赖现有 MD 文件。
> 更新日期：2026-04-19
> 
> 维护原则：
> 1. 代码变更后同步更新此文档
> 2. 保持架构描述与实际代码一致
> 3. 产品规划每季度更新