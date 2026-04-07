# AI Native 重设计白皮书

**项目名称**: Data-Agent Connector
**版本**: 3.0.0
**创建日期**: 2026-04-06
**状态**: 设计提案

---

## 执行摘要

本文档是对 Data-Agent Connector 项目的**AI Native 重设计提案**。经过对现有架构的深度分析，我们发现当前系统本质上是"带 NL2SQL 功能的传统数据网关"，而非真正的 AI Native 系统。

**核心问题**: 没有 AI，系统仍能作为普通数据网关运行——这违反了 AI Native 的第一性原理。

**重设计目标**: 将系统从"数据网关"重新定位为"AI 数据分析师"，让 AI 从被动执行者变为主动分析者。

---

# 第一部分：现状分析与根本质疑

## 1. AI 依赖测试（失败）

### 测试 1: 移除 AI 后系统还能用吗？

**当前状态**:
```python
# 核心查询引擎
async def execute_query(self, connector_name: str, query: str, ...) -> QueryExecutionResult:
    # 1. 限流检查
    # 2. 获取连接器
    # 3. SQL 安全检查
    # 4. 执行查询
    # 5. 记录审计日志
    pass

# NL2SQL 只是可选插件
async def execute_natural_language_query(self, ..., use_llm: Optional[bool] = True):
    if use_llm:
        sql = nl2sql_converter.convert(natural_language, connector_name)
    return await self.execute_query(query=sql, ...)
```

**结论**: 系统核心是 SQL 执行引擎，NL2SQL 是可选功能。移除 AI 后，系统退化为普通数据库代理——**AI 依赖测试失败**。

### 测试 2: AI 是被动执行还是主动理解？

**当前 NL2SQL 实现分析**:
```python
# converter.py - 基于规则的模式匹配
def convert(self, natural_language: str, ...) -> str:
    nl = natural_language.lower().strip()
    table = self._detect_table(nl, schema)  # 简单字符串匹配
    where_clause = self._extract_where(nl, table, schema)  # 正则匹配
    # ...
    return sql
```

**增强版 NL2SQL 分析**:
```python
# nl2sql_ai_service_enhanced.py
async def convert_to_sql(self, natural_language: str, schema: Dict, use_llm: bool):
    # 1. 意图识别 (LLM)
    # 2. Few-Shot 示例检索 (向量相似度)
    # 3. 构建 Prompt 生成 SQL
    # 4. SQL 验证
    # 5. 自校正 (如果失败)
    pass
```

**问题**:
- AI 只负责 SQL 生成，不参与查询规划
- 不理解业务语义（如"销售额"可能涉及多表 JOIN）
- 无法主动澄清歧义（澄清机制是被动的）
- 结果只是原始数据，没有洞察

**结论**: AI 是被动执行者，不是主动分析者——**自主性测试失败**。

### 测试 3: 用户交互范式分析

**当前 API**:
```
POST /api/ai/query
{
  "connector_name": "mysql",
  "natural_language": "查询上个月销售额 Top10 的产品",
  "use_llm": true
}

Response:
{
  "success": true,
  "sql": "SELECT product_id, SUM(amount) FROM orders WHERE ...",
  "data": [...],  // 原始数据
  "explanation": "..."  // 事后解释
}
```

**问题**:
- 用户需要知道数据源名称（技术细节）
- 返回的是原始数据，不是洞察
- 可视化由前端负责，AI 不参与
- 没有追问、没有建议、没有深度分析

**结论**: 用户仍在"写查询"，而非"问问题"——**交互范式测试失败**。

---

## 2. 架构 Gap 分析

### 2.1 现有架构 vs AI Native 架构

| 维度 | 当前架构 (v2.x) | AI Native 架构 (v3.0) |
|------|----------------|----------------------|
| **核心抽象** | SQL 执行引擎 | 自然语言数据网关 |
| **AI 角色** | 可选的 SQL 转换器 | 核心分析引擎 |
| **交互模式** | 查询 → 执行 → 返回数据 | 问题 → 分析 → 返回洞察 |
| **结果展示** | 原始表格数据 | 动态可视化 + 深度解读 |
| **澄清机制** | 被动等待用户重试 | 主动追问澄清 |
| **分析深度** | 单轮查询 | 多轮对话、深度钻取 |
| **可视化** | 前端静态配置 | AI 生成式 UI |
| **数据理解** | 表名/字段名匹配 | 业务语义理解 |

### 2.2 关键缺失能力

| 能力 | 当前状态 | AI Native 要求 |
|------|---------|---------------|
| **意图深度解析** | 简单意图分类 | 多层意图树、隐式需求挖掘 |
| **业务语义理解** | 无 | 业务术语映射、指标定义 |
| **主动澄清** | 歧义检测 | 交互式追问、选项提供 |
| **动态可视化** | 无 | 根据数据类型自适应图表 |
| **深度洞察** | 事后解释 | 趋势分析、异常检测、归因分析 |
| **多轮对话** | 无 | 上下文保持、渐进式分析 |
| **自主优化** | SQL 自校正 | 查询重写、性能优化 |
| **知识沉淀** | Few-Shot 示例库 | 业务知识图谱、查询模式学习 |

---

# 第二部分：愿景重定义

## 3. 新愿景陈述

### 3.1 愿景

**从**: "成为 AI Native 时代的数据网关，让每个 Agent 和业务人员都能安全、自然、高效地访问任何数据源。"

**到**: "**成为 AI 数据分析师，让每个人都能用自然语言与数据对话，获得深度洞察而非原始数据。**"

### 3.2 价值主张

| 维度 | 旧定位 (数据网关) | 新定位 (AI 数据分析师) |
|------|------------------|----------------------|
| **用户输入** | SQL 或类 SQL 自然语言 | 纯自然语言问题 |
| **系统输出** | 原始数据表格 | 洞察报告 + 可视化 |
| **AI 参与度** | SQL 生成 (可选) | 全流程 AI 驱动 |
| **价值创造** | 数据访问 democratization | 数据分析 democratization |

### 3.3 核心设计原则

1. **AI First**: 没有 AI，系统无法运行
2. **Insight over Data**: 返回洞察，不是数据
3. **Conversation over Query**: 对话式交互，非查询式
4. **Generative over Static**: 动态生成 UI，非预配置
5. **Proactive over Reactive**: 主动澄清和建议，非被动执行

---

## 4. 核心交互重设计

### 4.1 用户如何查询数据？

**当前**: 用户需要知道数据源名称，写类似 SQL 的自然语言
```
"在 mysql 数据源中查询 orders 表，筛选 status='completed'，按 created_at 降序排列"
```

**新设计**: 纯自然语言，无需技术细节
```
"上个月哪个产品的销售额最高？"
"和去年同期比怎么样？"
"为什么这个产品卖得好？"
```

### 4.2 AI 如何理解意图？

**当前**: 单层意图识别
```python
intent = recognize_intent(natural_language)  # → {"type": "simple_select"}
```

**新设计**: 多层意图树 + 隐式需求挖掘

```
用户问题: "上个月销售额怎么样？"

┌─ 表层意图: 查询销售额
├─ 时间范围: 上个月 (自动推断: 2026-03-01 ~ 2026-03-31)
├─ 隐含意图:
│  ├─ 需要对比 (环比、同比)
│  ├─ 需要细分 (按产品、地区)
│  └─ 需要趋势 (每日/每周走势)
└─ 建议追问:
   ├─ "您想看哪个地区的销售额？"
   ├─ "需要按产品分类查看吗？"
   └─ "要不要和去年同期对比？"
```

### 4.3 AI 如何展示结果？

**当前**: 返回原始数据
```json
{
  "data": [
    {"product_id": 1, "total_amount": 10000},
    {"product_id": 2, "total_amount": 8000}
  ]
}
```

**新设计**: 洞察报告 + 动态可视化

```json
{
  "insight": {
    "summary": "上个月总销售额为 125 万元，环比增长 15%，同比增长 32%",
    "key_findings": [
      "产品 A 贡献了 40% 的销售额，是销量冠军",
      "华东地区增长最快，环比 +45%",
      "第三周出现销售峰值，与促销活动相关"
    ],
    "anomalies": [
      "3 月 15 日销售额异常低，需关注"
    ]
  },
  "visualizations": [
    {
      "type": "kpi_card",
      "data": {"title": "总销售额", "value": "125 万", "trend": "+15%"}
    },
    {
      "type": "bar_chart",
      "data": {...},
      "title": "各产品销售额对比"
    },
    {
      "type": "line_chart",
      "data": {...},
      "title": "每日销售趋势"
    }
  ],
  "follow_up_questions": [
    "哪个地区的销售额最高？",
    "销售额最高的销售员是谁？",
    "查看销售额下降的原因"
  ]
}
```

### 4.4 AI 如何给出洞察？

**新设计**: 四层洞察引擎

```
Level 1: 描述性分析 (发生了什么)
  → "上个月销售额 125 万，环比 +15%"

Level 2: 诊断性分析 (为什么发生)
  → "增长主要来自华东地区和新产品 A 的热销"

Level 3: 预测性分析 (将要发生什么)
  → "按当前趋势，预计下月销售额将达到 140 万"

Level 4: 规范性分析 (应该做什么)
  → "建议加大华东地区投放，加快产品 A 的补货"
```

---

## 5. Generative UI 设计

### 5.1 查询界面动态生成

**当前**: 固定表单
```
┌─────────────────────────────────┐
│ 数据源：[mysql ▼]               │
│ 查询：[_________________]       │
│ [执行查询]                      │
└─────────────────────────────────┘
```

**新设计**: AI 动态生成界面

```
场景 1: 简单查询
┌─────────────────────────────────┐
│ 💬 "我想看上个月的销售额"       │
│ ─────────────────────────────── │
│ [📊 总销售额] [📈 趋势图]       │
│ [按产品细分] [按地区细分]       │
└─────────────────────────────────┘

场景 2: 对比分析
┌─────────────────────────────────┐
│ 💬 "对比今年和去年的销售情况"   │
│ ─────────────────────────────── │
│ [📊 双柱对比图] [📈 增长率曲线] │
│ [差异分析] [贡献度分析]         │
└─────────────────────────────────┘

场景 3: 异常检测
┌─────────────────────────────────┐
│ 💬 "为什么上周销售额下降了？"   │
│ ─────────────────────────────── │
│ [⚠️ 异常点标记] [🔍 归因分析]   │
│ [相关因素分析] [建议措施]       │
└─────────────────────────────────┘
```

### 5.2 结果可视化自适应

**可视化类型决策树**:

```
数据类型 → 推荐图表
├─ 单指标 (KPI) → 指标卡 + 趋势箭头
├─ 时间序列 → 折线图/面积图
├─ 分类对比 → 柱状图/条形图
├─ 占比分析 → 饼图/环形图/树图
├─ 关系分析 → 散点图/气泡图
├─ 地理数据 → 地图
├─ 漏斗转化 → 漏斗图
├─ 多维分析 → 雷达图/平行坐标
└─ 复杂分析 → 组合图表/仪表板
```

### 5.3 AI 思考过程展示

```
┌─────────────────────────────────────────────────────┐
│ 🤖 AI 思考过程                                       │
│ ─────────────────────────────────────────────────── │
│ 1. 理解问题: "上个月销售额 Top10 产品"              │
│ 2. 识别实体: 时间=上个月，指标=销售额，维度=产品    │
│ 3. 查找数据源: orders 表、products 表               │
│ 4. 构建查询: JOIN + GROUP BY + ORDER BY + LIMIT    │
│ 5. 生成洞察: 产品 A 领先，产品 B 增长最快           │
│ 6. 选择可视化: 柱状图 (对比) + 指标卡 (汇总)        │
└─────────────────────────────────────────────────────┘
```

---

# 第三部分：技术架构重设计

## 6. 从"SQL 执行引擎"到"自然语言数据网关"

### 6.1 架构对比

**当前架构**:
```
┌────────────────────────────────────────────────────┐
│                   API Layer                        │
│  /api/query  /api/ai/query  /api/connectors       │
└────────────────────────────────────────────────────┘
                        │
┌────────────────────────────────────────────────────┐
│                Query Engine                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ Rate Limit │ →│ SQL Check  │ →│ Execute    │  │
│  └────────────┘  └────────────┘  └────────────┘  │
│                        ↑                          │
│              (optional: NL2SQL conversion)        │
└────────────────────────────────────────────────────┘
                        │
┌────────────────────────────────────────────────────┐
│                Connectors                          │
│  MySQL  PG  Mongo  Redis  API  ...                │
└────────────────────────────────────────────────────┘
```

**AI Native 架构**:
```
┌────────────────────────────────────────────────────┐
│              Conversational UI Layer               │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ Chat Input  │  │ Voice Input │  │ File Upload│ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└────────────────────────────────────────────────────┘
                        │
┌────────────────────────────────────────────────────┐
│              AI Analysis Engine                    │
│  ┌──────────────────────────────────────────────┐ │
│  │  Intent Understanding (意图理解)             │ │
│  │  ├─ 表层意图识别                             │ │
│  │  ├─ 隐式需求挖掘                             │ │
│  │  └─ 业务语义映射                             │ │
│  └──────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────┐ │
│  │  Clarification Engine (澄清引擎)             │ │
│  │  ├─ 歧义检测                                 │ │
│  │  ├─ 主动追问                                 │ │
│  │  └─ 选项生成                                 │ │
│  └──────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────┐ │
│  │  Query Planning (查询规划)                   │ │
│  │  ├─ 数据源发现                               │ │
│  │  ├─ 表关系推断                               │ │
│  │  └─ 多步查询分解                             │ │
│  └──────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────┐ │
│  │  SQL Generation (SQL 生成)                    │ │
│  │  ├─ Few-Shot 示例增强                        │ │
│  │  ├─ Schema 关系增强                          │ │
│  │  └─ 自校正                                   │ │
│  └──────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────┐ │
│  │  Insight Generation (洞察生成)               │ │
│  │  ├─ 描述性分析                               │ │
│  │  ├─ 诊断性分析                               │ │
│  │  ├─ 预测性分析                               │ │
│  │  └─ 规范性分析                               │ │
│  └──────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────┐ │
│  │  Visualization Generator (可视化生成)        │ │
│  │  ├─ 图表类型选择                             │ │
│  │  ├─ 数据映射                                 │ │
│  │  └─ 样式优化                                 │ │
│  └──────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
                        │
┌────────────────────────────────────────────────────┐
│           Execution Layer (与安全边界集成)          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ Safety     │ →│ Rate Limit │ →│ Execute    │  │
│  │ Check      │  │            │  │            │  │
│  └────────────┘  └────────────┘  └────────────┘  │
└────────────────────────────────────────────────────┘
                        │
┌────────────────────────────────────────────────────┐
│                Connectors                          │
└────────────────────────────────────────────────────┘
```

### 6.2 核心模块设计

#### 6.2.1 Intent Understanding (意图理解)

```python
class IntentUnderstandingEngine:
    """意图理解引擎"""

    async def parse_intent(self, user_input: str, context: ConversationContext) -> ParsedIntent:
        """
        解析用户意图

        返回:
        -表层意图 (查询、对比、归因、预测等)
        -实体抽取 (时间、指标、维度、筛选条件)
        -隐式需求 (未明确表达但需要的分析)
        -置信度
        """
        pass

    def extract_business_entities(self, text: str) -> List[BusinessEntity]:
        """
        提取业务实体

        例如:"销售额" → Metric(name="sales", definition="SUM(order.amount)")
        "华东地区" → Dimension(name="region", filter="region IN ('上海', '江苏', '浙江')")
        """
        pass
```

#### 6.2.2 Clarification Engine (澄清引擎)

```python
class ClarificationEngine:
    """澄清引擎"""

    async def detect_ambiguity(self, intent: ParsedIntent) -> List[Ambiguity]:
        """
        检测歧义

        返回:
        - 实体歧义 ("苹果"是产品还是公司？)
        - 范围歧义 ("最近"指多久？)
        - 指标歧义 ("销售额"是含税还是不含税？)
        """
        pass

    async def generate_clarification_questions(self, ambiguities: List[Ambiguity]) -> List[ClarificationQuestion]:
        """
        生成澄清问题

        例如:
        - "您指的是哪个地区的销售额？"
        - "您想对比的时间范围是？"
        - "销售额是指含税还是不含税？"
        """
        pass

    async def generate_options(self, ambiguity: Ambiguity) -> List[Option]:
        """
        生成选项供用户选择

        例如:
        - [全部地区，华东，华北，华南，其他]
        - [最近 7 天，最近 30 天，最近 90 天，自定义]
        """
        pass
```

#### 6.2.3 Query Planning (查询规划)

```python
class QueryPlanningEngine:
    """查询规划引擎"""

    async def plan_query(self, intent: ParsedIntent, schema: SchemaInfo) -> QueryPlan:
        """
        规划查询

        处理:
        - 多表 JOIN 自动推断
        - 复杂查询分解为多步
        - 子查询/CTE生成
        - 性能优化建议
        """
        pass

    def discover_data_sources(self, intent: ParsedIntent) -> List[DataSource]:
        """
        自动发现所需数据源

        例如:"销售额" → 需要 orders 表 + products 表
        """
        pass

    def infer_table_relationships(self, tables: List[str], schema: SchemaInfo) -> List[JoinCondition]:
        """
        推断表关系

        例如:orders.product_id → products.id
        """
        pass
```

#### 6.2.4 Insight Generation (洞察生成)

```python
class InsightGenerationEngine:
    """洞察生成引擎"""

    async def generate_insights(self, query_result: QueryResult, context: AnalysisContext) -> Insights:
        """
        生成四层洞察

        Level 1: 描述性 (发生了什么)
        Level 2: 诊断性 (为什么发生)
        Level 3: 预测性 (将要发生什么)
        Level 4: 规范性 (应该做什么)
        """
        pass

    async def detect_anomalies(self, data: List[Dict]) -> List[Anomaly]:
        """
        异常检测

        使用统计方法 + AI 识别数据中的异常点
        """
        pass

    async def generate_attribution_analysis(self, metric: str, dimensions: List[str], data: List[Dict]) -> AttributionResult:
        """
        归因分析

        分析各因素对指标变化的贡献度
        """
        pass
```

#### 6.2.5 Visualization Generator (可视化生成)

```python
class VisualizationGenerator:
    """可视化生成器"""

    async def generate_visualizations(self, data: QueryResult, insights: Insights) -> List[Visualization]:
        """
        根据数据类型和洞察自动生成可视化

        决策逻辑:
        - 单指标 → KPI Card
        - 时间序列 → Line/Area Chart
        - 分类对比 → Bar Chart
        - 占比 → Pie/Donut Chart
        - 关系 → Scatter Plot
        - 地理 → Map
        - 多维 → Radar/Parallel Coordinates
        """
        pass

    def select_chart_type(self, data_characteristics: DataCharacteristics) -> ChartType:
        """选择最佳图表类型"""
        pass

    def generate_vega_spec(self, chart_type: ChartType, data: List[Dict], config: ChartConfig) -> Dict:
        """
        生成 Vega-Lite 规格

        返回可直接渲染的 Vega-Lite JSON
        """
        pass
```

### 6.3 业务语义层设计

**问题**: 当前系统只理解表名/字段名，不理解业务语义

**解决方案**: 引入业务语义层

```python
class BusinessSemanticLayer:
    """业务语义层"""

    # 业务术语定义
    business_terms = {
        "销售额": BusinessMetric(
            name="销售额",
            definition="SUM(orders.amount)",
            tables=["orders"],
            related_terms=["订单金额", "销售收入", "GMV"],
            filters=["status='completed'"],
            time_dimension="created_at"
        ),
        "毛利率": BusinessMetric(
            name="毛利率",
            definition="(SUM(orders.amount) - SUM(orders.cost)) / SUM(orders.amount)",
            tables=["orders"],
            related_terms=["利润率", "毛利"]
        ),
        "活跃用户": BusinessMetric(
            name="活跃用户",
            definition="COUNT(DISTINCT user_id)",
            tables=["user_activities"],
            filters=["activity_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"]
        )
    }

    # 维度层次
    dimension_hierarchies = {
        "地区": DimensionHierarchy(
            name="地区",
            levels=["大区", "省份", "城市", "区县"],
            relationships={
                "华东": ["上海", "江苏", "浙江", "安徽"],
                "华北": ["北京", "天津", "河北", "山西"]
            }
        ),
        "时间": DimensionHierarchy(
            name="时间",
            levels=["年", "季度", "月", "周", "日"]
        )
    }

    async def resolve_term(self, term: str, context: Context) -> ResolvedMetric:
        """
        解析业务术语为具体的 SQL 表达式

        例如:"销售额" → "SUM(orders.amount) WHERE status='completed'"
        """
        pass
```

---

## 7. NL2SQL 深度优化

### 7.1 当前 NL2SQL 问题分析

| 问题 | 原因 | 影响 |
|------|------|------|
| JOIN 准确率低 (65%) | 表关系推断不准确 | 复杂查询失败 |
| 嵌套查询支持弱 | 单层意图识别 | 深度分析无法处理 |
| 业务术语不理解 | 只有表名/字段名映射 | 用户需要知道技术细节 |
| 歧义处理被动 | 澄清机制不完善 | 用户体验差 |

### 7.2 优化方案

#### 方案 1: 知识图谱增强

```python
class KnowledgeGraphEnhancedNL2SQL:
    """知识图谱增强的 NL2SQL"""

    def __init__(self):
        self.knowledge_graph = self._build_knowledge_graph()

    def _build_knowledge_graph(self) -> KnowledgeGraph:
        """
        构建业务知识图谱

        节点:
        - 业务概念 (销售额、利润、用户)
        - 数据实体 (表、字段)
        - 关系 (属于、包含、相关)
        """
        kg = KnowledgeGraph()

        # 添加业务概念节点
        kg.add_node("销售额", type="metric")
        kg.add_node("订单", type="entity")
        kg.add_node("产品", type="entity")

        # 添加数据实体节点
        kg.add_node("orders.amount", type="column")
        kg.add_node("orders.status", type="column")
        kg.add_node("products.name", type="column")

        # 添加关系
        kg.add_edge("销售额", "基于", "orders.amount")
        kg.add_edge("销售额", "关联", "订单")
        kg.add_edge("订单", "包含", "产品")
        kg.add_edge("orders.product_id", "外键", "products.id")

        return kg

    async def convert_with_kg(self, natural_language: str) -> SQLResult:
        """
        使用知识图谱转换 NL2SQL

        步骤:
        1. 识别业务概念
        2. 在 KG 中查找对应数据实体
        3. 遍历 KG 获取关联表和关系
        4. 生成 SQL
        """
        pass
```

#### 方案 2: 思维链 (Chain-of-Thought) 增强

```python
COT_PROMPT = """
你是一个专业的数据分析师。请将用户的自然语言问题转换为 SQL 查询。

请按以下步骤思考:

1. **理解问题**: 用户想要什么信息？
2. **识别实体**: 涉及哪些业务概念 (指标、维度、筛选条件)?
3. **映射数据**: 这些概念对应哪些表和字段？
4. **推断关系**: 如果需要多表，表之间如何关联？
5. **构建 SQL**: 编写 SQL 查询
6. **验证 SQL**: 检查 SQL 是否正确

用户问题: "上个月哪个产品的销售额最高？"

思考过程:
1. **理解问题**: 用户想知道销售额最高的产品
2. **识别实体**:
   - 时间: 上个月
   - 指标: 销售额
   - 维度: 产品
   - 排序: 最高 (DESC)
   - 限制: 哪个 (LIMIT 1)
3. **映射数据**:
   - 销售额 → orders.amount (需要 SUM 聚合)
   - 产品 → products.name
   - 时间 → orders.created_at
4. **推断关系**:
   - orders.product_id = products.id
5. **构建 SQL**:
   ```sql
   SELECT p.name, SUM(o.amount) as total_sales
   FROM orders o
   JOIN products p ON o.product_id = p.id
   WHERE o.created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
     AND o.created_at < DATE_TRUNC('month', CURRENT_DATE)
   GROUP BY p.name
   ORDER BY total_sales DESC
   LIMIT 1
   ```
6. **验证 SQL**: ✓ 正确

SQL: [上述 SQL]
"""
```

#### 方案 3: 自学习机制

```python
class SelfLearningNL2SQL:
    """自学习 NL2SQL"""

    async def learn_from_feedback(self,
                                   natural_language: str,
                                   generated_sql: str,
                                   user_feedback: Feedback,
                                   corrected_sql: Optional[str] = None):
        """
        从用户反馈中学习

        学习策略:
        1. 记录错误模式
        2. 更新 Few-Shot 示例库
        3. 调整 Prompt 模板
        4. 更新知识图谱
        """
        pass

    async def learn_from_execution(self,
                                    natural_language: str,
                                    generated_sql: str,
                                    execution_result: ExecutionResult,
                                    user_behavior: UserBehavior):
        """
        从执行结果和用户行为中学习

        信号:
        - 用户是否修改了 SQL？
        - 用户是否重新查询？
        - 用户是否查看了结果？
        - 用户是否进行了下钻分析？
        """
        pass
```

---

## 8. AI 如何自主构建数据管道

### 8.1 从"查询执行"到"数据管道构建"

**当前能力**: 执行单次查询

**新增能力**: 自主构建和维护数据管道

```
用户问题: "我需要每天早上 9 点收到销售日报"

AI 行动:
1. 理解需求: 定时报表 + 邮件通知
2. 构建查询: 销售数据统计 SQL
3. 创建调度: 每天 9 点执行
4. 配置通知: 发送邮件给用户
5. 监控执行: 失败时自动重试
6. 优化建议: "您是否需要按产品细分？"
```

### 8.2 数据管道类型

| 管道类型 | 描述 | 示例 |
|---------|------|------|
| **报表管道** | 定时生成报表 | 日报、周报、月报 |
| **监控管道** | 持续监控指标 | 异常检测、阈值告警 |
| **ETL 管道** | 数据转换和加载 | 数据清洗、聚合 |
| **分析管道** | 自动化分析流程 | 归因分析、趋势预测 |

### 8.3 管道构建引擎

```python
class PipelineBuilderEngine:
    """管道构建引擎"""

    async def build_pipeline(self,
                              user_request: str,
                              context: PipelineContext) -> Pipeline:
        """
        构建数据管道

        步骤:
        1. 需求解析: 定时？监控？ETL?
        2. 查询生成: 创建基础查询
        3. 调度配置: cron 表达式或触发条件
        4. 输出配置: 邮件/API/仪表板
        5. 异常处理: 重试策略、告警
        """
        pass

    async def suggest_pipelines(self, user_profile: UserProfile) -> List[PipelineTemplate]:
        """
        基于用户画像推荐管道

        例如:
        - 销售经理 → 销售日报、周报
        - 运营 → DAU 监控、转化漏斗
        - 财务 → 收入报表、成本分析
        """
        pass
```

---

# 第四部分：迁移路径

## 9. 分阶段实施计划

### Phase 1: 意图理解增强 (4 周)

**目标**: 实现深度意图理解和业务语义映射

**交付物**:
- Intent Understanding Engine
- Business Semantic Layer
- 知识图谱 MVP

**关键功能**:
- 多层意图识别
- 业务术语解析
- 隐式需求挖掘

### Phase 2: 澄清对话引擎 (3 周)

**目标**: 实现主动澄清和多轮对话

**交付物**:
- Clarification Engine
- Conversation Context Manager
- 对话状态追踪

**关键功能**:
- 歧义检测
- 主动追问
- 选项生成
- 上下文保持

### Phase 3: 洞察与可视化生成 (4 周)

**目标**: 实现四层洞察和动态可视化

**交付物**:
- Insight Generation Engine
- Visualization Generator
- Vega-Lite 集成

**关键功能**:
- 描述性/诊断性/预测性/规范性分析
- 图表类型自适应
- 动态仪表板生成

### Phase 4: 查询规划优化 (3 周)

**目标**: 实现复杂查询自动规划

**交付物**:
- Query Planning Engine
- Knowledge Graph Enhanced NL2SQL
- Chain-of-Thought 增强

**关键功能**:
- 多表 JOIN 自动推断
- 复杂查询分解
- 自学习机制

### Phase 5: 数据管道自主构建 (4 周)

**目标**: 实现自主数据管道构建

**交付物**:
- Pipeline Builder Engine
- 调度集成
- 通知集成

**关键功能**:
- 定时报表
- 监控告警
- ETL 流程

### Phase 6: Generative UI (3 周)

**目标**: 实现对话式 UI 和 AI 思考过程展示

**交付物**:
- Conversational UI
- AI Thinking Visualization
- 动态表单生成

**关键功能**:
- 聊天式交互
- 思考过程透明化
- 动态界面生成

---

## 10. 技术债务处理

### 10.1 保留的现有能力

- 连接器框架 (28+ 连接器)
- 安全检查与审计
- 限流与配额管理
- 多租户架构
- 数据血缘追踪

### 10.2 需要重构的模块

| 模块 | 重构内容 | 优先级 |
|------|---------|--------|
| NL2SQL Converter | 替换为 AI Native 引擎 | P0 |
| Query Engine | 增加 AI 编排层 | P0 |
| API Layer | 增加对话式 API | P1 |
| Frontend | 重建为对话 UI | P1 |

### 10.3 废弃的功能

- 手动 SQL 输入（保留但隐藏）
- 静态图表配置
- 固定表单界面

---

## 11. 成功指标

### 11.1 产品指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|---------|
| NL2SQL 准确率 | 75% | 92% | 测试集评估 |
| 查询澄清率 | <5% | 30%+ | 主动澄清占比 |
| 洞察生成覆盖率 | 0% | 80%+ | 含洞察的查询占比 |
| 可视化自动生成率 | 0% | 90%+ | 自动图表占比 |
| 多轮对话占比 | 0% | 40%+ | 对话式查询占比 |

### 11.2 用户体验指标

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 首次查询成功率 | 65% | 85% |
| 用户满意度 | 3.5/5 | 4.5/5 |
| 平均查询轮次 | 1.0 | 2.5 (深度分析) |
| 任务完成时间 | 3 分钟 | 1 分钟 |

### 11.3 业务指标

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 活跃用户数 | 100 | 500 |
| 日均查询量 | 1000 | 5000 |
| 付费转化率 | 2% | 10% |

---

## 12. 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| LLM 成本高 | 高 | 中 | 缓存优化、小模型蒸馏 |
| 响应延迟增加 | 中 | 中 | 流式响应、异步处理 |
| 意图识别错误 | 高 | 中 | 人工审核、持续学习 |
| 用户接受度低 | 高 | 低 | 渐进式引导、A/B 测试 |
| 数据隐私风险 | 高 | 低 | 本地部署、数据脱敏 |

---

## 13. 竞品对标分析

### 13.1 AI 数据分析师竞品

| 产品 | 优势 | 劣势 | 我们的差异化 |
|------|------|------|-------------|
| **ChatGPT Data Analyst** | 品牌、模型能力 | 无企业级功能、数据连接弱 | 企业级安全、28+ 连接器 |
| **Microsoft Copilot (Power BI)** | Office 集成 | 仅限 Microsoft 生态 | 多源数据、开放架构 |
| **Tableau GPT** | 可视化强 | Tableau 绑定 | 独立部署、灵活集成 |
| **ThoughtSpot Sage** | 搜索强 | 价格高 | 开源、成本优势 |
| **Data-Agent Connector v3.0** | - | - | 业务语义层、四层洞察、生成式 UI |

### 13.2 核心差异化

1. **业务语义层**: 深度理解企业特定业务术语
2. **四层洞察**: 从描述到规范的完整分析链
3. **生成式 UI**: 动态适应查询类型的界面
4. **企业级安全**: 继承现有安全、审计、合规能力
5. **多源数据**: 28+ 连接器，支持任何数据源

---

# 第五部分：附录

## 附录 A: API 设计

### A.1 对话式 API

```python
# POST /api/v3/chat
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None  # 会话 ID
    context: Optional[Dict] = None  # 上下文

class ChatResponse(BaseModel):
    message: str  # AI 回复
    visualizations: List[Visualization]  # 可视化
    follow_up_questions: List[str]  # 追问建议
    clarification: Optional[Clarification] = None  # 澄清请求

# WebSocket /api/v3/chat/stream
# 支持流式响应
```

### A.2 洞察 API

```python
# POST /api/v3/insights/generate
class InsightRequest(BaseModel):
    query_result: List[Dict]
    original_question: str
    context: AnalysisContext

class InsightResponse(BaseModel):
    summary: str
    key_findings: List[str]
    anomalies: List[Anomaly]
    attribution: Optional[AttributionResult]
    predictions: Optional[PredictionResult]
    recommendations: List[str]
```

### A.3 可视化 API

```python
# POST /api/v3/visualizations/generate
class VisualizationRequest(BaseModel):
    data: List[Dict]
    schema: SchemaInfo
    intent: ParsedIntent

class VisualizationResponse(BaseModel):
    visualizations: List[Visualization]
    vega_specs: List[Dict]  # Vega-Lite JSON
    layout: DashboardLayout
```

---

## 附录 B: Prompt 模板

### B.1 意图识别 Prompt

```
你是一个专业的数据分析师助手。请分析用户的问题，提取以下信息:

1. 表层意图 (查询/对比/归因/预测/其他)
2. 时间范围 (明确或隐含)
3. 业务指标 (销售额/利润/用户数等)
4. 分析维度 (产品/地区/时间等)
5. 筛选条件
6. 隐式需求 (用户可能需要但未明确表达的)

用户问题: {user_input}
上下文: {context}

请以 JSON 格式返回分析结果。
```

### B.2 SQL 生成 Prompt (CoT 增强)

```
你是一个 SQL 专家。请将业务问题转换为 SQL 查询。

请按步骤思考:
1. 理解问题：用户想要什么？
2. 识别实体：涉及哪些指标、维度、筛选？
3. 映射数据：对应哪些表和字段？
4. 推断关系：表之间如何关联？
5. 构建 SQL：编写查询
6. 验证检查：SQL 是否正确？

业务问题: {question}
可用表：{tables}
表关系：{relationships}
业务术语定义：{business_terms}

思考过程:
{chain_of_thought}

SQL:
```

### B.3 洞察生成 Prompt

```
你是一个资深数据分析师。请分析以下查询结果，提供深度洞察:

查询问题：{question}
查询结果：{data}

请提供:
1. **关键发现** (3-5 点最重要的发现)
2. **趋势分析** (如有时间序列数据)
3. **异常检测** (识别异常点)
4. **归因分析** (关键驱动因素)
5. **建议** (基于数据的行动建议)

要求:
- 用简洁清晰的商业语言
- 突出关键数字
- 提供对比 (环比/同比)
- 给出可执行建议
```

---

## 附录 C: 数据模型

### C.1 会话模型

```python
class ConversationSession(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    messages: List[Message]
    context: ConversationContext

class Message(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    visualizations: Optional[List[Visualization]]
    clarifications: Optional[List[Clarification]]

class ConversationContext(BaseModel):
    current_topic: Optional[str]
    mentioned_entities: List[Entity]
    time_range: Optional[TimeRange]
    data_sources: List[str]
    previous_queries: List[QueryRecord]
```

### C.2 业务语义模型

```python
class BusinessTerm(BaseModel):
    name: str
    type: Literal["metric", "dimension", "entity", "filter"]
    definition: str  # SQL 表达式
    tables: List[str]
    related_terms: List[str]
    synonyms: List[str]
    examples: List[str]

class DimensionHierarchy(BaseModel):
    name: str
    levels: List[str]  # [年，季度，月，日]
    relationships: Dict[str, List[str]]  # 父→子

class BusinessGlossary(BaseModel):
    terms: Dict[str, BusinessTerm]
    hierarchies: Dict[str, DimensionHierarchy]
```

---

## 附录 D: 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                             │
│  Web App (React)  Mobile App  API Client  Slack/Teams      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway                              │
│  Rate Limiting  Authentication  Routing  Load Balancing    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 AI Native Core                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Conversation Engine                                 │   │
│  │ - Intent Understanding                              │   │
│  │ - Clarification Engine                              │   │
│  │ - Context Management                                │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Analysis Engine                                     │   │
│  │ - Query Planning                                    │   │
│  │ - Insight Generation                                │   │
│  │ - Visualization Generator                           │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Knowledge Layer                                     │   │
│  │ - Business Semantic Layer                           │   │
│  │ - Knowledge Graph                                   │   │
│  │ - Self-Learning                                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  Execution Layer                            │
│  Query Engine  Safety Check  Audit  Connectors             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  Data Sources                               │
│  MySQL  PG  Mongo  Redis  API  S3  ...                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. 总结

### 14.1 核心转变

| 从 | 到 |
|---|---|
| 带 NL2SQL 的数据网关 | AI 数据分析师 |
| SQL 执行引擎 | 自然语言数据网关 |
| 被动执行 | 主动分析 |
| 返回数据 | 返回洞察 |
| 静态界面 | 生成式 UI |
| 单轮查询 | 多轮对话 |

### 14.2 核心价值

1. **降低门槛**: 纯自然语言，无需技术细节
2. **提升效率**: 1 分钟完成原来 3 分钟的分析
3. **深度洞察**: 四层分析，不只是数据展示
4. **主动服务**: 澄清、建议、预警

### 14.3 下一步行动

1. **立即行动**: 组建 AI Native 重设计团队
2. **Week 1-2**: 完成详细设计和技术选型
3. **Week 3-6**: Phase 1 开发 (意图理解)
4. **Week 7-9**: Phase 2 开发 (澄清对话)
5. **Week 10-13**: Phase 3 开发 (洞察与可视化)
6. **Week 14-16**: Phase 4 开发 (查询规划)
7. **Week 17-20**: Phase 5-6 开发 (管道与 UI)
8. **Week 21-22**: 测试与发布

---

**文档状态**: 设计提案
**审批**: 待定
**更新日期**: 2026-04-06


---

## 第十二部分：DeerFlow 2.0 集成实现

### 12.1 架构选型

**统一 Agent 框架**: DeerFlow 2.0

根据 AI Incubation Platform 的统一架构标准，本项目采用 DeerFlow 2.0 作为 Agent 编排框架。

### 12.2 已实现组件

#### 12.2.1 Agents 层 (`src/agents/`)

| 文件 | 描述 | 状态 |
|------|------|------|
| `__init__.py` | 模块导出 | ✅ 完成 |
| `deerflow_client.py` | DeerFlow 客户端封装 | ✅ 完成 |
| `connector_agent.py` | 数据连接器 Agent | ✅ 完成 |

**ConnectorAgent 核心能力**:
- 意图理解：支持连接、查询、Schema、血缘等 7 种意图识别
- 实体提取：自动提取数据源类型、名称、角色等实体
- 歧义检测：检测缺失参数并生成澄清问题
- 隐式需求推断：自动推断验证连接、获取 Schema 等需求
- 对话管理：支持多轮对话上下文

#### 12.2.2 Workflows 层 (`src/workflows/`)

| 文件 | 描述 | 状态 |
|------|------|------|
| `__init__.py` | 模块导出 | ✅ 完成 |
| `connector_workflows.py` | 数据连接工作流 | ✅ 完成 |

**已实现工作流**:
1. `ConnectDatasourceWorkflow` - 连接数据源（6 步）
2. `DisconnectDatasourceWorkflow` - 断开连接（5 步）
3. `QueryDataWorkflow` - 查询数据（4 步）
4. `SchemaDiscoveryWorkflow` - Schema 发现（3 步）
5. `LineageAnalysisWorkflow` - 血缘分析（3 步）
6. `AutoDataPipelineWorkflow` - 自动数据管道（5 步）

#### 12.2.3 Tools 层 (`src/tools/`)

| 工具 | 描述 | 状态 |
|------|------|------|
| `deerflow_tools.py` | 15 个 DeerFlow 工具 | ✅ 完成 |

**工具分类**:
- 连接器管理：list_connectors, connect_datasource, disconnect_datasource
- 查询工具：execute_sql, nl_query
- Schema 工具：get_schema, refresh_schema, list_available_connector_types
- 血缘工具：get_lineage, analyze_impact, get_data_dictionary, search_data_dictionary, sync_dictionary_from_code, record_lineage, get_lineage_statistics

### 12.3 架构特点

1. **降级模式**: DeerFlow 不可用时自动切换本地执行
2. **工具注册表**: TOOLS_REGISTRY 统一注册和管理所有工具
3. **声明式工作流**: 使用 `@workflow` 和 `@step` 装饰器定义流程
4. **审计日志**: 敏感操作自动记录日志
5. **对话式交互**: Agent 支持 chat() 方法进行多轮对话

### 12.4 验收测试结果

```
============================================================
AI Native 转型集成测试
============================================================

[1] 测试 Connector Agent
----------------------------------------
  连接意图：connect (置信度：0.9) ✓
  查询意图：query ✓
  Schema 意图识别 ✓
  血缘意图识别 ✓
  列出连接器识别 ✓

[2] 测试工作流
----------------------------------------
  connect_datasource: ✓
  query_data: ✓
  schema_discovery: ✓
  lineage_analysis: ✓

[3] 测试工具注册表
----------------------------------------
  共 15 个工具可用 ✓

[4] 测试 DeerFlow 客户端
----------------------------------------
  降级模式：启用 ✓
  服务可用：否 (本地降级模式) ✓

[5] 完整流程测试
----------------------------------------
  多轮对话流程测试通过 ✓

============================================================
```

### 12.5 使用示例

#### 示例 1: 使用 Agent 进行对话式交互

```python
from src.agents.connector_agent import ConnectorAgent

agent = ConnectorAgent()

# 第一轮：列出数据源
response = await agent.chat("有哪些数据源？")
print(response.message)

# 第二轮：连接数据源
response = await agent.chat("连接一个 MySQL 数据库，叫 test_db")
print(response.message)
print(response.thinking_process)  # AI 思考过程

# 第三轮：查询数据
response = await agent.chat("查看 test_db 的表结构")
print(response.data)  # Schema 信息
print(response.suggested_actions)  # 建议的后续操作
```

#### 示例 2: 使用工作流编排

```python
from src.workflows.connector_workflows import (
    ConnectDatasourceWorkflow,
    QueryDataWorkflow
)

# 连接数据源工作流
workflow = ConnectDatasourceWorkflow()
result = await workflow.run(
    name="analytics_db",
    connector_type="mysql",
    role="read_only"
)
print(result.to_dict())

# 查询数据工作流
workflow = QueryDataWorkflow()
result = await workflow.run(
    query="查询上个月销售额 Top10 的产品",
    connector_name="analytics_db"
)
print(result.result)  # 包含数据和洞察
```

#### 示例 3: 使用 DeerFlow 客户端

```python
from src.agents.deerflow_client import DeerFlowClient

client = DeerFlowClient(fallback_enabled=True)

# 执行工作流（自动降级）
result = await client.run_workflow(
    "connect_datasource",
    name="test_db",
    connector_type="mysql"
)
print(result.to_dict())

# 调用 Agent
response = await client.call_agent(
    "connector",
    "我想看有哪些数据源",
    context={"user_id": "user123"}
)
```

### 12.6 文件清单

```
src/
├── agents/
│   ├── __init__.py              # 模块导出
│   ├── deerflow_client.py       # DeerFlow 客户端 (12KB)
│   └── connector_agent.py       # Connector Agent (28KB)
├── workflows/
│   ├── __init__.py              # 模块导出
│   └── connector_workflows.py   # 工作流定义 (30KB)
└── tools/
    ├── __init__.py              # 模块导出
    └── deerflow_tools.py        # 工具封装 (25KB)

tests/
└── test_ai_native_integration.py # 集成测试
```

### 12.7 下一步优化方向

1. **LLM 增强意图识别**: 使用真正的 LLM 替代规则匹配，提升意图识别准确率
2. **业务语义层**: 实现业务术语映射和知识图谱
3. **洞察生成引擎**: 实现四层洞察（描述性、诊断性、预测性、规范性）
4. **可视化生成**: 根据数据类型自动生成 Vega-Lite 规格
5. **多轮对话管理**: 增强上下文追踪和对话状态管理

---

*DeerFlow 2.0 集成已完成 - 2026-04-06*
