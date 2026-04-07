/**
 * 绩效管理页面
 */
import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  Button,
  Space,
  List,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  message,
  Empty,
  Divider,
  Progress,
  Statistic,
  Tabs,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  AimOutlined,
  FileTextOutlined,
  CalendarOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import { usePerformance } from '@/hooks/usePerformance';
import { useAuth } from '@/hooks/useAuth';
import type { ReviewCycle, PerformanceReview, Objective } from '@/services/performanceApi';
import dayjs from 'dayjs';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const Performance: React.FC = () => {
  const { user } = useAuth();
  const {
    reviewCyclesQuery,
    createReviewCycleMutation,
    launchReviewCycleMutation,
    completeReviewCycleMutation,
    employeeReviewsQuery,
    submitReviewMutation,
    employeeObjectivesQuery,
    createObjectiveMutation,
    performanceDashboardQuery,
  } = usePerformance();

  const [activeTab, setActiveTab] = useState('overview');
  const [cycleModalOpen, setCycleModalOpen] = useState(false);
  const [objectiveModalOpen, setObjectiveModalOpen] = useState(false);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [cycleForm] = Form.useForm();
  const [objectiveForm] = Form.useForm();
  const [reviewForm] = Form.useForm();

  const employeeId = user?.id || '';

  // 获取数据
  const { data: reviewCycles, isLoading: loadingCycles } = reviewCyclesQuery();
  const { data: reviews, isLoading: loadingReviews } = employeeReviewsQuery(employeeId);
  const { data: objectives, isLoading: loadingObjectives } = employeeObjectivesQuery(employeeId);
  performanceDashboardQuery([employeeId]);

  // 创建评估周期
  const handleCreateCycle = (values: any) => {
    createReviewCycleMutation.mutate(
      {
        name: values.name,
        start_date: values.start_date,
        end_date: values.end_date,
        review_type: values.review_type,
      },
      {
        onSuccess: () => {
          message.success('评估周期创建成功');
          setCycleModalOpen(false);
          cycleForm.resetFields();
        },
        onError: () => {
          message.error('创建评估周期失败');
        },
      }
    );
  };

  // 创建目标
  const handleCreateObjective = (values: any) => {
    createObjectiveMutation.mutate(
      {
        title: values.title,
        description: values.description,
        start_date: values.start_date,
        due_date: values.due_date,
        employee_id: employeeId,
      },
      {
        onSuccess: () => {
          message.success('目标创建成功');
          setObjectiveModalOpen(false);
          objectiveForm.resetFields();
        },
        onError: () => {
          message.error('创建目标失败');
        },
      }
    );
  };

  // 提交评估
  const handleSubmitReview = (reviewId: string) => {
    submitReviewMutation.mutate(reviewId, {
      onSuccess: () => {
        message.success('评估已提交');
        setReviewModalOpen(false);
        reviewForm.resetFields();
      },
      onError: () => {
        message.error('提交评估失败');
      },
    });
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string; icon?: React.ReactNode }> = {
      draft: { color: 'default', text: '草稿' },
      active: { color: 'processing', text: '进行中' },
      completed: { color: 'success', text: '已完成', icon: <CheckCircleOutlined /> },
      in_progress: { color: 'processing', text: '进行中', icon: <ClockCircleOutlined /> },
      submitted: { color: 'blue', text: '已提交' },
      on_track: { color: 'success', text: '正常', icon: <CheckCircleOutlined /> },
      at_risk: { color: 'warning', text: '有风险', icon: <ExclamationCircleOutlined /> },
      off_track: { color: 'error', text: '偏离轨道', icon: <ExclamationCircleOutlined /> },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color} icon={config.icon}>{config.text}</Tag>;
  };

  // 概览内容
  const OverviewContent = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 统计卡片 */}
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="进行中评估"
              value={reviews?.filter((r: any) => r.status === 'in_progress').length || 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成评估"
              value={reviews?.filter((r: any) => r.status === 'completed').length || 0}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="进行中的目标"
              value={objectives?.filter((o: any) => o.status === 'on_track' || o.status === 'at_risk').length || 0}
              prefix={<AimOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均完成度"
              value={
                objectives?.length
                  ? Math.round(
                      (objectives.reduce((sum, o) => sum + (o.progress || 0), 0) / objectives.length) * 100
                    ) / 100
                  : 0
              }
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 评估周期 */}
      <Card
        title={<><CalendarOutlined /> 评估周期</>}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCycleModalOpen(true)}
          >
            创建周期
          </Button>
        }
      >
        {loadingCycles ? (
          <Empty description="加载中..." />
        ) : !reviewCycles?.length ? (
          <Empty description="暂无评估周期" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={reviewCycles}
            renderItem={(item: ReviewCycle) => (
              <List.Item
                actions={[
                  item.status === 'draft' ? (
                    <Button
                      key="launch"
                      size="small"
                      type="primary"
                      onClick={() => launchReviewCycleMutation.mutate(item.id)}
                    >
                      启动
                    </Button>
                  ) : item.status === 'active' ? (
                    <Button
                      key="complete"
                      size="small"
                      onClick={() => completeReviewCycleMutation.mutate(item.id)}
                    >
                      完成
                    </Button>
                  ) : null,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{item.name}</Text>
                      {getStatusTag(item.status)}
                    </Space>
                  }
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text type="secondary">
                        {dayjs(item.start_date).format('YYYY-MM-DD')} - {dayjs(item.end_date).format('YYYY-MM-DD')}
                      </Text>
                      <Text type="secondary">类型：{item.review_type}</Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </Space>
  );

  // OKR 目标内容
  const ObjectivesContent = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Button
        type="primary"
        icon={<PlusOutlined />}
        onClick={() => setObjectiveModalOpen(true)}
        style={{ marginBottom: 16 }}
      >
        创建目标
      </Button>

      {loadingObjectives ? (
        <Empty description="加载中..." />
      ) : !objectives?.length ? (
        <Empty description="暂无目标" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Row gutter={16}>
          {(objectives || []).map((obj: Objective) => (
            <Col span={12} key={obj.id}>
              <Card
                title={obj.title}
                extra={getStatusTag(obj.status)}
                size="small"
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text type="secondary" style={{ fontSize: 14 }}>
                    {obj.description}
                  </Text>
                  <Divider style={{ margin: '12px 0' }} />
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Text type="secondary">进度</Text>
                      <Text strong>{obj.progress * 100}%</Text>
                    </Space>
                    <Progress
                      percent={obj.progress * 100}
                      status={
                        obj.status === 'completed'
                          ? 'success'
                          : obj.status === 'off_track'
                          ? 'exception'
                          : 'active'
                      }
                    />
                    <Space>
                      <Text type="secondary">截止：</Text>
                      <Text>{dayjs(obj.due_date).format('YYYY-MM-DD')}</Text>
                    </Space>
                  </Space>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </Space>
  );

  // 绩效评估内容
  const ReviewsContent = () => {
    return (
      <Space direction="vertical" style={{ width: '100%' }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setReviewModalOpen(true)}
          style={{ marginBottom: 16 }}
        >
          创建评估
        </Button>

        {loadingReviews ? (
          <Empty description="加载中..." />
        ) : !reviews?.length ? (
          <Empty description="暂无评估记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={reviews}
            renderItem={(item: PerformanceReview) => (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Text strong>评估 #{item.id.slice(-8)}</Text>
                    {getStatusTag(item.status)}
                    <Tag>{item.review_type}</Tag>
                  </Space>
                  <Divider style={{ margin: '12px 0' }} />
                  <Row gutter={16}>
                    <Col span={8}>
                      <Statistic
                        title="综合评分"
                        value={item.overall_score || 0}
                        precision={1}
                        suffix="/ 5"
                      />
                    </Col>
                    <Col span={16}>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        {item.strengths?.length > 0 && (
                          <div>
                            <Text strong>优势：</Text>
                            <ul>
                              {item.strengths.slice(0, 3).map((s, i) => (
                                <li key={i}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {item.areas_for_improvement?.length > 0 && (
                          <div>
                            <Text strong>待改进：</Text>
                            <ul>
                              {item.areas_for_improvement.slice(0, 3).map((a, i) => (
                                <li key={i}>{a}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </Space>
                    </Col>
                  </Row>
                  {item.status === 'in_progress' && (
                    <Button
                      type="primary"
                      onClick={() => handleSubmitReview(item.id)}
                      loading={submitReviewMutation.isPending}
                    >
                      提交评估
                    </Button>
                  )}
                </Space>
              </Card>
            )}
          />
        )}
      </Space>
    );
  };

  const tabItems = [
    {
      key: 'overview',
      label: (
        <span>
          <DashboardOutlined />
          概览
        </span>
      ),
      children: <OverviewContent />,
    },
    {
      key: 'objectives',
      label: (
        <span>
          <AimOutlined />
          OKR 目标
          <Badge count={objectives?.filter((o: any) => o.status === 'on_track').length || 0} style={{ marginLeft: 8 }} />
        </span>
      ),
      children: <ObjectivesContent />,
    },
    {
      key: 'reviews',
      label: (
        <span>
          <FileTextOutlined />
          绩效评估
          <Badge count={reviews?.filter((r: any) => r.status === 'in_progress').length || 0} style={{ marginLeft: 8 }} />
        </span>
      ),
      children: <ReviewsContent />,
    },
  ];

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Title level={2}>绩效管理</Title>
          <Paragraph type="secondary">
            设定目标、追踪进度、评估绩效，助力员工持续成长
          </Paragraph>
        </div>

        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Space>

      {/* 创建评估周期弹窗 */}
      <Modal
        title="创建评估周期"
        open={cycleModalOpen}
        onOk={() => cycleForm.submit()}
        onCancel={() => setCycleModalOpen(false)}
        confirmLoading={createReviewCycleMutation.isPending}
      >
        <Form form={cycleForm} layout="vertical" onFinish={handleCreateCycle}>
          <Form.Item
            name="name"
            label="周期名称"
            rules={[{ required: true, message: '请输入周期名称' }]}
          >
            <Input placeholder="例如：2024 年 Q1 绩效评估" />
          </Form.Item>
          <Form.Item
            name="review_type"
            label="评估类型"
            rules={[{ required: true, message: '请选择评估类型' }]}
          >
            <Select>
              <Select.Option value="360">360 度评估</Select.Option>
              <Select.Option value="manager">上级评估</Select.Option>
              <Select.Option value="peer">同事评估</Select.Option>
              <Select.Option value="self">自评</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="start_date"
            label="开始日期"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="end_date"
            label="结束日期"
            rules={[{ required: true, message: '请选择结束日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建目标弹窗 */}
      <Modal
        title="创建 OKR 目标"
        open={objectiveModalOpen}
        onOk={() => objectiveForm.submit()}
        onCancel={() => setObjectiveModalOpen(false)}
        confirmLoading={createObjectiveMutation.isPending}
      >
        <Form form={objectiveForm} layout="vertical" onFinish={handleCreateObjective}>
          <Form.Item
            name="title"
            label="目标标题"
            rules={[{ required: true, message: '请输入目标标题' }]}
          >
            <Input placeholder="简洁明了的目标描述" />
          </Form.Item>
          <Form.Item name="description" label="目标详情">
            <TextArea rows={3} placeholder="详细描述目标内容和期望结果..." />
          </Form.Item>
          <Form.Item
            name="start_date"
            label="开始日期"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="due_date"
            label="截止日期"
            rules={[{ required: true, message: '请选择截止日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建评估弹窗 */}
      <Modal
        title="创建绩效评估"
        open={reviewModalOpen}
        onOk={() => reviewForm.submit()}
        onCancel={() => setReviewModalOpen(false)}
      >
        <Form form={reviewForm} layout="vertical">
          <Form.Item
            name="review_type"
            label="评估类型"
            rules={[{ required: true, message: '请选择评估类型' }]}
          >
            <Select>
              <Select.Option value="360">360 度评估</Select.Option>
              <Select.Option value="manager">上级评估</Select.Option>
              <Select.Option value="peer">同事评估</Select.Option>
              <Select.Option value="self">自评</Select.Option>
            </Select>
          </Form.Item>
          <Paragraph type="secondary">
            评估表将包含评分、优势分析、待改进领域和发展目标等部分。
          </Paragraph>
        </Form>
      </Modal>
    </div>
  );
};

export default Performance;
