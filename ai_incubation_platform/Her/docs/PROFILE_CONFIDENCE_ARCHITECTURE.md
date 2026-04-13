# 用户置信度评估系统架构设计

> **版本**: v1.30.0
> **日期**: 2026-04-13
> **状态**: 已实现

## 概述

用户置信度评估系统是一个**多维度的概率性置信度评估框架**，用于判断用户基础信息的可信程度，帮助用户更安全地进行匹配。

### 核心理念

**非二元验证，而是概率性置信度评估**：
- 传统验证：通过/未通过（硬验证）
- 置信度评估：0-100% 可信度区间（软验证）

### 设计动机

**五问法分析**：

```
问题现象：用户注册后填写的基础信息缺乏真伪验证
├─ 为什么 1: 注册只做格式校验，不做真伪校验
├─ 为什么 2: 真伪校验需要多源交叉验证，架构未设计此能力
├─ 为什么 3: 外部 API 验证成本高、用户配合度低
├─ 为什么 4: 缺乏"轻量级置信度评估"的设计思路
└─ 为什么 5: 验证体系设计为"二元验证"，缺乏概率性判断

根本对策：建立多维置信度评估框架，后台自动计算，无需用户配合
```

---

## 系统架构

### 1. 置信度计算公式

```
overall_confidence = base_score (0.3)
  + identity_verified × 0.25      # 身份验证
  + cross_validation × 0.20       # 交叉验证
  + behavior_consistency × 0.15   # 行为一致性
  + social_endorsement × 0.10     # 社交背书
```

### 2. 各维度评估逻辑

#### 2.1 身份验证置信度 (0-1)

| 验证类型 | 分数贡献 |
|---------|---------|
| 实名认证 | +0.4 |
| 人脸核身 | +0.3 |
| 手机验证 | +0.15 |
| 邮箱验证 | +0.10 |
| 学历认证 | +0.15 |
| 职业认证 | +0.10 |

#### 2.2 交叉验证置信度 (0-1)

**规则一：年龄-学历匹配**

```python
# 假设毕业年龄
AGE_EDUCATION_EXPECTED_GRADUATION = {
    "high_school": 18,
    "college": 20,
    "bachelor": 22,
    "master": 25,
    "phd": 28,
}

# 异常判断
if user_age - expected_graduation_age < -2:
    # 年龄小于预期毕业年龄，高异常
    severity = "high"

if user_age - expected_graduation_age > 15:
    # 年龄差异过大，中异常
    severity = "medium"
```

**规则二：职业-收入匹配**

```python
# 职业收入范围（月薪，千元）
OCCUPATION_INCOME_RANGES = {
    "student": (0, 10),
    "tech": (10, 100),
    "finance": (15, 200),
    "education": (5, 30),
    ...
}

# 异常判断
if user_income_max < expected_min - 5:
    # 收入明显低于职业预期，高异常

if user_income_min > expected_max + 10:
    # 收入明显高于职业预期，低异常（可能是高管）
```

**规则三：地理-活跃时间匹配**

- 分析用户声称地理位置与实际活跃时间
- 例：声称北京但凌晨3-5点频繁活跃（非北京时区）→ 异常

#### 2.3 行为一致性置信度 (0-1)

| 检查项 | 说明 |
|-------|------|
| 兴趣-浏览匹配 | 声称兴趣与实际浏览内容的一致程度 |
| 性格-聊天匹配 | 声称性格与聊天风格的一致程度 |

#### 2.4 社交背书置信度 (0-1)

| 来源 | 分数贡献 |
|-----|---------|
| 邀请码注册 | +0.25 |
| 朋友推荐 | +0.30 |
| 好评率 > 70% | +0.20 |
| 好评率 50-70% | +0.10 |
| 好评率 < 30% | -0.10 |

#### 2.5 时间积累置信度 (0-1)

| 来源 | 计算逻辑 |
|-----|---------|
| 注册时长 | 每100天 +0.1，最多 +0.3 |
| 活跃天数 | 每100天 +0.1，最多 +0.2 |
| 画像完善度 | 100% → +0.5 |

---

## 置信度等级

| 等级 | 分数范围 | 名称 | 描述 | UI 颜色 |
|------|---------|------|------|--------|
| very_high | 80-100% | 极可信 | 信息经过多重验证 | 金色 💎 |
| high | 60-80% | 较可信 | 信息一致性良好 | 绿色 🌟 |
| medium | 40-60% | 普通用户 | 基本信息已验证 | 蓝色 ✓ |
| low | 0-40% | 需谨慎 | 信息存在异常标记 | 橙色 ⚠️ |

---

## 数据模型

### ProfileConfidenceDetailDB

```python
class ProfileConfidenceDetailDB(Base):
    __tablename__ = "profile_confidence_details"

    # 总置信度
    overall_confidence = Column(Float, default=0.3)
    confidence_level = Column(String(20))  # low/medium/high/very_high

    # 各维度
    identity_confidence = Column(Float)
    cross_validation_confidence = Column(Float)
    behavior_consistency = Column(Float)
    social_endorsement = Column(Float)
    time_accumulation = Column(Float)

    # 异常标记 (JSON)
    cross_validation_flags = Column(Text)
    # {"age_education_mismatch": {"severity": "high", "detail": "..."}}

    # 验证建议 (JSON)
    recommended_verifications = Column(Text)
    # [{"type": "identity_verify", "priority": "high", ...}]
```

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/profile/confidence` | GET | 获取完整置信度详情 |
| `/api/profile/confidence/summary` | GET | 获取置信度摘要 |
| `/api/profile/confidence/refresh` | POST | 手动刷新评估 |
| `/api/profile/confidence/recommendations` | GET | 获取验证建议 |
| `/api/profile/confidence/explain` | GET | 解释置信度系统 |
| `/api/profile/confidence/user/{id}/summary` | GET | 查看他人置信度 |

---

## 评估触发时机

| 触发来源 | 说明 |
|---------|------|
| register | 用户注册后首次评估 |
| profile_update | 画像更新后重新评估 |
| periodic | 定期评估（每日/每周） |
| manual | 用户手动触发 |
| behavior_change | 行为变化触发 |

---

## 前端集成

### ConfidenceBadge 组件

**使用场景**：
- 匹配卡片：展示对方可信度
- 用户资料页：展示自己的置信度详情
- 列表页：快速判断用户可信程度

```tsx
<ConfidenceBadge
  userId={match.user.id}
  size="small"
  showTooltip={true}
  showPercent={false}
/>
```

### ConfidenceDetailModal 组件

展示完整的置信度分析：
- 总置信度进度条
- 各维度评估
- 异常标记列表
- 验证建议

---

## 迁移执行

```bash
cd Her/src
PYTHONPATH=. python scripts/migrate_profile_confidence.py
```

---

## 后续优化方向

1. **LLM 深度验证**：使用 LLM 分析用户描述文本的一致性
2. **照片-画像匹配**：分析照片风格与声称性格的一致性
3. **跨平台验证**：接入更多外部验证 API
4. **用户反馈学习**：基于用户对置信度的反馈优化算法
5. **实时更新**：行为变化时实时更新置信度