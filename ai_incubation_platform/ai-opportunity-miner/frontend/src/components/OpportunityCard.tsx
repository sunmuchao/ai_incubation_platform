/**
 * 机会卡片组件 - Bento Grid 风格重构
 * 基于设计令牌系统，实现 Linear.app 风格的精致卡片
 */
import React, { useState } from 'react';
import {
  Tag,
  Space,
  Typography,
  Progress,
  Button,
  Collapse,
  Tooltip,
  Badge,
} from 'antd';
import {
  ThunderboltOutlined,
  RiseOutlined,
  FallOutlined,
  SafetyCertificateOutlined,
  WarningOutlined,
  LinkOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  BulbOutlined,
  TeamOutlined,
  DollarOutlined,
  FileTextOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import type { BusinessOpportunity, OpportunityType } from '../types';

const { Title, Paragraph, Text } = Typography;
const { Panel } = Collapse;

interface OpportunityCardProps {
  opportunity: BusinessOpportunity;
  onSelect?: (opportunity: BusinessOpportunity) => void;
  compact?: boolean;
}

/**
 * 机会类型配置 - 更新为设计令牌颜色
 */
const OPPORTUNITY_TYPE_CONFIG: Record<OpportunityType, { color: string; icon: React.ReactNode; label: string }> = {
  market: {
    color: 'var(--color-primary-500)',
    icon: <RiseOutlined />,
    label: '市场机会',
  },
  product: {
    color: 'var(--color-info)',
    icon: <BulbOutlined />,
    label: '产品机会',
  },
  partnership: {
    color: 'var(--color-success)',
    icon: <TeamOutlined />,
    label: '合作机会',
  },
  investment: {
    color: 'var(--color-gold)',
    icon: <DollarOutlined />,
    label: '投资机会',
  },
};

/**
 * 置信度颜色映射
 */
const getConfidenceColor = (score: number): string => {
  if (score >= 0.8) return 'var(--color-success)';
  if (score >= 0.6) return 'var(--color-warning)';
  if (score >= 0.4) return 'var(--color-warning-light)';
  return 'var(--color-error)';
};

/**
 * 风险等级颜色映射
 */
const getRiskColor = (score: number): string => {
  if (score >= 0.7) return 'var(--color-error)';
  if (score >= 0.4) return 'var(--color-warning)';
  return 'var(--color-success)';
};

/**
 * 风险等级标签
 */
const getRiskLabel = (score: number): string => {
  if (score >= 0.7) return '高风险';
  if (score >= 0.4) return '中风险';
  return '低风险';
};

/**
 * 格式化金额
 */
const formatCurrency = (value: number, currency: string = 'CNY'): string => {
  if (value >= 100000000) {
    return `¥${(value / 100000000).toFixed(2)} 亿`;
  }
  if (value >= 10000) {
    return `¥${(value / 10000).toFixed(1)} 万`;
  }
  return `¥${value.toFixed(0)}`;
};

/**
 * Bento 风格机会卡片主组件
 */
const OpportunityCard: React.FC<OpportunityCardProps> = ({
  opportunity,
  onSelect,
  compact = false,
}) => {
  const [expanded, setExpanded] = useState(false);
  const typeConfig = OPPORTUNITY_TYPE_CONFIG[opportunity.type] || OPPORTUNITY_TYPE_CONFIG.market;
  const confidenceColor = getConfidenceColor(opportunity.confidence_score);
  const riskColor = getRiskColor(opportunity.risk_score);
  const isHighConfidence = opportunity.confidence_score >= 0.8;
  const isHighValue = opportunity.potential_value >= 1000000;

  // 紧凑模式 - Bento 小卡片
  if (compact) {
    return (
      <div
        className="bento-card bento-card-sm fade-in"
        onClick={() => onSelect?.(opportunity)}
        style={{
          cursor: 'pointer',
          borderLeft: `3px solid ${typeConfig.color}`,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Space style={{ marginBottom: 8 }} wrap size={4}>
              <Badge
                color={typeConfig.color}
                style={{ borderRadius: 'var(--radius-sm)' }}
              />
              <Text
                strong
                className="truncate"
                style={{
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--font-size-sm)',
                }}
              >
                {opportunity.title}
              </Text>
            </Space>
            <Space size={4} wrap>
              <Tag
                style={{
                  background: `${typeConfig.color}15`,
                  border: `1px solid ${typeConfig.color}40`,
                  color: typeConfig.color,
                  fontSize: '10px',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                {typeConfig.label}
              </Tag>
              <Tag
                style={{
                  background: `${confidenceColor}15`,
                  border: `1px solid ${confidenceColor}40`,
                  color: confidenceColor,
                  fontSize: '10px',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                {(opportunity.confidence_score * 100).toFixed(0)}%
              </Tag>
              {opportunity.potential_value > 0 && (
                <Tag
                  style={{
                    background: 'var(--color-gold)15',
                    border: '1px solid var(--color-gold)40',
                    color: 'var(--color-gold)',
                    fontSize: '10px',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <DollarOutlined />
                  {formatCurrency(opportunity.potential_value)}
                </Tag>
              )}
            </Space>
          </div>
          <Text
            style={{
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-text-tertiary)',
              flexShrink: 0,
              marginLeft: 8,
            }}
          >
            {new Date(opportunity.created_at).toLocaleDateString('zh-CN')}
          </Text>
        </div>
      </div>
    );
  }

  // 完整模式 - Bento 大卡片
  return (
    <div
      className="bento-card bento-card-lg fade-in"
      style={{
        background: 'var(--gradient-bg-card)',
        border: '1px solid var(--color-border-base)',
      }}
    >
      {/* 顶部装饰条 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '2px',
          background: `linear-gradient(90deg, ${typeConfig.color} 0%, transparent 60%)`,
        }}
      />

      {/* 头部标签区 */}
      <div style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 12 }} wrap size={8}>
          <Tag
            icon={typeConfig.icon}
            style={{
              background: `${typeConfig.color}15`,
              border: `1px solid ${typeConfig.color}40`,
              color: typeConfig.color,
              fontWeight: 'var(--font-weight-medium)',
              borderRadius: 'var(--radius-md)',
              padding: '2px 12px',
            }}
          >
            {typeConfig.label}
          </Tag>
          {isHighConfidence && (
            <Tag
              icon={<ThunderboltOutlined />}
              style={{
                background: 'var(--color-gold)15',
                border: '1px solid var(--color-gold)40',
                color: 'var(--color-gold)',
                borderRadius: 'var(--radius-md)',
                padding: '2px 12px',
              }}
            >
              高置信度
            </Tag>
          )}
          {isHighValue && (
            <Tag
              icon={<DollarOutlined />}
              style={{
                background: 'var(--color-primary-500)15',
                border: '1px solid var(--color-primary-500)40',
                color: 'var(--color-primary-400)',
                borderRadius: 'var(--radius-md)',
                padding: '2px 12px',
              }}
            >
              高价值
            </Tag>
          )}
          <Tag
            icon={opportunity.status === 'validated' ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
            style={{
              background: opportunity.status === 'validated'
                ? 'var(--color-success)15'
                : 'var(--color-info)15',
              border: `1px solid ${opportunity.status === 'validated' ? 'var(--color-success)40' : 'var(--color-info)40'}`,
              color: opportunity.status === 'validated' ? 'var(--color-success)' : 'var(--color-info)',
              borderRadius: 'var(--radius-md)',
              padding: '2px 12px',
            }}
          >
            {opportunity.status === 'validated' ? '已验证' : '待验证'}
          </Tag>
        </Space>

        <Title
          level={4}
          className="line-clamp-2"
          style={{
            margin: 0,
            color: 'var(--color-text-primary)',
            fontWeight: 'var(--font-weight-semibold)',
          }}
        >
          {opportunity.title}
        </Title>
      </div>

      {/* 描述 */}
      <Paragraph
        className="line-clamp-2"
        style={{
          color: 'var(--color-text-secondary)',
          marginBottom: 20,
          lineHeight: 'var(--line-height-relaxed)',
          fontSize: 'var(--font-size-sm)',
        }}
      >
        {opportunity.description}
      </Paragraph>

      {/* 核心指标 - Bento 网格布局 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 'var(--spacing-3)',
          marginBottom: 20,
        }}
      >
        {/* AI 置信度 */}
        <div
          style={{
            background: 'var(--color-bg-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--spacing-3)',
            border: '1px solid var(--color-border-secondary)',
          }}
        >
          <Text
            style={{
              color: 'var(--color-text-tertiary)',
              fontSize: 'var(--font-size-xs)',
              display: 'block',
              marginBottom: 8,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            AI 置信度
          </Text>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Text
              style={{
                color: confidenceColor,
                fontSize: 'var(--font-size-xl)',
                fontWeight: 'var(--font-weight-bold)',
              }}
            >
              {(opportunity.confidence_score * 100).toFixed(0)}%
            </Text>
            <Progress
              percent={opportunity.confidence_score * 100}
              showInfo={false}
              size={{ width: '100%', height: 4 }}
              strokeColor={confidenceColor}
              trailColor="var(--color-bg-container)"
            />
          </div>
        </div>

        {/* 潜在价值 */}
        <div
          style={{
            background: 'var(--color-bg-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--spacing-3)',
            border: '1px solid var(--color-border-secondary)',
          }}
        >
          <Text
            style={{
              color: 'var(--color-text-tertiary)',
              fontSize: 'var(--font-size-xs)',
              display: 'block',
              marginBottom: 8,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            潜在价值
          </Text>
          <Text
            style={{
              color: 'var(--color-gold)',
              fontSize: 'var(--font-size-lg)',
              fontWeight: 'var(--font-weight-bold)',
            }}
          >
            {formatCurrency(opportunity.potential_value, opportunity.potential_value_currency)}
          </Text>
        </div>

        {/* 风险等级 */}
        <div
          style={{
            background: 'var(--color-bg-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--spacing-3)',
            border: '1px solid var(--color-border-secondary)',
          }}
        >
          <Text
            style={{
              color: 'var(--color-text-tertiary)',
              fontSize: 'var(--font-size-xs)',
              display: 'block',
              marginBottom: 8,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            风险等级
          </Text>
          <Space>
            <Text
              style={{
                color: riskColor,
                fontSize: 'var(--font-size-base)',
                fontWeight: 'var(--font-weight-semibold)',
              }}
            >
              {getRiskLabel(opportunity.risk_score)}
            </Text>
            <WarningOutlined style={{ color: riskColor }} />
          </Space>
        </div>
      </div>

      {/* 标签 */}
      {opportunity.tags.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Space wrap size={8}>
            {opportunity.tags.map((tag, index) => (
              <Tag
                key={index}
                style={{
                  background: 'var(--color-primary-500)15',
                  border: '1px solid var(--color-primary-500)30',
                  color: 'var(--color-primary-300)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--font-size-xs)',
                }}
                icon={<BulbOutlined />}
              >
                {tag}
              </Tag>
            ))}
          </Space>
        </div>
      )}

      {/* 风险标签 */}
      {opportunity.risk_labels.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Text
            style={{
              color: 'var(--color-text-tertiary)',
              fontSize: 'var(--font-size-xs)',
              display: 'block',
              marginBottom: 8,
            }}
          >
            <WarningOutlined style={{ marginRight: 4 }} />
            风险因素
          </Text>
          <Space wrap size={8}>
            {opportunity.risk_labels.map((label, index) => (
              <Tag
                key={index}
                style={{
                  background: `${riskColor}15`,
                  border: `1px solid ${riskColor}40`,
                  color: riskColor,
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--font-size-xs)',
                }}
              >
                {label.replace('_', ' ')}
              </Tag>
            ))}
          </Space>
        </div>
      )}

      {/* 来源信息 */}
      {opportunity.source_name && (
        <div
          style={{
            marginBottom: 16,
            padding: 'var(--spacing-3)',
            background: 'var(--color-bg-subtle)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-border-secondary)',
          }}
        >
          <Text
            style={{
              color: 'var(--color-text-tertiary)',
              fontSize: 'var(--font-size-xs)',
            }}
          >
            <FileTextOutlined style={{ marginRight: 6 }} />
            来源：{opportunity.source_name}
          </Text>
          {opportunity.source_url && (
            <Button
              type="link"
              size="small"
              href={opportunity.source_url}
              target="_blank"
              icon={<LinkOutlined />}
              style={{
                color: 'var(--color-accent-500)',
                marginLeft: 8,
                padding: 0,
              }}
            >
              查看原文
            </Button>
          )}
        </div>
      )}

      {/* 底部操作区 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingTop: 16,
          borderTop: '1px solid var(--color-border-secondary)',
        }}
      >
        <Text
          style={{
            color: 'var(--color-text-tertiary)',
            fontSize: 'var(--font-size-xs)',
          }}
        >
          创建于 {new Date(opportunity.created_at).toLocaleString('zh-CN')}
        </Text>
        <Space size={8}>
          <Button
            size="small"
            onClick={() => onSelect?.(opportunity)}
            style={{
              borderColor: 'var(--color-border-base)',
              color: 'var(--color-text-secondary)',
              background: 'var(--glass-light)',
            }}
          >
            深入分析
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<CheckCircleOutlined />}
          >
            标记为已验证
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default OpportunityCard;
