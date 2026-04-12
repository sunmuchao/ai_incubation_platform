# HEARTBEAT_RULES.md - Her 心跳任务清单

> 借鉴 OpenClaw 心跳机制，定义 Her 主动代理的定期检查规则
> 
> 规则会定期执行，由 LLM 自主判断是否需要采取行动

---

## rules: 定期检查规则

每个规则包含：
- `name`: 规则名称（唯一标识）
- `interval`: 执行间隔（30m = 30分钟，1h = 1小时，24h = 24小时）
- `prompt`: 执行时注入 LLM 的提示内容
- `action_type`: 如果需要行动，默认的行动类型

### 规则列表

```yaml
- name: check_new_matches
  interval: 30m
  prompt: |
    检查是否有新匹配成功但未推送破冰建议的用户。
    
    检查条件：
    - match_history 表中 created_at 在过去24小时内
    - icebreaker_pushed = FALSE 或 NULL
    - 用户开启了推送通知（push_enabled = TRUE）
    
    如果发现有符合条件的匹配，需要推送破冰建议。
  action_type: icebreaker

- name: check_stale_conversations
  interval: 1h
  prompt: |
    检查是否有对话停滞超过72小时的匹配，需要推送话题激活。
    
    检查条件：
    - match_history 表中 relationship_stage = 'chatting'
    - last_message_at 超过72小时
    - 过去24小时内未推送过话题激活（last_stale_push_at < now - 24h）
    - 用户开启了推送通知
    
    如果发现有符合条件的匹配，推送话题建议帮助激活对话。
    注意：同一匹配24小时内不重复推送。
  action_type: topic_suggestion

- name: check_user_activity
  interval: 24h
  prompt: |
    检查是否有超过7天未活跃的用户，需要推送激活提醒。
    
    检查条件：
    - users 表中 last_active_at 超过7天
    - 用户有待处理的匹配（match_history 中有未完成的匹配）
    - 用户开启了推送通知
    - 过去3天内未推送过激活提醒
    
    如果发现有符合条件的用户，推送关心的激活提醒。
    注意：同一用户3天内不重复推送，避免骚扰。
  action_type: activation_reminder

- name: check_pending_dates
  interval: 1h
  prompt: |
    检查是否有24小时内即将进行的约会，推送准备提醒。
    
    检查条件：
    - autonomous_date_plans 表中 status = 'confirmed'
    - 约会时间在接下来24小时内
    - 用户开启了推送通知
    - 未推送过约会准备提醒
    
    如果发现有符合条件的约会，推送约会准备建议。
  action_type: date_preparation

- name: check_relationship_health
  interval: 168h  # 每周一次
  prompt: |
    检查关系健康度，为已建立关系的用户推送健康报告。
    
    检查条件：
    - match_history 表中 relationship_stage = 'dating' 或 'in_relationship'
    - 距离上次健康报告推送超过7天
    - 用户开启了推送通知
    
    如果发现有符合条件的匹配，生成并推送关系健康度报告。
  action_type: relationship_health
```

---

## 心跳指导原则

以下原则会注入 LLM 心跳提示词，指导 AI 如何判断和行动：

```
- 如果无事需要处理，回复 HEARTBEAT_OK
- 如果需要推送，必须明确说明：
  - 推送对象（用户ID、匹配ID）
  - 推送内容类型（icebreaker/topic/activation/date/health）
  - 推送理由（为什么需要推送）
- 推送内容要个性化，避免模板化
- 注意用户推送偏好设置：
  - push_enabled 是否开启
  - push_proactive_level 主动程度（high/medium/low）
  - push_quiet_hours 免打扰时段（22:00-08:00）
- 检查是否有重复推送，避免骚扰用户
- 优先级排序：icebreaker > date > topic > activation > health
- 一次心跳最多推送3条消息，避免批量轰炸
```

---

## 响应格式约定

### HEARTBEAT_OK 格式（无事可做）

```
HEARTBEAT_OK
```

或带简短说明：

```
HEARTBEAT_OK
本次检查无新增匹配，对话活跃状态正常。
```

### 行动指令格式（需要推送）

```
ACTION_REQUIRED
推送对象: user_123, match_456
推送类型: icebreaker
推送理由: 用户user_123与用户user_456于2小时前匹配成功，双方尚未开始对话，建议推送破冰话题。
推荐内容: [
  "你们有3个共同兴趣：旅行、美食、电影，可以从这些话题开始聊",
  "可以问问对方最近看了什么好电影"
]
```

---

## 规则修改指南

修改此文件即可调整心跳行为，无需修改代码：

1. **新增规则**：在 rules 列表添加新条目
2. **调整间隔**：修改 interval 值
3. **调整提示**：修改 prompt 内容
4. **删除规则**：删除对应条目

修改后下次心跳周期自动生效。

---

## 统计信息

心跳执行统计信息会记录在 `heartbeat_rule_state` 表：

- `last_run_at`: 最后执行时间
- `last_result`: 最后结果（executed/skipped/heartbeat_ok）
- `run_count`: 执行次数
- `action_count`: 实际行动次数
- `skip_count`: 跳过次数（无到期规则）

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-04-11 | 初始版本，定义5个核心规则 |