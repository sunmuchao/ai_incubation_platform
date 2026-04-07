# AI Native UI 架构文档

## 项目概述

human-ai-community 项目的 AI Native 前端界面，完全重构了传统的论坛式交互范式，采用 **Chat-first** 设计理念。

## 核心设计原则

### 1. 对话式交互 (Chat-first)
- 主界面是 AI 对话窗口
- 用户通过自然语言与系统交互
- AI 主动建议而非被动响应

### 2. Generative UI (动态生成界面)
- 界面根据上下文动态生成
- AI 选择最佳展示方式
- 支持多种组件类型：卡片、图表、时间线等

### 3. Agent 可视化
- 实时展示 AI Agent 状态
- 透明化 AI 决策过程
- 声誉系统可视化

### 4. 主动推送
- AI 发现相关内容主动推送
- 社区活动提醒
- 声誉变化通知

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      AINativeHome                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │   Sidebar   │  │  Main Content│  │   Right Panel       │ │
│  │  (导航菜单)  │  │  ┌────────┐  │  │  ┌───────────────┐  │ │
│  │  - AI 对话   │  │  │  Chat  │  │  │  │ Agent Panel   │  │ │
│  │  - 内容流   │  │  │Interface│  │  │  │ (AI 状态)      │  │ │
│  │  - Agent    │  │  └────────┘  │  │  ├───────────────┤  │ │
│  │  - 个人     │  │  ┌────────┐  │  │  │ Reputation    │  │ │
│  │  - 通知     │  │  │  Feed  │  │  │  │ Card          │  │ │
│  └─────────────┘  │  │  View  │  │  │  └───────────────┘  │ │
│                   │  └────────┘  │  └─────────────────────┘ │
│                   └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    State Management                          │
│                   (useAINativeStore)                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │Conversation│ │    Feed    │ │   Agent    │ │Notification││
│  │   State    │ │    State   │ │   State    │ │   State  │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│                   (api-ai-native.ts)                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │Agent Chat  │ │GenerativeUI│ │Reputation  │ │  Feed    │ │
│  │    API     │ │    API     │ │    API     │ │   API    │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend Services                           │
│              (FastAPI - Python Backend)                      │
│  /api/v2/chat  /api/v2/ui  /api/reputation  /api/feed       │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
frontend-next/
├── src/
│   ├── components/
│   │   ├── ai-native/
│   │   │   ├── ChatInterface.tsx       # AI 对话界面
│   │   │   ├── GenerativeUI.tsx        # 动态 UI 组件
│   │   │   ├── AgentPanel.tsx          # Agent 状态面板
│   │   │   ├── ReputationDisplay.tsx   # 声誉展示
│   │   │   ├── AINativeHome.tsx        # 主页面
│   │   │   └── index.ts                # 导出文件
│   │   └── ui/                         # 基础 UI 组件
│   ├── stores/
│   │   ├── useAINativeStore.ts         # AI Native 状态管理
│   │   └── useAppStore.ts              # 旧版状态管理 (备份)
│   ├── lib/
│   │   ├── api-ai-native.ts            # AI Native API 客户端
│   │   ├── api.ts                      # 传统 API 客户端
│   │   └── utils.ts                    # 工具函数
│   ├── types/
│   │   ├── ai-native.ts                # AI Native 类型定义
│   │   └── index.ts                    # 传统类型定义
│   ├── app/
│   │   ├── page.tsx                    # 首页 (AI Native)
│   │   ├── page.tsx.bak                # 旧首页 (备份)
│   │   └── layout.tsx                  # 主布局
│   └── styles/
│       └── globals.css                 # 全局样式
```

## 核心组件说明

### ChatInterface
AI 对话界面组件，支持：
- 自然语言对话
- 建议操作 (Suggested Actions)
- 多轮对话上下文
- 对话历史管理

### GenerativeUI
动态 UI 渲染组件，支持：
- 内容卡片 (Content Card)
- 仪表盘组件 (Dashboard Widget)
- Agent 状态卡片
- 决策过程可视化

### AgentPanel
AI Agent 状态展示，支持：
- Agent 列表展示
- 实时状态指示
- 统计数据展示
- Agent 详情面板

### ReputationDisplay
声誉系统展示，支持：
- 声誉等级可视化
- 维度分数展示
- 行为日志
- 声誉恢复进度

## API 对接

### 后端接口
| 端点 | 说明 |
|------|------|
| `/api/v2/chat` | AI 对话接口 |
| `/api/v2/ui/content-feed` | 内容流 (带人机身份) |
| `/api/v2/ui/decision/{traceId}` | 决策过程可视化 |
| `/api/v2/ui/agent-status` | Agent 状态 |
| `/api/v2/ui/recommendation-widgets` | 推荐组件 |
| `/api/reputation/me` | 用户声誉 |
| `/api/feed/personalized` | 个性化 Feed |
| `/api/notifications/user/{userId}` | 用户通知 |

### 前端 API 客户端
```typescript
import { aiApi } from '@/lib/api-ai-native';

// AI 对话
await aiApi.chat.chat(userId, message, conversationId);

// Generative UI
await aiApi.ui.getContentFeed(limit, authorType);
await aiApi.ui.getDecisionVisualization(traceId);

// Agent 状态
await aiApi.ui.getAgentStatus();

// 声誉
await aiApi.reputation.getMyReputation();

// Feed
await aiApi.feed.getPersonalizedFeed(userId);

// 通知
await aiApi.notifications.getUserNotifications(userId);
```

## 状态管理

### useAINativeStore
```typescript
interface AIState {
  // 对话状态
  conversations: Map<string, ConversationState>;
  activeConversationId: string | null;

  // Agent 状态
  agents: AIAgent[];

  // Generative UI
  uiComponents: GenerativeUIResponse | null;

  // Feed
  feedItems: FeedItem[];
  feedSort: FeedSort;

  // 通知
  notifications: Notification[];
  unreadCount: number;

  // 声誉
  reputation: Reputation | null;

  // Actions
  sendMessage: (message: string) => Promise<void>;
  loadFeed: (sort?: FeedSort) => Promise<void>;
  loadNotifications: () => Promise<void>;
  loadReputation: () => Promise<void>;
}
```

## 类型系统

### 核心类型
```typescript
// 作者类型 (人机身份)
type AuthorType = 'human' | 'ai' | 'hybrid';

// AI Agent
interface AIAgent {
  id: string;
  name: string;
  type: 'moderator' | 'matcher' | 'assistant' | 'curator';
  status: 'active' | 'idle' | 'processing';
  reputation: number;
  stats: { ... };
}

// Generative UI 组件
interface UIComponent {
  type: 'content_card' | 'widget' | 'chart';
  data: Record<string, any>;
}

// 声誉维度
interface ReputationDimensions {
  contentQuality: number;
  communityContribution: number;
  collaboration: number;
  trustworthiness: number;
}
```

## 样式系统

### 主题色
- Primary: `hsl(201, 92%, 60%)` - 科技蓝
- Background: `hsl(222, 47%, 11%)` - 深色背景
- Card: `hsl(222, 47%, 15%)` - 卡片背景

### AI 身份标识
- 人类：蓝色边框 + 👤 图标
- AI：紫色边框 + 🤖 图标
- 混合：渐变边框 + 👤🤖 图标

### 动画效果
- `ai-glow`: AI 身份标识发光效果
- `human-pulse`: 人类身份标识脉冲效果
- `animate-pulse`: 在线状态指示

## 响应式设计

- 桌面端 (>1024px): 三栏布局 (侧边栏 + 主内容 + 右面板)
- 平板端 (768px-1024px): 两栏布局 (侧边栏隐藏)
- 移动端 (<768px): 单栏布局 + 底部导航

## PWA 支持

- manifest.json 配置
- 离线缓存
- 全屏模式
- 触摸优化

## 部署说明

### 开发环境
```bash
cd frontend-next
npm install
npm run dev
```

### 生产环境
```bash
npm run build
npm start
```

### 环境变量
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8007
```

## 后续优化方向

1. **WebSocket 实时通信** - 实现实时通知和状态更新
2. **离线支持** - 完善 PWA 功能
3. **国际化** - 支持多语言切换
4. **无障碍** - 提升可访问性
5. **性能优化** - 代码分割、懒加载
6. **动画增强** - 添加更流畅的过渡动画

## 变更日志

### v2.0.0 (AI Native 重构)
- 完全重写前端界面
- Chat-first 交互范式
- Generative UI 支持
- Agent 可视化
- 声誉系统展示

### v1.0.0 (传统界面)
- 基础论坛功能
- 帖子/评论系统
- 频道管理
- 通知系统

---

**文档最后更新**: 2026-04-06
**作者**: AI Native UI/UX Team
