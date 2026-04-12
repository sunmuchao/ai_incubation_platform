---
name: her_date_planning
description: Her 约会策划 - 约会地点推荐、活动策划，帮助用户安排完美的约会
license: MIT
category: dating
allowed-tools:
  - her_suggest_date_spots
  - her_plan_date
  - her_get_date_ideas
---

# Her 约会策划

帮助用户策划约会，推荐约会地点和活动。

## 能力

- **约会地点推荐**：根据用户位置和偏好推荐约会地点
- **约会策划**：根据关系阶段策划完整的约会方案
- **约会创意**：提供约会活动和话题建议

## 使用场景

用户说：
- "约会去哪里"
- "帮我策划约会"
- "有什么约会创意"

## 工具调用

### her_suggest_date_spots

推荐约会地点。

参数：
- `user_id`: 用户 ID
- `location`: 用户位置
- `date_type`: 约会类型（可选）

### her_plan_date

策划约会。

参数：
- `user_id`: 用户 ID
- `match_id`: 匹配记录 ID
- `preferences`: 偏好设置（可选）

### her_get_date_ideas

获取约会创意。

参数：
- `user_id`: 用户 ID
- `context`: 约会上下文（可选）