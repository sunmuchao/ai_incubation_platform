/**
 * 统计卡片组件
 */
import React from 'react';
import { Card, Statistic, Progress, Tooltip } from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import type { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: number | string;
  suffix?: string;
  prefix?: ReactNode;
  trend?: number;
  trendType?: 'up' | 'down';
  progress?: number;
  progressColor?: string;
  tooltip?: string;
  loading?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  suffix,
  prefix,
  trend,
  trendType = 'up',
  progress,
  progressColor,
  tooltip,
  loading = false,
}) => {
  const titleContent = tooltip ? (
    <Tooltip title={tooltip}>
      {title}
    </Tooltip>
  ) : (
    title
  );

  return (
    <Card loading={loading} bordered={false}>
      <Statistic
        title={<span style={{ color: '#666' }}>{titleContent}</span>}
        value={value}
        suffix={suffix}
        prefix={
          <>
            {prefix}
            {trend !== undefined && (
              <span style={{ fontSize: 12, marginLeft: 8 }}>
                {trendType === 'up' ? (
                  <ArrowUpOutlined style={{ color: '#cf1322' }} />
                ) : (
                  <ArrowDownOutlined style={{ color: '#3f8600' }} />
                )}
                <span style={{ color: trendType === 'up' ? '#cf1322' : '#3f8600', marginLeft: 4 }}>
                  {trend}%
                </span>
              </span>
            )}
          </>
        }
      />
      {progress !== undefined && (
        <Progress
          percent={progress}
          strokeColor={progressColor}
          showInfo={false}
          size="small"
          style={{ marginTop: 8 }}
        />
      )}
    </Card>
  );
};

export default StatCard;
