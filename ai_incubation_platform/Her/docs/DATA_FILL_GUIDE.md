# 生产环境数据填充说明

## 概述

本文档说明如何在生产环境中填充 `match_history` 和 `conversations` 表的数据，
以确保 PreCommunicationSkill 和相关功能正常工作。

---

## 数据表说明

### match_history 表

**用途**：存储用户的匹配历史记录，作为 PreCommunicationSkill 的会话数据源。

**关键字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(36) | 匹配记录唯一标识 |
| user_id_1 | VARCHAR(36) | 用户 A ID |
| user_id_2 | VARCHAR(36) | 用户 B ID |
| compatibility_score | FLOAT | 匹配度分数 (0-1) |
| status | VARCHAR(20) | 状态：pending/accepted/rejected/expired |
| match_reasoning | TEXT | 匹配理由 |
| common_interests | TEXT | 共同兴趣（JSON 数组） |
| interaction_count | INTEGER | 互动次数 |
| relationship_stage | VARCHAR(20) | 关系阶段：matched/chatting/dated/in_relationship |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### conversations 表

**用途**：存储用户之间的对话消息，作为 PreCommunicationSkill 的消息数据源。

**关键字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(36) | 消息唯一标识 |
| user_id_1 | VARCHAR(36) | 用户 A ID |
| user_id_2 | VARCHAR(36) | 用户 B ID |
| message_content | TEXT | 消息内容 |
| message_type | VARCHAR(20) | 消息类型：text/image/emoji/system |
| sender_id | VARCHAR(36) | 发送者 ID |
| topic_tags | TEXT | 话题标签（JSON 数组） |
| sentiment_score | FLOAT | 情感得分 (-1.0 到 1.0) |
| created_at | TIMESTAMP | 创建时间 |

---

## 数据填充策略

### 策略 1：用户行为驱动（推荐）

当用户在系统中执行以下行为时，自动创建数据：

1. **匹配成功时**：
   - 创建 `match_history` 记录
   - 状态设为 `accepted`
   - 记录匹配理由和共同兴趣

2. **用户发送消息时**：
   - 创建 `conversations` 记录
   - 关联到对应的 `match_history`
   - 更新 `interaction_count`

### 策略 2：批量导入（新系统上线时）

对于已有用户数据的历史系统，执行批量导入：

```sql
-- 示例：从现有用户表生成匹配记录
INSERT INTO match_history (id, user_id_1, user_id_2, compatibility_score, status, created_at)
SELECT 
  uuid() as id,
  u1.id as user_id_1,
  u2.id as user_id_2,
  0.75 as compatibility_score,  -- 默认匹配度
  'accepted' as status,
  NOW() as created_at
FROM users u1
JOIN users u2 ON u1.id != u2.id
WHERE u1.relationship_goal = u2.relationship_goal  -- 关系目标匹配
LIMIT 1000;  -- 控制数量
```

---

## 数据填充脚本示例

### Python 脚本（推荐）

```python
"""
生产环境数据填充脚本
运行方式：python scripts/fill_match_data.py --count 100
"""
import sys
sys.path.insert(0, 'src')

from db.database import SessionLocal
from db.models import MatchHistoryDB, ConversationDB, UserDB
from datetime import datetime
import uuid
import random

def fill_match_history(count: int = 100):
    """填充 match_history 表"""
    db = SessionLocal()
    
    # 获取活跃用户
    users = db.query(UserDB).filter(
        UserDB.is_active == True,
        UserDB.is_permanently_banned == False
    ).limit(50).all()
    
    if len(users) < 2:
        print("用户数量不足，无法生成匹配记录")
        return
    
    # 生成匹配记录
    for i in range(count):
        user_a = random.choice(users)
        user_b = random.choice([u for u in users if u.id != user_a.id])
        
        match = MatchHistoryDB(
            id=str(uuid.uuid4()),
            user_id_1=user_a.id,
            user_id_2=user_b.id,
            compatibility_score=random.uniform(0.6, 0.95),
            status=random.choice(['accepted', 'pending']),
            match_reasoning="系统自动匹配",
            common_interests='["旅行","美食","电影"]',
            interaction_count=random.randint(0, 50),
            relationship_stage=random.choice(['matched', 'chatting', 'dated']),
            created_at=datetime.now(),
        )
        db.add(match)
    
    db.commit()
    print(f"已生成 {count} 条匹配记录")

def fill_conversations(count: int = 500):
    """填充 conversations 表"""
    db = SessionLocal()
    
    # 获取匹配记录
    matches = db.query(MatchHistoryDB).filter(
        MatchHistoryDB.status == 'accepted'
    ).limit(100).all()
    
    if not matches:
        print("没有匹配记录，请先运行 fill_match_history")
        return
    
    # 模拟消息内容
    messages = [
        "你好，很高兴认识你！",
        "看了你的资料，觉得我们有很多共同兴趣~",
        "你平时喜欢做什么？",
        "我喜欢旅行，最近去了云南",
        "云南很美，我也想去！",
    ]
    
    for match in matches:
        for j in range(random.randint(3, 20)):
            sender = random.choice([match.user_id_1, match.user_id_2])
            
            conv = ConversationDB(
                id=str(uuid.uuid4()),
                user_id_1=match.user_id_1,
                user_id_2=match.user_id_2,
                message_content=random.choice(messages),
                message_type='text',
                sender_id=sender,
                topic_tags='["聊天"]',
                sentiment_score=random.uniform(-0.5, 1.0),
                created_at=datetime.now(),
            )
            db.add(conv)
    
    db.commit()
    print(f"已生成约 {count} 条对话记录")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=100)
    args = parser.parse_args()
    
    fill_match_history(args.count)
    fill_conversations(args.count * 5)
```

---

## 数据验证

填充后，验证数据完整性：

```sql
-- 验证 match_history 数据量
SELECT 
  COUNT(*) as total_matches,
  COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_matches,
  COUNT(CASE WHEN relationship_stage = 'chatting' THEN 1 END) as active_chats
FROM match_history;

-- 验证 conversations 数据量
SELECT 
  COUNT(*) as total_messages,
  COUNT(DISTINCT user_id_1) as unique_users
FROM conversations;

-- 验证数据关联
SELECT 
  mh.id,
  mh.compatibility_score,
  COUNT(c.id) as message_count
FROM match_history mh
LEFT JOIN conversations c ON (
  (c.user_id_1 = mh.user_id_1 AND c.user_id_2 = mh.user_id_2) OR
  (c.user_id_1 = mh.user_id_2 AND c.user_id_2 = mh.user_id_1)
)
GROUP BY mh.id
ORDER BY message_count DESC
LIMIT 10;
```

---

## 注意事项

1. **数据隐私**：确保填充的消息内容不包含真实用户数据
2. **数据量控制**：初始填充建议控制在 100-500 条匹配记录
3. **索引优化**：大量数据填充后，建议重建索引
4. **备份机制**：填充前备份原有数据

---

## 相关文档

- [PreCommunicationSkill 实现](../src/agent/skills/precommunication_skill.py)
- [数据库模型定义](../src/db/models.py)
- [架构问题修复记录](../docs/ARCHITECTURE_FIX_RECORDS.md)