# API 路由语义化命名重构方案

> **状态更新 (2026-04-11)**: 模型和服务层语义化命名重构已完成。
> - 所有 `p10/p11/p12/p13/p14/p15/p16/p17/p18_p22` 模型文件已重命名为语义化命名
> - 测试文件导入路径已全部更新
> - API 路由层仍保留原计划，待后续迭代

## 背景

当前系统使用 `P10`、`P11` 等 Priority/Phase 编号命名 API 路由，存在以下问题：
- 命名不直观，无法从 URL 知道功能
- 新成员上手困难
- API 文档可读性差
- 不符合 RESTful 最佳实践

## 已完成的重构（模型和服务层）

| 旧命名 | 新命名 | 状态 |
|--------|--------|------|
| `models/p10_models.py` | `models/milestone_models.py` | ✅ 已完成 |
| `models/p11_models.py` | `models/emotion_analysis_models.py` | ✅ 已完成 |
| `models/p12_models.py` | `models/behavior_lab_models.py` | ✅ 已完成 |
| `models/p13_models.py` | `models/relationship_enhancement_models.py` | ✅ 已完成 |
| `models/p14_models.py` | `models/date_simulation_models.py` | ✅ 已完成 |
| `models/p15_models.py` | `models/autonomous_dating_models.py` | ✅ 已完成 |
| `models/p16_models.py` | `models/social_tribe_models.py` | ✅ 已完成 |
| `models/p17_models.py` | `models/stress_test_models.py` | ✅ 已完成 |
| `models/p18_p22_models.py` | `models/advanced_feature_models.py` | ✅ 已完成 |

## 当前命名 vs 语义化命名对照表（API 路由层 - 待实施）

### P10 - 关系里程碑追踪

| 当前命名 | 语义化命名 | 功能描述 |
|---------|-----------|---------|
| `/api/milestones` | `/api/relationship-milestones` ✅ | 关系里程碑 |
| `/api/date-suggestions` | `/api/date-recommendations` ✅ | 约会建议 |
| `/api/couple-games` | `/api/couple-games` ✅ | 双人游戏 |

> P10 已经部分语义化，无需大改

---

### P11 - 感官洞察

| 当前命名 | 语义化命名 | 功能描述 |
|---------|-----------|---------|
| `/api/p11/emotion` | `/api/emotion-analysis` | AI 视频面诊/情感翻译 |
| `/api/p11/safety` | `/api/safety-guardian` | 物理安全守护神 |
| `/api/p11/reports` | `/api/emotion-reports` | 情感报告 |

---

### P12 - 行为实验室

| 当前命名 | 语义化命名 | 功能描述 |
|---------|-----------|---------|
| `/api/p12/experiences` | `/api/shared-experiences` | 时机感知破冰/共同经历检测 |
| `/api/p12/silence` | `/api/silence-detection` | 沉默检测 |
| `/api/p12/icebreaker` | `/api/icebreaker-topics` | 破冰话题 |
| `/api/p12/emotion` | `/api/emotion-mediation` | 情感调解 |
| `/api/p12/love-language` | `/api/love-language-translation` | 爱之语翻译 |
| `/api/p12/weather` | `/api/relationship-weather` | 关系气象 |

---

### P13 - 情感调解增强

| 当前命名 | 语义化命名 | 功能描述 |
|---------|-----------|---------|
| `/api/p13/love-language-profile` | `/api/love-language-profile` | 爱之语画像 |
| `/api/p13/relationship-trend` | `/api/relationship-trends` | 关系趋势预测 |
| `/api/p13/warning-response` | `/api/relationship-warnings` | 预警分级响应 |
| `/api/p13/comprehensive` | `/api/relationship-insights` | 综合关系洞察 |

---

### P14 - 实战演习

| 当前命名 | 语义化命名 | 功能描述 |
|---------|-----------|---------|
| `/api/p14/avatar` | `/api/dating-avatars` | AI 约会分身 |
| `/api/p14/simulation` | `/api/dating-simulation` | 约会模拟沙盒 |
| `/api/p14/outfit` | `/api/outfit-recommendations` | 穿搭推荐 |
| `/api/p14/venue` | `/api/venue-strategy` | 场所策略 |
| `/api/p14/topics` | `/api/conversation-topics` | 话题锦囊 |

---

### P15 - 虚实结合

| 当前命名 | 语义化命名 | 功能描述 |
|---------|-----------|---------|
| `/api/p15/date-plan` | `/api/autonomous-dating` | 自主约会策划 |
| `/api/p15/album` | `/api/relationship-albums` | 情感纪念册 |

---

### P16 - 圈子融合

| 当前命名 | 语义化命名 | 功能描述 |
|---------|-----------|---------|
| `/api/p16/tribe` | `/api/social-tribes` | 部落匹配 |
| `/api/p16/digital-home` | `/api/digital-homes` | 数字小家 |
| `/api/p16/family-sim` | `/api/family-meeting-simulation` | 见家长模拟 |

---

### P17 - 终极共振

| 当前命名 | 语义化命名 | 功能描述 |
|---------|-----------|---------|
| `/api/p17/stress-test` | `/api/relationship-stress-tests` | 关系压力测试 |
| `/api/p17/growth` | `/api/growth-plans` | 成长计划 |
| `/api/p17/trust` | `/api/trust-endorsements` | 信任背书 |

---

## 重构实施计划

### 阶段一：准备（1天）

1. **创建别名路由**：新命名和旧命名同时生效，保证兼容
2. **更新 API 文档**：标注旧命名已废弃
3. **通知前端团队**：同步命名变更

### 阶段二：重构（2-3天）

```python
# 示例：api/p11_apis.py 改造

# 旧代码
router_emotion_analysis = APIRouter(prefix="/api/p11/emotion", tags=["P11 情感分析"])

# 新代码
router_emotion_analysis = APIRouter(
    prefix="/api/emotion-analysis",
    tags=["情感分析", "deprecated: /api/p11/emotion"]
)
```

### 阶段三：清理（1天）

1. 移除旧路由别名
2. 更新测试用例
3. 清理相关代码注释

---

## 命名规范（新模块参考）

```
/api/{功能域}/{具体功能}

功能域示例：
- /api/matching/*      - 匹配相关
- /api/dating/*        - 约会相关
- /api/relationship/*  - 关系相关
- /api/safety/*        - 安全相关
- /api/emotion/*       - 情感相关
- /api/profile/*       - 用户画像

具体功能命名原则：
1. 使用名词复数（resources）
2. 使用 kebab-case（连字符）
3. 避免缩写，保持可读性
4. 最多 3 层深度
```

---

## 影响范围评估

| 影响项 | 评估 |
|-------|------|
| 后端代码 | 需修改路由定义、文档注释 |
| 前端代码 | 需更新 API 调用路径 |
| 测试代码 | 需更新测试用例 |
| 第三方集成 | 如有外部调用需通知 |

---

## 建议执行顺序

1. **优先重构 P11-P14**：这些是核心 AI 功能，使用频率可能较高
2. **其次重构 P15-P17**：高级功能，使用频率较低
3. **P10 保持现状**：已经部分语义化

是否需要我开始执行重构？