# Matchmaker Agent - 前端开发文档

> **AI Native 婚恋匹配平台前端实现**
>
> **版本**: v2.0.0
> **更新日期**: 2026-04-07

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [架构设计](#3-架构设计)
4. [AI Native 原则](#4-ai-native-原则)
5. [文件结构](#5-文件结构)
6. [核心组件](#6-核心组件)
7. [API 服务](#7-api-服务)
8. [类型定义](#8-类型定义)
9. [开发指南](#9-开发指南)

---

## 1. 项目概述

Matchmaker Agent 是一个 AI 原生驱动的婚恋匹配平台前端，提供从匹配、破冰、约会到关系维护的全链路智能服务。

### 1.1 核心功能

| 阶段 | 功能模块 | 状态 |
|------|---------|------|
| **P0-P9** | 基础能力（匹配/认证/聊天） | ✅ 完成 |
| **P10** | 关系里程碑 | ✅ 完成 |
| **P13** | 情感调解增强 | ✅ 完成 |
| **P14** | 实战演习 | ✅ 完成 |
| **P15** | 虚实结合 | ✅ 完成 |
| **P16** | 圈子融合 | ✅ 完成 |
| **P17** | 终极共振 | ✅ 完成 |

---

## 2. 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **框架** | React | 18.3.1 |
| **语言** | TypeScript | 5.2.2 |
| **UI 库** | Ant Design | 5.14.0 |
| **HTTP** | Axios | Latest |
| **构建** | Vite | Latest |
| **样式** | Less | Latest |

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ HomePage    │  │ GenerativeUI│  │ AgentVisualization  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      组件层                                  │
│  ┌────────┐  ┌────────┐  ┌─────────┐  ┌─────────────────┐   │
│  │Chat    │  │Match   │  │Timeline │  │LoveLanguage     │   │
│  │Interface│ │Card    │  │         │  │Profile          │   │
│  └────────┘  └────────┘  └─────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      API 服务层                              │
│  ┌────────┐  ┌────────┐  ┌─────────┐  ┌─────────────────┐   │
│  │p10_api │  │p13_api │  │p14_api  │  │p15_p16_p17_api  │   │
│  └────────┘  └────────┘  └─────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      类型定义层                              │
│  ┌────────┐  ┌────────┐  ┌─────────┐  ┌─────────────────┐   │
│  │index   │  │p10_    │  │p13_     │  │p15_p16_         │   │
│  │        │  │types   │  │types    │  │p17_types        │   │
│  └────────┘  └────────┘  └─────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. AI Native 原则

### 4.1 对话优先 (Chat-first)

- 主界面为对话式交互
- 用户通过自然语言表达意图
- AI 从对话中提取参数并执行

### 4.2 Generative UI

- 界面由 AI 动态生成
- 根据任务类型动态重组
- 千人千面的个性化体验

### 4.3 自主性 (Autonomy)

- AI 主动发现问题并推送
- 多步工作流自主执行
- 高置信度时自主执行

### 4.4 情境化 (Contextual)

- 界面随用户角色动态调整
- 随使用场景动态变化
- 情境记忆和偏好学习

---

## 5. 文件结构

```
frontend/
├── src/
│   ├── api/
│   │   ├── index.ts              # 核心 API
│   │   ├── p10_api.ts            # P10 API 服务
│   │   ├── p13_api.ts            # P13 API 服务
│   │   ├── p14_api.ts            # P14 API 服务
│   │   └── p15_p16_p17_api.ts    # P15-P17 API 服务
│   ├── components/
│   │   ├── AgentVisualization.tsx    # AI Agent 可视化
│   │   ├── AgentVisualization.less
│   │   ├── ChatInterface.tsx         # 对话式匹配界面
│   │   ├── ChatInterface.less
│   │   ├── GenerativeUI.tsx          # Generative UI 容器
│   │   ├── GenerativeUI.less
│   │   ├── LoveLanguageProfile.tsx   # 爱之语画像
│   │   ├── LoveLanguageProfile.less
│   │   ├── MatchCard.tsx             # 匹配卡片
│   │   ├── MatchCard.less
│   │   ├── RelationshipTimeline.tsx  # 关系时间线
│   │   ├── RelationshipTimeline.less
│   │   └── index.ts
│   ├── pages/
│   │   ├── HomePage.tsx          # AI Native 主页面
│   │   └── HomePage.less
│   ├── types/
│   │   ├── index.ts              # 核心类型
│   │   ├── p10_types.ts          # P10 类型
│   │   ├── p13_types.ts          # P13 类型
│   │   ├── p14_types.ts          # P14 类型
│   │   └── p15_p16_p17_types.ts  # P15-P17 类型
│   ├── App.tsx                   # 应用入口
│   └── main.tsx                  # 入口文件
├── package.json
└── tsconfig.json
```

---

## 6. 核心组件

### 6.1 HomePage - AI Native 主页面

```tsx
import HomePage from './pages/HomePage'

function App() {
  return <HomePage />
}
```

**功能**:
- 对话式匹配界面
- 侧边导航菜单
- AI Agent 状态可视化
- 多视图切换

### 6.2 ChatInterface - 对话式匹配

```tsx
import ChatInterface from './components/ChatInterface'

<ChatInterface onMatchSelect={handleMatchSelect} />
```

**功能**:
- 自然语言输入
- AI 回复展示
- 匹配结果卡片
- 快捷操作建议

### 6.3 GenerativeUI - 动态 UI 容器

```tsx
import GenerativeUIContainer from './components/GenerativeUI'

<GenerativeUIContainer
  data={{
    type: 'match',
    priority: 'high',
    data: matchData,
    ai_message: '为你找到一位非常匹配的对象',
    actions: [{ label: '查看详情', action: 'view' }]
  }}
  onAction={handleAction}
/>
```

**功能**:
- 根据类型动态渲染
- 优先级颜色区分
- 动画效果
- 行动按钮

### 6.4 RelationshipTimeline - 关系里程碑

```tsx
import RelationshipTimeline from './components/RelationshipTimeline'

<RelationshipTimeline userId1="user-1" userId2="user-2" />
```

**功能**:
- 里程碑时间线
- 统计数据展示
- AI 分析卡片
- 庆祝交互

### 6.5 LoveLanguageProfile - 爱之语画像

```tsx
import LoveLanguageProfile from './components/LoveLanguageProfile'

<LoveLanguageProfile userId="user-1" onProfileLoaded={handleProfileLoaded} />
```

**功能**:
- 爱之语分数展示
- AI 分析解读
- 爱之语说明
- 一键分析

---

## 7. API 服务

### 7.1 核心 API

```typescript
import { conversationMatchingApi, matchingApi, chatApi, userApi } from './api'

// 对话式匹配
await conversationMatchingApi.match({ user_intent: '想找喜欢旅行的女生' })

// 获取推荐
await matchingApi.getRecommendations(15, { age_min: 25, age_max: 35 })

// 发送消息
await chatApi.sendMessage('user-2', '你好', 'text')
```

### 7.2 P10 API - 关系里程碑

```typescript
import { milestoneApi, dateSuggestionApi, coupleGameApi } from './api'

// 记录里程碑
await milestoneApi.recordMilestone({
  user_id_1: 'user-1',
  user_id_2: 'user-2',
  milestone_type: 'first_date',
  title: '第一次约会',
  description: '在咖啡厅见面'
})

// 获取时间线
await milestoneApi.getMilestoneTimeline('user-1', 'user-2')

// 生成约会建议
await dateSuggestionApi.generateDateSuggestion('user-1', 'user-2', 'coffee')
```

### 7.3 P13 API - 情感调解增强

```typescript
import { loveLanguageProfileApi, relationshipTrendApi, warningResponseApi } from './api'

// 分析爱之语
await loveLanguageProfileApi.analyzeUserLoveLanguage('user-1')

// 关系趋势预测
await relationshipTrendApi.generateTrendPrediction('user-1', 'user-2', '7d')
```

### 7.4 P14 API - 实战演习

```typescript
import { avatarApi, simulationApi, outfitApi, venueApi, topicApi } from './api'

// 创建 AI 分身
await avatarApi.createAIDateAvatar('user-1', {
  avatar_name: '温柔型分身',
  personality_traits: [{ trait: 'gentle', intensity: 0.8 }],
  conversation_style: 'gentle'
})

// 开始模拟
await simulationApi.startSimulation('user-1', {
  avatar_id: 'avatar-1',
  scenario_type: 'first_coffee'
})
```

### 7.5 P15-P17 API

```typescript
import {
  datePlanApi, albumApi,       // P15
  tribeApi, digitalHomeApi, familySimApi,  // P16
  stressTestApi, growthPlanApi, trustApi   // P17
} from './api'
```

---

## 8. 类型定义

### 8.1 核心类型

```typescript
import type {
  User,
  MatchCandidate,
  AgentStatus,
  GenerativeCardData
} from './types'
```

### 8.2 P10 类型

```typescript
import type {
  Milestone,
  MilestoneTimeline,
  DateSuggestion,
  CoupleGame,
  GameInsights
} from './types'
```

### 8.3 P13 类型

```typescript
import type {
  LoveLanguageProfile,
  RelationshipTrendPrediction,
  EmotionWarning,
  ComprehensiveRelationshipAnalysis
} from './types'
```

### 8.4 P14 类型

```typescript
import type {
  AIDateAvatar,
  DateSimulation,
  OutfitRecommendation,
  VenueStrategy,
  TopicKit
} from './types'
```

---

## 9. 开发指南

### 9.1 组件开发规范

```tsx
import React from 'react'
import { Card, Typography } from 'antd'
import type { MyComponentProps } from '../types'
import './MyComponent.less'

const { Text } = Typography

interface MyComponentProps {
  userId: string
  onAction?: (action: string) => void
}

const MyComponent: React.FC<MyComponentProps> = ({
  userId,
  onAction,
}) => {
  // 组件逻辑

  return (
    <Card className="my-component">
      {/* 组件内容 */}
    </Card>
  )
}

export default MyComponent
```

### 9.2 API 开发规范

```typescript
import axios from 'axios'
import type { MyRequest, MyResponse } from '../types'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// JWT 拦截器
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const myApi = {
  async getData(id: string): Promise<MyResponse> {
    const response = await api.get(`/api/my/${id}`)
    return response.data
  },
}
```

### 9.3 样式开发规范

```less
.my-component {
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
  }

  .header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
  }

  .content {
    padding: 16px;
  }
}
```

### 9.4 测试开发规范

**使用 Jest + React Testing Library 编写测试**:

```tsx
// MyComponent.test.tsx
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import MyComponent from './MyComponent'

describe('MyComponent', () => {
  const mockProps = {
    userId: 'user-001',
    onAction: jest.fn(),
  }

  it('renders correctly', () => {
    render(<MyComponent {...mockProps} />)
    expect(screen.getByText(/some text/i)).toBeInTheDocument()
  })

  it('calls onAction when button clicked', async () => {
    render(<MyComponent {...mockProps} />)
    const button = screen.getByRole('button', { name: /action/i })
    fireEvent.click(button)
    await waitFor(() => {
      expect(mockProps.onAction).toHaveBeenCalled()
    })
  })
})
```

**运行测试**:

```bash
# 运行所有测试
npm run test

# 运行单个文件的测试
npm run test -- MyComponent.test.tsx

# 生成覆盖率报告
npm run test:coverage

# 监听模式运行测试
npm run test:watch
```

---

## 10. 测试指南

### 10.1 后端测试 (pytest)

```bash
# 运行所有测试
cd ..
pytest

# 运行特定模块的测试
pytest tests/test_relationship_milestone_service.py -v

# 生成覆盖率报告
pytest --cov=src/services --cov-report=html

# 运行单个测试
pytest tests/test_relationship_milestone_service.py::TestRelationshipMilestoneService::test_record_milestone_success -v
```

### 10.2 前端测试 (Jest)

```bash
# 运行所有测试
cd frontend
npm run test

# 生成覆盖率报告
npm run test:coverage
```

### 10.3 测试文件组织

```
tests/
├── conftest.py                     # 测试配置
├── test_ai_native.py               # AI Native 测试
├── test_relationship_milestone_service.py   # P10 里程碑服务测试
├── test_date_suggestion_service.py          # P10 约会建议服务测试
├── test_p13_enhancement_service.py          # P13 情感调解服务测试
├── test_p14_services.py                     # P14 实战演习服务测试
├── test_external_services.py                # 外部服务测试
└── p10/                            # P10 集成测试
└── p11/                            # P11 集成测试
└── p12/                            # P12 集成测试
```

### 10.4 外部服务配置

**天气服务配置** (用于 P14 穿搭推荐):

```bash
# .env 或 .env.local
WEATHER_PROVIDER=mock  # mock, openweathermap, qweather
OPENWEATHERMAP_API_KEY=your_key_here
QWEATHER_API_KEY=your_key_here
```

**预订服务配置** (用于 P15 自主约会策划):

```bash
# .env 或 .env.local
RESERVATION_RESTAURANT_PROVIDER=mock  # mock, dianping
RESERVATION_CINEMA_PROVIDER=mock      # mock, maoyan
DIANPING_API_KEY=your_key_here
MAOYAN_API_KEY=your_key_here
```

**测试模式**:

所有外部服务都提供 Mock 实现，测试环境自动使用 Mock，无需真实 API 密钥。

---

## 附录

### A. 快速开始

```bash
# 安装依赖
cd frontend
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

### B. API 端点映射

| 功能 | API 端点 | 服务方法 |
|------|---------|---------|
| 对话匹配 | `/api/conversation-matching/match` | `conversationMatchingApi.match()` |
| 推荐列表 | `/api/matching/recommend` | `matchingApi.getRecommendations()` |
| 里程碑时间线 | `/api/milestones/timeline/{user1}/{user2}` | `milestoneApi.getMilestoneTimeline()` |
| 爱之语分析 | `/api/p13/love-language-profile/analyze` | `loveLanguageProfileApi.analyzeUserLoveLanguage()` |

### C. 常见问题

**Q: 如何处理 JWT 认证？**
A: 登录后将 token 存入 localStorage，API 拦截器自动添加。

**Q: Generative UI 如何工作？**
A: 接收 `GenerativeCardData`，根据 `type` 动态渲染不同卡片。

**Q: 如何添加新功能？**
A: 1) 在 types 添加类型 2) 在 api 添加服务 3) 创建组件 4) 在 HomePage 集成

---

**文档版本**: v2.0.0
**最后更新**: 2026-04-07
**维护者**: AI Assistant
