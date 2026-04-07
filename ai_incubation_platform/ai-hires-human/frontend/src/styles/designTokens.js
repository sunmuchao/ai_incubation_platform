/**
 * Bento Grid 设计令牌系统
 *
 * 配色方案：Monochromatic (深蓝色系)
 * 布局原则：模块化网格，矩形卡片，均匀留白
 * 设计风格：Minimalism + Visual Polish (Linear.app 风格)
 */
// ==================== 配色系统 - Monochromatic 深蓝色系 ====================
export const colors = {
    // 主色系 - 深蓝灰色
    slate: {
        50: '#f8fafc',
        100: '#f1f5f9',
        200: '#e2e8f0',
        300: '#cbd5e1',
        400: '#94a3b8',
        500: '#64748b',
        600: '#475569',
        700: '#334155',
        800: '#1e293b',
        900: '#0f172a',
        950: '#020617',
    },
    // 强调色 - 蓝色（用于高亮和交互）
    blue: {
        50: '#eff6ff',
        100: '#dbeafe',
        200: '#bfdbfe',
        300: '#93c5fd',
        400: '#60a5fa',
        500: '#3b82f6',
        600: '#2563eb',
        700: '#1d4ed8',
        800: '#1e40af',
        900: '#1e3a8a',
    },
    // 成功色 - 绿色
    green: {
        50: '#f0fdf4',
        100: '#dcfce7',
        200: '#bbf7d0',
        300: '#86efac',
        400: '#4ade80',
        500: '#22c55e',
        600: '#16a34a',
        700: '#15803d',
        800: '#166534',
        900: '#14532d',
    },
    // 警告色 - 琥珀色
    amber: {
        50: '#fffbeb',
        100: '#fef3c7',
        200: '#fde68a',
        300: '#fcd34d',
        400: '#fbbf24',
        500: '#f59e0b',
        600: '#d97706',
        700: '#b45309',
        800: '#92400e',
        900: '#78350f',
    },
    // 错误色 - 红色
    red: {
        50: '#fef2f2',
        100: '#fee2e2',
        200: '#fecaca',
        300: '#fca5a5',
        400: '#f87171',
        500: '#ef4444',
        600: '#dc2626',
        700: '#b91c1c',
        800: '#991b1b',
        900: '#7f1d1d',
    },
    // 紫色 - AI 专用
    purple: {
        50: '#faf5ff',
        100: '#f3e8ff',
        200: '#e9d5ff',
        300: '#d8b4fe',
        400: '#c084fc',
        500: '#a855f7',
        600: '#9333ea',
        700: '#7e22ce',
        800: '#6b21a8',
        900: '#581c87',
    },
};
// ==================== 语义化颜色 ====================
export const semanticColors = {
    // 背景色
    background: {
        primary: colors.slate[50], // 主背景
        secondary: colors.slate[100], // 次级背景
        elevated: '#ffffff', // 浮层背景
        hover: colors.slate[200], // 悬停背景
        selected: colors.blue[50], // 选中背景
    },
    // 边框色
    border: {
        default: colors.slate[200],
        subtle: 'rgba(0, 0, 0, 0.06)', // Linear.app 风格细边框
        strong: colors.slate[300],
        focus: colors.blue[400],
    },
    // 文本色
    text: {
        primary: colors.slate[900],
        secondary: colors.slate[600],
        tertiary: colors.slate[400],
        disabled: colors.slate[300],
        inverse: '#ffffff',
        link: colors.blue[600],
    },
    // 功能色
    functional: {
        success: colors.green[600],
        successBg: colors.green[50],
        warning: colors.amber[600],
        warningBg: colors.amber[50],
        error: colors.red[600],
        errorBg: colors.red[50],
        info: colors.blue[600],
        infoBg: colors.blue[50],
        ai: colors.purple[600],
        aiBg: colors.purple[50],
    },
};
// ==================== 阴影系统 - Linear.app 风格 ====================
export const shadows = {
    // 无阴影
    none: 'none',
    // 极轻阴影 - 用于卡片
    card: '0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.08)',
    // 轻阴影 - 用于悬浮
    cardHover: '0 1px 3px rgba(0, 0, 0, 0.06), 0 6px 16px rgba(0, 0, 0, 0.1)',
    // 中等阴影 - 用于下拉菜单
    dropdown: '0 4px 12px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.04)',
    // 强阴影 - 用于模态框
    modal: '0 20px 40px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0, 0, 0, 0.04)',
    // 内阴影 - 用于凹陷效果
    inner: 'inset 0 1px 2px rgba(0, 0, 0, 0.04)',
    // 发光效果
    glow: {
        blue: '0 0 20px rgba(59, 130, 246, 0.3)',
        purple: '0 0 20px rgba(168, 85, 247, 0.25)',
        green: '0 0 20px rgba(34, 197, 94, 0.2)',
    },
};
// ==================== 圆角系统 ====================
export const radii = {
    none: 0,
    sm: 4,
    md: 8, // 默认圆角
    lg: 12, // 卡片圆角
    xl: 16,
    xxl: 24,
    full: 9999, // 圆形
};
// ==================== 间距系统 ====================
export const spacing = {
    0: 0,
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    '2xl': 24,
    '3xl': 32,
    '4xl': 40,
    '5xl': 48,
    '6xl': 64,
};
// ==================== 字体系统 ====================
export const typography = {
    fontFamily: {
        sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
        mono: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    },
    fontSize: {
        xs: '11px',
        sm: '12px',
        md: '14px',
        lg: '16px',
        xl: '18px',
        '2xl': '20px',
        '3xl': '24px',
        '4xl': '30px',
    },
    fontWeight: {
        normal: 400,
        medium: 500,
        semibold: 600,
        bold: 700,
    },
    lineHeight: {
        tight: 1.25,
        normal: 1.5,
        relaxed: 1.75,
    },
};
// ==================== 过渡动画 ====================
export const transitions = {
    duration: {
        fast: '150ms',
        normal: '200ms',
        slow: '300ms',
        slower: '500ms',
    },
    timing: {
        ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
        easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
        easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
        easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
};
// ==================== Bento Grid 布局配置 ====================
export const bentoGrid = {
    // 网格列数
    columns: {
        sm: 1,
        md: 2,
        lg: 3,
        xl: 4,
    },
    // 卡片尺寸比例
    cardSizes: {
        small: { width: 1, height: 1 }, // 1:1
        medium: { width: 2, height: 1 }, // 2:1
        large: { width: 2, height: 2 }, // 2:2
        tall: { width: 1, height: 2 }, // 1:2
        wide: { width: 3, height: 1 }, // 3:1
    },
    // 网格间距
    gap: {
        sm: spacing.md,
        md: spacing.lg,
        lg: spacing.xl,
    },
};
// ==================== 渐变色 ====================
export const gradients = {
    // 微妙的背景渐变
    subtle: {
        light: 'linear-gradient(180deg, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0.4) 100%)',
        dark: 'linear-gradient(180deg, rgba(15,23,42,0.1) 0%, rgba(15,23,42,0.02) 100%)',
    },
    // 卡片渐变
    card: {
        light: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.5) 100%)',
    },
    // 强调渐变
    accent: {
        blue: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
        purple: 'linear-gradient(135deg, #a855f7 0%, #9333ea 100%)',
        green: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    },
};
// ==================== 生成 CSS 变量的辅助函数 ====================
export const generateCSSVariables = () => {
    return `
    :root {
      /* Colors - Slate */
      --color-slate-50: ${colors.slate[50]};
      --color-slate-100: ${colors.slate[100]};
      --color-slate-200: ${colors.slate[200]};
      --color-slate-300: ${colors.slate[300]};
      --color-slate-400: ${colors.slate[400]};
      --color-slate-500: ${colors.slate[500]};
      --color-slate-600: ${colors.slate[600]};
      --color-slate-700: ${colors.slate[700]};
      --color-slate-800: ${colors.slate[800]};
      --color-slate-900: ${colors.slate[900]};

      /* Colors - Blue */
      --color-blue-500: ${colors.blue[500]};
      --color-blue-600: ${colors.blue[600]};

      /* Shadows */
      --shadow-card: ${shadows.card};
      --shadow-card-hover: ${shadows.cardHover};
      --shadow-dropdown: ${shadows.dropdown};

      /* Border Radius */
      --radius-md: ${radii.md}px;
      --radius-lg: ${radii.lg}px;

      /* Spacing */
      --spacing-sm: ${spacing.sm}px;
      --spacing-md: ${spacing.md}px;
      --spacing-lg: ${spacing.lg}px;

      /* Transitions */
      --transition-fast: ${transitions.duration.fast} ${transitions.timing.ease};
      --transition-normal: ${transitions.duration.normal} ${transitions.timing.ease};
      --transition-slow: ${transitions.duration.slow} ${transitions.timing.ease};
    }
  `;
};
// 组合导出
export const designTokens = {
    colors,
    semanticColors,
    shadows,
    radii,
    spacing,
    typography,
    transitions: {
        ...transitions,
        all: `all ${transitions.duration.normal} ${transitions.timing.ease}`,
    },
    bentoGrid,
    gradients,
};
export default designTokens;
