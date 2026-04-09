# 红娘 Agent (Matchmaker Agent)

> **让每一次匹配都有意义，让每一段关系都值得期待。**

红娘 Agent 是一个 **AI 驱动的深度婚恋匹配平台**，旨在通过智能算法和数据分析帮助用户找到真正匹配的伴侣或合作伙伴。

**当前版本**: v1.28.0 (AI Native 架构增强版)

## 核心差异化

我们不做"看脸滑动"的浅层社交，而是通过 AI 深度理解用户的价值观、性格特质、沟通风格和关系需求，实现"越用越懂你"的匹配体验。

| 竞品做法 | 红娘 Agent 做法 |
|---------|---------------|
| 滑动匹配看脸 | AI 分析价值观/兴趣/沟通风格 |
| 用户自己写简介 | AI 对话生成深度画像 |
| 匹配后靠用户聊 | AI 生成破冰话题、关系建议 |
| 成了就离开平台 | AI 追踪关系进展持续服务 |
| 黑盒推荐 | 可解释匹配、透明算法 |

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+ (前端)
- SQLite (默认) 或 PostgreSQL
- Redis (可选，用于缓存)

### 后端安装

```bash
cd Her
pip install -r requirements.txt
```

### 前端安装

```bash
cd Her/frontend
npm install
```

### 配置

复制环境变量配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要的参数：

```bash
# 应用配置
APP_NAME=matchmaker-agent
APP_VERSION=1.28.0
ENVIRONMENT=development
DEBUG=True

# 数据库配置
DATABASE_URL=sqlite:///./matchmaker_agent.db

# JWT 配置
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 服务配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### 启动服务

**后端服务**：
```bash
cd Her
python -m src.main
# 或使用 uvicorn
uvicorn src.main:app --reload --port 8000
```

**前端服务** (新窗口)：
```bash
cd Her/frontend
npm run dev
```

访问应用：
- 前端应用：http://localhost:3006/
- API 文档：http://localhost:8000/docs

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_ai_companion_service.py -v
pytest tests/test_matcher.py -v
pytest tests/test_membership_service.py -v

# 查看测试覆盖率
pytest --cov=src --cov-report=html
```

## 功能特性

### 已实现功能

| 阶段 | 功能 | 状态 |
|------|------|------|
| P0 | JWT 认证、AI 匹配算法、SQLite 持久化、API 限流、缓存系统 | ✅ |
| P1 | 破冰问题生成、地理位置距离计算、性格兼容性分析 | ✅ |
| P2 | 用户举报/封禁系统、兴趣社区匹配 | ✅ |
| P3 | 动态用户画像、行为追踪与学习 | ✅ |
| P4 | 照片管理、实名认证、实时聊天 | ✅ |
| P5 | 会员订阅体系、滑动交互 | ✅ |
| P6 | 信任标识体系、视频通话、AI 陪伴助手、关系类型标签、行为学习推荐 | ✅ |
| P7 | 安全风控 AI、对话分析助手增强 | ✅ |
| P8 | 企业数据看板、绩效管理、组织架构、运营角色 | ✅ |
| P9 | 推送通知系统、分享机制、邀请码 | ✅ |
| P10-P17 | 深度认知、感官洞察、情感调解等下一代功能 | ✅ 模型定义完成 |
| P18-P22 | AI 预沟通、消费画像、地理轨迹等 | ✅ 模型定义完成 |

### AI Native 架构增强 (v1.28.0)

**新增 Agent Skill 系统**，所有外部服务通过统一的 Skill 接口封装：

| Skill | 功能 | 自主触发 |
|-------|------|----------|
| `matchmaking_assistant` | AI 匹配助手 | 高质量匹配推送 |
| `pre_communication` | AI 预沟通 | 关系阶段推进 |
| `omniscient_insight` | AI 全知感知 | 异常检测 |
| `relationship_coach` | 关系教练 | 定期关系检查 |
| `date_planning` | 约会策划 | 纪念日提醒 |
| `bill_analysis` | 账单分析 | 消费异常检测 |
| `geo_location` | 地理位置 | 附近匹配提醒 |
| `gift_ordering` | 礼物订购 | 生日/纪念日提醒 |

**Generative UI 组件库** - AI 动态生成界面：
- `MatchSpotlight` - 单个高匹配对象展示
- `MatchCardList` / `MatchCarousel` - 匹配卡片列表/轮播
- `GiftGrid` / `GiftCarousel` - 礼物推荐网格
- `ConsumptionProfile` - 消费画像
- `DateSpotList` - 约会地点推荐
- `HealthReport` - 关系健康度报告

### AI 杀手级功能

我们的核心 AI 能力：

1. **AI 深度画像** - 通过对话和行为分析，构建性格/价值观/沟通风格的深度画像
2. **可解释匹配** - 每个匹配都有详细的理由和兼容性分析
3. **对话分析助手** - 分析聊天内容，给出关系建议和沟通指导
4. **关系进展追踪** - 识别关系阶段，给出下一步建议
5. **智能破冰** - 根据双方兴趣生成话题
6. **安全风控 AI** - 识别骚扰/诈骗/不当内容，保护用户安全
7. **AI 预沟通** - 在正式约会前，AI 辅助双方进行初步沟通
8. **Generative UI** - 根据场景动态生成最适合的界面

## API 端点

### 核心接口

| 接口 | 描述 |
|------|------|
| `POST /api/users/register` | 用户注册 |
| `POST /api/users/login` | 用户登录 |
| `POST /api/users/refresh` | 刷新令牌 |
| `GET /api/matching/candidates` | 获取推荐候选人 |
| `POST /api/matching/calculate` | 计算匹配度 |
| `GET /api/behavior/track` | 行为追踪 |
| `GET /api/relationship/progress` | 关系进展 |

### AI Native 接口 (v1.28.0 新增)

| 接口 | 描述 |
|------|------|
| `POST /api/agent/skill/execute` | 执行 Agent Skill |
| `GET /api/agent/skills` | 获取可用 Skills 列表 |
| `POST /api/ai/pre-communication` | AI 预沟通会话 |
| `GET /api/ai/pre-communication/sessions` | 获取预沟通会话历史 |
| `POST /api/ai/omniscient/perceive` | AI 全知感知 |

### 高级功能接口

| 接口 | 描述 |
|------|------|
| `POST /api/photos/upload` | 照片上传 |
| `POST /api/identity/verify` | 实名认证 |
| `POST /api/chat/send` | 发送消息 |
| `GET /api/chat/conversations` | 获取聊天历史 |
| `POST /api/membership/subscribe` | 会员订阅 |
| `POST /api/video/call` | 视频通话 |
| `GET /api/verification/badges` | 获取信任标识 |
| `POST /api/safety/check-content` | 内容安全检测 |
| `GET /api/safety/user-risk/{user_id}` | 用户风险评估 |
| `GET /api/dashboard/overview` | 获取企业数据看板 (P8) |
| `GET /api/performance/kpi-definitions` | 获取 KPI 定义 (P8) |
| `GET /api/departments/tree` | 获取组织架构树 (P8) |
| `POST /api/exports` | 创建数据导出任务 (P8) |
| `GET /api/notifications/unread-count` | 获取未读通知数 (P9) |
| `GET /api/notifications` | 获取通知列表 (P9) |
| `POST /api/notifications/{id}/read` | 标记通知为已读 (P9) |
| `POST /api/notifications/read-all` | 标记全部为已读 (P9) |
| `POST /api/share/invite-code` | 创建邀请码 (P9) |
| `GET /api/share/invite-codes` | 获取我的邀请码 (P9) |
| `POST /api/share/invite-code/validate` | 验证邀请码 (P9) |
| `POST /api/share/invite-code/use` | 使用邀请码 (P9) |
| `GET /api/share/stats` | 获取分享统计 (P9) |
| `GET /api/share/invite-stats` | 获取邀请统计 (P9) |

详细 API 文档请查看：http://localhost:8000/docs

## 项目结构

```
Her/
├── src/
│   ├── api/                    # API 路由层
│   │   ├── users.py            # 用户接口
│   │   ├── matching.py         # 匹配接口
│   │   ├── safety.py           # 安全风控接口 (P7)
│   │   ├── conversations_v2.py # 对话分析接口
│   │   └── ...
│   ├── services/               # 业务逻辑层
│   │   ├── safety_ai_service.py    # 安全风控 AI (P7)
│   │   ├── conversation_analysis_service.py  # 对话分析
│   │   ├── behavior_learning_service.py      # 行为学习
│   │   └── ...
│   ├── models/                 # 数据模型
│   │   ├── user.py             # 用户模型
│   │   ├── membership.py       # 会员模型
│   │   ├── payment.py          # 支付模型
│   │   └── __init__.py         # 模型注册中心
│   ├── db/                     # 数据库层
│   │   ├── database.py         # 数据库连接
│   │   ├── models.py           # SQLAlchemy 模型
│   │   ├── repositories.py     # 数据访问层
│   │   ├── payment_models.py   # 支付数据库模型
│   │   └── audit.py            # 审计日志
│   ├── matching/               # 匹配算法
│   │   └── matcher.py          # 匹配引擎
│   ├── auth/                   # 认证模块
│   │   ├── jwt.py              # JWT 认证
│   │   └── ...
│   ├── middleware/             # 中间件
│   │   ├── rate_limiter.py     # API 限流
│   │   └── ...
│   ├── cache/                  # 缓存模块
│   │   └── cache_manager.py    # 缓存管理
│   ├── agent/                  # AI Agent 模块 (v1.28.0 新增)
│   │   ├── skills/             # Agent Skills
│   │   │   ├── precommunication_skill.py
│   │   │   ├── bill_analysis_skill.py
│   │   │   ├── geo_location_skill.py
│   │   │   ├── gift_ordering_skill.py
│   │   │   └── registry.py
│   │   ├── tools/              # Agent 工具
│   │   └── workflows/          # Agent 工作流
│   ├── llm/                    # LLM 集成 (v1.28.0 新增)
│   │   └── skill_enhancer.py   # Skill 意图理解与响应生成
│   ├── integration/            # 外部服务集成 (v1.28.0 新增)
│   │   └── external_services.py # 账单/地理/礼物服务客户端
│   ├── config.py               # 配置管理
│   └── main.py                 # 应用入口
├── tests/                      # 测试文件
│   ├── test_matcher.py         # 匹配引擎测试
│   ├── test_skills.py          # AI Native Skills 测试
│   ├── test_ai_companion_service.py
│   └── ...
├── frontend/                   # 前端页面
│   ├── src/
│   │   ├── components/         # React 组件
│   │   │   ├── ChatInterface.tsx       # 对话界面
│   │   │   ├── ChatRoom.tsx            # 聊天室
│   │   │   ├── MatchCard.tsx           # 匹配卡片
│   │   │   ├── GenerativeUI.tsx        # Generative UI 组件库
│   │   │   └── ...
│   │   ├── pages/              # 页面组件
│   │   │   ├── HomePage.tsx            # 主页
│   │   │   ├── LoginPage.tsx           # 登录页
│   │   │   └── ...
│   │   ├── api/                # API 客户端
│   │   └── styles/             # 全局样式
│   ├── package.json
│   └── vite.config.ts
├── requirements.txt            # 依赖列表
└── README.md                   # 本文档
```

## 测试覆盖

当前测试覆盖情况：

```
总计：300+ 测试用例

# AI Native Skills 测试 (v1.28.0)
pytest tests/test_skills.py -v
# 42 个测试用例，85.7% 通过率

# 查看测试覆盖率
pytest --cov=src --cov-report=html
```

## AI Native 设计原则

本项目遵循 **AI Native** 架构设计原则：

1. **AI 依赖** - 没有 AI，核心功能失效或严重降级
2. **自主性** - AI 主动建议/自主执行，而非被动响应
3. **对话优先** - 交互范式为自然语言对话，而非表单 + 按钮
4. **Generative UI** - 界面由 AI 动态生成，而非固定布局
5. **架构模式** - `Agent + Tools` 模式，AI 为底层引擎

## 技术架构

### 后端技术栈

- **Web 框架**: FastAPI
- **数据库**: SQLite / PostgreSQL
- **ORM**: SQLAlchemy 2.0
- **认证**: JWT (python-jose)
- **缓存**: Redis (可选)
- **AI/ML**: PyTorch, Transformers, scikit-learn

### 前端技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite 5
- **UI 库**: Ant Design 5
- **样式**: Less + CSS Modules
- **状态管理**: React Hooks

### AI 能力

- **匹配算法**: 多维度兼容性计算（兴趣、价值观、性格、行为）
- **对话分析**: 话题提取、情感分析、沟通风格识别
- **安全风控**: 关键词检测、模式识别、用户风险评估
- **动态画像**: 基于行为持续学习更新用户特征
- **LLM 集成**: 意图理解、响应生成、Generative UI 选择 (v1.28.0)

### AI Native 架构组件 (v1.28.0)

- **Skill Registry** - 统一的 Skill 注册与执行中心
- **Skill Intent Parser** - LLM 驱动的自然语言意图理解
- **Skill Response Generator** - AI 响应生成与 UI 选择
- **External Services** - 账单/地理/礼物服务的 Skill 化封装
- **Generative UI Components** - React 动态组件库

## 核心价值观

1. **用户第一**: 始终把用户利益放在首位
2. **深度理解**: 追求对用户深度、全面、动态的理解
3. **可解释 AI**: 让 AI 的决策过程透明、可理解、可信任
4. **安全与隐私**: 将用户安全和隐私保护视为不可妥协的底线
5. **持续迭代**: 保持快速学习和改进，越用越懂用户
6. **真诚连接**: 促进用户之间真实、深度的连接
7. **AI Native**: AI 作为核心决策引擎，而非功能模块

## 愿景

> **成为中国最可信赖的 AI 婚恋顾问，帮助 1000 万用户找到人生伴侣。**

## AI Native 成熟度等级

| 等级 | 名称 | 标准 | 当前状态 |
|------|------|------|----------|
| L1 | 工具 | AI 作为工具被调用 | ✅ 已完成 |
| L2 | 助手 | AI 提供主动建议 | ✅ 已完成 |
| L3 | 代理 | AI 自主规划执行 | ✅ v1.28.0 达成 |
| L4 | 伙伴 | AI 持续学习成长 | 🚧 进行中 |
| L5 | 专家 | AI 领域超越人类 | 📅 长期愿景 |

## 开发路线

### 已完成
- [x] P0: 基础匹配功能
- [x] P1: 竞品功能对标
- [x] P2: 安全机制与兴趣社交
- [x] P3: 动态画像
- [x] P4: 照片管理与实时聊天
- [x] P5: 会员订阅
- [x] P6: 视频通话、信任标识、AI 陪伴
- [x] P7: 安全风控 AI、对话分析增强
- [x] P8: 企业数据看板与绩效管理
- [x] P9: 推送通知系统、分享机制
- [x] P10-P17: 下一代功能模型定义
- [x] P18-P22: AI 预沟通等模型定义
- [x] AI Native 架构增强 (v1.28.0) - Agent Skill 系统、Generative UI

### 规划中

**近期优化：**
- [ ] LLM 真实集成（当前使用关键词匹配降级方案）
- [ ] 外部 API 对接（账单/地理/礼物服务）
- [ ] 性能优化（LLM 响应缓存、查询优化）
- [ ] 移动端适配

**下一代功能（P10-P17）：**

| 阶段 | 主题 | 核心功能 |
|------|------|---------|
| P10 | 深度认知 | 数字潜意识、频率共振匹配、千人千面匹配卡 |
| P11 | 感官洞察 | AI 视频面诊、物理安全守护神 |
| P12 | 行为实验室 | 双人互动游戏、时机感知破冰、关系健康体检 |
| P13 | 情感调解 | 吵架预警、爱之语翻译、关系气象报告 |
| P14 | 实战演习 | 约会模拟沙盒、全能约会辅助、多代理协作 |
| P15 | 虚实结合 | 自主约会策划、情感纪念册 |
| P16 | 圈子融合 | 部落匹配、数字小家、见家长模拟 |
| P17 | 终极共振 | 压力测试、成长计划、靠谱背书 |

详见 [PRODUCT_ROADMAP.md](./PRODUCT_ROADMAP.md)

## 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 许可证

本项目采用 MIT 许可证

## 联系方式

- 项目地址：https://github.com/your-org/Her
- 问题反馈：请通过 GitHub Issues 提交

---

*让每一次匹配都有意义，让每一段关系都值得期待。*
