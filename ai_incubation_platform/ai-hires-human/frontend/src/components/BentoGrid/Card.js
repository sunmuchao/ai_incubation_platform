import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { designTokens } from '../../styles/designTokens';
const { colors, semanticColors, shadows, radii, spacing, transitions, typography, gradients } = designTokens;
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
export const Card = ({ children, className = '', onClick, hoverable = false, selected = false, variant = 'default', size = 'medium', padding = 'md', title, extra, style, }) => {
    const baseStyles = {
        backgroundColor: selected ? semanticColors.background.selected : '#ffffff',
        borderRadius: radii.lg,
        transition: transitions.all,
        position: 'relative',
        overflow: 'hidden',
    };
    // 变体样式
    const variantStyles = {
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
    const cursorStyle = {
        cursor: onClick ? 'pointer' : 'default',
    };
    // 尺寸样式
    const sizeStyles = {
        small: { minWidth: '200px' },
        medium: { minWidth: '280px' },
        large: { minWidth: '360px' },
    };
    // 内边距
    const paddingStyles = {
        none: { padding: 0 },
        sm: { padding: spacing.md },
        md: { padding: spacing.lg },
        lg: { padding: spacing.xl },
    };
    const mergedStyles = {
        ...baseStyles,
        ...variantStyles[variant],
        ...cursorStyle,
        ...sizeStyles[size],
        ...paddingStyles[padding],
        ...style,
    };
    return (_jsxs("div", { className: `bento-card ${hoverClasses} ${className}`, style: mergedStyles, onClick: onClick, children: [(title || extra) && (_jsxs("div", { style: styles.header, children: [title && _jsx("div", { style: styles.title, children: title }), extra && _jsx("div", { style: styles.extra, children: extra })] })), _jsx("div", { style: title ? styles.content : {}, children: children }), _jsx("div", { style: styles.gradientOverlay })] }));
};
const styles = {
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
