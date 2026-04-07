/**
 * AI Native 通知中心组件
 *
 * 显示 AI 主动推送的通知和建议
 */
import React, { useState, useEffect } from 'react';
import {
  Badge,
  Button,
  Card,
  Dropdown,
  List,
  Space,
  Tag,
  Typography,
  Drawer,
  Empty,
  Divider,
  Avatar
} from 'antd';
import {
  BellOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  TrophyOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  DeleteOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import aiNativeService, { PushNotification, AISuggestion } from '@/services/aiNativeService';
import './AINotification.less';

const { Title, Text, Paragraph } = Typography;

interface AINotificationProps {
  onNotificationClick?: (notification: PushNotification) => void;
}

const AINotification: React.FC<AINotificationProps> = ({ onNotificationClick }) => {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<PushNotification[]>([]);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    // 初始化服务
    aiNativeService.initialize();

    // 订阅通知
    const unsubscribeNotification = aiNativeService.onNotification((notification) => {
      setNotifications(prev => [notification, ...prev]);
      setUnreadCount(aiNativeService.getUnreadNotifications().length);
    });

    // 订阅建议
    const unsubscribeSuggestion = aiNativeService.onSuggestion((suggestion) => {
      setSuggestions(prev => [suggestion, ...prev]);
    });

    // 获取初始通知
    setNotifications(aiNativeService.getNotifications());
    setUnreadCount(aiNativeService.getUnreadNotifications().length);

    // 订阅主动推送
    const userId = localStorage.getItem('user_id') || 'demo_user';
    aiNativeService.subscribeToPush(userId);

    return () => {
      unsubscribeNotification();
      unsubscribeSuggestion();
    };
  }, []);

  const handleNotificationClick = (notification: PushNotification) => {
    aiNativeService.markAsRead(notification.id);
    setUnreadCount(aiNativeService.getUnreadNotifications().length);
    setNotifications(aiNativeService.getNotifications());
    onNotificationClick?.(notification);
    setOpen(false);
  };

  const handleMarkAllRead = () => {
    aiNativeService.markAllAsRead();
    setUnreadCount(0);
    setNotifications(aiNativeService.getNotifications());
  };

  const handleClearAll = () => {
    setNotifications([]);
    setUnreadCount(0);
  };

  const getTypeConfig = (type: string) => {
    switch (type) {
      case 'opportunity':
        return { icon: <ThunderboltOutlined />, color: '#722ed1', label: '机会' };
      case 'reminder':
        return { icon: <ExclamationCircleOutlined />, color: '#faad14', label: '提醒' };
      case 'achievement':
        return { icon: <TrophyOutlined />, color: '#52c41a', label: '成就' };
      case 'warning':
        return { icon: <ExclamationCircleOutlined />, color: '#ff4d4f', label: '警告' };
      default:
        return { icon: <InfoCircleOutlined />, color: '#1890ff', label: '通知' };
    }
  };

  const getNotificationIcon = (notification: PushNotification) => {
    const config = getTypeConfig(notification.type);
    return (
      <Avatar
        icon={config.icon}
        style={{ backgroundColor: config.color }}
        size={40}
      />
    );
  };

  const NotificationDropdown = () => (
    <div className="notification-dropdown">
      <div className="dropdown-header">
        <Title level={5} style={{ margin: 0 }}>通知中心</Title>
        <Space>
          <Button type="link" size="small" onClick={handleMarkAllRead}>
            <CheckOutlined /> 全部已读
          </Button>
          <Button type="link" size="small" danger onClick={handleClearAll}>
            <DeleteOutlined /> 清空
          </Button>
        </Space>
      </div>

      <Divider style={{ margin: 0 }} />

      <div className="dropdown-content">
        {notifications.length === 0 ? (
          <Empty description="暂无通知" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            dataSource={notifications.slice(0, 5)}
            renderItem={(item) => (
              <List.Item
                className={`notification-item ${!item.read ? 'unread' : ''}`}
                onClick={() => handleNotificationClick(item)}
              >
                <div className="notification-content">
                  <div className="notification-icon">
                    {getNotificationIcon(item)}
                  </div>
                  <div className="notification-info">
                    <div className="notification-header">
                      <Text strong className="notification-title">{item.title}</Text>
                      <Tag color={getTypeConfig(item.type).color} className="notification-tag">
                        {getTypeConfig(item.type).label}
                      </Tag>
                    </div>
                    <Paragraph className="notification-text" ellipsis={{ rows: 2 }}>
                      {item.content}
                    </Paragraph>
                    <Text type="secondary" className="notification-time">
                      {new Date(item.timestamp).toLocaleString('zh-CN')}
                    </Text>
                  </div>
                </div>
                {!item.read && <div className="unread-dot" />}
              </List.Item>
            )}
          />
        )}
      </div>

      <Divider style={{ margin: 0 }} />

      <div className="dropdown-footer">
        <Button type="primary" block onClick={() => setOpen(true)}>
          查看全部
        </Button>
      </div>
    </div>
  );

  return (
    <>
      <Dropdown
        overlay={<NotificationDropdown />}
        placement="bottomRight"
        trigger={['click']}
        overlayClassName="notification-dropdown-wrapper"
      >
        <Badge count={unreadCount} offset={[-5, 5]}>
          <Button
            type="text"
            icon={<BellOutlined style={{ fontSize: 18 }} />}
            className="notification-button"
          />
        </Badge>
      </Dropdown>

      <Drawer
        title="AI 通知中心"
        placement="right"
        width={400}
        open={open}
        onClose={() => setOpen(false)}
        className="ai-notification-drawer"
      >
        <div className="drawer-content">
          {/* AI 建议卡片 */}
          {suggestions.length > 0 && (
            <Card
              title={
                <Space>
                  <BulbOutlined style={{ color: '#faad14' }} />
                  AI 智能建议
                </Space>
              }
              size="small"
              className="ai-suggestions-card"
            >
              <List
                dataSource={suggestions.slice(0, 3)}
                renderItem={(suggestion) => (
                  <List.Item className="suggestion-item">
                    <div className="suggestion-content">
                      <div className="suggestion-header">
                        <Text strong>{suggestion.title}</Text>
                        <Tag color={suggestion.confidence >= 0.8 ? 'green' : 'orange'}>
                          {(suggestion.confidence * 100).toFixed(0)}% 置信度
                        </Tag>
                      </div>
                      <Paragraph type="secondary" className="suggestion-text">
                        {suggestion.description}
                      </Paragraph>
                      {suggestion.actions && (
                        <Space className="suggestion-actions">
                          {suggestion.actions.map((action, idx) => (
                            <Button
                              key={idx}
                              type="link"
                              size="small"
                              onClick={() => {
                                // 处理建议操作
                                console.log('执行建议操作:', action.action);
                              }}
                            >
                              {action.label}
                            </Button>
                          ))}
                        </Space>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          )}

          <Divider />

          {/* 全部通知列表 */}
          <div className="all-notifications">
            <div className="section-header">
              <Title level={5} style={{ margin: 0 }}>全部通知</Title>
              <Space>
                <Button type="link" size="small" onClick={handleMarkAllRead}>
                  全部已读
                </Button>
                <Button type="link" size="small" danger onClick={handleClearAll}>
                  清空
                </Button>
              </Space>
            </div>

            <List
              dataSource={notifications}
              renderItem={(item) => (
                <List.Item
                  className={`notification-item ${!item.read ? 'unread' : ''}`}
                  onClick={() => handleNotificationClick(item)}
                >
                  <div className="notification-content">
                    <div className="notification-icon">
                      {getNotificationIcon(item)}
                    </div>
                    <div className="notification-info">
                      <div className="notification-header">
                        <Text strong className="notification-title">{item.title}</Text>
                        <Tag color={getTypeConfig(item.type).color}>
                          {getTypeConfig(item.type).label}
                        </Tag>
                      </div>
                      <Paragraph className="notification-text" ellipsis={{ rows: 2 }}>
                        {item.content}
                      </Paragraph>
                      <Text type="secondary" className="notification-time">
                        {new Date(item.timestamp).toLocaleString('zh-CN')}
                      </Text>
                    </div>
                  </div>
                  {!item.read && <div className="unread-dot" />}
                </List.Item>
              )}
            />

            {notifications.length === 0 && (
              <Empty description="暂无通知" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </div>
        </div>
      </Drawer>
    </>
  );
};

export default AINotification;
