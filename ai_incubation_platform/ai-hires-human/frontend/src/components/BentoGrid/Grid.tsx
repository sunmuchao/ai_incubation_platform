import React from 'react';
import { designTokens } from '../../styles/designTokens';

const { spacing, bentoGrid } = designTokens;

export interface GridProps {
  children: React.ReactNode;
  className?: string;
  columns?: 1 | 2 | 3 | 4 | 5 | 6;
  gap?: 'sm' | 'md' | 'lg';
  style?: React.CSSProperties;
}

/**
 * Bento Grid 网格布局组件
 *
 * 响应式网格系统，支持不同列数和间距配置
 */
export const Grid: React.FC<GridProps> = ({
  children,
  className = '',
  columns = 3,
  gap = 'lg',
  style,
}) => {
  const gapValues = {
    sm: bentoGrid.gap.sm,
    md: bentoGrid.gap.md,
    lg: bentoGrid.gap.lg,
  };

  const gridStyles: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: `repeat(${columns}, 1fr)`,
    gap: gapValues[gap],
    ...style,
  };

  return (
    <div className={`bento-grid ${className}`} style={gridStyles}>
      {children}
    </div>
  );
};

export default Grid;
