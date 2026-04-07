/**
 * Generative UI Dashboard - AI 动态仪表板
 * Bento Grid & Monochromatic 设计风格
 */

import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Progress, Table, Tag, Alert, Badge } from 'antd';
import {
  BellOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  SecurityScanOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import type { AIDashboardResponse, ServiceHealth, Alert as AlertType } from '@/types';
import { useDashboardStore } from '@/store';
import { aiNativeApi, observabilityApi, getHealthColor } from '@/services/api';
import { colors, shadows, radii, spacing, typography, transitions, bentoGrid } from '@/styles/design-tokens';

/**
 * Bento Grid 卡片容器
 */
interface BentoCardProps {
  title?: React.ReactNode;
  children: React.ReactNode;
  size?: 'small' | 'medium' | 'large' | 'full';
  className?: string;
  noPadding?: boolean;
}

const BentoCard: React.FC<BentoCardProps> = ({
  title,
  children,
  size = 'medium',
  noPadding = false,
}) => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className="bento-card"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: colors.dark.bgCard,
        borderRadius: radii.lg,
        border: `1px solid ${colors.dark.border}`,
        boxShadow: isHovered ? shadows.cardHover : shadows.card,
        transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
        overflow: 'hidden',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {title && (
        <div
          style={{
            padding: spacing[4],
            borderBottom: `1px solid ${colors.dark.border}`,
            background: `linear-gradient(135deg, rgba(255,255,255,0.02) 0%, transparent 100%)`,
          }}
        >
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: parseInt(spacing[2]),
          }}>
            {title}
          </div>
        </div>
      )}
      <div style={{
        padding: noPadding ? 0 : spacing[4],
        flex: 1,
        overflow: 'auto',
      }}>
        {children}
      </div>
    </div>
  );
};

/**
 * 核心指标卡片 - Bento Grid 风格
 */
const MetricCards: React.FC<{ dashboardData: AIDashboardResponse }> = ({ dashboardData }) => {
  const cards = [
    {
      title: '系统健康度',
      value: dashboardData.health_score,
      suffix: '/ 100',
      icon: <SecurityScanOutlined />,
      color: dashboardData.health_score > 80 ? colors.semantic.success : dashboardData.health_score > 50 ? colors.semantic.warning : colors.semantic.error,
      status: dashboardData.status,
      trend: dashboardData.health_score > 80 ? 'up' : 'down',
    },
    {
      title: '活跃告警',
      value: dashboardData.active_alerts.length,
      icon: <BellOutlined />,
      color: dashboardData.active_alerts.filter((a) => a.severity === 'critical').length > 0 ? colors.semantic.error : colors.semantic.warning,
      trend: dashboardData.active_alerts.length > 3 ? 'down' : 'up',
    },
    {
      title: 'AI 洞察',
      value: dashboardData.ai_insights.length,
      icon: <ThunderboltOutlined />,
      color: colors.semantic.accent,
      trend: 'up',
    },
    {
      title: '建议操作',
      value: dashboardData.suggested_actions.length,
      icon: <RocketOutlined />,
      color: colors.semantic.info,
      trend: 'up',
    },
  ];

  return (
    <BentoCard>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: spacing[4],
      }}>
        {cards.map((card, index) => (
          <div
            key={index}
            style={{
              padding: spacing[4],
              background: colors.dark.bgCardHover,
              borderRadius: radii.md,
              border: `1px solid ${colors.dark.border}`,
              transition: `all ${transitions.durations.normal} ${transitions.timing.ease}`,
              cursor: 'default',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = colors.primary[900];
              e.currentTarget.style.borderColor = colors.primary[700];
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = colors.dark.bgCardHover;
              e.currentTarget.style.borderColor = colors.dark.border;
            }}
          >
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              marginBottom: spacing[3],
            }}>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: radii.lg,
                background: `${card.color}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: card.color,
                fontSize: 20,
              }}>
                {card.icon}
              </div>
              {card.trend && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  fontSize: typography.fontSize.xs,
                  color: card.trend === 'up' ? colors.semantic.success : colors.semantic.error,
                }}>
                  {card.trend === 'up' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                </div>
              )}
            </div>
            <div style={{
              fontSize: typography.fontSize['3xl'],
              fontWeight: 700,
              color: colors.neutral[100],
              marginBottom: spacing[1],
            }}>
              {card.value}{card.suffix}
            </div>
            <div style={{
              fontSize: typography.fontSize.sm,
              color: colors.neutral[400],
            }}>
              {card.title}
            </div>
            {card.status && (
              <Tag
                color={card.status === 'critical' ? 'red' : card.status === 'warning' ? 'orange' : 'green'}
                style={{
                  marginTop: spacing[2],
                  borderRadius: radii.sm,
                  fontSize: typography.fontSize.xs,
                }}
              >
                {card.status === 'critical' ? '严重' : card.status === 'warning' ? '警告' : '健康'}
              </Tag>
            )}
          </div>
        ))}
      </div>
    </BentoCard>
  );
};

/**
 * AI 洞察面板
 */
const AIInsightsPanel: React.FC<{ insights: string[] }> = ({ insights }) => {
  if (insights.length === 0) return null;

  return (
    <BentoCard
      title={
        <>
          <ThunderboltOutlined style={{ color: colors.semantic.accent }} />
          <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>AI 智能洞察</span>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[3] }}>
        {insights.map((insight, index) => (
          <div
            key={index}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: spacing[3],
              padding: spacing[3],
              background: `rgba(${parseInt(colors.semantic.accent.slice(1, 3), 16)}, ${parseInt(colors.semantic.accent.slice(3, 5), 16)}, ${parseInt(colors.semantic.accent.slice(5, 7), 16)}, 0.1)`,
              borderRadius: radii.md,
              border: `1px solid rgba(${parseInt(colors.semantic.accent.slice(1, 3), 16)}, ${parseInt(colors.semantic.accent.slice(3, 5), 16)}, ${parseInt(colors.semantic.accent.slice(5, 7), 16)}, 0.2)`,
            }}
          >
            <ThunderboltOutlined
              style={{
                color: colors.semantic.accent,
                fontSize: typography.fontSize.lg,
                marginTop: 2,
              }}
            />
            <div style={{
              color: colors.neutral[200],
              fontSize: typography.fontSize.base,
              lineHeight: typography.lineHeight.relaxed,
              flex: 1,
            }}>
              {insight}
            </div>
          </div>
        ))}
      </div>
    </BentoCard>
  );
};

/**
 * 告警列表 - Bento 风格
 */
const AlertsList: React.FC<{ alerts: AlertType[] }> = ({ alerts }) => {
  const getSeverityColor = (severity: string) => {
    const colorMap: Record<string, string> = {
      critical: colors.semantic.error,
      high: '#f97316',
      medium: colors.semantic.warning,
      low: colors.semantic.info,
    };
    return colorMap[severity] || colors.neutral[500];
  };

  return (
    <BentoCard
      title={
        <>
          <BellOutlined style={{ color: colors.semantic.error }} />
          <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>活跃告警</span>
        </>
      }
    >
      {alerts.length === 0 ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: spacing[12],
          color: colors.neutral[500],
        }}>
          <div style={{ fontSize: 32, marginBottom: spacing[2] }}>✓</div>
          <div style={{ fontSize: typography.fontSize.base }}>暂无告警</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[2] }}>
          {alerts.slice(0, 5).map((alert, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: spacing[3],
                padding: spacing[3],
                background: colors.dark.bgCardHover,
                borderRadius: radii.md,
                border: `1px solid ${colors.dark.border}`,
                transition: `all ${transitions.durations.fast}`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = getSeverityColor(alert.severity);
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = colors.dark.border;
              }}
            >
              <Badge
                color={getSeverityColor(alert.severity)}
                style={{
                  boxShadow: `0 0 8px ${getSeverityColor(alert.severity)}60`,
                }}
              />
              <div style={{ flex: 1 }}>
                <div style={{
                  color: colors.neutral[100],
                  fontSize: typography.fontSize.sm,
                  fontWeight: 500,
                }}>
                  {alert.service}
                </div>
                <div style={{
                  color: colors.neutral[400],
                  fontSize: typography.fontSize.xs,
                }}>
                  {alert.type}
                </div>
              </div>
              <div style={{
                color: colors.neutral[500],
                fontSize: typography.fontSize.xs,
              }}>
                {new Date(alert.detected_at).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </BentoCard>
  );
};

/**
 * 服务健康状态 - Bento 风格表格
 */
const ServiceHealthTable: React.FC<{ services: ServiceHealth[] }> = ({ services }) => {
  const columns = [
    {
      title: <span style={{ color: colors.neutral[300], fontSize: typography.fontSize.sm }}>服务名称</span>,
      dataIndex: 'service_name',
      key: 'service_name',
      render: (text: string) => <span style={{ color: colors.neutral[100], fontSize: typography.fontSize.base }}>{text}</span>,
    },
    {
      title: <span style={{ color: colors.neutral[300], fontSize: typography.fontSize.sm }}>健康状态</span>,
      dataIndex: 'health_status',
      key: 'health_status',
      render: (status: string) => {
        const config: Record<string, { color: string; icon: string }> = {
          healthy: { color: colors.semantic.success, icon: '🟢' },
          warning: { color: colors.semantic.warning, icon: '🟡' },
          critical: { color: colors.semantic.error, icon: '🔴' },
          unknown: { color: colors.neutral[500], icon: '⚪' },
        };
        const cfg = config[status] || config.unknown;
        return (
          <Tag
            color={cfg.color}
            style={{
              borderRadius: radii.sm,
              padding: `${spacing[1]} ${spacing[2]}`,
              fontSize: typography.fontSize.xs,
              border: `1px solid ${cfg.color}`,
              background: `${cfg.color}15`,
            }}
          >
            {cfg.icon} {status}
          </Tag>
        );
      },
    },
    {
      title: <span style={{ color: colors.neutral[300], fontSize: typography.fontSize.sm }}>健康分数</span>,
      dataIndex: 'health_score',
      key: 'health_score',
      render: (score: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing[2] }}>
          <Progress
            percent={Math.round(score)}
            strokeColor={getHealthColor(score > 80 ? 'healthy' : score > 50 ? 'warning' : 'critical')}
            trailColor={colors.dark.border}
            size="small"
            strokeWidth={6}
            format={() => `${Math.round(score)}`}
            style={{ width: 80 }}
          />
        </div>
      ),
    },
    {
      title: <span style={{ color: colors.neutral[300], fontSize: typography.fontSize.sm }}>错误数</span>,
      dataIndex: 'error_count',
      key: 'error_count',
      render: (count: number) => (
        <span style={{
          color: count > 0 ? colors.semantic.error : colors.neutral[400],
          fontSize: typography.fontSize.sm,
          fontWeight: count > 0 ? 600 : 400,
        }}>
          {count}
        </span>
      ),
    },
    {
      title: <span style={{ color: colors.neutral[300], fontSize: typography.fontSize.sm }}>警告数</span>,
      dataIndex: 'warning_count',
      key: 'warning_count',
      render: (count: number) => (
        <span style={{
          color: count > 0 ? colors.semantic.warning : colors.neutral[400],
          fontSize: typography.fontSize.sm,
          fontWeight: count > 0 ? 600 : 400,
        }}>
          {count}
        </span>
      ),
    },
  ];

  return (
    <BentoCard
      title={
        <>
          <LineChartOutlined style={{ color: colors.semantic.info }} />
          <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>服务健康状态</span>
        </>
      }
    >
      <Table
        columns={columns}
        dataSource={services}
        pagination={false}
        size="small"
        scroll={{ x: 500 }}
        locale={{ emptyText: '暂无服务数据' }}
        style={{ background: 'transparent' }}
        rowClassName={() => 'bento-table-row'}
      />
    </BentoCard>
  );
};

/**
 * 健康趋势图表 - Bento 风格
 */
const HealthTrendChart: React.FC = () => {
  const option = {
    title: { text: '', textStyle: { color: colors.neutral[100] } },
    tooltip: {
      trigger: 'axis',
      backgroundColor: colors.dark.bgCard,
      borderColor: colors.dark.border,
      borderWidth: 1,
      textStyle: { color: colors.neutral[200] },
    },
    xAxis: {
      type: 'category',
      data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
      axisLine: { lineStyle: { color: colors.dark.border } },
      axisLabel: { color: colors.neutral[400] },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { lineStyle: { color: colors.dark.border } },
      axisLabel: { color: colors.neutral[400] },
      splitLine: { lineStyle: { color: colors.dark.border } },
    },
    series: [
      {
        name: '健康分数',
        type: 'line',
        smooth: true,
        data: [82, 85, 83, 88, 85, 87],
        itemStyle: { color: colors.semantic.success },
        lineStyle: { width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: `${colors.semantic.success}40` },
            { offset: 1, color: `${colors.semantic.success}05` },
          ]),
        },
      },
    ],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
  };

  return (
    <BentoCard>
      <ReactECharts option={option} style={{ height: 280 }} />
    </BentoCard>
  );
};

/**
 * 主仪表板组件 - Bento Grid 布局
 */
const GenerativeDashboard: React.FC = () => {
  const { dashboardData, setDashboardData, services, setServices, alerts, setAlerts } =
    useDashboardStore();
  const [localLoading, setLocalLoading] = useState(false);

  const loadData = async () => {
    setLocalLoading(true);
    try {
      const dashboard = await aiNativeApi.getDashboard();
      setDashboardData(dashboard);
      const servicesData = await observabilityApi.getServices();
      setServices(Object.values(servicesData.services));
      setAlerts(dashboard.active_alerts);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLocalLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (localLoading || !dashboardData) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: 'calc(100vh - 200px)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: 64,
              height: 64,
              margin: '0 auto 24px',
              borderRadius: radii.xl,
              background: `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: shadows.glow,
              animation: 'pulse 2s ease-in-out infinite',
            }}
          >
            <RobotOutlined style={{ color: '#fff', fontSize: 32 }} />
          </div>
          <p style={{
            color: colors.neutral[400],
            fontSize: typography.fontSize.lg,
            marginTop: spacing[4],
          }}>
            AI 正在生成个性化仪表板...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: spacing[6] }}>
        <h1 style={{
          fontSize: typography.fontSize['4xl'],
          fontWeight: 700,
          color: colors.neutral[100],
          margin: 0,
          display: 'flex',
          alignItems: 'center',
          gap: spacing[3],
        }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: radii.lg,
              background: `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <ThunderboltOutlined style={{ color: '#fff', fontSize: 20 }} />
          </div>
          AI 动态仪表板
        </h1>
        <p style={{
          color: colors.neutral[500],
          marginTop: spacing[2],
          fontSize: typography.fontSize.base,
        }}>
          AI 根据系统状态实时生成的个性化监控视图
        </p>
      </div>

      {/* Bento Grid 布局 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: bentoGrid.gap.lg,
        marginBottom: spacing[6],
      }}>
        {/* 核心指标 - 占据整行 */}
        <div style={{ gridColumn: '1 / -1' }}>
          <MetricCards dashboardData={dashboardData} />
        </div>

        {/* AI 洞察 - 占据整行 */}
        {dashboardData.ai_insights.length > 0 && (
          <div style={{ gridColumn: '1 / -1' }}>
            <AIInsightsPanel insights={dashboardData.ai_insights} />
          </div>
        )}

        {/* 健康趋势图 - 2/3 宽度 */}
        <div style={{ gridColumn: 'span 2' }}>
          <HealthTrendChart />
        </div>

        {/* 告警列表 - 1/3 宽度 */}
        <div>
          <AlertsList alerts={alerts} />
        </div>

        {/* 服务健康状态 - 占据整行 */}
        <div style={{ gridColumn: '1 / -1' }}>
          <ServiceHealthTable services={services} />
        </div>
      </div>
    </div>
  );
};

export default GenerativeDashboard;
