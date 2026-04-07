# Bento Grid & Monochromatic 重构报告

## 重构概述

本次重构将 ai-runtime-optimizer 前端界面全面升级为 **Bento Grid 布局** 和 **Monochromatic 配色方案**，采用 **Linear.app 风格** 的精致设计。

## 设计原则

### 1. Bento Grid 布局
- 模块化网格布局，每个功能模块呈矩形卡片
- 卡片尺寸遵循响应式设计，使用 `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`
- 模块间留白均匀（24px gap），保持视觉节奏感

### 2. Monochromatic 配色方案
- **主色调**: 深蓝灰色系 (#102a43 → #f0f4f8)
- **中性色**: 灰度色系 (#030712 → #ffffff)
- **功能色**:
  - Success: #10b981
  - Warning: #f59e0b
  - Error: #ef4444
  - Info: #3b82f6
  - Accent: #8b5cf6

### 3. Linear.app 风格设计
- **精致阴影**:
  - `card: 0 1px 2px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.08)`
  - `cardHover: 0 2px 4px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.12)`
- **边框处理**: 1px solid `rgba(255,255,255,0.08)`
- **圆角**: 6px-16px 统一圆角系统
- **渐变**: 微妙的线性渐变增加层次感

## 重构文件清单

### 核心文件
| 文件路径 | 重构内容 |
|---------|---------|
| `src/styles/design-tokens.ts` | 新建 - 设计令牌系统（颜色、阴影、圆角、间距、字体、过渡） |
| `src/styles/index.less` | 重构 - 全局样式、CSS 变量、动画、Ant Design 覆盖 |
| `vite.config.ts` | 更新 - Tailwind/Ant Design 主题配置 |

### 组件文件
| 文件路径 | 重构内容 |
|---------|---------|
| `src/App.tsx` | 更新 - 集成设计令牌到 ConfigProvider |
| `src/components/MainLayout.tsx` | 重构 - Bento 风格侧边栏和顶部导航 |
| `src/components/GenerativeDashboard.tsx` | 重构 - Bento Grid 仪表板布局 |
| `src/components/AgentVisualization.tsx` | 重构 - Agent 状态卡片可视化 |
| `src/components/ChatInterface.tsx` | 重构 - 对话式聊天界面 |
| `src/pages/DiagnosisPage.tsx` | 重构 - AI 诊断页面 |
| `src/pages/SettingsPage.tsx` | 重构 - 设置页面 |

## 核心设计令牌

### 颜色系统
```typescript
colors = {
  primary: { 50-900 },     // 深蓝灰主色系
  neutral: { 0-950 },      // 中性灰度系
  dark: { bg, bgElevated, bgCard, bgCardHover, border, borderHover },
  semantic: { success, warning, error, info, accent }
}
```

### 阴影系统
```typescript
shadows = {
  card: '0 1px 2px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.08)',
  cardHover: '0 2px 4px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.12)',
  elevated: '0 4px 8px rgba(0,0,0,0.08), 0 16px 48px rgba(0,0,0,0.16)',
  glow: '0 0 20px rgba(99,102,241,0.3)'
}
```

### 圆角系统
```typescript
radii = {
  sm: '6px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px'
}
```

### 间距系统
```typescript
spacing = {
  0: '0', 1: '4px', 2: '8px', 3: '12px', 4: '16px',
  5: '20px', 6: '24px', 8: '32px', 12: '48px', ...
}
```

## 交互特性

### Hover 效果
- 卡片悬浮时提升阴影并改变边框颜色
- 按钮悬浮时上移 2px 并添加光晕效果
- 过渡时间 200ms，使用 `cubic-bezier(0.4, 0, 0.2, 1)` 缓动

### 动画系统
```less
@keyframes fadeIn { opacity: 0 → 1, translateY(10px) → 0 }
@keyframes slideUp { opacity: 0 → 1, translateY(20px) → 0 }
@keyframes pulse { opacity: 1 → 0.5, scale: 1 → 0.98 }
@keyframes glow { box-shadow: 20px → 40px }
@keyframes spin { rotate: 0deg → 360deg }
```

## 响应式设计

- 使用 `auto-fit` 和 `minmax()` 实现自适应网格布局
- 移动端抽屉式导航
- 统一的最小卡片尺寸：280px

## 技术栈

- React + TypeScript
- Ant Design (主题定制)
- Less (CSS 预处理器)
- Vite (构建工具)

## 视觉效果对比

### 重构前
- 简单的暗色主题
- 标准 Ant Design 组件样式
- 固定布局结构

### 重构后
- Bento Grid 模块化布局
- Monochromatic 精致配色
- Linear.app 风格阴影和渐变
- 流畅的 Hover 和过渡动画
- 统一的视觉语言

## 后续建议

1. **性能优化**: 考虑添加 React.memo 优化不必要的重渲染
2. **暗色/浅色模式切换**: 扩展设计令牌支持多主题
3. **可访问性**: 添加键盘导航和 ARIA 标签
4. **移动端优化**: 进一步优化小屏幕体验
