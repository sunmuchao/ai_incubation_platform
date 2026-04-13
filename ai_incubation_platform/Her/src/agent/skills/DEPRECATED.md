# Skills 废弃声明

> **状态**: DEPRECATED  
> **废弃日期**: 2026-04-13  
> **替代方案**: DeerFlow Agent + her_tools

---

## 废弃原因

系统已升级为 **Agent Native 架构**：

**旧架构（已废弃）**：
- `src/agent/skills` - 30+ Skills，包含大量硬编码逻辑
- Skills 内部有模板、阈值、规则等硬编码
- IntentRouterSkill 基于关键词匹配

**新架构（推荐使用）**：
- DeerFlow Agent - LLM 作为决策大脑，理解意图、解读数据、生成建议
- `her_tools` - 纯数据查询工具，不含业务逻辑
- SOUL.md - Agent 的知识框架和决策规则

---

## 架构对比

```
【旧架构 - 已废弃】
用户消息 → IntentRouter（关键词匹配） → Skills（硬编码模板） → 返回模板

【新架构 - Agent Native】
用户消息 → DeerFlow Agent（LLM思考） → her_tools（数据查询） → Agent解读 → 个性化建议
```

---

## 替代方案

| 旧 Skill | 新方案 |
|----------|--------|
| IntentRouterSkill | DeerFlow Agent 自然语言理解（见 SOUL.md 意图理解能力） |
| SilenceBreakerSkill | DeerFlow Agent + `her_get_conversation_history`（见 SOUL.md 沉默打破能力） |
| GiftSuggestionSkill | DeerFlow Agent + `her_get_user`/`her_get_target_user`（见 SOUL.md 礼物建议能力） |
| EmotionAnalysisSkill | DeerFlow Agent + `her_get_conversation_history`（见 SOUL.md 情感分析能力） |
| TopicSuggestSkill | DeerFlow Agent + `her_suggest_topics`（见 SOUL.md 话题推荐能力） |
| IcebreakerSkill | DeerFlow Agent + `her_get_icebreaker`（见 SOUL.md 破冰开场能力） |
| DatePlanningSkill | DeerFlow Agent + `her_plan_date`（见 SOUL.md 约会策划能力） |
| RelationshipAnalysisSkill | DeerFlow Agent + `her_analyze_compatibility`（见 SOUL.md 关系分析能力） |
| ProfileCollectionSkill | DeerFlow Agent + `her_collect_profile` |

---

## 新的 her_tools 列表

所有工具都是**纯数据查询**，不含业务逻辑：

| 工具 | 功能 | 返回数据 |
|------|------|----------|
| `her_find_matches` | 查询匹配候选人 | 候选人列表、筛选条件 |
| `her_daily_recommend` | 查询今日推荐 | 活跃用户列表 |
| `her_analyze_compatibility` | 查询双方画像对比 | 双方画像、对比因素 |
| `her_analyze_relationship` | 查询关系数据 | 匹配记录、互动数据 |
| `her_suggest_topics` | 查询话题推荐所需数据 | 用户画像、对话历史 |
| `her_get_icebreaker` | 查询破冰所需数据 | 双方画像、匹配点 |
| `her_plan_date` | 查询约会策划所需数据 | 双方画像、活动选项 |
| `her_collect_profile` | 查询信息缺失情况 | 缺失字段列表 |
| `her_get_user` | 查询用户画像 | 用户完整资料 |
| `her_get_target_user` | 查询目标用户画像 | 目标用户完整资料 |
| `her_get_conversation_history` | 查询对话历史 | 消息列表、沉默信息 |

---

## 迁移指南

如果你想从旧 Skills 迁移到新架构：

1. **移除旧 Skills 调用**：不再使用 `src/agent/skills` 目录下的 Skills
2. **使用 DeerFlow Agent**：所有请求直接发送给 DeerFlow Agent
3. **Agent 会自动调用 her_tools**：获取数据后在 Prompt 中做决策
4. **SOUL.md 定义决策规则**：所有业务逻辑在 Agent 的 Prompt 中表达

---

## 保留的 Skills（暂时）

以下 Skills 暂时保留，但建议未来迁移：

- `profile_collection_skill.py` - 信息收集（可与 `her_collect_profile` 合并）
- 其他 Skills - 所有逻辑应迁移到 SOUL.md

---

## 注意事项

1. **不要新增 Skills**：新功能应添加到 SOUL.md 或 her_tools
2. **不要修改旧 Skills**：除非是紧急修复
3. **逐步迁移**：可以按模块逐步迁移到新架构

---

**记住**：Agent Native 的核心是"Agent 决策，工具查询"。所有业务逻辑应在 Agent 的 Prompt（SOUL.md）中表达，工具只返回原始数据。