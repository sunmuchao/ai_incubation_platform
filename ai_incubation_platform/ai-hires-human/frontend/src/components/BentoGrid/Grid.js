import { jsx as _jsx } from "react/jsx-runtime";
import { designTokens } from '../../styles/designTokens';
const { spacing, bentoGrid } = designTokens;
/**
 * Bento Grid 网格布局组件
 *
 * 响应式网格系统，支持不同列数和间距配置
 */
export const Grid = ({ children, className = '', columns = 3, gap = 'lg', style, }) => {
    const gapValues = {
        sm: bentoGrid.gap.sm,
        md: bentoGrid.gap.md,
        lg: bentoGrid.gap.lg,
    };
    const gridStyles = {
        display: 'grid',
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gap: gapValues[gap],
        ...style,
    };
    return (_jsx("div", { className: `bento-grid ${className}`, style: gridStyles, children: children }));
};
export default Grid;
