import React from 'react';
import { Card, Row, Col, Form, Input, Switch, Select, Button, Divider, message } from 'antd';
import { SaveOutlined } from '@ant-design/icons';

const Settings: React.FC = () => {
  const [form] = Form.useForm();

  const handleSave = (values: any) => {
    console.log('Settings saved:', values);
    message.success('设置已保存');
  };

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>设置</h1>
        <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>
          系统配置和参数设置
        </p>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="通用设置">
            <Form form={form} layout="vertical" onFinish={handleSave}>
              <Form.Item
                label="系统名称"
                name="systemName"
                initialValue="AI Runtime Optimizer"
                rules={[{ required: true, message: '请输入系统名称' }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label="数据保留天数"
                name="retentionDays"
                initialValue={30}
              >
                <Select>
                  <Select.Option value={7}>7 天</Select.Option>
                  <Select.Option value={14}>14 天</Select.Option>
                  <Select.Option value={30}>30 天</Select.Option>
                  <Select.Option value={60}>60 天</Select.Option>
                  <Select.Option value={90}>90 天</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item
                label="刷新间隔 (秒)"
                name="refreshInterval"
                initialValue={30}
              >
                <Select>
                  <Select.Option value={10}>10 秒</Select.Option>
                  <Select.Option value={30}>30 秒</Select.Option>
                  <Select.Option value={60}>60 秒</Select.Option>
                  <Select.Option value={300}>5 分钟</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                  保存设置
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="告警通知设置">
            <Form layout="vertical">
              <Form.Item label="邮件通知" name="emailEnabled" initialValue={true} valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="Slack 通知" name="slackEnabled" initialValue={false} valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="钉钉通知" name="dingtalkEnabled" initialValue={true} valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="企业微信通知" name="wechatEnabled" initialValue={false} valuePropName="checked">
                <Switch />
              </Form.Item>
              <Divider />
              <Form.Item
                label="通知邮箱"
                name="notifyEmail"
                initialValue="admin@example.com"
              >
                <Input />
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="AI 引擎设置">
            <Form layout="vertical">
              <Form.Item
                label="LLM 提供商"
                name="llmProvider"
                initialValue="openai"
              >
                <Select>
                  <Select.Option value="openai">OpenAI</Select.Option>
                  <Select.Option value="anthropic">Anthropic</Select.Option>
                  <Select.Option value="azure">Azure OpenAI</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item
                label="API Key"
                name="apiKey"
                initialValue="sk-****"
              >
                <Input.Password />
              </Form.Item>
              <Form.Item
                label="模型"
                name="model"
                initialValue="gpt-4"
              >
                <Select>
                  <Select.Option value="gpt-4">GPT-4</Select.Option>
                  <Select.Option value="gpt-3.5-turbo">GPT-3.5</Select.Option>
                  <Select.Option value="claude-3">Claude 3</Select.Option>
                </Select>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="自动化设置">
            <Form layout="vertical">
              <Form.Item label="自动扩缩容" name="autoScaling" initialValue={true} valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="自动故障恢复" name="autoRemediation" initialValue={false} valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="自动备份" name="autoBackup" initialValue={true} valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="需要审批" name="requireApproval" initialValue={true} valuePropName="checked">
                <Switch />
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Settings;
