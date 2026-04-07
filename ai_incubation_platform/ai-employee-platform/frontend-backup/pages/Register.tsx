/**
 * 注册页面
 */
import React, { useState } from 'react';
import { Form, Input, Button, Select, Typography, message, Divider } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, PhoneOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { httpClient } from '@/services';
import './Login.less';

const { Title, Text } = Typography;
const { Option } = Select;

interface RegisterFormValues {
  username: string;
  email: string;
  phone?: string;
  password: string;
  confirmPassword: string;
  tenant_name: string;
  tenant_type: 'enterprise' | 'individual';
}

const Register: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const handleSubmit = async (values: RegisterFormValues) => {
    if (values.password !== values.confirmPassword) {
      message.error('两次输入的密码不一致');
      return;
    }

    setLoading(true);
    try {
      // 创建租户
      const tenantResponse = await httpClient.post('/api/employees/tenants', {
        name: values.tenant_name,
        type: values.tenant_type,
      });

      // 创建用户
      await httpClient.post(
        `/api/employees/tenants/${(tenantResponse.data as any).id}/users`,
        {
          username: values.username,
          email: values.email,
          phone: values.phone,
          password: values.password,
          role: values.tenant_type === 'enterprise' ? 'enterprise' : 'employee',
        }
      );

      message.success('注册成功，请登录');
      navigate('/login');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '注册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="register-container">
      <div className="login-header">
        <Title level={2} style={{ marginBottom: 8 }}>
          创建账号
        </Title>
        <Text type="secondary">AI 员工管理平台</Text>
      </div>

      <Form
        form={form}
        name="register"
        onFinish={handleSubmit}
        autoComplete="off"
        size="large"
        layout="vertical"
      >
        <Form.Item
          name="tenant_name"
          label="组织名称"
          rules={[{ required: true, message: '请输入组织名称' }]}
        >
          <Input placeholder="请输入组织名称" />
        </Form.Item>

        <Form.Item
          name="tenant_type"
          label="组织类型"
          initialValue="enterprise"
          rules={[{ required: true }]}
        >
          <Select>
            <Option value="enterprise">企业</Option>
            <Option value="individual">个人</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="username"
          label="用户名"
          rules={[{ required: true, message: '请输入用户名' }]}
        >
          <Input prefix={<UserOutlined />} placeholder="请输入用户名" />
        </Form.Item>

        <Form.Item
          name="email"
          label="邮箱"
          rules={[
            { required: true, message: '请输入邮箱' },
            { type: 'email', message: '邮箱格式不正确' },
          ]}
        >
          <Input prefix={<MailOutlined />} placeholder="请输入邮箱" />
        </Form.Item>

        <Form.Item
          name="phone"
          label="手机号（选填）"
          rules={[{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' }]}
        >
          <Input prefix={<PhoneOutlined />} placeholder="请输入手机号" />
        </Form.Item>

        <Form.Item
          name="password"
          label="密码"
          rules={[
            { required: true, message: '请输入密码' },
            { min: 6, message: '密码长度至少 6 位' },
          ]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
        </Form.Item>

        <Form.Item
          name="confirmPassword"
          label="确认密码"
          rules={[{ required: true, message: '请再次输入密码' }]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="请再次输入密码" />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            注册
          </Button>
        </Form.Item>

        <Divider>或</Divider>

        <div className="login-footer">
          <Text type="secondary">已有账号？</Text>
          <Button type="link" onClick={() => navigate('/login')}>
            立即登录
          </Button>
        </div>
      </Form>
    </div>
  );
};

export default Register;
