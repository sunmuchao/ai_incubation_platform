/**
 * AI Opportunity Miner - Bento Grid 风格主应用
 *
 * 设计理念：
 * 1. Bento Grid 布局 - 模块化网格，比例美学
 * 2. Monochromatic 配色 - 深蓝灰色系
 * 3. Linear.app 风格 - 精致细腻的阴影和边框
 * 4. Chat-first - 对话式交互作为核心界面
 */
import React, { useState, useEffect } from 'react';
import {
  Layout,
  Menu,
  theme,
  Badge,
  Avatar,
  Dropdown,
  Space,
  Typography,
  Button,
  Drawer,
  Tooltip,
} from 'antd';
import {
  MessageOutlined,
  DashboardOutlined,
  BulbOutlined,
  BellOutlined,
  SettingOutlined,
  UserOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  MenuOutlined,
  FireOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { BusinessOpportunity } from './types';
import { AIChat, OpportunityCard, AgentWorkflow } from './components';
import { listOpportunities, getAgentStatus } from './api';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

// 菜单项配置
const menuItems = [
  {
    key: 'chat',
    icon: <MessageOutlined />,
    label: 'AI 对话',
  },
  {
    key: 'dashboard',
    icon: <DashboardOutlined />,
    label: '仪表板',
  },
  {
    key: 'opportunities',
    icon: <BulbOutlined />,
    label: '机会列表',
    badge: 0,
  },
  {
    key: 'trends',
    icon: <LineChartOutlined />,
    label: '趋势分析',
  },
  {
    key: 'agents',
    icon: <ThunderboltOutlined />,
    label: 'Agent 状态',
  },
];

/**
 * Bento Grid 风格的仪表板组件
 */
const DashboardView: React.FC = () => {
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        const response = await fetch('http://localhost:8006/api/dashboard/overview');
        const data = await response.json();
        setOverview(data.data);
      } catch (error) {
        console.error('Failed to fetch overview:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchOverview();
  }, []);

  if (loading) {
    return (
      <div
        className="bento-grid"
        style={{ padding: 40, justifyContent: 'center', alignItems: 'center' }}
      >
        <div className="skeleton" style={{ width: 200, height: 200, borderRadius: 'var(--radius-2xl)' }} />
        <div className="skeleton" style={{ width: 200, height: 200, borderRadius: 'var(--radius-2xl)' }} />
        <div className="skeleton" style={{ width: 200, height: 200, borderRadius: 'var(--radius-2xl)' }} />
        <div className="skeleton" style={{ width: 200, height: 200, borderRadius: 'var(--radius-2xl)' }} />
      </div>
    );
  }

  // Bento Grid 统计卡片配置
  const statCards = [
    {
      title: '总机会数',
      value: overview?.summary?.total_opportunities || 0,
      color: 'var(--color-primary-500)',
      gradient: 'linear-gradient(135deg, var(--color-primary-500)20 0%, var(--color-bg-subtle) 100%)',
      icon: <BulbOutlined />,
    },
    {
      title: '本周新增',
      value: overview?.summary?.new_this_week || 0,
      color: 'var(--color-success)',
      gradient: 'linear-gradient(135deg, var(--color-success)20 0%, var(--color-bg-subtle) 100%)',
      icon: <FireOutlined />,
    },
    {
      title: '已验证',
      value: overview?.summary?.validated_opportunities || 0,
      color: 'var(--color-info)',
      gradient: 'linear-gradient(135deg, var(--color-info)20 0%, var(--color-bg-subtle) 100%)',
      icon: <CheckCircleOutlined />,
    },
    {
      title: '高置信度',
      value: overview?.summary?.high_confidence_count || 0,
      color: 'var(--color-gold)',
      gradient: 'linear-gradient(135deg, var(--color-gold)20 0%, var(--color-bg-subtle) 100%)',
      icon: <ThunderboltOutlined />,
    },
  ];

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <Title
          level={4}
          style={{
            color: 'var(--color-text-primary)',
            margin: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <DashboardOutlined /> 概览
        </Title>
      </div>

      {/* Bento Grid 统计卡片 - 4 列 */}
      <div
        className="bento-grid"
        style={{
          gridTemplateColumns: 'repeat(4, 1fr)',
          marginBottom: 32,
        }}
      >
        {statCards.map((stat, index) => (
          <div
            key={index}
            className="bento-card"
            style={{
              background: stat.gradient,
              border: `1px solid ${stat.color}30`,
              borderLeft: `3px solid ${stat.color}`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{ color: stat.color, fontSize: 20 }}>{stat.icon}</span>
              <Text style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--font-size-xs)', textTransform: 'uppercase' }}>
                {stat.title}
              </Text>
            </div>
            <Text
              style={{
                color: stat.color,
                fontSize: 'var(--font-size-4xl)',
                fontWeight: 'var(--font-weight-bold)',
              }}
            >
              {stat.value}
            </Text>
          </div>
        ))}
      </div>

      {/* 数据源状态 - Bento Grid */}
      <div style={{ marginBottom: 16 }}>
        <Text
          style={{
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 'var(--font-weight-semibold)',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            display: 'block',
            marginBottom: 16,
          }}
        >
          数据源状态
        </Text>
        <div
          className="bento-grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}
        >
          {Object.entries(overview?.data_sources || {}).map(([name, data]: [string, any]) => (
            <div
              key={name}
              className="bento-card bento-card-sm"
              style={{
                background: 'var(--gradient-bg-card)',
                border: '1px solid var(--color-border-base)',
              }}
            >
              <Space style={{ marginBottom: 8 }}>
                <Badge status={data.status === 'active' ? 'success' : 'error'} />
                <Text
                  strong
                  style={{
                    color: 'var(--color-text-primary)',
                    textTransform: 'capitalize',
                  }}
                >
                  {name}
                </Text>
              </Space>
              <Text
                style={{
                  color: 'var(--color-text-tertiary)',
                  fontSize: 'var(--font-size-xs)',
                }}
              >
                {data.count} 条数据
              </Text>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/**
 * 机会列表组件 - Bento Grid 布局
 */
const OpportunitiesView: React.FC<{
  onSelectOpportunity: (opp: BusinessOpportunity) => void;
}> = ({ onSelectOpportunity }) => {
  const [opportunities, setOpportunities] = useState<BusinessOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'high_value' | 'high_confidence'>('all');

  useEffect(() => {
    const fetchOpportunities = async () => {
      try {
        const response = await fetch('http://localhost:8006/api/opportunities');
        const data = await response.json();
        setOpportunities(data);
      } catch (error) {
        console.error('Failed to fetch opportunities:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchOpportunities();
  }, []);

  const filteredOpportunities = opportunities.filter((opp) => {
    if (filter === 'high_value') return opp.potential_value >= 1000000;
    if (filter === 'high_confidence') return opp.confidence_score >= 0.8;
    return true;
  });

  return (
    <div className="fade-in">
      {/* 过滤器 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <Title
          level={4}
          style={{
            color: 'var(--color-text-primary)',
            margin: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <BulbOutlined /> 机会列表
        </Title>
        <Space size={8}>
          {(['all', 'high_value', 'high_confidence'] as const).map((f) => (
            <Button
              key={f}
              size="small"
              onClick={() => setFilter(f)}
              style={{
                background: filter === f ? 'var(--gradient-accent)' : 'var(--glass-light)',
                border: filter === f ? 'none' : '1px solid var(--color-border-base)',
                color: filter === f ? '#fff' : 'var(--color-text-secondary)',
              }}
            >
              {f === 'all' ? '全部' : f === 'high_value' ? '高价值' : '高置信度'}
            </Button>
          ))}
        </Space>
      </div>

      {/* Bento Grid 机会卡片 */}
      {loading ? (
        <div
          className="bento-grid"
          style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}
        >
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton" style={{ height: 280, borderRadius: 'var(--radius-xl)' }} />
          ))}
        </div>
      ) : filteredOpportunities.length === 0 ? (
        <div
          style={{
            padding: 80,
            textAlign: 'center',
            color: 'var(--color-text-tertiary)',
          }}
        >
          暂无机会数据
        </div>
      ) : (
        <div
          className="bento-grid"
          style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}
        >
          {filteredOpportunities.map((opp) => (
            <OpportunityCard
              key={opp.id}
              opportunity={opp}
              onSelect={onSelectOpportunity}
            />
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Agent 状态组件 - Bento Grid 风格
 */
const AgentsView: React.FC = () => {
  const [agentStatus, setAgentStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAgentStatus = async () => {
      try {
        const response = await fetch('http://localhost:8006/agent/status');
        const data = await response.json();
        setAgentStatus(data);
      } catch (error) {
        console.error('Failed to fetch agent status:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchAgentStatus();
  }, []);

  if (loading) {
    return (
      <div
        className="bento-grid"
        style={{ padding: 40, justifyContent: 'center' }}
      >
        <div className="skeleton" style={{ width: 280, height: 140, borderRadius: 'var(--radius-xl)' }} />
        <div className="skeleton" style={{ width: 280, height: 140, borderRadius: 'var(--radius-xl)' }} />
        <div className="skeleton" style={{ width: 280, height: 140, borderRadius: 'var(--radius-xl)' }} />
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <Title
          level={4}
          style={{
            color: 'var(--color-text-primary)',
            margin: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <ThunderboltOutlined /> Agent 运行状态
        </Title>
      </div>

      {/* Bento Grid 状态卡片 - 3 列 */}
      <div
        className="bento-grid"
        style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 32 }}
      >
        <div
          className="bento-card"
          style={{
            background: agentStatus?.deerflow_available
              ? 'linear-gradient(135deg, var(--color-success)15 0%, var(--color-bg-subtle) 100%)'
              : 'linear-gradient(135deg, var(--color-error)15 0%, var(--color-bg-subtle) 100%)',
            border: `1px solid ${agentStatus?.deerflow_available ? 'var(--color-success)30' : 'var(--color-error)30'}`,
            borderLeft: `3px solid ${agentStatus?.deerflow_available ? 'var(--color-success)' : 'var(--color-error)'}`,
          }}
        >
          <Text
            style={{
              color: 'var(--color-text-tertiary)',
              fontSize: 'var(--font-size-xs)',
              display: 'block',
              marginBottom: 12,
              textTransform: 'uppercase',
            }}
          >
            DeerFlow 状态
          </Text>
          <Space size={12}>
            <Badge status={agentStatus?.deerflow_available ? 'success' : 'error'} />
            <Text
              strong
              style={{
                color: agentStatus?.deerflow_available ? 'var(--color-success)' : 'var(--color-error)',
                fontSize: 'var(--font-size-xl)',
              }}
            >
              {agentStatus?.deerflow_available ? '可用' : '不可用'}
            </Text>
          </Space>
        </div>

        <div
          className="bento-card"
          style={{
            background: 'linear-gradient(135deg, var(--color-primary-500)15 0%, var(--color-bg-subtle) 100%)',
            border: '1px solid var(--color-primary-500)30',
            borderLeft: '3px solid var(--color-primary-500)',
          }}
        >
          <Text
            style={{
              color: 'var(--color-text-tertiary)',
              fontSize: 'var(--font-size-xs)',
              display: 'block',
              marginBottom: 12,
              textTransform: 'uppercase',
            }}
          >
            已注册工具数
          </Text>
          <Text
            strong
            style={{
              color: 'var(--color-primary-400)',
              fontSize: 'var(--font-size-4xl)',
            }}
          >
            {agentStatus?.tools_registered || 0}
          </Text>
        </div>

        <div
          className="bento-card"
          style={{
            background: 'linear-gradient(135deg, var(--color-info)20 0%, var(--color-bg-subtle) 100%)',
            border: '1px solid var(--color-info)30',
            borderLeft: '3px solid var(--color-info)',
          }}
        >
          <Text
            style={{
              color: 'var(--color-text-tertiary)',
              fontSize: 'var(--font-size-xs)',
              display: 'block',
              marginBottom: 12,
              textTransform: 'uppercase',
            }}
          >
            审计日志数
          </Text>
          <Text
            strong
            style={{
              color: 'var(--color-info)',
              fontSize: 'var(--font-size-4xl)',
            }}
          >
            {agentStatus?.audit_logs_count || 0}
          </Text>
        </div>
      </div>

      {/* 工具列表 */}
      <Text
        style={{
          color: 'var(--color-text-secondary)',
          fontSize: 'var(--font-size-sm)',
          fontWeight: 'var(--font-weight-semibold)',
          display: 'block',
          marginBottom: 16,
        }}
      >
        可用工具
      </Text>
      <div
        className="bento-grid"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}
      >
        {(agentStatus?.tools_schema || []).map((tool: any, index: number) => (
          <div
            key={index}
            className="bento-card bento-card-sm"
            style={{
              background: 'var(--gradient-bg-card)',
              border: '1px solid var(--color-border-base)',
            }}
          >
            <Space style={{ marginBottom: 8 }}>
              <ThunderboltOutlined style={{ color: 'var(--color-primary-500)' }} />
              <Text strong style={{ color: 'var(--color-text-primary)' }}>
                {tool.name}
              </Text>
            </Space>
            <Text
              className="line-clamp-2"
              style={{
                color: 'var(--color-text-secondary)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              {tool.description}
            </Text>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 趋势分析组件 - Bento Grid 风格
 */
const TrendsView: React.FC = () => {
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTrends = async () => {
      try {
        const response = await fetch('http://localhost:8006/api/trends');
        const data = await response.json();
        setTrends(data);
      } catch (error) {
        console.error('Failed to fetch trends:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchTrends();
  }, []);

  if (loading) {
    return (
      <div className="bento-grid" style={{ padding: 40 }}>
        <div className="skeleton" style={{ height: 200, borderRadius: 'var(--radius-xl)' }} />
        <div className="skeleton" style={{ height: 200, borderRadius: 'var(--radius-xl)' }} />
        <div className="skeleton" style={{ height: 200, borderRadius: 'var(--radius-xl)' }} />
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <Title
          level={4}
          style={{
            color: 'var(--color-text-primary)',
            margin: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <LineChartOutlined /> 趋势分析
        </Title>
      </div>

      {trends.length === 0 ? (
        <div
          style={{
            padding: 80,
            textAlign: 'center',
            color: 'var(--color-text-tertiary)',
          }}
        >
          暂无趋势数据
        </div>
      ) : (
        <div
          className="bento-grid"
          style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}
        >
          {trends.map((trend: any) => (
            <div
              key={trend.id}
              className="bento-card"
              style={{
                background: 'var(--gradient-bg-card)',
                border: '1px solid var(--color-border-base)',
              }}
            >
              <div style={{ marginBottom: 16 }}>
                <Title
                  level={5}
                  style={{
                    color: 'var(--color-text-primary)',
                    marginBottom: 16,
                    fontSize: 'var(--font-size-lg)',
                  }}
                >
                  {trend.keyword}
                </Title>

                {/* 趋势分数 */}
                <div style={{ marginBottom: 16 }}>
                  <Text
                    style={{
                      color: 'var(--color-text-tertiary)',
                      fontSize: 'var(--font-size-xs)',
                      display: 'block',
                      marginBottom: 8,
                      textTransform: 'uppercase',
                    }}
                  >
                    趋势分数
                  </Text>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Text
                      style={{
                        color: trend.trend_score >= 0.7 ? 'var(--color-success)' : 'var(--color-warning)',
                        fontSize: 'var(--font-size-2xl)',
                        fontWeight: 'var(--font-weight-bold)',
                      }}
                    >
                      {(trend.trend_score * 100).toFixed(0)}
                    </Text>
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          height: 6,
                          background: 'var(--color-bg-subtle)',
                          borderRadius: 'var(--radius-full)',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${trend.trend_score * 100}%`,
                            height: '100%',
                            background: 'var(--gradient-primary)',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 增长率 */}
                <div style={{ marginBottom: 16 }}>
                  <Text
                    style={{
                      color: 'var(--color-text-tertiary)',
                      fontSize: 'var(--font-size-xs)',
                      display: 'block',
                      marginBottom: 8,
                      textTransform: 'uppercase',
                    }}
                  >
                    增长率
                  </Text>
                  <Text
                    style={{
                      color: trend.growth_rate > 0 ? 'var(--color-success)' : 'var(--color-error)',
                      fontSize: 'var(--font-size-lg)',
                      fontWeight: 'var(--font-weight-semibold)',
                    }}
                  >
                    {trend.growth_rate > 0 ? '+' : ''}{(trend.growth_rate * 100).toFixed(1)}%
                  </Text>
                </div>

                {/* 相关关键词 */}
                {trend.related_keywords?.length > 0 && (
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
                      {trend.related_keywords.slice(0, 5).map((kw: string, i: number) => (
                        <span
                          key={i}
                          style={{
                            padding: '4px 10px',
                            background: 'var(--color-primary-500)15',
                            borderRadius: 'var(--radius-md)',
                            color: 'var(--color-primary-300)',
                            fontSize: 'var(--font-size-xs)',
                          }}
                        >
                          {kw}
                        </span>
                      ))}
                    </Space>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * 主应用组件 - Bento Grid 布局
 */
function App() {
  const [selectedKey, setSelectedKey] = useState('chat');
  const [collapsed, setCollapsed] = useState(false);
  const [selectedOpportunity, setSelectedOpportunity] = useState<BusinessOpportunity | null>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const handleOpportunitySelect = (opportunity: BusinessOpportunity) => {
    setSelectedOpportunity(opportunity);
  };

  const handleWorkflowStart = (workflowType: string, params: any) => {
    console.log('Workflow started:', workflowType, params);
  };

  const userMenu = (
    <Menu
      style={{
        background: 'var(--color-bg-container-elevated)',
        border: '1px solid var(--color-border-base)',
      }}
    >
      <Menu.Item key="profile" icon={<UserOutlined />}>
        个人资料
      </Menu.Item>
      <Menu.Item key="settings" icon={<SettingOutlined />}>
        设置
      </Menu.Item>
      <Menu.Divider style={{ borderColor: 'var(--color-border-secondary)' }} />
      <Menu.Item key="logout" danger>
        退出登录
      </Menu.Item>
    </Menu>
  );

  const renderContent = () => {
    switch (selectedKey) {
      case 'chat':
        return (
          <AIChat
            onOpportunitySelect={handleOpportunitySelect}
            onWorkflowStart={handleWorkflowStart}
          />
        );
      case 'dashboard':
        return <DashboardView />;
      case 'opportunities':
        return <OpportunitiesView onSelectOpportunity={handleOpportunitySelect} />;
      case 'trends':
        return <TrendsView />;
      case 'agents':
        return <AgentsView />;
      default:
        return <DashboardView />;
    }
  };

  return (
    <Layout style={{ minHeight: '100vh', background: 'var(--color-bg-base)' }}>
      {/* 侧边栏 - Bento 风格 */}
      <Sider
        theme="dark"
        width={collapsed ? 72 : 220}
        style={{
          background: 'var(--color-bg-base-elevated)',
          borderRight: '1px solid var(--color-border-base)',
          transition: 'all var(--transition-base)',
        }}
        collapsed={collapsed}
      >
        {/* Logo 区域 */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 20px',
            borderBottom: '1px solid var(--color-border-base)',
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 'var(--radius-xl)',
              background: 'var(--gradient-accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'var(--shadow-glow-sm)',
              flexShrink: 0,
            }}
          >
            <ThunderboltOutlined style={{ color: '#fff', fontSize: 18 }} />
          </div>
          {!collapsed && (
            <div style={{ marginLeft: 12, overflow: 'hidden' }}>
              <Title
                level={5}
                style={{
                  margin: 0,
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-semibold)',
                  whiteSpace: 'nowrap',
                }}
              >
                Opportunity Miner
              </Title>
              <Text
                style={{
                  color: 'var(--color-text-tertiary)',
                  fontSize: 'var(--font-size-xs)',
                }}
              >
                AI Native
              </Text>
            </div>
          )}
        </div>

        {/* 菜单 */}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems.map((item) => ({
            ...item,
            icon: React.cloneElement(item.icon as React.ReactElement, {
              style: { fontSize: 18 },
            }),
          }))}
          onClick={({ key }) => setSelectedKey(key)}
          style={{
            background: 'transparent',
            borderRight: 'none',
            padding: 'var(--spacing-3) 0',
          }}
        />

        {/* 底部 - 收起/展开按钮 */}
        <div
          style={{
            position: 'absolute',
            bottom: 24,
            left: 0,
            right: 0,
            padding: `0 ${collapsed ? 16 : 20}px`,
          }}
        >
          <Button
            icon={collapsed ? <MenuOutlined /> : <MenuOutlined rotate={90} />}
            onClick={() => setCollapsed(!collapsed)}
            size="small"
            block
            style={{
              borderColor: 'var(--color-border-base)',
              color: 'var(--color-text-secondary)',
              background: 'var(--glass-light)',
            }}
          >
            {!collapsed && (collapsed ? '展开' : '收起')}
          </Button>
        </div>
      </Sider>

      {/* 主内容区 */}
      <Layout>
        {/* 顶部 Header */}
        <Header
          style={{
            padding: '0 24px',
            background: 'var(--color-bg-base-elevated)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--color-border-base)',
            height: 56,
          }}
        >
          <Title
            level={5}
            style={{
              margin: 0,
              color: 'var(--color-text-primary)',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 'var(--font-weight-semibold)',
            }}
          >
            {menuItems.find((item) => item.key === selectedKey)?.label}
          </Title>

          <Space size="large">
            {/* 通知 */}
            <Tooltip title="通知">
              <Badge
                count={notifications.length}
                offset={[-3, 3]}
                style={{ backgroundColor: 'var(--color-accent-500)' }}
              >
                <Button
                  type="text"
                  icon={<BellOutlined style={{ fontSize: 18, color: 'var(--color-text-secondary)' }} />}
                  style={{ background: 'transparent' }}
                />
              </Badge>
            </Tooltip>

            {/* 用户头像 */}
            <Dropdown overlay={userMenu} trigger={['click']} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar
                  style={{
                    background: 'var(--gradient-accent)',
                    width: 32,
                    height: 32,
                  }}
                  icon={<UserOutlined style={{ color: '#fff' }} />}
                />
                {!collapsed && (
                  <Text style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-sm)' }}>
                    用户
                  </Text>
                )}
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* 内容区域 - Bento Grid 容器 */}
        <Content
          style={{
            margin: 16,
            padding: 24,
            background: 'var(--color-bg-base-elevated)',
            borderRadius: 'var(--radius-2xl)',
            border: '1px solid var(--color-border-base)',
            overflow: 'auto',
          }}
        >
          {renderContent()}
        </Content>
      </Layout>

      {/* 机会详情抽屉 */}
      <Drawer
        title={selectedOpportunity?.title}
        placement="right"
        width={520}
        open={!!selectedOpportunity}
        onClose={() => setSelectedOpportunity(null)}
        styles={{
          header: {
            background: 'var(--color-bg-container)',
            borderBottom: '1px solid var(--color-border-base)',
          },
          body: {
            background: 'var(--color-bg-base)',
            padding: 0,
          },
        }}
      >
        {selectedOpportunity && (
          <OpportunityCard opportunity={selectedOpportunity} />
        )}
      </Drawer>
    </Layout>
  );
}

export default App;
