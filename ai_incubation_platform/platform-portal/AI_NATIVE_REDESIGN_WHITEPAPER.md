# AI Native 重设计白皮书

**项目**: platform-portal
**版本**: v3.0.0 AI Native Redesign (DeerFlow 2.0)
**日期**: 2026-04-06
**状态**: 重设计提案

---

## 执行摘要

platform-portal 是 AI Incubation Platform 的统一入口门户，负责整合所有子项目的访问入口和用户体验。本白皮书定义基于 DeerFlow 2.0 的 AI Native 门户架构。

---

## 第一部分：愿景重定义

### 1.1 新愿景

**新愿景**: **"AI 统一入口门户，用户通过自然语言对话访问所有子项目能力"**

**愿景解读**:
- **AI 是前台接待**: 统一接待用户请求，分发给对应子项目
- **AI 是导航员**: 理解用户意图，推荐合适的子项目
- **AI 是协调员**: 跨项目工作流自动编排

---

## 第二部分：DeerFlow 2.0 架构设计

### 2.1 Agent 设计

**Agent 名称**: PortalAgent (门户智能体)

**核心职责**:
- 意图识别：分析用户需求属于哪个子项目领域
- 路由分发：将请求转发到对应子项目 Agent
- 跨项目编排：协调多个子项目完成复杂任务

**工具注册表**:

```python
TOOLS_REGISTRY = {
    "identify_intent": {
        "name": "identify_intent",
        "description": "识别用户意图属于哪个子项目",
        "input_schema": {...}
    },
    "route_to_project": {
        "name": "route_to_project",
        "description": "路由请求到对应子项目",
        "input_schema": {...}
    },
    "aggregate_results": {
        "name": "aggregate_results",
        "description": "聚合多个子项目的结果",
        "input_schema": {...}
    },
    "cross_project_workflow": {
        "name": "cross_project_workflow",
        "description": "执行跨项目工作流",
        "input_schema": {...}
    }
}
```

### 2.2 核心工作流

**意图识别与路由工作流**:
1. 接收用户请求 → 2. LLM 意图分析 → 3. 匹配子项目 → 4. 路由请求 → 5. 聚合结果 → 6. 返回响应

**跨项目协作工作流**:
例如：用户说"我想创业"→ 同时调用：
- ai-opportunity-miner: 发现商机
- ai-hires-human: 发布任务找人
- ai-community-buying: 寻找团购资源

---

## 第三部分：项目结构

```
platform-portal/
├── src/
│   ├── agents/
│   │   ├── portal_agent.py
│   │   └── router_agent.py
│   ├── tools/
│   │   ├── intent_tools.py
│   │   └── routing_tools.py
│   ├── workflows/
│   │   ├── routing_workflows.py
│   │   └── cross_project_workflows.py
│   └── frontend/
│       └── chat_interface.py  # 统一对话界面
└── tests/
```

---

## 第四部分：实施清单

| 任务 | 优先级 | 预计工时 |
|------|-------|---------|
| 创建意图识别工具 | P0 | 2 天 |
| 创建路由工具 | P0 | 2 天 |
| 创建跨项目工作流 | P0 | 3 天 |
| 创建统一对话界面 | P1 | 3 天 |
| 集成测试 | P0 | 2 天 |
| **合计** | | **12 天** |

---

*本白皮书基于 DeerFlow 2.0 框架设计。*
