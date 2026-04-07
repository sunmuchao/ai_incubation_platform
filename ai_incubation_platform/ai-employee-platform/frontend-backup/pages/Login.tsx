/**
 * 登录页面
 */
import React, { useState } from 'react';
import { Form, Input, Button, Checkbox, Typography, message, Divider } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks';
import './Login.less';

const { Title, Text } = Typography;

interface LoginFormValues {
  username: string;
  password: string;
  remember?: boolean;
}

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('登录成功');
      navigate('/dashboard');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '登录失败，请检查账号密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-header">
        <Title level={2} style={{ marginBottom: 8 }}>
          AI Employee Platform
        </Title>
        <Text type="secondary">AI 员工管理平台</Text>
      </div>

      <Form
        form={form}
        name="login"
        onFinish={handleSubmit}
        autoComplete="off"
        size="large"
        layout="vertical"
      >
        <Form.Item
          name="username"
          rules={[{ required: true, message: '请输入用户名' }]}
        >
          <Input
            prefix={<UserOutlined />}
            placeholder="用户名"
            autoComplete="username"
          />
        </Form.Item>

        <Form.Item
          name="password"
          rules={[{ required: true, message: '请输入密码' }]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="密码"
            autoComplete="current-password"
          />
        </Form.Item>

        <Form.Item>
          <div className="login-options">
            <Checkbox>记住我</Checkbox>
            <a href="#" className="forgot-password">
              忘记密码
            </a>
          </div>
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            登录
          </Button>
        </Form.Item>

        <Divider>或</Divider>

        <div className="login-footer">
          <Text type="secondary">还没有账号？</Text>
          <Button type="link" onClick={() => navigate('/register')}>
            立即注册
          </Button>
        </div>
      </Form>

      {/* 演示账号提示 */}
      <div className="demo-tips">
        <Text type="secondary" style={{ fontSize: 12 }}>
          演示账号：admin / admin123
        </Text>
      </div>
    </div>
  );
};

export default Login;
