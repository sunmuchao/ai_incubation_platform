---
name: her_relationship_coach
description: Her 关系教练 - 关系健康度分析，帮助用户理解和改善关系
license: MIT
category: relationship
allowed-tools:
  - her_analyze_relationship
  - her_get_relationship_advice
  - her_check_health
---

# Her 关系教练

帮助用户分析和改善与匹配对象的关系。

## 能力

- **关系分析**：分析用户与匹配对象的关系状态和进展
- **健康度检查**：评估关系的健康程度
- **建议生成**：根据关系状态提供改进建议

## 使用场景

用户说：
- "我和小美的关系怎么样"
- "分析我和TA的关系"
- "我们的关系健康吗"

## 工具调用

### her_analyze_relationship

分析关系状态。

参数：
- `user_id`: 用户 ID
- `match_id`: 匹配记录 ID

### her_get_relationship_advice

获取关系建议。

参数：
- `user_id`: 用户 ID
- `match_id`: 匹配记录 ID
- `issue_type`: 问题类型（可选）

### her_check_health

检查关系健康度。

参数：
- `user_id`: 用户 ID
- `match_id`: 匹配记录 ID