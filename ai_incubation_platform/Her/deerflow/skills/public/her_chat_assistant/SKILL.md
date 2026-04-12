---
name: her_chat_assistant
description: Her 聊天助手 - 破冰话题推荐、聊天优化建议，帮助用户开启和维持对话
license: MIT
category: communication
allowed-tools:
  - her_get_icebreaker
  - her_suggest_topics
  - her_optimize_message
---

# Her 聊天助手

帮助用户开启和维持对话，提供破冰话题和聊天建议。

## 能力

- **破冰建议**：根据匹配对象特点提供开场白建议
- **话题推荐**：根据对话进展推荐聊天话题
- **消息优化**：优化用户发送的消息内容

## 使用场景

用户说：
- "怎么开场"
- "有什么话题"
- "怎么破冰"

## 工具调用

### her_get_icebreaker

获取破冰建议。

参数：
- `user_id`: 用户 ID
- `match_id`: 匹配记录 ID

### her_suggest_topics

推荐话题。

参数：
- `user_id`: 用户 ID
- `match_id`: 匹配记录 ID
- `context`: 对话上下文（可选）

### her_optimize_message

优化消息。

参数：
- `user_id`: 用户 ID
- `message`: 原始消息
- `tone`: 语气（可选）