# AI Native 重设计白皮书

**项目**: ai-employee-platform
**版本**: v3.0.0 AI Native Redesign (DeerFlow 2.0)
**日期**: 2026-04-06
**状态**: 重设计提案

---

## 执行摘要

经过对现有 ai-employee-platform 项目的全面分析，我们发现当前架构本质上是**"AI-Enabled"而非"AI-Native"**。尽管平台拥有完整的人才匹配、职业发展、绩效追踪等功能，但核心架构仍然是传统 CRUD + AI 服务调用模式。

本白皮书提出基于 **DeerFlow 2.0** 框架的 AI Native 重设计方案，将平台从"人才市场平台"转型为"AI 自主人才代理平台"。

---

## 第一部分：愿景重定义

### 1.1 新愿景

**新愿景**: **"AI 自主管理人才发展与组织匹配的智能体平台"**

**愿景解读**:
- **AI 是职业顾问**: 自主分析员工能力、规划发展路径
- **AI 是猎头顾问**: 自主匹配人才与机会（内部转岗/外部机会）
- **AI 是绩效教练**: 自主追踪绩效、提供改进建议
- **AI 是组织顾问**: 自主分析团队构成、提出优化建议

### 1.2 AI 角色重新定义

| 角色 | 旧设计 | 新设计 (DeerFlow 2.0) |
|------|-------|---------------------|
| 匹配引擎 | 被动响应用户搜索 | AI 主动推送匹配机会 |
| 职业顾问 | 提供课程推荐 | AI 自主规划发展路径并执行 |
| 绩效追踪 | 记录绩效数据 | AI 自主分析并提供改进建议 |
| 组织分析 | 生成静态报告 | AI 自主发现组织问题并建议 |

---

## 第二部分：DeerFlow 2.0 架构设计

### 2.1 统一 Agent 框架

根据 AI Incubation Platform 的统一标准，本项目采用 **DeerFlow 2.0** 作为 Agent 编排框架。

**选型理由**:
- 工具注册表：将 HR 操作封装为 AI 可调工具
- 工作流编排：多步人才管理流程自动化
- 审计日志：敏感 HR 操作自动记录
- 降级模式：DeerFlow 不可用时自动切换本地

### 2.2 Agent 设计

**Agent 名称**: TalentAgent (人才智能体)

**核心职责**:
- 自主分析员工能力画像
- 自主匹配人才与机会
- 自主规划职业发展路径
- 自主追踪绩效并提供建议

**DeerFlow 工具注册表**:

```python
# src/tools/talent_tools.py
TOOLS_REGISTRY = {
    "analyze_profile": {
        "name": "analyze_profile",
        "description": "分析员工能力画像",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string"},
                "include_projects": {"type": "boolean", "default": true}
            },
            "required": ["employee_id"]
        }
    },
    "match_opportunities": {
        "name": "match_opportunities",
        "description": "匹配人才与机会（转岗/晋升/项目）",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string"},
                "opportunity_type": {"type": "string", "enum": ["transfer", "promotion", "project"]},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["employee_id"]
        }
    },
    "plan_career": {
        "name": "plan_career",
        "description": "生成职业发展规划",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string"},
                "target_role": {"type": "string"},
                "timeframe_months": {"type": "integer", "default": 12}
            },
            "required": ["employee_id", "target_role"]
        }
    },
    "track_performance": {
        "name": "track_performance",
        "description": "追踪绩效并提供改进建议",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string"},
                "period": {"type": "string", "enum": ["weekly", "monthly", "quarterly"]}
            },
            "required": ["employee_id"]
        }
    },
    "analyze_team": {
        "name": "analyze_team",
        "description": "分析团队构成并提出优化建议",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string"},
                "analysis_type": {"type": "string", "enum": ["skills", "diversity", "performance"]}
            },
            "required": ["team_id"]
        }
    }
}
```

### 2.3 工作流编排

**核心工作流 1: 自主人才匹配**

```python
# src/workflows/talent_workflows.py
from deerflow import workflow, step

@workflow(name="auto_talent_match")
class AutoTalentMatchWorkflow:
    """
    自主人才匹配工作流

    流程：
    1. 分析员工画像
    2. 扫描可用机会
    3. 匹配度计算
    4. 生成推荐
    5. 发送通知
    6. 追踪反馈
    """

    @step
    async def analyze_employee(self, employee_id: str) -> dict:
        """Step 1: 分析员工画像"""
        pass

    @step
    async def scan_opportunities(self, profile: dict) -> dict:
        """Step 2: 扫描可用机会"""
        pass

    @step
    async def calculate_match(self, profile: dict, opportunities: list) -> dict:
        """Step 3: 匹配度计算"""
        pass

    @step
    async def generate_recommendations(self, matches: list) -> dict:
        """Step 4: 生成推荐"""
        pass

    @step
    async def notify_employee(self, employee_id: str, recommendations: list) -> dict:
        """Step 5: 发送通知"""
        pass

    @step
    async def track_feedback(self, notification_id: str) -> dict:
        """Step 6: 追踪反馈"""
        pass
```

**核心工作流 2: 自主职业发展**

```python
@workflow(name="auto_career_planning")
class AutoCareerPlanningWorkflow:
    """
    自主职业发展规划工作流

    流程：
    1. 识别职业目标
    2. 分析能力差距
    3. 生成发展计划
    4. 推荐学习资源
    5. 设置里程碑
    6. 定期追踪进度
    """

    @step
    async def identify_goal(self, employee_input: str) -> dict:
        """Step 1: 识别职业目标"""
        pass

    @step
    async def analyze_gap(self, employee_id: str, goal: dict) -> dict:
        """Step 2: 分析能力差距"""
        pass

    @step
    async def generate_plan(self, gap_analysis: dict) -> dict:
        """Step 3: 生成发展计划"""
        pass

    @step
    async def recommend_resources(self, plan: dict) -> dict:
        """Step 4: 推荐学习资源"""
        pass

    @step
    async def set_milestones(self, plan: dict) -> dict:
        """Step 5: 设置里程碑"""
        pass

    @step
    async def track_progress(self, employee_id: str, milestones: list) -> dict:
        """Step 6: 定期追踪进度"""
        pass
```

### 2.4 审计日志设计

**敏感 HR 操作自动记录**:

| 操作类型 | 审计字段 | 保留期限 |
|---------|---------|---------|
| 人才匹配 | employee_id, opportunity_id, match_score | 2 年 |
| 职业规划 | employee_id, plan_id, goal_changes | 5 年 |
| 绩效追踪 | employee_id, period, feedback_given | 3 年 |
| 团队分析 | team_id, analysis_type, recommendations | 2 年 |

**表结构**:

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    actor VARCHAR(100) NOT NULL,      -- 操作者 (HR/Manager/Agent)
    action VARCHAR(100) NOT NULL,     -- 操作类型
    resource VARCHAR(200),            -- 资源 ID (employee_id/team_id)
    request TEXT,                     -- JSON 请求
    response TEXT,                    -- JSON 响应
    status VARCHAR(20) NOT NULL,
    trace_id VARCHAR(100)
);

CREATE INDEX idx_audit_employee ON audit_logs(resource);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
```

---

## 第三部分：项目结构

### 3.1 DeerFlow 2.0 标准结构

```
ai-employee-platform/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── deerflow_client.py    # DeerFlow 客户端封装
│   │   └── talent_agent.py       # TalentAgent 实现
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── talent_tools.py       # 人才相关工具
│   │   ├── career_tools.py       # 职业发展工具
│   │   └── performance_tools.py  # 绩效管理工具
│   │
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── talent_workflows.py   # 人才匹配工作流
│   │   └── career_workflows.py   # 职业发展工作流
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

---

## 第四部分：实施清单

| 任务 | 优先级 | 预计工时 | 状态 |
|------|-------|---------|------|
| 安装 DeerFlow 2.0 | P0 | 0.5 天 | ⏸️ |
| 创建 tools 层 | P0 | 3 天 | ⏸️ |
| 创建工作流 | P0 | 2 天 | ⏸️ |
| 创建 Agent 层 | P0 | 2 天 | ⏸️ |
| 配置审计日志 | P1 | 1 天 | ⏸️ |
| 集成测试 | P0 | 2 天 | ⏸️ |
| **合计** | | **10.5 天** | |

---

## 第五部分：与平台架构对齐

根据 `/Users/sunmuchao/Downloads/ai_incubation_platform/DEERFLOW_V2_AGENT_ARCHITECTURE.md` 的定义，本项目遵循：

1. **统一工具注册表模式**: 所有业务操作封装为 Tools
2. **统一工作流编排**: 使用 DeerFlow 2.0 声明式工作流
3. **统一审计日志**: 敏感 HR 操作自动记录
4. **统一降级模式**: DeerFlow 不可用时自动切换本地

---

*本白皮书基于 DeerFlow 2.0 框架设计，所有后续实现需遵循本文档定义的原则和架构。*
