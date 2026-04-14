---
name: her_quick_start
description: Her 快速开始 - 新用户引导流程，智能收集用户偏好信息
license: MIT
category: profile
allowed-tools:
  - her_collect_profile
  - her_update_preference
  - her_find_matches
---

# Her 快速开始

当用户说"开始"或表达想要开始匹配时，智能引导收集必要信息。

## 触发场景

用户说以下内容时，应使用此流程：
- "开始"
- "我要开始"
- "开始吧"
- "我想开始匹配"
- "帮我找对象"（如果用户信息不完整）

## 执行流程

### Step 1: 检查用户信息完整性

调用 `her_collect_profile` 工具，检查用户是否有完整的关键信息：
- 年龄
- 性别
- 所在地
- 关系目标（relationship_goal）

### Step 2: 如果信息不完整

Agent 会收到一个 `question_card`，包含：
- `question`: 问题文本
- `question_type`: 问题类型（single_choice / tags / input）
- `options`: 选项列表（带 emoji 图标）
- `dimension`: 信息维度

**Agent 行为**：
1. 用友好的语气重复问题
2. 展示选项给用户（如果有选项）
3. 等待用户选择或输入

### Step 3: 用户回答后

**关键：用户回答后必须调用 `her_update_preference` 写入数据库！**

1. 先调用 `her_update_preference`，传入：
   - `user_id`: 用户 ID
   - `dimension`: 回答的维度（如 relationship_goal, accept_remote, preferred_age_min 等）
   - `value`: 用户回答的值

2. 然后再次调用 `her_collect_profile` 获取下一个问题

Agent 会收到：
- 下一个问题的 `question_card`（如果还有信息缺口）
- 或者匹配结果（如果信息已完整）

### Step 4: 信息收集完成

当用户信息完整后，自动调用 `her_find_matches` 展示匹配结果。

## 工具调用示例

### 首次调用

```
调用: her_collect_profile
参数: { user_id: "xxx", trigger_reason: "user_intent" }

返回: {
  need_collection: true,
  question_card: {
    question: "你想找什么样的关系呢？",
    question_type: "single_choice",
    options: [
      { value: "serious", label: "认真恋爱", icon: "💕" },
      { value: "marriage", label: "奔着结婚", icon: "💍" },
      { value: "dating", label: "轻松交友", icon: "☕" }
    ],
    dimension: "relationship_goal"
  },
  ai_message: "为了帮你找到合适的对象，我先了解一下你的需求~"
}
```

### 用户回答后

```
调用: her_collect_profile
参数: {
  user_id: "xxx",
  previous_answer: {
    dimension: "relationship_goal",
    answer: "serious"
  }
}

返回: {
  need_collection: true,
  question_card: {
    question: "你多大啦？",
    question_type: "single_choice",
    options: [...],
    dimension: "age"
  }
}
```

## Agent 行为指南

1. **自然对话**：不要机械地列出问题，用自然的语气引导
2. **展示选项**：如果有选项，用列表或卡片形式展示
3. **等待回答**：不要一次性问所有问题，逐步引导
4. **确认回答**：用户选择后，简短确认再继续下一个问题
5. **适时完成**：信息收集完成后，主动展示匹配结果

## 示例对话

```
用户: 开始

Agent:
好的！我来帮你开启寻爱之旅 💕

为了给你精准的匹配推荐，我先了解几个关键信息~

你想找什么样的关系呢？

[认真恋爱 💕] [奔着结婚 💍] [轻松交友 ☕] [随便聊聊 💭]

用户: 认真恋爱

Agent:
好的，认真恋爱~

那你多大啦？

[18-22岁 🌱] [23-26岁 🌿] [27-30岁 🌳] [31-35岁 🌲]

用户: 27-30岁

Agent:
记下了~

你在哪个城市？

[北京] [上海] [广州] [深圳] [杭州] [其他]

用户: 北京

Agent:
好的！信息收集完成~

为你推荐 3 位匹配对象：
...
```

## 注意事项

- 不要一次性列出所有问题，会让用户感到压力
- 每个问题都要有友好的引导语
- 选项要有 emoji 图标，增加亲和力
- 用户回答后，简短确认再继续