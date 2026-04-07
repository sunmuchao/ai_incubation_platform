/**
 * BentoGrid - Bento Grid 布局容器组件
 * 响应式网格布局，自动适配不同屏幕尺寸
 */
import React, { type ReactNode } from 'react';
import './BentoGrid.less';

export interface BentoGridProps {
  /** 网格内容 */
  children?: ReactNode;
  /** 最大列数 (默认 4) */
  maxColumns?: number;
  /** 卡片间距 */
  gap?: 'sm' | 'md' | 'lg';
  /** 是否居中 */
  centered?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 自定义样式 */
  style?: React.CSSProperties;
  /** 页面标题 */
  title?: string;
  /** 页面描述 */
  description?: string;
  /** 页面操作区 */
  extra?: ReactNode;
}

export const BentoGrid: React.FC<BentoGridProps> = ({
  children,
  maxColumns = 4,
  gap = 'md',
  centered = false,
  className = '',
  style,
  title,
  description,
  extra,
}) => {
  const gridClasses = `
    bento-grid
    bento-grid--gap-${gap}
    bento-grid--cols-${maxColumns}
    ${centered ? 'bento-grid--centered' : ''}
    ${className}
  `.trim();

  return (
    <div className="bento-grid-wrapper">
      {/* 页面头部 */}
      {(title || description || extra) && (
        <div className="bento-grid__header">
          <div className="bento-grid__header-content">
            {title && <h1 className="bento-grid__title">{title}</h1>}
            {description && (
              <p className="bento-grid__description">{description}</p>
            )}
          </div>
          {extra && <div className="bento-grid__header-extra">{extra}</div>}
        </div>
      )}

      {/* 网格容器 */}
      <div className={gridClasses} style={style}>
        {children}
      </div>
    </div>
  );
};

export default BentoGrid;
