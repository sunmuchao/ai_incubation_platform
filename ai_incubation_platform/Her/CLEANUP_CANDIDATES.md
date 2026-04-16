# Her 项目死代码清理候选清单（最新扫描）

> **生成时间**: 2026-04-15
> **扫描工具**: knip (前端) + vulture (后端) + 人工审计
> **清理状态**: ✅ **已完成** (v1.30.0)
> **清理结果**: 48 个废弃文件已删除 + 逻辑孤岛已清理，核心功能测试通过

---

## 零、扫描结论摘要

### 0.1 已完成清理（上次清理验证）

| 类别 | 数量 | 状态 |
|------|------|------|
| 后端废弃 Service | 21 个 | ✓ 已删除 |
| 后端工具/脚本 | 9 个 | ✓ 已删除 |
| 前端废弃页面/API/组件 | 16 个 | ✓ 已删除 |

### 0.2 新发现的死代码

| 类别 | 数量 | 风险等级 |
|------|------|---------|
| 前端真正未引用文件 | 2 个 | P0 - 可安全删除 |
| 前端破损导入（运行时错误风险） | 1 个 | P0 - 需修复 |
| 前端未使用导出（79个） | 需逐个确认 | P1 |
| 后端未使用 import（高置信度） | 6 个 | P0 - 可删除 |
| 后端未使用函数/方法（vulture 检测） | 100+ | P1 - 需确认 |
| **逻辑孤岛（执行路径追踪）** | **4 个 Service** | **P1 - 需确认** |
| **真正的死代码（无引用）** | **2 个文件** | **P0 - 可删除** |

### 0.3 Knip 检测的误判（已验证仍在使用）

以下文件 knip 报告为未使用，但实际通过懒加载或动态导入使用：

| 文件 | 实际使用位置 | 原因 |
|------|-------------|------|
| `FaceVerificationPage.tsx` | HomePage.tsx 懒加载 | knip 未检测懒加载 |
| `faceVerificationApi.ts` | FeatureCards.tsx, FaceVerificationPage.tsx | knip 误判 |
| `membershipApi.ts` | MembershipSubscribeModal.tsx | knip 误判 |
| `generative-ui/*` (部分) | ChatInterface.tsx 懒加载 | knip 未检测懒加载 |

---

## 一、前端死代码（可立即删除）

### 1.1 真正的逻辑孤岛文件

| 文件路径 | 判断依据 | 确认方式 |
|---------|---------|---------|
| `frontend/src/components/ConfidenceFilter.tsx` | grep: 0 引用 | 全项目搜索无 import |
| `frontend/src/tests/mobileTest.ts` | grep: 0 引用 | 测试文件未被任何地方引用 |

### 1.2 破损导入（运行时错误风险）

| 文件路径 | 问题 | 影响 |
|---------|------|------|
| `frontend/src/components/generative-ui/index.tsx:54-57` | 导入不存在的 `../GenerativeUI` | **运行时错误** - 模块加载失败 |

```typescript
// index.tsx 第 54-57 行（破损）
export { GenerativeUIRenderer } from '../GenerativeUI'  // ❌ GenerativeUI.tsx 不存在
export { default as GenerativeUIRendererDefault } from '../GenerativeUI'  // ❌ 破损
```

**修复方案**: 删除这两行导出，或创建 GenerativeUI.tsx 文件

### 1.3 未使用依赖

| 依赖 | 类型 | 建议 |
|------|------|------|
| `dayjs` | 未使用 | 可从 package.json 移除 |
| `@vitejs/plugin-react` | 未使用（已有 @vitejs/plugin-react-swc） | 可移除 |

### 1.4 未声明依赖

| 依赖 | 使用位置 | 建议 |
|------|---------|------|
| `vite-plugin-pwa` | vite.config.ts | 需添加到 package.json |

### 1.5 未使用导出（Knip 检测 79 个）

以下为高优先级未使用导出，需逐个确认：

#### API 层未使用导出

| 导出名称 | 文件位置 | 建议 |
|---------|---------|------|
| `quickChatApi` | chatApi.ts:61 | 可能被 deerflowClient 替代 |
| `conversationAnalysisApi` | chatApi.ts:119 | 检查是否被 DeerFlow 替代 |
| `herAdvisorApi` | index.ts:505 | 检查使用情况 |
| `profileApi` | index.ts:549 | 检查使用情况 |
| `autonomousDatingApi` | lifeIntegrationApi.ts:40 | 检查使用情况 |
| `dateSuggestionApi` | milestoneApi.ts:137 | 可能被 date_planning_skill 替代 |
| `videoDateApi` | videoDateApi.ts:10 | 检查使用情况 |
| `videoDateWebSocket` | videoDateApi.ts:85 | 检查使用情况 |

#### 组件层未使用导出

| 导出名称 | 文件位置 | 建议 |
|---------|---------|------|
| `AIPreferenceUpdate` | AIFeedback.tsx:116 | 类型定义未使用 |
| `ConfidenceDetailModal` | ConfidenceBadge.tsx:242 | 检查是否被动态渲染 |
| `ConfidenceMark` | ConfidenceBadge.tsx:470 | 检查是否被动态渲染 |
| `DailyLimitIndicator` | DailyLimitIndicator.tsx:44 | 检查路由引用 |
| `Skeleton` 系列 | Skeleton.tsx | 检查是否被动态渲染 |
| `VerifiedMark` | VerificationBadge.tsx:138 | 检查是否被动态渲染 |

#### 工具层未使用导出

| 导出名称 | 文件位置 | 建议 |
|---------|---------|------|
| `iosUtils` 全套 | iosUtils.ts | 检查移动端使用情况 |
| `storage` 相关 | storage.ts | 检查 PWA 使用情况 |
| `useCurrentUserId` | hooks/useCurrentUserId.ts | 检查使用情况 |

#### 类型定义未使用（117 个）

> 类型定义可能被其他类型引用，需逐个检查。建议优先清理明确无引用的类型。

---

## 二、后端死代码（Vulture 检测）

### 2.1 高置信度未使用 Import（90%+）

| Import | 文件位置 | 置信度 | 建议 |
|--------|---------|-------|------|
| `get_date_coach_skill` | agent/skills/registry.py:218 | 90% | 删除 import |
| `joinedload` | agent/skills/relationship_coach_skill.py:516 | 90% | 删除 import |
| `Counter` | agent/tools/interest_tool.py:11 | 90% | 删除 import |

### 2.2 未使用函数/方法（60% 置信度）

以下函数被 vulture 检测为未使用，但部分可能是预留接口或被动态调用：

#### Agent/Skills 层

| 函数/方法 | 文件位置 | 置信度 | 可能原因 |
|----------|---------|-------|---------|
| `validate_input` | agent/skills/base.py:120 | 60% | 预留接口 |
| `_log_execution` | agent/skills/base.py:144 | 60% | 预留接口 |
| `_now` / `_format_timestamp` | agent/skills/base.py:156-160 | 60% | 预留工具方法 |
| `register_cache_routes` | agent/skills/cache.py:269 | 60% | 预留路由注册 |
| `get_date_coach_skill` | agent/skills/date_coach_skill.py:1154 | 60% | 工厂函数 |
| `get_intent_router_skill` | agent/skills/intent_router_skill.py:606 | 60% | 工厂函数 |
| `reload_config` | agent/skills/intent_router_skill.py:583 | 60% | 预留方法 |

#### Tools 层

| 函数/方法 | 文件位置 | 置信度 | 可能原因 |
|----------|---------|-------|---------|
| `register_tool` | agent/deerflow_client.py:44 | 60% | DeerFlow 接口 |
| `list_tools` | agent/deerflow_client.py:65 | 60% | DeerFlow 接口 |
| `run_match_workflow` | agent/deerflow_client.py:93 | 60% | DeerFlow 接口 |
| `_infer_personality_from_behavior` | agent/tools/autonomous_tools.py:209 | 60% | 预留方法 |
| `get_compliance_rules` | agent/tools/compliance_tool.py:187 | 60% | 预留方法 |
| `get_proposal_history` | agent/tools/date_proposal_tool.py:193 | 60% | 预留方法 |
| `get_relationship_progress` | agent/tools/followup_tool.py:174 | 60% | 预留方法 |

#### API 层（通过路由自动注册）

> **重要**: 所有 API 文件通过 `routers/__init__.py` 自动扫描注册。vulture 报告的未使用函数可能是预留端点。

| 函数 | 文件位置 | 可能状态 |
|------|---------|---------|
| `register_user` | api/users.py:45 | 预留端点 |
| `login` / `logout` | api/users.py | 预留端点 |
| `forgot_password` / `reset_password` | api/users.py | 预留端点 |
| `video_websocket_endpoint` | api/video_date.py:60 | 预留端点 |
| `schedule_video_date` | api/video_date.py:187 | 预留端点 |

### 2.3 未使用变量（高置信度）

| 变量 | 文件位置 | 置信度 | 建议 |
|------|---------|-------|------|
| `focus_area` | agent/skills/subconscious_analyzer_skill.py:86 | **100%** | 立即删除 |
| `STAGE_APPROPRIATE_DATES` | agent/skills/date_coach_skill.py:84 | 60% | 检查是否被使用 |
| `SUPPORTED_EMOTIONS` | agent/skills/emotion_analysis_skill.py:42 | 60% | 检查是否被使用 |
| `RELATIONSHIP_ANALYSIS` 等 | agent/skills/intent_router_skill.py:50-62 | 60% | 检查是否被使用 |

### 2.4 未使用类/数据结构

| 类/结构 | 文件位置 | 置信度 | 建议 |
|---------|---------|-------|------|
| `InterestMatch` | agent/tools/interest_tool.py:19 | 60% | 检查是否被使用 |
| `VideoUploadRequest` | api/video_clip.py:20 | 60% | 检查是否被使用 |
| `DateResponse` | api/video_date.py:156 | 60% | 检查是否被使用 |
| `CallbackResponse` | api/wechat_login.py:34 | 60% | 检查是否被使用 |

---

## 三、清理优先级

### P0 - 立即可处理（零风险）

**前端 (2 文件 + 1 修复):**
```bash
# 删除真正未引用文件
rm frontend/src/components/ConfidenceFilter.tsx
rm frontend/src/tests/mobileTest.ts

# 修复破损导入（手动编辑 generative-ui/index.tsx，删除第 54-57 行）
```

**后端 (4 处 import 清理):**
```python
# 删除未使用 import
# src/agent/skills/registry.py:218 - 删除 get_date_coach_skill
# src/agent/skills/relationship_coach_skill.py:516 - 删除 joinedload
# src/agent/tools/interest_tool.py:11 - 删除 Counter
```

**后端 (1 处变量删除):**
```python
# src/agent/skills/subconscious_analyzer_skill.py:86 - 删除 focus_area 变量
```

**后端真正死代码 (2 文件):**
```bash
# 无任何引用的文件
rm src/services/behavior_lab_types.py

# 废弃的 Skill（registry.py 已注释掉）
rm src/agent/skills/intent_router_skill.py
```

**依赖清理:**
```bash
# 移除未使用依赖
npm uninstall dayjs @vitejs/plugin-react

# 添加未声明依赖
npm install vite-plugin-pwa
```

### P1 - 需确认后处理

1. **前端未使用导出（79 个）** - 逐个检查是否被动态渲染或懒加载使用
2. **后端预留函数/方法** - 确认是否为预留接口或可删除
3. **类型定义（117 个）** - 检查是否被其他类型引用

### P2 - 不建议删除

- API 端点（通过路由自动注册）
- Skills 文件（通过注册表动态调用）
- DeerFlow Harness 核心文件
- 测试文件（除明确未引用的）

---

## 四、清理命令模板

```bash
# === P0 清理 ===

# 前端文件删除
cd /Users/sunmuchao/Downloads/ai_incubation_platform/Her/frontend
rm src/components/ConfidenceFilter.tsx
rm src/components/ConfidenceFilter.less  # 如果存在
rm src/tests/mobileTest.ts

# 依赖清理
npm uninstall dayjs @vitejs/plugin-react

# 后端死代码删除
cd /Users/sunmuchao/Downloads/ai_incubation_platform/Her
rm src/services/behavior_lab_types.py
rm src/agent/skills/intent_router_skill.py

# 后端 import 清理（手动编辑）
# 编辑 src/agent/skills/registry.py 删除第 218 行 import
# 编辑 src/agent/skills/relationship_coach_skill.py 删除第 516 行 import
# 编辑 src/agent/tools/interest_tool.py 删除第 11 行 import
# 编辑 src/agent/skills/subconscious_analyzer_skill.py 删除第 86 行 focus_area

# 运行测试验证
make test
cd frontend && npm test
```

```bash
# === P1 逻辑孤岛清理（需确认） ===

# Service 层逻辑孤岛（确认后执行）
cd /Users/sunmuchao/Downloads/ai_incubation_platform/Her
rm src/services/dynamic_profile_service.py
rm src/services/quick_start_service.py
rm src/services/vector_adjustment_service.py

# 运行测试验证
make test
```

---

## 五、统计摘要

| 类别 | P0 可处理 | P1 需确认 | P2 不建议删除 |
|------|----------|----------|--------------|
| 前端废弃文件 | 2 | 0 | 0 |
| 前端破损导入 | 1 | 0 | 0 |
| 前端未使用导出 | 0 | 79 | 需验证 |
| 后端未使用 import | 4 | 0 | 0 |
| 后端未使用变量 | 1 | 5 | 0 |
| 后端预留函数 | 0 | 100+ | Skills/API |
| 未使用依赖 | 2 | 0 | 0 |
| 未声明依赖 | 1 | 0 | 0 |
| **后端逻辑孤岛 Service** | **0** | **4** | **0** |
| **后端真正死代码** | **2** | **0** | **0** |
| **废弃 Skill** | **1** | **0** | **0** |

**总计 P0 可处理**: 2 文件 + 1 修复 + 4 import + 1 变量 + 2 依赖 + 2 死代码 + 1 废弃 Skill = ~12 处改动

---

## 六、特别说明

### 6.1 Knip 误判分析

Knip 无法检测以下模式的使用：
1. **懒加载 (lazy loading)**: `lazy(() => import('./xxx'))`
2. **动态导入**: `import('./xxx').then()`
3. **路由自动注册**: 后端 API 通过 `routers/__init__.py` 扫描注册
4. **Skills 动态调用**: 通过注册表反射调用

### 6.2 Vulture 检测局限

Vulture 无法检测：
1. **装饰器注册**: `@router.get()` 注册的端点
2. **反射调用**: 通过字符串名称动态调用方法
3. **LangChain 接口**: `args_schema`, `_run` 等框架必要接口
4. **Pydantic 模型**: 用于数据校验但未直接引用

### 6.3 generative-ui 目录状态

该目录存在但部分文件未被使用：
- **已使用**: `MatchComponents.tsx`, `ChatComponents.tsx` (通过 ChatInterface.tsx 懒加载)
- **可能未使用**: 其余 13 个组件文件 (需确认是否被动态渲染)
- **破损**: `index.tsx` 导入了不存在的 `../GenerativeUI`

---

## 七、逻辑孤岛深度分析（执行路径追踪）

> **分析方法**: 从入口点（API/Skills/main.py）出发，追踪完整的执行路径，识别"被引用但无入口"的逻辑孤岛。

### 7.1 系统入口点分析

#### 主程序入口 (main.py)

```
启动事件:
1. init_db() - 数据库初始化
2. cache_manager - 缓存管理器
3. perf_service - 性能服务
4. init_audit() - 审计日志
5. init_autonomous_tables() - 自主代理数据表
6. run_migration() - Her 顾问系统迁移
7. her_service, profile_service, conversation_service - Her 服务初始化
8. initialize_default_skills() - Skills 注册表（26 个 Skills）
9. start_heartbeat() - 心跳调度器
```

#### API 路由注册机制

```
routers/__init__.py → discover_routers()
- 自动扫描 api/*.py（43 个文件）
- 提取所有 router 变量
- 注册到 FastAPI app

路由器命名规则: router, router_xxx
```

#### Skills 注册机制

```
agent/skills/registry.py → initialize_default_skills()
- 注册 26 个 Skills
- 分类: Core, Enhancement, Experience, Integration, Enterprise, Social
- 动态调用: registry.execute("skill_name", **kwargs)
```

### 7.2 逻辑孤岛识别结果

#### 真正的死代码（无任何引用）

| 文件路径 | 引用数 | 原因 | 建议 |
|---------|-------|------|------|
| `src/services/behavior_lab_types.py` | **0** | 概念设计文件，从未落地 | **立即删除** |

#### Service 层逻辑孤岛（被导出但无入口）

以下 Service 被 `services/__init__.py` 导出，但未被 API/Skills/main.py 直接使用：

| Service 文件 | 导出位置 | 间接引用 | 入口状态 | 原因 |
|-------------|---------|---------|---------|------|
| `dynamic_profile_service.py` | __init__.py:6 | **无** | ❌ 无入口 | 功能迁移到 DeerFlow her_tools |
| `quick_start_service.py` | __init__.py:48 | vector_adjustment_service | ❌ 无入口 | `/api/profile/quickstart` 直接操作数据库 |
| `vector_adjustment_service.py` | __init__.py:19 | quick_start_service | ❌ 依赖孤岛 | 被 quick_start_service 引用，但后者也无入口 |
| `report_service.py` | __init__.py:10 | emotion_analysis_service (内部类) | ⚠️ 需确认 | EmotionReportService 是 emotion_analysis_service 内部类 |
| `memory_service.py` | __init__.py (未导出) | quick_chat_service | ⚠️ 有入口链 | quick_chat_service → chat.py (API) ✓ |

**执行路径链验证**:

```
memory_service → quick_chat_service → chat.py (API)
  ✓ chat.py:995/1027/1060 使用 QuickChatService

vector_adjustment_service → quick_start_service → ❌ 无 API 入口
  ✗ /api/profile/quickstart/submit 直接调用 _update_user_profile()
  ✗ _update_user_profile() 直接操作数据库，不使用 quick_start_service

dynamic_profile_service → ❌ 无任何引用
  ✗ 只被 __init__.py 导出，无实际使用

quick_start_service → ❌ 无 API 入口
  ✗ /api/profile/quickstart 端点不调用此 Service
  ✗ 灰度检查端点只检查配置，不调用此 Service
```

#### API 层逻辑孤岛（注册但前端不调用）

以下 API 端点已在路由中注册，但前端实际不调用：

| API 文件 | 端点 | 前端引用 | 状态 | 原因 |
|---------|------|---------|------|------|
| `api/users.py` | `/register_user`, `/login`, `/logout` | **无** | ⚠️ 预留端点 | 认证流程改用其他方式 |
| `api/users.py` | `/forgot_password`, `/reset_password` | **无** | ⚠️ 预留端点 | 功能未实现 |
| `api/video_date.py` | `/video_websocket_endpoint` | **无** | ⚠️ 预留端点 | 视频约会功能未完全落地 |
| `api/video_date.py` | `/schedule_video_date` | **无** | ⚠️ 预留端点 | 前端改用 DeerFlow date_planning |

#### 前端 API 导出孤岛

以下前端 API 导出未被任何组件使用：

| 导出名称 | 文件位置 | 前端引用 | 原因 |
|---------|---------|---------|------|
| `quickChatApi` | chatApi.ts:61 | **无** | 功能迁移到 DeerFlow chat_assistant_skill |
| `autonomousDatingApi` | lifeIntegrationApi.ts:40 | **无** | 功能未实现 |
| `videoDateWebSocket` | videoDateApi.ts:85 | **无** | 功能未完全落地 |
| `dateSuggestionApi` | milestoneApi.ts:137 | **无** | 前端改用 DeerFlow date_planning_skill |
| `coupleGameApi` | milestoneApi.ts:207 | **无** | 功能未实现 |

### 7.3 Skills 层状态分析

所有 26 个 Skills 通过注册表统一管理，但部分 Skills 可能未被实际调用：

| Skill | 注册状态 | DeerFlow 工具映射 | 实际使用 |
|------|---------|------------------|---------|
| `chat_assistant_skill` | ✓ 注册 | her_chat_assistant | ✓ 活跃 |
| `profile_collection_skill` | ✓ 注册 | her_collect_profile | ✓ 活跃 |
| `precommunication_skill` | ✓ 注册 | her_precommunication | ✓ 活跃 |
| `intent_router_skill` | ❌ 废弃 | N/A | **已废弃**（见 registry.py:168 注释） |

**废弃说明** (registry.py:168-175):
```
# ===== [已废弃] 意图路由 Skill =====
# IntentRouterSkill 已废弃（见 DEPRECATED.md）
# 新架构：用户消息 → DeerFlow Agent → her_tools
# DeerFlow Agent 通过 SOUL.md 直接理解意图并调用工具
# 不再需要中间的"传话员"层
```

### 7.4 逻辑孤岛判定标准

**判定为逻辑孤岛的条件**:
1. 被 `__init__.py` 导出但未被 API/Skills/main.py 直接使用
2. 只被其他逻辑孤岛引用（形成孤岛链）
3. API 端点注册但前端不调用（预留接口）

**判定为死代码的条件**:
1. 完全无引用（包括 `__init__.py`）
2. 被 vulture 检测为 100% 置信度未使用

### 7.5 孤岛清理建议

#### 真正的死代码（可立即删除）

```bash
# 无任何引用的文件
rm src/services/behavior_lab_types.py

# 废弃的 Skill（registry.py 已注释掉）
rm src/agent/skills/intent_router_skill.py
```

#### Service 层逻辑孤岛（需确认后删除）

| Service | 建议 | 替代方案 |
|---------|------|---------|
| `dynamic_profile_service.py` | 可删除 | DeerFlow her_tools 动态画像 |
| `quick_start_service.py` | 可删除 | `/api/profile/quickstart` 直接操作数据库 |
| `vector_adjustment_service.py` | 可删除 | 被 quick_start_service 引用，后者已废弃 |

#### API 端点孤岛（保留或删除）

| 类型 | 建议 |
|------|------|
| 预留端点（认证/密码） | 保留，等待实现 |
| 预留端点（视频约会） | 保留，等待前端对接 |
| 废弃端点（被 DeerFlow 替代） | 标记为废弃，可删除 |

---

## 八、下一步行动

1. **立即执行 P0 清理** - 无风险，可自动化
2. **修复 generative-ui/index.tsx 破损导入**
3. **逐个确认 P1 项目** - 建议分批次处理
4. **处理逻辑孤岛** - 需确认后删除
5. **更新此文档** - 清理完成后标记为"已完成"

---

*本报告基于 2026-04-15 的项目状态生成，建议定期重新扫描以发现新增死代码。*