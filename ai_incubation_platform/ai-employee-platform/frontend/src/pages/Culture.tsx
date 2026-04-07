/**
 * 组织文化页面
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
  Rate,
  Avatar,
  Timeline,
  Statistic,
} from 'antd';
import {
  StarOutlined,
  TrophyOutlined,
  GiftOutlined,
  PlusOutlined,
  HeartOutlined,
  CalendarOutlined,
  UsergroupAddOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import { useCulture } from '@/hooks/useCulture';
import { useAuth } from '@/hooks/useAuth';
import type { Recognition, Badge, TeamEvent } from '@/services/cultureApi';
import dayjs from 'dayjs';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const Culture: React.FC = () => {
  const { user } = useAuth();
  const {
    cultureValuesQuery,
    employeeRecognitionsQuery,
    giveRecognitionMutation,
    badgesQuery,
    employeeBadgesQuery,
    teamEventsQuery,
    joinTeamEventMutation,
    pulsesQuery,
    submitPulseResponseMutation,
    cultureDashboardQuery,
    createTeamEventMutation,
  } = useCulture();

  const [recognitionModalOpen, setRecognitionModalOpen] = useState(false);
  const [eventModalOpen, setEventModalOpen] = useState(false);
  const [pulseModalOpen, setPulseModalOpen] = useState(false);
  const [recognitionForm] = Form.useForm();
  const [eventForm] = Form.useForm();
  const [pulseForm] = Form.useForm();

  const employeeId = user?.id || '';
  const tenantId = user?.tenant_id || '';

  // 获取数据
  const { data: cultureValues, isLoading: loadingValues } = cultureValuesQuery(tenantId);
  const { data: recognitions, isLoading: loadingRecognitions } = employeeRecognitionsQuery(employeeId, tenantId);
  const { data: badges, isLoading: loadingBadges } = badgesQuery(tenantId);
  const { data: employeeBadges } = employeeBadgesQuery(employeeId);
  const { data: teamEvents, isLoading: loadingEvents } = teamEventsQuery(tenantId);
  const { data: pulses } = pulsesQuery(tenantId);
  cultureDashboardQuery(tenantId);

  // 给予认可
  const handleGiveRecognition = (values: {
    recipient_id: string;
    recognition_type: string;
    category: string;
    title: string;
    description: string;
    points?: number;
  }) => {
    giveRecognitionMutation.mutate(
      {
        tenant_id: tenantId,
        giver_id: employeeId,
        ...values,
      },
      {
        onSuccess: () => {
          message.success('认可已发送');
          setRecognitionModalOpen(false);
          recognitionForm.resetFields();
        },
        onError: () => {
          message.error('发送认可失败');
        },
      }
    );
  };

  // 参加活动
  const handleJoinEvent = (eventId: string) => {
    joinTeamEventMutation.mutate(
      { eventId, employeeId },
      {
        onSuccess: () => {
          message.success('报名成功');
        },
        onError: () => {
          message.error('报名失败');
        },
      }
    );
  };

  // 提交脉冲调查
  const handleSubmitPulse = (values: { pulse_id: string; response_value: number; response_text?: string }) => {
    submitPulseResponseMutation.mutate(
      {
        pulse_id: values.pulse_id,
        respondent_id: employeeId,
        response_value: values.response_value,
        response_text: values.response_text,
      },
      {
        onSuccess: () => {
          message.success('调查已提交');
          setPulseModalOpen(false);
          pulseForm.resetFields();
        },
        onError: () => {
          message.error('提交调查失败');
        },
      }
    );
  };

  // 获取价值观类型标签
  const getValueTypeTag = (valueType: string) => {
    const typeMap: Record<string, { color: string; text: string }> = {
      core: { color: 'red', text: '核心价值观' },
      behavioral: { color: 'blue', text: '行为准则' },
      operational: { color: 'green', text: '运营理念' },
      aspirational: { color: 'purple', text: '愿景目标' },
    };
    const config = typeMap[valueType] || { color: 'default', text: valueType };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 获取徽章层级颜色
  const getBadgeTierColor = (tier: string) => {
    const tierMap: Record<string, string> = {
      bronze: '#cd7f32',
      silver: '#c0c0c0',
      gold: '#ffd700',
      platinum: '#e5e4e2',
      diamond: '#b9f2ff',
    };
    return tierMap[tier] || '#d9d9d9';
  };

  // 获取活动状态标签
  const getEventStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      scheduled: { color: 'blue', text: '已安排' },
      ongoing: { color: 'green', text: '进行中' },
      completed: { color: 'default', text: '已结束' },
      cancelled: { color: 'red', text: '已取消' },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Title level={2}>组织文化</Title>
          <Paragraph type="secondary">
            构建积极向上的组织文化，促进员工成长与企业发展
          </Paragraph>
        </div>

        {/* 快捷操作 */}
        <Card>
          <Row gutter={16}>
            <Col span={6}>
              <Button
                block
                icon={<HeartOutlined />}
                onClick={() => setRecognitionModalOpen(true)}
              >
                发送认可
              </Button>
            </Col>
            <Col span={6}>
              <Button
                block
                icon={<CalendarOutlined />}
                onClick={() => setEventModalOpen(true)}
              >
                创建活动
              </Button>
            </Col>
            <Col span={6}>
              <Button
                block
                icon={<DashboardOutlined />}
                onClick={() => setPulseModalOpen(true)}
                disabled={!pulses?.length}
              >
                文化脉冲
              </Button>
            </Col>
            <Col span={6}>
              <Button block icon={<UsergroupAddOutlined />}>
                文化建设
              </Button>
            </Col>
          </Row>
        </Card>

        {/* 文化概览 */}
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title="核心价值观"
                value={cultureValues?.length || 0}
                prefix={<StarOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="获得认可"
                value={recognitions?.length || 0}
                prefix={<HeartOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="收集徽章"
                value={employeeBadges?.length || 0}
                prefix={<TrophyOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="团队活动"
                value={teamEvents?.filter((e: any) => e.status === 'scheduled' || e.status === 'ongoing').length || 0}
                prefix={<GiftOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={16}>
          {/* 核心价值观 */}
          <Col span={12}>
            <Card
              title={<><StarOutlined /> 核心价值观</>}
              className="culture-values-card"
            >
              {loadingValues ? (
                <Empty description="加载中..." />
              ) : !cultureValues?.length ? (
                <Empty description="暂无核心价值观" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <List
                  itemLayout="horizontal"
                  dataSource={cultureValues}
                  renderItem={(item: any) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space>
                            <Text strong>{item.name}</Text>
                            {getValueTypeTag(item.value_type)}
                          </Space>
                        }
                        description={
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <Text type="secondary">{item.description}</Text>
                            {item.behavioral_indicators?.length > 0 && (
                              <div>
                                <Text type="secondary">行为指标：</Text>
                                <ul>
                                  {item.behavioral_indicators.slice(0, 2).map((indicator: any, i: number) => (
                                    <li key={i}>{indicator}</li>
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
              )}
            </Card>
          </Col>

          {/* 最近认可 */}
          <Col span={12}>
            <Card title={<><HeartOutlined /> 收到的认可</>}>
              {loadingRecognitions ? (
                <Empty description="加载中..." />
              ) : !recognitions?.length ? (
                <Empty description="暂无认可记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <Timeline
                  items={(recognitions || []).map((recognition: Recognition) => ({
                    key: recognition.id,
                    color: 'red',
                    children: (
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <Text strong>{recognition.title}</Text>
                          <Tag color="gold">
                            <StarOutlined /> +{recognition.points}
                          </Tag>
                        </Space>
                        <Text type="secondary">{recognition.description}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          来自：{recognition.giver_id} | {dayjs(recognition.created_at).format('YYYY-MM-DD')}
                        </Text>
                      </Space>
                    ),
                  }))}
                />
              )}
            </Card>
          </Col>
        </Row>

        {/* 徽章墙 */}
        <Card
          title={<><TrophyOutlined /> 徽章墙</>}
          extra={
            <Text type="secondary">
              已收集 {employeeBadges?.length || 0} / {badges?.length || 0}
            </Text>
          }
        >
          {loadingBadges ? (
            <Empty description="加载中..." />
          ) : !badges?.length ? (
            <Empty description="暂无徽章" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Row gutter={16}>
              {(badges || []).map((badge: Badge) => {
                const earned = employeeBadges?.some((b: any) => b.id === badge.id);
                return (
                  <Col span={4} key={badge.id}>
                    <Card
                      size="small"
                      hoverable
                      style={{
                        textAlign: 'center',
                        opacity: earned ? 1 : 0.5,
                        borderColor: getBadgeTierColor(badge.tier),
                      }}
                    >
                      <Avatar
                        size={64}
                        style={{
                          backgroundColor: getBadgeTierColor(badge.tier),
                          marginBottom: 8,
                        }}
                        icon={<TrophyOutlined />}
                      />
                      <Text strong>{badge.name}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {badge.category}
                      </Text>
                      <br />
                      {earned ? (
                        <Tag color="green">已获得</Tag>
                      ) : (
                        <Tag>未解锁</Tag>
                      )}
                    </Card>
                  </Col>
                );
              })}
            </Row>
          )}
        </Card>

        {/* 团队活动 */}
        <Card
          title={<><GiftOutlined /> 团队活动</>}
          extra={
            <Button type="link" onClick={() => setEventModalOpen(true)}>
              <PlusOutlined /> 创建活动
            </Button>
          }
        >
          {loadingEvents ? (
            <Empty description="加载中..." />
          ) : !teamEvents?.length ? (
            <Empty description="暂无团队活动" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Row gutter={16}>
              {(teamEvents || [])
                .filter((e: any) => e.status === 'scheduled' || e.status === 'ongoing')
                .map((event: TeamEvent) => (
                  <Col span={8} key={event.id}>
                    <Card
                      size="small"
                      title={event.title}
                      extra={getEventStatusTag(event.status)}
                      actions={[
                        <Button
                          type="primary"
                          size="small"
                          onClick={() => handleJoinEvent(event.id)}
                        >
                          报名
                        </Button>,
                      ]}
                    >
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Text type="secondary">{event.description}</Text>
                        <Text type="secondary">
                          <CalendarOutlined />{' '}
                          {dayjs(event.start_time).format('YYYY-MM-DD HH:mm')} -{' '}
                          {dayjs(event.end_time).format('HH:mm')}
                        </Text>
                        {event.location && (
                          <Text type="secondary">地点：{event.location}</Text>
                        )}
                      </Space>
                    </Card>
                  </Col>
                ))}
            </Row>
          )}
        </Card>

        {/* 文化脉冲调查 */}
        {pulses?.some((p: any) => p.status === 'active') && (
          <Card title={<><DashboardOutlined /> 文化脉冲调查</>}>
            <List
              itemLayout="horizontal"
              dataSource={pulses?.filter((p: any) => p.status === 'active') || []}
              renderItem={(pulse: any) => (
                <List.Item
                  actions={[
                    <Button
                      type="primary"
                      size="small"
                      onClick={() => {
                        pulseForm.setFieldsValue({ pulse_id: pulse.id });
                        setPulseModalOpen(true);
                      }}
                    >
                      参与调查
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={<Text strong>{pulse.title}</Text>}
                    description={
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Text type="secondary">{pulse.description}</Text>
                        <Text type="secondary">
                          截止时间：{dayjs(pulse.end_date).format('YYYY-MM-DD')}
                        </Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        )}
      </Space>

      {/* 发送认可弹窗 */}
      <Modal
        title="发送认可"
        open={recognitionModalOpen}
        onOk={() => recognitionForm.submit()}
        onCancel={() => setRecognitionModalOpen(false)}
        confirmLoading={giveRecognitionMutation.isPending}
      >
        <Form form={recognitionForm} layout="vertical" onFinish={handleGiveRecognition}>
          <Form.Item
            name="recipient_id"
            label="接收人"
            rules={[{ required: true, message: '请选择接收人' }]}
          >
            <Select placeholder="选择同事">
              <Select.Option value="emp1">张三</Select.Option>
              <Select.Option value="emp2">李四</Select.Option>
              <Select.Option value="emp3">王五</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="recognition_type"
            label="认可类型"
            rules={[{ required: true, message: '请选择认可类型' }]}
          >
            <Select>
              <Select.Option value="peer">同事认可</Select.Option>
              <Select.Option value="manager">上级认可</Select.Option>
              <Select.Option value="team">团队认可</Select.Option>
              <Select.Option value="company">公司认可</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="category"
            label="认可类别"
            rules={[{ required: true, message: '请选择认可类别' }]}
          >
            <Select>
              <Select.Option value="teamwork">团队协作</Select.Option>
              <Select.Option value="innovation">创新突破</Select.Option>
              <Select.Option value="excellence">卓越表现</Select.Option>
              <Select.Option value="dedication">敬业奉献</Select.Option>
              <Select.Option value="mentorship">辅导帮助</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder="简短描述认可原因" />
          </Form.Item>
          <Form.Item
            name="description"
            label="详细说明"
            rules={[{ required: true, message: '请输入详细说明' }]}
          >
            <TextArea rows={4} placeholder="详细描述被认可的行为或成就..." />
          </Form.Item>
          <Form.Item name="points" label="奖励积分">
            <Input type="number" defaultValue={10} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建活动弹窗 */}
      <Modal
        title="创建团队活动"
        open={eventModalOpen}
        onOk={() => eventForm.submit()}
        onCancel={() => setEventModalOpen(false)}
        confirmLoading={createTeamEventMutation.isPending}
      >
        <Form form={eventForm} layout="vertical" onFinish={(values) => {
          createTeamEventMutation.mutate(
            {
              tenant_id: tenantId,
              team_id: values.team_id,
              organizer_id: employeeId,
              ...values,
            },
            {
              onSuccess: () => {
                message.success('活动创建成功');
                setEventModalOpen(false);
                eventForm.resetFields();
              },
              onError: () => {
                message.error('创建活动失败');
              },
            }
          );
        }}>
          <Form.Item
            name="team_id"
            label="所属团队"
            rules={[{ required: true, message: '请选择团队' }]}
          >
            <Select>
              <Select.Option value="team1">技术部</Select.Option>
              <Select.Option value="team2">产品部</Select.Option>
              <Select.Option value="team3">运营部</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="event_type"
            label="活动类型"
            rules={[{ required: true, message: '请选择活动类型' }]}
          >
            <Select>
              <Select.Option value="team_building">团建</Select.Option>
              <Select.Option value="celebration">庆祝活动</Select.Option>
              <Select.Option value="workshop">工作坊</Select.Option>
              <Select.Option value="social">社交聚会</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="title"
            label="活动标题"
            rules={[{ required: true, message: '请输入活动标题' }]}
          >
            <Input placeholder="给活动起个名字" />
          </Form.Item>
          <Form.Item
            name="description"
            label="活动描述"
            rules={[{ required: true, message: '请输入活动描述' }]}
          >
            <TextArea rows={3} placeholder="描述活动内容和亮点..." />
          </Form.Item>
          <Form.Item
            name="start_time"
            label="开始时间"
            rules={[{ required: true, message: '请选择开始时间' }]}
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="end_time"
            label="结束时间"
            rules={[{ required: true, message: '请选择结束时间' }]}
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="location" label="活动地点">
            <Input placeholder="活动地址或线上链接" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 脉冲调查弹窗 */}
      <Modal
        title="文化脉冲调查"
        open={pulseModalOpen}
        onOk={() => pulseForm.submit()}
        onCancel={() => setPulseModalOpen(false)}
        confirmLoading={submitPulseResponseMutation.isPending}
      >
        <Form form={pulseForm} layout="vertical" onFinish={handleSubmitPulse}>
          <Form.Item
            name="pulse_id"
            hidden
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="response_value"
            label="您的评分"
            rules={[{ required: true, message: '请评分' }]}
          >
            <Rate />
          </Form.Item>
          <Form.Item name="response_text" label="意见或建议">
            <TextArea rows={4} placeholder="分享您的想法和建议..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Culture;
