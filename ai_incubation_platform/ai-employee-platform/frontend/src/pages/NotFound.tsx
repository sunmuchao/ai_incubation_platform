/**
 * 404 页面 - AI Native 风格
 */
import React from 'react';
import { Result, Button, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { RobotOutlined, HomeOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  const containerStyle: React.CSSProperties = {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    padding: 24,
  };

  const iconStyle: React.CSSProperties = {
    fontSize: 80,
    color: '#722ed1',
  };

  const titleStyle: React.CSSProperties = {
    color: '#fff',
  };

  const subTitleStyle: React.CSSProperties = {
    color: 'rgba(255,255,255,0.6)',
  };

  return (
    <div style={containerStyle}>
      <Result
        icon={<RobotOutlined style={iconStyle} />}
        title={<Title level={3} style={titleStyle}>页面未找到</Title>}
        subTitle={<Text style={subTitleStyle}>抱歉，AI 助手找不到您访问的页面</Text>}
        extra={[
          <Button
            key="home"
            type="primary"
            icon={<HomeOutlined />}
            onClick={() => navigate('/chat')}
            size="large"
          >
            返回对话首页
          </Button>,
          <Button
            key="help"
            onClick={() => navigate('/generative-ui')}
            size="large"
          >
            探索功能
          </Button>,
        ]}
      />
    </div>
  );
};

export default NotFound;
