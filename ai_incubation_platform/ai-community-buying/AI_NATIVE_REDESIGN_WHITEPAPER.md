# AI Native 重设计白皮书

**项目名称**: AI 社区团购平台
**文档版本**: v1.0.0
**创建日期**: 2026-04-06
**状态**: 推翻重设计

---

## 执行摘要

经过对现有项目的深度分析，我们发现当前项目**并非真正的 AI Native**，而是**传统电商 + AI 推荐功能**的架构。本白皮书提出彻底的 AI Native 重设计方案，将 AI 从"功能"升级为"核心引擎"。

---

# 第一部分：Vision Alignment（愿景对齐）

## 1.1 现有问题诊断

### 1.1.1 AI 依赖测试（失败）

| 测试场景 | 问题 | 结论 |
|----------|------|------|
| 关闭 AI 推荐 | 用户仍可浏览商品列表下单 | ❌ AI 不是必需 |
| 关闭 AI 定价 | 商品仍有基础价格可销售 | ❌ AI 不是必需 |
| 关闭 AI 预测 | 团购仍可正常进行 | ❌ AI 不是必需 |

**根本问题**: AI 是"锦上添花"的推荐功能，而非"没有 AI 就无法运行"的核心引擎

### 1.1.2 自主性测试（失败）

| 维度 | 当前实现 | AI Native 标准 |
|------|----------|---------------|
| 需求感知 | 用户主动浏览商品 | AI 主动感知用户需求 |
| 选品决策 | 用户手动选择 | AI 自主搜索 + 解释推荐理由 |
| 成团发起 | 用户手动参团 | AI 主动邀请 + 预测成功率 |
| 定价策略 | 静态 + 被动调价 | AI 动态议价 + 最优策略 |

**根本问题**: AI 是被动响应式的"工具"，而非主动感知决策的"管家"

### 1.1.3 界面形态测试（失败）

| 界面元素 | 当前实现 | AI Native 标准 |
|----------|----------|---------------|
| 首页 | 商品列表 + 分类 | 对话式交互 + 动态生成 |
| 商品详情 | 静态图文 | AI 生成推荐理由 + 对比分析 |
| 成团页面 | 进度条 + 人数 | 实时预测 + 主动邀请建议 |
| 订单确认 | 固定表单 | 动态生成最优方案 |

**根本问题**: 界面是静态的商品列表，而非随用户需求动态生成的 Generative UI

---

## 1.2 对标分析

### 1.2.1 错误对标（传统电商）

| 竞品 | 为什么不对标 |
|------|-------------|
| 美团优选 | 传统货架电商，AI 仅用于推荐 |
| 多多买菜 | 低价驱动，非 AI 驱动 |
| 兴盛优选 | 供应链驱动，非 AI 驱动 |

### 1.2.2 正确对标（AI Native 产品）

| 对标产品 | 核心特征 | 可借鉴点 |
|----------|----------|----------|
| **AI 购物助手** | 对话式交互、主动比价、自主下单 | 自然语言需求表达 |
| **AI 生活管家** | 理解偏好、主动推荐、自主决策 | 自主感知需求 |
| **Character.ai** | 生成式对话、个性化记忆 | 动态 UI + 个性化 |
| **Notion AI** | 内容自动生成、智能组织 | Generative UI |

---

## 1.3 新愿景定义

### 1.3.1 愿景陈述

> **从"AI 驱动的社区团购平台"升级为"每个社区的 AI 团购管家"**
>
> 让 AI 成为用户的**购物代理人**，自主感知需求、自主选品比价、自主成团下单、自主优化履约

### 1.3.2 核心转变

| 维度 | 旧愿景 | 新愿景 |
|------|--------|--------|
| **AI 角色** | 推荐功能 | 团购管家/购物代理人 |
| **交互方式** | 浏览商品列表 | 对话式 + 动态生成界面 |
| **决策主体** | 用户 | AI 主导 + 用户确认 |
| **价值主张** | 帮助团长选品 | 为用户代理购物决策 |

### 1.3.3 成功指标重定义

| 指标 | 旧定义 | 新定义 |
|------|--------|--------|
| **AI 渗透率** | AI 推荐成交占比 30% | **AI 自主决策订单占比 80%** |
| **用户留存** | 月活用户次月留存 40% | **AI 管家活跃使用率 90%** |
| **成团率** | 成功成团数/发起团购数 | **AI 预测准确率 >95%** |
| **新指标**: AI 代理度 | - | **无需用户操作的订单占比** |

---

# 第二部分：Gap Analysis（差距分析）

## 2.1 架构差距

### 2.1.1 现有架构分析

```
┌─────────────────────────────────────────────────────────┐
│                      用户                                │
│    浏览商品列表 → 手动选择 → 手动参团 → 等待成团         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI 应用层                         │
│  /api/products  /api/recommendation  /api/groups        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   服务层 (Services)                      │
│  ProductService, RecommendationService, GroupBuyService │
│  ↓ AI 功能作为"服务"之一                                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   数据层 (SQLite)                        │
│  Product, GroupBuy, Order, User 等实体                   │
└─────────────────────────────────────────────────────────┘
```

**问题**: AI 是服务层中的一个模块，而非核心引擎

### 2.1.2 AI Native 架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户                                │
│         对话交互 → AI 代理决策 → 用户确认 → 执行        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              AI Agent 核心引擎 (新增)                      │
│  ┌───────────┬───────────┬───────────┬─────────────┐    │
│  │ 需求理解  │ 自主决策  │ 执行编排  │ 学习进化    │    │
│  │  Agent    │  Agent    │  Agent    │  Agent      │    │
│  └───────────┴───────────┴───────────┴─────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   工具层 (Tools)                         │
│  商品搜索工具、价格比较工具、成团预测工具、履约调度工具  │
│  ↓ AI 可调用的原子能力                                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                Generative UI 引擎 (新增)                  │
│  根据对话上下文和 AI 决策动态生成界面                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   数据层 (向量 + 关系)                    │
│  用户画像向量库 + 商品知识图谱 + 交易数据库               │
└─────────────────────────────────────────────────────────┘
```

---

## 2.2 功能差距

### 2.2.1 现有功能 AI 化程度评估

| 功能模块 | AI 参与程度 | 问题 |
|----------|-------------|------|
| AI 选品顾问 | 被动推荐 | 需要用户主动查询，AI 不主动推荐 |
| 智能成团预测 | 被动查询 | 需要用户主动查询成团概率 |
| 动态定价引擎 | 半自动 | 定价策略需要人工配置 |
| 需求预测 | 后台分析 | 预测结果不直接驱动决策 |
| 个性化推荐 | 被动展示 | 基于浏览历史，非主动理解需求 |
| 智能履约调度 | 后台优化 | 用户无感知，不改变交互 |

### 2.2.2 缺失的 AI Native 功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| **对话式需求表达** | 用户说"我想买水果"，AI 理解并推荐 | P0 |
| **AI 自主选品** | AI 主动搜索全网商品，比较后推荐 | P0 |
| **AI 自主成团** | AI 主动邀请潜在参团者，预测成功率 | P0 |
| **AI 自主议价** | AI 与供应商/平台协商最优价格 | P1 |
| **AI 购物记忆** | 记住用户偏好，主动提醒补货 | P1 |
| **Generative UI** | 界面随对话和决策动态生成 | P1 |
| **AI 解释能力** | 解释推荐理由、价格判断依据 | P2 |
| **多 Agent 协作** | 选品 Agent、议价 Agent、履约 Agent 协作 | P2 |

---

## 2.3 技术差距

### 2.3.1 技术栈对比

| 技术层级 | 现有技术 | 需要新增 |
|----------|----------|----------|
| **AI 框架** | scikit-learn, numpy | **LLM 框架**(LangChain/LlamaIndex) |
| **交互方式** | REST API + 静态 UI | **WebSocket + Streaming + Generative UI** |
| **数据存储** | SQLite 关系型 | **+ 向量数据库**(Chroma/Milvus) |
| **知识表示** | 无 | **商品知识图谱 + 用户画像向量** |
| **Agent 框架** | 无 | **自主决策 Agent 框架** |
| **可解释性** | 无 | **AI 决策解释引擎** |

### 2.3.2 技术债务清单

| 债务项 | 影响 | 重构成本 |
|--------|------|----------|
| AI 作为"服务"而非"引擎" | 架构升级需推翻重来 | 高 |
| 缺少向量数据库 | 无法存储用户画像/商品嵌入 | 中 |
| 缺少 LLM 集成 | 无法实现对话式交互 | 高 |
| 静态 UI 架构 | Generative UI 需重新设计 | 高 |
| 没有 Agent 概念 | 自主决策能力需从零构建 | 高 |

---

# 第三部分：Technical Implementation（技术实现）

## 3.1 核心交互重设计

### 3.1.1 用户如何表达需求？（对话，不是浏览）

**旧交互**:
```
用户打开 APP → 浏览商品列表 → 搜索关键词 → 筛选 → 选择商品
```

**新交互**:
```
用户： "我想买点新鲜的水果，家里有两个小孩"
  ↓
AI 理解： {category: "水果", preference: "新鲜", constraint: "适合儿童"}
  ↓
AI 回复： "好的！我为您推荐几款适合小朋友的新鲜水果：
         1. 有机草莓 - 当季最新鲜，无农药，小朋友最爱
         2. 进口蓝莓 - 花青素丰富，对视力好
         3. 海南芒果 - 甜度高，核小肉厚
         您想看看哪一款的详情？"
```

**技术实现**:
```python
# 新增：需求理解 Agent
class DemandUnderstandingAgent:
    def __init__(self, llm: LLM, user_profile: VectorStore):
        self.llm = llm
        self.user_profile = user_profile

    async def understand(self, user_input: str, user_id: str) -> DemandIntent:
        # 1. 提取用户画像向量
        profile = await self.user_profile.get(user_id)

        # 2. LLM 理解意图
        intent = await self.llm.extract_intent(
            query=user_input,
            context=profile,
            schema=DemandIntentSchema
        )

        # 3. 填充隐含信息（基于历史偏好）
        intent = await self._fill_implicit_preferences(intent, profile)

        return intent
```

### 3.1.2 AI 如何选品？（自主搜索 + 理由解释）

**旧模式**:
```
用户点击"推荐" → 系统返回协同过滤结果 → 展示商品列表
```

**新模式**:
```
AI 接收需求 → 自主搜索全网商品 → 多维度比较 → 生成推荐理由 → 呈现给用户

AI 回复: "我为您比较了 15 款商品，精选出这 3 款：

🍓 有机草莓 (推荐指数: 95/100)
   ✅ 推荐理由: 当季最新鲜、有机认证无农药、您过去买过 3 次好评
   ❌ 缺点: 价格略高 (比均价高 20%)
   💰 成团价: ¥29.9/斤 (市场价 ¥39.9)
   📊 成团概率: 87% (还差 5 人，预计 2 小时内成团)

🫐 进口蓝莓 (推荐指数: 88/100)
   ✅ 推荐理由: 花青素丰富、对儿童视力好、保质期长
   ❌ 缺点: 物流时间较长 (3 天)
   💰 成团价: ¥45.9/盒 (市场价 ¥59.9)
   📊 成团概率: 72% (还差 12 人，预计 6 小时内成团)

...

您想发起哪个团购？我可以帮您自动邀请可能有兴趣的邻居。"
```

**技术实现**:
```python
# 新增：选品 Agent
class ProductSelectionAgent:
    def __init__(self, llm: LLM, product_kg: KnowledgeGraph, tools: ToolRegistry):
        self.llm = llm
        self.product_kg = product_kg
        self.tools = tools

    async def select(self, intent: DemandIntent) -> ProductRecommendation:
        # 1. 调用商品搜索工具
        candidates = await self.tools.search_products(intent)

        # 2. 多维度比较（价格、评价、新鲜度、物流...）
        compared = await self._compare_multi_dimension(candidates)

        # 3. 生成推荐理由（可解释性）
        explanations = await self.llm.generate_explanations(
            products=compared,
            user_profile=intent.user_profile
        )

        # 4. 预测成团概率
        for product in compared:
            product.group_success_prob = await self.tools.predict_group_success(product)

        # 5. 排序并返回 Top-N
        return sorted(compared, key=lambda x: x.score, reverse=True)[:5]
```

### 3.1.3 AI 如何成团？（主动邀请 + 预测成功率）

**旧模式**:
```
用户参团 → 等待其他人加入 → 被动查看进度条 → 焦虑等待
```

**新模式**:
```
AI 预测潜在参团者 → 主动发送邀请 → 实时更新预测 → 动态调整策略

AI 主动通知：
"您参与的【有机草莓团购】还差 5 人成团。

我已分析了本小区 500 户居民，发现 23 户有 80%+ 概率感兴趣：
- 3 号楼王阿姨：买过 5 次草莓，平均每月 2 次
- 7 号楼小李：家里有小孩，上周买过有机食品
- ...

我已自动发送邀请给这 23 户，预计 1 小时内可以成团！
当前成团概率：87% → 邀请后：95%

需要我继续扩大邀请范围吗？"
```

**技术实现**:
```python
# 新增：成团 Agent
class GroupFormationAgent:
    def __init__(self, llm: LLM, user_graph: GraphDB, prediction_model: Model):
        self.llm = llm
        self.user_graph = user_graph
        self.prediction_model = prediction_model

    async def auto_invite(self, group_buy: GroupBuy) -> InvitationResult:
        # 1. 分析潜在参团者（图神经网络）
        candidates = await self.user_graph.find_similar_users(
            seed_users=group_buy.existing_members,
            product=group_buy.product
        )

        # 2. 预测每个候选人的参团概率
        for candidate in candidates:
            candidate.prob = await self.prediction_model.predict_join_prob(
                user=candidate,
                group=group_buy
            )

        # 3. 选择最优邀请集合（最大化成团概率）
        invitees = self._optimize_invitation_set(candidates, target_count=group_buy.needed)

        # 4. 自动发送邀请
        invitations = await self._send_invitations(invitees, group_buy)

        # 5. 更新成团概率预测
        new_prob = await self.prediction_model.predict_group_success(
            group_buy, invitations
        )

        return InvitationResult(invitations=invitations, new_prob=new_prob)
```

### 3.1.4 AI 如何定价？（动态议价 + 最优策略）

**旧模式**:
```
静态价格 → 基于规则调价 → 需要人工配置策略
```

**新模式**:
```
AI 分析多方因素 → 自主制定定价策略 → 与供应商协商 → 动态调整

AI 定价报告：
"【有机草莓】定价分析：

📊 成本分析:
   - 采购成本：¥18/斤
   - 物流成本：¥3/斤
   - 损耗预估：5% (¥1/斤)
   - 总成本：¥22/斤

🏪 竞品价格:
   - 美团优选：¥35.9/斤
   - 多多买菜：¥32.9/斤
   - 市场价：¥39.9/斤

📈 需求弹性:
   - 价格敏感度：中等 (弹性系数 -1.5)
   - 最优价格点：¥28-32 区间

💡 建议定价:
   - 基础价：¥29.9/斤 (利润率 26%)
   - 成团折扣：满 20 人 ¥27.9/斤
   - 限时优惠：今晚 8 点前 ¥26.9/斤

我已自动与供应商协商，对方同意如果订单超过 50 斤，可再降¥2/斤。
是否需要我设置阶梯价格？"
```

**技术实现**:
```python
# 新增：定价 Agent
class PricingAgent:
    def __init__(self, llm: LLM, elasticity_model: Model, supplier_api: API):
        self.llm = llm
        self.elasticity_model = elasticity_model
        self.supplier_api = supplier_api

    async def determine_price(self, product: Product, context: PricingContext) -> PriceStrategy:
        # 1. 分析成本结构
        cost = await self._analyze_cost(product)

        # 2. 分析竞品价格
        competitor_prices = await self._fetch_competitor_prices(product)

        # 3. 预测需求弹性
        elasticity = await self.elasticity_model.predict_elasticity(
            product=product,
            context=context
        )

        # 4. 计算最优价格区间
        optimal_range = self._calculate_optimal_range(cost, elasticity, competitor_prices)

        # 5. 与供应商协商阶梯价格
        tiered_pricing = await self.supplier_api.negotiate_tiered_pricing(
            product=product,
            volume_commitment=context.expected_volume
        )

        # 6. 生成定价策略（可解释）
        strategy = await self.llm.generate_pricing_strategy(
            cost=cost,
            competitors=competitor_prices,
            elasticity=elasticity,
            tiered=tiered_pricing
        )

        return strategy
```

---

## 3.2 Generative UI 设计

### 3.2.1 界面如何随用户需求动态变化？

**传统静态 UI**:
```
首页 → 商品列表 → 商品详情 → 购物车 → 结算
(固定页面结构，所有用户看到一样的布局)
```

**Generative UI**:
```
用户输入 → AI 理解意图 → 动态生成界面组件 → 呈现个性化界面

场景 1: "我想买水果"
┌───────────────────────────────────────┐
│  🍓 精选水果推荐 (根据您的偏好)        │
│  ┌─────┐ ┌─────┐ ┌─────┐            │
│  │草莓 │ │蓝莓 │ │芒果 │  商品卡片   │
│  │¥29.9│ │¥45.9│ │¥19.9│            │
│  └─────┘ └─────┘ └─────┘            │
│                                       │
│  💡 AI 建议: 草莓当季最新鲜，推荐购买  │
│  [发起团购] [加入已有团购] [再看看]   │
└───────────────────────────────────────┘

场景 2: "我之前的团购怎么样了？"
┌───────────────────────────────────────┐
│  📊 您的团购进度                       │
│  ┌─────────────────────────────────┐  │
│  │ 有机草莓 ▓▓▓▓▓▓░░ 75% (15/20)  │  │
│  │ 预计 2 小时成团，概率 87%         │  │
│  │ [邀请邻居] [查看物流]           │  │
│  └─────────────────────────────────┘  │
│                                       │
│  AI 提醒: 还差 5 人，建议邀请以下邻居:  │
│  王阿姨 (90% 可能)、小李 (85% 可能)...  │
└───────────────────────────────────────┘

场景 3: "帮我比较一下几款牛奶"
┌───────────────────────────────────────┐
│  🥛 牛奶对比分析                       │
│  ┌─────────┬─────────┬─────────┐     │
│  │ 品牌 A  │ 品牌 B  │ 品牌 C  │     │
│  ├─────────┼─────────┼─────────┤     │
│  │ ¥59.9  │ ¥69.9  │ ¥49.9  │ 价格 │
│  │ 4.9⭐  │ 4.7⭐  │ 4.5⭐  │ 评分 │
│  │ 3 天   │ 2 天   │ 5 天   │ 物流 │
│  │ 高    │ 中    │ 低    │ 钙含量│
│  └─────────┴─────────┴─────────┘     │
│                                       │
│  💡 AI 推荐: 品牌 A 性价比最高        │
│  [选择品牌 A] [再比较其他]            │
└───────────────────────────────────────┘
```

### 3.2.2 技术实现

```python
# 新增：Generative UI 引擎
class GenerativeUIEngine:
    def __init__(self, llm: LLM, component_registry: ComponentRegistry):
        self.llm = llm
        self.components = component_registry

    async def generate(self, context: ConversationContext) -> UIState:
        # 1. 分析对话意图和用户目标
        intent = await self.llm.extract_ui_intent(context.messages)

        # 2. 选择需要的组件类型
        component_types = await self._select_components(intent)

        # 3. 为每个组件生成数据和配置
        components = []
        for comp_type in component_types:
            config = await self._generate_component_config(
                component_type=comp_type,
                context=context
            )
            components.append(UIComponent(type=comp_type, config=config))

        # 4. 生成布局建议
        layout = await self._generate_layout(components, intent)

        return UIState(components=components, layout=layout)

# 组件注册表
class ComponentRegistry:
    def __init__(self):
        self.components = {
            "product_card": ProductCardComponent,
            "comparison_table": ComparisonTableComponent,
            "progress_bar": ProgressBarComponent,
            "ai_suggestion": AISuggestionComponent,
            "action_buttons": ActionButtonsComponent,
            "chat_message": ChatMessageComponent,
            # ... 更多组件
        }
```

---

## 3.3 技术架构重设计

### 3.3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   对话式 UI     │  │  Generative UI  │  │   语音交互     │  │
│  │  (聊天界面)     │  │  (动态组件)     │  │  (可选)        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI Agent 核心引擎                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Orchestrator Agent                     │    │
│  │  (协调所有专业 Agent 的工作流)                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│      ┌──────────────┬────────┼────────┬──────────────┐          │
│      ▼              ▼        ▼        ▼              ▼          │
│  ┌────────┐  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐      │
│  │需求理解│  │ 选品  │ │ 成团  │ │ 定价  │ │ 履约调度│      │
│  │ Agent │  │ Agent │ │ Agent │ │ Agent │ │  Agent  │      │
│  └────────┘  └────────┘ └────────┘ └────────┘ └─────────┘      │
│                              │                                   │
│      ┌──────────────┬────────┼────────┬──────────────┐          │
│      ▼              ▼        ▼        ▼              ▼          │
│  ┌────────┐  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐      │
│  │ 记忆  │  │ 解释  │ │ 学习  │ │ 风控  │ │ 通知    │      │
│  │ Agent │  │ Agent │ │ Agent │ │ Agent │ │  Agent  │      │
│  └────────┘  └────────┘ └────────┘ └────────┘ └─────────┘      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      工具层 (Tools)                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │商品搜索 │ │价格比较 │ │成团预测 │ │用户分析 │ │履约优化 │   │
│  │ 工具   │ │ 工具   │ │ 工具   │ │ 工具   │ │ 工具   │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │通知发送 │ │订单管理 │ │支付处理 │ │库存查询 │ │供应商  │   │
│  │ 工具   │ │ 工具   │ │ 工具   │ │ 工具   │ │ API     │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据层                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   向量数据库    │  │   知识图谱      │  │   关系数据库    │  │
│  │  - 用户画像向量 │  │  - 商品知识图谱 │  │  - 订单数据     │  │
│  │  - 商品嵌入     │  │  - 用户关系图   │  │  - 交易记录     │  │
│  │  - 对话历史嵌入 │  │  - 社区图谱     │  │  - 库存数据     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│         (Chroma)            (Neo4j)            (PostgreSQL)      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3.2 Agent 详细设计

```python
# 1. Orchestrator Agent - 总协调器
class OrchestratorAgent:
    """
    负责理解用户意图，协调各专业 Agent 完成复杂任务
    """
    def __init__(self, llm: LLM, agent_registry: AgentRegistry):
        self.llm = llm
        self.agents = agent_registry

    async def execute(self, user_input: str, context: Context) -> Response:
        # 1. 理解用户意图
        intent = await self.llm.classify_intent(user_input)

        # 2. 规划执行步骤
        plan = await self.llm.generate_plan(
            intent=intent,
            available_agents=self.agents.list(),
            context=context
        )

        # 3. 执行计划（调用各 Agent）
        results = []
        for step in plan.steps:
            agent = self.agents.get(step.agent_name)
            result = await agent.execute(step.input)
            results.append(result)

        # 4. 汇总结果，生成自然语言回复
        response = await self.llm.generate_response(
            plan=plan,
            results=results,
            context=context
        )

        return response

# 2. Memory Agent - 长期记忆管理
class MemoryAgent:
    """
    管理用户长期记忆，支持个性化对话和推荐
    """
    def __init__(self, vector_store: VectorStore, llm: LLM):
        self.vector_store = vector_store
        self.llm = llm

    async def store(self, user_id: str, experience: Experience):
        # 将用户体验向量化存储
        embedding = await self.llm.embed(experience.to_text())
        await self.vector_store.add(
            user_id=user_id,
            text=experience.to_text(),
            embedding=embedding,
            metadata=experience.metadata
        )

    async def retrieve(self, user_id: str, query: str, top_k: int = 5) -> List[Experience]:
        # 根据查询检索相关记忆
        query_embedding = await self.llm.embed(query)
        memories = await self.vector_store.similarity_search(
            user_id=user_id,
            embedding=query_embedding,
            top_k=top_k
        )
        return [Experience.from_memory(m) for m in memories]

# 3. Learning Agent - 持续学习优化
class LearningAgent:
    """
    从用户反馈和交易结果中学习，持续优化模型
    """
    def __init__(self, feedback_db: Database, model_registry: ModelRegistry):
        self.feedback_db = feedback_db
        self.models = model_registry

    async def learn_from_feedback(self, interaction: Interaction):
        # 收集用户反馈
        feedback = await self._collect_feedback(interaction)

        # 分析反馈模式
        patterns = await self._analyze_patterns(feedback)

        # 更新模型（在线学习或批量训练）
        for model_name, model_data in patterns.items():
            model = self.models.get(model_name)
            await model.update(model_data)

    async def a_b_test_analysis(self, experiment_id: str) -> ExperimentResult:
        # 分析 A/B 测试结果
        result = await self._analyze_experiment(experiment_id)
        return result
```

### 3.3.3 数据模型设计

```python
# 1. 用户画像向量模型
class UserProfileVector:
    """
    用户画像的向量表示，用于个性化推荐和记忆检索
    """
    user_id: str
    embedding: List[float]  # 768 维向量

    # 结构化特征
    preferences: Dict[str, float]  # 品类偏好分数
    price_sensitivity: float  # 价格敏感度 (-1 到 1)
    activity_level: float  # 活跃度 (0 到 1)
    trust_score: float  # 信用分数 (0 到 100)

    # 元数据
    created_at: datetime
    updated_at: datetime
    version: int

# 2. 商品知识图谱
class ProductKnowledgeGraph:
    """
    商品知识图谱，支持语义搜索和推理
    """
    # 实体类型
    entity_types = ["Product", "Category", "Brand", "Supplier", "Ingredient"]

    # 关系类型
    relation_types = ["belongs_to", "made_by", "contains", "similar_to", "complementary_to"]

    # 图谱查询示例
    # MATCH (p:Product)-[:belongs_to]->(c:Category {name: "水果"})
    # WHERE p.organic = true
    # RETURN p ORDER BY p.rating DESC

# 3. 对话上下文模型
class ConversationContext:
    """
    对话上下文的完整表示
    """
    session_id: str
    user_id: str
    messages: List[Message]
    current_intent: Optional[Intent]
    retrieved_memories: List[Experience]
    ui_state: UIState
    agent_states: Dict[str, Any]

    def to_prompt(self) -> str:
        """转换为 LLM 提示词"""
        pass
```

---

## 3.4 迁移路径

### 3.4.1 阶段一：基础架构搭建（2 周）

| 任务 | 描述 | 产出 |
|------|------|------|
| 1.1 LLM 框架选型 | 评估 LangChain vs LlamaIndex | 技术选型报告 |
| 1.2 向量数据库部署 | 部署 Chroma/Milvus | 可运行的向量存储服务 |
| 1.3 Agent 框架设计 | 设计 Agent 基类和注册机制 | Agent 框架代码 |
| 1.4 对话式 UI 原型 | 实现基础聊天界面 | 可演示的对话 UI |

**里程碑**: 用户可以与 AI 进行基础对话，AI 能够调用现有 API 返回商品信息

### 3.4.2 阶段二：核心 Agent 开发（4 周）

| 任务 | 描述 | 产出 |
|------|------|------|
| 2.1 需求理解 Agent | 实现意图识别和槽位填充 | 需求理解服务 |
| 2.2 选品 Agent | 实现商品搜索和推荐理由生成 | 选品服务 |
| 2.3 成团 Agent | 实现潜在参团者分析和邀请 | 成团服务 |
| 2.4 记忆 Agent | 实现用户画像向量存储和检索 | 记忆服务 |

**里程碑**: AI 可以理解用户需求并推荐商品，记住用户偏好

### 3.4.3 阶段三：Generative UI 开发（3 周）

| 任务 | 描述 | 产出 |
|------|------|------|
| 3.1 组件注册表 | 实现 UI 组件注册和渲染机制 | 组件框架 |
| 3.2 布局引擎 | 实现动态布局生成算法 | 布局服务 |
| 3.3 前端集成 | 实现 Generative UI 前端渲染 | 可运行的前端 |

**里程碑**: 界面可以根据对话内容动态生成

### 3.4.4 阶段四：高级功能开发（3 周）

| 任务 | 描述 | 产出 |
|------|------|------|
| 4.1 定价 Agent | 实现智能定价和供应商协商 | 定价服务 |
| 4.2 解释 Agent | 实现 AI 决策可解释性 | 解释服务 |
| 4.3 学习 Agent | 实现在线学习和 A/B 测试 | 学习服务 |
| 4.4 多 Agent 协作 | 实现 Agent 间通信和协作 | 协作框架 |

**里程碑**: AI 可以自主制定定价策略并解释决策

### 3.4.5 阶段五：现有功能迁移（2 周）

| 任务 | 描述 | 产出 |
|------|------|------|
| 5.1 现有 API 封装 | 将现有服务封装为 Agent 工具 | 工具适配层 |
| 5.2 数据迁移 | 将现有数据迁移到新架构 | 数据迁移脚本 |
| 5.3 向后兼容 | 保持旧 API 可用 | 兼容层 |

**里程碑**: 旧功能在新架构下继续可用

### 3.4.6 阶段六：测试与优化（2 周）

| 任务 | 描述 | 产出 |
|------|------|------|
| 6.1 端到端测试 | 测试完整用户旅程 | 测试报告 |
| 6.2 性能优化 | 优化响应时间和资源消耗 | 性能报告 |
| 6.3 用户测试 | 收集真实用户反馈 | 用户反馈报告 |

**里程碑**: 产品达到生产就绪状态

---

## 3.5 总体时间线

```
Week 1-2:  [████████] 基础架构搭建
Week 3-6:          [████████████████] 核心 Agent 开发
Week 7-9:                          [████████████] Generative UI
Week 10-12:                                      [████████████] 高级功能
Week 13-14:                                                  [████████] 迁移
Week 15-16:                                                          [████████] 测试

总计：16 周（4 个月）
```

---

# 第四部分：总结

## 4.1 核心对比

| 维度 | 现有架构 | AI Native 架构 |
|------|----------|---------------|
| **AI 角色** | 推荐功能 | 核心引擎/购物代理人 |
| **交互方式** | 浏览 + 点击 | 对话式 + 动态生成 |
| **决策主体** | 用户主导 | AI 主导 + 用户确认 |
| **界面形态** | 静态列表 | Generative UI |
| **数据存储** | 关系型 | 向量 + 图谱 + 关系 |
| **技术栈** | FastAPI + sklearn | LLM + Agent + VectorDB |

## 4.2 风险与挑战

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 响应延迟 | 用户体验下降 | 流式输出 + 缓存策略 |
| LLM 幻觉问题 | 错误信息 | 事实核查 + 工具调用验证 |
| 成本增加 | LLM API 费用 | 本地模型 + 缓存优化 |
| 技术复杂度 | 开发周期延长 | 模块化开发 + 敏捷迭代 |

## 4.3 预期收益

| 指标 | 提升幅度 | 衡量方式 |
|------|----------|----------|
| 用户活跃度 | +50% | DAU/MAU |
| 订单转化率 | +30% | 下单数/访问数 |
| 用户留存 | +40% | 次月留存率 |
| AI 代理度 | 80% | AI 自主决策订单占比 |

---

## 4.4 下一步行动

1. **立即行动** (本周):
   - [ ] 确认 LLM 选型 (GPT-4/Claude/本地模型)
   - [ ] 确认向量数据库选型 (Chroma/Milvus)
   - [ ] 搭建开发环境

2. **短期** (2 周内):
   - [ ] 完成基础架构搭建
   - [ ] 实现对话式 UI 原型
   - [ ] 招募种子用户测试

3. **中期** (1 个月内):
   - [ ] 完成核心 Agent 开发
   - [ ] 开始 Generative UI 开发
   - [ ] 收集用户反馈迭代

---

**文档结束**

*本白皮书为 AI Native 重设计指导文件，具体实施细节将在各阶段技术方案中详细定义。*


---

## 第十一部分：DeerFlow 2.0 集成设计

### 11.1 架构选型

**统一 Agent 框架**: DeerFlow 2.0

根据 AI Incubation Platform 的统一架构标准，本项目采用 DeerFlow 2.0 作为 Agent 编排框架。

### 11.2 Agent 设计

**Agent 名称**: GroupbuyAgent (团购智能体)

**核心职责**:
- 自主发起团购活动
- 智能推荐商品
- 自动调度履约

**DeerFlow 工具注册表**:

```python
# src/tools/groupbuy_tools.py
TOOLS_REGISTRY = {
    "create_group": {
        "name": "create_group",
        "description": "创建新团购",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "min_participants": {"type": "integer"},
                "deadline": {"type": "string", "format": "date-time"}
            },
            "required": ["product_id", "min_participants"]
        }
    },
    "recommend_product": {
        "name": "recommend_product",
        "description": "基于用户画像推荐商品",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["user_id"]
        }
    },
    "schedule_fulfillment": {
        "name": "schedule_fulfillment",
        "description": "安排团购履约",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string"},
                "warehouse_id": {"type": "string"},
                "delivery_date": {"type": "string", "format": "date"}
            },
            "required": ["group_id"]
        }
    }
}
```

### 11.3 工作流编排

**核心工作流**:

```python
# src/workflows/groupbuy_workflows.py
from deerflow import workflow, step

@workflow(name="auto_groupbuy")
class AutoGroupbuyWorkflow:
    """
    自主发起团购工作流

    流程：
    1. 分析用户需求
    2. 选择商品
    3. 创建团购
    4. 邀请参与者
    5. 跟踪进度
    6. 安排履约
    """

    @step
    async def analyze_demand(self, user_input: str) -> dict:
        """Step 1: 分析用户需求"""
        pass

    @step
    async def select_product(self, demand: dict) -> dict:
        """Step 2: 选择最优商品"""
        pass

    @step
    async def create_group(self, product: dict) -> dict:
        """Step 3: 创建团购"""
        pass

    @step
    async def invite_participants(self, group: dict) -> dict:
        """Step 4: 邀请参与者"""
        pass

    @step
    async def track_progress(self, group: dict) -> dict:
        """Step 5: 跟踪进度"""
        pass

    @step
    async def schedule_fulfillment(self, result: dict) -> dict:
        """Step 6: 安排履约"""
        pass
```

### 11.4 项目结构

```
ai-community-buying/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── deerflow_client.py
│   │   └── groupbuy_agent.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── groupbuy_tools.py
│   │   ├── product_tools.py
│   │   └── fulfillment_tools.py
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── groupbuy_workflows.py
│   │   └── recommendation_workflows.py
│   ├── services/  # 原有
│   └── api/       # 原有
│   └── tests/
│       ├── test_agents.py
│       ├── test_tools.py
│       └── test_workflows.py
```

### 11.5 实施清单

| 任务 | 优先级 | 预计工时 |
|------|-------|---------|
| 安装 DeerFlow 2.0 | P0 | 0.5 天 |
| 创建 tools 层 | P0 | 3 天 |
| 创建工作流 | P0 | 2 天 |
| 创建 Agent 层 | P0 | 2 天 |
| 集成测试 | P0 | 2 天 |
| **合计** | | **9.5 天** |

---

*本白皮书基于 DeerFlow 2.0 框架重新设计。*
