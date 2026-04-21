# Her 项目死代码与清理候选清单

> **生成时间**: 2026-04-20（同日 **增补**：后端路由入口对照与逻辑孤岛分析）  
> **说明**: 本文件仅汇总扫描与审计结果，**未删除、未修改任何业务代码**。删除前请结合分支、产品规划与运行时行为二次确认。  
> **扫描根目录**: 本仓库 `Her/`（与 `CLAUDE.md` 所指项目根一致）

---

## 零、执行环境与命令

| 项目 | 命令 | 说明 |
|------|------|------|
| 主前端 `frontend/` | `cd frontend && npx --yes knip` | Knip 默认分析；退出码 1 表示报告到问题（预期） |
| 子项目 `deerflow/frontend/` | `cd deerflow/frontend && npx --yes knip` | DeerFlow 自带 Next 前端，与主应用独立 |
| 后端 Python | `python3 -m venv .cleanup_scan_venv && pip install vulture && vulture src scripts tests --min-confidence 61` | 临时 venv 仅用于本次扫描，可安全删除目录 `.cleanup_scan_venv`（若仍存在） |

---

## 一、Knip — `frontend/`（主应用）

### 1.1 未引用文件（Unused files）— 14 个

Knip 认为下列文件未被项目依赖图引用（**注意**：`React.lazy(() => import('...'))` 与 barrel `index.tsx` 可能被漏报或误报，见第四节）。

| 路径 | 判断依据 |
|------|----------|
| `frontend/src/components/DailyLimitIndicator.tsx` | Knip unused file；`rg` 无其他文件 import 该路径 |
| `frontend/src/components/generative-ui/CoachingComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/DashboardComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/DateComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/EmotionComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/GiftComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/index.tsx` | Knip unused file（barrel 未被直接引用时常出现） |
| `frontend/src/components/generative-ui/PrepComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/RelationshipComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/SafetyComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/SharedComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/TopicComponents.tsx` | Knip unused file |
| `frontend/src/components/generative-ui/TrendComponents.tsx` | Knip unused file |
| `frontend/src/test/match-filter-verify.js` | Knip unused file（测试/脚本类） |

**交叉验证（与 `ChatInterface.tsx`）**: 当前仅见对 `./generative-ui/MatchComponents` 与 `./generative-ui/ChatComponents` 的 `lazy()` 引用；其余 `generative-ui/*` 与 Knip「未引用」高度一致，疑似预留或历史 Generative UI 模块。

### 1.2 未使用的 npm 依赖（Knip）

| 类型 | 包名 | 依据 |
|------|------|------|
| dependencies | `@types/react-window`, `dayjs`, `react-window` | Knip 报告未使用 |
| devDependencies | `@vitejs/plugin-react` | Knip 报告未使用（注意：`vite.config.ts` 实际使用 `@vitejs/plugin-react-swc`，与该项不冲突时需再确认是否可删） |
| 未在 package.json 声明 | `@jest/globals` | Knip **Unlisted dependencies**：`src/test/__tests__/AvatarAndMatchReasons.test.tsx` 使用 |

### 1.3 未使用的导出（Unused exports）— 共 78 条（节选）

Knip 将「未被其他模块按**命名导出**消费」的导出标为 unused；默认导出与再导出、仅类型引用等易产生误判。

**API / 工具（节选）**

| 符号（函数/变量） | 文件:行 | 判断依据 |
|------------------|---------|----------|
| `quickChatApi`, `conversationAnalysisApi` | `src/api/chatApi.ts` | Knip unused exports |
| `getVerificationStatus`, `startVerification`, `submitVerification`, … | `src/api/faceVerificationApi.ts` | Knip unused exports（可能仅默认导出或字符串动态使用被漏检） |
| `herAdvisorApi`, `profileApi`, `getAuthHeaders`, `getCurrentUserId` | `src/api/index.ts` | Knip unused exports |
| `autonomousDatingApi`, `relationshipAlbumsApi`, … | `src/api/lifeIntegrationApi.ts` | Knip unused exports |
| `membershipApi` | `src/api/membershipApi.ts` | Knip unused exports |
| `dateSuggestionApi`, `coupleGameApi` | `src/api/milestoneApi.ts` | Knip unused exports |
| `photosApi` | `src/api/photosApi.ts` | Knip unused exports |
| `getProfileQuestion`, `submitProfileAnswer`, …, `profileApi` | `src/api/profileApi.ts` | Knip unused exports |
| `videoDateApi`, `videoDateWebSocket` | `src/api/videoDateApi.ts` | Knip unused exports |
| `normalizeAvatarUrl` | `src/utils/matchAvatar.ts:18` | Knip unused export（若业务将改用该工具函数需保留） |

**组件 / Hooks（节选）**

| 符号 | 文件 | 判断依据 |
|------|------|----------|
| `AIPreferenceUpdate`, `default` | `src/components/AIFeedback.tsx` | Knip |
| `ConfidenceDetailModal`, `ConfidenceMark`, `ConfidenceProgress` | `src/components/ConfidenceBadge.tsx` | Knip |
| `Skeleton*`, `default` | `src/components/Skeleton.tsx` | Knip |
| `Inline*Skeleton`, `default` | `src/components/skeletons.tsx` | Knip |
| `VerifiedMark`, `VerifiedIcon` | `src/components/VerificationBadge.tsx` | Knip |
| `default` | `src/hooks/useCurrentUserId.ts` | Knip |
| `runIOSTests` | `src/tests/iosTest.ts` | Knip |
| `validateProps`, `listAllComponents`, `default` | `src/types/generativeUI.ts` | Knip |
| `isAndroid`, `isMobile`, …, `iosUtils` | `src/utils/iosUtils.ts` | Knip（`main.tsx` 使用 `initIOSOptimizations`，其余子导出可能未用） |
| `pwaStorage`, `storage`, `default` | `src/utils/storage.ts` | Knip |

### 1.4 未使用的导出类型（Unused exported types）— 117 条

Knip 报告大量 `interface`/`type` 未被其他文件作为**值或显式类型导入**使用（常见于「仅在同文件使用」或「通过 `import type` 链」的边界）。完整列表过长，归类如下：

- `src/api/deerflowClient.ts`、`faceVerificationApi.ts`、`herAdvisorApi.ts`、`membershipApi.ts`、`photosApi.ts`、`profileApi.ts`、`whoLikesMeApi.ts`、`yourTurnApi.ts`、`index.ts` 等 API 类型
- `src/types/dateSimulationTypes.ts`、`loveLanguageTypes.ts`、`lifeIntegrationTypes.ts`、`milestoneTypes.ts`、`rose.ts`、`index.ts`、`generativeUI.ts` 等类型定义
- `src/components/ConfidenceBadge.tsx`、`generative-ui/types.ts` 等组件侧类型

**依据**: 均为 Knip `Unused exported types` 段输出。

### 1.5 重复导出（Duplicate exports）— 17 条

Knip 报告「同一模块既有命名导出又有 default」等重复导出模式，便于收敛为单一导出风格（非必须删除）。

涉及文件：`apiClient.ts`, `deerflowClient.ts`, `herAdvisorApi.ts`, `membershipApi.ts`, `photosApi.ts`, `profileApi.ts`, `roseApi.ts`, `AIFeedback.tsx`, `FeatureCards.tsx`, `FeaturesDrawer.tsx`, `PreCommunicationDialogCard.tsx`, `PreCommunicationSessionCard.tsx`, `Skeleton.tsx`, `skeletons.tsx`, `YourTurnReminder.tsx`, `useCurrentUserId.ts`, `generativeUI.ts`。

---

## 二、Knip — `deerflow/frontend/`（子项目摘要）

**未引用文件**: Knip 报告 **48** 个（含 `public/demo/threads/...` 下历史 demo 产物、`src/components/ai-elements/*` 未接线文件、`src/content/*/_meta.ts` 等）。

**说明**: 该目录为 DeerFlow 上游/集成前端，**是否与 Her 主产品同生命周期**需单独决策；不建议在未确认上游同步策略前批量删除。

完整 Knip 输出可在本地重新运行：`cd deerflow/frontend && npx --yes knip`。

---

## 三、Vulture — Python（`src/` + `scripts/` + `tests/`）

**配置**: `--min-confidence 61`（含 90%/100% 未使用 import、未使用变量、不可达代码等）。

### 3.1 按文件汇总（路径 → 项）

| 文件 | 项（vulture 描述） |
|------|-------------------|
| `scripts/add_user_avatars.py` | 未使用变量 `gender_specific` |
| `src/agent/skills/subconscious_analyzer_skill.py` | 未使用变量 `focus_area` |
| `src/api/deerflow.py` | 未使用 import `StreamEvent` |
| `src/api/gift_integration.py` | 未使用 import `get_budget_range_display` |
| `src/api/payment.py` | 未使用 import `SubscriptionCreateRequest` |
| `src/cache/cache_manager.py` | 未使用 import `RedisConnectionError` |
| `src/db/payment_models.py` | 未使用 import `SQLEnum` |
| `src/integration/llm_client.py` | 未使用 import `MatchContext` |
| `src/llm/client.py` | 未使用 import `lru_cache` |
| `src/services/ai_awareness_service.py` | 未使用 import `joinedload` |
| `src/services/autonomous_dating_service.py` | 未使用 import `CoupleFootprintDB`, `DateReservationDB`, `GeneratedMediaDB` |
| `src/services/behavior_event_emitter.py` | `return` 后不可达代码 |
| `src/services/chat_service.py` | 未使用 import `joinedload` |
| `src/services/emotion_analysis_service.py` | 多个未使用 DB 模型 import |
| `src/services/gift_service.py` | 未使用 import `sql_func` |
| `src/services/her_advisor_service.py` | 未使用变量 `profile_snapshot` |
| `src/services/identity_verification_service.py` | 未使用变量 `id_photo_url`, `face_photo_url` |
| `src/services/llm_semantic_service.py` | 未使用 import `lru_cache` |
| `src/services/notification_service.py` | 未使用变量 `invited_user_email` |
| `src/services/profile_confidence_service.py` | 未使用变量 `force_refresh` |
| `src/services/rose_service.py` | 未使用 import `RoseTransaction` |
| `src/services/social_tribe_service.py` | 未使用 import `TribeCompatibilityDB` |
| `src/services/stress_test_service.py` | 未使用 import `GrowthResourceRecommendationDB`, `TrustEndorsementSummaryDB` |
| `src/services/warning_response_service.py` | 未使用 import `CalmingKitDB` |
| `src/utils/logger.py` | 未使用变量 `parent_span_id` |
| `src/utils/skills_checker.py` | 未使用 import `ast` |
| `tests/**` | 大量未使用 import / fixture 变量（测试代码常见，清理优先级低） |

**依据**: 均为 Vulture 静态分析；测试目录中的项多属「测试未用到的 import」，不等价于生产死代码。

---

## 四、人工审计：未被其他文件 import 的源文件

### 4.1 方法说明

1. **前端 `frontend/src`**: 从 `main.tsx` 做 **静态** `import` / `import()` 字符串的 BFS 解析（含 `@/` 别名），得到「从入口不可达」集合；**不包含** Jest 以 `setupFilesAfterEnv` 等方式单独加载的测试树。  
2. **后端 `src`**: `routers/__init__.py` 通过 `importlib.import_module("api.<stem>")` **动态**注册路由，**不能**用「仅从 `main.py` 静态 import 图」推断 `api/*.py` 是否废弃。  
3. **仓库根目录 `scripts/*.py`**: 设计为 CLI / 一次性运维脚本，通常**不应**被 `src` import；未在 `src` 中出现 `import` 不等价于删除。

### 4.2 前端：从 `main.tsx` 静态可达性 — 生产代码侧「疑似仅测试引用」

下列路径在 **BFS（起点 `frontend/src/main.tsx`）中不可达**，且 `rg` 显示**仅**或**主要**被 `src/test/**` 引用（或完全无引用），**疑似**生产包未使用（需与产品确认后再删）：

| 路径 | 判断依据 |
|------|----------|
| `frontend/src/components/RelationshipTimeline.tsx` | BFS 不可达；仅 `RelationshipTimeline.test.tsx` import |
| `frontend/src/pages/RegistrationConversationPage.tsx` | BFS 不可达；仅 `RegistrationConversationPage.test.tsx` import |
| `frontend/src/components/DailyLimitIndicator.tsx` | BFS 不可达；与 Knip「未引用文件」一致 |
| `frontend/src/components/generative-ui/{Coaching,Dashboard,Date,Emotion,Gift,Prep,Relationship,Safety,Shared,Topic,Trend}Components.tsx` | BFS 不可达；与 Knip 一致 |
| `frontend/src/components/generative-ui/index.tsx` | BFS 不可达；与 Knip 一致 |

**下列路径 BFS 不可达属正常**：`frontend/src/test/**`、`test/setup.tsx`（由 Jest 配置直接指定，不经 `main.tsx`）。

**下列脚本**: `frontend/src/test/match-filter-verify.js` — Knip 标记未引用；是否保留作本地验证工具需人工决定。

### 4.3 后端：不宜用「未被 import」判定废弃的文件

- **路由模块** `src/api/*.py`：由 `src/routers/__init__.py` 的 `discover_routers` 扫描注册，**静态 import 图无法列出**。判断是否废弃应结合：OpenAPI、`/docs`、前端调用、集成测试。  
- **服务 / Agent / 工具**：多由上述 API 或任务流间接引用，需按模块边界做专项审计，而非全仓「未被 import」。

### 4.4 仓库级 `scripts/*.py`（非 `src/scripts`）

| 文件 | 是否被 `src` import | 判断依据 |
|------|---------------------|----------|
| `scripts/*.py`（如 `generate_fake_users.py`, `add_user_avatars.py`, `migrations/*.py` 等） | 否（抽样 `rg` 未见 `from scripts` 引用） | 预期为命令行/迁移脚本，**非死代码** |
| `src/scripts/migrate_her_advisor.py` | 是 | `src/main.py` 条件导入 `from scripts.migrate_her_advisor import run_migration` |

---

## 五、合并优先级建议（仅建议，未执行删除）

| 优先级 | 对象 | 建议动作 | 综合依据 |
|--------|------|----------|----------|
| P0 调研 | `generative-ui/*Components.tsx` + `index.tsx` | 确认产品是否仍规划 Generative UI 扩展；若否可考虑移除或合并 | Knip 未引用 + BFS 不可达 + 与当前 `lazy` 仅 Match/Chat 一致 |
| P0 调研 | `DailyLimitIndicator.tsx`, `match-filter-verify.js` | 确认是否保留为后续功能/本地脚本 | Knip |
| P1 | `RelationshipTimeline.tsx`, `RegistrationConversationPage.tsx` | 若确认无上线计划：删除或移入 `deprecated_archive`；否则从 `HomePage`/`ChatInterface` 接回路由或 lazy | 仅测试引用 + BFS 不可达 |
| P1 | Vulture 标出的 `src/services/*`、`src/api/*` 未使用 import | 分批删除 import 或启用对应逻辑 | Vulture 90%+ 置信 |
| **P1 孤岛** | `src/services/confidence/{extended_validation_rules,llm_confidence_analyzer,realtime_update}.py` 与 `confidence/__init__.py` 内 `IntegratedConfidenceEvaluator` | 未挂到任何已注册 HTTP 路由或 `main` 启动链；属「综合置信度」抽象未完成接线 | 见 **第七节** |
| **P1 孤岛** | `src/services/report_service.py` | 仅被 `services/__init__.py` 再导出，`api/` 与 `agent/` 无引用 | 见 **第七节** |
| P2 | Knip `Unused exports` / `Unused exported types` | 收敛导出面或改为 `export type` + 内部使用；避免误删对外 SDK 式 API | Knip；注意误判 |
| P2 | `deerflow/frontend` Knip 48 文件 | 与 DeerFlow 升级策略一并处理 | 子项目独立 |

---

## 六、误判与注意事项（审计必读）

1. **React `lazy(() => import('./path'))`**：Knip 对部分 lazy 路径支持不完整；已确认 `MatchComponents` / `ChatComponents` 在 `ChatInterface.tsx` 中被 lazy 引用。  
2. **Barrel `index.tsx`**：`generative-ui/index.tsx` 若未被直接引用，Knip 会标为 unused，但若未来改为统一入口则仍有价值。  
3. **类型仅导出**：`Unused exported types` 许多仍可能被同文件或未来模块使用，删除前建议配合 `tsc --noEmit` 与测试。  
4. **Python 动态路由**：勿仅凭「未被 import」删除 `src/api/*.py`。  
5. **测试目录**：`tests/` 下 Vulture 项多数为测试代码噪音，清理时与生产代码分开批次。

---

## 七、后端深度分析：路由入口对照与逻辑孤岛

本节回答：**当前真正挂在 FastAPI 上的入口是什么？** 以及 **哪些 Service 模块虽然内部互相 import，却从未连到这些入口（或 Agent 技能入口）？**

### 7.1 活跃业务入口（对照基准）

| 入口类型 | 位置 / 机制 | 说明 |
|----------|-------------|------|
| **HTTP 路由批量注册** | `src/main.py` 在模块加载末尾调用 `register_all_routers(app)` | 唯一全量 API 挂载点（除 `GET /`、`/health`、`/metrics` 等内联路由外） |
| **路由发现** | `src/routers/__init__.py` → `discover_routers()` | 对 `src/api/*.py` 逐个 `importlib.import_module("api.<stem>")`，收集模块内**所有**以 `router` 开头且带 `.routes` 的对象并 `include_router` |
| **非路由 API 工具模块** | `src/api/errors.py` | **无** `router*` 变量，不参与注册（设计如此，非孤岛） |
| **启动期副作用 / 常驻服务** | `src/main.py` → `@app.on_event("startup")` | 显式 `import`：`performance_service`、`her_advisor_service`、`user_profile_service`、`conversation_match_service`、`initialize_default_skills`、`start_heartbeat` 等（与 HTTP 并行，属**活跃入口**） |
| **Agent 能力入口** | `src/main.py` startup → `agent.skills.registry.initialize_default_skills()` | 注册大量 Skill；Skill 内常见 **函数体内** `from services.xxx import ...`（静态全文件 AST 若不扫 Skill 文件会漏边） |

**实测（本地 import 成功前提下）**：`src/api` 下除 `errors.py` 外，**其余已扫描到的模块均至少暴露 1 个 `router*`**；另有 `life_integration_apis`、`milestone_apis`、`notification_share_apis` 多路由文件。合计约 **44 个** `api.*` 模块参与路由器发现（与 `discover_routers` 实现一致）。

### 7.2 Service 是否在「执行路径」上：判定方法

1. **正向（推荐）**：从每个 `api/*` 路由处理函数出发，跟踪其 `Depends` / 函数体内 `from services... import` 及调用的方法 — 若在**用户可触达的 HTTP 路径**上调用，则为活跃。  
2. **Agent 补充入口**：对 `agent/skills/*.py` 中注册的 Skill，其运行时 `from services...` 同样视为活跃（例如情感调解、价值观推断等）。  
3. **反向陷阱**：仅因 `services/A.py` import `services/B.py`，**不能**推断 B 在生产路径上；若 A 本身不在入口可达集合内，则 A、B 可能同属**逻辑孤岛**。

### 7.3 已识别逻辑孤岛（高置信：未连到 HTTP 路由或 main/agent 入口链）

下列模块**全仓库无** `api/*.py`、`main.py`、`agent/**/*.py`（含 Skill 内字符串）对其顶层模块的引用，或仅被**同样未接线的包内 `__init__.py`** 引用；属于「做过设计/实现、但未接入当前产品闭环」的典型遗留。

| 对象 | 互相引用 / 局部关系 | 为何判定为孤岛、可能已过时 |
|------|---------------------|------------------------------|
| **`src/services/confidence/extended_validation_rules.py`** | 仅被 **`services/confidence/__init__.py`** 顶层 import；`__init__` **从未**被其他包 `import services.confidence` 方式加载 | 扩展校验规则集未挂到 `profile_confidence_service` 或 `feedback_loop`。**过时假设**：曾计划由 `IntegratedConfidenceEvaluator` 统一编排，但产品最终只保留「基础评估 + 反馈 API」两条线。 |
| **`src/services/confidence/llm_confidence_analyzer.py`** | 同上，仅经 `confidence/__init__.py` 引用 | LLM 深度置信分析未暴露为独立 API，也未从 `feedback_loop` / `profile_confidence_service` 调用。**过时假设**：深度分析成本高或产品裁剪后未上线。 |
| **`src/services/confidence/realtime_update.py`** | 同上 | 实时触发器/调度未与 `api/profile_confidence` 或 `confidence_feedback` 路由 wiring。**过时假设**：实时置信度管线未完成与消息总线/定时任务的集成。 |
| **`services/confidence/__init__.py` 中的 `IntegratedConfidenceEvaluator` / `integrated_evaluator`** | 聚合上述子模块 + `profile_confidence_service`，但 **无任何外部模块 import 该类** | `rg` 仅命中包内自身与 `api/confidence_feedback.py`（后者只 import **`feedback_loop.router`**）。**过时假设**：「一站式综合评估」API 未落地，代码停留在库层。 |
| **`src/services/report_service.py`** | 仅出现在 **`services/__init__.py`** 的再导出列表；`api/`、`agent/` **零引用** | 举报/风控报告类服务未接线到任何路由或 Skill。**过时假设**：运营后台或用户举报入口未实现或已迁移方案。 |

**仍属活跃链（对照说明，不是孤岛）**：

- **`services/confidence/feedback_loop.py`**：`api/confidence_feedback.py` 直接 `from services.confidence.feedback_loop import router` → **在 HTTP 路径上**。  
- **`services/confidence/dynamic_weights.py`**：被 **`feedback_loop`**（含函数内 import）使用 → **在 HTTP 间接路径上**。  
- **`services/profile_confidence_service.py`**：`api/profile_confidence.py` 及注册/资料相关 API 使用 → **活跃**。  
- **`services/conversation_match/__init__.py`**：看似「仅 barrel」；子模块由 **`conversation_match_service.py`** 直接 `from services.conversation_match.match_executor import ...` 引用，且该 Service 由 **`main` startup**、`api/deerflow.py`、`api/matching.py`、`api/her_advisor.py` 等使用 → **非孤岛**（勿删 `__init__` 误判为死代码）。

### 7.4 Agent 技能链（避免误判为孤岛）

以下 Service **未**出现在 `src/api` 的静态 import 中，但通过 **已注册 Skill** 的函数体内 import 使用，应视为**潜在活跃**（取决于 DeerFlow/对话是否实际调度到该 Skill）：

| Service | 典型引用位置 |
|---------|----------------|
| `values_evolution_service` | `agent/skills/values_inferencer_skill.py` |
| `perception_layer_service` | `agent/skills/subconscious_analyzer_skill.py` |
| `emotion_mediation_service` → 内聚 `love_language_translation_service`、`weather_service` | `agent/skills/emotion_mediator_skill.py` |
| `behavior_credit_service` | `agent/skills/trust_analyzer_skill.py` |

**结论**：清理「逻辑孤岛」时必须 **合并 Agent 入口** 做第二次核对，否则会误删「仅 AI 路径使用」的能力。

### 7.5 辅助：纯静态 import 图 BFS 的局限（工具结论）

曾以「所有已注册 `api.*` 源文件 + `main.py` + 少量 `agent` 文件」为起点做模块级 BFS，会得到诸如 `services/confidence/__init__.py` 等「假孤儿」——原因是 **`services.confidence` 包从未作为整体被 import**，而子文件 `feedback_loop` 被直接 deep import；这与 **7.3** 的人工结论一致，印证了**不能单靠粗粒度 BFS 定案**。

---

## 八、复现命令速查

```bash
cd /path/to/Her/frontend && npx --yes knip
cd /path/to/Her/deerflow/frontend && npx --yes knip
cd /path/to/Her && python3 -m venv .cleanup_scan_venv && .cleanup_scan_venv/bin/pip install vulture && .cleanup_scan_venv/bin/vulture src scripts tests --min-confidence 61
```

---

*本清单替代此前同日期的旧版「已完成清理」叙述；以 2026-04-20 扫描及当日后端路由/孤岛对照为准。*

**2026-04-20 执行记录（与清单对齐的已落地清理）**：已从主树移除并删除归档副本：`services/confidence` 中未接线子模块（`extended_validation_rules`、`llm_confidence_analyzer`、`realtime_update`）及 `IntegratedConfidenceEvaluator` 聚合实现；`services/report_service.py`；前端 Knip 未引用之 `generative-ui/*Components`、`index.tsx`、`DailyLimitIndicator`、`RelationshipTimeline`、注册引导页与对应仅测文件等。验证：`npm run build`、`npm test`、`PYTHONPATH=. python3 -c "from main import app"`、抽样 `pytest` 通过。细节见 `README.md` 架构节与 Git diff。
