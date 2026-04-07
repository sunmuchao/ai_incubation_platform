# ai-runtime-optimizer 项目文档

**版本**: v4.0.0 AI Native
**最后更新**: 2026-04-07
**状态**: AI Native 转型已完成

---

## 1. 执行摘要

### 1.1 项目定位和核心价值主张

**ai-runtime-optimizer** 是一个 **AI 原生的自主运维工程师系统**，专注于运行态性能优化和自主故障修复。

> **核心使命**: 从"AI 驱动的性能优化顾问"升级为"AI 原生自主运维工程师"

**核心价值**:
- **AI 主动感知**: 持续扫描指标、日志、追踪数据，在问题发生前预警
- **AI 自主诊断**: 多 Agent 协同分析，构建完整证据链，定位根因
- **AI 自主修复**: 高置信度时自主执行修复，包含安全验证和自动回滚
- **AI 自主优化**: 分析系统瓶颈，生成优化代码建议，自动提交 PR

### 1.2 AI Native 成熟度等级评估

**当前等级**: **L2 (助手) → L3 (代理) 过渡阶段**

| 评估维度 | 当前状态 | 证据 |
|---------|---------|------|
| **AI 依赖测试** | ✓ 通过 | 核心功能依赖 AI Agent 决策 |
| **自主性测试** | ✓ 部分通过 | AI 可主动发现问题并推送建议 |
| **对话优先测试** | ✓ 通过 | 提供 `/api/ai/ask` 自然语言交互 |
| **Generative UI** | ✓ 通过 | 动态仪表板 API 和前端组件 |
| **架构模式测试** | ✓ 通过 | Agent + Tools + Workflows 架构 |

**L2 → L3 迁移进度**:
- [x] AI 能主动发现问题（感知 Agent）
- [x] AI 推送建议（通知系统）
- [ ] AI 多步工作流编排（DeerFlow 集成中）
- [x] 高置信度自主执行（置信度阈值 0.9）
- [x] 执行护栏（风险评估、回滚机制）

### 1.3 关键成就和里程碑

| 里程碑 | 完成日期 | 说明 |
|--------|---------|------|
| v1.0 基础监控 | 2026-02-xx | 指标采集、告警系统 |
| v2.0 AI 增强 | 2026-03-xx | 异常检测、根因分析 |
| v3.0 自主修复 | 2026-04-02 | 执行引擎、验证引擎 |
| **v4.0 AI Native** | **2026-04-06** | **DeerFlow 2.0 Agent 架构** |

---

## 2. 项目现状

### 2.1 技术架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      Generative UI Layer                         │
│                    (前端 React + Ant Design)                      │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │  ChatFirst   │  │  Dashboard   │  │   Agent Viz  │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                      AI Native API Layer                         │
│   ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌────────────┐        │
│   │ /ask    │ │/diagnose │ │/remediate │ │ /optimize  │        │
│   └─────────┘ └──────────┘ └───────────┘ └────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    DeerFlow 2.0 Client                           │
│   ┌─────────────────┐  ┌─────────────────────────────────┐     │
│   │  Remote Mode    │  │      Local Fallback Mode        │     │
│   │  (DeerFlow API) │  │  (本地工作流执行)               │     │
│   └─────────────────┘  └─────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    Optimizer Agent (大脑)                        │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│   │Perceive     │ │ Diagnose    │ │ Remediate   │              │
│   │感知信号     │ │ 诊断根因    │ │ 执行修复    │              │
│   └─────────────┘ └─────────────┘ └─────────────┘              │
│   ┌─────────────┐ ┌─────────────┐                              │
│   │ Optimize    │ │ Tools       │                              │
│   │ 优化建议    │ │ 工具注册表  │                              │
│   └─────────────┘ └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    AI Native Sensor Layer                        │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│   │ Metrics  │   │  Logs    │   │ Tracing  │   │ Anomaly  │   │
│   │ 指标采集  │   │ 日志分析 │   │ 链路追踪 │   │ 异常检测 │   │
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    Data Storage Layer                            │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │  Redis       │  │  InfluxDB    │  │  SQLite      │         │
│   │  缓存/状态   │  │  时序数据    │  │  配置/知识   │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心功能模块清单

| 模块 | 文件路径 | 说明 |
|------|---------|------|
| **Agent 层** | `src/agents/` | AI Agent 核心逻辑 |
| ├── `optimizer_agent.py` | 核心优化 Agent，协调感知 - 诊断 - 修复 - 优化 |
| ├── `deerflow_client.py` | DeerFlow 2.0 客户端，支持远程和本地降级 |
| └── `__init__.py` | 模块导出 |
| **Tools 层** | `src/tools/` | 工具注册表和业务工具 |
| ├── `registry.py` | 工具注册、发现、调用 |
| └── `performance_tools.py` | 性能分析工具集 |
| **Workflows 层** | `src/workflows/` | 声明式工作流编排 |
| ├── `optimizer_workflows.py` | 核心优化工作流定义 |
| └── `local_workflows.py` | 本地降级工作流实现 |
| **Core 层** | `src/core/` | 核心业务逻辑 |
| ├── `anomaly_detector.py` | 异常检测（孤立森林/SVM） |
| ├── `causal_inference.py` | 因果推断引擎 |
| ├── `root_cause_analysis.py` | 根因分析 |
| ├── `remediation_engine.py` | 修复引擎 |
| ├── `execution_engine_v2.py` | 执行引擎 V2（沙箱隔离） |
| ├── `observability_engine.py` | 可观测性引擎 V2.4 |
| ├── `predictive_maintenance_v2.py` | 预测性维护 V2.3 |
| ├── `knowledge_graph.py` | 知识图谱 V2 |
| └── `ai_optimization.py` | AI 优化建议引擎 V2.5 |
| **API 层** | `src/api/` | REST API 端点 |
| ├── `ai_native.py` | AI Native 对话式 API |
| ├── `optimizer.py` | 基础优化器 API |
| ├── `p5_features.py` | P5 预测性维护 API |
| ├── `remediation.py` | 修复 API |
| └── `causal_inference.py` | 因果推断 API |
| **Adapters 层** | `src/adapters/` | 外部系统集成 |
| ├── `metrics/` | 指标采集适配器 |
| ├── `logs/` | 日志采集适配器 |
| └── `tracing/` | 追踪采集适配器 |
| **Models 层** | `src/models/` | 数据模型 |
| ├── `signals.py` | 信号和诊断模型 |
| ├── `analysis.py` | 分析结果模型 |
| └── `strategy.py` | 策略模型 |

### 2.3 数据模型和数据库设计

#### 核心数据模型 (`src/models/signals.py`)

```python
@dataclass
class Signal:
    """感知层信号"""
    id: str
    source: str  # metrics, logs, tracing
    type: str  # anomaly, pattern, bottleneck
    severity: str  # low, medium, high, critical
    timestamp: datetime
    data: Dict[str, Any]
    context: Dict[str, Any]

@dataclass
class Diagnosis:
    """诊断结果"""
    id: str
    root_cause: str
    confidence: float
    evidence: List[Dict[str, Any]]
    affected_services: List[str]
    impact_assessment: Dict[str, Any]
    report: str
    recommended_actions: List[Dict[str, Any]]
    timestamp: datetime

@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    action_type: str  # remediate, optimize
    action_name: str
    details: Dict[str, Any]
    validation_result: Optional[Dict[str, Any]]
    rollback_performed: bool
    error_message: Optional[str]
    timestamp: datetime
```

#### 数据库表设计

**SQLite 表** (配置和知识库):
```sql
-- 知识图谱节点
CREATE TABLE knowledge_nodes (
    id TEXT PRIMARY KEY,
    type TEXT,  -- service, metric, log_pattern
    name TEXT,
    properties JSON,
    created_at TIMESTAMP
);

-- 知识图谱边
CREATE TABLE knowledge_edges (
    source_id TEXT,
    target_id TEXT,
    relation_type TEXT,
    weight REAL,
    PRIMARY KEY (source_id, target_id)
);

-- 案例库
CREATE TABLE case_library (
    id TEXT PRIMARY KEY,
    problem_description TEXT,
    root_cause TEXT,
    solution TEXT,
    confidence REAL,
    created_at TIMESTAMP
);

-- 审计日志
CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY,
    action_type TEXT,
    agent_id TEXT,
    context JSON,
    result JSON,
    timestamp TIMESTAMP
);
```

**InfluxDB** (时序指标):
```
measurements:
- service_metrics (CPU, memory, latency, error_rate)
- system_metrics (disk_io, network_io, cpu_usage)
- anomaly_scores (isolation_forest, svm_score)
```

**Redis** (缓存和状态):
```
keys:
- agent:state:{agent_id}  - Agent 状态
- cache:metrics:{service} - 指标缓存
- session:{session_id}    - 会话数据
```

### 2.4 API 路由和服务接口

#### AI Native API (`/api/ai/*`)

| 端点 | 方法 | 说明 | 请求/响应 |
|------|------|------|----------|
| `/ask` | POST | 自然语言问答 | `AIAskRequest` → `AIAskResponse` |
| `/diagnose` | POST | AI 深度诊断 | `AIDiagnoseRequest` → `AIDiagnoseResponse` |
| `/remediate` | POST | 自主修复执行 | `AIRemediateRequest` → `AIRemediateResponse` |
| `/optimize` | POST | 优化建议生成 | `AIOptimizeRequest` → `AIOptimizeResponse` |
| `/dashboard` | GET | 动态仪表板 | - → `AIDashboardResponse` |
| `/autonomous-loop` | POST | 完整运维循环 | - → `AutonomousLoopResult` |
| `/tools` | GET | 工具列表 | - → `ToolListResponse` |
| `/tools/{name}/invoke` | POST | 工具调用 | `ToolInvokeRequest` → `ToolInvokeResponse` |

#### 基础 API

| API 前缀 | 说明 | 版本 |
|---------|------|------|
| `/api/runtime/*` | 运行时指标和用法 | v1.0 |
| `/api/p5/*` | P5 预测性维护/知识图谱 | v2.0 |
| `/api/remediation/*` | 修复引擎 | v2.1 |
| `/api/root-cause/*` | 因果推断/根因分析 | v2.2 |
| `/api/predictive-maintenance/*` | 预测性维护 | v2.3 |
| `/api/observability/*` | 可观测性引擎 | v2.4 |
| `/api/optimization/*` | AI 优化建议 | v2.5 |

---

## 3. AI Native 特性分析

### 3.1 对话式交互实现

**实现位置**: `src/api/ai_native.py` + `frontend/src/components/ChatInterface.tsx`

**核心能力**:
```python
# 用户用自然语言提问
POST /api/ai/ask
{
    "question": "支付服务为什么延迟高？"
}

# AI 返回完整答案 + 证据 + 可执行操作
{
    "answer": "检测到延迟问题。可能的原因包括：\n1. 数据库查询缓慢...\n2. 外部 API 响应超时...",
    "evidence": [...],
    "actions": [{"type": "diagnose", "endpoint": "/api/ai/diagnose"}],
    "confidence": 0.85
}
```

**前端 Chat 组件**:
- 自然语言输入框
- 消息气泡展示（用户/AI/系统）
- 置信度彩色标签
- 操作按钮（执行/确认/取消）
- 快捷建议（预设问题）
- Agent 状态指示器

### 3.2 自主代理能力

**Optimizer Agent** (`src/agents/optimizer_agent.py`) 实现完整自主运维循环：

```python
async def analyze_and_optimize(
    self,
    service: Optional[str] = None,
    auto_execute: bool = True
) -> Dict[str, Any]:
    """
    完整自主运维循环：
    1. Perceive - 感知信号
    2. Diagnose - 诊断根因
    3. Remediate - 执行修复（高置信度时）
    4. Optimize - 生成优化建议
    """
    trace_id = str(uuid.uuid4())

    # Step 1: Perceive
    signals = await self.perceive(service=service)

    # Step 2: Diagnose
    diagnosis = await self.diagnose(signals)

    # Step 3: Remediate (if confidence >= 0.9)
    if diagnosis.confidence >= self.auto_execute_threshold:
        result = await self.remediate(diagnosis, auto_execute=True)

    # Step 4: Optimize
    optimization = await self.optimize(context={"service": service})
```

**Agent 状态机**:
- `IDLE` - 空闲
- `PERCEIVING` - 感知中
- `DIAGNOSING` - 诊断中
- `REMEDIATING` - 修复中
- `OPTIMIZING` - 优化中
- `ERROR` - 错误

### 3.3 Generative UI 支持

**实现位置**: `src/api/ai_native.py:ai_dashboard` + `frontend/src/components/GenerativeDashboard.tsx`

**动态仪表板生成**:
```python
@router.get("/dashboard", response_model=AIDashboardResponse)
async def ai_dashboard(service: Optional[str] = None, focus: Optional[str] = None):
    # AI 根据当前状态动态生成仪表板

    # 检测系统状态
    critical_signals = [s for s in signals if s.severity == "critical"]

    if critical_signals:
        status = "critical"
        health_score = 20.0
        ai_insights = ["检测到严重问题，需要立即处理"]
    else:
        status = "healthy"
        health_score = 95.0
        ai_insights = ["系统运行正常"]

    # 动态生成建议操作
    suggested_actions = generate_suggested_actions(signals)
```

**前端动态组件**:
- 核心指标卡片（健康度/告警/AI 洞察/建议）
- AI 洞察面板（动态生成）
- 健康趋势图表（ECharts 可视化）
- 服务健康状态表
- 活跃告警列表

### 3.4 主动感知和推送机制

**感知 Agent** (`src/agents/optimizer_agent.py:perceive`):

```python
async def perceive(self, service: Optional[str] = None) -> List[Signal]:
    """
    AI 主动感知系统状态

    1. 收集指标、日志、追踪数据
    2. 识别异常模式
    3. 输出结构化信号
    """
    self.state = AgentState.PERCEIVING

    # 使用 DeerFlow 工作流或本地降级
    result = await self.df_client.run_workflow(
        "perceive_signals",
        service=service
    )

    signals = [Signal(...) for s in result.get("signals", [])]
    return signals
```

**推送机制**:
- WebSocket 实时通知 (`/api/ai/stream`)
- 告警 Badge 更新
- 前端状态指示器

---

## 4. 长远目标和愿景

### 4.1 L5 专家级 AI Native 愿景描述

**愿景**: 成为企业级的 **AI 自主运维专家系统**，实现零人工干预的运行态优化。

**L5 特征**:
| 特征 | 描述 |
|------|------|
| **完全自主** | 99% 的问题无需人工介入 |
| **预测性维护** | 提前 7 天预测潜在问题 |
| **知识进化** | 从历史案例持续学习 |
| **跨系统协同** | 协调多个服务/集群 |
| **代码级优化** | 自主生成并提交优化 PR |

### 4.2 平台生态规划

```
┌─────────────────────────────────────────────────────────┐
│                    AI Incubation Platform                 │
│  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │ ai-runtime-optimizer│  │  ai-hires-human     │      │
│  │ (运维专家)          │  │  (人力资源专家)     │      │
│  └─────────────────────┘  └─────────────────────┘      │
│  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │ ai-community-buying │  │  ai-employee-platform│     │
│  │ (社区团购专家)      │  │  (零工经济专家)     │      │
│  └─────────────────────┘  └─────────────────────┘      │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           DeerFlow 2.0 Agent Framework          │   │
│  │           (统一 Agent 运行时)                    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.3 商业模式演进路径

| 阶段 | 模式 | 目标客户 |
|------|------|---------|
| **Phase 1** | 开源项目 | 开发者社区 |
| **Phase 2** | SaaS 服务 | 中小企业 |
| **Phase 3** | 企业版 | 大型企业（私有部署） |
| **Phase 4** | 平台生态 | ISV/SI 合作伙伴 |

---

## 5. 执行计划和路线图

### 5.1 已完成的功能清单

| 功能 | 状态 | 说明 |
|------|------|------|
| DeerFlow 2.0 Agent 框架 | ✓ 完成 | Optimizer Agent、DeerFlow 客户端 |
| Tools 注册表 | ✓ 完成 | 性能分析工具集 |
| Workflows 编排 | ✓ 完成 | 感知/诊断/修复/优化工作流 |
| AI Native API | ✓ 完成 | 对话式 API 端点 |
| Generative UI | ✓ 完成 | 动态仪表板前端组件 |
| 前端 ChatFirst UI | ✓ 完成 | 对话式主界面 |
| Agent 可视化 | ✓ 完成 | Agent 状态实时展示 |

### 5.2 待完善的功能和技术债 (TODO 列表)

| 任务 | 优先级 | 说明 |
|------|-------|------|
| **修复循环导入问题** | P0 | `registry.py` ↔ `performance_tools.py` |
| **修复 optimizer_agent 导入路径** | P0 | 使用绝对导入代替相对导入 |
| **增强 LLM 集成** | P1 | 完整的自然语言理解和生成 |
| **完善知识图谱** | P1 | 更丰富的节点类型和关系 |
| **添加单元测试** | P1 | 工具注册表和 Agent 模块 |
| **前端构建优化** | P2 | 代码分割，减少 bundle 大小 |
| **完善文档** | P2 | 部署指南、故障排查 |

### 5.3 下一步行动计划（按优先级排序）

**P0 - 立即执行 (本周)**:
1. 修复 `registry.py` 和 `performance_tools.py` 的循环导入问题
2. 修复 `optimizer_agent.py` 的导入路径
3. 验证所有 AI Native API 正常工作

**P1 - 高优先级 (下周)**:
1. 增强 LLM 集成，实现真正的自然语言理解
2. 添加全面的单元测试
3. 完善知识图谱功能

**P2 - 中优先级 (本月)**:
1. 前端构建优化
2. 完善文档和部署指南
3. 性能优化和压力测试

---

## 6. 快速启动指南

### 6.1 环境配置要求

**最低要求**:
- Python 3.9+
- Node.js 16+
- Redis (可选，用于缓存)
- InfluxDB (可选，用于时序数据)

**推荐配置**:
- Python 3.10+
- Node.js 18+
- 4GB+ RAM
- 2 核 CPU+

### 6.2 依赖安装步骤

**后端**:
```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform/ai-runtime-optimizer

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

**前端**:
```bash
cd frontend

# 安装依赖
npm install

# 或使用 yarn
yarn install
```

### 6.3 启动命令

**启动后端**:
```bash
# 设置环境变量（可选）
export AI_OPTIMIZER_PORT=8009
export PYTHONPATH=/path/to/src

# 启动服务
python3 src/main.py

# 或使用 uvicorn 直接启动
uvicorn src.main:app --host 0.0.0.0 --port 8009
```

**启动前端 (开发模式)**:
```bash
cd frontend
npm run dev

# 访问 http://localhost:3009
```

**启动前端 (生产构建)**:
```bash
cd frontend
npm run build

# 构建输出到 dist/
```

### 6.4 API 测试方法

**健康检查**:
```bash
curl http://localhost:8009/health
```

**系统概览**:
```bash
curl http://localhost:8009/
```

**AI 自然语言问答**:
```bash
curl -X POST http://localhost:8009/api/ai/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "系统当前状态如何？"}'
```

**AI 深度诊断**:
```bash
curl -X POST http://localhost:8009/api/ai/diagnose \
  -H "Content-Type: application/json" \
  -d '{"service": "payment-service"}'
```

**动态仪表板**:
```bash
curl http://localhost:8009/api/ai/dashboard
```

**工具列表**:
```bash
curl http://localhost:8009/api/ai/tools
```

**自主运维循环**:
```bash
curl -X POST http://localhost:8009/api/ai/autonomous-loop \
  -H "Content-Type: application/json" \
  -d '{"service": "payment-service", "auto_execute": true}'
```

### 6.5 测试和验证

**运行单元测试**:
```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform/ai-runtime-optimizer
pytest tests/ -v
```

**运行演示脚本**:
```bash
python3 demo_ai_native.py
```

---

## 附录 A: 文件路径索引

```
ai-runtime-optimizer/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── deerflow_client.py         # DeerFlow 2.0 客户端
│   │   └── optimizer_agent.py         # 核心优化 Agent
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py                # 工具注册表
│   │   └── performance_tools.py       # 性能分析工具
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── optimizer_workflows.py     # 核心工作流
│   │   └── local_workflows.py         # 本地降级工作流
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ai_native.py               # AI Native API
│   │   ├── optimizer.py               # 基础优化 API
│   │   ├── p5_features.py             # P5 功能 API
│   │   ├── remediation.py             # 修复 API
│   │   ├── causal_inference.py        # 因果推断 API
│   │   ├── predictive_maintenance_v2.py
│   │   ├── observability_v24.py
│   │   └── ai_optimization_v25.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── storage.py
│   │   ├── storage_redis.py
│   │   ├── storage_timeseries.py
│   │   ├── anomaly_detector.py
│   │   ├── anomaly_enhanced.py
│   │   ├── ai_root_cause.py
│   │   ├── ai_optimization.py
│   │   ├── alert_engine.py
│   │   ├── alert_enhanced.py
│   │   ├── audit.py
│   │   ├── causal_inference.py
│   │   ├── execution_engine_v2.py
│   │   ├── knowledge_graph.py
│   │   ├── llm_integration.py
│   │   ├── observability_engine.py
│   │   ├── predictive_maintenance.py
│   │   ├── predictive_maintenance_v2.py
│   │   ├── remediation_engine.py
│   │   ├── root_cause_analysis.py
│   │   ├── security.py
│   │   ├── service_map.py
│   │   ├── strategy_engine.py
│   │   └── tracing.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── metrics/
│   │   ├── logs/
│   │   └── tracing/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── signals.py
│   │   ├── analysis.py
│   │   ├── strategy.py
│   │   └── remediation.py
│   ├── middleware/
│   ├── repositories/
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   ├── pages/
│   │   ├── store/
│   │   ├── services/
│   │   ├── types/
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── styles/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── tests/
│   └── test_ai_native.py
├── examples/
├── sdk/
├── .env.example
├── requirements.txt
├── pytest.ini
├── start.sh
├── AI_NATIVE_REDESIGN_WHITEPAPER.md   # AI Native 重设计白皮书
├── AI_NATIVE_COMPLETION_REPORT.md     # AI Native 转型完成报告
├── AI_NATIVE_FRONTEND_COMPLETION_REPORT.md
├── TEST_REPORT.md                     # 测试报告
└── PROJECT_DOCUMENTATION.md           # 本文档
```

---

## 附录 B: 配置参考

### 环境变量

```bash
# 基本配置
AI_OPTIMIZER_PORT=8009
AI_OPTIMIZER_DEBUG=true

# LLM 配置（可选）
LLM_ENABLED=true
LLM_PROVIDER=openai  # 或 anthropic
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-4

# 存储配置
STORAGE_TYPE=memory  # 或 redis, influxdb
REDIS_URL=redis://localhost:6379
INFLUXDB_URL=http://localhost:8086

# DeerFlow 配置
DEERFLOW_ENABLED=true
DEERFLOW_BASE_URL=http://localhost:8000
DEERFLOW_FALLBACK_ENABLED=true
```

---

**文档维护者**: AI Assistant
**最后审查**: 2026-04-07
**下次更新**: 功能变更时自动更新
