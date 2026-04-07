# AI Native UI 设计文档

## 项目概述

**ai-traffic-booster** 前端已完成 AI Native 转型，从传统的表单 + 按钮界面转变为对话式、生成式的 AI Native 界面。

## 架构设计

### 技术栈
- **框架**: Vue 3 + TypeScript
- **UI 库**: Element Plus
- **图表**: ECharts 5.x
- **状态管理**: Pinia
- **构建工具**: Vite 5.x

### 目录结构
```
frontend-vue/
├── src/
│   ├── api/
│   │   └── chat.ts              # AI 对话 API 接口
│   ├── components/
│   │   └── generative/          # Generative UI 组件
│   │       ├── GenerativeChart.vue
│   │       ├── MetricCard.vue
│   │       ├── DataTable.vue
│   │       ├── WorkflowProgress.vue
│   │       ├── InsightCard.vue
│   │       └── index.ts
│   ├── layouts/
│   │   └── MainLayout.vue       # 主布局 (AI Native 风格)
│   ├── router/
│   │   └── index.ts             # 路由配置
│   ├── views/
│   │   ├── AIChatHome.vue       # AI 对话首页 (主要入口)
│   │   └── AgentsOverview.vue   # Agent 中心
│   └── utils/
│       └── http.ts              # HTTP 客户端
```

## AI Native 特性实现

### 1. 对话式交互 (Chat-first)

**位置**: `src/views/AIChatHome.vue`

- 用户通过自然语言与 AI 助手交流
- AI 理解意图后自主执行任务
- 支持多轮对话调整策略

**示例对话**:
- "帮我分析上周流量为什么下跌"
- "发现增长机会"
- "执行 SEO 优化策略"

### 2. Generative UI (动态生成界面)

**组件位置**: `src/components/generative/`

根据 AI 响应动态生成可视化组件：

| 组件 | 用途 | 触发条件 |
|------|------|----------|
| GenerativeChart | 数据图表 | AI 响应包含 chart 数据 |
| MetricCard | 指标卡片 | AI 响应包含 metrics 数据 |
| DataTable | 数据表格 | AI 响应包含 table 数据 |
| WorkflowProgress | 工作流进度 | AI 执行工作流时 |
| InsightCard | 洞察卡片 | AI 推送洞察时 |

### 3. Agent 可视化

**位置**: `src/views/AgentsOverview.vue`

展示各 Agent 工作状态：
- SEO Agent
- 内容 Agent
- A/B 测试 Agent
- 分析 Agent
- 竞品 Agent
- 优化 Agent

### 4. 主动推送

**API**: `/chat/insights`

AI 主动发现并推送：
- 异常检测 (anomaly)
- 增长机会 (opportunity)
- 效果报告 (report)

## API 接口

### Chat API

```typescript
// 发送消息
POST /chat/message
{
  message: string,
  session_id?: string,
  user_id?: string
}

// 获取洞察
GET /chat/insights?session_id=xxx&limit=10

// 获取 AI 状态
GET /chat/status
```

### Workflow API

```typescript
// 运行诊断工作流
POST /chat/workflows/diagnosis

// 运行机会发现工作流
POST /chat/workflows/opportunities

// 创建策略工作流
POST /chat/workflows/strategy/create
```

## 路由配置

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | AIChatHome | AI 对话首页 (默认) |
| `/dashboard` | Dashboard | 传统仪表板 |
| `/agents` | AgentsOverview | Agent 中心 |
| `/traffic` | TrafficAnalysis | 流量分析 |
| `/seo` | SEOAnalysis | SEO 分析 |
| `/competitor` | CompetitorAnalysis | 竞品分析 |
| `/automation` | Automation | 自动化中心 |
| `/alerts` | Alerts | 告警管理 |
| `/reports` | Reports | 报告中心 |

## 设计规范

### 颜色方案

```scss
// 渐变色
--gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
--gradient-2: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
--gradient-3: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
--gradient-4: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);

// 状态色
--success: #67c23a;
--warning: #e6a23c;
--danger: #f56c6c;
--info: #409EFF;
```

### 动画效果

- **pulse-ring**: AI 头像脉冲效果
- **thinking-bounce**: 思考中动画
- **working-pulse**: Agent 工作中动画
- **spin**: 加载旋转动画

## 开发指南

### 添加新的 Generative UI 组件

1. 在 `src/components/generative/` 创建新组件
2. 在 `index.ts` 中导出
3. 在 `AIChatHome.vue` 的 `getUiComponent` 方法中注册

### 扩展 AI 能力

1. 在后端 `src/api/chat.py` 添加新的工作流
2. 在前端 `src/api/chat.ts` 添加对应的 API 方法
3. 在 `AIChatHome.vue` 中添加调用逻辑

## 构建和部署

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build

# 预览构建结果
npm run preview
```

## 与后端集成

后端启动后，前端通过 Vite 代理访问 API:

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## 性能优化

1. **组件懒加载**: 路由使用动态导入
2. **图表按需初始化**: 只在需要时渲染图表
3. **虚拟滚动**: 大数据列表使用虚拟滚动
4. **防抖节流**: 搜索和滚动事件使用防抖

## 后续优化方向

1. **WebSocket 实时推送**: 实现 AI 洞察的实时推送
2. **语音交互**: 添加语音输入支持
3. **离线模式**: Service Worker 缓存
4. **PWA 支持**: 安装为桌面应用

## 变更日志

### v4.0.0 (AI Native)
- [新增] AIChatHome 作为默认首页
- [新增] Generative UI 组件系统
- [新增] AgentsOverview Agent 中心
- [移除] 传统 Dashboard 作为默认页
- [重构] MainLayout 采用 AI Native 设计

### v3.0.0
- [新增] AI 助手对话框
- [新增] 查询历史记录
- [新增] 查询模板

### v2.0.0
- [新增] 数据可视化仪表板
- [新增] 流量分析模块
