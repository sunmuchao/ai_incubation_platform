/**
 * 设置页面
 */
import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  Form,
  Input,
  Button,
  Space,
  Switch,
  Select,
  Divider,
  message,
  Avatar,
  List,
  Modal,
  Tag,
  Empty,
} from 'antd';
import {
  UserOutlined,
  BellOutlined,
  SecurityScanOutlined,
  SettingOutlined,
  UploadOutlined,
  ApiOutlined,
  DeleteOutlined,
  PlusOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { useAuth } from '@/hooks/useAuth';

const { Title, Paragraph, Text } = Typography;

const Settings: React.FC = () => {
  const { user, updateUser } = useAuth();
  const [profileForm] = Form.useForm();
  const [notificationForm] = Form.useForm();
  const [privacyForm] = Form.useForm();
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [passwordForm] = Form.useForm();
  const [apiKeys, setApiKeys] = useState<Array<{ id: string; name: string; key: string; createdAt: string; active: boolean }>>([]);
  const [apiKeyModalOpen, setApiKeyModalOpen] = useState(false);
  const [apiKeyForm] = Form.useForm();

  // 更新个人资料
  const handleProfileUpdate = (values: any) => {
    updateUser({
      ...user,
      ...values,
    });
    message.success('个人资料更新成功');
  };

  // 更新通知设置
  const handleNotificationUpdate = () => {
    message.success('通知设置已更新');
  };

  // 更新隐私设置
  const handlePrivacyUpdate = () => {
    message.success('隐私设置已更新');
  };

  // 修改密码
  const handlePasswordChange = (values: any) => {
    if (values.newPassword !== values.confirmPassword) {
      message.error('两次输入的新密码不一致');
      return;
    }
    // TODO: 调用修改密码 API
    message.success('密码修改成功');
    setPasswordModalOpen(false);
    passwordForm.resetFields();
  };

  // 生成新的 API 密钥
  const handleGenerateApiKey = (values: any) => {
    const newKey = {
      id: `key_${Date.now()}`,
      name: values.name,
      key: `sk_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`,
      createdAt: new Date().toISOString(),
      active: true,
    };
    setApiKeys([...apiKeys, newKey]);
    message.success('API 密钥生成成功');
    setApiKeyModalOpen(false);
    apiKeyForm.resetFields();
  };

  // 删除 API 密钥
  const handleDeleteApiKey = (id: string) => {
    setApiKeys(apiKeys.filter(key => key.id !== id));
    message.success('API 密钥已删除');
  };

  // 切换 API 密钥状态
  const handleToggleApiKey = (id: string) => {
    setApiKeys(apiKeys.map(key =>
      key.id === id ? { ...key, active: !key.active } : key
    ));
    message.success('API 密钥状态已更新');
  };

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Title level={2}>系统设置</Title>
          <Paragraph type="secondary">
            管理您的个人账号、通知偏好、隐私设置等
          </Paragraph>
        </div>

        <Row gutter={16}>
          {/* 左侧导航 */}
          <Col span={6}>
            <Card>
              <List
                dataSource={[
                  { key: 'profile', label: '个人资料', icon: <UserOutlined /> },
                  { key: 'notification', label: '通知设置', icon: <BellOutlined /> },
                  { key: 'privacy', label: '隐私与安全', icon: <SecurityScanOutlined /> },
                  { key: 'api', label: 'API 密钥', icon: <ApiOutlined /> },
                  { key: 'workspace', label: '工作区设置', icon: <SettingOutlined /> },
                ]}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      padding: '12px 16px',
                      borderRadius: 8,
                      transition: 'background 0.3s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = '#f5f5f5';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <Space>
                      {item.icon}
                      <Text>{item.label}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Col>

          {/* 右侧内容 */}
          <Col span={18}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* 个人资料 */}
              <Card
                title={<><UserOutlined /> 个人资料</>}
                extra={
                  <Button type="link" onClick={() => profileForm.submit()}>
                    保存修改
                  </Button>
                }
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
                    <Avatar size={80} icon={<UserOutlined />} />
                    <Button icon={<UploadOutlined />}>更换头像</Button>
                  </div>
                  <Divider />
                  <Form
                    form={profileForm}
                    layout="vertical"
                    initialValues={{
                      name: user?.username || '',
                      email: user?.email,
                      phone: '',
                      department: '',
                      position: '',
                      bio: '',
                    }}
                    onFinish={handleProfileUpdate}
                  >
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name="name"
                          label="姓名"
                          rules={[{ required: true, message: '请输入姓名' }]}
                        >
                          <Input />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name="email"
                          label="邮箱"
                          rules={[
                            { required: true, message: '请输入邮箱' },
                            { type: 'email', message: '请输入有效的邮箱地址' },
                          ]}
                        >
                          <Input />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="phone" label="手机号">
                          <Input />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="position" label="职位">
                          <Input />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="department" label="部门">
                          <Input />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="location" label="工作地点">
                          <Input />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item name="bio" label="个人简介">
                      <Input.TextArea rows={4} placeholder="介绍一下自己..." />
                    </Form.Item>
                  </Form>
                </Space>
              </Card>

              {/* 通知设置 */}
              <Card title={<><BellOutlined /> 通知设置</>}>
                <Form
                  form={notificationForm}
                  layout="vertical"
                  onFinish={handleNotificationUpdate}
                >
                  <List
                    dataSource={[
                      {
                        key: 'email_notification',
                        label: '邮件通知',
                        description: '接收系统邮件通知',
                      },
                      {
                        key: 'task_notification',
                        label: '任务通知',
                        description: '接收任务分配和更新通知',
                      },
                      {
                        key: 'meeting_notification',
                        label: '会议通知',
                        description: '接收会议提醒和变更通知',
                      },
                      {
                        key: 'mention_notification',
                        label: '@提及通知',
                        description: '接收他人@你的通知',
                      },
                      {
                        key: 'system_notification',
                        label: '系统通知',
                        description: '接收系统公告和维护通知',
                      },
                    ]}
                    renderItem={(item) => (
                      <List.Item
                        actions={[
                          <Switch defaultChecked key={item.key} />,
                        ]}
                      >
                        <List.Item.Meta
                          title={<Text strong>{item.label}</Text>}
                          description={item.description}
                        />
                      </List.Item>
                    )}
                  />
                  <Button type="primary" htmlType="submit">
                    保存设置
                  </Button>
                </Form>
              </Card>

              {/* 隐私与安全 */}
              <Card
                title={<><SecurityScanOutlined /> 隐私与安全</>}
                extra={
                  <Button type="link" onClick={() => setPasswordModalOpen(true)}>
                    修改密码
                  </Button>
                }
              >
                <Form
                  form={privacyForm}
                  layout="vertical"
                  onFinish={handlePrivacyUpdate}
                >
                  <List
                    dataSource={[
                      {
                        key: 'profile_visibility',
                        label: '个人资料可见性',
                        description: '谁可以看到您的个人资料',
                        type: 'select',
                        options: [
                          { value: 'public', label: '所有人' },
                          { value: 'company', label: '仅公司内部' },
                          { value: 'team', label: '仅团队成员' },
                          { value: 'private', label: '仅自己' },
                        ],
                      },
                      {
                        key: 'performance_visibility',
                        label: '绩效信息可见性',
                        description: '谁可以看到您的绩效评估',
                        type: 'select',
                        options: [
                          { value: 'manager', label: '仅上级' },
                          { value: 'company', label: '公司管理层' },
                          { value: 'private', label: '仅自己' },
                        ],
                      },
                      {
                        key: 'online_status',
                        label: '在线状态',
                        description: '显示您的在线状态给其他人',
                        type: 'switch',
                      },
                      {
                        key: 'activity_status',
                        label: '活动状态',
                        description: '显示您的最近活动时间',
                        type: 'switch',
                      },
                    ]}
                    renderItem={(item: any) => (
                      <List.Item>
                        <List.Item.Meta
                          title={<Text strong>{item.label}</Text>}
                          description={item.description}
                        />
                        {item.type === 'select' ? (
                          <Select defaultValue={item.options[0].value} style={{ width: 150 }}>
                            {item.options.map((opt: any) => (
                              <Select.Option key={opt.value} value={opt.value}>
                                {opt.label}
                              </Select.Option>
                            ))}
                          </Select>
                        ) : (
                          <Switch defaultChecked />
                        )}
                      </List.Item>
                    )}
                  />
                  <Divider />
                  <div>
                    <Title level={5}>登录设备</Title>
                    <List
                      dataSource={[
                        { device: 'Chrome on macOS', location: '北京，中国', time: '当前设备', current: true },
                        { device: 'Safari on iPhone', location: '北京，中国', time: '2 小时前', current: false },
                      ]}
                      renderItem={(item: any) => (
                        <List.Item
                          actions={[
                            item.current ? (
                              <Tag color="green">当前设备</Tag>
                            ) : (
                              <Button danger type="link" size="small">
                                下线
                              </Button>
                            ),
                          ]}
                        >
                          <List.Item.Meta
                            title={<Text strong>{item.device}</Text>}
                            description={`${item.location} · ${item.time}`}
                          />
                        </List.Item>
                      )}
                    />
                  </div>
                </Form>
              </Card>

              {/* API 密钥管理 */}
              <Card
                title={<><ApiOutlined /> API 密钥管理</>}
                extra={
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setApiKeyModalOpen(true)}
                  >
                    创建新密钥
                  </Button>
                }
              >
                {apiKeys.length === 0 ? (
                  <Empty
                    description="暂无 API 密钥"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                ) : (
                  <List
                    dataSource={apiKeys}
                    renderItem={(item) => (
                      <List.Item
                        actions={[
                          <Switch
                            checked={item.active}
                            onChange={() => handleToggleApiKey(item.id)}
                            key="switch"
                          />,
                          <Button
                            danger
                            type="link"
                            icon={<DeleteOutlined />}
                            onClick={() => handleDeleteApiKey(item.id)}
                            key="delete"
                          >
                            删除
                          </Button>,
                        ]}
                      >
                        <List.Item.Meta
                          title={
                            <Space>
                              <Text strong>{item.name}</Text>
                              <Tag color={item.active ? 'green' : 'default'}>
                                {item.active ? '启用中' : '已禁用'}
                              </Tag>
                            </Space>
                          }
                          description={
                            <Space direction="vertical" style={{ width: '100%' }}>
                              <Text code>{item.key}</Text>
                              <Text type="secondary">
                                创建于 {new Date(item.createdAt).toLocaleString()}
                              </Text>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                )}
              </Card>

              {/* 工作区设置 */}
              <Card title={<><SettingOutlined /> 工作区设置</>}>
                <Form layout="vertical">
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item label="语言">
                        <Select defaultValue="zh-CN">
                          <Select.Option value="zh-CN">简体中文</Select.Option>
                          <Select.Option value="zh-TW">繁體中文</Select.Option>
                          <Select.Option value="en-US">English</Select.Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="时区">
                        <Select defaultValue="Asia/Shanghai">
                          <Select.Option value="Asia/Shanghai">上海 (UTC+8)</Select.Option>
                          <Select.Option value="Asia/Tokyo">东京 (UTC+9)</Select.Option>
                          <Select.Option value="America/New_York">纽约 (UTC-5)</Select.Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item label="主题模式">
                        <Select defaultValue="auto">
                          <Select.Option value="auto">跟随系统</Select.Option>
                          <Select.Option value="light">浅色模式</Select.Option>
                          <Select.Option value="dark">深色模式</Select.Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label=" compact 模式">
                        <Switch defaultChecked={false} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Divider />
                  <div>
                    <Title level={5}>数据导出</Title>
                    <Paragraph type="secondary">
                      导出您的个人数据，包括绩效记录、培训历史等
                    </Paragraph>
                    <Space>
                      <Button icon={<DownloadOutlined />}>导出数据</Button>
                    </Space>
                  </div>
                </Form>
              </Card>
            </Space>
          </Col>
        </Row>
      </Space>

      {/* 修改密码弹窗 */}
      <Modal
        title="修改密码"
        open={passwordModalOpen}
        onOk={() => passwordForm.submit()}
        onCancel={() => {
          setPasswordModalOpen(false);
          passwordForm.resetFields();
        }}
      >
        <Form form={passwordForm} layout="vertical" onFinish={handlePasswordChange}>
          <Form.Item
            name="currentPassword"
            label="当前密码"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="newPassword"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '密码长度至少 8 位' },
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label="确认新密码"
            rules={[{ required: true, message: '请确认新密码' }]}
          >
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建 API 密钥弹窗 */}
      <Modal
        title="创建 API 密钥"
        open={apiKeyModalOpen}
        onOk={() => apiKeyForm.submit()}
        onCancel={() => {
          setApiKeyModalOpen(false);
          apiKeyForm.resetFields();
        }}
      >
        <Form form={apiKeyForm} layout="vertical" onFinish={handleGenerateApiKey}>
          <Form.Item
            name="name"
            label="密钥名称"
            rules={[{ required: true, message: '请输入密钥名称' }]}
          >
            <Input placeholder="例如：个人访问令牌" />
          </Form.Item>
          <Paragraph type="secondary">
            请妥善保存您的 API 密钥，它将只显示一次。一旦丢失，您需要重新创建新的密钥。
          </Paragraph>
        </Form>
      </Modal>
    </div>
  );
};

export default Settings;
