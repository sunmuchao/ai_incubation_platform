# 自主代理引擎设计方案

> 版本：v2.0
> 日期：2026-04-11
> 状态：**已实现** ✅
> 
> **实现位置**: `src/agent/autonomous/`
> - `executor.py` - 执行器
> - `scheduler.py` - 调度器
> - `event_listener.py` - 事件监听
> - `push_executor.py` - 推送执行
> - `rule_parser.py` - 规则解析
> - `HEARTBEAT_RULES.md` - 心跳规则配置
> 
> **核心理念**：让 Her 从「被动响应的工具」进化为「主动推进的代理」，实现 AI Native 成熟度从 L1 到 L3 的跃迁。
> 
> **v2.0 更新说明**：借鉴 OpenClaw 心跳机制，引入「LLM 自主判断」范式
> - **HEARTBEAT_RULES.md**：任务清单文件，替代硬编码规则，支持动态调整
> - **心跳跳过机制**：无到期规则时跳过 LLM 调用，节省 API 成本
> - **HEARTBEAT_OK 协议**：无事可做时静默返回，不推送消息
> - **LLM 自主判断**：让 AI 决定"是否需要行动"，而非代码硬编码判断

---

## 目录

1. [背景与问题](#一背景与问题)
2. [核心思想](#二核心思想)
3. [系统架构](#三系统架构)
4. [心跳规则设计（HEARTBEAT_RULES.md）](#四心跳规则设计heartbeat_rulesmd)
5. [任务追踪器设计](#五任务追踪器设计)
6. [推送执行器设计](#六推送执行器设计)
7. [数据模型设计](#七数据模型设计)
8. [接口设计](#八接口设计)
9. [实现路线图](#九实现路线图)
10. [效果评估](#十效果评估)

---

## 一、背景与问题

### 1.1 用户痛点

用户反馈：「Her 就是一个不负责任的红娘，我不找她、不问她，她就不帮我推进找对象的事情」

这反映了用户的真实期望：
- **主动感知**：Her 应该感知到时机，而不是等待用户触发
- **持续推进**：匹配成功后，Her 应该持续追踪进度
- **适时介入**：在关键节点（对话停滞、约会前、关系瓶颈）主动出手

### 1.2 五问法根因分析

```
问题现象：Her 不会主动推进"找对象"这件事
├─ 为什么 1: 系统只在用户发起请求时才响应，没有主动触发机制
├─ 为什么 2: 架构是"请求→响应"模式，而非"感知→行动→确认"闭环
├─ 为什么 3: 缺少对用户状态和时机的持续追踪判断能力
├─ 为什么 4: 没有"任务生命周期管理"概念，匹配后任务就结束了
└─ 根本原因: 缺少「自主代理引擎」——一个持续运行、感知时机、主动行动的核心组件
```

### 1.3 现状盘点

**已有能力（但处于"僵尸状态"）**：

| 组件 | 文件 | 能力 | 问题 |
|------|------|------|------|
| 自主匹配工作流 | `autonomous_workflows.py` | AutoMatchRecommendWorkflow | 无触发机制 |
| 关系健康度分析 | `autonomous_workflows.py` | RelationshipHealthCheckWorkflow | 无定时调度 |
| 自主破冰助手 | `autonomous_workflows.py` | AutoIcebreakerWorkflow | 无时机感知 |
| 推送通知服务 | `notification_service.py` | NotificationService | 仅被动调用 |
| 兼容性分析工具 | `autonomous_tools.py` | CompatibilityAnalysisTool | 无触发调用 |

**缺失的核心组件**：

| 缺失项 | 影响 |
|--------|------|
| 定时任务调度器 | 无法定期扫描用户状态 |
| 时机感知器 | 无法识别"该出手"的时刻 |
| 任务追踪器 | 无法记录"找对象"任务进度 |
| 事件监听机制 | 无法响应关键事件（新匹配、对话停滞） |

### 1.4 AI Native 成熟度对标

| 等级 | 名称 | 当前 Her 状态 | 期望状态 |
|------|------|--------------|----------|
| L1 | 工具 | ✓ 被动响应 API 调用 | — |
| L2 | 助手 | 部分（有推送能力，但未激活） | ✓ 主动发现问题并推送 |
| L3 | 代理 | — | ✓ 多步工作流自主执行 |
| L4 | 伙伴 | — | 记忆用户偏好并进化 |
| L5 | 专家 | — | 长期愿景 |

**目标**：通过自主代理引擎，让 Her 从 L1 跨越到 L3。

---

## 二、核心思想

### 2.1 范式转变

```
旧范式：请求 → 处理 → 响应
├── 用户主动发起一切
├── Her 被动等待调用
└── 匹配成功 = 任务完成

新范式：感知 → 判断 → 行动 → 确认
├── Her 感知环境变化（新匹配、时间流逝、用户行为）
├── 判断是否"该出手"（时机识别）
├── 自主采取行动（推送建议、发起对话）
└── 用户确认/反馈，形成闭环
```

### 2.2 核心隐喻：负责任的红娘

想象一个真正负责任的红娘：

```
传统红娘（当前 Her）：
用户："给我介绍个对象"
红娘："好的，这是候选名单"
用户："……"
红娘：（沉默等待）
用户："怎么还没进展？"
红娘："你没问我啊"

负责任的红娘（期望的 Her）：
红娘："今天发现 3 位新匹配对象，要不要看看？"
用户：（没回复）
3天后：
红娘："你和匹配对象 A 还没开始聊天，要不要我帮你破冰？"
用户："好啊"
红娘："根据你们共同兴趣，建议聊这些话题..."
1周后：
红娘："你们聊了 7 天了，要不要约见面？我帮你们找个合适的地点"
```

### 2.3 设计原则

| 原则 | 说明 |
|------|------|
| **感知优先** | 先感知时机，再决定行动，而非盲目推送 |
| **时机敏感** | 推送内容要与当前情境匹配（破冰/约会/激活） |
| **用户可控** | 用户可以设置"免打扰"或"主动程度"偏好 |
| **反馈闭环** | 推送后追踪用户响应，调整后续策略 |
| **避免骚扰** | 推送频率控制，避免过度打扰 |
| **成本可控** | 无事可做时跳过 LLM 调用，节省 API 成本 |

### 2.4 借鉴 OpenClaw 心跳机制

> 参考：[OpenClaw Heartbeat](https://github.com/openclaw/openclaw/blob/main/docs/gateway/heartbeat.md)

OpenClaw 的心跳机制提供了一个非常优雅的设计范式：

```
核心设计：
├── HEARTBEAT.md 文件：定义要定期检查的任务清单
├── interval 间隔：每个任务有独立的执行间隔（30m/1h/24h）
├── HEARTBEAT_OK 协议：无事可做时返回静默确认
├── 心跳跳过机制：无到期任务时跳过 LLM 调用
└── LLM 自主判断：让 AI 自己决定"是否需要行动"
```

**关键启发**：

| 原方案（硬编码） | OpenClaw 方式（LLM自主） |
|-----------------|-------------------------|
| Python 代码硬编码规则 | `HEARTBEAT_RULES.md` 文件定义 |
| `if condition → push` | LLM 自主判断"是否需要行动" |
| 改规则需改代码 | 改文件即可，无需改代码 |
| 每次扫描都执行 | 无到期任务则跳过调用 |

**Her 整合后的心跳范式**：

```
每 30 分钟心跳：
├── 读取 HEARTBEAT_RULES.md（任务清单）
├── 筛选"到期"的规则（根据 interval 和 last_run）
├── 无到期规则 → 跳过心跳，记录 reason=no-rules-due
├── 有到期规则 → 组装心跳提示词，调用 LLM
├── LLM 返回 HEARTBEAT_OK → 静默结束，不推送
├── LLM 返回行动指令 → 执行推送，记录结果
└── 更新 last_run 时间戳

事件驱动触发：
├── match_created 事件 → 立即触发心跳（优先级高）
├── message_sent 事件 → 更新活跃状态，取消可能的停滞推送
└── user_login 事件 → 更新活跃状态，取消可能的激活推送
```

**HEARTBEAT_RULES.md 示例**：

```markdown
# Her 心跳任务清单

rules:
- name: check_new_matches
  interval: 30m
  prompt: "检查是否有新匹配成功但未推送破冰建议的用户"

- name: check_stale_conversations  
  interval: 1h
  prompt: "检查是否有对话停滞超过72小时的匹配，需要推送话题激活"

- name: check_user_activity
  interval: 24h
  prompt: "检查是否有超过7天未活跃的用户，需要推送激活提醒"

- name: check_pending_dates
  interval: 1h
  prompt: "检查是否有24小时内即将进行的约会，推送准备提醒"

# 心跳指导原则
- 如果无事需要处理，回复 HEARTBEAT_OK
- 如果需要推送，说明推送对象和内容类型
- 推送内容要个性化，避免模板化
- 注意用户推送偏好设置，尊重免打扰时段
```

---

## 三、系统架构

### 3.1 架构总览（v2.0 - 心跳范式）

```
自主代理引擎 (Autonomous Agent Engine)
│
├── 心跳调度器 (Heartbeat Scheduler)
│   ├── APScheduler 集成：定时触发心跳（默认 30m）
│   ├── 规则解析器：读取 HEARTBEAT_RULES.md，筛选到期规则
│   ├── 心跳跳过检查：无到期规则则跳过 LLM 调用
│   └── 分布式锁：防止重复执行
│
├── 心跳执行器 (Heartbeat Executor)
│   ├── 心跳提示词组装：将到期规则注入 LLM prompt
│   ├── LLM 自主判断：让 AI 决定"是否需要行动"
│   ├── HEARTBEAT_OK 协议：无事可做时静默返回
│   └── 行动指令解析：解析 LLM 返回的行动意图
│
├── 推送执行器 (Push Executor)
│   ├── 推送策略选择：根据行动意图选择推送内容
│   ├── 现有工作流调用：激活 AutoMatchRecommendWorkflow 等
│   ├── 现有推送服务调用：调用 NotificationService
│   └── 效果追踪：记录推送效果（用户是否响应）
│
├── 任务追踪器 (Task Tracker)
│   ├── 任务生命周期管理：记录"找对象"任务进度
│   ├── last_run 时间戳：记录每个规则的最后执行时间
│   └── 执行历史追踪：记录已完成的行动和效果
│
└── 事件监听器 (Event Listener)
    ├── match_created：新匹配成功 → 立即触发心跳
    ├── message_sent：消息发送 → 更新活跃状态
    ├── user_login：用户登录 → 取消激活推送
    └── date_scheduled：约会安排 → 设置约会提醒
```

### 3.2 核心范式转变

```
v1.0 硬编码范式：
├── scan_new_matches() → 硬编码判断 → push
├── scan_stale_conversations() → 硬编码判断 → push
├── 每个规则都是 Python 代码
└── 改规则需改代码、重启服务

v2.0 心跳范式：
├── HEARTBEAT_RULES.md 定义规则（文件）
├── 筛选到期规则 → 组装心跳提示词
├── LLM 自主判断"是否需要行动"
├── HEARTBEAT_OK → 静默结束
├── 行动指令 → 执行推送
└── 改规则只需改文件，无需重启
```

### 3.3 心跳执行流程

```
                    ┌─────────────────────────────────┐
                    │        心跳调度器               │
                    │     (APScheduler, 30m)          │
                    └─────────┬───────────────────────┘
                              │ 定时触发
                              ▼
                    ┌─────────────────────────────────┐
                    │     读取 HEARTBEAT_RULES.md     │
                    │     解析 rules + intervals      │
                    └─────────┬───────────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────────┐
                    │     筛选到期规则                 │
                    │  根据 last_run 和 interval      │
                    └─────────┬───────────────────────┘
                              │
                              ▼
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────┐         ┌─────────────────────────────┐
│ 无到期规则          │         │      有到期规则             │
│ reason=no-rules-due │         │  组装心跳提示词              │
│ 跳过 LLM 调用       │         │  注入到期规则 + 上下文       │
│ 更新 last_run      │         └─────────┬───────────────────┘
└─────────────────────┘                   │
                                          │ 调用 LLM
                                          ▼
                          ┌─────────────────────────────────┐
                          │      LLM 自主判断               │
                          │  "是否有需要行动的事项？"        │
                          └─────────┬───────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│    返回 HEARTBEAT_OK        │   │    返回行动指令             │
│    无事可做                 │   │    "需要推送给用户X..."     │
│    静默结束，不推送         │   │    解析行动意图             │
│    更新 last_run           │   └─────────┬───────────────────┘
└─────────────────────────────┘             │
                                            │ 执行推送
                                            ▼
                          ┌─────────────────────────────────┐
                          │        推送执行器               │
                          │  - 选择推送策略                  │
                          │  - 调用现有工作流                │
                          │  - 调用 NotificationService      │
                          │  - 记录推送效果                  │
                          └─────────┬───────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────────────────────┐
                          │           用户端                │
                          │  收到主动推送                    │
                          │  响应/忽略                       │
                          └─────────────────────────────────┘
```

### 3.4 事件驱动触发

```
事件监听器处理关键业务事件：

match_created 事件：
├── 匹配成功时立即触发
├── 调用 trigger_immediate("check_new_matches")
├── 不等待下一次心跳周期
└── 优先级：高

message_sent 事件：
├── 更新 match_history.last_message_at
├── 重置 stale_hours = 0
├── 取消可能存在的"对话停滞"推送计划
└── 优先级：中

user_login 事件：
├── 更新 users.last_login_at
├── 重置 inactive_days = 0
├── 取消可能存在的"用户激活"推送计划
└── 优先级：中

date_scheduled 事件：
├── 记录约会时间
├── 设置约会提醒定时任务（约会前24h）
└── 优先级：高
```

### 3.5 与现有系统集成

```
现有系统                          自主代理引擎（新增）
────────                          ────────────────

autonomous_workflows.py     ←───  推送执行器调用
├── AutoMatchRecommendWorkflow
├── RelationshipHealthCheckWorkflow
└── AutoIcebreakerWorkflow

notification_service.py     ←───  推送执行器调用
└── NotificationService

autonomous_tools.py         ←───  工作流内部调用
├── CompatibilityAnalysisTool
├── TopicSuggestionTool
└── RelationshipTrackingTool

HEARTBEAT_RULES.md          ←───  心跳调度器读取（新增）
└── 任务清单文件，定义 rules + intervals

数据库                       ←───  任务追踪器读写
├── users
├── match_history
├── chat_messages
├── heartbeat_rule_state（新增：规则执行状态，记录 last_run）
└── push_history（新增：推送历史）
```

---

## 四、心跳规则设计（HEARTBEAT_RULES.md）

### 4.1 规则文件结构

```markdown
# HEARTBEAT_RULES.md - Her 心跳任务清单

rules:
- name: check_new_matches
  interval: 30m
  prompt: "检查是否有新匹配成功但未推送破冰建议的用户"
  action_type: icebreaker
  
- name: check_stale_conversations  
  interval: 1h
  prompt: "检查是否有对话停滞超过72小时的匹配，需要推送话题激活"
  action_type: topic_suggestion
  
- name: check_user_activity
  interval: 24h
  prompt: "检查是否有超过7天未活跃的用户，需要推送激活提醒"
  action_type: activation_reminder
  
- name: check_pending_dates
  interval: 1h
  prompt: "检查是否有24小时内即将进行的约会，推送准备提醒"
  action_type: date_preparation

# 心跳指导原则（注入 LLM prompt）
- 如果无事需要处理，回复 HEARTBEAT_OK
- 如果需要推送，说明：
  - 推送对象（用户ID/匹配ID）
  - 推送内容类型（icebreaker/topic/activation/date）
  - 推送理由（为什么需要推送）
- 推送内容要个性化，避免模板化
- 注意用户推送偏好设置，尊重免打扰时段
- 检查是否有重复推送（避免骚扰）
```

### 4.2 规则执行状态表

```sql
CREATE TABLE heartbeat_rule_state (
    id VARCHAR(64) PRIMARY KEY,
    rule_name VARCHAR(64) NOT NULL,      -- 规则名称
    user_id VARCHAR(64),                 -- 用户ID（可选，全局规则时为NULL）
    
    -- 执行状态
    last_run_at TIMESTAMP,               -- 最后执行时间
    last_result VARCHAR(32),             -- 最后结果：executed/skipped/heartbeat_ok
    last_action VARCHAR(128),            -- 最后执行的行动
    
    -- 统计信息
    run_count INT DEFAULT 0,             -- 执行次数
    action_count INT DEFAULT 0,          -- 实际行动次数（非 HEARTBEAT_OK）
    skip_count INT DEFAULT 0,            -- 跳过次数
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_rule_name (rule_name),
    INDEX idx_user_id (user_id),
    INDEX idx_last_run (last_run_at)
);
```

### 4.3 规则筛选逻辑

```python
class HeartbeatRuleSelector:
    """心跳规则筛选器"""
    
    def select_due_rules(self, db_session) -> List[dict]:
        """筛选到期需要执行的规则"""
        # 1. 读取 HEARTBEAT_RULES.md
        rules = self._load_rules_from_file()
        
        # 2. 查询每个规则的 last_run_at
        due_rules = []
        for rule in rules:
            interval_minutes = self._parse_interval(rule["interval"])
            last_run = self._get_last_run(rule["name"], db_session)
            
            # 3. 计算是否到期
            if last_run is None:
                # 从未执行过，需要执行
                due_rules.append(rule)
            else:
                minutes_since_last = (datetime.now() - last_run).total_seconds() / 60
                if minutes_since_last >= interval_minutes:
                    due_rules.append(rule)
        
        return due_rules
    
    def should_skip_heartbeat(self, due_rules: List[dict]) -> bool:
        """判断是否跳过心跳（无到期规则）"""
        if not due_rules:
            return True  # 跳过，记录 reason=no-rules-due
        return False
```

### 4.4 心跳提示词组装

```python
HEARTBEAT_PROMPT_TEMPLATE = """
你现在是 Her 约会助手的心跳代理。请检查以下到期任务：

{due_rules_section}

当前上下文：
- 用户数：{user_count}
- 匹配数：{match_count}
- 最近活跃用户：{recent_active_users}

指导原则：
{guidelines_section}

如果无事需要处理，回复 HEARTBEAT_OK
如果需要推送，说明推送对象、内容类型和理由。
"""

def assemble_heartbeat_prompt(due_rules: List[dict], context: dict) -> str:
    """组装心跳提示词"""
    # 将到期规则注入提示词
    due_rules_text = "\n".join([
        f"- [{r['name']}] (间隔 {r['interval']}): {r['prompt']}"
        for r in due_rules
    ])
    
    guidelines = load_guidelines_from_heartbeat_rules()
    
    return HEARTBEAT_PROMPT_TEMPLATE.format(
        due_rules_section=due_rules_text,
        user_count=context["user_count"],
        match_count=context["match_count"],
        recent_active_users=context["recent_active_users"],
        guidelines_section=guidelines
    )
```

### 4.5 HEARTBEAT_OK 协议处理

```python
HEARTBEAT_TOKEN = "HEARTBEAT_OK"
HEARTBEAT_ACK_MAX_CHARS = 300  # HEARTBEAT_OK 后最多允许 300 字符

def process_heartbeat_response(response: str) -> dict:
    """处理心跳响应"""
    if response.strip().startswith(HEARTBEAT_TOKEN):
        # 静默确认
        remaining = response.replace(HEARTBEAT_TOKEN, "").strip()
        if len(remaining) <= HEARTBEAT_ACK_MAX_CHARS:
            return {
                "type": "heartbeat_ok",
                "action": None,
                "message": remaining if remaining else None
            }
    
    # 尝试解析行动指令
    action = parse_action_from_response(response)
    if action:
        return {
            "type": "action_required",
            "action": action,
            "message": response
        }
    
    # 无法解析，默认为需要人工确认
    return {
        "type": "unclear",
        "action": None,
        "message": response
    }
```

---

## 五、任务追踪器设计

### 5.1 任务生命周期定义

```
"找对象"任务生命周期：

阶段1：寻找匹配 (seeking_match)
├── 状态：单身、正在找对象
├── 下一步：完善资料、等待匹配
├── Her 负责：主动推送新匹配

阶段2：破冰接触 (icebreaking)
├── 状态：有匹配、尚未开始聊天
├── 下一步：发起第一次对话
├── Her 负责：推送破冰话题、提醒行动

阶段3：建立连接 (connecting)
├── 状态：正在聊天、尚未约见面
├── 下一步：深化对话、安排约会
├── Her 负责：推送话题建议、约会准备

阶段4：线下约会 (dating)
├── 状态：已约会或正在约会
├── 下一步：约会反馈、关系确认
├── Her 负责：约会建议、反馈征集

阶段5：关系发展 (relationship)
├── 状态：已确认关系
├── 下一步：关系维护、长期规划
├── Her 负责：关系健康度分析、里程碑庆祝

阶段6：成功/结束 (completed/ended)
├── 状态：找到对象或放弃
├── 任务结束
```

### 5.2 任务状态数据结构

```python
class AgentTask:
    """代理任务数据结构"""
    
    user_id: str              # 用户ID
    match_id: Optional[str]   # 当前聚焦的匹配ID（如果有）
    
    # 任务阶段
    phase: str                # seeking_match / icebreaking / connecting / dating / relationship
    
    # 下一步行动
    next_action: str          # 当前"应该做什么"
    next_action_reason: str   # 为什么应该做这个
    suggested_at: datetime    # 建议时间
    
    # 任务进度
    progress_metrics: dict    # 进度指标
    # {
    #   "matches_received": 10,
    #   "conversations_started": 3,
    #   "dates_scheduled": 1,
    #   "days_in_current_phase": 5,
    # }
    
    # 用户响应记录
    user_responses: List[dict]  # 用户对推送的响应历史
    # [
    #   {"push_type": "icebreaker", "responded": True, "response_time": "2h"},
    #   {"push_type": "topic", "responded": False, "ignored": True},
    # ]
    
    # 推送偏好
    push_preferences: dict    # 用户推送偏好
    # {
    #   "enabled": True,
    #   "proactive_level": "high",  # high/medium/low
    #   "quiet_hours": ["22:00-08:00"],
    #   "preferred_channels": ["push", "sms"],
    # }
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    phase_entered_at: datetime  # 进入当前阶段的时间
```

### 5.3 下一步行动推荐算法

```python
class NextActionRecommender:
    """下一步行动推荐"""
    
    ACTION_RULES = {
        "seeking_match": [
            {
                "condition": "profile_completion < 80%",
                "action": "完善资料",
                "reason": "资料完善度影响匹配质量",
                "priority": 1,
            },
            {
                "condition": "days_since_last_match > 3",
                "action": "等待新匹配推送",
                "reason": "系统正在为您筛选合适对象",
                "priority": 2,
            },
        ],
        "icebreaking": [
            {
                "condition": "hours_since_match > 24",
                "action": "发起第一次对话",
                "reason": "越早行动，成功率越高",
                "priority": 1,
                "suggestion": "使用破冰话题建议",
            },
        ],
        "connecting": [
            {
                "condition": "message_count < 20",
                "action": "深化对话",
                "reason": "建立更多了解再约会",
                "priority": 1,
                "suggestion": "使用话题建议",
            },
            {
                "condition": "message_count >= 20 and days_since_first_chat >= 5",
                "action": "安排约会",
                "reason": "已经聊得足够多，该见面了",
                "priority": 1,
            },
        ],
        "dating": [
            {
                "condition": "date_status == scheduled",
                "action": "约会准备",
                "reason": "约会前准备能提升成功率",
                "priority": 1,
            },
            {
                "condition": "date_status == completed",
                "action": "约会反馈",
                "reason": "您的反馈能帮助系统优化",
                "priority": 1,
            },
        ],
    }
    
    def recommend_next_action(self, task: AgentTask) -> dict:
        """推荐下一步行动"""
        # 根据当前阶段和条件，计算最合适的下一步行动
        # 返回行动建议、理由、优先级
```

---

## 六、推送执行器设计

### 6.1 推送策略选择

```python
class PushStrategySelector:
    """推送策略选择器"""
    
    PUSH_STRATEGIES = {
        "icebreaker": {
            "template": "新匹配破冰推送",
            "content_type": "话题建议",
            "call_to_action": "开始对话",
            "workflow": "AutoIcebreakerWorkflow",
            "urgency": "high",
        },
        "topic_suggestion": {
            "template": "对话停滞激活推送",
            "content_type": "话题建议",
            "call_to_action": "继续聊天",
            "workflow": "AutoIcebreakerWorkflow",
            "urgency": "medium",
        },
        "activation_reminder": {
            "template": "用户激活推送",
            "content_type": "关心+新匹配",
            "call_to_action": "回来看看",
            "workflow": "AutoMatchRecommendWorkflow",
            "urgency": "low",
        },
        "daily_recommend": {
            "template": "每日推荐推送",
            "content_type": "匹配动态",
            "call_to_action": "查看推荐",
            "workflow": "AutoMatchRecommendWorkflow",
            "urgency": "low",
        },
        "date_preparation": {
            "template": "约会准备推送",
            "content_type": "约会建议",
            "call_to_action": "查看建议",
            "workflow": "AutoIcebreakerWorkflow",
            "urgency": "high",
        },
        "relationship_health": {
            "template": "关系健康度推送",
            "content_type": "关系报告",
            "call_to_action": "查看报告",
            "workflow": "RelationshipHealthCheckWorkflow",
            "urgency": "medium",
        },
    }
    
    def select_strategy(self, trigger_type: str, context: dict) -> dict:
        """选择推送策略"""
        # 根据触发类型和上下文选择合适的策略
        # 返回策略配置
```

### 6.2 推送内容生成

```python
class PushContentGenerator:
    """推送内容生成器"""
    
    def generate_icebreaker_push(
        self, 
        user_id: str, 
        match_id: str,
        match_user: dict
    ) -> dict:
        """生成破冰推送内容"""
        # 调用 AutoIcebreakerWorkflow 获取话题建议
        # 生成个性化推送文案
        
        return {
            "title": f"您和 {match_user['name']} 匹配成功！",
            "message": f"你们有{len(match_user['common_interests'])}个共同兴趣，要不要聊聊？",
            "topics": ["话题1", "话题2", "话题3"],
            "cta": "开始对话",
            "data": {"match_id": match_id, "action": "start_chat"},
        }
    
    def generate_stale_conversation_push(
        self,
        user_id: str,
        match_id: str,
        stale_hours: int
    ) -> dict:
        """生成对话停滞激活推送"""
        # 调用 TopicSuggestionTool 获取话题建议
        # 生成激活推送文案
        
        return {
            "title": f"您和 {match_user['name']} 的对话停了{stale_hours}小时",
            "message": "要不要我帮你想几个话题，重新激活对话？",
            "topics": ["话题1", "话题2"],
            "cta": "继续聊天",
            "data": {"match_id": match_id, "action": "continue_chat"},
        }
    
    def generate_activation_reminder_push(
        self,
        user_id: str,
        inactive_days: int,
        pending_matches: int
    ) -> dict:
        """生成用户激活推送"""
        return {
            "title": "好久不见，想你了~",
            "message": f"您有{pending_matches}个待处理的匹配，要不要回来看看？",
            "cta": "回来看看",
            "data": {"action": "return_to_app"},
        }
```

### 6.3 推送效果追踪

```python
class PushEffectTracker:
    """推送效果追踪器"""
    
    def record_push(
        self,
        user_id: str,
        push_type: str,
        push_content: dict,
        push_channel: str,
        db_session
    ) -> str:
        """记录推送发送"""
        # 创建 push_history 记录
        # 返回 push_id
        
    def record_response(
        self,
        push_id: str,
        response_type: str,  # clicked / ignored / acted
        response_time: Optional[int],  # 响应时间（秒）
        db_session
    ):
        """记录用户响应"""
        # 更新 push_history 记录
        # 更新任务追踪器中的 user_responses
        
    def analyze_effectiveness(
        self,
        user_id: str,
        push_type: str,
        days: int = 30
    ) -> dict:
        """分析推送效果"""
        # 计算点击率、转化率、平均响应时间
        # 用于优化推送策略
```

---

## 七、数据模型设计

### 7.1 新增数据表

#### 7.1.1 agent_tasks 表（代理任务追踪）

```sql
CREATE TABLE agent_tasks (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    match_id VARCHAR(64),                -- 当前聚焦的匹配ID
    
    -- 任务阶段
    phase VARCHAR(32) NOT NULL,          -- seeking_match/icebreaking/connecting/dating/relationship
    phase_entered_at TIMESTAMP,          -- 进入当前阶段的时间
    
    -- 下一步行动
    next_action VARCHAR(128),            -- 当前"应该做什么"
    next_action_reason VARCHAR(512),     -- 为什么应该做这个
    suggested_at TIMESTAMP,              -- 建议时间
    
    -- 进度指标（JSON）
    progress_metrics TEXT,               -- 进度指标JSON
    
    -- 用户响应记录（JSON）
    user_responses TEXT,                 -- 用户响应历史JSON
    
    -- 推送偏好（JSON）
    push_preferences TEXT,               -- 用户推送偏好JSON
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_phase (phase),
    INDEX idx_match_id (match_id)
);
```

#### 7.1.2 push_history 表（推送历史）

```sql
CREATE TABLE push_history (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    match_id VARCHAR(64),                -- 关联的匹配ID（如果有）
    
    -- 推送类型
    push_type VARCHAR(32) NOT NULL,      -- icebreaker/topic_suggestion/activation_reminder等
    trigger_type VARCHAR(32),            -- 触发时机类型
    
    -- 推送内容
    title VARCHAR(128),
    message TEXT,
    data TEXT,                           -- 推送携带的数据JSON
    
    -- 推送渠道
    push_channel VARCHAR(32),            -- push/sms/email
    
    -- 推送结果
    push_status VARCHAR(16),             -- sent/delivered/failed
    push_error TEXT,                     -- 失败原因
    pushed_at TIMESTAMP,
    
    -- 用户响应
    response_type VARCHAR(16),           -- clicked/ignored/acted
    response_time INT,                   -- 响应时间（秒）
    responded_at TIMESTAMP,
    
    -- 效果追踪
    action_taken VARCHAR(64),            -- 用户采取的具体行动
    action_result TEXT,                  -- 行动结果
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_push_type (push_type),
    INDEX idx_pushed_at (pushed_at),
    INDEX idx_match_id (match_id)
);
```

#### 7.1.3 trigger_events 表（触发事件记录）

```sql
CREATE TABLE trigger_events (
    id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(32) NOT NULL,     -- match_created/message_sent/date_scheduled等
    event_source VARCHAR(64),            -- 事件来源（用户ID/匹配ID等）
    
    -- 事件数据
    event_data TEXT,                     -- 事件详情JSON
    
    -- 触发结果
    triggered_action VARCHAR(32),        -- 触发的行动类型
    triggered_push_id VARCHAR(64),       -- 触发的推送ID
    
    -- 时间戳
    event_time TIMESTAMP,
    processed_at TIMESTAMP,
    
    -- 索引
    INDEX idx_event_type (event_type),
    INDEX idx_event_time (event_time)
);
```

### 7.2 现有表扩展

#### 7.2.1 users 表扩展

```sql
ALTER TABLE users ADD COLUMN (
    -- 用户推送偏好
    push_enabled BOOLEAN DEFAULT TRUE,
    push_proactive_level VARCHAR(16) DEFAULT 'medium',  -- high/medium/low/none
    push_quiet_hours_start TIME DEFAULT '22:00',
    push_quiet_hours_end TIME DEFAULT '08:00',
    push_preferred_channels TEXT,        -- JSON: ["push", "sms"]
    
    -- 用户活跃状态
    last_login_at TIMESTAMP,
    last_active_at TIMESTAMP,
    inactive_days INT DEFAULT 0,
    
    -- 任务状态引用
    current_agent_task_id VARCHAR(64),   -- 当前代理任务ID
);
```

#### 7.2.2 match_history 表扩展

```sql
ALTER TABLE match_history ADD COLUMN (
    -- 匹配推送状态
    icebreaker_pushed BOOLEAN DEFAULT FALSE,
    icebreaker_pushed_at TIMESTAMP,
    stale_push_count INT DEFAULT 0,
    last_stale_push_at TIMESTAMP,
    
    -- 对话活跃状态
    last_message_at TIMESTAMP,
    stale_hours INT DEFAULT 0,
    
    -- 约会状态
    date_scheduled BOOLEAN DEFAULT FALSE,
    date_scheduled_at TIMESTAMP,
    date_completed BOOLEAN DEFAULT FALSE,
    date_completed_at TIMESTAMP,
);
```

---

## 八、接口设计

### 8.1 内部接口（供调度器和工作流调用）

#### 8.1.1 时机感知器接口

```python
# src/agent/autonomous/timing_perception.py

class TimingPerceptionService:
    """时机感知服务"""
    
    def scan_new_matches(self, hours: int = 24) -> List[dict]:
        """扫描新匹配"""
        pass
    
    def scan_stale_conversations(self, hours: int = 72) -> List[dict]:
        """扫描停滞对话"""
        pass
    
    def scan_inactive_users(self, days: int = 7) -> List[dict]:
        """扫描不活跃用户"""
        pass
    
    def scan_pending_dates(self, hours: int = 24) -> List[dict]:
        """扫描待约会"""
        pass
    
    def evaluate_trigger(self, user_id: str, trigger_type: str, context: dict) -> bool:
        """评估是否触发"""
        pass
```

#### 8.1.2 任务追踪器接口

```python
# src/agent/autonomous/task_tracker.py

class TaskTrackerService:
    """任务追踪服务"""
    
    def create_task(self, user_id: str, initial_phase: str = "seeking_match") -> AgentTask:
        """创建代理任务"""
        pass
    
    def get_task(self, user_id: str) -> Optional[AgentTask]:
        """获取用户任务"""
        pass
    
    def update_phase(self, user_id: str, new_phase: str) -> AgentTask:
        """更新任务阶段"""
        pass
    
    def recommend_next_action(self, user_id: str) -> dict:
        """推荐下一步行动"""
        pass
    
    def record_user_response(self, user_id: str, push_id: str, response: dict):
        """记录用户响应"""
        pass
```

#### 8.1.3 推送执行器接口

```python
# src/agent/autonomous/push_executor.py

class PushExecutorService:
    """推送执行服务"""
    
    def execute_push(
        self,
        user_id: str,
        push_type: str,
        context: dict,
        auto_execute: bool = True
    ) -> dict:
        """执行推送"""
        pass
    
    def generate_push_content(
        self,
        push_type: str,
        user_id: str,
        context: dict
    ) -> dict:
        """生成推送内容"""
        pass
    
    def record_push_result(self, push_id: str, result: dict):
        """记录推送结果"""
        pass
```

### 8.2 外部 API（供前端调用）

#### 8.2.1 用户推送偏好设置 API

```python
# src/api/agent_preferences.py

@router.put("/users/{user_id}/push-preferences")
async def update_push_preferences(
    user_id: str,
    preferences: PushPreferencesRequest
):
    """更新用户推送偏好"""
    pass

@router.get("/users/{user_id}/push-preferences")
async def get_push_preferences(user_id: str):
    """获取用户推送偏好"""
    pass
```

#### 8.2.2 任务状态查询 API

```python
# src/api/agent_task.py

@router.get("/users/{user_id}/task-status")
async def get_task_status(user_id: str):
    """获取用户任务状态"""
    # 返回当前阶段、下一步行动、进度指标
    pass

@router.get("/users/{user_id}/next-action")
async def get_next_action(user_id: str):
    """获取下一步行动建议"""
    pass
```

#### 8.2.3 推送历史 API

```python
# src/api/push_history.py

@router.get("/users/{user_id}/push-history")
async def get_push_history(
    user_id: str,
    limit: int = 20,
    offset: int = 0
):
    """获取推送历史"""
    pass

@router.post("/push/{push_id}/response")
async def record_push_response(
    push_id: str,
    response: PushResponseRequest
):
    """记录推送响应"""
    pass
```

### 8.3 调度器配置接口

```python
# src/agent/autonomous/scheduler.py

class AutonomousScheduler:
    """自主代理调度器"""
    
    SCHEDULE_CONFIG = {
        "hourly_scan": {
            "interval": 1,  # 每小时
            "tasks": ["scan_new_matches", "scan_stale_conversations"],
        },
        "daily_scan": {
            "interval": 24,  # 每天
            "time": "09:00",  # 9点执行
            "tasks": ["scan_user_activity", "daily_recommend_push"],
        },
        "weekly_scan": {
            "interval": 168,  # 每周
            "day": "sunday",
            "time": "10:00",
            "tasks": ["scan_relationship_health"],
        },
    }
    
    def start(self):
        """启动调度器"""
        pass
    
    def stop(self):
        """停止调度器"""
        pass
    
    def add_task(self, task_name: str, config: dict):
        """添加定时任务"""
        pass
    
    def trigger_immediate(self, task_name: str, user_id: str = None):
        """立即触发任务（用于事件驱动）"""
        pass
```

---

## 九、实现路线图

### 9.1 分阶段实施

```
阶段1：基础设施搭建（预计2天）
├── Day 1: 数据表创建
│   ├── agent_tasks 表
│   ├── push_history 表
│   ├── trigger_events 表
│   └── 现有表扩展（users, match_history）
│
├── Day 2: 调度器集成
│   ├── APScheduler 集成
│   ├── 基础定时任务配置
│   └── 任务执行框架搭建

阶段2：时机感知器实现（预计3天）
├── Day 3: 状态扫描器
│   ├── scan_new_matches
│   ├── scan_stale_conversations
│   ├── scan_user_activity
│
├── Day 4: 触发规则引擎
│   ├── 触发规则配置
│   ├── 条件评估逻辑
│   ├── 冷却时间检查
│
├── Day 5: 事件监听器
│   ├── 事件类型定义
│   ├── 事件处理逻辑
│   ├── 与现有系统事件集成

阶段3：任务追踪器实现（预计2天）
├── Day 6: 任务生命周期管理
│   ├── 任务创建
│   ├── 阶段更新
│   ├── 进度追踪
│
├── Day 7: 下一步行动推荐
│   ├── 行动规则配置
│   ├── 推荐算法
│   └── 用户响应记录

阶段4：推送执行器实现（预计2天）
├── Day 8: 推送策略与内容生成
│   ├── 推送策略选择
│   ├── 内容生成器
│   ├── 与现有工作流集成
│
├── Day 9: 推送效果追踪
│   ├── 推送记录
│   ├── 响应追踪
│   ├── 效果分析

阶段5：测试与优化（预计2天）
├── Day 10: 单元测试与集成测试
│   ├── 各组件单元测试
│   ├── 调度器测试
│   ├── 推送流程测试
│
├── Day 11: 效果评估与优化
│   ├── 推送效果分析
│   ├── 策略调整
│   ├── 性能优化
```

### 9.2 文件结构规划

```
src/agent/autonomous/
├── __init__.py
├── scheduler.py              # 调度器（APScheduler集成）
├── timing_perception.py      # 时机感知器
│   ├── UserStatusScanner     # 状态扫描器
│   ├── TriggerRuleEngine     # 触发规则引擎
│   └── EventListener         # 事件监听器
├── task_tracker.py           # 任务追踪器
│   ├── TaskLifecycleManager  # 任务生命周期管理
│   └── NextActionRecommender # 下一步行动推荐
├── push_executor.py          # 推送执行器
│   ├── PushStrategySelector  # 推送策略选择
│   ├── PushContentGenerator  # 推送内容生成
│   └── PushEffectTracker     # 推送效果追踪
├── engine.py                 # 自主代理引擎（整合所有组件）
└── config.py                 # 配置文件（触发规则、调度配置等）

src/api/
├── agent_preferences.py      # 用户推送偏好API
├── agent_task.py             # 任务状态API
└── push_history.py           # 推送历史API

src/db/
├── autonomous_models.py      # 新增数据模型
│   ├── AgentTaskDB
│   ├── PushHistoryDB
│   └── TriggerEventDB
```

---

## 十、效果评估

### 10.1 核心指标

| 指标类型 | 指标名称 | 目标值 | 测量方法 |
|----------|----------|--------|----------|
| **主动性指标** | 主动推送覆盖率 | > 90% | 有匹配的用户是否收到破冰推送 |
| | 对话停滞激活率 | > 50% | 停滞对话收到推送后是否有新消息 |
| | 用户激活召回率 | > 30% | 不活跃用户收到推送后是否回归 |
| **任务推进指标** | 破冰成功率 | > 40% | 收到破冰推送后是否开始对话 |
| | 约会转化率 | > 20% | 聊天用户是否成功约会 |
| | 平均任务周期缩短 | > 30% | 从匹配到约会的时间缩短 |
| **用户体验指标** | 推送点击率 | > 25% | 推送消息的点击打开率 |
| | 推送满意度 | > 80% | 用户对主动推送的评价 |
| | 骚扰投诉率 | < 1% | 用户投诉过度推送的比例 |

### 10.2 对比测试设计

```
A/B测试设计：

对照组（旧系统）：
├── 无主动推送
├── 用户主动发起一切
├── 记录：匹配→对话→约会转化率

实验组（新系统）：
├── 自主代理引擎激活
├── 主动推送破冰/话题/约会建议
├── 记录：同样转化率指标

对比维度：
1. 从匹配到第一次对话的时间
2. 从第一次对话到约会的转化率
3. 用户活跃度（登录频率、消息数）
4. 用户满意度问卷
```

### 10.3 成功标准

```
短期目标（1个月）：
├── 破冰推送覆盖率 > 90%
├── 推送点击率 > 20%
├── 无骚扰投诉

中期目标（3个月）：
├── 破冰成功率 > 40%
├── 对话停滞激活率 > 50%
├── 用户满意度 > 75%

长期目标（6个月）：
├── 约会转化率提升 > 20%
├── 平均任务周期缩短 > 30%
├── AI Native成熟度达到 L3
```

---

## 附录：推送文案模板示例

### A.1 破冰推送模板

```
【标题】您和 {name} 匹配成功！

【正文】
你们有 {n} 个共同兴趣：{interest_list}
要不要开始聊聊？我帮你准备了几个话题：
- {topic_1}
- {topic_2}

【CTA】开始对话
```

### A.2 对话停滞激活模板

```
【标题】您和 {name} 的对话停了 {hours} 小时

【正文】
对话陷入沉默了吗？别担心，我帮你想几个话题：
- {topic_1}
- {topic_2}
试试这些，说不定能重新激活你们的对话~

【CTA】继续聊天
```

### A.3 用户激活模板

```
【标题】好久不见，想你了~

【正文】
您有 {n} 个待处理的匹配对象：
- {name_1}：{description_1}
- {name_2}：{description_2}

回来看看吧，说不定缘分就在其中~

【CTA】回来看看
```

### A.4 约会准备模板

```
【标题】明天就要和 {name} 约会了！

【正文】
约会小贴士：
- 地点：{venue_name}（距离你 {distance}km）
- 建议话题：{topic_list}
- 注意事项：{tips}

祝你约会顺利！

【CTA】查看约会详情
```

---

## 总结

本方案借鉴 OpenClaw 心跳机制，引入「LLM 自主判断」范式，解决 Her 从「被动工具」向「主动代理」的转变问题。

### v2.0 核心设计

| 设计要点 | 说明 |
|----------|------|
| **HEARTBEAT_RULES.md** | 任务清单文件，替代硬编码规则，支持动态调整 |
| **心跳跳过机制** | 无到期规则时跳过 LLM 调用，节省 API 成本 |
| **HEARTBEAT_OK 协议** | 无事可做时静默返回，不推送消息 |
| **LLM 自主判断** | 让 AI 决定"是否需要行动"，而非代码硬编码 |
| **事件驱动触发** | match_created 等关键事件立即触发心跳 |

### 核心组件

1. **心跳调度器**：定时触发心跳（30m），读取 HEARTBEAT_RULES.md，筛选到期规则
2. **心跳执行器**：组装心跳提示词，调用 LLM，处理 HEARTBEAT_OK / 行动指令
3. **推送执行器**：解析行动指令，调用现有工作流和推送服务
4. **任务追踪器**：记录规则执行状态（last_run），追踪推送效果

### 实施效果预期

- 新匹配立即推送破冰建议（match_created 事件驱动）
- 对话停滞自动激活（LLM 自主判断 + 话题推送）
- 用户不活跃主动召回（24h 规则检查）
- 任务全程追踪推进（heartbeat_rule_state 表）

### 与 v1.0 的对比

| 维度 | v1.0（硬编码） | v2.0（心跳） |
|------|---------------|-------------|
| 规则定义 | Python 代码 | HEARTBEAT_RULES.md 文件 |
| 执行判断 | `if condition → push` | LLM 自主判断 |
| 灵活性 | 改规则需改代码 | 改文件即可 |
| 成本 | 每次扫描都执行 | 无到期规则则跳过 |

最终目标是让 Her 从 **L1 工具** 跨越到 **L3 代理**，成为真正「负责任的红娘」——主动感知、自主判断、适时出手。