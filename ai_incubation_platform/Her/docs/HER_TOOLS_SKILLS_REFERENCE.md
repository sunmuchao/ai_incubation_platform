# Her Tools & Skills 参考文档

> **版本**: v3.2
> **更新日期**: 2026-04-17
> **架构**: Agent Native（Agent 决策，Tool 执行）

---

## 目录

1. [架构概述](#架构概述)
2. [Tool vs Skill 定义](#tool-vs-skill-定义)
3. [Tools 列表](#tools-列表)
4. [Skills 列表](#skills-列表)
5. [典型流程](#典型流程)
6. [设计原则](#设计原则)

---

## 架构概述

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOUL.md（Agent 人格）                        │
│  角色：智能红娘                                                  │
│  原则：诚实、理解意图、主动补齐                                    │
│  Skills 引用：告诉 Agent 有哪些 Skills 可用                       │
└─────────────────────────────────────────────────────────────────┘
                           ↓ 注入
┌─────────────────────────────────────────────────────────────────┐
│                     Skills（规则文档）                            │
│  场景化处理规则                                                  │
│  告诉 Agent：在什么场景下，调用哪些 Tool，怎么处理                │
└─────────────────────────────────────────────────────────────────┘
                           ↓ 指导
┌─────────────────────────────────────────────────────────────────┐
│                     Agent（决策大脑）                             │
│  理解意图 → 选择 Tool → 解读数据 → 生成回复                       │
│  Agent 自己决策：筛选、排序、推荐几位                             │
└─────────────────────────────────────────────────────────────────┘
                           ↓ 调用
┌─────────────────────────────────────────────────────────────────┐
│                     Tools（执行器）                               │
│  查询数据库 → 返回原始数据                                        │
│  Tool 只执行，不做业务判断                                        │
└─────────────────────────────────────────────────────────────────┘
                           ↓ 依赖
┌─────────────────────────────────────────────────────────────────┐
│                     Database（数据层）                            │
│  users, matches, messages 等                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tool vs Skill 定义

| 维度 | Tool | Skill |
|------|------|-------|
| **是什么** | 可调用接口（Python 函数） | 规则文档（SKILL.md） |
| **做什么** | 执行操作、查询数据 | 告诉 Agent 怎么做 |
| **输出** | JSON 数据 | Prompt 规则 |
| **调用方式** | Agent 调用，传入参数 | Agent 参考规则，不传参 |
| **示例** | `her_find_matches(user_id)` | `her_match_display/SKILL.md` |

**一句话总结**：
- **Tool** = 干活的（查询、执行）
- **Skill** = 教怎么干的（规则、步骤）

---

## Tools 列表

### 分类概览

| 分类 | Tools |
|------|-------|
| **匹配工具** | `her_find_matches`, `her_daily_recommend` |
| **分析工具** | `her_analyze_compatibility`, `her_analyze_relationship` |
| **沟通工具** | `her_suggest_topics`, `her_get_icebreaker`, `her_plan_date` |
| **资料工具** | `her_collect_profile`, `her_update_preference` |
| **用户工具** | `her_get_user`, `her_get_target_user`, `her_get_conversation_history`, `her_initiate_chat` |
| **查询工具** | `her_safe_query`, `her_find_user_by_name` |
| **展示工具** | `her_display_user_profile` |
| **能力工具** | `her_get_product_capabilities` |

---

### 1. 匹配工具

#### her_find_matches

| 属性 | 值 |
|------|-----|
| **名称** | `her_find_matches` |
| **文件** | `match_tools.py` |
| **描述** | 获取候选匹配对象池（纯数据） |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID（默认当前用户） |
| `intent` | string | 否 | 用户意图描述 |

**返回**：
```json
{
  "success": true,
  "data": {
    "candidates": [
      {
        "user_id": "xxx",
        "name": "余静",
        "age": 26,
        "gender": "female",
        "location": "无锡",
        "interests": ["跑步", "健身"],
        "bio": "...",
        "relationship_goal": "结婚",
        "confidence_level": "high",
        "confidence_score": 70,
        "confidence_icon": "🌟"
      }
    ],
    "query_request_id": "uuid",
    "user_preferences": {
      "preferred_age_min": 25,
      "preferred_age_max": 30,
      "preferred_location": "无锡",
      "accept_remote": "no",
      "relationship_goal": "marriage",
      "user_gender": "male",
      "user_location": "无锡",
      "target_gender": "female"
    },
    "filter_applied": {
      "hard_constraints": ["排除封禁用户", "性别过滤（female）"],
      "soft_constraints": "由 Agent 自行判断"
    }
  }
}
```

**硬约束（Tool 执行）**：
- 排除封禁用户
- 排除自己
- 排除测试账号
- 性别过滤（异性恋默认排除同性）
- 地点硬约束（用户明确不接受异地 → 只查同城）

**软约束（Agent 决策）**：
- 年龄范围筛选
- 地点匹配优先级
- 关系目标匹配
- 推荐顺序

---

#### her_daily_recommend

| 属性 | 值 |
|------|-----|
| **名称** | `her_daily_recommend` |
| **文件** | `match_tools.py` |
| **描述** | 获取今日活跃用户推荐 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |

**返回**：
```json
{
  "success": true,
  "data": {
    "component_type": "MatchCardList",
    "recommendations": [
      {"user_id": "...", "name": "...", "age": ..., "location": "...", "interests": [...]}
    ],
    "total": 3
  }
}
```

---

### 2. 分析工具

#### her_analyze_compatibility

| 属性 | 值 |
|------|-----|
| **名称** | `her_analyze_compatibility` |
| **文件** | `analysis_tools.py` |
| **描述** | 获取两个用户的画像对比数据 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |
| `target_user_id` | string | 是 | 目标用户 ID |

**返回**：
```json
{
  "success": true,
  "data": {
    "user_a": {"name": "...", "age": ..., "interests": [...]},
    "user_b": {"name": "...", "age": ..., "interests": [...]},
    "comparison_factors": [
      {"factor": "年龄差距", "value": "2岁", "user_a": 28, "user_b": 26},
      {"factor": "所在地", "user_a": "无锡", "user_b": "无锡", "same_city": true},
      {"factor": "兴趣爱好", "common": ["健身", "跑步"]}
    ]
  }
}
```

---

#### her_analyze_relationship

| 属性 | 值 |
|------|-----|
| **名称** | `her_analyze_relationship` |
| **文件** | `analysis_tools.py` |
| **描述** | 分析关系健康度 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |
| `match_id` | string | 是 | 匹配对象 ID |

**返回**：
```json
{
  "success": true,
  "data": {
    "user_a": {...},
    "user_b": {...},
    "match_info": {
      "status": "active",
      "created_at": "...",
      "compatibility_score": 0.92
    }
  }
}
```

---

### 3. 沟通工具

#### her_suggest_topics

| 属性 | 值 |
|------|-----|
| **名称** | `her_suggest_topics` |
| **文件** | `conversation_tools.py` |
| **描述** | 获取聊天话题推荐所需的用户画像数据 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |
| `match_id` | string | 否 | 匹配对象 ID |
| `context` | string | 否 | 对话上下文 |

**返回**：
```json
{
  "success": true,
  "data": {
    "component_type": "ConversationGuideCard",
    "intent_type": "topic_request",
    "user_profile": {"interests": [...], "location": "..."},
    "target_profile": {"interests": [...], "location": "..."},
    "conversation_history": [...],
    "analysis": {
      "common_interests": ["健身"],
      "unique_user_interests": ["编程"],
      "unique_target_interests": ["瑜伽"]
    }
  }
}
```

---

#### her_get_icebreaker

| 属性 | 值 |
|------|-----|
| **名称** | `her_get_icebreaker` |
| **文件** | `conversation_tools.py` |
| **描述** | 获取破冰开场白所需的匹配点数据 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |
| `match_id` | string | 否 | 目标用户 ID |
| `target_name` | string | 否 | 目标用户名字 |

**返回**：
```json
{
  "success": true,
  "data": {
    "component_type": "ConversationGuideCard",
    "intent_type": "icebreaker_request",
    "user_profile": {...},
    "target_profile": {...},
    "match_points": [
      {"type": "interest", "content": ["健身"]},
      {"type": "location", "content": "无锡"}
    ]
  }
}
```

---

#### her_plan_date

| 属性 | 值 |
|------|-----|
| **名称** | `her_plan_date` |
| **文件** | `conversation_tools.py` |
| **描述** | 获取约会策划所需的用户画像和活动数据 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |
| `match_id` | string | 否 | 约会对象 ID |
| `target_name` | string | 否 | 约会对象名字 |
| `location` | string | 否 | 约会地点范围 |
| `preferences` | string | 否 | 偏好设置 |

**返回**：
```json
{
  "success": true,
  "data": {
    "user_profile": {"interests": [...], "location": "..."},
    "target_profile": {...},
    "date_context": {
      "location": "无锡",
      "common_interests": ["健身"]
    },
    "activity_options": [
      {"interest": "美食", "activities": ["餐厅", "咖啡厅"]}
    ]
  }
}
```

---

### 4. 资料工具

#### her_collect_profile

| 属性 | 值 |
|------|-----|
| **名称** | `her_collect_profile` |
| **文件** | `profile_tools.py` |
| **描述** | 查询用户信息缺失情况 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |
| `trigger_reason` | string | 否 | 触发原因 |

**返回**：
```json
{
  "success": true,
  "data": {
    "need_collection": true,
    "missing_fields": ["occupation", "interests"],
    "missing_preferences": ["age_preference"],
    "user_profile": {...},
    "preference_status": "partial"
  }
}
```

---

#### her_update_preference

| 属性 | 值 |
|------|-----|
| **名称** | `her_update_preference` |
| **文件** | `profile_tools.py` |
| **描述** | 更新用户偏好到数据库 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |
| `dimension` | string | 是 | 偏好维度 |
| `value` | string | 是 | 偏好值 |

**支持的维度**：
- `accept_remote`（异地接受度）
- `relationship_goal`（关系目标）
- `preferred_age_min/max`（年龄偏好）
- `preferred_location`（地点偏好）

**返回**：
```json
{
  "success": true,
  "data": {
    "updated_dimension": "accept_remote",
    "updated_value": "只找同城"
  }
}
```

---

### 5. 用户工具

#### her_get_user

| 属性 | 值 |
|------|-----|
| **名称** | `her_get_user` |
| **文件** | `user_tools.py` |
| **描述** | 获取用户画像数据 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |

**返回**：
```json
{
  "success": true,
  "data": {
    "user_profile": {"name": "...", "age": ..., "interests": [...]}
  }
}
```

---

#### her_get_target_user

| 属性 | 值 |
|------|-----|
| **名称** | `her_get_target_user` |
| **文件** | `user_tools.py` |
| **描述** | 获取目标用户详细画像 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target_user_id` | string | 是 | 目标用户 ID |

**返回**：
```json
{
  "success": true,
  "data": {
    "component_type": "UserProfileCard",
    "selected_user": {...}
  }
}
```

---

#### her_get_conversation_history

| 属性 | 值 |
|------|-----|
| **名称** | `her_get_conversation_history` |
| **文件** | `user_tools.py` |
| **描述** | 获取对话历史记录 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户 ID |
| `match_id` | string | 是 | 匹配对象 ID |
| `limit` | int | 否 | 返回数量（默认 20） |

**返回**：
```json
{
  "success": true,
  "data": {
    "messages": [...],
    "total": 15,
    "silence_info": {
      "last_message_time": "...",
      "silence_seconds": 3600
    }
  }
}
```

---

#### her_initiate_chat

| 属性 | 值 |
|------|-----|
| **名称** | `her_initiate_chat` |
| **文件** | `user_tools.py` |
| **描述** | 准备发起聊天的目标用户信息 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target_user_id` | string | 是 | 目标用户 ID |
| `context` | string | 否 | 上下文 |
| `compatibility_score` | int | 否 | 匹配度分数 |

**返回**：
```json
{
  "success": true,
  "data": {
    "component_type": "ChatInitiationCard",
    "target_user_id": "...",
    "target_user_name": "余静",
    "target_user_avatar": "...",
    "compatibility_score": 92
  }
}
```

---

### 6. 查询工具

#### her_safe_query

| 属性 | 值 |
|------|-----|
| **名称** | `her_safe_query` |
| **文件** | `query_tools.py` |
| **描述** | 执行安全的 SQL 查询，用于补齐缺失信息 |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sql` | string | 是 | SQL 查询语句（必须是 SELECT） |

**安全边界**：
- 只允许 SELECT
- 只允许白名单表：`users`, `profiles`, `matches`, `messages`
- 自动添加 LIMIT 10
- 禁止 DELETE/DROP/UPDATE/INSERT

**返回**：
```json
{
  "success": true,
  "data": {
    "rows": [...],
    "columns": ["id", "name"],
    "row_count": 3
  }
}
```

---

#### her_find_user_by_name

| 属性 | 值 |
|------|-----|
| **名称** | `her_find_user_by_name` |
| **文件** | `query_tools.py` |
| **描述** | 根据名字查找用户，获取 user_id |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 用户名字（支持模糊匹配） |
| `location` | string | 否 | 城市 |
| `limit` | int | 否 | 返回数量（默认 5） |

**返回**：
```json
{
  "success": true,
  "data": {
    "users": [
      {"user_id": "...", "name": "余静", "age": 26, "location": "无锡"}
    ],
    "total": 1
  }
}
```

---

### 7. 展示工具

#### her_display_user_profile

| 属性 | 值 |
|------|-----|
| **名称** | `her_display_user_profile` |
| **文件** | `display_tools.py` |
| **描述** | 展示用户卡片（GENERATIVE_UI 格式） |

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 单个用户 ID |
| `user_ids` | string | 否 | 多个用户 ID（逗号分隔） |

**返回（单个用户）**：
```json
{
  "success": true,
  "data": {
    "component_type": "UserProfileCard",
    "user_id": "...",
    "name": "余静",
    "age": 26,
    "location": "无锡",
    "interests": ["跑步", "健身"],
    "bio": "...",
    "confidence_level": "high",
    "confidence_score": 70,
    "confidence_icon": "🌟"
  }
}
```

**返回（多个用户）**：
```json
{
  "success": true,
  "data": {
    "component_type": "UserProfileCardList",
    "cards": [...],
    "total": 3
  }
}
```

---

### 8. 能力工具

#### her_get_product_capabilities

| 属性 | 值 |
|------|-----|
| **名称** | `her_get_product_capabilities` |
| **文件** | `capabilities_tools.py` |
| **描述** | 获取产品能力开关状态 |

**参数**：无

**返回**：
```json
{
  "success": true,
  "data": {
    "product_capabilities": {
      "version": "1.0",
      "capabilities": [
        {"id": "match_pool_subscription", "enabled": true, "description_zh": "..."}
      ]
    }
  }
}
```

---

## Skills 列表

### 分类概览

| Skill | 场景 | 关键规则 |
|-------|------|---------|
| `her_match_display` | 展示候选人 | 调用 `her_display_user_profile` 工具 |
| `her_matching_flow` | 匹配流程 | 从找对象到破冰的完整编排 |
| `her_dating_coach` | 约会教练 | 约会前准备到约会后复盘 |
| `her_relationship_guide` | 关系指导 | 关系健康度分析到冲突调解 |

---

### 1. her_match_display

**文件**: `skills/public/her/match_display/SKILL.md`

**描述**: 候选人展示规则

**核心规则**:
- 展示候选人时，必须调用 `her_display_user_profile` 工具
- 不要自己拼接 GENERATIVE_UI

**触发场景**:
- 已通过 `her_find_matches` 获取候选池
- 已完成筛选和决策
- 准备输出给用户时

**执行流程**:
```
1. 用户："帮我找对象"
2. Agent 调用 her_find_matches → 获取候选池
3. Agent 筛选、决策 → 确定推荐 2-3 位
4. Agent 调用 her_display_user_profile(user_ids="id1,id2,id3")
5. 工具返回 UserProfileCardList 格式
6. Agent 直接输出 + 简短介绍
```

**禁止行为**:
- ❌ 自己拼接 GENERATIVE_UI
- ❌ Markdown 表格列出候选人
- ❌ 文本列表（"**朱彤** · 29岁"）
- ❌ 直接输出 her_find_matches 结果

---

### 2. her_matching_flow

**文件**: `skills/public/her/matching_flow/SKILL.md`

**描述**: 智能匹配流程 - 从找对象到破冰建议的完整编排

**能力**:
- 匹配推荐
- 兼容性分析
- 破冰建议
- 约会策划
- 偏好更新

**可用工具**:
- `her_find_matches`
- `her_analyze_compatibility`
- `her_get_icebreaker`
- `her_plan_date`
- `her_update_preference`

---

### 3. her_dating_coach

**文件**: `skills/public/her/dating_coach/SKILL.md`

**描述**: 约会教练流程 - 约会前准备到约会后复盘

**能力**:
- 约会前准备：地点建议、话题储备、开场白准备
- 约会中支持：话题切换建议、气氛调节技巧
- 约会后复盘：关系进展分析、下一步建议

**可用工具**:
- `her_plan_date`
- `her_suggest_topics`
- `her_get_icebreaker`
- `her_analyze_relationship`

---

### 4. her_relationship_guide

**文件**: `skills/public/her/relationship_guide/SKILL.md`

**描述**: 关系指导流程 - 关系健康度分析到冲突调解

**能力**:
- 关系分析
- 健康度检查
- 建议生成

**可用工具**:
- `her_analyze_relationship`
- `her_analyze_compatibility`
- `her_suggest_topics`

---

## 典型流程

### 流程 1：用户找对象

```
用户："帮我找对象"
    ↓
Agent 理解意图：匹配请求
    ↓
Agent 调用 her_find_matches → 获取候选池（最多 30 位）
    ↓
Agent 参考 user_preferences 筛选 → 决定推荐 2-3 位
    ↓
Agent 调用 her_display_user_profile(user_ids="id1,id2,id3")
    ↓
Tool 返回 UserProfileCardList 格式
    ↓
Agent 输出："我为你推荐 3 位候选人！" + 卡片 + "请告诉我你的选择"
```

### 流程 2：查看某人详情

```
用户："介绍一下余静"
    ↓
Agent 理解意图：查看详情
    ↓
Agent 只有名字"余静"，缺少 user_id
    ↓
Agent 调用 her_find_user_by_name(name="余静") → 获取 user_id
    ↓
Agent 调用 her_display_user_profile(user_id="xxx")
    ↓
Agent 输出：卡片 + "你想进一步了解她吗？"
```

### 流程 3：匹配度分析

```
用户："我和余静匹配度怎么样"
    ↓
Agent 理解意图：兼容性分析
    ↓
Agent 调用 her_find_user_by_name → 获取 user_id
    ↓
Agent 调用 her_analyze_compatibility(target_user_id="xxx")
    ↓
Tool 返回对比数据（年龄差距、共同兴趣、地点等）
    ↓
Agent 分析数据 → 生成匹配度结论 + 建议
```

---

## 设计原则

### Tool 设计原则

1. **只返回原始数据**
   - Tool 不做业务判断
   - Tool 不生成建议模板
   - Tool 不预设输出格式（展示工具除外）

2. **硬约束在 Tool 中执行**
   - 安全边界（排除封禁用户）
   - 商业限制（付费、次数限制）
   - 数据校验（必填字段）
   - 性别过滤（异性恋硬约束）

3. **软约束由 Agent 决策**
   - 年龄范围筛选
   - 地点优先级
   - 关系目标匹配
   - 推荐顺序和数量

### Skill 设计原则

1. **告诉 Agent 怎么做**
   - 不包含 Python 代码
   - 是规则文档，不是执行器
   - 引导 Agent 选择合适的 Tool

2. **场景化规则**
   - 定义触发场景
   - 定义执行流程
   - 定义禁止行为

3. **与 SOUL.md 分工**
   - SOUL.md：Agent 人格、核心原则
   - Skill：场景化处理规则

### Agent 决策原则

1. **理解意图而非匹配关键词**
2. **诚实原则：工具返回什么 → 你说什么**
3. **信息缺失时主动补齐**
4. **自主决策筛选、排序、推荐数量**

---

## 文件位置

| 类型 | 路径 |
|------|------|
| **Tool 文件** | `deerflow/backend/packages/harness/deerflow/community/her_tools/*.py` |
| **Skill 文件** | `deerflow/skills/public/her/*/SKILL.md` |
| **SOUL.md** | `deerflow/backend/.deer-flow/SOUL.md` |
| **工具注册** | `deerflow/config.yaml` |

---

## 更新记录

| 版本 | 日期 | 改动 |
|------|------|------|
| v3.2 | 2026-04-17 | 新增 `her_display_user_profile` 展示工具，分离展示层和决策层 |
| v3.1 | 2026-04-16 | 新增 `her_safe_query` 安全查询工具，Agent 可自主补齐信息 |
| v3.0 | 2026-04-15 | 模块化拆分 her_tools，Agent Native 重构 |
| v2.0 | 2026-04-10 | 移除硬编码模板，Agent 自己生成建议 |
| v1.0 | 2026-04-01 | 初始版本，硬编码模板 |