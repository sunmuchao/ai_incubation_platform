# Human-AI Community 设计系统

## 版本 v1.0.0 - Bento Grid + Monochromatic

---

## 设计理念

### 1. Bento Grid 布局
- **模块化网格**：每个功能模块呈矩形卡片，遵循比例美学（1:1, 2:1, 3:2）
- **均匀留白**：模块间保持统一间距，创造视觉节奏感
- **响应式适配**：根据屏幕尺寸自动调整网格列数

### 2. Monochromatic 配色
- **主色调**：深蓝色系（Hue 210°, Saturation 12%）
- **色阶系统**：使用同色系不同明度创建 8 个层级
- **强调色**：蓝色点缀（不超过 10% 面积）

### 3. Linear.app 风格
- **精致阴影**：多层次阴影创造深度感
- **细腻边框**：1px solid rgba(255,255,255,0.12)
- **统一圆角**：8-12px 圆角系统
- **微妙渐变**：线性渐变增加层次感

---

## 设计令牌

### 颜色系统

```css
/* 背景色阶 - 从深到浅 */
--bg-primary: hsl(210, 12%, 8%);    /* 最深背景 */
--bg-secondary: hsl(210, 12%, 11%);
--bg-tertiary: hsl(210, 12%, 14%);
--bg-elevated: hsl(210, 12%, 16%);
--bg-sunken: hsl(210, 12%, 6%);     /* 最暗背景 */

/* 边框色阶 */
--border-subtle: hsla(210, 12%, 40%, 0.08);
--border-default: hsla(210, 12%, 40%, 0.12);
--border-strong: hsla(210, 12%, 40%, 0.2);
--border-hover: hsla(210, 12%, 40%, 0.25);

/* 文字色阶 */
--text-primary: hsl(210, 12%, 92%);
--text-secondary: hsl(210, 12%, 70%);
--text-tertiary: hsl(210, 12%, 50%);
--text-muted: hsl(210, 12%, 35%);

/* 强调色 - 蓝色 */
--accent-primary: hsl(210, 100%, 60%);
--accent-hover: hsl(210, 100%, 65%);
--accent-subtle: hsla(210, 100%, 60%, 0.1);
```

### 阴影系统

```css
--shadow-xs: 0 1px 2px hsla(0, 0%, 0%, 0.04);
--shadow-sm: 0 1px 3px hsla(0, 0%, 0%, 0.06), 0 2px 6px hsla(0, 0%, 0%, 0.04);
--shadow-md: 0 1px 2px hsla(0, 0%, 0%, 0.04), 0 4px 12px hsla(0, 0%, 0%, 0.08);
--shadow-lg: 0 2px 4px hsla(0, 0%, 0%, 0.06), 0 8px 24px hsla(0, 0%, 0%, 0.12);
--shadow-xl: 0 4px 8px hsla(0, 0%, 0%, 0.08), 0 16px 48px hsla(0, 0%, 0%, 0.16);

/* 光晕效果 */
--glow-subtle: 0 0 40px hsla(210, 100%, 60%, 0.1);
--glow-strong: 0 0 80px hsla(210, 100%, 60%, 0.15);
```

### 圆角系统

```css
--radius-sm: 6px;   /* 小按钮、标签 */
--radius-md: 8px;   /* 输入框、小卡片 */
--radius-lg: 10px;  /* 标准卡片 */
--radius-xl: 12px;  /* 大卡片、模态框 */
--radius-2xl: 16px; /* 超大卡片 */
--radius-full: 9999px; /* 圆形头像、徽章 */
```

### 间距系统

```css
--space-1: 0.25rem;  /* 4px */
--space-2: 0.5rem;   /* 8px */
--space-3: 0.75rem;  /* 12px */
--space-4: 1rem;     /* 16px */
--space-5: 1.25rem;  /* 20px */
--space-6: 1.5rem;   /* 24px */
--space-8: 2rem;     /* 32px */
--space-10: 2.5rem;  /* 40px */
--space-12: 3rem;    /* 48px */
--space-16: 4rem;    /* 64px */
```

---

## 组件规范

### Bento 卡片尺寸

| 尺寸类 | 列跨度 | 行跨度 | 用途 |
|--------|--------|--------|------|
| `.bento-sm` | 1 | 1 | 小型信息卡片 |
| `.bento-md` | 2 | 1 | 中等信息卡片 |
| `.bento-lg` | 2 | 2 | 大型重点卡片 |
| `.bento-xl` | 3 | 2 | 超宽卡片 |
| `.bento-full` | 4 | 1 | 通栏卡片 |

### 卡片样式

```css
.bento-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  transition: all 0.25s ease;
}

.bento-card:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### 按钮样式

```css
/* 主按钮 */
.btn-primary {
  background: var(--accent-primary);
  color: #fff;
  box-shadow: var(--shadow-sm);
}

.btn-primary:hover {
  background: var(--accent-hover);
  box-shadow: var(--shadow-md), var(--glow-subtle);
  transform: translateY(-1px);
}

/* 次按钮 */
.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}
```

---

## 动画规范

### 持续时间

```css
--duration-fast: 150ms;    /* 悬停、点击反馈 */
--duration-normal: 250ms;  /* 卡片展开、模态框 */
--duration-slow: 400ms;    /* 页面过渡 */
```

### 缓动函数

```css
--ease-default: cubic-bezier(0.4, 0, 0.2, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
```

### 标准动画

```css
/* 淡入动画 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 滑入动画 */
@keyframes slideInRight {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

/* 骨架屏加载 */
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## 响应式断点

```css
/* 桌面优先 */
@media (max-width: 768px) {
  /* 平板适配 */
  --sidebar-width: 100%;
  .bento-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 480px) {
  /* 手机适配 */
  html { font-size: 14px; }
  .bento-grid { grid-template-columns: 1fr; }
}
```

---

## 使用指南

### 1. 创建 Bento 卡片

```html
<div class="bento-grid">
  <div class="bento-card bento-lg">
    <div class="bento-card-header">
      <span class="bento-card-title">标题</span>
      <div class="bento-card-icon">📊</div>
    </div>
    <!-- 内容 -->
  </div>
  <div class="bento-card bento-sm">
    <!-- 小型卡片内容 -->
  </div>
</div>
```

### 2. 使用设计令牌

```css
.my-component {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  color: var(--text-primary);
}
```

### 3. 添加交互效果

```css
.interactive-card {
  transition: all var(--duration-normal) var(--ease-default);
}

.interactive-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
```

---

## 可访问性

### 焦点样式

```css
:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
```

### 对比度要求

- 主要文本：WCAG AAA (7:1 以上)
- 次要文本：WCAG AA (4.5:1 以上)
- 装饰元素：WCAG AA Large (3:1 以上)

---

## 更新日志

### v1.0.0 (2026-04-06)
- 初始版本
- Bento Grid 布局系统
- Monochromatic 配色方案
- Linear.app 风格视觉优化
- 完整响应式支持
