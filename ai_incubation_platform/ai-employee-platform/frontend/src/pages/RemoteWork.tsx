/**
 * 远程工作页面
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
  message,
  Empty,
  Divider,
  Statistic,
  Progress,
  Avatar,
  DatePicker,
  Badge,
  Switch,
} from 'antd';
import {
  HomeOutlined,
  UsergroupAddOutlined,
  CoffeeOutlined,
  VideoCameraOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  PlusOutlined,
  DashboardOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons';
import { useRemoteWork } from '@/hooks/useRemoteWork';
import { useAuth } from '@/hooks/useAuth';
import type { PresenceStatus, VirtualWorkspace } from '@/services/remoteWorkApi';
import dayjs from 'dayjs';
import 'dayjs/plugin/duration';

dayjs.extend(require('dayjs/plugin/duration'));

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const RemoteWork: React.FC = () => {
  const { user } = useAuth();
  const {
    activeSessionQuery,
    startSessionMutation,
    endSessionMutation,
    presenceQuery,
    allPresenceQuery,
    setPresenceMutation,
    workspacesQuery,
    createWorkspaceMutation,
    joinWorkspaceMutation,
    teamEventsQuery,
    rsvpEventMutation,
    createEventMutation,
    activeWaterCoolersQuery,
    startWaterCoolerMutation,
  } = useRemoteWork();

  const [workspaceModalOpen, setWorkspaceModalOpen] = useState(false);
  const [eventModalOpen, setEventModalOpen] = useState(false);
  const [workspaceForm] = Form.useForm();
  const [eventForm] = Form.useForm();

  const employeeId = user?.id || '';

  // 获取数据
  const { data: activeSession } = activeSessionQuery(employeeId);
  const { data: presence } = presenceQuery(employeeId);
  const { data: allPresence, isLoading: loadingAllPresence } = allPresenceQuery;
  const { data: workspaces, isLoading: loadingWorkspaces } = workspacesQuery();
  const { data: teamEvents, isLoading: loadingEvents } = teamEventsQuery(undefined, true);
  const { data: waterCoolers, isLoading: loadingWaterCoolers } = activeWaterCoolersQuery;

  // 开始工作会话
  const handleStartSession = (workMode: string) => {
    startSessionMutation.mutate(
      { employeeId, workMode },
      {
        onSuccess: () => {
          message.success('工作会话已开始');
        },
        onError: () => {
          message.error('开始工作会话失败');
        },
      }
    );
  };

  // 结束工作会话
  const handleEndSession = () => {
    if (activeSession?.id) {
      endSessionMutation.mutate(
        { sessionId: activeSession.id },
        {
          onSuccess: () => {
            message.success('工作会话已结束');
          },
          onError: () => {
            message.error('结束工作会话失败');
          },
        }
      );
    }
  };

  // 设置在线状态
  const handleSetPresence = (status: string, statusMessage?: string) => {
    setPresenceMutation.mutate(
      {
        employeeId,
        status,
        workMode: activeSession?.work_mode || 'remote',
        statusMessage,
      },
      {
        onSuccess: () => {
          message.success('状态已更新');
        },
        onError: () => {
          message.error('更新状态失败');
        },
      }
    );
  };

  // 加入工作空间
  const handleJoinWorkspace = (workspaceId: string) => {
    joinWorkspaceMutation.mutate(
      { workspaceId, employeeId },
      {
        onSuccess: () => {
          message.success('已加入工作空间');
        },
        onError: () => {
          message.error('加入工作空间失败');
        },
      }
    );
  };

  // 创建虚拟工作空间
  const handleCreateWorkspace = (values: any) => {
    createWorkspaceMutation.mutate(
      {
        name: values.name,
        owner_id: employeeId,
        workspace_type: values.workspace_type,
        capacity: values.capacity,
        description: values.description,
        is_private: values.is_private,
      },
      {
        onSuccess: () => {
          message.success('工作空间创建成功');
          setWorkspaceModalOpen(false);
          workspaceForm.resetFields();
        },
        onError: () => {
          message.error('创建工作空间失败');
        },
      }
    );
  };

  // 创建活动
  const handleCreateEvent = (values: any) => {
    createEventMutation.mutate(
      {
        title: values.title,
        organizer_id: employeeId,
        event_type: values.event_type,
        start_time: values.start_time,
        duration_minutes: values.duration_minutes,
        description: values.description,
      },
      {
        onSuccess: () => {
          message.success('活动创建成功');
          setEventModalOpen(false);
          eventForm.resetFields();
        },
        onError: () => {
          message.error ('创建活动失败');
        },
      }
    );
  };

  // RSVP 活动
  const handleRsvpEvent = (eventId: string, status: 'going' | 'not_going' | 'maybe') => {
    rsvpEventMutation.mutate(
      { eventId, employeeId, status },
      {
        onSuccess: () => {
          message.success('已回复活动');
        },
        onError: () => {
          message.error('回复活动失败');
        },
      }
    );
  };

  // 启动虚拟茶水间
  const handleStartWaterCooler = () => {
    startWaterCoolerMutation.mutate(
      { initiatorId: employeeId, topic: '休闲聊天' },
      {
        onSuccess: () => {
          message.success('茶水间已开启');
        },
        onError: () => {
          message.error('开启茶水间失败');
        },
      }
    );
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string; icon?: React.ReactNode }> = {
      available: { color: 'success', text: '可用', icon: <CheckCircleOutlined /> },
      busy: { color: 'error', text: '忙碌' },
      away: { color: 'warning', text: '离开' },
      offline: { color: 'default', text: '离线' },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color} icon={config.icon}>{config.text}</Tag>;
  };

  // 获取工作模式标签
  const getWorkModeTag = (workMode: string) => {
    const modeMap: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
      remote: { color: 'blue', text: '远程', icon: <HomeOutlined /> },
      office: { color: 'green', text: '办公室', icon: <EnvironmentOutlined /> },
      hybrid: { color: 'purple', text: '混合', icon: <EnvironmentOutlined /> },
    };
    const config = modeMap[workMode] || { color: 'default', text: workMode, icon: null };
    return (
      <Tag color={config.color}>
        {config.icon} {config.text}
      </Tag>
    );
  };

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Title level={2}>远程工作</Title>
          <Paragraph type="secondary">
            管理远程工作状态，与团队成员保持连接
          </Paragraph>
        </div>

        {/* 工作状态控制 */}
        <Card title={<><DashboardOutlined /> 工作状态</>}>
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="当前状态"
                value={presence?.status || 'offline'}
                valueRender={() => getStatusTag(presence?.status || 'offline')}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="工作模式"
                value={activeSession?.work_mode || '-'}
                valueRender={() => getWorkModeTag(activeSession?.work_mode || 'remote')}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="工作时长"
                value={activeSession?.start_time ? dayjs().diff(dayjs(activeSession.start_time), 'minute') : 0}
                suffix="分钟"
              />
            </Col>
          </Row>
          <Divider />
          <Space>
            {!activeSession ? (
              <>
                <Text>开始工作：</Text>
                <Button
                  icon={<HomeOutlined />}
                  onClick={() => handleStartSession('remote')}
                  loading={startSessionMutation.isPending}
                >
                  远程办公
                </Button>
                <Button
                  icon={<EnvironmentOutlined />}
                  onClick={() => handleStartSession('office')}
                  loading={startSessionMutation.isPending}
                >
                  办公室
                </Button>
              </>
            ) : (
              <Button
                danger
                icon={<CheckCircleOutlined />}
                onClick={handleEndSession}
                loading={endSessionMutation.isPending}
              >
                结束工作
              </Button>
            )}
            <Divider type="vertical" />
            <Text>状态切换：</Text>
            <Button
              size="small"
              type={presence?.status === 'available' ? 'primary' : 'default'}
              onClick={() => handleSetPresence('available')}
            >
              可用
            </Button>
            <Button
              size="small"
              type={presence?.status === 'busy' ? 'primary' : 'default'}
              onClick={() => handleSetPresence('busy')}
            >
              忙碌
            </Button>
            <Button
              size="small"
              type={presence?.status === 'away' ? 'primary' : 'default'}
              onClick={() => handleSetPresence('away')}
            >
              离开
            </Button>
          </Space>
        </Card>

        <Row gutter={16}>
          {/* 团队成员在线状态 */}
          <Col span={12}>
            <Card
              title={<><UsergroupAddOutlined /> 团队成员</>}
              extra={
                <Badge count={allPresence?.filter((p: any) => p.status === 'available').length || 0}
                  color="green"
                  style={{ marginRight: 8 }}
                />
              }
            >
              {loadingAllPresence ? (
                <Empty description="加载中..." />
              ) : !allPresence?.length ? (
                <Empty description="暂无团队成员" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <List
                  itemLayout="horizontal"
                  dataSource={allPresence}
                  renderItem={(item: PresenceStatus) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={
                          <Badge status={item.status === 'available' ? 'success' : item.status === 'busy' ? 'error' : 'default'}>
                            <Avatar icon={<UsergroupAddOutlined />} />
                          </Badge>
                        }
                        title={
                          <Space>
                            <Text strong>{item.employee_id}</Text>
                            {getStatusTag(item.status)}
                          </Space>
                        }
                        description={
                          <Space>
                            {getWorkModeTag(item.work_mode)}
                            {item.status_message && <Text type="secondary">{item.status_message}</Text>}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              )}
            </Card>
          </Col>

          {/* 虚拟工作空间 */}
          <Col span={12}>
            <Card
              title={<><VideoCameraOutlined /> 虚拟工作空间</>}
              extra={
                <Button
                  type="link"
                  icon={<PlusOutlined />}
                  onClick={() => setWorkspaceModalOpen(true)}
                >
                  创建
                </Button>
              }
            >
              {loadingWorkspaces ? (
                <Empty description="加载中..." />
              ) : !workspaces?.length ? (
                <Empty description="暂无工作空间" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <List
                  itemLayout="horizontal"
                  dataSource={workspaces}
                  renderItem={(item: VirtualWorkspace) => {
                    const occupancy = (item.current_occupants / item.capacity) * 100;
                    return (
                      <List.Item
                        actions={[
                          <Button
                            key="join"
                            size="small"
                            type="primary"
                            onClick={() => handleJoinWorkspace(item.id)}
                          >
                            加入
                          </Button>,
                        ]}
                      >
                        <List.Item.Meta
                          title={
                            <Space>
                              <Text strong>{item.name}</Text>
                              <Tag>{item.workspace_type}</Tag>
                              {item.is_private && <Tag color="gold">私有</Tag>}
                            </Space>
                          }
                          description={
                            <Space direction="vertical" style={{ width: '100%' }}>
                              <Text type="secondary">{item.description}</Text>
                              <Progress
                                percent={occupancy}
                                format={() => `${item.current_occupants}/${item.capacity}`}
                                size="small"
                              />
                            </Space>
                          }
                        />
                      </List.Item>
                    );
                  }}
                />
              )}
            </Card>
          </Col>
        </Row>

        <Row gutter={16}>
          {/* 团队活动 */}
          <Col span={12}>
            <Card
              title={<><ClockCircleOutlined />  upcoming 活动</>}
              extra={
                <Button
                  type="link"
                  icon={<PlusOutlined />}
                  onClick={() => setEventModalOpen(true)}
                >
                  创建
                </Button>
              }
            >
              {loadingEvents ? (
                <Empty description="加载中..." />
              ) : !teamEvents?.length ? (
                <Empty description="暂无即将开始的活动" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <List
                  itemLayout="horizontal"
                  dataSource={teamEvents}
                  renderItem={(item: any) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space>
                            <Text strong>{item.title}</Text>
                            <Tag>{item.event_type}</Tag>
                          </Space>
                        }
                        description={
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <Text type="secondary">
                              {item.start_time ? dayjs(item.start_time).format('YYYY-MM-DD HH:mm') : '时间待定'}
                            </Text>
                            <Text type="secondary">{item.description}</Text>
                            <Space>
                              <Button
                                size="small"
                                type="primary"
                                onClick={() => handleRsvpEvent(item.id, 'going')}
                              >
                                参加
                              </Button>
                              <Button
                                size="small"
                                onClick={() => handleRsvpEvent(item.id, 'maybe')}
                              >
                                待定
                              </Button>
                              <Button
                                size="small"
                                danger
                                onClick={() => handleRsvpEvent(item.id, 'not_going')}
                              >
                                不参加
                              </Button>
                            </Space>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              )}
            </Card>
          </Col>

          {/* 虚拟茶水间 */}
          <Col span={12}>
            <Card
              title={<><CoffeeOutlined /> 虚拟茶水间</>}
              extra={
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleStartWaterCooler}
                  loading={startWaterCoolerMutation.isPending}
                >
                  开启聊天
                </Button>
              }
            >
              {loadingWaterCoolers ? (
                <Empty description="加载中..." />
              ) : !waterCoolers?.length ? (
                <Empty
                  description="暂无活跃的茶水间聊天"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              ) : (
                <List
                  itemLayout="horizontal"
                  dataSource={waterCoolers}
                  renderItem={(item: any) => (
                    <List.Item
                      actions={[
                        <Button key="join" size="small" type="primary">
                          加入
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={<Text strong>{item.topic || '休闲聊天'}</Text>}
                        description={
                          <Space>
                            <Text type="secondary">
                              发起人：{item.initiator_id}
                            </Text>
                            <Text type="secondary">
                              参与者：{item.participants?.length || 0}人
                            </Text>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              )}
            </Card>
          </Col>
        </Row>
      </Space>

      {/* 创建虚拟工作空间弹窗 */}
      <Modal
        title="创建虚拟工作空间"
        open={workspaceModalOpen}
        onOk={() => workspaceForm.submit()}
        onCancel={() => setWorkspaceModalOpen(false)}
        confirmLoading={createWorkspaceMutation.isPending}
      >
        <Form form={workspaceForm} layout="vertical" onFinish={handleCreateWorkspace}>
          <Form.Item
            name="name"
            label="空间名称"
            rules={[{ required: true, message: '请输入空间名称' }]}
          >
            <Input placeholder="例如：前端专注室" />
          </Form.Item>
          <Form.Item
            name="workspace_type"
            label="空间类型"
            rules={[{ required: true, message: '请选择空间类型' }]}
          >
            <Select>
              <Select.Option value="meeting">会议室</Select.Option>
              <Select.Option value="focus">专注室</Select.Option>
              <Select.Option value="collaboration">协作空间</Select.Option>
              <Select.Option value="social">社交空间</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="capacity" label="容量">
            <Input type="number" defaultValue={10} />
          </Form.Item>
          <Form.Item name="description" label="空间描述">
            <TextArea rows={2} placeholder="描述这个空间的用途..." />
          </Form.Item>
          <Form.Item name="is_private" label="私有空间" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建活动弹窗 */}
      <Modal
        title="创建团队活动"
        open={eventModalOpen}
        onOk={() => eventForm.submit()}
        onCancel={() => setEventModalOpen(false)}
        confirmLoading={createEventMutation.isPending}
      >
        <Form form={eventForm} layout="vertical" onFinish={handleCreateEvent}>
          <Form.Item
            name="title"
            label="活动标题"
            rules={[{ required: true, message: '请输入活动标题' }]}
          >
            <Input placeholder="例如：周五欢乐时光" />
          </Form.Item>
          <Form.Item
            name="event_type"
            label="活动类型"
            rules={[{ required: true, message: '请选择活动类型' }]}
          >
            <Select>
              <Select.Option value="meeting">会议</Select.Option>
              <Select.Option value="social">社交</Select.Option>
              <Select.Option value="team_building">团建</Select.Option>
              <Select.Option value="workshop">工作坊</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="start_time"
            label="开始时间"
            rules={[{ required: true, message: '请选择开始时间' }]}
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="duration_minutes" label="时长（分钟）">
            <Input type="number" defaultValue={60} />
          </Form.Item>
          <Form.Item name="description" label="活动描述">
            <TextArea rows={3} placeholder="描述活动内容和流程..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default RemoteWork;
