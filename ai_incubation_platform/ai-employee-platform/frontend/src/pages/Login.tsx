/**
 * AI Native 登录页面
 * 简洁现代的登录界面
 */
import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, message, Divider } from 'antd';
import { UserOutlined, LockOutlined, RobotOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import './Login.less';

const { Title, Text } = Typography;

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      // 模拟登录，实际应该调用 API
      localStorage.setItem('user_id', values.username);
      localStorage.setItem('username', values.username);

      message.success('登录成功！');
      navigate('/chat');
    } catch (error) {
      message.error('登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = () => {
    localStorage.setItem('user_id', 'demo_user');
    localStorage.setItem('username', '演示用户');
    message.success('已使用演示账号登录');
    navigate('/chat');
  };

  return (
    <div className="login-page">
      <div className="login-background">
        <div className="bg-circle circle-1" />
        <div className="bg-circle circle-2" />
        <div className="bg-circle circle-3" />
      </div>

      <div className="login-container">
        <div className="login-header">
          <RobotOutlined className="logo-icon" />
          <Title level={2} style={{ margin: '12px 0 0 0', color: '#fff' }}>
            AI Employee Platform
          </Title>
          <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
            AI 智能职业发展助手
          </Text>
        </div>

        <Card className="login-card">
          <Title level={4} style={{ textAlign: 'center', marginBottom: 24 }}>
            欢迎回来
          </Title>

          <Form
            name="login"
            initialValues={{ remember: true }}
            onFinish={onFinish}
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="用户名"
                size="large"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="密码"
                size="large"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
                className="login-button"
              >
                登录
              </Button>
            </Form.Item>
          </Form>

          <Divider>或</Divider>

          <Button
            block
            size="large"
            onClick={handleQuickLogin}
            icon={<ThunderboltOutlined />}
            className="quick-login-button"
          >
            使用演示账号体验
          </Button>

          <div className="login-footer">
            <Text type="secondary" style={{ fontSize: 12 }}>
              还没有账号？<a href="#">立即注册</a>
            </Text>
          </div>
        </Card>

        <div className="login-features">
          <div className="feature-item">
            <ThunderboltOutlined className="feature-icon" />
            <Text>AI 智能匹配</Text>
          </div>
          <div className="feature-item">
            <RobotOutlined className="feature-icon" />
            <Text>自主职业顾问</Text>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
