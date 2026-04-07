/**
 * 对话消息组件
 *
 * 展示用户和 AI 的消息，支持多种消息类型
 */
import React from 'react';
import { Avatar, Typography, Space, Tag, Timeline } from 'antd';
import { RobotOutlined, UserOutlined, InfoCircleOutlined } from '@ant-design/icons';
import './ChatMessage.less';

const { Text, Paragraph } = Typography;

interface MessageProps {
  message: {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
    data?: Record<string, any>;
  };
}

// 简单的 Markdown 渲染支持
const renderContent = (content: string) => {
  // 处理粗体 **text**
  const boldRegex = /\*\*(.+?)\*\*/g;
  const parts = content.split(boldRegex);

  return parts.map((part, index) => {
    if (index % 2 === 1) {
      return <strong key={index}>{part}</strong>;
    }
    // 处理列表项
    const lines = part.split('\n');
    return lines.map((line, lineIndex) => {
      if (line.startsWith('• ')) {
        return (
          <div key={`${index}-${lineIndex}`} className="message-list-item">
            {line.slice(2)}
          </div>
        );
      }
      if (line.trim()) {
        return <p key={`${index}-${lineIndex}`}>{line}</p>;
      }
      return null;
    });
  });
};

const ChatMessage: React.FC<MessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  if (isSystem) {
    return (
      <div className="message system-message">
        <InfoCircleOutlined className="system-icon" />
        <Text type="secondary">{message.content}</Text>
      </div>
    );
  }

  return (
    <div className={`message ${isUser ? 'user-message' : 'assistant-message'}`}>
      <Avatar
        size={40}
        icon={isUser ? <UserOutlined /> : <RobotOutlined />}
        style={{
          backgroundColor: isUser ? '#1890ff' : '#722ed1',
          flexShrink: 0,
        }}
      />
      <div className="message-content">
        <div className="message-header">
          <Text strong className="message-sender">
            {isUser ? '我' : 'AI 助手'}
          </Text>
          <Text type="secondary" className="message-time">
            {formatTime(message.timestamp)}
          </Text>
        </div>
        <div className="message-body">
          <Paragraph className="message-text">
            {renderContent(message.content)}
          </Paragraph>
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
