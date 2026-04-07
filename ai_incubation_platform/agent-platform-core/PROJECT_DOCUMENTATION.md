# Agent Platform Core 项目文档

**项目名称**: agent-platform-core
**版本**: v3.0.0 - DeerFlow 2.0 Core Framework
**最后更新**: 2026-04-06
**状态**: ✅ 核心功能完成

---

## 1. 执行摘要

### 1.1 项目定位和核心价值主张

**agent-platform-core** 是 AI Incubation Platform 的**核心框架层**，为所有子项目提供统一的 Agent 基础设施和 DeerFlow 2.0 集成能力。

**核心价值**:
- **统一 DeerFlow 客户端**: 所有子项目共享的 AI 服务接入层
- **标准化接口**: 工具注册表、审计日志、配置管理的统一规范
- **降级容错**: DeerFlow 不可用时的自动降级和本地执行能力
- **企业级功能**: 审计追溯、密钥管理、限流控制、异常处理

### 1.2 AI Native 成熟度等级

**当前等级**: **L3 - 代理层** (部分 L4 特征)

| 维度 | 评估 | 依据 |
|------|------|------|
| 自主性测试 | ✅ L3 | AI 作为核心决策引擎，支持多步工作流编排 |
| 对话优先测试 | ⚠️ L2 | 提供对话接口框架，但需上层应用实现 |
| Generative UI | ❌ L1 | 作为框架层不直接提供 UI 能力 |
| 主动感知 | ⚠️ L2 | 提供健康检查和降级模式，但推送机制需上层实现 |
| 架构模式 | ✅ L4 | `Agent + Tools` 模式，AI 服务位于核心 |

### 1.3 关键成就和里程碑

- ✅ **DeerFlow 2.0 完整实现** (~1,200 行代码)
  - 客户端封装、自动重试、降级模式
  - 工作流编排引擎（支持 DAG、并行、条件分支）
- ✅ **工具系统** (~1,270 行代码)
  - 工具基类、注册表、装饰器
  - 输入验证、限流控制、执行统计
- ✅ **审计日志系统** (~1,050 行代码)
  - 异步写入、脱敏处理、保留策略
  - 查询过滤、报告生成、导出功能
- ✅ **配置与密钥管理** (~800 行代码)
  - 多来源配置加载（文件、环境变量）
  - 密钥加密存储、轮换、过期管理
- ✅ **统一异常处理** (~600 行代码)
  - 14 种具体异常类型
  - 标准化错误响应格式
- ✅ **测试覆盖**: 9/9 测试通过 (100%)

---

## 2. 项目现状

### 2.1 技术架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    platform-portal (统一入口)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  agent-platform-core                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    DeerFlow Layer                         │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │   │
│  │  │   client.py  │ │ workflow.py  │ │ fallback.py  │      │   │
│  │  │  客户端封装   │ │ 工作流引擎    │ │ 降级模式     │      │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     Tools Layer                           │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │   │
│  │  │   base.py    │ │ registry.py  │ │ decorators.py│      │   │
│  │  │   工具基类    │ │ 工具注册表    │ │ 工具装饰器   │      │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     Audit Layer                           │   │
│  │  ┌──────────────┐ ┌──────────────┐                       │   │
│  │  │  models.py   │ │  logger.py   │                       │   │
│  │  │  数据模型     │ │  日志记录器   │                       │   │
│  │  └──────────────┘ └──────────────┘                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     Config Layer                          │   │
│  │  ┌──────────────┐ ┌──────────────┐                       │   │
│  │  │ settings.py  │ │ secrets.py   │                       │   │
│  │  │  配置管理     │ │  密钥管理     │                       │   │
│  │  └──────────────┘ └──────────────┘                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     Utils Layer                           │   │
│  │  ┌──────────────┐ ┌──────────────┐                       │   │
│  │  │ logging.py   │ │ exceptions.py│                       │   │
│  │  │  日志工具     │ │  异常处理     │                       │   │
│  │  └──────────────┘ └──────────────┘                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────┬───────┼───────┬─────────────┐
        ▼             ▼       ▼       ▼             ▼
  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
  │ ai-hires  │ │ community │ │ employee  │ │ 其他子项目 │
  └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

### 2.2 核心功能模块清单

| 模块 | 文件 | 代码行数 | 功能描述 |
|------|------|----------|----------|
| **DeerFlow** | | | |
| | `deerflow/client.py` | ~436 行 | DeerFlow 2.0 客户端封装 |
| | `deerflow/workflow.py` | ~496 行 | 工作流编排引擎 |
| | `deerflow/fallback.py` | ~405 行 | 降级模式实现 |
| **Tools** | | | |
| | `tools/base.py` | ~391 行 | 工具基类定义 |
| | `tools/registry.py` | ~385 行 | 工具注册表 |
| | `tools/decorators.py` | ~430 行 | 工具装饰器 |
| **Audit** | | | |
| | `audit/models.py` | ~407 行 | 审计数据模型 |
| | `audit/logger.py` | ~475 行 | 审计日志记录器 |
| **Config** | | | |
| | `config/settings.py` | ~413 行 | 统一配置管理 |
| | `config/secrets.py` | ~515 行 | 密钥管理 |
| **Utils** | | | |
| | `utils/logging.py` | ~378 行 | 统一日志工具 |
| | `utils/exceptions.py` | ~454 行 | 统一异常处理 |

### 2.3 数据模型和数据库设计

#### 核心数据模型

**1. DeerFlow 响应模型** (`DeerFlowResponse`)
```python
@dataclass
class DeerFlowResponse:
    success: bool              # 是否成功
    data: Any                  # 响应数据
    error: Optional[str]       # 错误信息
    trace_id: Optional[str]    # 追踪 ID
    latency_ms: float          # 延迟 (毫秒)
    is_fallback: bool          # 是否降级执行
```

**2. 工具执行结果** (`ToolResult`)
```python
@dataclass
class ToolResult:
    success: bool              # 是否成功
    data: Any                  # 返回数据
    error: Optional[str]       # 错误信息
    status: ToolStatus         # 执行状态
    execution_time_ms: float   # 执行时间
    request_id: Optional[str]  # 请求 ID
```

**3. 审计日志** (`AuditLog`)
```python
@dataclass
class AuditLog:
    id: str                    # 唯一标识
    actor: str                 # 执行者 ID
    action: str                # 操作类型
    resource: str              # 资源标识
    resource_type: AuditResourceType  # 资源类型
    request: Dict              # 请求数据 (脱敏)
    response: Dict             # 响应数据 (脱敏)
    status: AuditLogStatus     # 状态
    trace_id: str              # 追踪 ID
    start_time: float          # 开始时间
    end_time: Optional[float]  # 结束时间
    duration_ms: float         # 执行时长
```

**4. 密钥条目** (`SecretEntry`)
```python
@dataclass
class SecretEntry:
    name: str                  # 密钥名称
    value: str                 # 密钥值 (加密存储)
    secret_type: SecretType    # 密钥类型
    expires_at: Optional[float]# 过期时间
    metadata: Dict             # 元数据
    tags: List[str]            # 标签
```

#### 存储设计

| 组件 | 存储类型 | 说明 |
|------|----------|------|
| 审计日志 | Memory/File | 默认内存存储，支持文件持久化 (JSONL 格式) |
| 密钥存储 | Memory/File/ENV | 支持内存、文件、环境变量三种存储方式 |
| 工具注册表 | Memory | 运行时注册，进程重启后重置 |
| 配置管理 | Memory | 启动时加载，支持热更新 |

### 2.4 API 路由和服务接口

#### DeerFlow 客户端接口

```python
class DeerFlowClient:
    # 初始化
    def __init__(
        self,
        api_key: Optional[str] = None,
        fallback_enabled: bool = True,
        retry_config: Optional[RetryConfig] = None,
        audit_logger: Optional[Any] = None,
        timeout: float = 30.0
    )

    # 工作流
    async def run_workflow(name: str, **kwargs) -> DeerFlowResponse
    async def _run_local_workflow(name: str, **kwargs) -> Dict

    # 工具管理
    def register_tool(name: str, handler: Callable, description: str = "", ...)
    def unregister_tool(name: str)
    def list_tools() -> List[Dict[str, str]]
    async def execute_tool(name: str, **kwargs) -> DeerFlowResponse

    # 连接管理
    async def connect() -> bool
    async def disconnect()

    # 属性
    @property
    def status() -> ClientStatus
    @property
    def is_connected() -> bool
    @property
    def is_degraded() -> bool
```

#### 工作流引擎接口

```python
class WorkflowEngine:
    # 工作流管理
    def register_workflow(name: str, description: str = "", ...) -> WorkflowDefinition
    def unregister_workflow(name: str) -> bool
    def get_workflow(name: str) -> Optional[WorkflowDefinition]
    def list_workflows() -> List[Dict[str, str]]

    # 节点管理
    def register_node_handler(name: str, handler: Callable)

    # 执行
    async def execute(workflow_name: str, initial_context: Dict = None,
                     timeout: Optional[float] = None) -> WorkflowExecution

    # 执行实例管理
    def get_execution(execution_id: str) -> Optional[WorkflowExecution]
    def cancel_execution(execution_id: str) -> bool
```

#### 工具注册表接口

```python
class ToolsRegistry:
    # 工具管理
    def register(name: str, handler: Union[BaseTool, Callable],
                description: str, input_schema: Dict, ...)
    def unregister(name: str) -> bool
    def get(name: str) -> Optional[ToolRegistration]
    def list_tools() -> List[Dict[str, Any]]
    def search_tools(query: str) -> List[Dict[str, Any]]

    # 执行
    async def execute(name: str, context: Optional[ToolContext] = None,
                     **kwargs) -> ToolResult

    # 统计
    def get_stats(tool_name: Optional[str] = None) -> Dict[str, Any]
    def clear_rate_limits()
```

#### 审计日志接口

```python
class AuditLogger:
    # 日志记录
    async def log(actor: str, action: str, resource: str, ...) -> AuditLog

    # 查询
    async def query(query: Optional[AuditQuery] = None, **kwargs) -> List[AuditLog]
    async def get_by_id(log_id: str) -> Optional[AuditLog]
    async def get_by_trace(trace_id: str) -> List[AuditLog]

    # 报告
    async def generate_report(start_time: float, end_time: float, ...) -> AuditReport
    async def get_stats(time_range: Optional[tuple] = None) -> Dict[str, Any]
    async def export_logs(format: str = "json", ...) -> str

    # 管理
    async def close()
    def clear()
```

---

## 3. AI Native 特性分析

### 3.1 对话式交互实现

**框架层支持**:
- `DeerFlowClient` 提供统一的对话接口
- `ToolContext` 支持自然语言参数传递
- 工具注册表支持 AI 发现 (`list_tools()`, `search_tools()`)

**示例**:
```python
# 工具发现 (供 AI 使用)
tools = registry.search_tools("search")
# 返回: [{"name": "search_users", "description": "...", "relevance": 5.0}]

# 工具执行上下文
context = ToolContext(
    user_id="user123",
    metadata={"intent": "find_user_by_name"}
)
result = await registry.execute("search_users", query="john")
```

### 3.2 自主代理能力

**工作流编排**:
- 支持声明式工作流定义
- DAG 依赖图自动解析
- 条件分支和并行执行
- 超时和自动重试

**示例 - 链式工作流**:
```python
# 定义 ETL 工作流
workflow = engine.register_workflow("data_pipeline")
extract_id = workflow.add_node("extract", handler=extract_fn)
transform_id = workflow.add_node(
    "transform",
    handler=transform_fn,
    dependencies=[extract_id]
)
load_id = workflow.add_node(
    "load",
    handler=load_fn,
    dependencies=[transform_id]
)

# 自主执行
execution = await engine.execute("data_pipeline")
print(f"完成：{execution.status}, 耗时：{execution.duration}ms")
```

**降级自主性**:
```python
# 自动降级判断
if fallback_manager.should_fallback():
    result = await fallback_manager.execute(
        primary_func=call_deerflow,
        fallback_func=local_execute,
        cache_key="workflow_123"
    )
```

### 3.3 Generative UI 支持

**框架层能力**:
- 动态工具注册 (运行时添加/删除)
- 灵活的结果封装 (`ToolResult`, `DeerFlowResponse`)
- 结构化数据输出 (JSON 格式)

**为上层应用提供的原始能力**:
```python
# 工具信息 (可供 UI 动态渲染)
tool_info = {
    "name": "search_users",
    "description": "Search users by name",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
    }
}
```

### 3.4 主动感知和推送机制

**健康检查**:
```python
# DeerFlow 健康检查
status = await fallback_manager.health_check()
print(f"降级状态：{status['is_degraded']}")
print(f"DeerFlow 可用：{status['deerflow_available']}")
```

**降级模式自动切换**:
| 模式 | 行为 |
|------|------|
| `DISABLED` | 不使用降级，直接失败 |
| `LOCAL_ONLY` | 仅本地执行 |
| `HYBRID` | 混合模式，优先 DeerFlow，失败时降级 |
| `CACHED` | 使用缓存结果 |

**审计告警** (通过报告生成):
```python
# 生成审计报告
report = await logger.generate_report(
    start_time=time.time() - 86400,  # 过去 24 小时
    end_time=time.time()
)
print(f"错误数：{report.failed_count}")
print(f"慢操作数：{len(report.slow_operations)}")
```

---

## 4. 长远目标和愿景

### 4.1 L5 专家级 AI Native 愿景

**目标架构**:
```
┌─────────────────────────────────────────────────────────────┐
│                    AI-Native Agent Core                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              自主决策层 (Autonomous Decision)          │   │
│  │  - 意图理解与任务拆解                                 │   │
│  │  - 多 Agent 协作编排                                   │   │
│  │  - 置信度评估与自主执行                               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              工具执行层 (Tool Execution)              │   │
│  │  - 动态工具发现与组合                                 │   │
│  │  - 执行路径优化                                       │   │
│  │  - 容错与降级                                         │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              感知反馈层 (Perception & Feedback)       │   │
│  │  - 环境状态感知                                       │   │
│  │  - 执行结果评估                                       │   │
│  │  - 持续学习与优化                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**L5 特征**:
- **完全自主**: AI 能够独立理解模糊需求并拆解为可执行任务
- **多 Agent 协作**: 多个专业 Agent 协同完成复杂任务
- **持续学习**: 从历史执行中学习优化策略
- **情境感知**: 理解上下文并动态调整行为

### 4.2 平台生态规划

**子项目集成架构**:
```
                    ┌─────────────────┐
                    │  platform-portal│
                    │   (统一入口)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │agent-platform-  │
                    │     core        │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │ai-hires │        │community│        │employee │
    │  Human  │        │ Buying  │        │Platform │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                   ┌────────▼────────┐
                   │  共享能力层      │
                   │ - 工具注册表     │
                   │ - 审计日志       │
                   │ - 配置管理       │
                   │ - 密钥管理       │
                   └─────────────────┘
```

**能力输出**:
- **工具标准化**: 所有子项目使用统一的工具接口
- **审计统一**: 跨项目操作追溯和关联分析
- **配置集中**: 共享配置和密钥管理
- **降级容错**: 统一的服务可用性保障

### 4.3 商业模式演进路径

| 阶段 | 目标 | 能力 |
|------|------|------|
| **L1-L2** (当前) | 基础设施完善 | 工具注册、工作流、审计 |
| **L3** (短期) | 自主代理能力 | 多步任务编排、条件执行 |
| **L4** (中期) | 个性化学习 | 用户偏好记忆、行为优化 |
| **L5** (长期) | 领域专家 | 行业知识沉淀、决策建议 |

---

## 5. 执行计划和路线图

### 5.1 已完成的功能清单

| 模块 | 功能 | 状态 |
|------|------|------|
| **DeerFlow** | 客户端封装 | ✅ 完成 |
| | 工作流编排引擎 | ✅ 完成 |
| | 降级模式实现 | ✅ 完成 |
| | 自动重试机制 | ✅ 完成 |
| **Tools** | 工具基类 | ✅ 完成 |
| | 工具注册表 | ✅ 完成 |
| | 工具装饰器 | ✅ 完成 |
| | 输入验证 | ✅ 完成 |
| | 限流控制 | ✅ 完成 |
| **Audit** | 审计日志记录 | ✅ 完成 |
| | 审计查询过滤 | ✅ 完成 |
| | 审计报告生成 | ✅ 完成 |
| | 日志脱敏 | ✅ 完成 |
| **Config** | 配置管理 | ✅ 完成 |
| | 密钥管理 | ✅ 完成 |
| | 密钥轮换 | ✅ 完成 |
| **Utils** | 日志工具 | ✅ 完成 |
| | 异常处理 | ✅ 完成 |

### 5.2 待完善的功能和技术债 (TODO)

#### 高优先级 (P0)

- [ ] **数据库持久化**: 审计日志当前为内存存储，需支持数据库持久化
- [ ] **Redis 集成**: 缓存后端和分布式限流支持
- [ ] **OpenTelemetry**: 分布式追踪集成

#### 中优先级 (P1)

- [ ] **多租户隔离**: 支持多租户数据隔离
- [ ] **配置中心同步**: 与远程配置中心同步
- [ ] **密钥轮换通知**: Webhook 通知机制

#### 低优先级 (P2)

- [ ] **性能监控**: 关键指标监控和告警
- [ ] **文档完善**: API 参考文档和使用指南
- [ ] **基准测试**: 性能基准测试和优化

### 5.3 下一步行动计划

| 序号 | 任务 | 优先级 | 预计工时 | 依赖 |
|------|------|--------|----------|------|
| 1 | 添加 SQLite/PostgreSQL 审计存储 | P0 | 2 天 | - |
| 2 | Redis 缓存集成 | P0 | 2 天 | - |
| 3 | OpenTelemetry 追踪 | P1 | 3 天 | - |
| 4 | 多租户隔离支持 | P1 | 3 天 | 1 |
| 5 | 配置中心同步 | P1 | 2 天 | - |
| 6 | 性能监控和告警 | P2 | 2 天 | 3 |

---

## 6. 快速启动指南

### 6.1 环境配置要求

**系统要求**:
- Python 3.8+
- 内存: 512MB 以上
- 磁盘: 100MB 可用空间

**可选依赖**:
- Redis (缓存和限流)
- PostgreSQL/SQLite (审计日志持久化)

### 6.2 依赖安装步骤

```bash
# 进入项目目录
cd agent-platform-core

# 安装依赖
pip install -r requirements.txt

# 可选：安装 DeerFlow (如需 AI 功能)
# pip install deerflow>=2.0.0

# 可选：安装 Redis 支持
# pip install redis>=4.0.0

# 可选：安装 PostgreSQL 支持
# pip install asyncpg>=0.28.0
```

### 6.3 启动命令

**基本使用**:
```python
# 1. 初始化 DeerFlow 客户端
from deerflow import DeerFlowClient

client = DeerFlowClient(
    api_key="your-deerflow-api-key",  # 可选
    fallback_enabled=True,
    timeout=30.0
)

# 2. 初始化工具注册表
from tools import ToolsRegistry

registry = ToolsRegistry()

# 3. 注册工具
@registry.register(
    name="hello",
    description="Say hello",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        },
        "required": ["name"]
    }
)
async def say_hello(name: str) -> dict:
    return {"message": f"Hello, {name}!"}

# 4. 执行工具
import asyncio

async def main():
    result = await registry.execute("hello", name="World")
    print(result.to_dict())

asyncio.run(main())
```

**完整示例**:
```python
import asyncio
from deerflow import DeerFlowClient, WorkflowEngine
from tools import ToolsRegistry, BaseTool, ToolContext, ToolResult
from audit import AuditLogger
from config import Settings, SecretsManager

async def main():
    # 1. 初始化组件
    client = DeerFlowClient(fallback_enabled=True)
    registry = ToolsRegistry()
    audit_logger = AuditLogger()
    workflow_engine = WorkflowEngine()

    # 2. 定义工具
    class SearchTool(BaseTool):
        name = "search"
        description = "Search for items"
        input_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }

        async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
            # 实现搜索逻辑
            return ToolResult.ok(data={"results": [...]})

    # 3. 注册工具
    registry.register("search", SearchTool(),
                     description="Search for items",
                     input_schema=SearchTool.input_schema)

    # 4. 定义工作流
    workflow = workflow_engine.register_workflow("search_pipeline")
    workflow.add_node("search", handler=lambda ctx: registry.execute("search", query=ctx.get("query")))

    # 5. 执行工作流
    execution = await workflow_engine.execute("search_pipeline",
                                              initial_context={"query": "test"})
    print(f"工作流完成：{execution.status}")

    # 6. 生成审计报告
    report = await audit_logger.generate_report(
        start_time=0,
        end_time=time.time()
    )
    print(f"审计统计：{report.to_dict()}")

asyncio.run(main())
```

### 6.4 配置管理

**环境变量配置**:
```bash
# 基本配置
export AGENT_APP_ENV=development
export AGENT_LOG_LEVEL=INFO
export AGENT_PORT=8000

# DeerFlow 配置
export AGENT_DEERFLOW_API_KEY=your-api-key
export AGENT_DEERFLOW_API_URL=https://api.deerflow.ai

# 审计配置
export AGENT_AUDIT_ENABLED=true
export AGENT_AUDIT_RETENTION_DAYS=30

# 密钥配置
export AGENT_SECRET_KEY=your-secret-key
export SECRETS_STORE_TYPE=memory  # memory/file/env
```

**配置文件** (`config.yaml`):
```yaml
app_name: my-agent-app
app_env: development
port: 8000
debug: true

deerflow:
  api_key: ${DEERFLOW_API_KEY}
  timeout: 30.0
  max_retries: 3

audit:
  enabled: true
  retention_days: 30
  storage_type: file
  storage_path: ./logs/audit
```

### 6.5 API 测试方法

**运行测试**:
```bash
# 运行完整测试套件
python test_core.py

# 运行简化测试
python test_simple.py

# 使用 pytest
pytest -v --asyncio-mode=auto
```

**预期输出**:
```
**************************************************
Agent Platform Core 测试套件
**************************************************

==================================================
测试导入...                                    [OK]
测试配置管理...                                 [OK]
测试密钥管理...                                 [OK]
测试审计日志...                                 [OK]
测试工具系统...                                 [OK]
测试工作流引擎...                               [OK]
测试降级模式...                                 [OK]
测试 DeerFlow 客户端...                         [OK]
测试异常处理...                                 [OK]

==================================================
测试结果：9 通过，0 失败
==================================================
```

**手动测试**:
```python
# 测试工具注册和执行
from tools import ToolsRegistry, ToolContext, ToolResult

registry = ToolsRegistry()

# 注册测试工具
async def test_tool(x: int, y: int) -> dict:
    return {"sum": x + y}

registry.register(
    name="add",
    handler=test_tool,
    description="Add two numbers",
    input_schema={
        "type": "object",
        "properties": {
            "x": {"type": "integer"},
            "y": {"type": "integer"}
        },
        "required": ["x", "y"]
    }
)

# 执行测试
import asyncio

async def test():
    result = await registry.execute("add", x=5, y=3)
    assert result.success == True
    assert result.data["sum"] == 8
    print("测试通过!")

asyncio.run(test())
```

---

## 附录

### A. 文件结构

```
agent-platform-core/
├── deerflow/
│   ├── __init__.py          # 模块入口，导出核心类
│   ├── client.py            # DeerFlow 客户端封装
│   ├── workflow.py          # 工作流编排引擎
│   └── fallback.py          # 降级模式实现
│
├── tools/
│   ├── __init__.py          # 模块入口
│   ├── base.py              # 工具基类
│   ├── registry.py          # 工具注册表
│   └── decorators.py        # 工具装饰器
│
├── audit/
│   ├── __init__.py          # 模块入口
│   ├── models.py            # 审计数据模型
│   └── logger.py            # 审计日志记录器
│
├── config/
│   ├── __init__.py          # 模块入口
│   ├── settings.py          # 配置管理
│   └── secrets.py           # 密钥管理
│
├── utils/
│   ├── __init__.py          # 模块入口
│   ├── logging.py           # 日志工具
│   └── exceptions.py        # 异常处理
│
├── src/
│   └── __init__.py          # 包入口，统一导出
│
├── test_core.py             # pytest 集成测试
├── test_simple.py           # 独立单元测试
├── requirements.txt         # 依赖清单
├── AI_NATIVE_REDESIGN_WHITEPAPER.md  # AI Native 白皮书
├── AI_NATIVE_COMPLETION_REPORT.md    # 完成报告
└── PROJECT_DOCUMENTATION.md          # 本文档
```

### B. 代码统计

| 类别 | 文件数 | 代码行数 |
|------|--------|----------|
| DeerFlow 层 | 4 | ~1,337 |
| Tools 层 | 4 | ~1,206 |
| Audit 层 | 3 | ~882 |
| Config 层 | 3 | ~928 |
| Utils 层 | 3 | ~832 |
| 测试文件 | 2 | ~1,000 |
| **总计** | **19** | **~6,185** |

### C. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v3.0.0 | 2026-04-06 | DeerFlow 2.0 完整实现 |
| v2.0.0 | - | 初始版本 |

### D. 相关文档

- [AI Native 白皮书](./AI_NATIVE_REDESIGN_WHITEPAPER.md)
- [完成报告](./AI_NATIVE_COMPLETION_REPORT.md)
- [DEERFLOW_V2_AGENT_ARCHITECTURE.md](../DEERFLOW_V2_AGENT_ARCHITECTURE.md)

---

*文档生成时间：2026-04-07*
*版本号：v3.0.0*
