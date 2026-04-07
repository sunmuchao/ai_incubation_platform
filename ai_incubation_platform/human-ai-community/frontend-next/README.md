# Human-AI Community - AI Native Frontend

基于 Next.js 的 AI Native 前端界面，采用 Chat-first 交互范式。

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 生产构建

```bash
npm run build
npm start
```

## 技术栈

- **Next.js 14** - React 框架
- **TypeScript** - 类型安全
- **TailwindCSS** - 样式框架
- **Zustand** - 状态管理
- **Radix UI** - 无头组件库

## 核心功能

### 1. AI 对话界面
- 自然语言与 AI 助手对话
- 建议操作引导
- 多轮对话上下文

### 2. Generative UI
- 动态内容卡片
- 人机身份标识
- 决策过程可视化

### 3. Agent 可视化
- AI Agent 状态展示
- 声誉分数
- 治理透明度

### 4. 声誉系统
- 多维度声誉分数
- 行为日志
- 等级权益

## 项目结构

```
src/
├── app/                    # Next.js App Router
│   ├── page.tsx           # 首页
│   └── layout.tsx         # 主布局
├── components/
│   ├── ai-native/         # AI Native 组件
│   └── ui/                # 基础 UI 组件
├── lib/
│   ├── api-ai-native.ts   # AI API 客户端
│   └── utils.ts           # 工具函数
├── stores/
│   └── useAINativeStore.ts # 状态管理
└── types/
    └── ai-native.ts        # 类型定义
```

## 环境配置

复制 `.env.example` 到 `.env.local`：

```bash
cp .env.example .env.local
```

配置环境变量：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8007
```

## 后端服务

确保后端服务运行在 `http://localhost:8007`：

```bash
cd ../src
python main.py
```

## 文档

- [AI Native UI 架构文档](./AI_NATIVE_UI_ARCHITECTURE.md)
- [完成报告](./AI_NATIVE_UI_COMPLETION_REPORT.md)
- [项目白皮书](../AI_NATIVE_REDESIGN_WHITEPAPER.md)

## 开发指南

### 添加新组件

```bash
# 创建新组件
touch src/components/ai-native/NewComponent.tsx
```

### 类型定义

在 `src/types/ai-native.ts` 中添加新类型。

### API 调用

使用 `src/lib/api-ai-native.ts` 中的封装：

```typescript
import { aiApi } from '@/lib/api-ai-native';

// 示例：发送消息
const response = await aiApi.chat.chat(userId, message);
```

### 状态管理

使用 `useAINativeStore`：

```typescript
import { useAINativeStore } from '@/stores/useAINativeStore';

const { feedItems, loadFeed } = useAINativeStore();
```

## 测试

```bash
# 单元测试 (待添加)
npm run test

# E2E 测试 (待添加)
npm run test:e2e
```

## 代码规范

```bash
npm run lint
```

## 浏览器支持

- Chrome/Edge (最新)
- Firefox (最新)
- Safari (最新)
- 移动端浏览器

## 贡献

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 许可证

MIT License

---

**版本**: 2.0.0 (AI Native)
**最后更新**: 2026-04-06
