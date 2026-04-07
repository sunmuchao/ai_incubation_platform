# AI Native UI 设计文档

**项目**: ai-employee-platform
**版本**: v4.0.0 AI Native UI
**日期**: 2026-04-06

---

## 架构概述

本次重构将传统的前端界面完全转变为 AI Native 对话式界面，遵循以下核心原则：

### 1. Chat-first 交互范式

主界面是对话窗口，而非传统的表单 + 按钮布局。用户通过自然语言表达需求，AI 理解并执行。

### 2. Generative UI 动态生成

界面组件由 AI 根据上下文动态生成，而非预先定义的固定模板。

### 3. Agent 可视化

实时显示 AI 智能体的工作状态、置信度和执行进度。

### 4. 主动推送

AI 主动发现机会并推送建议，而非被动等待用户查询。

---

## 技术架构

```
frontend/src/
├── pages/
│   ├── ChatInterface.tsx      # 主对话界面
│   ├── GenerativeUI.tsx       # Generative UI 演示
│   ├── AgentStatus.tsx        # Agent 状态监控
│   ├── OpportunityMatch.tsx   # 机会匹配页面
│   ├── CareerPlan.tsx         # 职业规划页面
│   ├── PerformanceReview.tsx  # 绩效评估页面
│   └── Login.tsx              # 登录页面
├── components/
│   ├── ChatMessage.tsx        # 对话消息组件
│   ├── GenerativeUIRenderer.tsx # UI 渲染器
│   ├── AgentStatusPanel.tsx   # Agent 状态面板
│   ├── SuggestedActions.tsx   # 建议操作组件
│   ├── OpportunityCards.tsx   # 机会卡片
│   ├── CareerTimeline.tsx     # 职业时间线
│   ├── SkillRadar.tsx         # 技能雷达图
│   └── DashboardStats.tsx     # 仪表盘统计
├── routes.tsx                  # 路由配置
└── App.tsx                     # 主应用
```

---

## 核心组件说明

### ChatInterface (主对话界面)

**功能**:
- 自然语言输入
- 消息历史展示
- 快捷操作按钮
- 意图标签快速入口

**状态**:
- `messages`: 对话历史
- `isLoading`: 加载状态
- `agentStatus`: Agent 工作状态 (idle/thinking/executing/completed)

### GenerativeUIRenderer

**功能**:
- 根据 AI 响应动态渲染不同 UI 组件
- 支持的组件类型:
  - `opportunity_cards`: 机会匹配卡片
  - `career_timeline`: 职业发展时间线
  - `skill_radar`: 技能雷达图
  - `dashboard_stats`: 仪表盘统计

### AgentStatusPanel

**功能**:
- 显示 Agent 实时状态
- 工作流进度可视化
- 工具使用统计
- AI 能力标签

---

## API 集成

### 对话 API

```typescript
POST /api/chat/
Request:
{
  "user_id": "string",
  "message": "string",
  "conversation_id": "string (optional)"
}

Response:
{
  "conversation_id": "string",
  "message": {
    "role": "assistant",
    "content": "string",
    "timestamp": "string"
  },
  "suggested_actions": [
    { "action": "string", "label": "string" }
  ],
  "data": { ... }  // 用于 Generative UI 渲染
}
```

### 意图识别

后端支持的意图类型:
- `career_plan`: 职业规划
- `skill_analysis`: 技能分析
- `opportunity_match`: 机会匹配
- `performance_review`: 绩效评估
- `learning_resources`: 学习资源
- `mentor_match`: 导师匹配
- `dashboard`: 仪表盘

---

## 设计规范

### 颜色方案

| 用途 | 颜色 | Hex |
|------|------|-----|
| 主色 | Purple | #722ed1 |
| 辅助色 | Blue | #1890ff |
| 成功 | Green | #52c41a |
| 警告 | Orange | #faad14 |
| 错误 | Red | #ff4d4f |

### 动画效果

- `fadeIn`: 淡入效果 (0.3s)
- `slideUp`: 上滑效果 (0.3s)
- `pulse`: 脉冲效果 (用于加载状态)

### 响应式断点

- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

---

## 使用指南

### 启动开发服务器

```bash
cd frontend
npm install
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 主要路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 重定向到 `/chat` | 默认进入对话界面 |
| `/chat` | ChatInterface | 主对话界面 |
| `/generative-ui` | GenerativeUI | Generative UI 演示 |
| `/agent-status` | AgentStatus | Agent 状态监控 |
| `/opportunities` | OpportunityMatch | 机会匹配 |
| `/career-plan` | CareerPlan | 职业规划 |
| `/performance-review` | PerformanceReview | 绩效评估 |

---

## AI Native 特性检查清单

- [x] 对话式交互 (Chat-first)
- [x] Generative UI 动态生成
- [x] Agent 可视化
- [x] 主动推送建议
- [x] 置信度显示
- [x] 工作流进度可视化
- [x] 意图识别快捷入口
- [x] 上下文感知界面

---

## 后续优化方向

1. **WebSocket 实时更新**: 实现 AI 响应的流式输出
2. **语音交互**: 集成语音识别和合成
3. **多模态输入**: 支持图片、文件上传
4. **个性化主题**: 用户自定义界面风格
5. **离线模式**: 缓存对话历史和常用功能
