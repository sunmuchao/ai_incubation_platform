/**
 * 趋势图表组件 - Bento Grid 风格重构
 * 根据趋势数据动态生成可视化图表
 */
import React from 'react';
import { Progress, Space, Typography, Tag } from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  ThunderboltOutlined,
  RiseOutlined,
  FireOutlined,
} from '@ant-design/icons';
import type { MarketTrend } from '../types';

const { Title, Text } = Typography;

interface TrendChartProps {
  trends: MarketTrend[];
  compact?: boolean;
}

/**
 * 趋势方向图标和颜色
 */
const getTrendIndicator = (growthRate: number) => {
  if (growthRate > 0.1) {
    return { icon: <ArrowUpOutlined />, color: 'var(--color-success)', label: '上升' };
  }
  if (growthRate < -0.1) {
    return { icon: <ArrowDownOutlined />, color: 'var(--color-error)', label: '下降' };
  }
  return { icon: <MinusOutlined />, color: 'var(--color-warning)', label: '平稳' };
};

/**
 * 趋势分数颜色
 */
const getTrendScoreColor = (score: number): string => {
  if (score >= 0.8) return 'var(--color-success)';
  if (score >= 0.6) return 'var(--color-info)';
  if (score >= 0.4) return 'var(--color-warning)';
  return 'var(--color-error)';
};

/**
 * 趋势图表组件 - Bento Grid 风格
 */
const TrendChart: React.FC<TrendChartProps> = ({ trends, compact = false }) => {
  if (!trends || trends.length === 0) {
    return (
      <div
        className="bento-card bento-card-sm"
        style={{
          background: 'var(--color-bg-subtle)',
          border: '1px solid var(--color-border-secondary)',
        }}
      >
        <Text style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
          暂无趋势数据
        </Text>
      </div>
    );
  }

  // 紧凑模式 - Bento 列表展示
  if (compact) {
    return (
      <Space direction="vertical" style={{ width: '100%' }} size={12}>
        {trends.map((trend, index) => {
          const indicator = getTrendIndicator(trend.growth_rate);
          const scoreColor = getTrendScoreColor(trend.trend_score);

          return (
            <div
              key={trend.id || index}
              className="bento-card bento-card-sm"
              style={{
                background: 'var(--gradient-bg-card)',
                border: `1px solid ${scoreColor}30`,
                borderLeft: `3px solid ${scoreColor}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <Space style={{ marginBottom: 8 }}>
                    <Tag
                      color={`${scoreColor}20`}
                      style={{
                        border: `1px solid ${scoreColor}`,
                        color: scoreColor,
                        borderRadius: 'var(--radius-md)',
                      }}
                      icon={<RiseOutlined />}
                    >
                      {(trend.trend_score * 100).toFixed(0)}分
                    </Tag>
                    <Text
                      strong
                      style={{
                        color: 'var(--color-text-primary)',
                        fontSize: 'var(--font-size-sm)',
                      }}
                    >
                      {trend.keyword}
                    </Text>
                  </Space>
                  <Space size={12}>
                    <Text
                      style={{
                        color: indicator.color,
                        fontSize: 'var(--font-size-sm)',
                      }}
                    >
                      {indicator.icon} {indicator.label} {Math.abs(trend.growth_rate * 100).toFixed(1)}%
                    </Text>
                  </Space>
                </div>
                <div style={{ width: 100 }}>
                  <Progress
                    percent={trend.trend_score * 100}
                    showInfo={false}
                    strokeColor={scoreColor}
                    trailColor="var(--color-bg-subtle)"
                    strokeWidth={6}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </Space>
    );
  }

  // 完整模式 - Bento 网格展示
  return (
    <div
      className="bento-grid"
      style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}
    >
      {trends.map((trend, index) => {
        const indicator = getTrendIndicator(trend.growth_rate);
        const scoreColor = getTrendScoreColor(trend.trend_score);

        return (
          <div
            key={trend.id || index}
            className="bento-card"
            style={{
              background: 'var(--gradient-bg-card)',
              border: `1px solid ${scoreColor}30`,
              borderLeft: `3px solid ${scoreColor}`,
            }}
          >
            {/* 标题区域 */}
            <div style={{ marginBottom: 16 }}>
              <Space style={{ marginBottom: 8 }} wrap size={4}>
                <Tag
                  color={`${scoreColor}20`}
                  style={{
                    border: `1px solid ${scoreColor}`,
                    color: scoreColor,
                    borderRadius: 'var(--radius-md)',
                    padding: '2px 10px',
                  }}
                  icon={<ThunderboltOutlined />}
                >
                  趋势评分
                </Tag>
                {trend.trend_score >= 0.8 && (
                  <Tag
                    color="rgba(82, 196, 26, 0.15)"
                    style={{
                      border: '1px solid var(--color-success)40',
                      color: 'var(--color-success)',
                      borderRadius: 'var(--radius-md)',
                      padding: '2px 10px',
                    }}
                    icon={<FireOutlined />}
                  >
                    热门
                  </Tag>
                )}
              </Space>
              <Title
                level={5}
                style={{
                  margin: 0,
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--font-size-lg)',
                  fontWeight: 'var(--font-weight-semibold)',
                }}
              >
                {trend.keyword}
              </Title>
            </div>

            {/* 趋势分数进度条 */}
            <div
              style={{
                marginBottom: 16,
                padding: 12,
                background: 'var(--color-bg-subtle)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--color-border-secondary)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <Text
                  style={{
                    color: 'var(--color-text-tertiary)',
                    fontSize: 'var(--font-size-xs)',
                    textTransform: 'uppercase',
                  }}
                >
                  趋势强度
                </Text>
                <Text
                  style={{
                    color: scoreColor,
                    fontWeight: 'var(--font-weight-semibold)',
                    fontSize: 'var(--font-size-sm)',
                  }}
                >
                  {(trend.trend_score * 100).toFixed(0)}%
                </Text>
              </div>
              <Progress
                percent={trend.trend_score * 100}
                showInfo={false}
                strokeColor={scoreColor}
                trailColor="var(--color-bg-container)"
                strokeWidth={8}
              />
            </div>

            {/* 增长率 */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px',
                background: 'var(--color-bg-subtle)',
                borderRadius: 'var(--radius-lg)',
                marginBottom: 12,
                border: '1px solid var(--color-border-secondary)',
              }}
            >
              <Text
                style={{
                  color: 'var(--color-text-tertiary)',
                  fontSize: 'var(--font-size-xs)',
                  textTransform: 'uppercase',
                }}
              >
                增长趋势
              </Text>
              <Space size={8}>
                <span style={{ color: indicator.color, fontSize: 16 }}>
                  {indicator.icon}
                </span>
                <Text
                  strong
                  style={{
                    color: indicator.color,
                    fontSize: 'var(--font-size-base)',
                  }}
                >
                  {Math.abs(trend.growth_rate * 100).toFixed(1)}%
                </Text>
              </Space>
            </div>

            {/* 相关关键词 */}
            {trend.related_keywords && trend.related_keywords.length > 0 && (
              <div>
                <Text
                  style={{
                    color: 'var(--color-text-tertiary)',
                    fontSize: 'var(--font-size-xs)',
                    display: 'block',
                    marginBottom: 8,
                    textTransform: 'uppercase',
                  }}
                >
                  相关关键词
                </Text>
                <Space wrap size={8}>
                  {trend.related_keywords.slice(0, 5).map((keyword, i) => (
                    <Tag
                      key={i}
                      color="rgba(114, 46, 209, 0.15)"
                      style={{
                        border: '1px solid var(--color-primary-500)30',
                        color: 'var(--color-primary-300)',
                        fontSize: 'var(--font-size-xs)',
                        borderRadius: 'var(--radius-md)',
                        padding: '2px 10px',
                      }}
                    >
                      {keyword}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default TrendChart;
