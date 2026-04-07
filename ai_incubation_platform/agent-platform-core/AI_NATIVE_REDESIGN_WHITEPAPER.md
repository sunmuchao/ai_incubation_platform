# AI Native 重设计白皮书

**项目**: agent-platform-core
**版本**: v3.0.0 AI Native Redesign (DeerFlow 2.0)
**日期**: 2026-04-06
**状态**: 重设计提案

---

## 执行摘要

agent-platform-core 是 AI Incubation Platform 的核心框架层，提供统一的 Agent 基础设施和 DeerFlow 2.0 集成能力。

---

## 第一部分：愿景重定义

### 1.1 新愿景

**新愿景**: **"统一的 Agent 基础设施框架，所有子项目共享的 DeerFlow 2.0 核心能力"**

**核心职责**:
- DeerFlow 2.0 客户端封装与降级模式
- 统一工具注册表基类
- 统一工作流编排引擎
- 统一审计日志组件
- 统一配置管理

---

## 第二部分：架构设计

### 2.1 核心组件

```
agent-platform-core/
├── deerflow/
│   ├── __init__.py
│   ├── client.py           # DeerFlow 客户端封装
│   ├── workflow.py         # 工作流编排引擎
│   └── fallback.py         # 降级模式实现
│
├── tools/
│   ├── __init__.py
│   ├── base.py             # 工具基类
│   ├── registry.py         # 工具注册表
│   └── decorators.py       # 工具装饰器
│
├── audit/
│   ├── __init__.py
│   ├── logger.py           # 审计日志记录器
│   └── models.py           # 审计数据模型
│
├── config/
│   ├── __init__.py
│   ├── settings.py         # 统一配置管理
│   └── secrets.py          # 密钥管理
│
└── utils/
    ├── __init__.py
    ├── logging.py          # 统一日志
    └── exceptions.py       # 统一异常
```

### 2.2 DeerFlow 客户端封装

```python
# deerflow/client.py
class DeerFlowClient:
    """
    DeerFlow 2.0 客户端封装

    功能:
    - 统一 API 密钥管理
    - 自动重试机制
    - 降级模式切换
    - 审计日志集成
    """

    def __init__(self, api_key: str = None, fallback: bool = True):
        self.api_key = api_key
        self.fallback_enabled = fallback
        self._client = self._init_client()

    def _init_client(self):
        """初始化 DeerFlow 客户端"""
        if self.api_key:
            try:
                from deerflow import Client
                return Client(api_key=self.api_key)
            except Exception:
                if self.fallback_enabled:
                    return None  # 降级模式
                raise
        return None

    async def run_workflow(self, name: str, **kwargs) -> dict:
        """运行工作流"""
        if self._client:
            return await self._client.run_workflow(name, **kwargs)
        else:
            return await self._run_local_workflow(name, **kwargs)

    def register_tool(self, name: str, handler: callable, ...):
        """注册工具"""
        pass
```

### 2.3 工具注册表基类

```python
# tools/registry.py
class ToolsRegistry:
    """
    统一工具注册表

    功能:
    - 工具注册与发现
    - 输入验证
    - 审计日志自动记录
    - 限流控制
    """

    def __init__(self):
        self._tools = {}
        self._audit_logger = AuditLogger()

    def register(self, name: str, handler: callable,
                 description: str, input_schema: dict,
                 requires_auth: bool = False,
                 audit_log: bool = True,
                 rate_limit: int = None):
        """注册工具"""
        pass

    async def execute(self, name: str, **kwargs) -> any:
        """执行工具"""
        # 1. 验证工具存在
        # 2. 验证输入
        # 3. 记录审计日志（如需要）
        # 4. 执行工具
        # 5. 返回结果
        pass

    def list_tools(self) -> list:
        """列出所有工具（供 AI 发现）"""
        pass
```

### 2.4 审计日志组件

```python
# audit/logger.py
class AuditLogger:
    """
    统一审计日志记录器

    功能:
    - 自动记录敏感操作
    - 支持多项目隔离
    - 支持追溯查询
    """

    async def log(self, actor: str, action: str, resource: str,
                  request: dict, response: dict, status: str,
                  trace_id: str = None):
        """记录审计日志"""
        pass

    async def query(self, actor: str = None, action: str = None,
                    resource: str = None, time_range: tuple = None) -> list:
        """查询审计日志"""
        pass
```

---

## 第三部分：与子项目关系

```
┌─────────────────────────────────────────────────────────────┐
│                    platform-portal                           │
│                    (统一入口)                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  agent-platform-core                         │
│                  (DeerFlow 2.0 核心)                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ DeerFlow    │ │ Tools       │ │ Audit       │           │
│  │ Client      │ │ Registry    │ │ Logger      │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────┬───────┼───────┬─────────────┐
        ▼             ▼       ▼       ▼             ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│ ai-hires  │ │ community │ │ employee  │ │ opportunity│
│  - Task   │ │  - Group  │ │  - Talent │ │  - Miner  │
│   Agent   │ │   Agent   │ │   Agent   │ │   Agent   │
└───────────┘ └───────────┘ └───────────┘ └───────────┘
```

---

## 第四部分：实施清单

| 任务 | 优先级 | 预计工时 |
|------|-------|---------|
| DeerFlow 客户端封装 | P0 | 2 天 |
| 工具注册表基类 | P0 | 2 天 |
| 审计日志组件 | P0 | 2 天 |
| 配置管理模块 | P1 | 1 天 |
| 单元测试 | P0 | 2 天 |
| 文档编写 | P2 | 1 天 |
| **合计** | | **10 天** |

---

## 第五部分：与全局架构对齐

根据 `/Users/sunmuchao/Downloads/ai_incubation_platform/DEERFLOW_V2_AGENT_ARCHITECTURE.md` 的定义，本项目提供：

1. **统一 DeerFlow 客户端**: 所有子项目共享
2. **统一工具注册表**: 标准化接口
3. **统一审计日志**: 跨项目追溯
4. **统一配置管理**: 集中式配置

---

*本白皮书定义了 agent-platform-core 的 DeerFlow 2.0 架构设计。*
