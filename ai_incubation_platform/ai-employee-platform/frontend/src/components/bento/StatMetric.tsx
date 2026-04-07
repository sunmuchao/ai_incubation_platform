/**
 * StatMetric - 统计指标组件
 * 用于 Bento Card 中的指标展示
 */
import React from 'react';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';
import './StatMetric.less';

export interface StatMetricProps {
  /** 指标标签 */
  label: string;
  /** 指标值 */
  value: number | string;
  /** 值前缀 */
  prefix?: string;
  /** 值后缀 */
  suffix?: string;
  /** 趋势值 (百分比) */
  trend?: number;
  /** 趋势类型 */
  trendType?: 'up' | 'down' | 'neutral';
  /** 趋势标签 */
  trendLabel?: string;
  /** 图标 */
  icon?: React.ReactNode;
  /** 是否显示趋势 */
  showTrend?: boolean;
  /** 小数位数 */
  decimalPlaces?: number;
  /** 自定义类名 */
  className?: string;
}

export const StatMetric: React.FC<StatMetricProps> = ({
  label,
  value,
  prefix,
  suffix,
  trend,
  trendType = 'up',
  trendLabel,
  icon,
  showTrend = true,
  decimalPlaces = 0,
  className = '',
}) => {
  // 格式化数值
  const formatValue = (val: number | string): string => {
    if (typeof val === 'number') {
      return val.toLocaleString('zh-CN', {
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces,
      });
    }
    return val;
  };

  const getTrendIcon = () => {
    if (trend === undefined || !showTrend) return null;

    if (trend === 0 || trendType === 'neutral') {
      return <MinusOutlined className="stat-metric__trend-icon stat-metric__trend-icon--neutral" />;
    }

    if (trendType === 'up') {
      return <ArrowUpOutlined className="stat-metric__trend-icon stat-metric__trend-icon--up" />;
    }

    return <ArrowDownOutlined className="stat-metric__trend-icon stat-metric__trend-icon--down" />;
  };

  const formattedValue = formatValue(value);

  return (
    <div className={`stat-metric ${className}`}>
      {/* 指标头部 */}
      <div className="stat-metric__header">
        {icon && <span className="stat-metric__icon">{icon}</span>}
        <span className="stat-metric__label">{label}</span>
      </div>

      {/* 指标值 */}
      <div className="stat-metric__value-container">
        <span className="stat-metric__value">
          {prefix && <span className="stat-metric__prefix">{prefix}</span>}
          {formattedValue}
          {suffix && <span className="stat-metric__suffix">{suffix}</span>}
        </span>
      </div>

      {/* 趋势 */}
      {showTrend && trend !== undefined && (
        <div className="stat-metric__trend">
          {getTrendIcon()}
          <span className={`stat-metric__trend-value stat-metric__trend-value--${trendType}`}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
          {trendLabel && (
            <span className="stat-metric__trend-label">{trendLabel}</span>
          )}
        </div>
      )}
    </div>
  );
};

export default StatMetric;
