/**
 * TrendIndicator - 趋势指示器组件
 */
import React from 'react';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';
import './TrendIndicator.less';

export interface TrendIndicatorProps {
  /** 趋势值 (百分比) */
  value: number;
  /** 趋势类型 (自动或手动指定) */
  type?: 'up' | 'down' | 'neutral' | 'auto';
  /** 是否显示正值符号 */
  showPlus?: boolean;
  /** 是否隐藏图标 */
  hideIcon?: boolean;
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg';
  /** 自定义类名 */
  className?: string;
}

export const TrendIndicator: React.FC<TrendIndicatorProps> = ({
  value,
  type = 'auto',
  showPlus = true,
  hideIcon = false,
  size = 'md',
  className = '',
}) => {
  // 自动判断趋势类型
  const trendType = type === 'auto'
    ? value > 0 ? 'up' : value < 0 ? 'down' : 'neutral'
    : type;

  const trendValue = Math.abs(value);

  const indicatorClasses = `
    trend-indicator
    trend-indicator--${size}
    trend-indicator--${trendType}
    ${className}
  `.trim();

  const renderIcon = () => {
    if (hideIcon) return null;

    if (trendType === 'up') {
      return <ArrowUpOutlined className="trend-indicator__icon" />;
    }
    if (trendType === 'down') {
      return <ArrowDownOutlined className="trend-indicator__icon" />;
    }
    return <MinusOutlined className="trend-indicator__icon" />;
  };

  return (
    <span className={indicatorClasses}>
      {!hideIcon && (
        <span className="trend-indicator__icon-wrapper">
          {renderIcon()}
        </span>
      )}
      <span className="trend-indicator__value">
        {trendType === 'up' && showPlus ? '+' : ''}
        {trendValue.toFixed(1)}%
      </span>
    </span>
  );
};

export default TrendIndicator;
