/**
 * AI Chat 组件 - Bento Grid 风格重构
 * 对话式交互界面，Linear.app 风格
 */
import React, { useState, useRef, useEffect } from 'react';
import {
  Input,
  Button,
  Space,
  Typography,
  Divider,
  Alert,
  Tooltip,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  SearchOutlined,
  LineChartOutlined,
  BellOutlined,
  SparklesOutlined,
} from '@ant-design/icons';
import type { ChatMessage, BusinessOpportunity, MarketTrend } from '../types';
import { sendChatMessage, getSuggestions, listIntents } from '../api';
import OpportunityCard from './OpportunityCard';
import TrendChart from './TrendChart';
import AgentWorkflow from './AgentWorkflow';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

interface AIChatProps {
  onOpportunitySelect?: (opportunity: BusinessOpportunity) => void;
  onWorkflowStart?: (workflowType: string, params: any) => void;
}

/**
 * AI Chat 主组件 - Bento Grid 风格
 */
const AIChat: React.FC<AIChatProps> = ({ onOpportunitySelect, onWorkflowStart }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        '您好！我是您的 AI 商业机会挖掘助手。我可以帮您：\n\n' +
        '🔍 **发现商机** - "帮我找人工智能领域的商机"\n' +
        '📈 **分析趋势** - "分析新能源行业趋势"\n' +
        '⭐ **评估机会** - "评估这个商机的价值"\n' +
        '🔔 **主动推送** - "有重要机会时通知我"\n\n' +
        '请告诉我您感兴趣的领域或需求~',
      timestamp: new Date().toISOString(),
      suggestions: [
        '帮我找人工智能领域的商机',
        '分析新能源行业趋势',
        '显示所有高价值商机',
        '启用高价值商机推送',
      ],
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [workflowSteps, setWorkflowSteps] = useState<any[]>([]);
  const [activeAlerts, setActiveAlerts] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<TextArea>(null);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 处理发送消息
  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setWorkflowSteps([]);

    try {
      // 如果是工作流相关的查询，显示工作流进度
      const isWorkflowQuery =
        content.includes('分析') ||
        content.includes('挖掘') ||
        content.includes('调研') ||
        content.includes('评估');

      if (isWorkflowQuery) {
        setWorkflowSteps([
          { id: '1', name: '理解意图', status: 'running', description: 'AI 正在分析您的需求' },
          { id: '2', name: '数据收集', status: 'pending', description: '从多源数据获取信息' },
          { id: '3', name: '智能分析', status: 'pending', description: 'AI 深度分析与评估' },
          { id: '4', name: '生成报告', status: 'pending', description: '整理分析结果' },
        ]);
      }

      const response = await sendChatMessage({ query: content });

      // 更新工作流步骤状态
      if (isWorkflowQuery) {
        setWorkflowSteps((prev) =>
          prev.map((step) => ({
            ...step,
            status: 'completed' as const,
            result: { success: true },
          }))
        );
      }

      const assistantMessage: ChatMessage = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        data: response.data,
        suggestions: response.suggestions,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (onWorkflowStart && isWorkflowQuery) {
        onWorkflowStart(response.intent || 'unknown', response.data);
      }
    } catch (error: any) {
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        role: 'system',
        content: `请求失败：${error.message || '请稍后重试'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  // 处理建议点击
  const handleSuggestionClick = (suggestion: string) => {
    handleSendMessage(suggestion);
  };

  // 渲染消息内容
  const renderMessageContent = (message: ChatMessage) => {
    const { role, content, data } = message;

    // 渲染机会卡片
    const renderOpportunities = () => {
      const opportunities = data?.opportunities || [];
      if (opportunities.length === 0) return null;

      return (
        <div style={{ marginTop: 16 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 12,
            }}
          >
            <BulbOutlined style={{ color: 'var(--color-primary-500)', fontSize: 14 }} />
            <Text
              strong
              style={{
                color: 'var(--color-text-secondary)',
                fontSize: 'var(--font-size-xs)',
                textTransform: 'uppercase',
              }}
            >
              发现 {opportunities.length} 条商机
            </Text>
          </div>
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            {opportunities.map((opp: BusinessOpportunity, index: number) => (
              <OpportunityCard
                key={opp.id || index}
                opportunity={opp}
                onSelect={onOpportunitySelect}
                compact
              />
            ))}
          </Space>
        </div>
      );
    };

    // 渲染趋势图表
    const renderTrends = () => {
      const trends = data?.trends || [];
      if (trends.length === 0) return null;

      return (
        <div style={{ marginTop: 16 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 12,
            }}
          >
            <LineChartOutlined style={{ color: 'var(--color-primary-500)', fontSize: 14 }} />
            <Text
              strong
              style={{
                color: 'var(--color-text-secondary)',
                fontSize: 'var(--font-size-xs)',
                textTransform: 'uppercase',
              }}
            >
              趋势分析
            </Text>
          </div>
          <TrendChart trends={trends} />
        </div>
      );
    };

    // 渲染警报 - Bento 风格
    const renderAlerts = () => {
      if (!data?.alert) return null;
      const alert = data.alert;

      return (
        <div
          className="bento-card bento-card-sm fade-in"
          style={{
            marginTop: 16,
            background: alert.priority === 'high'
              ? 'linear-gradient(135deg, var(--color-error)15 0%, var(--color-bg-subtle) 100%)'
              : 'linear-gradient(135deg, var(--color-warning)15 0%, var(--color-bg-subtle) 100%)',
            border: `1px solid ${alert.priority === 'high' ? 'var(--color-error)30' : 'var(--color-warning)30'}`,
            borderLeft: `3px solid ${alert.priority === 'high' ? 'var(--color-error)50' : 'var(--color-warning)50'}`,
          }}
        >
          <Space size={8}>
            <BellOutlined
              style={{
                color: alert.priority === 'high' ? 'var(--color-error)' : 'var(--color-warning)',
              }}
            />
            <Text strong style={{ color: 'var(--color-text-primary)' }}>
              {alert.message}
            </Text>
          </Space>
        </div>
      );
    };

    // 根据角色渲染不同样式
    if (role === 'user') {
      return (
        <div
          className="fade-in"
          style={{ display: 'flex', justifyContent: 'flex-end' }}
        >
          <div
            style={{
              background: 'var(--gradient-accent)',
              borderRadius: 'var(--radius-2xl) var(--radius-2xl) var(--radius-md) var(--radius-2xl)',
              padding: '12px 16px',
              color: '#fff',
              maxWidth: '80%',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <Paragraph style={{ margin: 0, color: '#fff', fontSize: 'var(--font-size-sm)' }}>
              {content}
            </Paragraph>
          </div>
        </div>
      );
    }

    if (role === 'system') {
      return (
        <Alert
          message={content}
          type="error"
          showIcon
          style={{
            marginTop: 8,
            background: 'var(--color-error)15',
            border: '1px solid var(--color-error)30',
          }}
        />
      );
    }

    // 助手消息 - Bento 风格
    return (
      <div className="fade-in" style={{ display: 'flex', gap: 12 }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 'var(--radius-lg)',
            background: 'var(--gradient-accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            boxShadow: 'var(--shadow-glow-sm)',
          }}
        >
          <RobotOutlined style={{ color: '#fff', fontSize: 18 }} />
        </div>
        <div style={{ flex: 1, maxWidth: '80%' }}>
          <div
            style={{
              background: 'var(--color-bg-container)',
              borderRadius: 'var(--radius-2xl) var(--radius-2xl) var(--radius-2xl) var(--radius-md)',
              padding: '16px',
              border: '1px solid var(--color-border-base)',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <Paragraph
              style={{
                margin: 0,
                whiteSpace: 'pre-wrap',
                color: 'var(--color-text-primary)',
                fontSize: 'var(--font-size-sm)',
                lineHeight: 'var(--line-height-relaxed)',
              }}
            >
              {content}
            </Paragraph>
          </div>
          {renderOpportunities()}
          {renderTrends()}
          {renderAlerts()}

          {/* 渲染建议 - Bento 标签风格 */}
          {message.suggestions && message.suggestions.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <Space wrap size={8}>
                {message.suggestions.map((suggestion: string, index: number) => (
                  <div
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="bento-card bento-card-sm"
                    style={{
                      cursor: 'pointer',
                      background: 'var(--color-primary-500)10',
                      border: '1px solid var(--color-primary-500)20',
                      padding: '6px 12px',
                      transition: 'all var(--transition-fast)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'var(--color-primary-500)20';
                      e.currentTarget.style.borderColor = 'var(--color-primary-500)40';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'var(--color-primary-500)10';
                      e.currentTarget.style.borderColor = 'var(--color-primary-500)20';
                    }}
                  >
                    <Space size={4}>
                      <ThunderboltOutlined
                        style={{
                          color: 'var(--color-primary-400)',
                          fontSize: 12,
                        }}
                      />
                      <Text
                        style={{
                          color: 'var(--color-primary-300)',
                          fontSize: 'var(--font-size-xs)',
                        }}
                      >
                        {suggestion}
                      </Text>
                    </Space>
                  </div>
                ))}
              </Space>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div
      className="bento-card"
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--color-bg-container)',
        border: '1px solid var(--color-border-base)',
      }}
    >
      {/* 工作流进度显示 - Bento 风格 */}
      {workflowSteps.length > 0 && (
        <div
          className="fade-in"
          style={{
            marginBottom: 16,
            padding: 16,
            background: 'var(--color-primary-500)10',
            borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--color-primary-500)20',
          }}
        >
          <AgentWorkflow steps={workflowSteps} />
        </div>
      )}

      {/* 警报区域 */}
      {activeAlerts.length > 0 && (
        <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
          {activeAlerts.map((alert) => (
            <div
              key={alert.alert_id}
              className="bento-card bento-card-sm"
              style={{
                background:
                  alert.priority === 'high'
                    ? 'linear-gradient(135deg, var(--color-error)15 0%, var(--color-bg-subtle) 100%)'
                    : 'linear-gradient(135deg, var(--color-warning)15 0%, var(--color-bg-subtle) 100%)',
                border: `1px solid ${alert.priority === 'high' ? 'var(--color-error)30' : 'var(--color-warning)30'}`,
                borderLeft: `3px solid ${alert.priority === 'high' ? 'var(--color-error)' : 'var(--color-warning)'}`,
              }}
            >
              <Space size={8}>
                <BellOutlined
                  style={{
                    color: alert.priority === 'high' ? 'var(--color-error)' : 'var(--color-warning)',
                  }}
                />
                <Text strong style={{ color: 'var(--color-text-primary)' }}>
                  {alert.message}
                </Text>
              </Space>
            </div>
          ))}
        </Space>
      )}

      {/* 消息列表 */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
        }}
      >
        {messages.map((message) => (
          <div key={message.id}>{renderMessageContent(message)}</div>
        ))}

        {/* 加载中状态 - Bento 风格 */}
        {isLoading && (
          <div
            className="fade-in"
            style={{ display: 'flex', gap: 12, alignItems: 'center' }}
          >
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 'var(--radius-lg)',
                background: 'var(--gradient-accent)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 'var(--shadow-glow-sm)',
              }}
            >
              <RobotOutlined style={{ color: '#fff', fontSize: 18 }} />
            </div>
            <div
              style={{
                padding: '8px 16px',
                background: 'var(--color-bg-subtle)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--color-border-base)',
              }}
            >
              <Space size={8}>
                <span
                  className="pulse"
                  style={{
                    display: 'inline-block',
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: 'var(--color-primary-500)',
                  }}
                />
                <Text
                  style={{
                    color: 'var(--color-text-secondary)',
                    fontSize: 'var(--font-size-sm)',
                  }}
                >
                  AI 正在思考...
                </Text>
              </Space>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 - Bento 风格 */}
      <div
        style={{
          padding: 16,
          background: 'var(--color-bg-subtle)',
          borderTop: '1px solid var(--color-border-base)',
          borderRadius: '0 0 var(--radius-xl) var(--radius-xl)',
        }}
      >
        {/* 快捷操作按钮 */}
        <Space wrap size={8} style={{ marginBottom: 12 }}>
          <Tooltip title="快速发现商机">
            <Button
              size="small"
              icon={<SearchOutlined />}
              onClick={() => handleSendMessage('帮我找最近的高价值商机')}
              style={{
                borderColor: 'var(--color-border-base)',
                color: 'var(--color-text-secondary)',
                background: 'var(--glass-light)',
              }}
            >
              发现商机
            </Button>
          </Tooltip>
          <Tooltip title="行业趋势分析">
            <Button
              size="small"
              icon={<LineChartOutlined />}
              onClick={() => handleSendMessage('分析当前热门行业趋势')}
              style={{
                borderColor: 'var(--color-border-base)',
                color: 'var(--color-text-secondary)',
                background: 'var(--glass-light)',
              }}
            >
              分析趋势
            </Button>
          </Tooltip>
          <Tooltip title="启用主动推送">
            <Button
              size="small"
              icon={<BellOutlined />}
              onClick={() => handleSendMessage('启用高价值商机推送')}
              style={{
                borderColor: 'var(--color-border-base)',
                color: 'var(--color-text-secondary)',
                background: 'var(--glass-light)',
              }}
            >
              推送提醒
            </Button>
          </Tooltip>
        </Space>

        {/* 输入框 */}
        <div style={{ display: 'flex', gap: 8 }}>
          <TextArea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSendMessage(inputValue);
              }
            }}
            placeholder="告诉我您感兴趣的领域，AI 将为您挖掘商业机会...（Shift+Enter 换行）"
            autoSize={{ minRows: 2, maxRows: 4 }}
            style={{
              background: 'var(--color-bg-container)',
              border: '1px solid var(--color-border-base)',
              color: 'var(--color-text-primary)',
              borderRadius: 'var(--radius-lg)',
              fontSize: 'var(--font-size-sm)',
              resize: 'none',
            }}
            disabled={isLoading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => handleSendMessage(inputValue)}
            loading={isLoading}
            disabled={!inputValue.trim()}
            style={{
              background: 'var(--gradient-accent)',
              border: 'none',
              borderRadius: 'var(--radius-lg)',
              minWidth: 48,
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default AIChat;
