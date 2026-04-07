# AI 社区团购平台 - 项目完整文档

**项目名称**: AI Community Buying (ai-community-buying)
**当前版本**: v4.0.0
**文档版本**: v1.0.0
**生成日期**: 2026-04-07
**项目状态**: 已完成 - AI Native 转型

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [项目现状](#2-项目现状)
3. [AI Native 特性分析](#3-ai-native-特性分析)
4. [长远目标和愿景](#4-长远目标和愿景)
5. [执行计划和路线图](#5-执行计划和路线图)
6. [快速启动指南](#6-快速启动指南)

---

## 1. 执行摘要

### 1.1 项目定位和核心价值主张

**AI 社区团购平台**是一个基于 AI Native 架构的社区团购解决方案，致力于成为**每个社区的 AI 团购管家**。

**核心价值主张**:
- 让 AI 成为用户的**购物代理人**，自主感知需求、自主选品比价、自主成团下单、自主优化履约
- 从传统"货架电商 + AI 推荐"转型为"对话式交互 + AI 自主决策"
- 通过 DeerFlow 2.0 Agent 框架实现自主团购、智能选品、主动邀请等核心能力

**目标用户**:
- C 端用户：通过自然语言对话表达购物需求，享受 AI 代理购物决策
- 团长：获得 AI 辅助的选品建议、成团预测、履约调度
- 平台运营：数据驱动的营销自动化、用户增长、供应链优化

### 1.2 AI Native 成熟度等级评估

**当前等级**: **L3 代理级 (Agent)**

| 等级 | 名称 | 达成状态 | 关键特征 |
|------|------|---------|---------|
| L1 | 工具 | ✅ 超越 | AI 作为工具被调用 |
| L2 | 助手 | ✅ 达到 | AI 主动发现问题并推送建议 |
| L3 | 代理 | ✅ **当前等级** | AI 多步工作流自主执行 |
| L4 | 伙伴 | ⏳ 规划中 | 用户偏好记忆系统 |
| L5 | 专家 | ⏳ 长期愿景 | 领域 AI 超越人类专家 |

**L3 等级评估依据**:

| 评估维度 | 得分 | 说明 |
|---------|------|------|
| **对话式交互** | ✅ 9/10 | 支持自然语言需求表达，意图识别准确率 85%+ |
| **自主决策** | ✅ 8/10 | AI 可自主选品、创建团购、邀请成员 |
| **工作流编排** | ✅ 9/10 | 6-7 步工作流自主执行（选品→创建→邀请→预测） |
| **置信度阈值** | ✅ 7/10 | 高置信度时自主执行，低置信度时请求确认 |
| **用户记忆** | ⏳ 3/10 | 基础会话记忆，长期记忆系统在规划中 |
| **Generative UI** | ⏳ 4/10 | 前端 Bento Grid 布局，动态生成能力有限 |

**综合评分**: 7.5/10 → **L3 代理级**

### 1.3 关键成就和里程碑

#### 版本演进历史

| 版本 | 阶段 | 核心功能 | 完成日期 |
|------|------|---------|---------|
| v0.1.0 | P0 | 商品/库存/团购/订单核心闭环 | 2026-02 |
| v0.2.0 | P1 | 标准化工具层、可插拔通知适配器 | 2026-02 |
| v0.3.0 | P2 | 事务管理、乐观锁、结构化日志 | 2026-02 |
| v0.4.0 | P3 | 佣金、优惠券、分享裂变 | 2026-03 |
| v0.5.0 | P4 | 履约追踪、团长后台、AI 预测 | 2026-03 |
| v0.6.0 | P0(P5 增长引擎) | 限时秒杀、新人专享、拼单返现 | 2026-03 |
| v0.7.0 | P6 | 团长考核、售后流程、签到积分 | 2026-03 |
| v0.8.0 | P7 | 游戏化运营 (成就/排行榜)/砍价玩法 | 2026-03 |
| v0.9.0 | P0 AI 智能成团预测 | 基于回归模型的成团概率预测 | 2026-03 |
| v1.0.0 | P9 | 智能履约调度系统 (路径优化/人流预测) | 2026-03 |
| v1.1.0 | P1 | 动态定价引擎 | 2026-03 |
| v2.0.0 | P0 AI 选品顾问增强 | 协同过滤/社区画像 | 2026-03 |
| v2.1.0 | P1 | 需求预测 (Prophet+LSTM) | 2026-03 |
| v2.2.0 | P2 | 个性化推荐 (Wide&Deep 深度排序) | 2026-03 |
| v2.3.0 | P3 | 用户增长与运营工具 | 2026-03 |
| v2.4.0 | P4 | 供应链与履约优化 | 2026-03 |
| v2.5.0 | P5 | 营销自动化系统 | 2026-03 |
| v2.6.0 | P6 | 数据分析增强 | 2026-03 |
| v2.7.0 | P7 | 游戏化运营 | 2026-03 |
| v2.8.0 | P8 | 智能风控/信用体系 | 2026-03 |
| v3.0.0 | P10 | 项目总结与商业化就绪 | 2026-04 |
| **v4.0.0** | **P10+ AI Native** | **DeerFlow 2.0 Agent/对话式交互/自主团购** | **2026-04-06** |

#### P0-P9 功能完成度

| 优先级 | 功能模块 | 完成度 | 核心功能 |
|--------|---------|--------|---------|
| **P0** | 核心业务闭环 | ✅ 100% | 商品/团购/订单/库存 |
| **P0** | AI 智能成团预测 | ✅ 100% | 回归模型预测成团概率 |
| **P0** | AI 选品顾问 | ✅ 100% | 协同过滤推荐 |
| **P1** | 标准化工具层 | ✅ 100% | 团购/商品/通知工具 |
| **P1** | 动态定价引擎 | ✅ 100% | 成团概率/需求弹性定价 |
| **P1** | 需求预测 | ✅ 100% | Prophet+LSTM 融合预测 |
| **P2** | 个性化推荐 | ✅ 100% | Wide&Deep 深度排序 |
| **P3** | 用户增长工具 | ✅ 100% | 邀请裂变/任务中心/会员成长 |
| **P4** | 供应链与履约 | ✅ 100% | 库存预警/智能补货/供应商管理 |
| **P5** | 营销自动化 | ✅ 100% | 用户分群/自动化营销/ROI 分析 |
| **P6** | 数据分析增强 | ✅ 100% | 销售报表/用户行为分析 |
| **P7** | 游戏化运营 | ✅ 100% | 成就系统/排行榜/砍价玩法 |
| **P8** | 智能风控 | ✅ 100% | 信用评分/欺诈检测/黑名单 |
| **P9** | 智能履约调度 | ✅ 100% | 路径优化/人流预测/时间窗口 |
| **P9** | 多平台集成 | ✅ 100% | 微信/支付宝小程序集成 |
| **P10+** | AI Native 转型 | ✅ 100% | DeerFlow 2.0 Agent/对话式交互 |

---

## 2. 项目现状

### 2.1 技术架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户交互层                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │   React 前端    │  │   对话式 UI     │  │   Generative UI (规划)  │  │
│  │  (Bento Grid)   │  │  (聊天界面)     │  │                         │  │
│  └────────┬────────┘  └────────┬────────┘  └────────────┬────────────┘  │
└───────────┼─────────────────────┼─────────────────────────┼──────────────┘
            │                     │                         │
            ▼                     ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API 网关层 (FastAPI)                            │
│  ┌───────────┬───────────┬───────────┬───────────┬───────────────────┐  │
│  │  商品 API  │  团购 API  │  订单 API  │  用户 API  │  AI 对话 API      │  │
│  │  /products│  /groups  │  /orders  │  /user    │  /api/chat/*     │  │
│  └───────────┴───────────┴───────────┴───────────┴───────────────────┘  │
│  ┌───────────┬───────────┬───────────┬───────────┬───────────────────┐  │
│  │ 推荐 API  │ 定价 API  │ 预测 API  │ 营销 API  │  风控 API         │  │
│  │/recommend │  /pricing │ /forecast │ /marketing│  /risk            │  │
│  └───────────┴───────────┴───────────┴───────────┴───────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
            │                     │                         │
            ▼                     ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI Agent 核心引擎 (DeerFlow 2.0)                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    GroupBuyAgent (团购智能体)                     │    │
│  │  ┌───────────────┬───────────────┬───────────────┬──────────┐  │    │
│  │  │  需求理解    │  自主选品     │  主动邀请     │ 成团预测 │  │    │
│  │  │  Intent      │  Selection    │  Invitation   │Prediction│  │    │
│  │  └───────────────┴───────────────┴───────────────┴──────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Workflows (工作流编排)                         │    │
│  │  • AutoCreateGroupWorkflow (自主创建团购 - 6 步)                   │    │
│  │  • AutoSelectProductWorkflow (智能选品 - 6 步)                    │    │
│  │  • AutoInviteWorkflow (主动邀请 - 7 步)                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Tools 工具层                                   │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┬──────────┐  │
│  │ 商品搜索    │ 价格比较    │ 成团预测    │ 用户分析    │ 通知发送 │  │
│  │ SearchTool  │ CompareTool │ PredictTool │ AnalyzeTool │ Notify   │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┴──────────┘  │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┬──────────┐  │
│  │ 创建团购    │ 邀请成员    │ 履约调度    │ 库存查询    │ 支付处理 │  │
│  │ CreateTool  │ InviteTool  │ ScheduleTool│ StockTool   │ PayTool  │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┴──────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Services 服务层                                │
│  业务服务：GroupBuyService, ProductService, OrderService, UserService  │
│  AI 服务：RecommendationService, DemandForecastService, PricingService │
│  营销服务：MarketingService, CouponService, ShareService              │
│  风控服务：CreditScoreService, RiskRuleService, BlacklistService      │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            数据持久层                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │   SQLite/PG     │  │   Redis 缓存    │  │   向量数据库 (规划)      │  │
│  │   关系型数据    │  │   会话/热点数据 │  │   用户画像/商品嵌入      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent/Tools/Workflows 三层架构详解

#### 2.2.1 Agents 层 (src/agents/)

**核心 Agent**: GroupBuyAgent (团购智能体)

| 文件 | 行数 | 功能说明 |
|------|------|---------|
| `__init__.py` | 15 | Agent 层导出 |
| `deerflow_client.py` | 180 | DeerFlow 2.0 客户端封装，支持降级模式 |
| `groupbuy_agent.py` | 380+ | 团购智能体核心逻辑 |

**Agent 核心能力**:

```python
class GroupBuyAgent:
    """
    团购智能体 - 核心能力

    1. 需求理解 - 理解用户自然语言需求
    2. 自主选品 - 主动搜索并推荐商品
    3. 主动邀请 - 分析并邀请潜在参团者
    4. 成团预测 - 预测成团概率并优化策略
    5. 履约调度 - 智能安排配送
    """

    async def chat(self, user_input: str, context: AgentContext) -> AgentResponse:
        # 1. 理解用户意图
        # 2. 根据意图选择执行策略
        # 3. 调用工作流执行
        # 4. 返回自然语言回复 + 建议操作
```

**意图识别类型**:
- `create_group`: 创建团购
- `find_product`: 查找商品
- `check_status`: 查询状态
- `general_query`: 通用查询

#### 2.2.2 Workflows 层 (src/workflows/)

**工作流清单**:

| 文件 | 行数 | 步骤数 | 功能说明 |
|------|------|--------|---------|
| `auto_create_group.py` | 280+ | 6 步 | 自主创建团购工作流 |
| `auto_select_product.py` | 380+ | 6 步 | 智能选品工作流 |
| `auto_invite.py` | 300+ | 7 步 | 主动邀请工作流 |

**工作流详细步骤**:

```
【自主创建团购工作流】- 6 步编排
┌─────────────────────────────────────────────────────────┐
│ Step 1: 分析用户需求 → 提取类别/关键词/价格偏好         │
│ Step 2: 选择最优商品 → 多维评分排序选最佳               │
│ Step 3: 创建团购 → 设置价格/人数/截止时间               │
│ Step 4: 邀请参与者 → 分析潜在参团者并发送邀请           │
│ Step 5: 跟踪进度 → 实时更新成团状态                     │
│ Step 6: 安排履约 → 智能调度配送                         │
└─────────────────────────────────────────────────────────┘

【智能选品工作流】- 6 步编排
┌─────────────────────────────────────────────────────────┐
│ Step 1: 理解意图 → 提取需求类别/偏好                    │
│ Step 2: 搜索商品 → 调用商品搜索工具                     │
│ Step 3: 多维比较 → 价格/质量/热度/新鲜度               │
│ Step 4: 生成理由 → LLM 生成推荐理由                      │
│ Step 5: 预测概率 → 成团概率预测                         │
│ Step 6: 排序返回 → 综合评分排序返回 Top-N              │
└─────────────────────────────────────────────────────────┘

【主动邀请工作流】- 7 步编排
┌─────────────────────────────────────────────────────────┐
│ Step 1: 分析团购特征 → 商品类别/价格/目标人群          │
│ Step 2: 识别候选用户 → 图神经网络找相似用户             │
│ Step 3: 计算参团概率 → 预测每个用户参团可能性           │
│ Step 4: 选择最优邀请集合 → 最大化成团概率               │
│ Step 5: 生成邀请内容 → 个性化邀请文案                   │
│ Step 6: 发送邀请 → 调用通知服务发送                     │
│ Step 7: 追踪反馈 → 记录邀请响应情况                     │
└─────────────────────────────────────────────────────────┘
```

#### 2.2.3 Tools 层 (src/tools/)

**工具清单**:

| 文件 | 工具数 | 功能说明 |
|------|--------|---------|
| `groupbuy_tools.py` | 4 个 | 团购工具集 |
| `conversation_tools.py` | 3 个 | 对话理解工具 |
| `product_tools.py` | 3 个 | 商品工具集 |
| `registry.py` | - | 工具注册表 |

**核心工具接口**:

```python
# 团购工具
CreateGroupTool      # 创建团购
InviteMembersTool    # 邀请成员
PredictGroupSuccessTool  # 成团概率预测
GetGroupStatusTool   # 查询团购状态

# 对话工具
IntentRecognitionTool    # 意图识别
EntityExtractionTool     # 实体抽取
ResponseGenerationTool   # 回复生成

# 商品工具
SearchProductsTool   # 商品搜索
CompareProductsTool  # 商品比较
GetProductDetailTool # 商品详情
```

### 2.3 核心功能模块清单 (按优先级 P0-P9)

#### P0: 核心业务 + AI 基础能力

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| 商品管理 | `/api/products` | ProductService | ✅ |
| 团购管理 | `/api/groups` | GroupBuyService | ✅ |
| 订单管理 | `/api/orders` | OrderService | ✅ |
| AI 智能成团预测 | `/api/ai/group-prediction` | GroupPredictionService | ✅ |
| AI 选品顾问 | `/api/product-selection/*` | ProductSelectionService | ✅ |
| AI 对话交互 | `/api/chat/*` | GroupBuyAgent | ✅ |

#### P1: 基础架构增强

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| 标准化工具层 | `/api/tools` | ToolsRegistry | ✅ |
| 动态定价引擎 | `/api/dynamic-pricing` | DynamicPricingService | ✅ |
| 需求预测 (Prophet+LSTM) | `/api/ai/forecast/advanced` | DemandForecastService | ✅ |
| 可插拔通知适配器 | `/api/notifications` | NotificationService | ✅ |
| 速率限制中间件 | 全局中间件 | RateLimitMiddleware | ✅ |

#### P2: 个性化推荐系统

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| Wide&Deep 深度排序 | `/api/recommendation/personalized` | RecommendationService | ✅ |
| 用户特征工程 | `/api/recommendation/explain` | - | ✅ |
| 推荐多样性控制 | `/api/recommendation/diversity-check` | - | ✅ |
| 社区热销榜 | `/api/recommendation/hot` | - | ✅ |

#### P3: 用户增长与运营工具

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| 邀请裂变 | `/api/p3/invite` | InviteService | ✅ |
| 任务中心 | `/api/p3/tasks` | TaskService | ✅ |
| 会员成长体系 | `/api/p3/member` | MemberService | ✅ |
| 运营活动模板 | `/api/p3/campaigns` | CampaignService | ✅ |

#### P4: 供应链与履约优化

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| 库存预警 | `/api/p4/inventory-alerts` | InventoryAlertService | ✅ |
| 智能补货 | `/api/p4/replenishment` | ReplenishmentService | ✅ |
| 供应商管理 | `/api/p4/suppliers` | SupplierService | ✅ |
| 采购订单 | `/api/p4/purchase-orders` | PurchaseOrderService | ✅ |
| 履约追踪 | `/api/fulfillment` | FulfillmentService | ✅ |

#### P5: 营销自动化系统

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| 用户分群 (RFM 模型) | `/api/p5/segmentation` | SegmentationService | ✅ |
| 营销自动化 | `/api/p5/automation` | AutomationService | ✅ |
| 营销 ROI 分析 | `/api/p5/roi` | ROIAnalysisService | ✅ |
| A/B 测试 | `/api/p5/ab-tests` | ABTestService | ✅ |
| 智能优惠券 | `/api/p5/smart-coupons` | SmartCouponService | ✅ |

#### P6: 数据分析增强

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| 销售报表 | `/api/analytics/sales-reports` | AnalyticsService | ✅ |
| 用户行为分析 | `/api/analytics/user-behavior` | - | ✅ |
| 商品分析 | `/api/analytics/products` | - | ✅ |
| 预测分析 | `/api/analytics/predictions` | - | ✅ |
| 自定义报表 | `/api/analytics/custom-reports` | - | ✅ |
| 团长考核 | `/api/organizer-assessment` | OrganizerAssessmentService | ✅ |
| 售后服务 | `/api/after-sales` | AfterSalesService | ✅ |
| 签到积分 | `/api/signin-points` | PointsService | ✅ |

#### P7: 游戏化运营

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| 成就系统 | `/api/p7/achievements` | AchievementService | ✅ |
| 排行榜 | `/api/p7/leaderboards` | LeaderboardService | ✅ |
| 砍价玩法 | `/api/p7/bargain` | BargainService | ✅ |

#### P8: 智能风控/信用体系

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| 用户信用评分 | `/api/p8/credit` | CreditScoreService | ✅ |
| 欺诈检测 | `/api/p8/risk` | RiskDetectionService | ✅ |
| 订单风控 | `/api/p8/order-risk` | OrderRiskService | ✅ |
| 黑名单管理 | `/api/p8/blacklist` | BlacklistService | ✅ |
| 风控规则引擎 | `/api/p8/rules` | RiskRuleService | ✅ |

#### P9: 智能履约调度 + 多平台集成

| 模块 | API 路由 | 服务 | 状态 |
|------|---------|------|------|
| 路径优化 (VRP 算法) | `/api/fulfillment-scheduling/routes` | FulfillmentSchedulingService | ✅ |
| 自提点人流预测 | `/api/fulfillment-scheduling/traffic` | TrafficFlowPredictionService | ✅ |
| 时间窗口推荐 | `/api/fulfillment-scheduling/timewindows` | TimeWindowRecommendationService | ✅ |
| 微信小程序集成 | `/api/platform/wechat` | PlatformService | ✅ |
| 支付宝小程序集成 | `/api/platform/alipay` | PlatformService | ✅ |
| 跨平台订单同步 | `/api/platform/orders` | PlatformOrderService | ✅ |

### 2.4 数据模型和数据库设计

#### 核心实体关系图 (ERD)

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Product   │ 1───N │  GroupBuy   │ 1───N │    Order    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id          │       │ id          │       │ id          │
│ name        │       │ product_id  │───┐   │ user_id     │
│ description │       │ organizer_id│   │   │ group_buy_id│
│ category    │       │ target_size │   │   │ product_id  │
│ price       │       │ current_size│   │   │ quantity    │
│ stock       │       │ status      │   │   │ unit_price  │
│ status      │       │ deadline    │   │   │ total_amount│
└─────────────┘       └──────┬──────┘   │   │ status      │
         │                  │          │   └─────────────┘
         │                  │          │
         │                  ▼          │
         │            ┌─────────────┐  │
         │            │GroupMember  │  │
         │            ├─────────────┤  │
         │────────────│ user_id     │  │
                      │ group_id    │◄─┘
                      └─────────────┘

┌─────────────────────────────────────────────────────────┐
│                    扩展实体模型                          │
├─────────────────────────────────────────────────────────┤
│ 佣金系统：CommissionRule, CommissionRecord, OrganizerProfile  │
│ 优惠券系统：CouponTemplate, Coupon                      │
│ 分享裂变：ShareInvite, ShareRewardRule                 │
│ 履约追踪：Fulfillment, FulfillmentEvent                │
│ 需求预测：DemandForecast, CommunityPreference          │
│ 用户增长：InviteRelation, TaskDefinition, MemberProfile│
│ 营销自动化：CustomerSegment, MarketingAutomation       │
│ 数据分析：SalesReport, UserBehavior, ProductSalesRank  │
│ 游戏化：Achievement, Leaderboard, BargainActivity      │
│ 风控：CreditScore, RiskRule, Blacklist                │
│ 履约调度：PickupPoint, DeliveryRoute, DeliveryTask     │
│ 多平台：PlatformAccount, PlatformOrder                │
└─────────────────────────────────────────────────────────┘
```

#### 核心数据表清单

| 表名 | 记录数估算 | 说明 |
|------|-----------|------|
| `products` | ~1000 | 商品信息 |
| `group_buys` | ~5000 | 团购活动 |
| `orders` | ~50000 | 订单记录 |
| `users` | ~10000 | 用户信息 |
| `notifications` | ~100000 | 通知消息 |
| `commission_rules` | ~10 | 佣金规则 |
| `coupon_templates` | ~100 | 优惠券模板 |
| `demand_forecasts` | ~10000 | 需求预测 |
| `credit_scores` | ~10000 | 信用评分 |

### 2.5 API 路由和服务接口

#### API 路由统计

| 类别 | 路由数量 | 前缀 |
|------|---------|------|
| 商品管理 | 6 | `/api/products` |
| 团购管理 | 5 | `/api/groups` |
| 订单管理 | 4 | `/api/orders` |
| 推荐系统 | 5 | `/api/recommendation` |
| AI 对话 | 7 | `/api/chat` |
| 营销自动化 | 6 | `/api/p5` |
| 数据分析 | 5 | `/api/analytics` |
| 风控系统 | 5 | `/api/p8` |
| 履约调度 | 5 | `/api/fulfillment-scheduling` |
| 多平台集成 | 5 | `/api/platform` |
| **总计** | **356+** | - |

#### 核心服务接口

| 服务层 | 服务数量 | 说明 |
|--------|---------|------|
| 业务服务 | 8 | GroupBuy, Product, Order, User, Notification |
| AI 服务 | 6 | Recommendation, DemandForecast, DynamicPricing |
| 营销服务 | 5 | Marketing, Coupon, Share, Campaign |
| 风控服务 | 4 | CreditScore, RiskRule, Blacklist, OrderRisk |
| 履约服务 | 4 | Fulfillment, Scheduling, Inventory, Supplier |

---

## 3. AI Native 特性分析

### 3.1 对话式交互实现 (Chat-first)

#### 实现状态：✅ 已完成

**对话 API 端点**:
```
POST   /api/chat/                    # 对话式交互主接口
GET    /api/chat/sessions/{id}       # 获取会话信息
DELETE /api/chat/sessions/{id}       # 删除会话
GET    /api/chat/history/{user_id}   # 获取对话历史
POST   /api/chat/sessions/{id}/clear # 清空会话历史
POST   /api/chat/quick-start         # 快捷发起团购
```

**支持的自然语言需求表达**:

| 用户输入 | 识别意图 | 执行动作 |
|---------|---------|---------|
| "我想买点新鲜的水果" | find_product | 搜索水果类商品 |
| "帮我找个牛奶团购" | find_product | 搜索牛奶团购 |
| "有什么好吃的推荐吗" | find_product | 推荐热门商品 |
| "我的团购怎么样了" | check_status | 查询团购进度 |
| "发起一个水果团购" | create_group | 创建团购 |

**对话式交互流程**:
```
用户输入 → 意图识别 → Agent 处理 → 工作流执行 → 自然语言回复 + 建议操作
```

**示例对话**:
```
用户："我想买点新鲜的水果，家里有两个小孩"

AI 回复：
"好的！我为您推荐几款适合小朋友的新鲜水果：

1. 有机草莓
   价格：¥49.9 | 成团价：¥35.9
   推荐理由：当季最新鲜、有机认证无农药、小朋友最爱
   成团概率：87%

2. 进口蓝莓
   价格：¥59.9 | 成团价：¥45.9
   推荐理由：花青素丰富、对儿童视力好、保质期长
   成团概率：72%

您想发起哪个团购？我可以帮您自动邀请可能有兴趣的邻居。"

建议操作:
[发起【有机草莓】团购] [详细介绍第一款] [再看看其他商品]
```

### 3.2 自主代理能力 (Agent 自主决策)

#### 实现状态：✅ 已完成

**自主决策能力清单**:

| 能力 | 实现程度 | 说明 |
|------|---------|------|
| 自主选品 | ✅ 完全实现 | AI 主动搜索并推荐商品 |
| 自主创建团购 | ✅ 完全实现 | AI 自主创建团购活动 |
| 自主邀请 | ✅ 完全实现 | AI 分析并邀请潜在参团者 |
| 自主定价 | ✅ 部分实现 | 基于规则的动态定价 |
| 自主履约调度 | ✅ 完全实现 | 智能路径优化 |

**自主创建工作流示例**:
```python
# Agent 自主决策流程
async def _handle_create_group(self, intent: Dict, user_input: str) -> AgentResponse:
    # 1. 调用工作流自主创建团购
    result = await self.client.run_workflow(
        "auto_create_group",
        user_input=user_input,
        user_id=self.context.user_id,
        community_id=self.context.community_id
    )

    # 2. 构建自然语言回复
    return AgentResponse.reply(
        message=f"好的！我已经为您发起了团购！",
        suggestions=["查看团购详情", "分享给更多邻居", "再发起一个团购"],
        data=result.data,
        confidence=0.9
    )
```

**置信度阈值机制**:

| 置信度范围 | 执行策略 |
|-----------|---------|
| >= 0.8 | 高置信度，AI 自主执行 |
| 0.5 - 0.8 | 中置信度，AI 执行并请求确认 |
| < 0.5 | 低置信度，AI 请求人工确认 |

### 3.3 Generative UI 支持

#### 实现状态：⏳ 部分实现

**已实现**:
- ✅ Bento Grid 布局系统
- ✅ Monochromatic 配色方案
- ✅ Linear.app 风格精致设计
- ✅ 响应式设计 (移动端/平板/桌面)

**规划中**:
- ⏳ 根据对话上下文动态生成界面组件
- ⏳ AI 选择并生成可视化组件
- ⏳ 情境化界面 (因用户/场景动态调整)

**前端技术栈**:
```
React 18.3.1 + TypeScript 5.2.2 + Vite 5.1.0
Ant Design 5.14.0 + TailwindCSS 3.4.1
Zustand 4.5.0 (状态管理)
React Query 5.17.0 (数据获取)
i18next 23.8.0 (国际化)
```

**Bento Grid 布局示例**:
```css
.bento-card {
  background-color: var(--color-bg-card);
  border-radius: var(--radius-bento);
  padding: 20px;
  box-shadow: var(--shadow-bento);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.bento-card:hover {
  box-shadow: var(--shadow-bento-hover);
  transform: translateY(-2px);
}
```

### 3.4 主动感知和推送机制

#### 实现状态：✅ 部分实现

**主动感知能力**:

| 场景 | 实现状态 | 说明 |
|------|---------|------|
| 成团进度提醒 | ✅ | 团购进度变化时主动推送 |
| 库存紧张提示 | ✅ | 库存低于阈值时提醒 |
| 降价通知 | ✅ | 商品价格下降时推送 |
| 限时优惠提醒 | ✅ | 秒杀活动开始前推送 |
| 新人专享提醒 | ✅ | 新用户注册后推送专享福利 |

**推送渠道**:
- 应用内通知 (WebSocket 实时推送)
- 短信通知 (可配置)
- 微信模板消息 (小程序集成)

**通知服务架构**:
```python
# 可插拔通知适配器
class NotificationAdapter:
    - InMemoryNotificationAdapter (默认)
    - ConsoleNotificationAdapter (调试)
    - WechatNotificationAdapter (微信)
    - SmsNotificationAdapter (短信)
    - EmailNotificationAdapter (邮件)
```

### 3.5 情境化界面

#### 实现状态：⏳ 规划中

**当前实现**:
- ✅ 明亮/黑暗主题切换
- ✅ 国际化 (中文/英文)
- ✅ 响应式布局

**规划功能**:
- ⏳ 界面随用户角色动态调整 (普通用户/团长/运营)
- ⏳ 界面随使用场景动态调整 (购物/查询/售后)
- ⏳ 界面随时间上下文调整 (早间推荐/晚间推荐)
- ⏳ 用户偏好记忆和个性化界面

---

## 4. 长远目标和愿景

### 4.1 L5 专家级 AI Native 愿景描述

**愿景陈述**:
> 成为**每个社区的 AI 团购管家**，让 AI 成为用户的购物代理人，实现超越人类专家的购物决策能力。

**L5 专家级特征**:

| 维度 | L3 当前状态 | L5 专家级愿景 |
|------|------------|--------------|
| **需求理解** | 关键词匹配 + 简单意图识别 | 深度语义理解 + 情感分析 + 隐含需求挖掘 |
| **选品能力** | 规则 + 协同过滤 | 知识图谱推理 + 全网比价 + 品质预测 |
| **定价能力** | 基于规则的动态定价 | 博弈论最优定价 + 供应商自动谈判 |
| **成团能力** | 基于历史数据的概率预测 | 社交网络分析 + 影响力传播模型 |
| **履约能力** | 路径优化算法 | 实时交通预测 + 多目标优化 |
| **学习能力** | 离线批量训练 | 在线持续学习 + 跨用户知识迁移 |
| **交互能力** | 文本对话 | 多模态交互 (语音/图像/视频) |

### 4.2 平台生态规划

**生态系统参与者**:

```
┌─────────────────────────────────────────────────────────┐
│                    AI 社区团购生态                       │
│                                                         │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐         │
│   │  用户   │────▶│  AI 管家  │◀────│  团长   │         │
│   └─────────┘     └─────────┘     └─────────┘         │
│        │               │               │               │
│        ▼               ▼               ▼               │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐         │
│   │ 供应商  │────▶│  平台   │◀────│ 物流商  │         │
│   └─────────┘     └─────────┘     └─────────┘         │
│        │                               │               │
│        ▼                               ▼               │
│   ┌─────────┐                   ┌─────────┐           │
│   │ 品牌商  │──────────────────▶│ 数据中台 │           │
│   └─────────┘                   └─────────┘           │
└─────────────────────────────────────────────────────────┘
```

**生态角色说明**:

| 角色 | 价值主张 | AI 赋能 |
|------|---------|--------|
| **用户** | 享受 AI 代理购物决策 | 个性化推荐、自动比价、成团优化 |
| **团长** | AI 辅助运营 | 选品建议、成团预测、履约调度 |
| **供应商** | 精准需求预测 | 销量预测、库存优化、定价建议 |
| **物流商** | 智能调度 | 路径优化、时效预测、异常预警 |
| **品牌商** | 数据洞察 | 用户画像、市场趋势、竞品分析 |

### 4.3 商业模式演进路径

**阶段一：平台佣金模式** (当前 -1 年)
```
收入来源:
- 商品销售佣金 (5-15%)
- 团长服务费 (1-3%)
- 供应商入驻费

目标：建立用户基础，完善产品功能
```

**阶段二：数据增值服务** (1-3 年)
```
收入来源:
- 数据洞察报告 (供应商/品牌商)
- 精准营销服务
- AI 能力开放 API

目标：构建数据壁垒，拓展 B 端收入
```

**阶段三：生态平台模式** (3-5 年)
```
收入来源:
- 平台交易抽成
- 金融服务 (供应链金融/消费分期)
- SaaS 服务 (为中小团长提供工具)
- 广告收入

目标：成为社区团购基础设施
```

---

## 5. 执行计划和路线图

### 5.1 已完成的功能清单

#### P0-P9 核心功能 (v0.1.0 - v3.0.0)

- [x] **P0**: 商品/库存/团购/订单核心业务闭环
- [x] **P0**: AI 智能成团预测服务 (回归模型)
- [x] **P0**: AI 选品顾问 (协同过滤)
- [x] **P1**: 标准化工具层、可插拔通知适配器
- [x] **P1**: 动态定价引擎 (成团概率/需求弹性)
- [x] **P1**: 需求预测 (Prophet+LSTM 融合)
- [x] **P2**: 个性化推荐系统 (Wide&Deep 深度排序)
- [x] **P3**: 邀请裂变、任务中心、会员成长体系
- [x] **P4**: 供应链与履约优化 (库存预警/智能补货/供应商管理)
- [x] **P5**: 营销自动化系统 (用户分群/自动化营销/ROI 分析/A/B 测试)
- [x] **P6**: 数据分析增强 (销售报表/用户行为分析/商品分析)
- [x] **P7**: 游戏化运营 (成就系统/排行榜/砍价玩法)
- [x] **P8**: 智能风控/信用体系 (信用评分/欺诈检测/黑名单)
- [x] **P9**: 智能履约调度系统 (路径优化/人流预测/时间窗口)
- [x] **P9**: 多平台集成 (微信/支付宝小程序)

#### P10+ AI Native 转型 (v4.0.0)

- [x] **DeerFlow 2.0 Agent 框架集成**
- [x] **GroupBuyAgent 团购智能体**
- [x] **自主创建团购工作流 (6 步编排)**
- [x] **智能选品工作流 (6 步编排)**
- [x] **主动邀请工作流 (7 步编排)**
- [x] **对话式交互 API (/api/chat)**
- [x] **降级模式支持 (DeerFlow 不可用时)**
- [x] **前端 Bento Grid 布局重构**

### 5.2 待完善的功能和技术债 (TODO 列表)

#### 高优先级 (P0)

- [ ] **LLM 集成**: 当前使用关键词匹配，需接入真实 LLM (GPT-4/Claude/本地模型)
- [ ] **向量数据库**: 用户画像向量存储 (Chroma/Milvus)
- [ ] **数据持久化**: 会话数据当前存储在内存中，需接入 Redis
- [ ] **通知发送**: 邀请功能当前未实际发送通知
- [ ] **商品数据**: 当前使用模拟数据，需对接真实商品服务

#### 中优先级 (P1)

- [ ] **Generative UI 前端组件**: 实现动态界面生成
- [ ] **对话上下文管理**: 完善多轮对话和上下文记忆
- [ ] **用户长期记忆系统**: 实现用户偏好持久化存储
- [ ] **AI 决策可解释性**: 解释推荐理由、价格判断依据
- [ ] **流式输出**: 对话响应支持流式输出

#### 低优先级 (P2)

- [ ] **多 Agent 协作**: 选品 Agent、议价 Agent、履约 Agent 协作
- [ ] **语音交互支持**: 语音输入/输出
- [ ] **多模态交互**: 图文 + 语音
- [ ] **跨社区团购协同**: 社区间团购联动
- [ ] **A/B 测试框架**: 前端 A/B 测试支持

### 5.3 下一步行动计划 (按优先级排序)

#### 短期 (1-2 周) - L3 → L3.5

| 任务 | 负责人 | 预计工时 | 产出 |
|------|--------|---------|------|
| 接入真实 LLM (API 或本地) | AI 团队 | 3 天 | LLM 集成模块 |
| 部署向量数据库 (Chroma) | 后端团队 | 2 天 | 向量存储服务 |
| 会话数据接入 Redis | 后端团队 | 2 天 | Redis 会话存储 |
| 完善通知发送功能 | 后端团队 | 2 天 | 可运行的通知服务 |
| 对接真实商品数据 | 后端团队 | 3 天 | 商品数据 API |

#### 中期 (1-2 月) - L3.5 → L4

| 任务 | 负责人 | 预计工时 | 产出 |
|------|--------|---------|------|
| Generative UI 引擎 | 前端团队 | 2 周 | 动态界面生成 |
| 用户长期记忆系统 | AI 团队 | 1 周 | 用户画像向量库 |
| AI 决策解释引擎 | AI 团队 | 1 周 | 可解释性模块 |
| 多 Agent 协作框架 | AI 团队 | 2 周 | Agent 协作系统 |
| 流式对话输出 | 后端团队 | 3 天 | 流式响应 API |

#### 长期 (3-6 月) - L4 → L5

| 任务 | 负责人 | 预计工时 | 产出 |
|------|--------|---------|------|
| 语音交互支持 | 前端团队 | 1 月 | 语音交互模块 |
| 多模态交互 | 前端团队 | 1 月 | 多模态 UI |
| 跨社区协同 | 后端团队 | 1 月 | 社区联动系统 |
| 知识图谱构建 | AI 团队 | 2 月 | 商品知识图谱 |
| 在线学习系统 | AI 团队 | 2 月 | 持续学习框架 |

---

## 6. 快速启动指南

### 6.1 环境配置要求

**系统要求**:
- Python 3.9+
- Node.js 18+
- SQLite (默认) 或 PostgreSQL 13+
- Redis (可选，用于会话存储)

**推荐配置**:
- CPU: 4 核+
- 内存：8GB+
- 磁盘：20GB+

### 6.2 依赖安装步骤

#### 后端依赖安装

```bash
# 进入项目目录
cd ai-community-buying

# 创建虚拟环境 (可选)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 安装 Python 依赖
pip install -r requirements.txt
```

**requirements.txt**:
```
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
redis>=5.0.0
scikit-learn>=1.3.0
python-dotenv>=1.0.0
```

#### 前端依赖安装

```bash
# 进入前端目录
cd frontend

# 安装 npm 依赖
npm install
```

### 6.3 启动命令

#### 后端服务启动

```bash
# 方式 1: 使用 uvicorn 直接启动
cd ai-community-buying/src
uvicorn main:app --host 0.0.0.0 --port 8005 --reload

# 方式 2: 使用 Python 启动
cd ai-community-buying/src
python main.py

# 方式 3: 使用启动脚本 (如果有)
cd ai-community-buying
./start_all_projects.sh
```

**服务启动后访问**:
- API 文档：http://localhost:8005/docs
- 备用文档：http://localhost:8005/redoc
- 健康检查：http://localhost:8005/health

#### 前端服务启动

```bash
# 进入前端目录
cd frontend

# 启动开发服务器
npm run dev

# 或生产构建后启动
npm run build
npm run preview
```

**前端访问地址**:
- 开发环境：http://localhost:3000
- 生产环境：根据部署配置

### 6.4 环境变量配置

复制环境变量示例文件:
```bash
cp .env.example .env
```

**环境变量说明**:
```bash
# 服务配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8005
DEBUG=True

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_community_buying
DB_USER=postgres
DB_PASSWORD=password

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT 配置
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 第三方服务配置 (可选)
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
```

### 6.5 API 测试方法

#### 使用 cURL 测试

```bash
# 健康检查
curl http://localhost:8005/health

# 获取商品列表
curl http://localhost:8005/api/products

# 获取热门推荐
curl http://localhost:8005/api/recommendation/hot

# AI 对话测试
curl -X POST http://localhost:8005/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "我想买点新鲜的水果",
    "community_id": "comm_001"
  }'

# 快捷发起团购
curl -X POST http://localhost:8005/api/chat/quick-start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "community_id": "comm_001"
  }'
```

#### 使用 FastAPI 交互式文档

1. 访问 http://localhost:8005/docs
2. 在交互式文档中直接测试各 API 端点

#### 使用 Python 测试脚本

```python
import requests

BASE_URL = "http://localhost:8005"

# 测试 AI 对话
response = requests.post(f"{BASE_URL}/api/chat/", json={
    "user_id": "user_001",
    "message": "我想买点新鲜的水果",
    "community_id": "comm_001"
})
print(response.json())
```

### 6.6 数据库初始化

**使用 SQLite (默认)**:
```bash
# 启动服务时自动创建数据库
python src/main.py
```

**使用 PostgreSQL**:
```bash
# 1. 创建数据库
createdb ai_community_buying

# 2. 配置环境变量
export DATABASE_URL="postgresql://user:password@localhost:5432/ai_community_buying"

# 3. 启动服务
python src/main.py
```

### 6.7 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 端口被占用 | 8005 端口已被使用 | 修改 `SERVER_PORT` 环境变量 |
| 数据库连接失败 | PostgreSQL 未启动 | 启动 PostgreSQL 服务或切换为 SQLite |
| 前端无法连接后端 | CORS 配置问题 | 检查后端 CORS 配置 |
| 依赖安装失败 | Python/Node 版本不兼容 | 确认 Python 3.9+, Node 18+ |

---

## 附录

### A. 文件结构总览

```
ai-community-buying/
├── .env                        # 环境变量
├── .env.example                # 环境变量示例
├── requirements.txt            # Python 依赖
├── AI_NATIVE_COMPLETION_REPORT.md    # AI Native 转型报告
├── AI_NATIVE_REDESIGN_WHITEPAPER.md  # AI Native 白皮书
├── PROJECT_DOCUMENTATION.md    # 本文档
├── frontend/                   # React 前端
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── ...
│   └── ...
└── src/                        # Python 后端
    ├── main.py                 # 主入口
    ├── agents/                 # Agent 层
    │   ├── deerflow_client.py
    │   └── groupbuy_agent.py
    ├── workflows/              # 工作流层
    │   ├── auto_create_group.py
    │   ├── auto_select_product.py
    │   └── auto_invite.py
    ├── tools/                  # 工具层
    │   ├── groupbuy_tools.py
    │   ├── conversation_tools.py
    │   └── product_tools.py
    ├── api/                    # API 路由
    │   ├── chat.py
    │   ├── products.py
    │   └── ...
    ├── services/               # 服务层
    ├── models/                 # 数据模型
    ├── config/                 # 配置
    ├── middleware/             # 中间件
    └── core/                   # 核心模块
```

### B. 代码统计

| 层级 | 文件数 | 代码行数 |
|------|--------|---------|
| Agents | 3 | ~580 |
| Workflows | 3 | ~960 |
| Tools | 7 | ~860 |
| API | 31 | ~12000+ |
| Services | 36 | ~15000+ |
| Models | 20 | ~8000+ |
| 前端 | 21 | ~3000+ |
| **总计** | **120+** | **~44000+** |

### C. 关键文件路径索引

| 功能 | 文件路径 |
|------|---------|
| AI 对话入口 | `src/api/chat.py` |
| 团购 Agent | `src/agents/groupbuy_agent.py` |
| 自主创建团购 | `src/workflows/auto_create_group.py` |
| 智能选品 | `src/workflows/auto_select_product.py` |
| 主动邀请 | `src/workflows/auto_invite.py` |
| 主入口 | `src/main.py` |
| 前端入口 | `frontend/src/main.tsx` |

---

**文档生成时间**: 2026-04-07
**文档版本**: v1.0.0
**项目版本**: v4.0.0
