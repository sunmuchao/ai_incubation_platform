/**
 * Bento Grid 全局样式
 *
 * 配色方案：Monochromatic (深蓝色系)
 * 设计风格：Minimalism + Visual Polish (Linear.app 风格)
 */
import designTokens, { generateCSSVariables } from './designTokens';
// 生成 CSS 变量
export const cssVariables = generateCSSVariables();
// 全局样式
export const globalStyles = `
  ${cssVariables}

  /* 基础重置 */
  *, *::before, *::after {
    box-sizing: border-box;
  }

  /* 全局字体和颜色 */
  body {
    font-family: ${designTokens.typography.fontFamily.sans};
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    background-color: ${designTokens.semanticColors.background.primary};
    color: ${designTokens.semanticColors.text.primary};
  }

  /* 滚动条样式 - macOS 风格 */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-track {
    background: transparent;
  }

  ::-webkit-scrollbar-thumb {
    background: ${designTokens.colors.slate[300]};
    border-radius: ${designTokens.radii.sm}px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: ${designTokens.colors.slate[400]};
  }

  /* 思考动画 */
  @keyframes thinking-dots {
    0%, 20% { content: '.'; }
    40%, 60% { content: '..'; }
    80%, 100% { content: '...'; }
  }

  .thinking-dots::after {
    animation: thinking-dots 1.5s infinite;
  }

  /* Bento Grid 卡片基础样式 */
  .bento-card {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .bento-card:hover {
    transform: translateY(-2px);
    box-shadow: ${designTokens.shadows.cardHover};
  }

  /* 选中状态 */
  .bento-card.selected {
    border-color: ${designTokens.colors.blue[500]};
    box-shadow: 0 0 0 2px ${designTokens.colors.blue[100]};
  }

  /* 淡入动画 */
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .fade-in {
    animation: fadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* 脉冲动画 - 用于 AI 状态指示 */
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  /* 高亮闪烁动画 */
  @keyframes highlight-flash {
    0%, 100% { background-color: transparent; }
    50% { background-color: rgba(59, 130, 246, 0.1); }
  }

  .highlight-flash {
    animation: highlight-flash 1s ease-out;
  }
`;
export default globalStyles;
