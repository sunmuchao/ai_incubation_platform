# Bento Grid 设计系统

## 概述

本项目采用了 **Bento Grid** 布局系统和 **Monochromatic** 配色方案，的设计风格。设计灵感来源于 Linear.app 的精致设计语言。

## 设计原则

### 1. Bento Grid 布局
- **模块化**: 每个功能模块呈矩形卡片
- **比例美学**: 卡片尺寸遵循 1:1, 2:1, 3:2 等比例
- **均匀留白**: 模块间保持一致的间距

### 2. Monochromatic 配色
- **主色调**: 深蓝/灰色系 (#1a1f2c)
- **层次变化**: 使用同色系不同明度/饱和度
- **强调色**: 紫色 (#7c3aed) 点缀，不超过 10% 面积

### 3. Linear.app 风格
- **精致阴影**: 微妙的多层阴影增加深度感
- **细腻边框**: 1px solid rgba(0,0,0,0.06)
- **统一圆角**: 8-12px 圆角处理
- **微妙渐变**: 轻度渐变增加层次感

## 核心组件

### BentoGrid - 网格容器

```tsx
import { BentoGrid } from '@/components/bento';

<BentoGrid
  title="工作台"
  description="欢迎使用 AI 员工管理平台"
  maxColumns={4}
  gap="md"
>
  {/* BentoCard 子组件 */}
</BentoGrid>
```

**Props:**
| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| maxColumns | number | 4 | 最大列数 |
| gap | 'sm' \| 'md' \| 'lg' | 'md' | 卡片间距 |
| title | string | - | 页面标题 |
| description | string | - | 页面描述 |
| centered | boolean | false | 是否居中 |

### BentoCard - 卡片组件

```tsx
import { BentoCard } from '@/components/bento';

<BentoCard
  size="2x1"
  title="统计卡片"
  icon={<Icon />}
  clickable
  onClick={() => console.log('clicked')}
>
  卡片内容
</BentoCard>
```

**尺寸规格:**
| 尺寸 | 占用网格 | 最小高度 |
|------|----------|----------|
| 1x1 | 1 列 × 1 行 | 160px |
| 2x1 | 2 列 × 1 行 | 160px |
| 2x2 | 2 列 × 2 行 | 320px |
| 3x2 | 3 列 × 2 行 | 320px |
| 4x2 | 4 列 × 2 行 | 320px |
| full | 全宽 | 自动 |

**Props:**
| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| size | BentoCardSize | '2x1' | 卡片尺寸 |
| title | ReactNode | - | 标题 |
| description | string | - | 副标题 |
| icon | ReactNode | - | 图标 |
| extra | ReactNode | - | 右上角操作区 |
| clickable | boolean | false | 是否可点击 |
| accent | boolean | false | 强调色边框 |
| gradient | boolean | false | 渐变背景 |

### StatMetric - 统计指标

```tsx
import { StatMetric } from '@/components/bento';

<StatMetric
  label="总收入"
  value={45600}
  prefix="¥"
  trend={18}
  trendType="up"
  icon={<DollarOutlined />}
/>
```

**Props:**
| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| label | string | - | 指标名称 |
| value | number \| string | - | 数值 |
| prefix | string | - | 前缀符号 |
| suffix | string | - | 后缀单位 |
| trend | number | - | 趋势百分比 |
| trendType | 'up' \| 'down' \| 'neutral' | 'up' | 趋势方向 |
| icon | ReactNode | - | 图标 |

### TrendIndicator - 趋势指示器

```tsx
import { TrendIndicator } from '@/components/bento';

<TrendIndicator
  value={18.5}
  size="md"
  showPlus
/>
```

### MiniChart - 迷你图表

```tsx
import { MiniChart } from '@/components/bento';

<MiniChart
  type="area"
  data={[120, 150, 180, 220, 280, 456]}
  color="#7c3aed"
  height={180}
  gradient
  smooth
/>
```

**类型:** `'line' | 'area' | 'bar' | 'progress'`

## 设计令牌

### 颜色系统

```less
// 主色调 - 深蓝灰色系
--color-primary-base: #1a1f2c;
--color-primary-light: #2d3548;
--color-primary-lighter: #3f485e;

// 中性色
--color-neutral-0: #ffffff;
--color-neutral-50: #f7f8fa;
--color-neutral-100: #f0f2f5;
// ... 200-950

// 强调色 - 紫色
--color-accent: #7c3aed;
--color-accent-light: #8b5cf6;
--color-accent-dark: #6d28d9;

// 功能色
--color-success: #00c853;
--color-warning: #ffb300;
--color-error: #ff5252;
--color-info: #2979ff;
```

### 阴影系统

```less
--shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.02);
--shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
--shadow-md: 0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.08);
--shadow-lg: 0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.08);
--shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.08), 0 8px 24px rgba(0, 0, 0, 0.06);
```

### 圆角系统

```less
--border-radius-xs: 4px;
--border-radius-sm: 6px;
--border-radius-md: 8px;
--border-radius-lg: 10px;
--border-radius-xl: 12px;
--border-radius-2xl: 16px;
--border-radius-full: 9999px;
```

### 间距系统

```less
--spacing-0: 0;
--spacing-1: 4px;
--spacing-2: 8px;
--spacing-3: 12px;
--spacing-4: 16px;
--spacing-5: 20px;
--spacing-6: 24px;
--spacing-8: 32px;
--spacing-10: 40px;
--spacing-12: 48px;
```

## 响应式断点

```less
@breakpoint-xs: 480px;   // 手机横屏
@breakpoint-sm: 640px;   // 小屏设备
@breakpoint-md: 768px;   // 平板竖屏
@breakpoint-lg: 1024px;  // 平板横屏
@breakpoint-xl: 1280px;  // 标准桌面
@breakpoint-2xl: 1536px; // 大屏桌面
```

## 使用示例

### Dashboard 页面布局

```tsx
<BentoGrid title="工作台" maxColumns={4}>
  {/* 统计卡片区 */}
  <BentoCard size="1x1">
    <StatMetric label="员工总数" value={24} trend={12} />
  </BentoCard>
  <BentoCard size="1x1">
    <StatMetric label="可雇佣" value={18} trend={8} />
  </BentoCard>
  <BentoCard size="1x1">
    <StatMetric label="工作时长" value={1280} suffix="小时" />
  </BentoCard>
  <BentoCard size="1x1">
    <StatMetric label="收入" value={45600} prefix="¥" />
  </BentoCard>

  {/* 图表区 */}
  <BentoCard size="2x2" title="员工分布">
    {/* 图表内容 */}
  </BentoCard>
  <BentoCard size="2x2" title="收入趋势">
    <MiniChart type="area" data={[...]} />
  </BentoCard>

  {/* 列表区 */}
  <BentoCard size="3x2" title="热门员工">
    {/* 员工列表 */}
  </BentoCard>
  <BentoCard size="1x2" title="任务完成率">
    {/* 任务进度 */}
  </BentoCard>
</BentoGrid>
```

## 暗色模式

系统支持暗色模式，通过 `data-theme` 属性控制：

```tsx
// 切换暗色模式
document.documentElement.setAttribute('data-theme', 'dark');

// 切换亮色模式
document.documentElement.setAttribute('data-theme', 'light');
```

## 最佳实践

1. **卡片尺寸选择**: 根据内容复杂度选择合适的卡片尺寸
2. **视觉层次**: 使用阴影和边框创造深度层次
3. **颜色使用**: 强调色用于重要操作和状态，不超过 10%
4. **留白**: 保持一致的间距，避免内容过于拥挤
5. **响应式**: 确保在所有屏幕尺寸下都有良好的显示效果

## 文件结构

```
frontend/src/
├── styles/
│   ├── design-tokens.less    # 设计令牌 (Less 变量)
│   └── variables.css         # CSS 自定义属性
├── components/
│   └── bento/
│       ├── BentoCard.tsx     # 卡片组件
│       ├── BentoCard.less
│       ├── BentoGrid.tsx     # 网格容器
│       ├── BentoGrid.less
│       ├── StatMetric.tsx    # 统计指标
│       ├── StatMetric.less
│       ├── TrendIndicator.tsx # 趋势指示器
│       ├── TrendIndicator.less
│       ├── MiniChart.tsx     # 迷你图表
│       ├── MiniChart.less
│       └── index.ts          # 导出
└── pages/
    ├── Dashboard.tsx         # Dashboard 示例
    ├── Dashboard.less
    ├── Marketplace.tsx       # Marketplace 示例
    └── Marketplace.less
```

## 更新日志

- **2024-04-06**: 初始版本，完成核心组件和 Dashboard、Marketplace 页面重构
