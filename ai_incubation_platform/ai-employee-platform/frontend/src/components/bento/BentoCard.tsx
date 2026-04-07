/**
 * BentoCard - Bento Grid 核心卡片组件
 * Linear.app 风格设计，精致的阴影和边框处理
 */
import React, { useState, type ReactNode } from 'react';
import './BentoCard.less';

export type BentoCardSize = '1x1' | '2x1' | '1x2' | '2x2' | '3x2' | '4x2' | 'full';

export interface BentoCardProps {
  /** 卡片尺寸 */
  size?: BentoCardSize;
  /** 卡片标题 */
  title?: ReactNode;
  /** 卡片副标题/描述 */
  description?: string;
  /** 卡片右上角操作区 */
  extra?: ReactNode;
  /** 卡片图标 */
  icon?: ReactNode;
  /** 卡片内容 */
  children?: ReactNode;
  /** 是否可点击 */
  clickable?: boolean;
  /** 点击回调 */
  onClick?: () => void;
  /** 是否加载中 */
  loading?: boolean;
  /** 是否选中状态 */
  selected?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 自定义样式 */
  style?: React.CSSProperties;
  /** 强调色标识 */
  accent?: boolean;
  /** 渐变背景 */
  gradient?: boolean;
}

export const BentoCard: React.FC<BentoCardProps> = ({
  size = '2x1',
  title,
  description,
  extra,
  icon,
  children,
  clickable = false,
  onClick,
  loading = false,
  selected = false,
  className = '',
  style,
  accent = false,
  gradient = false,
}) => {
  const [isHovered, setIsHovered] = useState(false);

  const handleClick = () => {
    if (clickable && onClick) {
      onClick();
    }
  };

  const cardClasses = `
    bento-card
    bento-card--${size}
    ${clickable ? 'bento-card--clickable' : ''}
    ${selected ? 'bento-card--selected' : ''}
    ${accent ? 'bento-card--accent' : ''}
    ${gradient ? 'bento-card--gradient' : ''}
    ${loading ? 'bento-card--loading' : ''}
    ${className}
  `.trim();

  return (
    <div
      className={cardClasses}
      style={style}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleClick}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onKeyDown={(e) => {
        if (clickable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      {/* 卡片头部 */}
      {(title || extra || icon) && (
        <div className="bento-card__header">
          <div className="bento-card__header-start">
            {icon && <span className="bento-card__icon">{icon}</span>}
            {title && (
              <div className="bento-card__title-container">
                <h3 className="bento-card__title">{title}</h3>
                {description && (
                  <p className="bento-card__description">{description}</p>
                )}
              </div>
            )}
          </div>
          {extra && <div className="bento-card__extra">{extra}</div>}
        </div>
      )}

      {/* 卡片内容区 */}
      {children && (
        <div className="bento-card__content">
          {loading ? (
            <div className="bento-card__skeleton">
              <div className="bento-card__skeleton-line" />
              <div className="bento-card__skeleton-line short" />
              <div className="bento-card__skeleton-line" />
            </div>
          ) : (
            children
          )}
        </div>
      )}

      {/* 悬停光晕效果 */}
      {clickable && (
        <div
          className={`bento-card__glow ${isHovered ? 'bento-card__glow--visible' : ''}`}
        />
      )}
    </div>
  );
};

export default BentoCard;
