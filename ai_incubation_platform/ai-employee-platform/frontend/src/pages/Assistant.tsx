/**
 * 智能助手页面
 */
import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  List,
  Tag,
  Button,
  Space,
  Divider,
  Timeline,
  Empty,
  Spin,
  Tabs,
  Badge,
  Modal,
  message,
  Statistic,
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  PlusOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import { useAssistant } from '@/hooks/useAssistant';
import { useAuth } from '@/hooks/useAuth';
import type { TaskRecommendation, MeetingSummary, DailyReport } from '@/services/assistantApi';
import dayjs from 'dayjs';

const { Title, Paragraph, Text } = Typography;

const Assistant: React.FC = () => {
  const { user } = useAuth();
  const {
    taskRecommendationsQuery,
    scheduledTasksQuery,
    completeTaskMutation,
    upcomingMeetingsQuery,
    meetingSummariesQuery,
    dailyReportsQuery,
    generateDailyReportMutation,
    insightsQuery,
  } = useAssistant();

  const [activeTab, setActiveTab] = useState('tasks');
  const [reportModalOpen, setReportModalOpen] = useState(false);

  // 获取数据
  const employeeId = user?.id || '';
  const { data: taskRecommendations, isLoading: loadingTasks } = taskRecommendationsQuery(employeeId);
  const { data: scheduledTasks, isLoading: loadingScheduled } = scheduledTasksQuery(employeeId);
  const { data: upcomingMeetings, isLoading: loadingMeetings } = upcomingMeetingsQuery(employeeId);
  const { data: meetingSummaries, isLoading: loadingSummaries } = meetingSummariesQuery(employeeId);
  const { data: dailyReports, isLoading: loadingReports } = dailyReportsQuery(employeeId);
  const { data: insights, isLoading: loadingInsights } = insightsQuery(employeeId);

  // 完成任务
  const handleCompleteTask = (taskId: string) => {
    completeTaskMutation.mutate(
      { taskId, employeeId },
      {
        onSuccess: () => {
          message.success('任务已完成');
        },
        onError: () => {
          message.error('完成任务失败');
        },
      }
    );
  };

  // 生成日报
  const handleGenerateReport = () => {
    generateDailyReportMutation.mutate(
      { employeeId },
      {
        onSuccess: () => {
          message.success('日报已生成');
          setReportModalOpen(false);
        },
        onError: () => {
          message.error('生成日报失败');
        },
      }
    );
  };

  // 获取优先级标签颜色
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      case 'low':
        return 'green';
      default:
        return 'default';
    }
  };

  // 任务列表内容
  const TaskListContent = () => {
    if (loadingTasks || loadingScheduled) {
      return <Spin />;
    }

    if (!taskRecommendations?.length && !scheduledTasks?.length) {
      return <Empty description="暂无推荐任务" />;
    }

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 推荐任务 */}
        <Card title={<><ThunderboltOutlined /> 智能推荐任务</>} size="small">
          <List
            itemLayout="horizontal"
            dataSource={taskRecommendations || []}
            renderItem={(item: TaskRecommendation) => (
              <List.Item
                actions={[
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckCircleOutlined />}
                    onClick={() => handleCompleteTask(item.id)}
                    loading={completeTaskMutation.isPending}
                  >
                    完成
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{item.title}</Text>
                      <Tag color={getPriorityColor(item.priority)}>{item.priority}</Tag>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text type="secondary">{item.description}</Text>
                      <Space>
                        {item.due_date && (
                          <Text type="secondary">
                            <ClockCircleOutlined /> 截止：{dayjs(item.due_date).format('YYYY-MM-DD')}
                          </Text>
                        )}
                        <Text type="secondary">
                          预估：{item.estimated_hours}小时
                        </Text>
                        {item.related_skills?.map((skill) => (
                          <Tag key={skill} color="blue">{skill}</Tag>
                        ))}
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>

        {/* 已安排任务 */}
        <Card title={<><CalendarOutlined /> 今日已安排</>} size="small">
          <List
            itemLayout="horizontal"
            dataSource={scheduledTasks || []}
            renderItem={(item: TaskRecommendation) => (
              <List.Item
                actions={[
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckCircleOutlined />}
                    onClick={() => handleCompleteTask(item.id)}
                    loading={completeTaskMutation.isPending}
                  >
                    完成
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{item.title}</Text>
                      <Tag color={getPriorityColor(item.priority)}>{item.priority}</Tag>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text type="secondary">{item.description}</Text>
                      <Space>
                        <Text type="secondary">
                          预估：{item.estimated_hours}小时
                        </Text>
                        {item.related_skills?.map((skill) => (
                          <Tag key={skill} color="blue">{skill}</Tag>
                        ))}
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      </Space>
    );
  };

  // 会议内容
  const MeetingContent = () => {
    if (loadingMeetings || loadingSummaries) {
      return <Spin />;
    }

    if (!upcomingMeetings?.length && !meetingSummaries?.length) {
      return <Empty description="暂无会议信息" />;
    }

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 即将开始的会议 */}
        <Card title={<><VideoCameraOutlined /> 即将开始</>} size="small">
          <Timeline
            items={(upcomingMeetings || []).map((meeting: any, index) => ({
              key: index,
              color: 'blue',
              children: (
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong>{meeting.title}</Text>
                    <Text type="secondary">
                      <CalendarOutlined /> {dayjs(meeting.start_time).format('YYYY-MM-DD HH:mm')}
                    </Text>
                    {meeting.participants?.length > 0 && (
                      <Text type="secondary">
                        参会人：{meeting.participants.join(', ')}
                      </Text>
                    )}
                    <Button size="small" icon={<FileTextOutlined />}>
                      查看议程
                    </Button>
                  </Space>
                </Card>
              ),
            }))}
          />
        </Card>

        {/* 会议摘要 */}
        <Card title={<><FileTextOutlined /> 历史会议摘要</>} size="small">
          <List
            itemLayout="horizontal"
            dataSource={meetingSummaries || []}
            renderItem={(item: MeetingSummary) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{item.title}</Text>
                      <Text type="secondary">{dayjs(item.date).format('YYYY-MM-DD')}</Text>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Paragraph ellipsis={{ rows: 2 }} type="secondary">
                        {item.summary}
                      </Paragraph>
                      {item.key_points?.length > 0 && (
                        <div>
                          <Text type="secondary">关键点：</Text>
                          <ul>
                            {item.key_points.slice(0, 3).map((point, i) => (
                              <li key={i}>{point}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      </Space>
    );
  };

  // 报告内容
  const ReportContent = () => {
    if (loadingReports) {
      return <Spin />;
    }

    if (!dailyReports?.length) {
      return (
        <Empty
          description="暂无工作简报"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleGenerateReport}
            loading={generateDailyReportMutation.isPending}
          >
            生成今日报告
          </Button>
        </Empty>
      );
    }

    return (
      <Space direction="vertical" style={{ width: '100%' }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleGenerateReport}
          loading={generateDailyReportMutation.isPending}
          style={{ marginBottom: 16 }}
        >
          生成今日报告
        </Button>

        <List
          itemLayout="horizontal"
          dataSource={dailyReports || []}
          renderItem={(item: DailyReport) => (
            <Card size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="完成任务"
                      value={item.completed_tasks?.length || 0}
                      suffix="个"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="工作时长"
                      value={item.hours_worked || 0}
                      suffix="小时"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="参加会议"
                      value={item.meetings_attended || 0}
                      suffix="场"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="日期"
                      value={dayjs(item.date).format('MM-DD')}
                    />
                  </Col>
                </Row>
                <Divider style={{ margin: '12px 0' }} />
                {item.highlights?.length > 0 && (
                  <div>
                    <Text strong>亮点：</Text>
                    <ul>
                      {item.highlights.map((h, i) => (
                        <li key={i}>{h}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {item.blockers?.length > 0 && (
                  <div>
                    <Text strong>阻碍：</Text>
                    <ul>
                      {item.blockers.map((b, i) => (
                        <li key={i}>{b}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </Space>
            </Card>
          )}
        />
      </Space>
    );
  };

  // 洞察内容
  const InsightsContent = () => {
    if (loadingInsights) {
      return <Spin />;
    }

    if (!insights?.length) {
      return <Empty description="暂无智能洞察" />;
    }

    return (
      <List
        grid={{ gutter: 16, column: 2 }}
        dataSource={insights || []}
        renderItem={(item: any) => (
          <Col>
            <Card>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong type={item.type === 'warning' ? 'danger' : 'success'}>
                  {item.category}
                </Text>
                <Paragraph>{item.content}</Paragraph>
                {item.suggestions?.length > 0 && (
                  <div>
                    <Text type="secondary">建议：</Text>
                    <ul>
                      {item.suggestions.map((s: string, i: number) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </Space>
            </Card>
          </Col>
        )}
      />
    );
  };

  const tabItems = [
    {
      key: 'tasks',
      label: (
        <span>
          <CheckCircleOutlined />
          任务管理
          {(taskRecommendations?.length || 0) + (scheduledTasks?.length || 0) > 0 && (
            <Badge count={(taskRecommendations?.length || 0) + (scheduledTasks?.length || 0)} style={{ marginLeft: 8 }} />
          )}
        </span>
      ),
      children: <TaskListContent />,
    },
    {
      key: 'meetings',
      label: (
        <span>
          <VideoCameraOutlined />
          会议助理
          {(upcomingMeetings?.length || 0) > 0 && (
            <Badge count={upcomingMeetings?.length || 0} style={{ marginLeft: 8 }} />
          )}
        </span>
      ),
      children: <MeetingContent />,
    },
    {
      key: 'reports',
      label: (
        <span>
          <FileTextOutlined />
          工作简报
        </span>
      ),
      children: <ReportContent />,
    },
    {
      key: 'insights',
      label: (
        <span>
          <DashboardOutlined />
          智能洞察
        </span>
      ),
      children: <InsightsContent />,
    },
  ];

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Title level={2}>智能助手</Title>
          <Paragraph type="secondary">
            AI 驱动的工作助手，帮助您更高效地完成工作
          </Paragraph>
        </div>

        {/* 快捷操作 */}
        <Card>
          <Space>
            <Button
              icon={<PlusOutlined />}
              onClick={() => setReportModalOpen(true)}
            >
              生成日报
            </Button>
            <Button icon={<CalendarOutlined />}>
              优化日程
            </Button>
            <Button icon={<ThunderboltOutlined />}>
              推荐任务
            </Button>
          </Space>
        </Card>

        {/* 主内容区 */}
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Space>

      {/* 生成日报弹窗 */}
      <Modal
        title="生成工作日报"
        open={reportModalOpen}
        onOk={handleGenerateReport}
        onCancel={() => setReportModalOpen(false)}
        confirmLoading={generateDailyReportMutation.isPending}
      >
        <Paragraph type="secondary">
          系统将自动收集您今天的工作数据，生成包含完成任务、会议记录、工作亮点等内容的日报。
        </Paragraph>
      </Modal>
    </div>
  );
};

export default Assistant;
