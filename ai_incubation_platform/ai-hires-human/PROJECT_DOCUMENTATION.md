# AI 灵活用工平台 (ai-hires-human) 项目文档

**版本**: v1.25.0 AI Native (DeerFlow 2.0)
**最后更新**: 2026-04-07
**状态**: 已实现 AI Native 架构转型

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [项目现状](#2-项目现状)
3. [AI Native 特性分析](#3-ai-native-特性分析)
4. [长远目标和愿景](#4-长远目标和愿景)
5. [执行计划和路线图](#5-执行计划和路线图)
6. [快速启动指南](#6-快速启动指南)
7. [附录](#附录)

---

## 1. 执行摘要

### 1.1 项目定位和核心价值主张

**ai-hires-human** 是一个 **AI Native 灵活用工平台**，核心理念是：

> **当 AI 要做一件事但做不到时（与真实世界交互、需肉身或人工签核），通过本平台雇佣真人完成，并把交付结果回传给上游 AI / Agent。**

**核心价值主张**:
- **AI 是雇主**: AI 自主决定何时、为何、如何雇佣真人
- **AI 是调度员**: AI 智能匹配并调度最优执行人
- **AI 是验收官**: AI 主导验收，人类仅处理边缘案例
- **对话式交互**: 用户通过自然语言与平台交互

### 1.2 当前 AI Native 成熟度等级

**当前等级**: **L3 - 代理级** (部分 L4 特性)

| 等级 | 名称 | 达成状态 | 关键特征 |
|------|------|---------|---------|
| L1 | 工具 | ✅ 已超越 | AI 被动响应 |
| L2 | 助手 | ✅ 已达成 | AI 主动建议 + 推送 |
| L3 | 代理 | ✅ 已达成 | AI 多步工作流自主执行 |
| L4 | 伙伴 | ⚠️ 部分实现 | 需要用户偏好记忆系统 |
| L5 | 专家 | ⏸️ 长期愿景 | AI 领域超越人类 |

**评估依据**:

| 维度 | 评估结果 | 说明 |
|------|---------|------|
| **AI 依赖测试** | ✅ 通过 | 无 AI 时核心功能（意图解析、智能匹配、自主验收）失效 |
| **自主性测试** | ✅ 通过 | 支持自动分配（置信度≥0.8）、自动验收（置信度≥0.9） |
| **对话优先测试** | ✅ 通过 | /api/chat 端点支持自然语言交互 |
| **架构模式测试** | ✅ 通过 | Agent + Tools + Workflows 架构 |
| **Generative UI** | ✅ 通过 | 前端支持 9 种动态 UI 组件类型 |

### 1.3 关键成就和里程碑

| 里程碑 | 版本 | 日期 | 状态 |
|--------|------|------|------|
| P0 基础任务发布/接单 | v0.1.0 | 2026-01 | ✅ 完成 |
| P1-P4 信誉体系/反作弊 | v0.9.0 | 2026-02 | ✅ 完成 |
| P5 迭代功能（仪表板/SLA） | v1.0.0 | 2026-02 | ✅ 完成 |
| P6 AI 杀手级功能（任务分解/智能验收） | v1.1.0 | 2026-03 | ✅ 完成 |
| P7 黄金标准测试 | v1.2.0 | 2026-03 | ✅ 完成 |
| P8 平台化功能（开放 API） | v1.3.0 | 2026-03 | ✅ 完成 |
| P9-P27 国际化/移动端/区块链等 | v1.4.0-v1.24.0 | 2026-03 | ✅ 完成 |
| **AI Native 架构转型** | v1.25.0 | 2026-04 | ✅ 完成 |

---

## 2. 项目现状

### 2.1 技术架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    ai-hires-human 架构                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Web 前端    │  │  移动端     │  │  Open API   │             │
│  │  (React)    │  │  (待开发)   │  │  开发者门户  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          │                                       │
│              ┌───────────▼───────────┐                          │
│              │   API Gateway 层       │                          │
│              │  (FastAPI + Middleware)│                          │
│              └───────────┬───────────┘                          │
│                          │                                       │
│     ┌────────────────────┼────────────────────┐                 │
│     │                    │                    │                  │
│     ▼                    ▼                    ▼                  │
│ ┌─────────┐      ┌─────────────┐     ┌─────────────┐            │
│ │  Chat   │      │  REST API   │     │  Webhooks   │            │
│ │  API    │      │  Endpoints  │     │  回调接口    │            │
│ └────┬────┘      └──────┬──────┘     └──────┬──────┘            │
│      │                  │                   │                    │
│      ▼                  ▼                   ▼                    │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │                   AI Agent 层                              │   │
│ │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │   │
│ │  │ TaskAgent   │  │ DeerFlow    │  │  Workflows  │        │   │
│ │  │ (核心引擎)  │  │  Client     │  │  编排层      │        │   │
│ │  └──────┬──────┘  └─────────────┘  └─────────────┘        │   │
│ │         │                                                   │   │
│ │         ▼                                                   │   │
│ │  ┌─────────────────────────────────────────┐               │   │
│ │  │            Tools 工具注册表              │               │   │
│ │  │  • Task Tools (5 个)                    │               │   │
│ │  │  • Worker Tools (5 个)                  │               │   │
│ │  │  • Verification Tools (6 个)            │               │   │
│ │  └─────────────────────────────────────────┘               │   │
│ └───────────────────────────────────────────────────────────┘   │
│                          │                                       │
│              ┌───────────▼───────────┐                          │
│              │   业务服务层           │                          │
│              │  (46 个 Services)      │                          │
│              └───────────┬───────────┘                          │
│                          │                                       │
│              ┌───────────▼───────────┐                          │
│              │   数据持久层           │                          │
│              │  PostgreSQL / SQLite   │                          │
│              │  Redis (缓存/会话)     │                          │
│              └───────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent/Tools/Workflows 三层架构详解

#### 2.2.1 Agents 层 (`/src/agents/`)

| 文件 | 行数 | 说明 |
|------|------|------|
| `__init__.py` | 8 | 模块导出 |
| `deerflow_client.py` | 176 | DeerFlow 客户端封装，支持降级模式 |
| `task_agent.py` | 333 | TaskAgent 核心实现 |

**TaskAgent 核心能力**:

```python
class TaskAgent:
    """任务代理 - AI Native 核心引擎"""

    # 1. 意图解析 - 从自然语言提取任务参数
    async def parse_intent(self, natural_language: str) -> Dict[str, Any]

    # 2. 从自然语言发布任务
    async def post_task_from_natural_language(self, user_id: str, natural_language: str, context: Optional[Dict] = None)

    # 3. 智能匹配工人（支持自动分配）
    async def match_workers_for_task(self, task_id: str, auto_assign: bool = False)

    # 4. 自主验收（高置信度时自动通过）
    async def verify_delivery(self, task_id: str, delivery_content: str, auto_approve_threshold: float = 0.9)

    # 5. 审计日志记录
    async def _log_audit(self, actor: str, action: str, resource: str, request: Dict, response: Dict, status: str)
```

**意图解析能力**:

| 提取字段 | 解析逻辑 | 示例 |
|---------|---------|------|
| 技能需求 | 关键词匹配（线下采集、数据标注等） | "线下拍照" → {"线下采集": "基础"} |
| 交互类型 | 检测"线下/实地/物理"等关键词 | "到北京现场" → physical |
| 优先级 | 检测"急/马上/尽快"等关键词 | "紧急任务" → urgent |
| 地点 | 提取城市名 | "北京" → location_hint="北京" |
| 报酬 | 正则提取数字 | "报酬 200 元" → reward_amount=200.0 |

**自主决策机制**:

```python
# 自动分配：置信度 >= 0.8 时自主执行
if auto_assign and result.get("matches"):
    best_match = result["matches"][0]
    if best_match.get("confidence", 0) >= 0.8:
        await self.run_tool("assign_worker", task_id=task_id, worker_id=best_match["worker_id"])
        result["auto_assigned"] = True

# 自动验收：置信度 >= 0.9 时自主通过
if result.get("confidence", 0) >= auto_approve_threshold:
    await self.run_tool("approve_task", task_id=task_id, reason=f"AI 验收通过（置信度：{result['confidence']:.2f}）")
    result["auto_approved"] = True
```

#### 2.2.2 Tools 层 (`/src/tools/`)

| 文件 | 行数 | 说明 |
|------|------|------|
| `__init__.py` | 15 | 工具注册表合并 |
| `task_tools.py` | 419 | 任务相关工具 |
| `worker_tools.py` | 442 | 工人相关工具 |
| `verification_tools.py` | 540 | 验证工具 |

**工具注册表完整列表** (共 16 个工具):

| 类别 | 工具函数 | 说明 |
|------|---------|------|
| **Task Tools** | `post_task` | 发布任务到平台 |
| | `get_task` | 获取任务详情 |
| | `search_tasks` | 多维度搜索任务 |
| | `cancel_task` | 取消任务 |
| | `get_task_stats` | 任务统计数据 |
| **Worker Tools** | `search_workers` | 搜索工人 |
| | `get_worker_profile` | 获取工人画像 |
| | `match_workers` | 智能匹配工人（带置信度） |
| | `assign_worker` | 分配工人 |
| | `get_worker_stats` | 工人统计 |
| **Verification Tools** | `verify_delivery` | 验证交付物质量 |
| | `check_anti_cheat` | 反作弊检查 |
| | `approve_task` | 批准任务完成 |
| | `reject_task` | 拒绝任务交付 |
| | `request_manual_review` | 请求人工复核 |
| | `get_quality_score` | 获取质量评分 |

#### 2.2.3 Workflows 层 (`/src/workflows/`)

| 文件 | 行数 | 说明 |
|------|------|------|
| `__init__.py` | 13 | 工作流导出 |
| `task_workflows.py` | 349 | 任务工作流 |
| `matching_workflows.py` | 373 | 匹配工作流 |

**核心工作流**:

| 工作流 | Steps | 说明 |
|--------|-------|------|
| `AutoPostAndMatchWorkflow` | 5 | 自主发布任务并匹配工人 |
| `AutoVerifyDeliveryWorkflow` | 5 | 自主验收交付物 |
| `SmartMatchingWorkflow` | 5 | 智能匹配工人（多维度评分） |
| `BatchMatchingWorkflow` | 3 | 批量任务匹配 |

**工作流执行流程示例**:

```
AutoPostAndMatchWorkflow:
1. parse_intent     → 解析用户自然语言意图
2. create_task      → 创建并发布任务
3. match_workers    → 智能匹配工人
4. auto_assign      → 自动分配（置信度 >= 0.8）
5. log_audit        → 记录审计日志

AutoVerifyDeliveryWorkflow:
1. get_delivery     → 获取任务和交付内容
2. verify_quality   → 验证交付物质量
3. check_anti_cheat → 执行反作弊检查
4. make_decision    → 自动决策（通过/拒绝/人工复核）
5. log_audit        → 记录审计日志
```

### 2.3 核心功能模块清单（按优先级 P0-P8+）

| 优先级 | 模块 | API 端点 | 状态 |
|--------|------|---------|------|
| **P0** | 基础任务管理 | `/api/tasks` | ✅ 完成 |
| | 工人画像 | `/api/workers` | ✅ 完成 |
| | 支付交易 | `/api/payment` | ✅ 完成 |
| **P1** | 反作弊（设备指纹） | `/api/anti-cheat` | ✅ 完成 |
| **P2** | 批量任务 | `/api/batch-tasks` | ✅ 完成 |
| | Escrow 资金托管 | `/api/escrow` | ✅ 完成 |
| **P3** | 信誉体系 | `/api/reputation` | ✅ 完成 |
| **P4** | 增强反作弊 | `/api/anti-cheat` | ✅ 完成 |
| **P5** | 数据仪表板 | `/api/dashboard` | ✅ 完成 |
| | 团队权限 | `/api/team` | ✅ 完成 |
| | SLA 服务协议 | `/api/sla` | ✅ 完成 |
| **P6** | AI 任务分解 | `/api/task-decomposition` | ✅ 完成 |
| | 智能验收 | `/api/intelligent-acceptance` | ✅ 完成 |
| | 质量预测 | `/api/quality-prediction` | ✅ 完成 |
| | AI 反作弊增强 | `/api/ai-anti-cheat` | ✅ 完成 |
| **P7** | 黄金标准测试 | `/api/golden-standard` | ✅ 完成 |
| **P8** | 开放 API | `/api/open` | ✅ 完成 |
| | 用户贡献数据 | `/api/contributions` | ✅ 完成 |
| **P9** | 国际化多语言 | `/api/i18n` | ✅ 完成 |
| **P10** | 高级分析预测 | `/api/analytics` | ✅ 完成 |
| **P11** | 移动端优化 | `/api/mobile` | ✅ 完成 |
| **P19** | 区块链存证 | `/api/blockchain` | ✅ 完成 |
| **P20** | 智能合约支付 | `/api/smart-contracts` | ✅ 完成 |
| **P21** | 团队匹配 | `/api/team-matching` | ✅ 完成 |
| **P22** | 争议预防 | `/api/dispute-prevention` | ✅ 完成 |
| | 质量改进建议 | `/api/quality-improvement` | ✅ 完成 |
| **P23** | 社交网络增强 | `/api/social` | ✅ 完成 |
| **P24** | 职业发展支持 | `/api/career` | ✅ 完成 |
| **P25** | 法律法规支持 | `/api/legal` | ✅ 完成 |
| **P26** | 隐私安全中心 | `/api/privacy-security` | ✅ 完成 |
| **P27** | 用户体验优化 | `/api/ux/*` | ✅ 完成 |
| **AI Native** | 对话式交互 | `/api/chat` | ✅ 完成 |

### 2.4 数据模型和数据库设计

**核心数据表** (基于 `/src/models/db_models.py`):

| 表名 | 实体 | 关键字段 |
|------|------|---------|
| `tasks` | 任务表 | id, ai_employer_id, title, description, status, reward_amount, worker_id, interaction_type, required_skills |
| `worker_profiles` | 工人画像 | worker_id, name, skills, level, rating, completed_tasks, total_earnings, location |
| `employer_profiles` | 雇主画像 | employer_id, name, total_tasks_posted, total_amount_paid |
| `payment_transactions` | 支付交易 | id, transaction_type, amount, payer_id, payee_id, task_id, status |
| `wallets` | 用户钱包 | user_id, balance, frozen_balance |
| `escrow_transactions` | 资金托管 | escrow_id, task_id, principal_amount, status, released_at |
| `golden_standard_tests` | 黄金标准测试 | test_id, task_id, questions, passing_score |
| `worker_test_attempts` | 测试尝试 | attempt_id, test_id, worker_id, score, passed |
| `worker_certifications` | 资格认证 | certification_id, worker_id, certification_type, level, status |
| `device_fingerprints` | 设备指纹 | fingerprint, user_id, ip_address, user_agent |
| `ip_records` | IP 记录 | ip_address, is_proxy, is_vpn, is_blacklisted |
| `behavioral_events` | 行为事件 | event_id, user_id, event_type, event_metadata |
| `audit_logs` | 审计日志 | actor, action, resource, request, response, status, trace_id |
| `task_templates` | 任务模板 | template_name, title_template, description_template |
| `user_language_preferences` | 语言偏好 | user_id, preferred_language |
| `task_translations` | 任务翻译 | task_id, language_code, translated_title |

**数据库配置**:
- 默认：SQLite (`sqlite+aiosqlite:///./test.db`)
- 生产：PostgreSQL (通过 `AI_HIRES_HUMAN_DATABASE_URL` 环境变量)
- 缓存/会话：Redis (可选)

### 2.5 API 路由和服务接口

**API 端点总数**: 45+ 个

**主要 API 路由**:

| 路由前缀 | 端点数量 | 功能 |
|---------|---------|------|
| `/api/tasks` | 5 | 任务管理 |
| `/api/workers` | 3 | 工人管理 |
| `/api/payment` | 4 | 支付管理 |
| `/api/escrow` | 3 | 资金托管 |
| `/api/dashboard` | 2 | 数据仪表板 |
| `/api/analytics` | 3 | 数据分析 |
| `/api/team` | 4 | 团队权限 |
| `/api/sla` | 2 | SLA 管理 |
| `/api/quality` | 3 | 质量控制 |
| `/api/golden-standard` | 4 | 黄金标准测试 |
| `/api/certifications` | 3 | 资格认证 |
| `/api/reputation` | 2 | 信誉体系 |
| `/api/task-decomposition` | 2 | AI 任务分解 |
| `/api/intelligent-acceptance` | 2 | 智能验收 |
| `/api/chat` | 3 | 对话式交互 |
| `/api/blockchain` | 2 | 区块链存证 |
| `/api/smart-contracts` | 3 | 智能合约 |
| `/api/social` | 5 | 社交网络 |
| `/api/career` | 4 | 职业发展 |
| `/api/legal` | 5 | 法律服务 |
| `/api/privacy-security` | 3 | 隐私安全 |
| `/api/ux/*` | 8 | 用户体验 |

**服务层模块** (46 个 Services):

```
src/services/
├── task_service.py              # 任务服务
├── worker_service.py            # 工人服务
├── payment_service.py           # 支付服务
├── escrow_service.py            # 资金托管服务
├── matching_service.py          # 匹配服务
├── quality_control_service.py   # 质量控制服务
├── anti_cheat_service.py        # 反作弊服务
├── notification_service.py      # 通知服务
├── analytics_service.py         # 分析服务
├── dashboard_service.py         # 仪表板服务
├── team_service.py              # 团队服务
├── sla_service.py               # SLA 服务
├── golden_standard_service.py   # 黄金标准服务
├── certification_service.py     # 认证服务
├── reputation_service.py        # 信誉服务
├── blockchain_proof_service.py  # 区块链存证服务
├── smart_contract_service.py    # 智能合约服务
├── social_service.py            # 社交服务
├── career_development_service.py# 职业发展服务
├── legal_services_service.py    # 法律服务
├── privacy_security_service.py  # 隐私安全服务
├── theme_service.py             # 主题服务
├── onboarding_service.py        # 新手引导服务
└── ... (共 46 个服务文件)
```

---

## 3. AI Native 特性分析

### 3.1 对话式交互实现（Chat-first）

**核心端点**: `/api/chat` (`/src/api/chat.py`)

**支持的意图类型**:

| 意图 | 触发关键词 | 处理函数 |
|------|-----------|---------|
| 发布任务 | "发布", "创建", "新建", "post", "create" + "任务" | `_handle_post_task` |
| 搜索任务 | "搜索", "查找", "找任务", "search" + "任务" | `_handle_search_tasks` |
| 搜索工人 | "工人", "师傅", "接单" + "搜索/查找/找" | `_handle_search_workers` |
| 查询状态 | "状态", "进度", "status" + "任务" | `_handle_get_task_status` |
| 匹配工人 | "匹配", "推荐", "match" + "工人" | `_handle_match_workers` |
| 验收交付 | "验收", "审核", "批准", "verify" | `_handle_verify_delivery` |
| 查看统计 | "统计", "数据", "报表" | `_handle_get_stats` |

**对话流示例**:

```
用户：帮我发布一个线下采集任务，需要到北京现场拍照，报酬 200 元

AI Agent 处理流程:
1. 解析意图 → 提取参数:
   - title: "线下采集任务 - 北京现场拍照"
   - description: "需要到北京现场拍照"
   - interaction_type: "physical"
   - location_hint: "北京"
   - reward_amount: 200.0
   - priority: "medium"

2. 调用 post_task 工具 → 创建任务

3. 返回响应:
   {
     "message": "任务已成功发布！任务 ID: xxx",
     "action": "post_task",
     "data": {"task_id": "xxx", ...},
     "suggestions": ["查看任务 xxx 的状态", "为任务 xxx 匹配工人"]
   }
```

### 3.2 自主代理能力（TaskAgent 自主决策）

**自主决策场景**:

| 场景 | 触发条件 | 自主行动 |
|------|---------|---------|
| 自动分配工人 | 匹配置信度 >= 0.8 | 调用 `assign_worker` 工具 |
| 自动验收通过 | 验证置信度 >= 0.9 | 调用 `approve_task` 工具 |
| 自动拒绝交付 | 作弊检测通过 | 调用 `reject_task` 工具 |
| 请求人工复核 | 置信度 < 0.6 | 调用 `request_manual_review` 工具 |

**置信度分级策略**:

```python
# 自动分配阈值
AUTO_ASSIGN_THRESHOLD = 0.8  # 80% 匹配度自动分配

# 自动验收阈值
AUTO_APPROVE_THRESHOLD = 0.9  # 90% 置信度自动通过
MANUAL_REVIEW_THRESHOLD = 0.6  # 60% 以下需要人工复核

# 决策逻辑
if confidence >= AUTO_APPROVE_THRESHOLD:
    decision = "approve"  # AI 自主决策
elif confidence >= MANUAL_REVIEW_THRESHOLD:
    decision = "approve"  # AI 决策但置信度较低
else:
    decision = "manual_review"  # 转人工
```

### 3.3 Generative UI 支持

**前端实现**: `/frontend/src/components/GenerativeUI.tsx`

**支持的 UI 组件类型**:

| Action 类型 | 生成组件 | 描述 |
|------------|---------|------|
| `search_tasks` | TaskList | 任务列表表格 |
| `search_workers` | WorkerList | 工人列表卡片 |
| `post_task` | TaskCreated | 任务发布成功卡片 |
| `match_workers` | MatchResults | 匹配结果展示 |
| `get_task_status` | TaskStatus | 任务状态详情 |
| `get_stats` | DashboardStats | 统计数据仪表板 |
| `verify_delivery` | VerificationResult | 验证结果展示 |
| `notification` | NotificationPanel | 通知提醒 |
| `team_match` | TeamComposition | 团队组成展示 |

**置信度颜色编码**:

```typescript
const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return '#52c41a';  // 高 - 绿色
  if (confidence >= 0.6) return '#1890ff';  // 中 - 蓝色
  if (confidence >= 0.4) return '#faad14';  // 低 - 黄色
  return '#ff4d4f';                          // 极低 - 红色
};
```

### 3.4 主动感知和推送机制

**通知类型** (`/frontend/src/components/NotificationPanel.tsx`):

| 类型 | 标识 | 触发场景 |
|------|------|---------|
| success | ✅ | 任务完成验收 |
| info | ℹ️ | 一般信息通知 |
| warning | ⚠️ | 任务交付异常 |
| error | ❌ | 操作失败 |
| ai_suggestion | ⚡ | AI 主动建议（如：发现高匹配工人） |

**推送示例**:

```json
{
  "id": "notif_1",
  "type": "ai_suggestion",
  "title": "AI 发现合适候选人",
  "content": "发现一位匹配度 92% 的候选人，擅长数据标注和线下采集，评分 4.8 分",
  "data": { "worker_id": "worker_123", "confidence": 0.92 },
  "action": {
    "label": "查看候选人",
    "handler": () => viewWorker("worker_123")
  }
}
```

### 3.5 情境化界面

**前端设计原则**:

1. **Chat-first**: 对话作为主要交互方式
2. **Generative UI**: 界面根据任务类型动态重组
3. **Agent 可视化**: 显示 AI 思考和执行过程
4. **主动推送**: AI 发现机会/风险时主动通知

**菜单结构** (`/frontend/src/App.tsx`):

```
- 🏠 AI 助手 (默认视图 - ChatInterface)
- 📄 任务管理 (通过 AI 助手管理)
- 👥 工人管理 (通过 AI 助手管理)
- 📊 数据分析 (通过 AI 助手查看)
- ⚙️ 设置 (个性化配置)
```

---

## 4. 长远目标和愿景

### 4.1 L5 专家级 AI Native 愿景描述

**终极愿景**: 成为 **"AI 自主雇佣真人完成物理世界任务的智能体平台"**

**L5 专家级特征**:

1. **完全自主的任务发现与发布**
   - AI 能够主动识别能力缺口并自主发布任务
   - 无需人类干预，AI 完成从需求分析到结果交付的全流程

2. **全球化的真人执行网络**
   - 覆盖全球 200+ 国家和地区的真人执行者
   - 支持 100+ 语言和时区的无缝协作

3. **AI 领域能力超越人类**
   - 在任务质量评估、工人匹配、风险识别等关键指标上超越人类专家
   - AI 决策准确率达到 99.9% 以上

4. **生态系统自我进化**
   - 平台能够从历史交互中持续学习并优化
   - AI Agent 能够自主发现并修复系统问题

### 4.2 平台生态规划

**生态系统参与者**:

```
┌─────────────────────────────────────────────────────────┐
│                  ai-hires-human 生态                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────┐│
│  │  AI 雇主     │◄────►│   平台      │◄────►│  工人   ││
│  │ (上游 Agent)│      │ (调度中心)  │      │ (真人)  ││
│  └─────────────┘      └─────────────┘      └─────────┘│
│         │                    │                    │     │
│         │                    │                    │     │
│         ▼                    ▼                    ▼     │
│  ┌─────────────────────────────────────────────────────┐│
│  │                  第三方服务生态                      ││
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  ││
│  │  │ 支付    │ │ 物流    │ │ 认证    │ │ 保险    │  ││
│  │  │ 服务商  │ │ 服务商  │ │ 机构    │ │ 服务商  │  ││
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**生态角色**:

| 角色 | 描述 | 价值主张 |
|------|------|---------|
| AI 雇主 | 上游 AI Agent/系统 | 快速获取真人执行结果 |
| 工人 | 真人执行者 | 灵活就业机会，按劳取酬 |
| 开发者 | 第三方开发者 | 基于 Open API 构建应用 |
| 服务商 | 支付/物流/认证机构 | 生态合作，共享收益 |

### 4.3 商业模式演进路径

**阶段 1: 交易佣金模式** (当前)
- 平台收取任务报酬的 10-20% 作为服务费
- 收入来源：任务交易佣金

**阶段 2: 增值服务模式** (1-2 年)
- 高级分析报表订阅
- 优先匹配和加急服务
- 企业级 SLA 保障

**阶段 3: 平台生态模式** (3-5 年)
- Open API 调用收费
- 第三方服务分成
- 数据洞察和分析服务

**阶段 4: AI 即服务模式** (5 年+)
- AI Agent 租赁服务
- 行业解决方案授权
- 全球任务网络接入

---

## 5. 执行计划和路线图

### 5.1 已完成的功能清单

| 阶段 | 功能模块 | 完成日期 | 状态 |
|------|---------|---------|------|
| 阶段 1 | P0 基础任务发布/接单 | 2026-01 | ✅ 完成 |
| 阶段 2 | P1-P4 信誉体系/反作弊 | 2026-02 | ✅ 完成 |
| 阶段 3 | P5 迭代功能（仪表板/SLA） | 2026-02 | ✅ 完成 |
| 阶段 4 | P6 AI 杀手级功能 | 2026-03 | ✅ 完成 |
| 阶段 5 | P7-P8 黄金标准/平台化 | 2026-03 | ✅ 完成 |
| 阶段 6 | P9-P27 扩展功能 | 2026-03 | ✅ 完成 |
| 阶段 7 | AI Native 架构转型 | 2026-04 | ✅ 完成 |
| 阶段 8 | AI Native UI 实现 | 2026-04 | ✅ 完成 |

**代码统计**:

| 指标 | 数值 |
|------|------|
| API 端点数量 | 45+ |
| 服务层模块 | 46 |
| 数据模型 | 16 |
| Agent 数量 | 1 (TaskAgent) |
| 工具函数 | 16 |
| 工作流数量 | 4 |
| 前端组件 | 9 (Generative UI 类型) |

### 5.2 待完善的功能和技术债（TODO 列表）

**P0 - 高优先级**:

- [ ] **WebSocket 实时通知**: 当前使用轮询方式，需升级为 WebSocket 推送
- [ ] **移动端适配优化**: 前端需针对移动设备进行优化
- [ ] **语音输入支持**: 集成语音识别 API 支持语音交互
- [ ] **完整的错误处理和恢复机制**: 增强异常场景的容错能力

**P1 - 中优先级**:

- [ ] **用户偏好记忆系统**: 记录用户习惯并实现个性化推荐（L4 关键特性）
- [ ] **多轮对话上下文**: 支持更复杂的对话流和历史上下文追踪
- [ ] **更多 Generative UI 模板**: 扩展动态 UI 组件类型
- [ ] **开发者门户完善**: 完善 Open API 文档和 SDK

**P2 - 低优先级**:

- [ ] **AR/VR 界面探索**: 探索沉浸式交互体验
- [ ] **多模态交互**: 支持图片/视频输入输出
- [ ] **情感识别**: 识别用户情绪并调整回应
- [ ] **区块链支付集成**: 支持加密货币支付

**技术债**:

- [ ] **数据库索引优化**: 部分查询缺少有效索引
- [ ] **单元测试覆盖率**: 需提升至 80% 以上
- [ ] **API 文档完善**: 部分端点缺少详细的 API 文档
- [ ] **日志系统规范化**: 统一日志格式和级别

### 5.3 下一步行动计划（按优先级排序）

**本周内 (2026-04-07 ~ 2026-04-14)**:

1. [ ] 启动 WebSocket 实时通知开发
2. [ ] 完成移动端适配优化
3. [ ] 补充关键路径日志埋点

**本月内 (2026-04-07 ~ 2026-04-30)**:

1. [ ] 实现用户偏好记忆系统原型
2. [ ] 完善多轮对话上下文管理
3. [ ] 提升单元测试覆盖率至 60%

**本季度内 (2026-04-07 ~ 2026-06-30)**:

1. [ ] 完成 L4 特性（用户偏好记忆）开发
2. [ ] 实现语音输入支持
3. [ ] 完善开发者门户和 Open API 文档
4. [ ] 探索 AR/VR 界面原型

---

## 6. 快速启动指南

### 6.1 环境配置要求

**系统要求**:
- Python 3.9+
- Node.js 18+ (前端)
- PostgreSQL 14+ (生产环境) 或 SQLite (开发环境)
- Redis 6+ (可选，用于缓存和会话)

**推荐配置**:
- CPU: 4 核以上
- 内存：8GB 以上
- 磁盘：20GB 可用空间

### 6.2 依赖安装步骤

**后端依赖安装**:

```bash
cd ai-hires-human

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

**前端依赖安装**:

```bash
cd ai-hires-human/frontend

# 安装依赖
npm install

# 或使用 yarn
yarn install
```

### 6.3 启动命令

**后端启动**:

```bash
# 方式 1: 直接启动
cd ai-hires-human
python src/main.py

# 方式 2: 使用 uvicorn 直接启动
uvicorn src.main:app --host 0.0.0.0 --port 8004 --reload

# 方式 3: 使用环境变量配置
AI_HIRES_HUMAN_PORT=8004 python src/main.py
```

**前端启动**:

```bash
cd ai-hires-human/frontend

# 开发模式
npm run dev

# 生产构建
npm run build
npm run preview
```

### 6.4 API 测试方法

**使用 Swagger UI**:

访问 `http://localhost:8004/docs` 查看交互式 API 文档

**使用 curl 测试对话 API**:

```bash
# 发布任务
curl -X POST "http://localhost:8004/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我发布一个线下采集任务，需要到北京现场拍照，报酬 200 元",
    "user_id": "test_user_001"
  }'

# 搜索工人
curl -X POST "http://localhost:8004/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "找会数据标注的工人，评分要高",
    "user_id": "test_user_001"
  }'

# 查询任务状态
curl -X POST "http://localhost:8004/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询任务 task-123 的状态",
    "user_id": "test_user_001"
  }'
```

**使用测试脚本**:

```bash
# 运行 AI Native 功能测试
python test_ai_native.py
```

**使用 Postman 测试**:

导入 OpenAPI Schema:
```bash
curl http://localhost:8004/openapi.json -o openapi.json
```

### 6.5 环境变量配置

创建 `.env` 文件（参考 `.env.example`）:

```bash
# 服务配置
AI_HIRES_HUMAN_PORT=8004
AI_HIRES_HUMAN_PUBLIC_BASE_URL=http://127.0.0.1:8004

# 回调安全配置
AI_HIRES_HUMAN_CALLBACK_SECRET=your-secret-key-here

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# 数据库配置（可选，默认使用 SQLite）
# DATABASE_URL=postgresql://user:password@localhost:5432/ai_hires_human

# Redis 配置（可选）
# REDIS_URL=redis://localhost:6379/0

# DeerFlow 配置（可选，不配置时使用本地降级）
# DEERFLOW_API_KEY=your_deerflow_api_key
# DEERFLOW_BASE_URL=http://localhost:8000
```

---

## 附录

### 附录 A: 文件结构

```
ai-hires-human/
├── src/
│   ├── agents/                    # AI Agent 层
│   │   ├── __init__.py
│   │   ├── deerflow_client.py     # DeerFlow 客户端
│   │   └── task_agent.py          # TaskAgent 核心
│   │
│   ├── tools/                     # Tools 工具层
│   │   ├── __init__.py
│   │   ├── task_tools.py          # 任务工具 (5 个)
│   │   ├── worker_tools.py        # 工人工具 (5 个)
│   │   └── verification_tools.py  # 验证工具 (6 个)
│   │
│   ├── workflows/                 # Workflows 编排层
│   │   ├── __init__.py
│   │   ├── task_workflows.py      # 任务工作流
│   │   └── matching_workflows.py  # 匹配工作流
│   │
│   ├── api/                       # API 端点层 (45+ 个端点)
│   │   ├── chat.py                # 对话式 API
│   │   ├── tasks.py               # 任务管理
│   │   ├── workers.py             # 工人管理
│   │   └── ... (40+ 个端点文件)
│   │
│   ├── services/                  # 业务服务层 (46 个服务)
│   │   ├── task_service.py
│   │   ├── worker_service.py
│   │   └── ... (44+ 个服务文件)
│   │
│   ├── models/                    # 数据模型层 (16 个模型)
│   │   ├── db_models.py           # 核心 ORM 模型
│   │   └── ... (15+ 个模型文件)
│   │
│   ├── config/                    # 配置层
│   │   ├── logging_config.py
│   │   └── ...
│   │
│   ├── middleware/                # 中间件层
│   │   ├── rate_limit.py
│   │   └── ...
│   │
│   └── main.py                    # 应用入口
│
├── frontend/                      # 前端 (React + TypeScript)
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── GenerativeUI.tsx
│   │   │   ├── AgentStatus.tsx
│   │   │   └── NotificationPanel.tsx
│   │   ├── services/
│   │   ├── styles/
│   │   └── App.tsx
│   └── package.json
│
├── requirements.txt               # Python 依赖
├── .env.example                   # 环境变量示例
└── test_ai_native.py              # AI Native 功能测试
```

### 附录 B: 关键术语表

| 术语 | 定义 |
|------|------|
| **AI Native** | AI 作为核心决策引擎，而非功能模块 |
| **TaskAgent** | 任务智能体，负责任务发布、匹配和验收的自主决策 |
| **DeerFlow 2.0** | 孵化器统一 Agent 框架 |
| **Generative UI** | 由 AI 动态生成的用户界面 |
| **置信度阈值** | AI 自主决策的置信度门槛（如 0.8 自动分配） |
| **Chat-first** | 对话作为主要交互方式的设计理念 |

### 附录 C: 参考文档

| 文档 | 说明 |
|------|------|
| [AI_NATIVE_COMPLETION_REPORT.md](./AI_NATIVE_COMPLETION_REPORT.md) | AI Native 功能完成报告 |
| [AI_NATIVE_REDESIGN_WHITEPAPER.md](./AI_NATIVE_REDESIGN_WHITEPAPER.md) | AI Native 重设计白皮书 |
| [AI_NATIVE_UI_COMPLETION_REPORT.md](./AI_NATIVE_UI_COMPLETION_REPORT.md) | AI Native UI 实现报告 |

---

*文档生成时间：2026-04-07*
*文档版本：v1.0*
*项目版本：ai-hires-human v1.25.0*
