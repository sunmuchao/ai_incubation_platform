import React from 'react';
import { Table, Tag, Button, Space, Descriptions, Collapse, Statistic, Row, Col, Alert, Tree, Avatar, List, Rate, Card as AntCard } from 'antd';
import {
  UserOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  TeamOutlined,
  RocketOutlined,
  WarningOutlined,
  NotificationOutlined,
} from '@ant-design/icons';
import { ChatMessage } from '../services/chatService';
import designTokens from '../styles/designTokens';

const { Panel } = Collapse;

interface GenerativeUIProps {
  message: ChatMessage;
  onActionSelect?: (action: string, data?: any) => void;
}

/**
 * Generative UI 动态渲染引擎 - Bento Grid 风格
 *
 * 根据 AI 响应的 action 类型动态生成最适合的 UI 组件
 */
export const GenerativeUI: React.FC<GenerativeUIProps> = ({ message, onActionSelect }) => {
  const { action, data } = message;

  if (!action || !data) {
    return null;
  }

  switch (action) {
    case 'search_tasks':
      return <TaskList data={data} onActionSelect={onActionSelect} />;

    case 'search_workers':
      return <WorkerList data={data} onActionSelect={onActionSelect} />;

    case 'post_task':
      return <TaskCreated data={data} onActionSelect={onActionSelect} />;

    case 'match_workers':
      return <MatchResults data={data} onActionSelect={onActionSelect} />;

    case 'get_task_status':
      return <TaskStatus data={data} onActionSelect={onActionSelect} />;

    case 'get_stats':
      return <DashboardStats data={data} onActionSelect={onActionSelect} />;

    case 'verify_delivery':
      return <VerificationResult data={data} onActionSelect={onActionSelect} />;

    case 'notification':
      return <NotificationPanel data={data} onActionSelect={onActionSelect} />;

    case 'team_match':
      return <TeamComposition data={data} onActionSelect={onActionSelect} />;

    default:
      return <GenericData data={data} />;
  }
};

// ==================== 任务列表组件 ====================

interface TaskListProps {
  data: any;
  onActionSelect?: (action: string, data?: any) => void;
}

const TaskList: React.FC<TaskListProps> = ({ data, onActionSelect }) => {
  const tasks = data.tasks || [];

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: any) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{text}</span>
          {record.priority === 'urgent' && <Tag color="red" style={{ borderRadius: designTokens.radii.sm }}>紧急</Tag>}
          {record.priority === 'high' && <Tag color="orange" style={{ borderRadius: designTokens.radii.sm }}>高优先级</Tag>}
        </Space>
      ),
    },
    {
      title: '报酬',
      dataIndex: 'reward_amount',
      key: 'reward_amount',
      render: (amount: number) => (
        <span style={{ color: designTokens.colors.green[600], fontWeight: 600 }}>
          ¥{amount}
        </span>
      ),
    },
    {
      title: '交互类型',
      dataIndex: 'interaction_type',
      key: 'interaction_type',
      render: (type: string) => {
        const typeMap: Record<string, { text: string; color: string }> = {
          physical: { text: '线下', color: 'blue' },
          digital: { text: '线上', color: 'green' },
          hybrid: { text: '混合', color: 'purple' },
        };
        const config = typeMap[type] || { text: type, color: 'default' };
        return <Tag color={config.color} style={{ borderRadius: designTokens.radii.sm }}>{config.text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          published: { text: '已发布', color: 'blue' },
          in_progress: { text: '进行中', color: 'processing' },
          completed: { text: '已完成', color: 'success' },
          cancelled: { text: '已取消', color: 'default' },
        };
        const config = statusMap[status] || { text: status, color: 'default' };
        return <Tag color={config.color} style={{ borderRadius: designTokens.radii.sm }}>{config.text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => onActionSelect?.('view_task', record)}
            style={{ color: designTokens.colors.blue[600] }}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => onActionSelect?.('match_worker', record)}
            style={{ color: designTokens.colors.blue[600] }}
          >
            匹配
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ marginTop: 12 }}>
      <AntCard
        size="small"
        title={<span style={{ fontWeight: 600 }}>找到 {data.total || tasks.length} 个任务</span>}
        style={{
          borderRadius: designTokens.radii.lg,
          boxShadow: designTokens.shadows.card,
          border: `1px solid ${designTokens.semanticColors.border.subtle}`,
        }}
      >
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 5, size: 'small' }}
          size="small"
          scroll={{ x: 800 }}
          showHeader={true}
        />
      </AntCard>
    </div>
  );
};

// ==================== 工人列表组件 ====================

interface WorkerListProps {
  data: any;
  onActionSelect?: (action: string, data?: any) => void;
}

const WorkerList: React.FC<WorkerListProps> = ({ data, onActionSelect }) => {
  const workers = data.workers || [];

  return (
    <div style={{ marginTop: 12 }}>
      <AntCard
        size="small"
        title={<span style={{ fontWeight: 600 }}>找到 {data.total || workers.length} 个工人</span>}
        style={{
          borderRadius: designTokens.radii.lg,
          boxShadow: designTokens.shadows.card,
          border: `1px solid ${designTokens.semanticColors.border.subtle}`,
        }}
      >
        <List
          dataSource={workers}
          renderItem={(worker: any) => (
            <List.Item
              actions={[
                <Button
                  key="view"
                  type="link"
                  size="small"
                  onClick={() => onActionSelect?.('view_worker', worker)}
                  style={{ color: designTokens.colors.blue[600] }}
                >
                  查看
                </Button>,
                <Button
                  key="hire"
                  type="primary"
                  size="small"
                  onClick={() => onActionSelect?.('hire_worker', worker)}
                  style={{
                    borderRadius: designTokens.radii.md,
                    background: designTokens.colors.blue[600],
                  }}
                >
                  雇佣
                </Button>,
              ]}
              style={{
                padding: `${designTokens.spacing.md} 0`,
                borderBottom: `1px solid ${designTokens.semanticColors.border.subtle}`,
              }}
            >
              <List.Item.Meta
                avatar={
                  <Avatar
                    style={{
                      backgroundColor: designTokens.colors.blue[500],
                      boxShadow: designTokens.shadows.card,
                    }}
                    icon={<UserOutlined />}
                  />
                }
                title={
                  <Space>
                    <span style={{ fontWeight: 600 }}>{worker.name}</span>
                    <Tag color="gold" style={{ borderRadius: designTokens.radii.sm }}>Lv.{worker.level}</Tag>
                  </Space>
                }
                description={
                  <Space direction="vertical" size={0}>
                    <Space>
                      <Rate disabled defaultValue={worker.rating} allowHalf />
                      <span style={{ color: designTokens.semanticColors.text.secondary }}>{worker.rating}分</span>
                    </Space>
                    <Space size="small">
                      <Tag style={{ borderRadius: designTokens.radii.sm }}>{worker.completed_tasks}单完成</Tag>
                      <Tag style={{ borderRadius: designTokens.radii.sm }}>{(worker.success_rate * 100).toFixed(0)}%成功率</Tag>
                    </Space>
                    {worker.skills && (
                      <Space size="small" wrap>
                        {Object.keys(worker.skills).slice(0, 5).map((skill: string) => (
                          <Tag key={skill} color="blue" style={{ borderRadius: designTokens.radii.sm }}>{skill}</Tag>
                        ))}
                      </Space>
                    )}
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </AntCard>
    </div>
  );
};

// ==================== 任务发布成功组件 ====================

interface TaskCreatedProps {
  data: any;
  onActionSelect?: (action: string, data?: any) => void;
}

const TaskCreated: React.FC<TaskCreatedProps> = ({ data, onActionSelect }) => {
  const task = data.task || data;

  return (
    <div style={{ marginTop: 12 }}>
      <Alert
        message="任务发布成功！"
        description={
          <Descriptions column={1} size="small">
            <Descriptions.Item label="任务 ID">{task.id}</Descriptions.Item>
            <Descriptions.Item label="任务名称">{task.title}</Descriptions.Item>
            <Descriptions.Item label="报酬">
              <span style={{ color: designTokens.colors.green[600], fontWeight: 600 }}>
                ¥{task.reward_amount}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color="blue" style={{ borderRadius: designTokens.radii.sm }}>已发布</Tag>
            </Descriptions.Item>
          </Descriptions>
        }
        type="success"
        showIcon
        icon={<CheckCircleOutlined />}
        style={{
          borderRadius: designTokens.radii.lg,
          border: `1px solid ${designTokens.colors.green[200]}`,
        }}
      />
      <Space style={{ marginTop: 12 }}>
        <Button
          type="primary"
          onClick={() => onActionSelect?.('match_workers', { task_id: task.id })}
          style={{
            borderRadius: designTokens.radii.md,
            background: designTokens.colors.blue[600],
          }}
        >
          匹配工人
        </Button>
        <Button
          onClick={() => onActionSelect?.('view_task', { id: task.id })}
          style={{
            borderRadius: designTokens.radii.md,
            border: `1px solid ${designTokens.semanticColors.border.default}`,
          }}
        >
          查看任务
        </Button>
      </Space>
    </div>
  );
};

// ==================== 匹配结果组件 ====================

interface MatchResultsProps {
  data: any;
  onActionSelect?: (action: string, data?: any) => void;
}

const MatchResults: React.FC<MatchResultsProps> = ({ data, onActionSelect }) => {
  const matches = data.matches || [];

  return (
    <div style={{ marginTop: 12 }}>
      <AntCard
        size="small"
        title={
          <Space>
            <span style={{ fontWeight: 600 }}>匹配结果</span>
            <Tag color="blue" style={{ borderRadius: designTokens.radii.sm }}>共{matches.length}个匹配</Tag>
          </Space>
        }
        style={{
          borderRadius: designTokens.radii.lg,
          boxShadow: designTokens.shadows.card,
          border: `1px solid ${designTokens.semanticColors.border.subtle}`,
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {matches.map((match: any, index: number) => (
            <div
              key={match.worker_id || index}
              style={{
                padding: designTokens.spacing.md,
                borderRadius: designTokens.radii.lg,
                border: `1px solid ${designTokens.semanticColors.border.subtle}`,
                backgroundColor: match.confidence >= 0.8 ? designTokens.colors.green[50] : '#ffffff',
                transition: designTokens.transitions.all,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = designTokens.shadows.cardHover;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Space>
                  <Avatar
                    style={{
                      backgroundColor: getConfidenceColor(match.confidence),
                      boxShadow: designTokens.shadows.card,
                    }}
                  >
                    {index + 1}
                  </Avatar>
                  <div>
                    <div style={{ fontWeight: 600 }}>{match.worker_name}</div>
                    <Space size="small">
                      <Tag
                        color={getConfidenceColor(match.confidence)}
                        style={{ borderRadius: designTokens.radii.sm }}
                      >
                        匹配度 {Math.round(match.confidence * 100)}%
                      </Tag>
                      <Tag style={{ borderRadius: designTokens.radii.sm }}>{match.rating}分</Tag>
                    </Space>
                  </div>
                </Space>
                <Button
                  type={match.confidence >= 0.8 ? 'primary' : 'default'}
                  size="small"
                  onClick={() =>
                    onActionSelect?.('assign_worker', {
                      task_id: data.task_id,
                      worker_id: match.worker_id,
                    })
                  }
                  style={{
                    borderRadius: designTokens.radii.md,
                  }}
                >
                  {match.confidence >= 0.8 ? '自动分配' : '分配'}
                </Button>
              </Space>
            </div>
          ))}
        </Space>
        {data.auto_assigned && (
          <Alert
            message="已自动分配给最佳匹配工人"
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
            style={{
              marginTop: 8,
              borderRadius: designTokens.radii.lg,
            }}
          />
        )}
      </AntCard>
    </div>
  );
};

// ==================== 任务状态组件 ====================

interface TaskStatusProps {
  data: any;
  onActionSelect?: (action: string, data?: any) => void;
}

const TaskStatus: React.FC<TaskStatusProps> = ({ data, onActionSelect }) => {
  const task = data.task || {};

  return (
    <div style={{ marginTop: 12 }}>
      <AntCard
        size="small"
        title={<span style={{ fontWeight: 600 }}>任务状态</span>}
        style={{
          borderRadius: designTokens.radii.lg,
          boxShadow: designTokens.shadows.card,
          border: `1px solid ${designTokens.semanticColors.border.subtle}`,
        }}
      >
        <Descriptions column={1} size="small">
          <Descriptions.Item label="任务 ID">{task.id}</Descriptions.Item>
          <Descriptions.Item label="任务名称">{task.title}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <StatusTag status={task.status} />
          </Descriptions.Item>
          <Descriptions.Item label="当前工人">
            {task.worker_id || '暂无'}
          </Descriptions.Item>
          <Descriptions.Item label="报酬">¥{task.reward_amount}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatDate(task.created_at)}</Descriptions.Item>
        </Descriptions>
        <Space style={{ marginTop: 12 }}>
          <Button
            onClick={() => onActionSelect?.('view_task', { id: task.id })}
            style={{
              borderRadius: designTokens.radii.md,
              border: `1px solid ${designTokens.semanticColors.border.default}`,
            }}
          >
            查看详情
          </Button>
          {task.status === 'published' && (
            <Button
              danger
              onClick={() => onActionSelect?.('cancel_task', { id: task.id })}
              style={{ borderRadius: designTokens.radii.md }}
            >
              取消任务
            </Button>
          )}
        </Space>
      </AntCard>
    </div>
  );
};

// ==================== 统计数据组件 ====================

interface DashboardStatsProps {
  data: any;
  onActionSelect?: (action: string, data?: any) => void;
}

const DashboardStats: React.FC<DashboardStatsProps> = ({ data }) => {
  const taskStats = data.task_stats || {};
  const workerStats = data.worker_stats || {};

  return (
    <div style={{ marginTop: 12 }}>
      <AntCard
        size="small"
        title={<span style={{ fontWeight: 600 }}>平台统计</span>}
        style={{
          borderRadius: designTokens.radii.lg,
          boxShadow: designTokens.shadows.card,
          border: `1px solid ${designTokens.semanticColors.border.subtle}`,
        }}
      >
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div style={{
              padding: designTokens.spacing.lg,
              borderRadius: designTokens.radii.lg,
              backgroundColor: designTokens.colors.blue[50],
              border: `1px solid ${designTokens.colors.blue[100]}`,
            }}>
              <Statistic
                title="总任务数"
                value={taskStats.total || 0}
                prefix={<RocketOutlined style={{ color: designTokens.colors.blue[600] }} />}
                valueStyle={{ fontSize: 24, fontWeight: 700 }}
              />
            </div>
          </Col>
          <Col span={6}>
            <div style={{
              padding: designTokens.spacing.lg,
              borderRadius: designTokens.radii.lg,
              backgroundColor: designTokens.colors.green[50],
              border: `1px solid ${designTokens.colors.green[100]}`,
            }}>
              <Statistic
                title="总工人数"
                value={workerStats.total_workers || 0}
                prefix={<TeamOutlined style={{ color: designTokens.colors.green[600] }} />}
                valueStyle={{ fontSize: 24, fontWeight: 700 }}
              />
            </div>
          </Col>
          <Col span={6}>
            <div style={{
              padding: designTokens.spacing.lg,
              borderRadius: designTokens.radii.lg,
              backgroundColor: designTokens.colors.amber[50],
              border: `1px solid ${designTokens.colors.amber[100]}`,
            }}>
              <Statistic
                title="平均评分"
                value={workerStats.avg_rating || 0}
                precision={1}
                prefix={<UserOutlined style={{ color: designTokens.colors.amber[600] }} />}
                valueStyle={{ fontSize: 24, fontWeight: 700 }}
              />
            </div>
          </Col>
          <Col span={6}>
            <div style={{
              padding: designTokens.spacing.lg,
              borderRadius: designTokens.radii.lg,
              backgroundColor: designTokens.colors.purple[50],
              border: `1px solid ${designTokens.colors.purple[100]}`,
            }}>
              <Statistic
                title="完成率"
                value={taskStats.completion_rate || 0}
                precision={1}
                suffix="%"
                prefix={<CheckCircleOutlined style={{ color: designTokens.colors.purple[600] }} />}
                valueStyle={{ fontSize: 24, fontWeight: 700 }}
              />
            </div>
          </Col>
        </Row>
      </AntCard>
    </div>
  );
};

// ==================== 验证结果组件 ====================

interface VerificationResultProps {
  data: any;
  onActionSelect?: (action: string, data?: any) => void;
}

const VerificationResult: React.FC<VerificationResultProps> = ({ data, onActionSelect }) => {
  const passed = data.passed || data.confidence >= 0.9;
  const confidence = data.confidence || 0;

  return (
    <div style={{ marginTop: 12 }}>
      <Alert
        message={passed ? '验证通过' : '验证未通过'}
        description={
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <div>置信度：<span style={{ fontWeight: 600 }}>{Math.round(confidence * 100)}%</span></div>
            {data.details && (
              <Collapse size="small" ghost>
                <Panel header="查看详情" key="details">
                  <pre style={{
                    fontSize: 12,
                    margin: 0,
                    padding: designTokens.spacing.md,
                    backgroundColor: designTokens.semanticColors.background.secondary,
                    borderRadius: designTokens.radii.md,
                    overflow: 'auto',
                  }}>
                    {JSON.stringify(data.details, null, 2)}
                  </pre>
                </Panel>
              </Collapse>
            )}
          </Space>
        }
        type={passed ? 'success' : 'warning'}
        showIcon
        icon={passed ? <CheckCircleOutlined /> : <WarningOutlined />}
        style={{
          borderRadius: designTokens.radii.lg,
        }}
      />
      {passed && (
        <Space style={{ marginTop: 12 }}>
          <Button
            type="primary"
            onClick={() => onActionSelect?.('approve_task', data)}
            style={{
              borderRadius: designTokens.radii.md,
              background: designTokens.colors.green[600],
            }}
          >
            批准完成
          </Button>
        </Space>
      )}
    </div>
  );
};

// ==================== 通知面板组件 ====================

interface NotificationPanelProps {
  data: any;
  onActionSelect?: (action: string, data?: any) => void;
}

const NotificationPanel: React.FC<NotificationPanelProps> = ({ data, onActionSelect }) => {
  const notifications = data.notifications || [data];

  return (
    <div style={{ marginTop: 12 }}>
      <AntCard
        size="small"
        title={
          <Space>
            <NotificationOutlined style={{ color: designTokens.colors.blue[600] }} />
            <span style={{ fontWeight: 600 }}>通知</span>
          </Space>
        }
        style={{
          borderRadius: designTokens.radii.lg,
          boxShadow: designTokens.shadows.card,
          border: `1px solid ${designTokens.semanticColors.border.subtle}`,
        }}
      >
        <List
          dataSource={notifications}
          renderItem={(notification: any) => (
            <List.Item style={{ padding: `${designTokens.spacing.md} 0` }}>
              <Alert
                message={notification.title || '新通知'}
                description={notification.content || notification.message}
                type={notification.type || 'info'}
                showIcon
                style={{
                  width: '100%',
                  borderRadius: designTokens.radii.lg,
                }}
              />
            </List.Item>
          )}
        />
      </AntCard>
    </div>
  );
};

// ==================== 团队组成组件 ====================

interface TeamCompositionProps {
  data: any;
  onActionSelect?: (action: string, data?: any) => void;
}

const TeamComposition: React.FC<TeamCompositionProps> = ({ data }) => {
  return (
    <div style={{ marginTop: 12 }}>
      <AntCard
        size="small"
        title={
          <Space>
            <TeamOutlined style={{ color: designTokens.colors.blue[600] }} />
            <span style={{ fontWeight: 600 }}>团队组成</span>
          </Space>
        }
        style={{
          borderRadius: designTokens.radii.lg,
          boxShadow: designTokens.shadows.card,
          border: `1px solid ${designTokens.semanticColors.border.subtle}`,
        }}
      >
        <Descriptions column={1} size="small">
          <Descriptions.Item label="团队 ID">{data.team_id}</Descriptions.Item>
          <Descriptions.Item label="项目 ID">{data.project_id}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <StatusTag status={data.status} />
          </Descriptions.Item>
          <Descriptions.Item label="总信誉分">{data.total_reputation}</Descriptions.Item>
        </Descriptions>
        {data.members && (
          <AntCard
            size="small"
            title="成员"
            style={{
              marginTop: 8,
              backgroundColor: designTokens.semanticColors.background.secondary,
              borderRadius: designTokens.radii.md,
            }}
          >
            <List
              dataSource={Object.entries(data.members)}
              renderItem={([workerId, role]: [string, any]) => (
                <List.Item style={{ padding: `${designTokens.spacing.sm} 0` }}>
                  <Space>
                    <Avatar
                      icon={<UserOutlined />}
                      style={{ backgroundColor: designTokens.colors.blue[500] }}
                    />
                    <span>{workerId}</span>
                    <Tag style={{ borderRadius: designTokens.radii.sm }}>{role}</Tag>
                  </Space>
                </List.Item>
              )}
            />
          </AntCard>
        )}
      </AntCard>
    </div>
  );
};

// ==================== 通用数据展示组件 ====================

interface GenericDataProps {
  data: any;
}

const GenericData: React.FC<GenericDataProps> = ({ data }) => {
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{
        padding: designTokens.spacing.lg,
        borderRadius: designTokens.radii.lg,
        backgroundColor: designTokens.semanticColors.background.secondary,
        border: `1px solid ${designTokens.semanticColors.border.subtle}`,
      }}>
        <pre style={{
          fontSize: 12,
          overflow: 'auto',
          margin: 0,
          fontFamily: designTokens.typography.fontFamily.mono,
          color: designTokens.semanticColors.text.secondary,
        }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    </div>
  );
};

// ==================== 工具函数和组件 ====================

const StatusTag: React.FC<{ status: string }> = ({ status }) => {
  const statusMap: Record<string, { text: string; color: string }> = {
    published: { text: '已发布', color: 'blue' },
    in_progress: { text: '进行中', color: 'processing' },
    completed: { text: '已完成', color: 'success' },
    cancelled: { text: '已取消', color: 'default' },
    pending: { text: '待处理', color: 'warning' },
    active: { text: '活跃', color: 'green' },
    inactive: { text: '未激活', color: 'default' },
  };
  const config = statusMap[status] || { text: status, color: 'default' };
  return (
    <Tag
      color={config.color}
      style={{
        borderRadius: designTokens.radii.sm,
        fontWeight: 500,
      }}
    >
      {config.text}
    </Tag>
  );
};

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return designTokens.colors.green[600];
  if (confidence >= 0.6) return designTokens.colors.blue[600];
  if (confidence >= 0.4) return designTokens.colors.amber[600];
  return designTokens.colors.red[600];
}

function formatDate(dateString: string): string {
  if (!dateString) return '-';
  try {
    return new Date(dateString).toLocaleString('zh-CN');
  } catch {
    return dateString;
  }
}

export default GenerativeUI;
