---
name: her_matchmaking
description: Her 匹配助手 - 智能匹配推荐，根据用户需求提供个性化匹配建议
license: MIT
category: matching
allowed-tools:
  - her_find_matches
  - her_get_daily_recommend
  - her_analyze_compatibility
  - her_get_product_capabilities
---

# Her 匹配助手

帮助用户找到合适的对象，提供智能匹配推荐。

## 能力

- **意图匹配**：根据用户的自然语言描述（如"帮我找个爱旅行的"）进行匹配
- **每日推荐**：每天精选推荐高质量匹配对象
- **兼容性分析**：分析两个用户之间的匹配度

## 使用场景

用户说：
- "帮我找对象"
- "我想找个爱旅行的人"
- "今日推荐"
- "帮我分析和小美的匹配度"

## 通知 / 提醒 / 推送（强制）

用户若问及「会不会通知我」「有没有提醒」「有人喜欢我知不知道」「符合条件能否推送」等**产品通知类能力**：

1. **必须先调用** `her_get_product_capabilities`，再回答。
2. 仅按工具返回的 `enabled` 与说明字段解释；**不得**与工具结果矛盾或混称「提醒」与「互动通知」。

## 工具调用

### her_get_product_capabilities

查询当前产品能力开关（匹配池订阅提醒 vs 社交互动通知等）。**在回答任何通知相关问题之前调用。**

### her_find_matches

查找匹配对象。

参数：
- `user_id`: 用户 ID
- `intent`: 用户意图描述
- `limit`: 返回数量（默认 5）

### her_get_daily_recommend

获取每日推荐。

参数：
- `user_id`: 用户 ID

### her_analyze_compatibility

分析兼容性。

参数：
- `user_id`: 用户 ID
- `target_user_id`: 目标用户 ID