# AI Code Understanding - 项目完整文档

**版本**: v3.0 AI Native (DeerFlow 2.0)
**最后更新**: 2026-04-06
**状态**: AI Native 转型完成

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

**AI Code Understanding** 是一个 AI Native 代码理解平台，让 AI 成为每个开发者的**首席代码理解官**。

**核心价值主张**:
- **对话式代码理解**: 通过自然语言与 AI 协作，理解代码库、架构设计和调用关系
- **动态可视化**: 根据用户意图动态生成依赖图、流程图、序列图等可视化视图
- **自主代码分析**: AI 主动发现架构问题、代码坏味道和潜在风险
- **引用溯源**: 所有 AI 输出都附带代码引用，杜绝幻觉

### 1.2 AI Native 成熟度等级

**当前等级**: **L3 (代理级)** ✅

| 等级 | 名称 | 状态 | 说明 |
|------|------|------|------|
| L1 | 工具 | ✅ 达到 | AI 作为工具被调用 |
| L2 | 助手 | ✅ 达到 | AI 提供主动建议 |
| L3 | 代理 | ✅ 达到 | AI 自主规划执行 |
| L4 | 伙伴 | ⏸️ 待实现 | AI 持续学习成长 |
| L5 | 专家 | 🔮 长期愿景 | AI 领域超越人类 |

**评估依据**:
- ✅ **对话式交互**: Chat-first API，支持自然语言输入和流式输出
- ✅ **自主规划**: 多步工作流编排（理解→检索→分析→解释→验证）
- ✅ **Generative UI**: 根据意图动态生成可视化视图
- ✅ **置信度阈值**: 输出附带置信度评分和引用溯源
- ⏸️ **持续学习**: 用户偏好记忆系统待实现

### 1.3 关键成就和里程碑

| 里程碑 | 日期 | 状态 |
|--------|------|------|
| P0: 基础代码理解能力 | 2026-04-02 | ✅ 完成 |
| P3: 依赖图与 Git 集成 | 2026-04-03 | ✅ 完成 |
| P5: CLI 与监控指标 | 2026-04-04 | ✅ 完成 |
| P6: 知识图谱 | 2026-04-05 | ✅ 完成 |
| P8: 代码审查功能 | 2026-04-06 | ✅ 完成 |
| P9: 文档问答 | 2026-04-06 | ✅ 完成 |
| **AI Native 转型** | 2026-04-06 | ✅ 完成 |

---

## 2. 项目现状

### 2.1 技术架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI Code Understanding v3.0                │
├─────────────────────────────────────────────────────────────────┤
│  交互层 (Interaction Layer)                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Web Frontend   │  │  CLI Tool       │  │  API Gateway    │ │
│  │  React + Vite   │  │  Click-based    │  │  FastAPI        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  AI 代理层 (Agent Layer) - DeerFlow 2.0                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Code Agent      │  │ Workflows       │  │ Tools Registry  │ │
│  │ 意图识别 + 执行   │  │ 多步编排        │  │ 8 个核心工具     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  服务层 (Service Layer)                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Understanding Service (核心业务逻辑)                       │ │
│  │ - 代码解释 · 模块摘要 · 语义问答 · 全局地图 · 影响分析      │ │
│  └───────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  核心能力层 (Core Capabilities)                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ Indexer     │ │ Global Map  │ │ Task Guide  │ │  Dependency│ │
│  │ 索引管线    │ │ 全局地图    │ │ 任务引导    │ │  依赖图谱  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ Knowledge   │ │ Git         │ │ LSP         │ │ Halluci-  │ │
│  │ Graph       │ │ Integration │ │ Integration │ │ nation Ctrl││
│  │ 知识图谱    │ │ Git 集成    │ │ LSP 支持    │ │ 幻觉控制  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  基础设施层 (Infrastructure)                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ Tree-sitter │ │ ChromaDB    │ │ OpenAI API  │ │ Embedding │ │
│  │ 代码解析    │ │ 向量存储    │ │ LLM 调用    │ │ 模型      │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心功能模块清单

#### 2.2.1 Agents 层

| 模块 | 文件路径 | 说明 |
|------|----------|------|
| `CodeUnderstandingAgent` | `src/agents/code_agent.py` | 代码理解 AI Agent，支持 DeerFlow 云端调用和本地降级 |
| `DeerFlowClient` | `src/agents/deerflow_client.py` | DeerFlow 2.0 客户端封装 |

#### 2.2.2 Tools 层

| 工具 | 方法名 | 说明 |
|------|--------|------|
| `index_project` | `index_project()` | 索引项目代码，构建向量索引和知识图谱 |
| `global_map` | `global_map()` | 生成全局代码地图（技术栈、分层、入口点） |
| `explain_code` | `explain_code()` | 解释代码片段 |
| `summarize_module` | `summarize_module()` | 生成模块摘要 |
| `search_code` | `search_code()` | 语义搜索代码 |
| `ask_codebase` | `ask_codebase()` | 代码库问答 |
| `get_dependency_graph` | `get_dependency_graph()` | 获取依赖图谱 |
| `analyze_change_impact` | `analyze_change_impact()` | 分析变更影响 |

#### 2.2.3 Workflows 层

| 工作流 | 类名 | 步骤 | 说明 |
|--------|------|------|------|
| `code_understanding` | `CodeUnderstandingWorkflow` | 5 步 | 解析意图→检索代码→分析结构→生成解释→验证 |
| `code_exploration` | `CodeExplorationWorkflow` | 3 步 | 扫描项目→发现模式→识别问题 |
| `impact_analysis` | `ImpactAnalysisWorkflow` | 3 步 | 定位文件→分析影响→生成报告 |

#### 2.2.4 API 层

| 端点 | 方法 | 说明 |
|------|------|------|
| `POST /api/chat/` | SSE 流式 | 对话式 API，支持流式输出 |
| `POST /api/chat/sync` | JSON | 同步对话接口 |
| `POST /api/generative-ui/generate` | JSON | 动态 UI 生成 |
| `GET /api/generative-ui/visualizer` | HTML | 可视化中心页面 |
| `POST /api/understanding/explain` | JSON | 代码解释 |
| `POST /api/understanding/summarize` | JSON | 模块摘要 |
| `POST /api/understanding/ask` | JSON | 代码库问答 |
| `GET /api/understanding/global-map` | JSON | 全局地图 |
| `GET /api/understanding/dependency-graph` | JSON | 依赖图谱 |
| `POST /api/understanding/analyze-change-impact` | JSON | 影响分析 |
| `POST /api/docs/generate/*` | JSON | 文档生成系列 API |
| `POST /api/doc-qa/ask` | JSON | 文档问答 |
| `POST /api/code-nav/go-to-definition` | JSON | 跳转定义 |
| `POST /api/code-nav/find-references` | JSON | 查找引用 |

#### 2.2.5 服务层

| 服务 | 文件路径 | 说明 |
|------|----------|------|
| `UnderstandingService` | `src/services/understanding_service.py` | 核心业务逻辑，封装所有代码理解能力 |
| `CodeReviewService` | `src/services/code_review_service.py` | 代码审查服务 |
| `DocGenerationService` | `src/services/doc_generation_service.py` | 文档生成服务 |
| `DocQaService` | `src/services/doc_qa_service.py` | 文档问答服务 |
| `CodeNavigationService` | `src/services/code_navigation_service.py` | 代码导航服务 |

### 2.3 数据模型和数据库设计

#### 2.3.1 向量数据库 (ChromaDB)

```
集合名：{project_name}

文档结构:
{
    "id": "<chunk_id>",
    "content": "<代码内容>",
    "metadata": {
        "file_path": "src/module/file.py",
        "language": "python",
        "start_line": 10,
        "end_line": 50,
        "chunk_type": "function",  // function, class, module, comment
        "symbols": ["ClassName", "function_name"],
        "ast_hash": "<AST 哈希值>",
        "embedding_cache_key": "<embedding 缓存键>"
    }
}
```

#### 2.3.2 知识图谱

```python
class KnowledgeGraphNode:
    node_id: str          # 节点唯一标识
    node_type: str        # file, class, function, variable
    name: str             # 节点名称
    file_path: str        # 所属文件
    start_line: int       # 起始行号
    end_line: int         # 结束行号
    symbols: List[str]    # 导出符号
    metadata: Dict        # 额外元数据

class KnowledgeGraphEdge:
    source_id: str        # 源节点
    target_id: str        # 目标节点
    edge_type: str        # imports, inherits, calls, defines, references
    metadata: Dict        # 边元数据
```

#### 2.3.3 依赖图谱

```python
class DependencyNode:
    file_path: str        # 文件路径
    module_name: str      # 模块名
    node_type: str        # module, package, entrypoint
    in_degree: int        # 被依赖数
    out_degree: int       # 依赖他人数
    symbols: List[str]    # 导出符号

class DependencyEdge:
    source: str           # 源模块
    target: str           # 目标模块
    edge_type: str        # import, from_import, relative_import
    symbols: List[str]    # 导入的具体符号
```

#### 2.3.4 API Key 存储

```json
{
    "api_keys": {
        "<api_key_hash>": {
            "name": "Key 名称",
            "created_at": "2026-04-06T00:00:00",
            "expires_at": "2026-05-06T00:00:00",
            "last_used": "2026-04-06T12:00:00",
            "usage_count": 100,
            "is_active": true
        }
    }
}
```

#### 2.3.5 索引状态存储

```
data/index_state/{project_name}/
├── indexed_files.json    # 已索引文件列表
├── file_hashes.json      # 文件哈希映射
└── processing_stats.json # 处理统计
```

### 2.4 API 路由和服务接口

#### 2.4.1 路由结构

```
src/api/
├── chat.py              # 对话式 API
├── generative_ui.py     # Generative UI API
├── understanding.py     # 代码理解核心 API
├── docs.py              # 文档生成 API
├── doc_qa.py            # 文档问答 API
└── code_navigation.py   # 代码导航 API
```

#### 2.4.2 核心 API 接口定义

```python
# 对话式 API 请求/响应
class ChatRequest(BaseModel):
    message: str
    project: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    type: str  # thinking, discovery, explanation, visualization, suggestion
    content: Any
    metadata: Optional[Dict[str, Any]] = None

# Generative UI 请求/响应
class UIViewRequest(BaseModel):
    intent: str       # explore, understand, modify, debug
    data_type: str    # flow, dependency, call, dataflow
    context: Optional[Dict[str, Any]] = None

# 代码理解 API
class ExplainRequest(BaseModel):
    code: str
    language: str = "python"
    context: Optional[str] = None

class ExplainResponse(BaseModel):
    summary: str
    detailed_explanation: str
    symbols: List[str]
    confidence: float
    citations: List[Dict]
```

---

## 3. AI Native 特性分析

### 3.1 对话式交互实现

#### 3.1.1 Chat-first 架构

```
用户输入 (自然语言)
       │
       ▼
┌─────────────────────────────────────┐
│ 1. 意图识别 (Intent Detection)      │
│    - 分类：explain/explore/search/ask│
│    - 实体提取：项目/模块/函数        │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 2. 工作流选择 (Workflow Selection)  │
│    - code_understanding             │
│    - code_exploration               │
│    - impact_analysis                │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 3. 流式响应 (SSE Streaming)         │
│    - thinking: 思考过程             │
│    - discovery: 发现信息            │
│    - explanation: 主要解释          │
│    - visualization: 可视化数据      │
│    - suggestion: 下一步建议         │
└─────────────────────────────────────┘
```

#### 3.1.2 流式事件类型

| 事件类型 | 说明 | 示例内容 |
|----------|------|----------|
| `thinking` | AI 思考过程 | "正在检索相关代码..." |
| `discovery` | 发现相关信息 | "找到 5 个相关代码片段" |
| `explanation` | 主要解释内容 | 代码解释文本 |
| `visualization` | 可视化数据 | 依赖图节点/边数据 |
| `suggestion` | 下一步建议 | ["查看相关函数定义", "分析模块结构"] |
| `done` | 回答完成 | - |
| `error` | 错误信息 | - |

#### 3.1.3 上下文保持

```python
# 聊天上下文存储 (TODO: 待实现持久化)
conversation_history = [
    {
        "role": "user",
        "content": "帮我理解这个项目的认证逻辑",
        "timestamp": "2026-04-06T10:00:00",
    },
    {
        "role": "assistant",
        "content": "认证流程如下...",
        "citations": [...],
        "timestamp": "2026-04-06T10:00:05",
    },
]
```

### 3.2 自主代理能力

#### 3.2.1 多步工作流编排

**代码理解工作流 (CodeUnderstandingWorkflow)**:

```
步骤 1: parse_intent
  └─ 分析用户请求，识别意图和关键实体

步骤 2: retrieve_code
  └─ 根据意图检索相关代码和信息

步骤 3: analyze_code
  └─ 分析代码结构和逻辑

步骤 4: generate_explanation
  └─ 生成自然语言解释

步骤 5: verify_and_suggest
  └─ 验证输出准确性并生成建议
```

#### 3.2.2 自主探索能力

**代码探索工作流 (CodeExplorationWorkflow)**:

```
步骤 1: scan_project
  └─ 扫描项目结构，生成全局地图

步骤 2: discover_patterns
  └─ 发现架构模式（如多层架构、分布式入口点）

步骤 3: identify_issues
  └─ 识别潜在问题（置信度<0.7 的模式标记为问题）
```

#### 3.2.3 影响分析能力

**影响分析工作流 (ImpactAnalysisWorkflow)**:

```
步骤 1: locate_file
  └─ 定位目标文件

步骤 2: analyze_direct_impact
  └─ 分析直接影响（直接依赖该文件的模块）

步骤 3: generate_report
  └─ 生成影响报告（受影响文件/函数列表、风险等级、建议）
```

### 3.3 Generative UI 支持

#### 3.3.1 视图模板引擎

```python
VIEW_TEMPLATES = {
    ("explore", "dependency"): "dependency_graph_view",
    ("explore", "flow"): "code_flow_view",
    ("understand", "flow"): "sequence_diagram_view",
    ("understand", "dependency"): "architecture_map_view",
    ("modify", "dependency"): "dependency_impact_view",
    ("debug", "call"): "stack_trace_view",
    # ... 共 16 种视图模板
}
```

#### 3.3.2 可视化视图类型

| 视图类型 | 用途 | 布局 | 渲染组件 |
|----------|------|------|----------|
| `dependency_graph_view` | 依赖关系图 | 力导向布局 | D3 力导向图 |
| `code_flow_view` | 代码流程图 | 水平布局 | 流程图 |
| `architecture_map_view` | 架构图 | 分层布局 | 分层图 |
| `impact_analysis_view` | 影响分析图 | 径向布局 | 径向图 |
| `sequence_diagram_view` | 序列图 | 序列布局 | 序列图 |

#### 3.3.3 前端组件实现

```typescript
// DependencyGraph 组件核心功能
- D3 力导向布局
- 节点拖拽交互
- 缩放和平移控制
- 节点类型颜色编码
- 节点详情弹窗
- SVG 导出功能

// 节点类型映射
const NODE_COLORS = {
    module: "#3d9cf5",      // 蓝
    class: "#4caf50",       // 绿
    function: "#ff9800",    // 橙
    interface: "#9c27b0",   // 紫
    file: "#607d8b",        // 灰
    package: "#e91e63",     // 粉
};
```

### 3.4 主动感知和推送机制

#### 3.4.1 当前实现

- ✅ **流式响应推送**: 实时推送 AI 思考过程
- ✅ **发现事件通知**: 发现相关代码时推送通知
- ✅ **建议问题**: 回答完成后提供下一步建议

#### 3.4.2 待实现能力

- ⏸️ **主动问题发现**: AI 主动扫描代码库并报告潜在问题
- ⏸️ **代码变更通知**: 监听 Git 变更并自动触发影响分析
- ⏸️ **架构演进追踪**: 持续追踪项目架构变化并生成报告

---

## 4. 长远目标和愿景

### 4.1 L5 专家级 AI Native 愿景

**愿景陈述**:
> 让 AI 成为每个开发者的首席代码理解官，能够自主理解代码库、主动发现架构问题、动态生成解释文档，并在代码质量和技术决策上超越人类专家水平。

### 4.2 平台生态规划

```
AI Code Understanding 生态系统

┌─────────────────────────────────────────────────────────────┐
│                     核心平台                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AI 代码理解引擎                                     │   │
│  │  - 多语言支持 (Python, Java, TypeScript, Go...)     │   │
│  │  - 多模型路由 (OpenAI, Anthropic, 本地模型)          │   │
│  │  - 分布式索引 (支持超大型代码库)                     │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     扩展层                                   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │ VS Code   │ │ JetBrains │ │ CLI Tool  │ │ Web       │  │
│  │ 插件      │ │ 插件      │ │         │ │ Dashboard │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
├─────────────────────────────────────────────────────────────┤
│                     集成层                                   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │ GitHub    │ │ GitLab    │ │ Jira      │ │ Slack     │  │
│  │ Actions   │ │ CI/CD     │ │ 集成      │ │ 通知      │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
├─────────────────────────────────────────────────────────────┤
│                     数据层                                   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │ 代码知识  │ │ 用户偏好  │ │ 项目记忆  │ │ 技能库    │  │
│  │ 图谱      │ │ 学习      │ │ 库        │ │         │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 商业模式演进路径

| 阶段 | 模式 | 目标用户 | 核心功能 |
|------|------|----------|----------|
| **阶段 1** | 开源免费 | 个人开发者 | 基础代码理解、CLI 工具 |
| **阶段 2** | SaaS 订阅 | 中小企业 | 团队协作、私有部署、高级分析 |
| **阶段 3** | 企业授权 | 大型企业 | 本地部署、定制模型、SLA 保障 |
| **阶段 4** | 平台生态 | 全行业 | API 市场、插件生态、技能交易 |

---

## 5. 执行计划和路线图

### 5.1 已完成的功能清单

#### P0 阶段 - 基础能力
- [x] Tree-sitter 代码解析
- [x] 向量索引管线（ChromaDB）
- [x] 代码解释 API
- [x] 模块摘要生成
- [x] 代码库语义问答
- [x] 全局代码地图

#### P3 阶段 - 增强能力
- [x] 依赖图谱生成
- [x] Git 集成（差异索引）
- [x] 变更影响分析
- [x] LSP 符号解析

#### P5 阶段 - 工程化
- [x] CLI 命令行工具
- [x] 监控指标与链路追踪
- [x] API Key 认证
- [x] Markdown 格式化输出
- [x] 可视化界面（依赖图）

#### P6 阶段 - 知识图谱
- [x] 知识图谱构建
- [x] 知识图谱查询接口
- [x] 图谱可视化

#### P8 阶段 - 代码审查
- [x] 代码审查服务
- [x] 代码质量评估
- [x] 审查报告生成

#### P9 阶段 - 文档能力
- [x] 自动文档生成（API/架构/数据流/README）
- [x] 文档语义搜索
- [x] 文档问答（带引用溯源）
- [x] 代码导航辅助

#### AI Native 阶段 - DeerFlow 2.0 集成
- [x] CodeUnderstandingAgent
- [x] Tools 注册表（8 个工具）
- [x] Workflows 编排（3 个工作流）
- [x] 对话式 API（流式输出）
- [x] Generative UI 引擎
- [x] React 前端界面

### 5.2 待完善的功能和技术债

#### 高优先级 (P0)

| 编号 | 问题 | 影响 | 修复方案 |
|------|------|------|----------|
| BUG-001 | 后端端口配置不一致（8010 vs 8006） | API 调用失败 | 统一端口为 8006 |
| BUG-002 | 两个 agent 目录导致导入混乱 | 循环依赖风险 | 统一为 `src/agents/` |
| BUG-003 | Pydantic Field validate_default 使用不当 | 验证无效 | 改用 Annotated 语法 |

#### 中优先级 (P1)

| 编号 | 问题 | 影响 | 修复方案 |
|------|------|------|----------|
| BUG-004 | 重复的 sys.path.insert 调用 | 代码冗余 | 删除重复行 |
| BUG-005 | 日志记录器初始化不一致 | 日志格式不统一 | 统一使用 ObservableLogger |
| BUG-006 | DeerFlow 依赖缺失时错误提示不明确 | 用户体验差 | 添加安装指引 |
| BUG-007 | 聊天历史功能未实现 | 功能不可用 | 添加数据库表存储历史 |

#### 低优先级 (P2)

| 编号 | 问题 | 影响 | 修复方案 |
|------|------|------|----------|
| BUG-008 | Agent 状态显示步骤名称硬编码 | 进度信息不准确 | 动态接收步骤名称 |
| BUG-009 | 前端类型定义不完整（使用 any） | 类型安全降低 | 补充完整接口定义 |
| BUG-010 | 缺少数据库连接健康检查 | 无法及时发现连接问题 | 添加 ChromaDB 连接检查 |

### 5.3 下一步行动计划

#### 短期 (1-2 周)

| 任务 | 优先级 | 预计工时 | 负责人 |
|------|--------|----------|--------|
| 修复 BUG-001/002/003 | P0 | 2 小时 | 后端组 |
| 实现聊天历史持久化 | P0 | 4 小时 | 后端组 |
| 完善 Generative UI 组件 | P0 | 8 小时 | 前端组 |
| 添加更多视图模板（序列图、调用链） | P1 | 8 小时 | 前端组 |

#### 中期 (1 个月)

| 任务 | 优先级 | 预计工时 | 负责人 |
|------|--------|----------|--------|
| 实现用户偏好学习（学习代理） | P1 | 16 小时 | AI 组 |
| 添加主动问题发现功能 | P1 | 16 小时 | AI 组 |
| 集成 LSP 符号解析增强 | P1 | 8 小时 | 后端组 |
| 移动端适配 | P2 | 16 小时 | 前端组 |

#### 长期 (3 个月+)

| 任务 | 优先级 | 预计工时 | 负责人 |
|------|--------|----------|--------|
| 实现 L4 伙伴级能力（持续记忆） | P2 | 40 小时 | AI 组 |
| 多项目跨仓库分析 | P2 | 24 小时 | 后端组 |
| 自动修复建议生成 | P2 | 32 小时 | AI 组 |
| VS Code 插件开发 | P2 | 40 小时 | 工具组 |

---

## 6. 快速启动指南

### 6.1 环境配置要求

#### 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| Python | 3.9+ | 3.11+ |
| Node.js | 18+ | 20+ |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 2GB | 10GB+ |

#### 环境变量

```bash
# 必需配置
export OPENAI_API_KEY="sk-..."           # OpenAI API Key
export DEERFLOW_API_KEY="df-..."         # DeerFlow API Key (可选)

# 可选配置
export PORT=8010                         # 后端服务端口
export CHROMA_DB_PATH="./data/chroma"    # ChromaDB 存储路径
export LOG_LEVEL="INFO"                  # 日志级别
```

### 6.2 依赖安装步骤

#### 后端安装

```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 前端安装

```bash
cd frontend

# 安装依赖
npm install

# 开发模式构建
npm run build
```

### 6.3 启动命令

#### 启动后端服务

```bash
# 方式 1: 直接运行 main.py
python src/main.py

# 方式 2: 使用 uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8010 --reload

# 服务将在 http://localhost:8010 启动
# API 文档：http://localhost:8010/docs
```

#### 启动前端服务

```bash
cd frontend

# 开发模式（热重载）
npm run dev

# 生产模式
npm run build
npm run preview

# 前端将在 http://localhost:3006 启动
```

#### 使用 CLI 工具

```bash
# 查看帮助
python src/cli.py --help

# 解释代码
python src/cli.py explain --code 'def hello(): return "world"'

# 生成模块摘要
python src/cli.py summarize --file src/main.py

# 代码库问答
python src/cli.py ask --question "这个项目的认证逻辑是什么？"

# 生成全局地图
python src/cli.py global-map --project my_project

# 分析变更影响
python src/cli.py impact --file src/api/auth.py
```

### 6.4 API 测试方法

#### 使用 curl 测试

```bash
# 同步对话
curl -X POST http://localhost:8010/api/chat/sync \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "message": "帮我理解这个项目的认证逻辑",
    "project": "my_project"
  }'

# 流式对话（SSE）
curl -N http://localhost:8010/api/chat \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "解释这段代码"}'

# 生成动态 UI
curl -X POST http://localhost:8010/api/generative-ui/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "intent": "explore",
    "data_type": "dependency",
    "context": {"project_name": "my_project"}
  }'

# 代码解释
curl -X POST http://localhost:8010/api/understanding/explain \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "code": "def authenticate(user, password):...",
    "language": "python"
  }'

# 获取依赖图谱
curl http://localhost:8010/api/understanding/dependency-graph \
  -H "X-API-Key: your-api-key"
```

#### 使用 API 管理端点

```bash
# 查看 API Key 健康状态
curl http://localhost:8010/api/auth/health

# 创建新的 API Key
curl -X POST http://localhost:8010/api/auth/manage \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-admin-key" \
  -d '{"action": "create", "name": "Test Key", "expires_in_days": 30}'

# 列出所有 API Key
curl -X POST http://localhost:8010/api/auth/manage \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-admin-key" \
  -d '{"action": "list"}'

# 撤销 API Key
curl -X POST http://localhost:8010/api/auth/manage \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-admin-key" \
  -d '{"action": "revoke", "key": "key-to-revoke"}'
```

#### 使用 Swagger UI

```bash
# 访问 http://localhost:8010/docs
# 使用内置的 Swagger UI 进行交互式 API 测试
```

### 6.5 运行测试

```bash
# 运行 AI Native 集成测试
python test_ai_native.py

# 预期输出
# ==================================================================
# 测试结果汇总
# ==================================================================
#   [PASS] Agents 层
#   [PASS] Tools 层
#   [PASS] Workflows 层
#   [PASS] API 路由
#   [PASS] Generative UI
#   [PASS] DeerFlow 集成
#   [PASS] 工作流执行
#
# 总计：7/7 测试通过
```

---

## 附录

### A. 项目目录结构

```
ai-code-understanding/
├── src/
│   ├── agent/
│   │   ├── deerflow_runtime.py
│   │   ├── tools.py
│   │   └── workflows/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── code_agent.py
│   │   └── deerflow_client.py
│   ├── api/
│   │   ├── chat.py
│   │   ├── code_navigation.py
│   │   ├── doc_qa.py
│   │   ├── docs.py
│   │   ├── generative_ui.py
│   │   └── understanding.py
│   ├── core/
│   │   ├── dependency_graph/
│   │   ├── git_integration/
│   │   ├── global_map/
│   │   ├── hallucination_control/
│   │   ├── impact_analyzer/
│   │   ├── indexer/
│   │   ├── knowledge_graph/
│   │   ├── lsp_integration/
│   │   └── task_guide/
│   ├── middleware/
│   │   ├── auth.py
│   │   └── observability.py
│   ├── services/
│   │   ├── code_navigation_service.py
│   │   ├── code_review_service.py
│   │   ├── doc_generation_service.py
│   │   ├── doc_qa_service.py
│   │   └── understanding_service.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── code_tools.py
│   │   └── monorepo_indexer.py
│   ├── cli.py
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── data/
│   ├── chroma/
│   ├── index_state/
│   └── ast_index/
├── tests/
├── requirements.txt
├── test_ai_native.py
└── PROJECT_DOCUMENTATION.md
```

### B. 关键文件路径

| 文件 | 绝对路径 |
|------|----------|
| 主入口 | `/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding/src/main.py` |
| 核心服务 | `/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding/src/services/understanding_service.py` |
| Agent | `/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding/src/agents/code_agent.py` |
| 工作流 | `/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding/src/agent/workflows/code_workflows.py` |
| 对话 API | `/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding/src/api/chat.py` |
| Generative UI | `/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding/src/api/generative_ui.py` |
| 前端入口 | `/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding/frontend/src/main.tsx` |
| 依赖图组件 | `/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding/frontend/src/components/DependencyGraph.tsx` |

### C. 参考文档

- [AI Native 完成报告](./AI_NATIVE_COMPLETION_REPORT.md)
- [AI Native 重设计白皮书](./AI_NATIVE_REDESIGN_WHITEPAPER.md)
- [AI Native UI 实现报告](./AI_NATIVE_UI_IMPLEMENTATION.md)
- [测试报告](./test_report.md)

---

*文档生成时间：2026-04-06*
*AI Code Understanding v3.0*
