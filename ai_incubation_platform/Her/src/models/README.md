# Models 目录索引

本文档帮助开发者快速定位所需的模型定义。

## 领域映射表

| 领域 | 文件 | 主要模型 |
|------|------|---------|
| **用户身份** | `user.py` | User, UserCreate, UserProfile, Gender |
| **身份认证** | `identity_models.py` | TrustBadgeDB, EducationCredentialDB, OccupationCredentialDB |
| **会员系统** | `membership.py` | MembershipTier, UserMembership, MembershipOrder |
| **支付系统** | `payment.py`, `db/payment_models.py` | CouponDB, RefundDB, InvoiceDB, SubscriptionDB |
| **企业管理** | `verification_models.py` | DepartmentDB, OperatorRoleDB, DashboardMetricsDB |
| **通知分享** | `notification_models.py` | UserNotificationDB, InviteCodeDB, ShareRecordDB |

### 关系管理领域

| 功能 | 文件 | 主要模型 |
|------|------|---------|
| **关系里程碑** | `milestone_models.py` | RelationshipMilestoneDB, DateSuggestionDB, CoupleGameDB |
| **情感分析** | `emotion_analysis_models.py` | EmotionAnalysisDB, SafetyCheckDB, SafetyAlertDB |
| **行为实验室** | `behavior_lab_models.py` | SharedExperienceDB, SilenceEventDB, IcebreakerTopicDB |
| **爱之语/预警** | `relationship_enhancement_models.py` | UserLoveLanguageProfileDB, WarningResponseStrategyDB |
| **约会模拟** | `date_simulation_models.py` | AIDateAvatarDB, DateSimulationDB, DateOutfitRecommendationDB |
| **约会策划** | `autonomous_dating_models.py` | AutonomousDatePlanDB, RelationshipAlbumDB, SweetMomentDB |
| **部落匹配** | `social_tribe_models.py` | LifestyleTribeDB, CoupleDigitalHomeDB |
| **压力测试** | `stress_test_models.py` | StressTestScenarioDB, GrowthPlanDB |
| **关系状态** | `emotion_weather_models.py` | RelationshipStateDB, DatingAdviceDB |
| **AI预沟通** | `advanced_feature_models.py` | AIChatSession, ConsumptionProfile, GeoTrajectory |
| **聊天助手** | `future_models.py` | ChatAssistantSuggestionDB, DatePlanDB, DateVenueP20DB |

### 感知与价值观领域

| 功能 | 文件 | 主要模型 |
|------|------|---------|
| **冲突处理** | `conflict_models.py` | ConflictStyleDB, ConflictCompatibilityDB |
| **感知层** | `perception_models.py` | UserVectorDB, DigitalSubconsciousProfileDB |
| **价值观演化** | `values_models.py` | DeclaredValuesDB, ValuesEvolutionHistoryDB |
| **数字孪生** | `digital_twin_models.py` | DigitalTwinProfile, DigitalTwinSimulation |

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
from models.milestone_models import DateSuggestionDB
from models.membership import MembershipTier
```

## 注意事项

1. **避免循环导入**：始终从 `models` 包导入，而非直接从子模块导入
2. **数据库迁移**：修改模型后需创建对应的迁移脚本
3. **命名冲突**：`DateVenueDB`（milestone）和 `DateVenueP20DB`（future）是不同的表