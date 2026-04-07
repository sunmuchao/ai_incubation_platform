# AI Native 重设计白皮书

**项目**: ai-hires-human
**版本**: v3.0.0 AI Native Redesign (DeerFlow 2.0)
**日期**: 2026-04-06
**状态**: 重设计提案

---

## 执行摘要

经过对现有 ai-hires-human 项目的全面分析，我发现了一个根本性问题：**当前项目是"AI-Enabled"而非"AI-Native"**。尽管有 27+ 个优先级功能、45+ 个 API 端点、完整的商业化路线图，但核心架构仍然是传统 CRUD + AI 调用的模式，AI 是"附加功能"而非"核心引擎"。

本白皮书提出彻底的 AI Native 重设计方案，将平台从"AI 发布任务 - 真人执行 - AI 验收"的工具型产品，转型为"AI 自主决策 - 人机协同执行 - AI 主导交付"的智能体平台。

---

## 第一部分：愿景重定义

### 1.1 原愿景的问题诊断

**原愿景**: "当 AI 要做一件事但做不到时，通过本平台雇佣真人执行，并把交付结果回传给上游 AI / Agent。"

**五问法根因分析**:

```
问题现象：现有架构不是 AI Native，而是 AI-Enabled

├─ 为什么 1: 为什么现有架构是 AI-Enabled 而非 AI-Native？
│  └─ 答：因为 AI 是被动响应（等待 API 调用），而非主动决策
│
├─ 为什么 2: 为什么 AI 是被动响应而非主动决策？
│  └─ 答：因为架构设计为 CRUD API + AI 服务调用模式
│
├─ 为什么 3: 为什么采用 CRUD + AI 调用模式？
│  └─ 答：因为设计时对标的是传统众包平台（MTurk、Upwork）
│
├─ 为什么 4: 为什么要对标传统众包平台？
│  └─ 答：因为团队对"AI Native"的理解停留在"有 AI 功能"层面
│
└─ 为什么 5: 为什么对 AI Native 的理解停留在表面？
   └─ 根本原因：缺乏对 AI Native 本质的系统性认知框架
      - AI Native 的本质是 AI 作为核心决策引擎，而非功能模块
      - 交互范式应从 GUI（图形界面）转向 LUI（语言界面）
      - 界面形态应从固定布局转向 Generative UI
```

**核心问题清单**:

| 维度 | 现状 | AI Native 要求 | 差距 |
|------|------|---------------|------|
| **AI 依赖测试** | 无 AI 时平台仍可用（人工发布任务） | AI 缺席时核心功能应失效 | ❌ 严重 |
| **自主性测试** | AI 被动响应 API 调用 | AI 主动建议/自主执行 | ❌ 严重 |
| **界面形态测试** | 固定布局（React + Ant Design） | 动态生成的 Generative UI | ❌ 严重 |
| **交互范式测试** | 表单 + 按钮操作 | 自然语言对话优先 | ❌ 严重 |
| **架构模式测试** | CRUD + AI 服务调用 | AI 为底层引擎，传统服务为辅助 | ❌ 严重 |

### 1.2 新愿景表述

**新愿景**: **"AI 自主雇佣真人完成物理世界任务的智能体平台"**

**愿景解读**:
- **AI 是雇主**：不是"AI 发布任务"，而是"AI 自主决定何时、为何、如何雇佣真人"
- **AI 是调度员**：不是"真人选择任务"，而是"AI 智能匹配并调度最优执行人"
- **AI 是验收官**：不是"AI 辅助验收"，而是"AI 主导验收，人类仅处理边缘案例"
- **界面是 AI 的延伸**：不是"固定布局供用户操作"，而是"AI 根据任务动态生成 UI"

### 1.3 AI 在新愿景中的角色

| 角色 | 描述 | 现有实现 | 新设计 |
|------|------|---------|--------|
| **决策引擎** | 决定是否发布任务、发布什么任务 | 人工决定 | AI 基于 capability gap 自主决策 |
| **调度中心** | 匹配最优工人、协调任务执行 | 推荐算法 | AI 自主调度，支持多人协作 |
| **验收主体** | 判定交付物质量、决定支付 | AI 辅助检查 | AI 主导验收，人类仲裁例外 |
| **界面生成器** | 动态生成任务界面、进度展示 | 固定布局 | Generative UI，因任务而异 |
| **对话伙伴** | 与雇主/工人自然语言交互 | 表单输入 | 对话优先，表单为辅 |

---

## 第二部分：核心交互重设计

### 2.1 首页重设计：从任务列表到 AI 对话

**现状**: 首页是任务市场列表，用户通过筛选器浏览任务。

**新设计**: 首页是 AI Agent 对话界面。

```
[Vision Alignment]
- AI 作为平台的"前台"，所有交互始于对话
- 任务列表不是起点，而是 AI 分析后的推荐结果
- 用户意图通过自然语言表达，AI 解析并执行

[Gap Analysis]
- 现有首页：/tasks 路由，TaskMarketPage 组件展示任务卡片列表
- 交互流程：用户打开页面 → 浏览列表 → 筛选 → 点击详情 → 操作
- 问题：用户需要主动寻找任务，AI 被动等待操作

[Technical Implementation]
- 新首页：/ 路由，ChatInterface 组件作为主界面
- AI Agent 能力：
  1. 意图识别：分析用户是雇主还是工人，想发布任务还是接任务
  2. 任务解析：从自然语言中提取任务要素（标题、描述、报酬等）
  3. 智能推荐：基于用户画像推荐任务或工人
  4. 自主执行：确认后可直接发布任务、接单、验收
```

**对话流设计示例**:

```
场景 1: AI 雇主发布任务

AI: "你好！我是你的 AI 任务助理。你今天想完成什么任务？"

用户: "我需要有人去北京市朝阳区拍摄 10 家奶茶店的价格"

AI: "好的，我理解你需要一个线下调研任务。让我确认一下细节：
     - 任务类型：线下拍照 + 数据采集
     - 地点：北京市朝阳区
     - 目标：10 家奶茶店的价格信息
     - 交付物：照片 + 价格表格

     我建议报酬设为 200 元，预计 24 小时内完成。
     需要我现在发布这个任务吗？"

用户: "好的，发布吧"

AI: "任务已发布！我已自动匹配了 3 位符合条件的工人，
     他们的平均评分 4.8，位置都在朝阳区附近。
     任务链接：[task://12345]
     你可以在这里查看进度，或者继续告诉我其他需求。"
```

```
场景 2: 工人接任务

用户: "我想接一些任务"

AI: "欢迎！根据你的技能标签（数据标注、内容审核、线下调研）
     和历史表现（完成率 98%，平均评分 4.9），
     我为你推荐以下任务：

     1. 门店价格调研（朝阳区）- 报酬 200 元 ⭐ 强烈推荐
        推荐理由：位置匹配、技能匹配、高报酬

     2. 数据标注任务（线上）- 报酬 50 元
        推荐理由：你的强项、可立即开始

     3. 内容审核（线上）- 报酬 80 元
        推荐理由：时间灵活、批量任务

     想接哪个任务？或者直接说'接第一个'？"

用户: "接第一个"

AI: "好的，你已成功接单！
     任务详情已发送到你手机。
     记得在 24 小时内完成并提交交付物哦~"
```

### 2.2 任务发布重设计：从表单到对话解析

**现状**: 雇主通过表单填写任务信息（标题、描述、报酬等字段）。

**新设计**: AI 通过多轮对话收集信息，自动填充并优化任务描述。

| 字段 | 现有方式 | 新设计 |
|------|---------|--------|
| 标题 | 文本输入框 | AI 从对话提取并优化 |
| 描述 | 多行文本框 | AI 追问细节后生成结构化描述 |
| 验收标准 | 手动列表输入 | AI 根据任务类型推荐标准模板 |
| 报酬 | 数字输入 | AI 基于市场数据建议合理价格 |
| 截止时间 | 日期选择器 | AI 根据任务复杂度推荐 |
| 技能要求 | 标签选择 | AI 自动分析任务需求推荐技能 |

### 2.3 任务匹配重设计：从搜索到 AI 自主调度

**现状**: 工人通过搜索、筛选找到任务，然后主动申请。

**新设计**: AI 主动推送匹配任务，支持"一键接单"和"自动派单"模式。

### 2.4 交付验收重设计：从人工提交到 AI 主导

**现状**: 工人提交交付物 → AI 智能验收检查 → 人工确认 → 支付

**新设计**: 工人提交 → AI 全自动验收 → AI 决定支付 → 例外转人工

---

## 第三部分：Generative UI 设计

### 3.1 界面动态生成原理

**现状**: 固定布局的 React 组件，所有页面预先定义。

**新设计**: AI 根据任务类型、用户角色、当前上下文动态生成 UI。

### 3.2 任务类型对应的 UI 模板

| 任务类型 | 动态生成的 UI 组件 |
|---------|------------------|
| **线下拍照** | 地图、照片墙、位置打卡器、时间戳显示 |
| **数据标注** | 标注工具、进度条、质量热图、快捷键提示 |
| **内容审核** | 内容预览、审核按钮组、原因选择器、批量操作 |
| **问卷调查** | 问卷预览、回收统计、数据可视化、导出按钮 |
| **文档处理** | 文档预览、编辑区、版本对比、批注工具 |

### 3.3 AI 思考过程可视化

设计方案：展示 AI 工作状态面板，让用户感知 AI 在主动工作。

---

## 第四部分：技术架构重设计

### 4.1 现有架构问题

**当前架构**: CRUD + AI 服务调用模式

问题诊断:
1. **AI 是附加层**: AI 服务位于业务服务之下，是可选的增强功能
2. **被动响应模式**: AI 等待 API 调用，不主动决策
3. **数据流单向**: 用户操作 → API → 服务 → AI → 数据库，AI 无自主性
4. **界面固定**: UI 与 AI 分离，AI 无法动态生成界面

### 4.2 新架构设计：AI 为底层引擎

新架构包含:
- **交互层（多模态）**: 对话界面、语音交互、Generative UI
- **AI Agent 编排层**: Task Agent、Matching Agent、Quality Agent、UI Agent
- **工具层（Tools）**: TaskTool、WorkerTool、PaymentTool、NotifyTool
- **数据持久层**: PostgreSQL、Redis、VectorDB

### 4.3 核心 Agent 设计

- **Task Agent**: 自主决策任务的发布与执行
- **Matching Agent**: 自主调度工人
- **Quality Agent**: 自主验收与支付
- **UI Agent**: 动态生成界面

---

## 第五部分：迁移路径

### 5.1 现有代码保留清单

**可保留的代码**（约 40%）:
- 数据模型（90% 保留）
- 工具层服务（70% 保留）
- 基础设施（100% 保留）
- API 层部分（30% 保留）

**必须重写的代码**（约 60%）:
- 主入口（架构范式变化）
- 任务服务（被动变主动）
- 匹配服务（推荐变调度）
- 前端页面（固定变动态）
- 交互流程（表单变对话）

### 5.2 迁移优先级

**阶段 1: AI 对话层（4 周）**
**阶段 2: Agent 核心能力（6 周）**
**阶段 3: Generative UI（4 周）**
**阶段 4: 自主性增强（持续）**

### 5.3 迁移节奏建议

第 1-2 周：原型验证
第 3-6 周：阶段 1 开发
第 7-12 周：阶段 2 开发
第 13-16 周：阶段 3 开发
第 17 周+：阶段 4 迭代

---

## 第六部分：对标 AI Native 竞品

### 6.1 竞品分析框架

**要对标**: Devin、Cursor、Character.ai（AI Native）

### 6.2 核心能力对标

| 能力 | Devin | Cursor | ai-hires-human 现状 | ai-hires-human 目标 |
|------|-------|--------|---------------------|---------------------|
| **自主决策** | ✅ | ✅ | ❌ | ✅ |
| **对话优先** | ✅ | ✅ | ❌ | ✅ |
| **Generative UI** | ⚠️ | ✅ | ❌ | ✅ |
| **AI 作为引擎** | ✅ | ✅ | ❌ | ✅ |

---

## 第七部分：原型设计

### 7.1 核心对话流原型

完整展示 AI 自主发布任务的对话流程。

### 7.2 关键界面文字原型

包含对话主界面和任务进度界面的设计。

### 7.3 API 端点重设计清单

现有 API 保留为 Tool 层，新增 AI Native 接口。

---

## 第八部分：风险与缓解

### 8.1 技术风险
### 8.2 产品风险
### 8.3 商业风险

---

## 第九部分：成功标准

### 9.1 产品指标
### 9.2 技术指标
### 9.3 商业指标

---

## 第十部分：总结与行动呼吁

### 10.1 核心发现

1. **现有项目是 AI-Enabled 而非 AI-Native**: AI 是附加功能，不是核心引擎
2. **架构需要根本性重构**: 从 CRUD+AI 变为 Agent+Tools
3. **交互范式需要转变**: 从表单按钮到对话优先
4. **界面需要动态化**: 从固定布局到 Generative UI

### 10.2 战略建议

**立即行动**:
1. 停止在现有架构上叠加新功能
2. 组建 AI Native 重构专项团队
3. 启动原型验证（2 周）

**3 个月目标**:
1. 完成对话层和 Task Agent 开发
2. 核心用户可体验 alpha 版本
3. 收集反馈并迭代

**6 个月目标**:
1. 完成全部 Agent 开发
2. Generative UI 上线
3. 正式发布 AI Native v2.0

### 10.3 最终愿景

从现在的"AI 辅助工具"转型为"AI 自主平台"。

---

*本白皮书由 AI 助手生成，用于指导 ai-hires-human 项目的 AI Native 重设计。*
*最后更新：2026-04-06*


---

## 第十一部分：DeerFlow 2.0 集成设计

### 11.1 架构选型

**统一 Agent 框架**: DeerFlow 2.0

根据 AI Incubation Platform 的统一架构标准，本项目采用 DeerFlow 2.0 作为 Agent 编排框架。

**选型理由**:
| 评估维度 | DeerFlow 2.0 | 自研 Agent 框架 | 其他开源框架 |
|---------|-------------|---------------|------------|
| 工具注册 | ✅ 内置 | ⚠️ 需开发 | ⚠️ 功能有限 |
| 工作流编排 | ✅ 声明式 | ⚠️ 需开发 | ⚠️ 复杂度高 |
| 审计日志 | ✅ 自动记录 | ⚠️ 需开发 | ❌ 不支持 |
| 降级模式 | ✅ 内置 | ⚠️ 需开发 | ❌ 不支持 |
| 学习曲线 | ✅ 低 | ⚠️ 高 | ⚠️ 中 |
| 平台统一 | ✅ 所有项目共用 | ❌ 各自为政 | ❌ 不统一 |

### 11.2 Agent 设计

**Agent 名称**: TaskAgent (任务智能体)

**核心职责**:
- 自主决策任务的发布时机
- 智能匹配并调度最优工人
- 主导验收与支付决策

**DeerFlow 工具注册表**:

```python
# src/tools/task_tools.py
TOOLS_REGISTRY = {
    "post_task": {
        "name": "post_task",
        "description": "发布新任务到任务市场",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "任务标题"},
                "description": {"type": "string", "description": "任务描述"},
                "reward": {"type": "number", "description": "报酬金额"},
                "deadline": {"type": "string", "format": "date-time"}
            },
            "required": ["title", "description", "reward"]
        }
    },
    "match_workers": {
        "name": "match_workers",
        "description": "为任务匹配最优工人",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"},
                "limit": {"type": "integer", "description": "返回数量", "default": 10}
            },
            "required": ["task_id"]
        }
    },
    "verify_delivery": {
        "name": "verify_delivery",
        "description": "验收交付物并决定是否支付",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "submission_id": {"type": "string"},
                "auto_approve": {"type": "boolean", "default": true}
            },
            "required": ["task_id", "submission_id"]
        }
    }
}
```

### 11.3 工作流编排

**核心工作流**:

```python
# src/workflows/task_workflows.py
from deerflow import workflow, step

@workflow(name="auto_post_and_match")
class AutoPostAndMatchWorkflow:
    """
    自主发布任务并匹配工作流

    流程：
    1. 解析用户需求
    2. 发布任务
    3. 匹配工人
    4. 发送通知
    5. 记录审计
    """

    @step
    async def parse_intent(self, user_input: str) -> dict:
        """Step 1: 解析用户意图"""
        # 使用 LLM 提取任务要素
        pass

    @step
    async def post_task(self, parsed: dict) -> dict:
        """Step 2: 发布任务"""
        # 调用 post_task 工具
        pass

    @step
    async def match_workers(self, task_result: dict) -> dict:
        """Step 3: 匹配工人"""
        # 调用 match_workers 工具
        pass

    @step
    async def notify_workers(self, match_result: dict) -> dict:
        """Step 4: 通知工人"""
        # 发送通知
        pass

    @step
    async def audit_log(self, result: dict) -> dict:
        """Step 5: 记录审计"""
        # 自动记录操作日志
        pass
```

### 11.4 审计日志设计

**敏感操作自动记录**:

| 操作类型 | 审计字段 | 保留期限 |
|---------|---------|---------|
| 任务发布 | task_id, employer_id, reward, timestamp | 3 年 |
| 工人匹配 | task_id, worker_ids, match_score, timestamp | 3 年 |
| 验收决策 | task_id, submission_id, decision, reason | 永久 |
| 支付操作 | payment_id, amount, recipient, status | 永久 |

**数据库表结构**:

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    actor VARCHAR(100) NOT NULL,      -- 操作者 (用户 ID 或 Agent)
    action VARCHAR(100) NOT NULL,     -- 操作类型
    resource VARCHAR(200),            -- 操作资源 ID
    request TEXT,                     -- JSON 请求
    response TEXT,                    -- JSON 响应
    status VARCHAR(20) NOT NULL,      -- success/failure
    trace_id VARCHAR(100)             -- 追踪 ID
);

CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
```

### 11.5 降级模式

**DeerFlow 不可用时的降级策略**:

```python
# src/agents/task_agent.py
class TaskAgent:
    def __init__(self, deerflow_api_key: str = None):
        self.df_client = DeerFlowClient(api_key=deerflow_api_key)
        self.fallback_enabled = True

    async def run_workflow(self, name: str, **input_data):
        """运行工作流（支持降级）"""
        if self.df_client.is_available():
            return await self.df_client.run_workflow(name, **input_data)
        elif self.fallback_enabled:
            # 本地降级模式
            return await self._run_local_workflow(name, **input_data)
        else:
            raise RuntimeError("DeerFlow unavailable")
```

### 11.6 项目结构

**DeerFlow 2.0 标准结构**:

```
ai-hires-human/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── deerflow_client.py    # DeerFlow 客户端封装
│   │   └── task_agent.py         # TaskAgent 实现
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── task_tools.py         # 任务相关工具
│   │   ├── worker_tools.py       # 工人相关工具
│   │   └── payment_tools.py      # 支付相关工具
│   │
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── task_workflows.py     # 任务工作流
│   │   └── matching_workflows.py # 匹配工作流
│   │
│   ├── services/                 # 原有业务服务（保留）
│   └── api/                      # 原有 API 层（保留）
│
├── tests/
│   ├── test_agents.py
│   ├── test_tools.py
│   └── test_workflows.py
│
└── requirements.txt
```

### 11.7 实施清单

| 任务 | 优先级 | 预计工时 | 状态 |
|------|-------|---------|------|
| 安装 DeerFlow 2.0 | P0 | 0.5 天 | ⏸️ |
| 创建 tools 层 | P0 | 2 天 | ⏸️ |
| 创建工作流 | P0 | 2 天 | ⏸️ |
| 创建 Agent 层 | P0 | 2 天 | ⏸️ |
| 配置审计日志 | P1 | 1 天 | ⏸️ |
| 集成测试 | P0 | 2 天 | ⏸️ |
| 文档更新 | P2 | 1 天 | ⏸️ |
| **合计** | | **10.5 天** | |

---

*本白皮书基于 DeerFlow 2.0 框架重新设计，所有后续实现需遵循本文档定义的原则和架构。*
