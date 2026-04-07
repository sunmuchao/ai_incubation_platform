import React from 'react';
import { designTokens } from '../../styles/designTokens';

const { colors, semanticColors, shadows, radii, spacing, transitions, typography, gradients } = designTokens;

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hoverable?: boolean;
  selected?: boolean;
  variant?: 'default' | 'elevated' | 'outlined' | 'filled';
  size?: 'small' | 'medium' | 'large';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  title?: React.ReactNode;
  extra?: React.ReactNode;
  style?: React.CSSProperties;
}

/**
 * Bento Grid 卡片组件
 *
 * 设计原则：
 * - Linear.app 风格精致阴影
 * - 1px 细边框增加层次感
 * - 统一 12px 圆角
 * - 微妙的渐变背景
 * - 流畅的 hover 动画
 */
export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  onClick,
  hoverable = false,
  selected = false,
  variant = 'default',
  size = 'medium',
  padding = 'md',
  title,
  extra,
  style,
}) => {
  const baseStyles: React.CSSProperties = {
    backgroundColor: selected ? semanticColors.background.selected : '#ffffff',
    borderRadius: radii.lg,
    transition: transitions.all,
    position: 'relative',
    overflow: 'hidden',
  };

  // 变体样式
  const variantStyles: Record<string, React.CSSProperties> = {
    default: {
      backgroundColor: '#ffffff',
      boxShadow: shadows.card,
      border: `1px solid ${semanticColors.border.subtle}`,
    },
    elevated: {
      backgroundColor: '#ffffff',
      boxShadow: shadows.dropdown,
      border: `1px solid ${semanticColors.border.default}`,
    },
    outlined: {
      backgroundColor: 'transparent',
      boxShadow: 'none',
      border: `1px solid ${semanticColors.border.default}`,
    },
    filled: {
      backgroundColor: semanticColors.background.secondary,
      boxShadow: 'none',
      border: `1px solid ${semanticColors.border.default}`,
    },
  };

  // Hover 样式 - 通过 CSS 类实现，不使用内联样式
  const hoverClasses = hoverable ? 'bento-card-hoverable' : '';
  const cursorStyle: React.CSSProperties = {
    cursor: onClick ? 'pointer' : 'default',
  };

  // 尺寸样式
  const sizeStyles: Record<string, React.CSSProperties> = {
    small: { minWidth: '200px' },
    medium: { minWidth: '280px' },
    large: { minWidth: '360px' },
  };

  // 内边距
  const paddingStyles: Record<string, React.CSSProperties> = {
    none: { padding: 0 },
    sm: { padding: spacing.md },
    md: { padding: spacing.lg },
    lg: { padding: spacing.xl },
  };

  const mergedStyles: React.CSSProperties = {
    ...baseStyles,
    ...variantStyles[variant],
    ...cursorStyle,
    ...sizeStyles[size],
    ...paddingStyles[padding],
    ...style,
  };

  return (
    <div
      className={`bento-card ${hoverClasses} ${className}`}
      style={mergedStyles}
      onClick={onClick}
    >
      {/* 标题栏 */}
      {(title || extra) && (
        <div style={styles.header}>
          {title && <div style={styles.title}>{title}</div>}
          {extra && <div style={styles.extra}>{extra}</div>}
        </div>
      )}
      {/* 内容区 */}
      <div style={title ? styles.content : {} }>
        {children}
      </div>
      {/* 微妙的渐变叠加层增加层次感 */}
      <div style={styles.gradientOverlay} />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.lg,
    paddingBottom: spacing.lg,
    borderBottom: `1px solid ${semanticColors.border.subtle}`,
  },
  title: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.semibold,
    color: semanticColors.text.primary,
  },
  extra: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
  },
  content: {
    position: 'relative',
    zIndex: 1,
  },
  gradientOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: gradients.card.light,
    pointerEvents: 'none',
    zIndex: 0,
  },
};

export default Card;
