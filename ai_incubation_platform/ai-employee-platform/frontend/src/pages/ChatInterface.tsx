/**
 * AI Native 对话式主界面
 *
 * Chat-first 交互范式:
 * - 自然语言输入
 * - AI 主动建议
 * - 动态生成 UI 组件
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  Layout,
  Input,
  Button,
  Space,
  Avatar,
  Typography,
  Spin,
  Divider,
  Tag,
  Card,
  Dropdown,
  MenuProps,
  message,
  Drawer,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
  HomeOutlined,
  BulbOutlined,
  ScheduleOutlined,
  DashboardOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import ChatMessage from '@/components/ChatMessage';
import GenerativeUIRenderer from '@/components/GenerativeUIRenderer';
import AgentStatusPanel from '@/components/AgentStatusPanel';
import SuggestedActions from '@/components/SuggestedActions';
import AINotification from '@/components/AINotification';
import './ChatInterface.less';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;
const { TextArea } = Input;

// 意图模式定义
interface IntentMode {
  key: string;
  label: string;
  icon: React.ReactNode;
  prompt: string;
  color: string;
}

const INTENT_MODES: IntentMode[] = [
  {
    key: 'opportunity_match',
    label: '机会匹配',
    icon: <ThunderboltOutlined />,
    prompt: '有什么适合我的工作机会？',
    color: '#722ed1',
  },
  {
    key: 'career_plan',
    label: '职业规划',
    icon: <ScheduleOutlined />,
    prompt: '帮我做职业规划',
    color: '#1890ff',
  },
  {
    key: 'skill_analysis',
    label: '技能分析',
    icon: <BulbOutlined />,
    prompt: '分析我的技能情况',
    color: '#52c41a',
  },
  {
    key: 'dashboard',
    label: '仪表盘',
    icon: <DashboardOutlined />,
    prompt: '显示我的整体情况',
    color: '#faad14',
  },
];

// 消息类型
interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  data?: Record<string, any>;
  suggestedActions?: Array<{ action: string; label: string; available?: boolean }>;
  uiComponent?: string;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [showAgentPanel, setShowAgentPanel] = useState(true);
  const [agentStatus, setAgentStatus] = useState<'idle' | 'thinking' | 'executing' | 'completed'>('idle');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 初始化欢迎消息
  useEffect(() => {
    const welcomeMessage: Message = {
      id: 'welcome',
      role: 'assistant',
      content: `您好！我是您的 AI 职业发展助手 🤖

我可以帮助您：
• 🔍 **发现机会** - 智能匹配晋升/转岗/项目机会
• 📋 **职业规划** - 生成个性化发展路径
• 💡 **技能分析** - 分析能力差距并提供建议
• 📊 **绩效追踪** - 评估表现并给出改进方案

请告诉我您想了解什么，或者点击下方快捷操作开始！`,
      timestamp: new Date().toISOString(),
      suggestedActions: [
        { action: 'opportunity_match', label: '发现机会' },
        { action: 'career_plan', label: '职业规划' },
        { action: 'skill_analysis', label: '技能分析' },
        { action: 'dashboard', label: '查看仪表盘' },
      ],
    };
    setMessages([welcomeMessage]);
  }, []);

  // 发送消息
  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setAgentStatus('thinking');

    try {
      const userId = localStorage.getItem('user_id') || 'demo_user';
      const response = await fetch('http://localhost:8000/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          message: content.trim(),
          conversation_id: conversationId || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error('请求失败');
      }

      const data = await response.json();

      setConversationId(data.conversation_id || conversationId);

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.message?.content || '抱歉，我暂时无法处理您的请求。',
        timestamp: new Date().toISOString(),
        data: data.data,
        suggestedActions: data.suggested_actions,
        uiComponent: detectUIComponent(content, data),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setAgentStatus('completed');

      setTimeout(() => setAgentStatus('idle'), 2000);
    } catch (error) {
      console.error('发送消息失败:', error);

      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'system',
        content: '抱歉，连接服务器时遇到问题，请稍后重试。',
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, errorMessage]);
      message.error('请求失败，请检查网络连接');
      setAgentStatus('idle');
    } finally {
      setIsLoading(false);
    }
  };

  // 根据响应内容检测需要渲染的 UI 组件
  const detectUIComponent = (input: string, data: any): string | undefined => {
    const lowerInput = input.toLowerCase();

    if (lowerInput.includes('机会') || lowerInput.includes('匹配') || data.data?.opportunities) {
      return 'opportunity_cards';
    }
    if (lowerInput.includes('职业') || lowerInput.includes('规划') || data.data?.development_phases) {
      return 'career_timeline';
    }
    if (lowerInput.includes('技能') || lowerInput.includes('分析') || data.data?.skills) {
      return 'skill_radar';
    }
    if (lowerInput.includes('仪表') || lowerInput.includes('概览')) {
      return 'dashboard_stats';
    }

    return undefined;
  };

  // 处理快捷操作
  const handleSuggestedAction = (action: string) => {
    const mode = INTENT_MODES.find((m) => m.key === action);
    if (mode) {
      sendMessage(mode.prompt);
    } else {
      // 其他操作
      switch (action) {
        case 'view_full_plan':
          sendMessage('查看完整的职业规划');
          break;
        case 'set_goal':
          sendMessage('帮我设定具体目标');
          break;
        case 'apply':
          sendMessage('申请这个职位');
          break;
        default:
          message.info(`执行操作：${action}`);
      }
    }
  };

  // 快捷模式菜单
  const shortcutMenu: MenuProps = {
    items: INTENT_MODES.map((mode) => ({
      key: mode.key,
      icon: mode.icon,
      label: mode.label,
      onClick: () => sendMessage(mode.prompt),
    })),
  };

  return (
    <Layout className="chat-interface">
      <Sider
        width={280}
        theme="dark"
        collapsible
        collapsed={!showAgentPanel}
        collapsedWidth={0}
        style={{ overflow: 'hidden' }}
      >
        <AgentStatusPanel
          status={agentStatus}
          onToggle={() => setShowAgentPanel(!showAgentPanel)}
        />
      </Sider>

      <Layout>
        <Header className="chat-header">
          <Space>
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setShowAgentPanel(!showAgentPanel)}
            />
            <div className="header-logo">
              <RobotOutlined style={{ fontSize: 24, color: '#722ed1' }} />
              <Title level={4} style={{ margin: 0, color: '#333' }}>
                AI 职业发展助手
              </Title>
            </div>
          </Space>

          <Space>
            <AINotification />
            <Dropdown menu={shortcutMenu} placement="bottomRight" arrow>
              <Button type="primary" icon={<ThunderboltOutlined />}>
                快捷操作
              </Button>
            </Dropdown>
          </Space>
        </Header>

        <Content className="chat-content">
          <div className="messages-container">
            {messages.map((msg) => (
              <React.Fragment key={msg.id}>
                <ChatMessage message={msg} />
                {msg.uiComponent && (
                  <div className="generative-ui-container">
                    <GenerativeUIRenderer
                      componentType={msg.uiComponent}
                      data={msg.data}
                    />
                  </div>
                )}
                {msg.suggestedActions && msg.role === 'assistant' && (
                  <SuggestedActions
                    actions={msg.suggestedActions}
                    onSelect={handleSuggestedAction}
                  />
                )}
              </React.Fragment>
            ))}

            {isLoading && (
              <div className="loading-indicator">
                <Spin indicator={<LoadingOutlined spin />} size="large" />
                <Text type="secondary">
                  {agentStatus === 'thinking' ? 'AI 正在思考...' : 'AI 正在执行操作...'}
                </Text>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </Content>

        <div className="chat-input-area">
          <div className="intent-quick-actions">
            {INTENT_MODES.slice(0, 4).map((mode) => (
              <Tag
                key={mode.key}
                color={mode.color}
                className="intent-tag"
                onClick={() => sendMessage(mode.prompt)}
              >
                {mode.icon} {mode.label}
              </Tag>
            ))}
          </div>

          <div className="input-wrapper">
            <TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  sendMessage(inputValue);
                }
              }}
              placeholder="告诉我您的需求，例如：帮我找适合的工作机会 / 分析我的技能差距 / 制定职业发展计划..."
              autoSize={{ minRows: 2, maxRows: 6 }}
              disabled={isLoading}
            />
            <Button
              type="primary"
              size="large"
              onClick={() => sendMessage(inputValue)}
              disabled={!inputValue.trim() || isLoading}
              icon={<SendOutlined />}
              className="send-button"
            >
              发送
            </Button>
          </div>
        </div>
      </Layout>
    </Layout>
  );
};

export default ChatInterface;
