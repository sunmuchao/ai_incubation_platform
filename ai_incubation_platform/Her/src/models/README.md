# Models 目录索引

本文档帮助开发者快速定位所需的模型定义。

## 领域映射表

| 领域 | 文件 | 主要模型 |
|------|------|---------|
| **用户身份** | `user.py` | User, UserCreate, UserProfile, Gender |
| **身份认证** | `p0_identity_models.py` | TrustBadgeDB, EducationCredentialDB, OccupationCredentialDB |
| **会员系统** | `membership.py` | MembershipTier, UserMembership, MembershipOrder |
| **支付系统** | `payment.py`, `db/payment_models.py` | CouponDB, RefundDB, InvoiceDB, SubscriptionDB |
| **企业管理** | `p8_models.py` | DepartmentDB, OperatorRoleDB, DashboardMetricsDB |
| **通知分享** | `p9_models.py` | UserNotificationDB, InviteCodeDB, ShareRecordDB |

### 关系管理领域

| 功能 | 文件 | 主要模型 |
|------|------|---------|
| **关系里程碑** | `p10_models.py` | RelationshipMilestoneDB, DateSuggestionDB, CoupleGameDB |
| **情感分析** | `p11_models.py` | EmotionAnalysisDB, SafetyCheckDB, SafetyAlertDB |
| **行为实验室** | `p12_models.py` | SharedExperienceDB, SilenceEventDB, IcebreakerTopicDB |
| **爱之语/预警** | `p13_models.py` | UserLoveLanguageProfileDB, WarningResponseStrategyDB |
| **约会模拟** | `p14_models.py` | AIDateAvatarDB, DateSimulationDB, DateOutfitRecommendationDB |
| **约会策划** | `p15_models.py` | AutonomousDatePlanDB, RelationshipAlbumDB, SweetMomentDB |
| **部落匹配** | `p16_models.py` | LifestyleTribeDB, CoupleDigitalHomeDB |
| **压力测试** | `p17_models.py` | StressTestScenarioDB, GrowthPlanDB |
| **关系状态** | `p18_models.py` | RelationshipStateDB, DatingAdviceDB |
| **AI预沟通** | `p18_p22_models.py` | AIChatSession, ConsumptionProfile, GeoTrajectory |
| **聊天助手** | `p20_models.py` | ChatAssistantSuggestionDB, DatePlanDB, DateVenueP20DB |

### 感知与价值观领域

| 功能 | 文件 | 主要模型 |
|------|------|---------|
| **冲突处理** | `p1_conflict_models.py` | ConflictStyleDB, ConflictCompatibilityDB |
| **感知层** | `p1_perception_models.py` | UserVectorDB, DigitalSubconsciousProfileDB |
| **价值观演化** | `p1_values_models.py` | DeclaredValuesDB, ValuesEvolutionHistoryDB |
| **数字孪生** | `p2_digital_twin_models.py` | DigitalTwinProfile, DigitalTwinSimulation |

### AI 与学习领域

| 功能 | 文件 | 主要模型 |
|------|------|---------|
| **AI 反馈** | `ai_feedback_models.py` | AIFeedbackDB, AIFeedbackSessionDB |
| **持续学习** | `l4_learning_models.py` | UserPreferenceMemory, BehaviorLearningPattern |

## 命名规范

- `*DB` - SQLAlchemy 数据库模型（映射到数据库表）
- `*Create` / `*Update` - Pydantic 请求模型
- `*Response` - Pydantic 响应模型
- `*Base` - 基础模型类

## 使用示例

```python
# 从 models 包导入（推荐）
from models import UserMembership, RelationshipMilestoneDB

# 直接从文件导入（当需要特定模型时）
from models.p10_models import DateSuggestionDB
from models.membership import MembershipTier
```

## 注意事项

1. **避免循环导入**：始终从 `models` 包导入，而非直接从子模块导入
2. **数据库迁移**：修改模型后需创建对应的迁移脚本
3. **命名冲突**：`DateVenueDB`（p10）和 `DateVenueP20DB`（p20）是不同的表