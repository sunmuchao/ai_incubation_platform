---
name: matchmaking
description: Her 匹配全流程 - 直接调用 her_find_candidates 获取候选池和用户信息。无需先调用 her_get_profile。在用户说"帮我找对象"、"推荐几个"、"看看有谁"时直接使用 her_find_candidates。
license: MIT
allowed-tools:
  - her_find_candidates
  - her_get_profile
  - her_update_preference
  - her_record_feedback
  - her_get_feedback_history
---

# Her 匹配全流程（优化版）

**关键优化**：一次调用完成所有。直接调用 `her_find_candidates`，它会同时返回：
- 候选人列表
- 用户画像
- 缺失字段提示

## 执行流程（Agent 自主决策）

```
用户请求 → her_find_candidates（一次调用完成所有）
│
├─ 返回 candidates + user_profile + missing_fields
│
├─ 如果 missing_fields 较多 → 展示候选人 + 同时引导补充
│
├─ 如果 missing_fields 较少 → 直接展示候选人
│
└─ 如果信息完整 → 直接展示候选人
```

**优化**：her_find_candidates 已返回 `user_profile` 和 `missing_fields`，无需先调用 her_get_profile。

## 工具调用

### her_get_profile（可选检查）

**建议**：直接调用 her_find_candidates，它会同时返回用户信息和候选池。

仅在需要单独查看用户画像时调用。

参数：
- user_id: 不传或传 'me'（获取当前用户）

返回：
- display_id: 语义化标识符
- user_profile: 用户当前信息
- missing_fields: 缺失的基础字段（name、age、gender、location）
- missing_preferences: 缺失的偏好维度
- preference_status: 偏好完整性状态（complete/partial/incomplete）

用途：
- 单独检查用户信息完整性（一般不需要）

### her_find_candidates

获取候选匹配对象池。

参数：
- user_id: 不传或传 'me' 使用当前用户

返回：
- candidates: 候选人列表（display_id、姓名、年龄、地点、兴趣等）
- user_preferences: 用户偏好信息
- filter_applied: 已应用的硬约束

用途：展示匹配结果。

### her_update_preference

更新用户偏好到数据库。

参数：
- dimension: 偏好维度
  - accept_remote: 异地接受度（"只找同城"/"同城优先"/"接受异地"）
  - relationship_goal: 关系目标（"serious"/"marriage"/"dating"/"casual"）
  - preferred_age_min: 年龄下限（数字）
  - preferred_age_max: 年龄上限（数字）
  - preferred_location: 偏好地点（城市名）
- value: 偏好值

用途：记录用户在对话中表达的偏好。

## 展示候选人格式

按照 UserProfileCard 格式展示，包装为 GENERATIVE_UI。

```json
{
  "component_type": "UserProfileCard",
  "display_id": "从候选人数据取",
  "name": "从候选人数据取",
  "age": "从候选人数据取",
  "location": "从候选人数据取",
  "interests": "从候选人数据取（最多5个）",
  "bio": "从候选人数据取",
  "relationship_goal": "从候选人数据取"
}
```

**输出示例**：
```
我为你推荐 3 位候选人！

[GENERATIVE_UI]
{"component_type": "UserProfileCard", "display_id": "candidate_001", ...}
[/GENERATIVE_UI]

你想进一步了解哪位？
```

## 使用场景

当用户想要：
- 开始匹配流程
- 找匹配对象
- 获取推荐
- 设置匹配偏好
- 完善个人信息

口语化触发：
- "开始"
- "帮我找对象"
- "推荐几个"
- "设置偏好"
- "完善信息"

## 推荐优先级

1. 同城/附近城市优先
2. 兴趣匹配优先
3. 关系目标一致优先
4. 年龄范围在偏好内优先

Agent 根据候选池情况和用户偏好设置自主调整。

## 禁止行为

| ❌ 禁止 | 原因 |
|--------|------|
| 直接输出工具返回的原始 JSON | 需要按 UserProfileCard 格式展示 |
| 使用 Markdown 表格列出候选人 | 必须用 GENERATIVE_UI 卡片格式 |
| 使用 UUID 标识候选人 | 使用 display_id 或 name |
| 展示过多候选人（>5个） | 推荐 1-3 位 |
| 预定义"新用户"/"老用户"路径 | Agent 根据数据状态自主决策 |

---

## 反馈闭环（新增）

### her_record_feedback

记录用户对候选人的反馈，建立反馈闭环。

参数：
- candidate_id: 候选人 ID（display_id 或 user_id）
- feedback_type: 反馈类型（like/dislike/neutral/skip）
- reason: 不喜欢原因（仅 dislike 时需要）
- detail: 用户自定义原因（可选）

返回：
- recorded: 是否成功记录
- feedback_id: 反馈记录 ID
- message: 反馈确认消息

用途：
- 当用户表达"不喜欢""换一个"时记录反馈
- 后续推荐会避开用户不喜欢的原因

### Agent 行为指导

当用户说"不喜欢，换一个"时：

**Step 1：询问不喜欢原因**

> "能告诉我为什么吗？年龄差距太大？距离太远？兴趣不匹配？还是其他原因？"

**Step 2：记录反馈**

```
her_record_feedback(candidate_id="candidate_001", feedback_type="dislike", reason="年龄差距太大")
```

**Step 3：告知用户已记住偏好**

> "好的，已记住！后续推荐会避开年龄差距较大的候选人～"

**Step 4：推荐下一个候选人**

> "为您推荐另一位——钟静，27岁，天津..."

### 预设不喜欢原因

| 原因 | 说明 |
|------|------|
| 年龄差距太大 | 用户与候选人年龄差超过偏好范围 |
| 距离太远 | 异地距离超出接受范围 |
| 兴趣不匹配 | 兴趣爱好差异较大 |
| 没有眼缘 | 外观/第一印象不合适 |
| 关系目标不一致 | 关系目标冲突（如认真恋爱 vs 随便聊聊） |
| 其他 | 用户自定义原因 |

### her_get_feedback_history

获取用户反馈历史，用于分析偏好模式。

参数：
- feedback_type: 筛选类型（可选）
- limit: 返回数量限制（默认 20）

返回：
- feedbacks: 反馈列表
- statistics: 用户反馈统计汇总

---

> **Agent Native 原则**：先调用 her_get_profile 检查 missing_fields，根据信息完整性自主决定下一步。信息缺失 → 先引导补充；信息完整 → 直接展示候选人。一套流程，智能判断。用户表达不喜欢 → 先询问原因 → 记录反馈 → 推荐下一个 → 建立反馈闭环。