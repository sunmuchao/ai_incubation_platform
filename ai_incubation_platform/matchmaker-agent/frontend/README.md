# AI Matchmaker 前端

**AI Native 智能红娘匹配系统前端**

## 快速开始

### 开发模式

```bash
cd frontend
npm install
npm run dev
```

### 生产构建

```bash
npm run build
```

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Ant Design 5** - UI 组件库
- **Axios** - HTTP 客户端
- **Less** - CSS 预处理器
- **Vite** - 构建工具

## AI Native 核心特性

### 1. 对话式交互 (Chat-first)

通过自然语言与 AI 红娘交流，表达匹配需求：

- "帮我找对象"
- "我想找喜欢旅行的女生"
- "看看今天有什么推荐"

### 2. Generative UI

- 动态生成的匹配卡片
- 兼容性环形进度条可视化
- 共同兴趣高亮显示
- AI 匹配理由展示

### 3. Agent 可视化

实时显示 AI 红娘工作状态：
- 分析偏好
- 寻找匹配
- 生成推荐
- 推送结果

**状态类型**:
- `idle` - AI 红娘待命中
- `analyzing` - 正在分析你的偏好
- `matching` - 正在寻找匹配对象
- `recommending` - 正在生成推荐
- `pushing` - 正在推送匹配结果

### 4. 主动推送

AI 发现高匹配候选人时主动推送通知

## 组件说明

| 组件 | 说明 |
|------|------|
| `ChatInterface` | 对话式匹配界面 |
| `MatchCard` | 动态匹配卡片 |
| `AgentVisualization` | Agent 状态可视化 |
| `PushNotifications` | AI 推送通知 |

## 项目结构

```
frontend/
├── src/
│   ├── api/
│   │   └── index.ts                 # API 服务层
│   ├── components/
│   │   ├── ChatInterface.tsx        # 对话式匹配界面
│   │   ├── MatchCard.tsx            # 动态匹配卡片
│   │   ├── AgentVisualization.tsx   # Agent 状态可视化
│   │   └── PushNotifications.tsx    # AI 推送通知
│   ├── pages/
│   │   └── HomePage.tsx             # AI Native 主页
│   ├── types/
│   │   └── index.ts                 # TypeScript 类型定义
│   ├── styles/
│   │   └── index.less               # 全局样式
│   ├── App.tsx                      # 应用入口
│   └── main.tsx                     # 主入口
└── package.json
```

## API 对接

前端对接后端 AI Native API：

| 接口 | 功能 |
|------|------|
| `POST /api/conversation-matching/match` | 对话式匹配 |
| `GET /api/conversation-matching/daily-recommend` | 每日推荐 |
| `GET /api/conversation-matching/ai/push/recommendations` | AI 推送 |
| `POST /api/conversation-matching/relationship/analyze` | 关系分析 |
| `POST /api/conversation-matching/topics/suggest` | 话题建议 |

### 调用示例

```typescript
import { conversationMatchingApi } from './api'

// 对话式匹配
const response = await conversationMatchingApi.match({
  user_intent: "我想找喜欢旅行的女生"
})

// 每日推荐
const response = await conversationMatchingApi.dailyRecommend()

// 关系分析
const response = await conversationMatchingApi.analyzeRelationship({
  match_id: "match_123",
  analysis_type: "health_check"
})
```

## 类型定义

```typescript
// 核心类型
interface MatchCandidate {
  user: User
  compatibility_score: number
  score_breakdown: Record<string, number>
  common_interests: string[]
  reasoning: string
}

interface ConversationMatchResponse {
  success: boolean
  message: string
  matches?: MatchCandidate[]
  suggestions?: string[]
  next_actions?: string[]
}

interface AgentStatus {
  status: 'idle' | 'analyzing' | 'matching' | 'recommending' | 'pushing'
  progress: number
  message: string
  current_action?: string
}
```

## 开发指南

### 添加新组件

1. 在 `src/components/` 下创建 `.tsx` 和 `.less` 文件
2. 在 `src/components/index.ts` 中导出
3. 在页面中使用

### 组件使用

```tsx
import { ChatInterface, MatchCard, AgentVisualization } from './components'

// 对话界面
<ChatInterface onMatchSelect={(match) => console.log(match)} />

// 匹配卡片
<MatchCard
  match={matchCandidate}
  onLike={() => console.log('liked')}
  onPass={() => console.log('passed')}
/>

// Agent 可视化
<AgentVisualization status={agentStatus} />
```

## AI Native 设计原则

1. **意图驱动**: 用户通过自然语言表达需求
2. **动态生成**: 界面根据上下文动态调整
3. **主动服务**: AI 主动发现问题并推送建议
4. **透明决策**: 展示 AI 匹配理由和置信度

## 注意事项

- 后端服务需运行在 `http://localhost:8007`
- 需要 JWT token 进行认证
- 开发模式下注意 CORS 配置

## 相关文档

- [AI Native 完成报告](../AI_NATIVE_COMPLETION_REPORT.md)
- [AI Native 白皮书](../AI_NATIVE_REDESIGN_WHITEPAPER.md)
- [项目完整文档](../PROJECT_DOCUMENTATION.md)
