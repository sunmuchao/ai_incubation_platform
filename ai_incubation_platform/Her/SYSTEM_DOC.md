# Her 系统文档

> **AI Native 婚恋匹配平台** - Agent Native 架构实践

---

## 目录

1. [愿景与背景](#愿景与背景)
2. [系统架构](#系统架构)
3. [核心功能模块](#核心功能模块)
4. [技术栈概览](#技术栈概览)
5. [数据模型设计](#数据模型设计)
6. [API 层设计](#api-层设计)
7. [前端架构](#前端架构)
8. [产品规划建议](#产品规划建议)

---

## 愿景与背景

### 核心愿景

**Her** 致力于成为 **AI Native 婚恋匹配平台**，以 AI Agent 作为核心决策引擎，实现从"被动工具"到"主动顾问"的范式跃迁。

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
│  │ (对话入口)   │  │ (主页面)    │  │ (滑动匹配)   │  │ (动态组件)       │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────────────────┐
│                           后端层 (FastAPI + SQLAlchemy)                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  REST API 层     │  │  Service 层      │  │  Skills Registry         │  │
│  │  (45+ 路由文件)  │  │  (70+ 服务文件) │  │  (30+ Skills)             │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓ Agent 调用
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DeerFlow Agent Runtime (LangGraph)                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Lead Agent      │  │  SOUL.md         │  │  her_tools (Tools Layer) │  │
│  │  (决策引擎)      │  │  (System Prompt) │  │  (纯数据查询)            │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓ 数据访问
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据层 (SQLite/PostgreSQL + Redis)                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  UserDB          │  │  Matching Models │  │  Profile Models          │  │
│  │  (125 字段)      │  │  (匹配历史)      │  │  (画像数据)              │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Native 三层分离架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     System Prompt Layer                          │
│  所有决策逻辑通过 Prompt 表达                                     │
│  - SOUL.md: Her 角色定义、决策规则、输出规范                       │
│  - 不硬编码 if-else，用自然语言描述规则                           │
└─────────────────────────────────────────────────────────────────┘
                           ↓ 调用
┌─────────────────────────────────────────────────────────────────┐
│                     Tools Layer (Pure Execution)                 │
│  her_tools 只做数据查询和执行，不含业务逻辑                        │
│  - her_find_matches: 查询候选人列表                               │
│  - her_analyze_compatibility: 查询双方画像                        │
│  - her_get_icebreaker: 查询破冰建议数据                           │
│  - 返回原始数据（JSON），Agent 自己解读                           │
└─────────────────────────────────────────────────────────────────┘
                           ↓ 依赖
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer                                   │
│  数据存储，无业务逻辑                                             │
│  - UserDB: 用户核心信息（125 字段）                               │
│  - Profile Models: SelfProfile + DesireProfile                   │
│  - Matching Models: SwipeActionDB, MatchHistoryDB                │
└─────────────────────────────────────────────────────────────────┘
```

### 执行循环

```
用户消息 → DeerFlow Agent 思考(LLM) → 选择 her_tools → 执行工具(纯数据)
                                                              ↓
                           Agent 再思考(LLM) ← 解读数据决定下一步
                                                              ↓
                           输出回复 + Generative UI → 完成
```

---

## 核心功能模块

### 1. 智能匹配系统

**定位**：AI Native 对话式匹配，替代传统表单筛选

**核心组件**：
- `ConversationMatchService`: 意图分析 + 匹配编排
- `HerAdvisorService`: 认知偏差识别 + 匹配建议
- `her_find_matches`: 数据查询工具

**流程设计**：

```
用户消息 → IntentAnalyzer (意图理解)
         → UserProfileService (获取画像)
         → CognitiveBiasDetector (偏差识别)
         → MatchExecutor (执行匹配)
         → AdviceGenerator (生成建议)
         → UIBuilder (构建 Generative UI)
         → 返回响应
```

**关键特性**：
- 自然语言表达偏好："我想找个喜欢户外运动的女生"
- 自动提取条件：interests=["户外运动"], gender="female"
- 认知偏差识别：用户想要的 ≠ 用户适合的
- 每条匹配都有 MatchAdvice（建议 + 风险提示）

### 2. Her 顾问服务

**定位**：拥有 20 年经验的专业婚恋顾问

**核心能力**：

| 能力 | 实现方式 | 效果 |
|------|---------|------|
| **认知偏差识别** | LLM 自主判断（不硬编码规则） | 发现用户想要的和适合的差异 |
| **匹配建议生成** | 四层匹配架构 | 每条匹配有专业建议 |
| **主动建议输出** | 搜索时主动提醒 | 帮助用户调整期待 |

**Her 知识框架**：
- 心理学：依恋理论、人格类型、权力动态、情感需求
- 社会学：人生阶段、价值观差异、文化背景
- 人际关系学：沟通风格、冲突处理、相处节奏

### 3. 用户画像系统

**双画像设计**：

| 画像类型 | 描述 | 数据来源 |
|---------|------|---------|
| **SelfProfile** | 这个人是什么样的 | 注册表单 + QuickStart + 行为推断 |
| **DesireProfile** | 这个人想要什么 | 用户表达 + 搜索行为 + 点击模式 |

**画像维度**（QuickStart 收集）：

```
===== 注册表单基础字段 =====
- name, age, gender, location (必填)

===== QuickStart 属性字段 =====
- height, education, occupation, income, housing, has_car

===== 一票否决维度（最高优先级）=====
- want_children (生育意愿)
- spending_style (消费观念)

===== 核心价值观维度 =====
- family_importance (家庭重要度)
- work_life_balance (工作生活平衡)

===== 迁移能力维度 =====
- migration_willingness (迁移意愿)
- accept_remote (异地接受度)

===== 生活方式维度 =====
- sleep_type (作息类型)
```

**置信度系统**：
- 每个维度有独立置信度
- 主动填写 > 行为推断 > 默认值
- 置信度低于阈值时触发信息收集

### 4. Generative UI 系统

**定位**：界面由 AI 动态生成，而非固定布局

**前后端映射 Schema**：

| backend_type | frontend_card | 描述 |
|--------------|---------------|------|
| `MatchCardList` | `match` | 匹配结果列表 |
| `UserProfileCard` | `user_profile` | 用户详情卡片 |
| `ProfileQuestionCard` | `profile_question` | 画像问题卡片 |
| `QuickStartCard` | `quick_start` | 快速入门问题 |
| `PreCommunicationPanel` | `precommunication` | AI 预沟通会话列表 |
| `DatePlanCard` | `feature` | 约会方案卡片 |
| `CompatibilityChart` | `compatibility` | 兼容性分析图表 |
| `CapabilityCard` | `feature` | 能力介绍卡片 |
| `IcebreakerCard` | `feature` | 破冰建议卡片 |

**设计原则**：
- 前端组件只负责渲染，不包含业务逻辑
- 后端通过 `generative_ui_schema.py` 定义输出格式
- 新增组件必须在前后端同步注册

### 5. AI 预沟通系统

**定位**：Agent 代替用户进行初步沟通

**流程**：
1. 用户对候选人感兴趣 → 创建预沟通会话
2. Her Agent 与对方 Agent 进行多轮对话
3. 收集关键信息：性格、兴趣、沟通风格
4. 用户查看对话摘要 → 决定是否发起真实聊天

**数据模型**：
- `AIPreCommunicationSessionDB`: 会话状态管理
- `AIPreCommunicationMessageDB`: 对话消息存储

### 6. 安全风控系统

**核心组件**：
- `SafetyGuardianSkill`: 紧急求助、位置安全监测
- `UserReportDB`: 用户举报机制
- `UserBlockDB`: 黑名单系统
- `SafetyZoneDB`: 安全区域设置

**分级响应机制**：
- L1（轻微）：AI 提醒
- L2（中等）：人工介入
- L3（严重）：紧急联系通知

### 7. 会员订阅系统

**功能模块**：
- 会员等级管理（普通/VIP/至尊）
- 功能使用追踪
- 支付集成（微信支付/支付宝）

**数据模型**：
- `UserMembershipDB`: 会员状态
- `MembershipOrderDB`: 订单记录
- `MemberFeatureUsageDB`: 功能使用统计

---

## 技术栈概览

### 后端技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| **框架** | FastAPI 0.104+ | 高性能异步框架 |
| **数据库** | SQLAlchemy 2.0+ | ORM，支持 SQLite/PostgreSQL |
| **缓存** | Redis 5.0+ | 分布式缓存、会话管理 |
| **AI Runtime** | DeerFlow (LangGraph) | Agent 执行引擎 |
| **LLM** | 火山引擎豆包/通义千问 | 多模型支持 |
| **认证** | JWT (python-jose) | Token 认证 |
| **推送** | 极光推送 (JPush) | 移动端通知 |
| **地图** | 高德地图 API | 位置服务 |

### 前端技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| **框架** | React 18 | 函数式组件 + Hooks |
| **语言** | TypeScript | 类型安全 |
| **UI 库** | Ant Design 5.x | 企业级组件库 |
| **国际化** | i18next | 中英日韩四语言 |
| **状态管理** | useState/useContext | 轻量级方案 |
| **懒加载** | React.lazy + Suspense | 性能优化 |

### Agent Runtime (DeerFlow)

| 类别 | 技术 | 说明 |
|------|------|------|
| **框架** | LangGraph | Agent 工作流编排 |
| **System Prompt** | SOUL.md | Her 角色定义 |
| **Tools** | her_tools | 纯数据查询工具集 |
| **Memory** | LangGraph Memory | 对话上下文持久化 |

---

## 数据模型设计

### 数据库表概览

系统共设计 **45+ 数据模型**，按领域分类：

| 领域 | 模型数量 | 核心模型 |
|------|---------|---------|
| 用户核心 | 1 | UserDB (125 字段) |
| 匹配领域 | 7 | MatchHistoryDB, SwipeActionDB, UserPreferenceDB |
| 对话领域 | 4 | ConversationDB, BehaviorEventDB |
| 实时聊天 | 2 | ChatMessageDB, ChatConversationDB |
| 照片管理 | 1 | PhotoDB |
| 认证验证 | 4 | IdentityVerificationDB, VerificationBadgeDB |
| 会员订阅 | 3 | UserMembershipDB, MembershipOrderDB |
| 视频约会 | 6 | VideoCallDB, VideoDateDB, IcebreakerQuestionDB |
| AI 集成 | 5 | AICompanionSessionDB, SemanticAnalysisDB, LLMMetricsDB |
| 安全领域 | 4 | SafetyZoneDB, TrustedContactDB, UserBlockDB |
| 用户画像 | 5 | UserVectorProfileDB, ProfileInferenceRecordDB |
| 关系进展 | 2 | RelationshipProgressDB, SavedLocationDB |

### UserDB 核心字段 (125 字段)

```python
# ===== 基础字段 =====
id, username, name, email, password_hash, age, gender, location, interests, values, bio, avatar_url

# ===== 注册对话收集的用户画像字段 =====
relationship_goal, personality, ideal_type, lifestyle, deal_breakers

# ===== QuickStart 可选字段 =====
education, occupation, income, height, has_car, housing

# ===== 一票否决维度 =====
want_children, spending_style

# ===== 核心价值观维度 =====
family_importance, work_life_balance

# ===== 迁移能力维度 =====
migration_willingness, accept_remote

# ===== 生活方式维度 =====
sleep_type

# ===== 偏好设置 =====
preferred_age_min, preferred_age_max, preferred_location, preferred_gender, sexual_orientation

# ===== 动态画像 =====
self_profile_json, desire_profile_json, profile_confidence, profile_completeness

# ===== 手机号/微信登录 =====
phone, wechat_openid, wechat_unionid
```

---

## API 层设计

### 路由自动注册机制

系统采用**自动扫描注册**替代手动导入：

```python
# 扫描 api/*.py 所有文件
# 提取所有以 'router' 开头的变量
# 自动注册到 FastAPI 应用
```

**路由文件数量**：45+ 个

### API 分类

| 分类 | 路径前缀 | 功能 |
|------|---------|------|
| **核心** | `/api/users`, `/api/matching`, `/api/relationship` | 用户、匹配、关系 |
| **社交** | `/api/chat`, `/api/photos`, `/api/activities` | 聊天、照片、活动 |
| **会员** | `/api/membership`, `/api/payment` | 会员、支付 |
| **安全** | `/api/identity`, `/api/verification` | 认证、验证 |
| **AI 功能** | `/api/ai-companion`, `/api/skills` | AI 陪伴、技能 |
| **里程碑** | `/api/milestones`, `/api/date-suggestions` | 关系里程碑 |
| **生活集成** | `/api/autonomous-dating`, `/api/tribe` | 自主约会、部落 |
| **AI Native** | `/api/deerflow`, `/api/autonomous` | DeerFlow Agent |

### 核心 API 端点示例

**匹配相关**：
- `POST /api/matching/conversation-match`: 对话式匹配
- `GET /api/matching/recommendations`: 获取推荐
- `POST /api/matching/swipe`: 滑动匹配

**用户相关**：
- `POST /api/users/register`: 用户注册
- `POST /api/users/login`: 登录
- `GET /api/users/profile`: 获取画像

**AI 相关**：
- `POST /api/deerflow/chat`: DeerFlow Agent 对话
- `POST /api/skills/execute`: 执行 Skill

---

## 前端架构

### 组件结构

```
frontend/src/
├── components/
│   ├── ChatInterface.tsx       # 对话式交互核心
│   ├── HomePage.tsx            # AI Native 主页面
│   ├── SwipeMatchContainer.tsx # 滑动匹配容器
│   ├── MatchCard.tsx           # 匹配卡片
│   ├── ProfileQuestionCard.tsx # 画像问题卡片
│   ├── generative-ui/          # Generative UI 组件
│   │   ├── MatchComponents.tsx
│   │   ├── ChatComponents.tsx
│   │   ├── EmotionComponents.tsx
│   │   ├── RelationshipComponents.tsx
│   │   └── ...
├── pages/
│   ├── LoginPage.tsx
│   ├── SwipeMatchPage.tsx
│   ├── WhoLikesMePage.tsx
│   ├── ConfidenceManagementPage.tsx
│   └── ...
├── api/
│   ├── deerflowClient.ts       # DeerFlow Agent 客户端
│   ├── profileApi.ts           # 画像 API
│   ├── chatApi.ts              # 聊天 API
│   └── ...
├── types/
│   ├── generativeUI.ts         # Generative UI Schema
│   ├── index.ts                # 类型定义
│   └── ...
├── locales/
│   ├── zh/                     # 中文
│   ├── en/                     # 英文
│   ├── ja/                     # 日文
│   └── ko/                     # 韩文
```

### AI Native 设计原则

1. **对话优先 (Chat-first)**：
   - 无传统菜单导航
   - 所有功能通过对话触发
   - ChatInterface 是唯一交互入口

2. **Generative UI**：
   - AI 动态决定渲染什么组件
   - 前端只负责渲染，不包含业务逻辑
   - 新增组件需前后端同步注册

3. **AI 自主性**：
   - Agent 主动感知缺失信息
   - Agent 主动推送建议
   - 高置信度时自主执行

### 性能优化策略

- **懒加载**：React.lazy + Suspense 包裹大型组件
- **骨架屏**：SkeletonComponents 提供加载占位
- **消息限制**：MAX_MESSAGES = 50 防止内存泄漏
- **并行请求**：useCallback + useMemo 缓存渲染结果

---

## 产品规划建议

### 当前成熟度评估

| 维度 | 评估 | 说明 |
|------|------|------|
| **AI Native 成熟度** | L3 (Agent) | Agent 自主规划执行，高置信度自主行动 |
| **核心功能完整度** | 85% | 匹配、画像、聊天、会员已完整 |
| **AI 顾问能力** | 70% | 认知偏差识别已实现，需更多知识库 |
| **Generative UI** | 60% | 核心组件已实现，需扩展更多场景 |
| **数据基础设施** | 90% | 画像系统、置信度系统完善 |

### 未来 3-6 个月迭代方向

#### 短期（1-2 个月）：用户体验优化

| 目标 | 具体措施 | 优先级 |
|------|---------|--------|
| **信息收集体验优化** | QuickStart 流程平滑化，减少打断感 | P0 |
| **匹配结果呈现优化** | MatchAdvice 可视化增强，添加对比图表 | P0 |
| **破冰建议深化** | 从兴趣扩展到价值观、性格匹配话题 | P1 |
| **移动端适配** | iOS/Android 原生体验优化 | P1 |

#### 中期（3-4 个月）：AI 能力增强

| 目标 | 具体措施 | 优先级 |
|------|---------|--------|
| **Her 知识库扩展** | 添加婚恋案例库，增强推理能力 | P0 |
| **情感识别增强** | 对话中识别情绪变化，调整策略 | P0 |
| **关系经营能力** | 添加关系阶段追踪、冲突预警 | P1 |
| **AI 视频面诊** | 视频约会实时辅助（话题提示） | P2 |

#### 长期（5-6 个月）：生态扩展

| 目标 | 具体措施 | 优先级 |
|------|---------|--------|
| **部落匹配** | 基于社交圈、兴趣部落匹配 | P1 |
| **数字小家** | 虚拟共同空间、情感纪念册 | P2 |
| **见家长模拟** | AI 模拟家长对话，准备见面 | P2 |
| **第三方服务集成** | 餐厅预订、电影票预订闭环 | P2 |

### 技术优化建议

| 领域 | 建议 | 优先级 |
|------|------|--------|
| **性能优化** | LLM 调用并行化（已部分实现），添加缓存层 | P0 |
| **可观测性** | 完善 LLM 调用追踪、匹配效果追踪 | P0 |
| **安全加固** | 添加敏感词过滤、隐私数据脱敏 | P0 |
| **测试覆盖** | 补充 AI 顾问单元测试、匹配效果评估测试 | P1 |
| **文档完善** | 补充 API 文档、部署文档 | P2 |

### 技术债务清理

| 项目 | 说明 | 建议 |
|------|------|------|
| **废弃 Skill 清理** | IntentRouterSkill 等已废弃 | 移除代码，更新文档 |
| **路由文件整合** | 部分 API 文件职责重叠 | 合并为领域模块 |
| **前端组件复用** | 部分组件重复逻辑 | 抽取公共组件 |

---

## 附录

### A. 系统版本历史

| 版本 | 日期 | 核心更新 |
|------|------|---------|
| v1.30.0 | 2025-04 | Agent Native 架构重构，Her 顾问服务上线 |
| v1.28.0 | 2025-04 | Generative UI 系统完善 |
| v1.23.0 | 2025-03 | 性能优化仪表板、缓存预热 |
| v1.20.0 | 2025-03 | AI Native 转型：对话式匹配 |
| v1.0.0 | 2025-01 | 项目初始化 |

### B. 关键配置说明

参见 `.env.example` 文件，核心配置：

- `LLM_ENABLED`: LLM 核心引擎开关
- `LLM_PROVIDER`: 支持 volces/qwen/glm/openai
- `DATABASE_URL`: 支持 SQLite/PostgreSQL
- `REDIS_URL`: 缓存服务地址
- `AMAP_API_KEY`: 高德地图服务

### C. 部署架构

推荐生产环境：
- 后端：Gunicorn + Uvicorn 多进程
- 数据库：PostgreSQL（主库）+ Redis（缓存）
- LLM：火山引擎豆包（国内推荐）
- 推送：极光推送
- 地图：高德地图 API

---

**文档版本**: v1.0.0  
**生成日期**: 2026-04-15  
**生成方式**: Claude Code 自动扫描代码库生成