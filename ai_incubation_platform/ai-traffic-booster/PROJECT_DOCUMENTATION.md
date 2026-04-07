# AI Traffic Booster 项目文档

**项目名称**: AI Traffic Booster
**当前版本**: v3.0 AI Native
**文档版本**: v1.0
**最后更新**: 2026-04-07

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

**AI Traffic Booster** 是一个**AI 驱动的流量增长 Agent 平台**，旨在从传统的"数据分析工具"转型为"虚拟增长团队"。

| 维度 | 传统定位 (v2.2) | 新定位 (v3.0) |
|------|----------------|--------------|
| **产品形态** | 流量分析工具 | AI 自主增长 Agent |
| **用户关系** | 人使用工具 | 人与 Agent 协作 |
| **工作模式** | 被动响应查询 | 主动发现问题并执行 |
| **价值主张** | "帮你分析数据" | "帮你增长流量" |

**核心价值**:
- **自主感知**: 7×24 小时持续监控流量，自动发现异常和机会
- **自主决策**: 基于置信度阈值的智能决策引擎
- **自主执行**: 低风险优化操作自主执行，无需人工干预
- **对话交互**: 自然语言对话替代手动配置和复杂表单

### 1.2 AI Native 成熟度等级评估

**当前等级**: **L2 → L3 过渡期** (AI Assisted → AI Driven)

| 等级 | 名称 | 当前状态 | 评估依据 |
|------|------|---------|---------|
| L1 | AI Wrapper | ✅ 已超越 | 已有独立 Agent 架构 |
| L2 | AI Assisted | ✅ 已达到 | AI 主动推送洞察和建议 |
| L3 | AI Driven | ⚠️ 部分达到 | 置信度阈值决策已实现，但 LLM 深度集成待完成 |
| L4 | AI Autonomous | ❌ 未达到 | 自主执行能力有限，需要更多执行工具 |
| L5 | AI Evolving | ❌ 未达到 | 学习引擎尚未实现 |

**评估依据**:

| 测试维度 | 标准 | 当前实现 | 判定 |
|----------|------|---------|------|
| **AI 依赖测试** | 没有 AI，核心功能应失效 | 降级模式仍可运行规则引擎 | ⚠️ 部分通过 |
| **自主性测试** | AI 主动建议/自主执行 | 置信度阈值控制已实现 | ✅ 通过 |
| **对话优先测试** | 交互范式为自然语言对话 | Chat API 已实现 | ✅ 通过 |
| **Generative UI 测试** | 界面由 AI 动态生成 | 固定 Vue 组件，待实现 | ❌ 未通过 |
| **架构模式测试** | Agent + Tools 模式 | DeerFlow 2.0 架构已实现 | ✅ 通过 |

### 1.3 关键成就和里程碑

| 里程碑 | 完成日期 | 状态 |
|--------|---------|------|
| v1.0 基础流量分析 | 2026-03-01 | ✅ 完成 |
| v1.7 可视化仪表板增强 | 2026-03-15 | ✅ 完成 |
| v1.8 AI 查询助手 | 2026-03-20 | ✅ 完成 |
| v1.9 竞品分析模块 | 2026-03-25 | ✅ 完成 |
| v2.0 AI 自动化优化 | 2026-03-30 | ✅ 完成 |
| v2.1 跨平台集成 | 2026-04-01 | ✅ 完成 |
| v2.2 商业化就绪 | 2026-04-05 | ✅ 完成 |
| **v3.0 AI Native 架构转型** | **2026-04-06** | ✅ **完成** |

**v3.0 核心交付物**:
- ✅ Agent 层：`TrafficAgent` 自主流量优化 Agent
- ✅ Tools 层：6 个流量分析工具
- ✅ Workflows 层：6 个多步工作流
- ✅ Chat API：14 个对话式 API 端点
- ✅ 22 个测试用例全部通过

---

## 2. 项目现状

### 2.1 技术架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI Traffic Booster v3.0                           │
│                          技术架构全景图                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      前端层 (Vue 3 + TypeScript)                  │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │    │
│  │  │ AIChatHome  │ │ Dashboard   │ │ Agents      │ │ Reports   │  │    │
│  │  │ (对话主页)  │ │ (仪表板)    │ │ (Agent 中心) │ │ (报告)    │  │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘  │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │    │
│  │  │ Traffic     │ │ SEO         │ │ Automation  │ │ Alerts    │  │    │
│  │  │ Analysis    │ │ Analysis    │ │ (自动化)    │ │ (告警)    │  │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    │ HTTP/REST API                       │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      API 层 (FastAPI)                             │    │
│  │                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │ Chat API (v3.0 AI Native)                                │   │    │
│  │  │ /api/chat/message         - 自然语言对话                  │   │    │
│  │  │ /api/chat/insights        - 主动洞察推送                  │   │    │
│  │  │ /api/chat/workflows/*     - 工作流编排                    │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  │                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │ 核心业务 API                                              │   │    │
│  │  │ /api/analytics            - 流量分析                      │   │    │
│  │  │ /api/seo                  - SEO 分析                      │   │    │
│  │  │ /api/content              - 内容优化                      │   │    │
│  │  │ /api/ab-test              - A/B 测试                      │   │    │
│  │  │ /api/competitor           - 竞品分析                      │   │    │
│  │  │ /api/dashboard            - 仪表板                        │   │    │
│  │  │ /api/data-sources         - 数据源管理                    │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  │                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │ AI 能力 API                                                 │   │    │
│  │  │ /api/ai/anomaly           - 异常检测 (P1)                 │   │    │
│  │  │ /api/ai/root-cause        - 根因分析 (P1)                 │   │    │
│  │  │ /api/ai/suggestions       - 优化建议 (P2)                 │   │    │
│  │  │ /api/ai/query             - AI 查询助手                    │   │    │
│  │  │ /api/ai-optimization      - AI 自动化优化 (v2.0)          │   │    │
│  │  │ /api/ai/learning          - 持续学习 (P3)                 │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    服务层 (Services)                             │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │    │
│  │  │ QueryAssistant│ │ AlertService │ │ LLMService   │            │    │
│  │  │ Service      │ │              │ │              │            │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘            │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │    │
│  │  │ Collaboration│ │ Competitor   │ │ LearningLoop │            │    │
│  │  │ Service      │ │ Service      │ │ Service      │            │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              AI Agent 层 (DeerFlow 2.0)                           │    │
│  │                                                                  │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │ TrafficAgent (流量优化 Agent)                            │    │    │
│  │  │ - 意图识别引擎                                           │    │    │
│  │  │ - 置信度阈值控制                                         │    │    │
│  │  │ - 自主执行决策                                           │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  │                                                                  │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │ DeerFlowClient (Agent 运行时客户端)                       │    │    │
│  │  │ - 工具注册管理                                           │    │    │
│  │  │ - 工作流编排                                             │    │    │
│  │  │ - 降级模式 (Fallback)                                    │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  │                                                                  │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │ Workflows (工作流)                                       │    │    │
│  │  │ - auto_diagnosis       - 自动流量诊断                    │    │    │
│  │  │ - opportunity_discovery - 增长机会发现                   │    │    │
│  │  │ - strategy_execution   - 优化策略执行                    │    │    │
│  │  │ - create_strategy      - 策略创建                        │    │    │
│  │  │ - evaluate_strategy    - 策略评估                        │    │    │
│  │  │ - optimize_strategy    - 策略优化                        │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  │                                                                  │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │ TrafficTools (工具集)                                    │    │    │
│  │  │ - get_traffic_data     - 获取流量数据                    │    │    │
│  │  │ - detect_anomaly       - 检测流量异常                    │    │    │
│  │  │ - analyze_root_cause   - 分析根因                        │    │    │
│  │  │ - get_opportunities    - 获取增长机会                    │    │    │
│  │  │ - execute_strategy     - 执行优化策略                    │    │    │
│  │  │ - get_competitor_data  - 获取竞品数据                    │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      数据持久层                                 │    │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │    │
│  │  │ SQLite        │  │ PostgreSQL    │  │ Redis         │       │    │
│  │  │ (开发/测试)   │  │ (生产)        │  │ (缓存)        │       │    │
│  │  └───────────────┘  └───────────────┘  └───────────────┘       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心功能模块清单

| 模块 | 文件路径 | 功能描述 | 状态 |
|------|---------|---------|------|
| **SEO 优化** | `src/seo/` | 关键词分析、内容优化、Technical SEO | ✅ 完成 |
| **内容优化** | `src/content/` | 内容质量分析、关键词密度优化 | ✅ 完成 |
| **流量分析** | `src/analytics/` | 流量趋势、来源分析、用户行为 | ✅ 完成 |
| **A/B 测试** | `src/ab_test/` | 实验设计、效果分析、统计显著性 | ✅ 完成 |
| **竞品分析** | `src/api/competitor_analysis.py` | 竞品追踪、市场份额、策略分析 | ✅ 完成 |
| **AI 查询助手** | `src/api/query_assistant.py` | 自然语言查询、查询历史、报告生成 | ✅ 完成 |
| **AI 异常检测** | `src/api/anomaly_detection.py` | 流量异常检测、自动告警 | ✅ 完成 |
| **AI 根因分析** | `src/api/root_cause_analysis.py` | 根因分析、因果推断 | ✅ 完成 |
| **AI 自动化优化** | `src/api/ai_optimization.py` | 自动优化建议、代码生成 | ✅ 完成 |
| **AI 对话助手** | `src/api/chat.py` | 自然语言对话、工作流编排 | ✅ 完成 |
| **可视化仪表板** | `frontend-vue/src/views/Dashboard.vue` | 数据可视化、图表展示 | ✅ 完成 |

### 2.3 数据模型和数据库设计

**主要数据实体**:

| 实体 | 模型文件 | 描述 |
|------|---------|------|
| `QueryHistory` | `src/models/query_assistant.py` | 查询历史记录 |
| `QueryFavorite` | `src/models/query_assistant.py` | 用户收藏查询 |
| `SavedReport` | `src/models/query_assistant.py` | 保存的报告 |
| `QueryTemplate` | `src/models/query_assistant.py` | 查询模板 |
| `TrafficData` | (内置于服务层) | 流量数据 |
| `AnomalyRecord` | (内置于服务层) | 异常记录 |
| `AlertConfig` | (内置于服务层) | 告警配置 |

**QueryIntent 枚举** (查询意图分类):
```python
class QueryIntent(Enum):
    TRAFFIC_QUERY = "traffic_query"      # 流量查询
    TREND_QUERY = "trend_query"          # 趋势查询
    COMPARISON_QUERY = "comparison"      # 对比查询
    PAGE_QUERY = "page_query"            # 页面查询
    USER_QUERY = "user_query"            # 用户查询
    COMPETITOR_QUERY = "competitor"      # 竞品查询
    ANOMALY_QUERY = "anomaly_query"      # 异常查询
    ROOT_CAUSE_QUERY = "root_cause"      # 根因查询
    RECOMMENDATION_QUERY = "recommendation"  # 建议查询
```

### 2.4 API 路由和服务接口

**核心 API 端点清单**:

| 路由前缀 | 端点 | 方法 | 描述 |
|---------|------|------|------|
| `/api/chat` | `/message` | POST | 发送自然语言消息 |
| `/api/chat` | `/insights` | GET | 获取 AI 主动洞察 |
| `/api/chat` | `/insights/approve` | POST | 批准洞察操作 |
| `/api/chat` | `/sessions/{id}/history` | GET | 获取会话历史 |
| `/api/chat` | `/workflows/diagnosis` | POST | 运行诊断工作流 |
| `/api/chat` | `/workflows/opportunities` | POST | 运行机会发现工作流 |
| `/api/chat` | `/workflows/strategy/create` | POST | 创建策略工作流 |
| `/api/chat` | `/status` | GET | AI 助手状态 |
| `/api/analytics` | `/traffic` | GET | 获取流量数据 |
| `/api/analytics` | `/trends` | GET | 流量趋势 |
| `/api/analytics` | `/paths` | GET | 路径分析 |
| `/api/seo` | `/analysis` | GET | SEO 分析 |
| `/api/seo` | `/keywords` | GET | 关键词分析 |
| `/api/competitor` | `/analysis` | GET | 竞品分析 |
| `/api/ai` | `/anomaly` | POST | 异常检测 |
| `/api/ai` | `/root-cause` | POST | 根因分析 |
| `/api/ai` | `/suggestions` | GET | 获取建议 |
| `/api/ai` | `/query` | POST | AI 查询 |

---

## 3. AI Native 特性分析

### 3.1 对话式交互实现

**核心实现**: `src/api/chat.py`

**对话流程**:
```
用户输入 → 意图识别 → Agent 处理 → 执行工作流 → 返回结果
    │                                              │
    └────────────── 会话历史记录 ──────────────────┘
```

**意图分类逻辑** (`src/agents/traffic_agent.py`):
```python
def _classify_intent(self, message: str) -> str:
    # 执行类意图（优先级最高）
    if any(kw in message_lower for kw in ["执行", "运行", "开始", "execute"]):
        return "execute"
    # 分析类意图
    if any(kw in message_lower for kw in ["为什么", "分析", "原因", "analyze"]):
        return "analyze"
    # 优化类意图
    if any(kw in message_lower for kw in ["优化", "机会", "提升", "optimize"]):
        return "optimize"
    return "general"
```

**示例对话**:
```
用户：分析上周流量为什么下跌
AI:  正在分析：分析上周流量为什么下跌 [追踪 ID: trace_xxx]
     检测到流量下跌 15%，主要原因是...

用户：发现增长机会
AI:  正在分析增长机会... [机会发现工作流启动]
     发现 3 个关键词有上升空间...

用户：执行 SEO 优化策略
AI:  建议执行优化策略，预计提升流量 15%
     [批准执行] [查看详情]
```

### 3.2 自主代理能力

**置信度阈值控制**:

| 置信度范围 | 决策模式 | 行为 |
|-----------|---------|------|
| >= 0.9 | 自主执行 | AI 直接执行，事后通知 |
| 0.7 - 0.9 | 请求批准 | AI 建议，用户批准后执行 |
| < 0.7 | 仅建议 | AI 提供建议，用户手动执行 |

**自主执行流程** (`src/agents/traffic_agent.py`):
```python
async def execute_optimization(self, strategy_id: str) -> AgentResponse:
    confidence = 0.85  # 从策略获取

    if confidence >= self.auto_execute_threshold:
        return await self._auto_execute(strategy_id)  # 自主执行
    elif confidence >= self.request_approval_threshold:
        return AgentResponse(
            message="建议执行优化策略...",
            requires_approval=True
        )
    else:
        return AgentResponse(
            message="发现优化机会，建议人工审核",
            requires_approval=True
        )
```

### 3.3 Generative UI 支持

**当前状态**: ❌ 未实现

**已实现的 UI 组件** (固定布局):
- `AIChatHome.vue` - AI 对话主页
- `Dashboard.vue` - 数据仪表板
- `AgentsOverview.vue` - Agent 状态概览
- `TrafficAnalysis.vue` - 流量分析页
- `SEOAnalysis.vue` - SEO 分析页

**待实现的 Generative UI**:
```python
# 目标：动态生成仪表板
class GenerativeDashboard:
    def generate(self, context: UserContext) -> Dashboard:
        # 基于当前状态动态生成内容
        priorities = self.ai.identify_priorities(context)
        components = [self.render_component(p) for p in priorities]
        return Dashboard(components=components)
```

### 3.4 主动感知和推送机制

**主动洞察推送** (`src/api/chat.py`):
```python
@router.get("/insights", response_model=List[Dict])
async def get_insights(
    limit: int = 10,
    insight_type: Optional[str] = None
) -> List[Dict]:
    """获取 AI 主动发现的洞察"""
    # 洞察类型：anomaly, opportunity, report
```

**推送类型**:

| 类型 | 触发条件 | 推送渠道 |
|------|---------|---------|
| **异常检测** | 流量下跌>15% | 即时推送 |
| **增长机会** | ROI 预测>30% | 每日汇总 |
| **效果报告** | 优化完成 | 即时通知 |
| **周报/月报** | 周期性 | 定时推送 |

**示例推送内容**:
```json
{
  "id": "insight_1",
  "type": "anomaly",
  "title": "流量异常下跌 15%",
  "content": "检测到自然搜索流量较昨日下跌 15%",
  "priority": "high",
  "data": {
    "metric": "organic_traffic",
    "change_percent": -15
  },
  "actions": [
    {"action": "analyze", "label": "分析原因"},
    {"action": "fix", "label": "一键修复"}
  ]
}
```

---

## 4. 长远目标和愿景

### 4.1 L5 专家级 AI Native 愿景

**愿景陈述**:
> AI Traffic Booster 不是一个工具，而是一个 24/7 自主工作的"虚拟增长团队"。它不仅能分析数据，更能自主制定策略、执行优化、学习进化，最终在流量增长领域超越人类专家。

**L5 特征**:
| 特征 | 描述 |
|------|------|
| **完全自主** | 99% 的优化操作无需人工干预 |
| **持续学习** | 从每次执行中学习，策略持续进化 |
| **因果推理** | 深度理解流量变化的因果关系 |
| **跨域协同** | 与营销、产品、技术系统无缝协作 |
| **预测能力** | 提前预测趋势，预防问题发生 |

### 4.2 平台生态规划

**短期目标** (6 个月):
```
┌─────────────────────────────────────────────────────┐
│                   AI Traffic Booster                 │
│                        平台化                        │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Agent 市场  │  │ 工具市场    │  │ 模板市场    │ │
│  │ - 第三方   │  │ - 数据源    │  │ - 查询模板  │ │
│  │   Agent     │  │ - 分析工具 │  │ - 报告模板  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

**中期目标** (1-2 年):
```
┌─────────────────────────────────────────────────────┐
│                 AI 增长云平台                         │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐│
│  │              统一 Agent 运行时                    ││
│  │  (DeerFlow 2.0 企业版)                           ││
│  └─────────────────────────────────────────────────┘│
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ 流量优化    │  │ 转化优化    │  │ 用户增长    │ │
│  │ Agent       │  │ Agent       │  │ Agent       │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

**长期目标** (3-5 年):
```
┌─────────────────────────────────────────────────────┐
│              企业级 AI 增长操作系统                    │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐│
│  │              AI Growth OS                        ││
│  │  - 统一知识图谱                                 ││
│  │  - 跨 Agent 协作                                 ││
│  │  - 自主战略决策                                 ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### 4.3 商业模式演进路径

| 阶段 | 模式 | 目标客户 | 收入来源 |
|------|------|---------|---------|
| **v1-v2** | 工具订阅 | 中小企业 | SaaS 订阅费 |
| **v3** | Agent 服务 | 成长型企业 | 基础订阅 + 执行分成 |
| **v4** | 平台生态 | 全规模企业 | 平台抽成 + 企业定制 |
| **v5** | 操作系统 | 大型集团 | 授权费 + 持续服务 |

---

## 5. 执行计划和路线图

### 5.1 已完成的功能清单

**基础模块** (v1.0-v2.2):
- [x] SEO 分析模块
- [x] 内容优化模块
- [x] 流量分析模块
- [x] A/B 测试模块
- [x] 竞品分析模块
- [x] 可视化仪表板
- [x] AI 查询助手
- [x] AI 异常检测
- [x] AI 根因分析
- [x] AI 自动化优化
- [x] 跨平台集成
- [x] 商业化就绪

**AI Native 核心** (v3.0):
- [x] DeerFlow 2.0 客户端集成
- [x] TrafficAgent 自主 Agent
- [x] TrafficTools 工具集 (6 个工具)
- [x] TrafficWorkflows 工作流 (3 个工作流)
- [x] StrategyWorkflows 工作流 (3 个工作流)
- [x] Chat API 对话接口 (14 个端点)
- [x] 意图识别引擎
- [x] 置信度阈值控制
- [x] 22 个测试用例

### 5.2 待完善的功能和技术债 (TODO)

**高优先级** (P0):
- [ ] LLM 深度集成 - 使用 Claude API 进行深度分析
- [ ] 自然语言报告生成 - AI 生成可读性强的分析报告
- [ ] 执行工具完善 - 实现更多可自主执行的工具
- [ ] 生产环境部署 - Docker 容器化、K8s 编排

**中优先级** (P1):
- [ ] 实时感知层 - 事件驱动的实时监控
- [ ] WebSocket 推送通知 - 实时推送洞察
- [ ] 预测性预警 - 基于趋势预测的提前预警
- [ ] Generative UI - 动态生成仪表板

**低优先级** (P2):
- [ ] 强化学习引擎 - 策略持续优化
- [ ] 知识图谱构建 - 流量知识沉淀
- [ ] 效果归因分析 - 验证优化效果
- [ ] 多租户支持 - SaaS 化改造

### 5.3 下一步行动计划

| 优先级 | 任务 | 预计工时 | 负责人 |
|--------|------|---------|--------|
| P0 | LLM 集成 (Claude API) | 2 周 | TBD |
| P0 | 执行工具完善 (5+ 新工具) | 2 周 | TBD |
| P0 | 生产环境部署配置 | 1 周 | TBD |
| P1 | 实时事件流 (Kafka) | 2 周 | TBD |
| P1 | WebSocket 推送 | 1 周 | TBD |
| P1 | Generative UI 原型 | 2 周 | TBD |
| P2 | 强化学习框架调研 | 1 周 | TBD |

---

## 6. 快速启动指南

### 6.1 环境配置要求

**系统要求**:
- 操作系统：macOS / Linux / Windows (WSL2)
- Python: 3.9+
- Node.js: 18+
- 内存：最低 4GB，推荐 8GB
- 磁盘：最低 1GB 可用空间

**外部依赖** (可选):
- PostgreSQL: 生产环境数据库
- Redis: 缓存和会话存储
- DeerFlow AI 服务：AI 推理服务

### 6.2 依赖安装步骤

**后端依赖**:
```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform/ai-traffic-booster

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

**前端依赖**:
```bash
cd frontend-vue

# 安装依赖
npm install

# 或镜像加速
npm install --registry=https://registry.npmmirror.com
```

### 6.3 启动命令

**方式一：分别启动**

启动后端:
```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform/ai-traffic-booster
source venv/bin/activate
python src/main.py

# 后端将运行在 http://localhost:8000
# API 文档：http://localhost:8000/docs
```

启动前端:
```bash
cd frontend-vue
npm run dev

# 前端将运行在 http://localhost:3000
```

**方式二：一键启动所有项目** (孵化器统一)
```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform
./start_all_projects.sh  # 启动所有项目
# 或
./start_all_frontends.sh  # 仅启动前端
```

### 6.4 API 测试方法

**使用 Swagger UI**:
1. 访问 http://localhost:8000/docs
2. 选择要测试的 API 端点
3. 点击 "Try it out"
4. 填写参数并执行

**使用 curl 命令**:

测试 Chat API:
```bash
# 发送消息
curl -X POST "http://localhost:8000/api/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "分析上周流量", "user_id": "test_user"}'

# 获取 AI 状态
curl "http://localhost:8000/api/chat/status"

# 获取洞察
curl "http://localhost:8000/api/chat/insights"
```

测试诊断工作流:
```bash
curl -X POST "http://localhost:8000/api/chat/workflows/diagnosis" \
  -H "Content-Type: application/json" \
  -d '{
    "date_range": {"start": "2026-04-01", "end": "2026-04-07"},
    "metrics": ["sessions", "pv", "uv"]
  }'
```

**运行测试套件**:
```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform/ai-traffic-booster
source venv/bin/activate

# 运行所有 AI Native 测试
pytest test_ai_native.py -v

# 运行特定测试
pytest test_ai_native.py::TestTrafficAgent::test_intent_classification -v
```

### 6.5 环境变量配置

复制环境配置示例:
```bash
cp .env.example .env
```

编辑 `.env` 文件，设置必要的环境变量:
```bash
# 基础配置
APP_NAME=AI Traffic Booster
ENVIRONMENT=development
DEBUG=true

# 数据库配置
DATABASE_URL=sqlite:///./ai_traffic_booster.db

# 安全配置
SECRET_KEY=your-super-secret-key-here

# AI 配置 (可选)
# OPENAI_API_KEY=sk-your-key
# ANTHROPIC_API_KEY=sk-ant-your-key
```

---

## 附录

### 附录 A: 项目结构总览

```
ai-traffic-booster/
├── src/
│   ├── agents/                    # AI Agent 层
│   │   ├── __init__.py
│   │   ├── deerflow_client.py     # DeerFlow 客户端
│   │   └── traffic_agent.py       # 流量优化 Agent
│   ├── workflows/                 # 工作流层
│   │   ├── __init__.py
│   │   ├── traffic_workflows.py   # 流量工作流
│   │   └── strategy_workflows.py  # 策略工作流
│   ├── tools/
│   │   ├── __init__.py
│   │   └── traffic_tools.py       # 流量工具集
│   ├── api/                       # API 路由层
│   │   ├── chat.py                # Chat API (v3.0)
│   │   ├── analytics.py           # 流量分析 API
│   │   ├── seo.py                 # SEO 分析 API
│   │   └── ...                    # 其他 API
│   ├── services/                  # 服务层
│   │   ├── query_assistant_service.py
│   │   ├── alert_service.py
│   │   └── ...
│   ├── models/                    # 数据模型
│   │   └── query_assistant.py
│   ├── db/                        # 数据库
│   │   ├── __init__.py
│   │   └── models.py
│   ├── core/                      # 核心配置
│   │   ├── config.py
│   │   └── response.py
│   └── main.py                    # 主入口
├── frontend-vue/                  # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── AIChatHome.vue
│   │   │   ├── Dashboard.vue
│   │   │   └── ...
│   │   └── components/
│   └── package.json
├── tests/                         # 测试目录
├── scripts/                       # 脚本工具
├── requirements.txt               # Python 依赖
├── .env.example                   # 环境配置示例
├── AI_NATIVE_REDESIGN_WHITEPAPER.md  # 架构白皮书
├── AI_NATIVE_COMPLETION_REPORT.md      # 完成报告
└── PROJECT_DOCUMENTATION.md       # 本文档
```

### 附录 B: 关键指标

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 代码行数 | ~15,000 | - |
| API 端点数 | 30+ | 50+ |
| 测试用例数 | 22 | 100+ |
| 测试覆盖率 | 60% | 80%+ |
| AI 工具数 | 6 | 20+ |
| AI 工作流数 | 6 | 15+ |

### 附录 C: 相关文档

- [AI Native 重设计白皮书](AI_NATIVE_REDESIGN_WHITEPAPER.md) - 架构转型详细设计
- [AI Native 完成报告](AI_NATIVE_COMPLETION_REPORT.md) - v3.0 实现总结
- [启动指南](STARTUP_GUIDE.md) - 快速启动步骤

---

**文档维护**: AI Traffic Booster 团队
**最后更新**: 2026-04-07
