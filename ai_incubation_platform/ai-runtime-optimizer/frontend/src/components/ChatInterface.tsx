/**
 * AI Chat Component - 对话式交互核心组件
 * Bento Grid & Monochromatic 设计风格
 */

import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Card, Tag, message as antdMessage } from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import type { ChatMessage, ChatAction } from '@/types';
import type { AgentStateItem } from '@/store';
import { useChatStore, useAgentStore } from '@/store';
import { aiNativeApi, formatConfidence } from '@/services/api';
import { colors, shadows, radii, spacing, typography, transitions } from '@/styles/design-tokens';

const { TextArea } = Input;

interface ChatInterfaceProps {
  onNavigate?: (path: string) => void;
}

/**
 * 消息气泡组件 - Bento 风格
 */
const MessageBubble: React.FC<{ message: ChatMessage }> = ({ message }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: spacing[4],
        animation: 'fadeIn 0.3s ease',
      }}
    >
      {!isUser && (
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: radii.lg,
            background: isSystem
              ? `linear-gradient(135deg, ${colors.semantic.accent} 0%, ${colors.primary[700]} 100%)`
              : `linear-gradient(135deg, ${colors.semantic.info} 0%, ${colors.primary[600]} 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: spacing[3],
            flexShrink: 0,
            boxShadow: shadows.card,
          }}
        >
          <RobotOutlined style={{ color: '#fff', fontSize: 18 }} />
        </div>
      )}

      <div
        style={{
          maxWidth: '70%',
          padding: `${spacing[3]} ${spacing[4]}`,
          borderRadius: radii.lg,
          background: isUser
            ? `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`
            : isSystem
            ? `linear-gradient(135deg, ${colors.semantic.accent} 0%, ${colors.primary[700]} 100%)`
            : colors.dark.bgCard,
          color: '#fff',
          boxShadow: isUser ? shadows.card : `0 2px 8px rgba(0,0,0,0.2)`,
          border: isUser ? 'none' : `1px solid ${colors.dark.border}`,
          transition: `all ${transitions.durations.normal}`,
        }}
        onMouseEnter={(e) => {
          if (!isUser) {
            e.currentTarget.style.borderColor = colors.primary[600];
            e.currentTarget.style.boxShadow = shadows.cardHover;
          }
        }}
        onMouseLeave={(e) => {
          if (!isUser) {
            e.currentTarget.style.borderColor = colors.dark.border;
            e.currentTarget.style.boxShadow = isUser ? shadows.card : `0 2px 8px rgba(0,0,0,0.2)`;
          }
        }}
      >
        {/* 消息内容 */}
        <div style={{
          whiteSpace: 'pre-wrap',
          lineHeight: typography.lineHeight.relaxed,
          fontSize: typography.fontSize.base,
        }}>
          {message.content}
        </div>

        {/* 置信度显示 */}
        {!isUser && message.confidence !== undefined && (
          <div style={{
            marginTop: spacing[2],
            display: 'flex',
            alignItems: 'center',
            gap: spacing[2],
          }}>
            <Tag
              color={message.confidence > 0.8 ? colors.semantic.success : message.confidence > 0.5 ? colors.semantic.warning : colors.semantic.error}
              style={{
                borderRadius: radii.full,
                fontSize: typography.fontSize.xs,
                padding: `0 ${spacing[2]}`,
                background: `${message.confidence > 0.8 ? colors.semantic.success : message.confidence > 0.5 ? colors.semantic.warning : colors.semantic.error}20`,
                border: `1px solid ${message.confidence > 0.8 ? colors.semantic.success : message.confidence > 0.5 ? colors.semantic.warning : colors.semantic.error}`,
              }}
            >
              置信度 {formatConfidence(message.confidence)}
            </Tag>
          </div>
        )}

        {/* 附件/图表 */}
        {message.attachments && message.attachments.map((attachment, index) => (
          <div key={index} style={{ marginTop: spacing[3] }}>
            <Card
              size="small"
              title={
                <span style={{ color: colors.neutral[200], fontSize: typography.fontSize.sm }}>
                  {attachment.title}
                </span>
              }
              style={{
                background: colors.dark.bgCardHover,
                border: `1px solid ${colors.dark.border}`,
                borderRadius: radii.md,
              }}
            >
              <pre style={{
                background: colors.dark.bg,
                borderRadius: radii.sm,
                padding: spacing[3],
                color: colors.neutral[300],
                fontSize: typography.fontSize.xs,
                fontFamily: typography.fontFamily.mono,
                overflow: 'auto',
                margin: 0,
              }}>
                {JSON.stringify(attachment.data, null, 2)}
              </pre>
            </Card>
          </div>
        ))}

        {/* 操作按钮 */}
        {message.actions && message.actions.length > 0 && (
          <div style={{
            marginTop: spacing[3],
            display: 'flex',
            flexWrap: 'wrap',
            gap: spacing[2],
            paddingTop: spacing[3],
            borderTop: `1px solid ${isUser ? 'rgba(255,255,255,0.1)' : colors.dark.border}`,
          }}>
            {message.actions.map((action, index) => (
              <ActionKey key={index} action={action} />
            ))}
          </div>
        )}

        {/* 时间戳 */}
        <div
          style={{
            fontSize: typography.fontSize.xs,
            color: 'rgba(255,255,255,0.4)',
            marginTop: spacing[2],
            textAlign: 'right',
          }}
        >
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>

      {isUser && (
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: radii.lg,
            background: `linear-gradient(135deg, ${colors.primary[500]} 0%, ${colors.primary[700]} 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginLeft: spacing[3],
            flexShrink: 0,
            boxShadow: shadows.card,
          }}
        >
          <UserOutlined style={{ color: '#fff', fontSize: 18 }} />
        </div>
      )}
    </div>
  );
};

/**
 * 操作密钥组件 - Bento 风格按钮
 */
const ActionKey: React.FC<{ action: ChatAction }> = ({ action }) => {
  const getIcon = () => {
    switch (action.type) {
      case 'execute':
        return <ThunderboltOutlined />;
      case 'confirm':
        return <CheckCircleOutlined />;
      case 'cancel':
        return <WarningOutlined />;
      default:
        return null;
    }
  };

  return (
    <Button
      size="small"
      type="primary"
      icon={getIcon()}
      style={{
        background: `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`,
        border: 'none',
        borderRadius: radii.full,
        padding: `${spacing[2]} ${spacing[3]}`,
        fontSize: typography.fontSize.sm,
        fontWeight: 500,
        boxShadow: shadows.card,
        transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
        height: 'auto',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = `${shadows.cardHover}, 0 0 16px ${colors.primary[700]}60`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = shadows.card;
      }}
      onClick={() => {
        antdMessage.info(`执行操作：${action.label}`);
        console.log('Action clicked:', action);
      }}
    >
      {action.label}
    </Button>
  );
};

/**
 * 快捷建议组件 - Bento 风格
 */
const QuickSuggestions: React.FC<{ onSuggestionClick: (question: string) => void }> = ({
  onSuggestionClick,
}) => {
  const suggestions = [
    { icon: '🔍', text: '系统当前有什么异常？' },
    { icon: '📊', text: '显示性能瓶颈分析' },
    { icon: '🤖', text: '运行自主运维循环' },
    { icon: '💡', text: '获取优化建议' },
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
      gap: spacing[3],
      marginBottom: spacing[4],
    }}>
      {suggestions.map((suggestion, index) => (
        <button
          key={index}
          onClick={() => onSuggestionClick(suggestion.text)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: spacing[2],
            padding: `${spacing[3]} ${spacing[4]}`,
            background: colors.dark.bgCard,
            border: `1px solid ${colors.dark.border}`,
            borderRadius: radii.lg,
            cursor: 'pointer',
            transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
            textAlign: 'left',
            width: '100%',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = colors.dark.bgCardHover;
            e.currentTarget.style.borderColor = colors.primary[600];
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = shadows.cardHover;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = colors.dark.bgCard;
            e.currentTarget.style.borderColor = colors.dark.border;
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = shadows.card;
          }}
        >
          <span style={{ fontSize: 20 }}>{suggestion.icon}</span>
          <span style={{
            color: colors.neutral[200],
            fontSize: typography.fontSize.sm,
            fontWeight: 500,
          }}>
            {suggestion.text}
          </span>
        </button>
      ))}
    </div>
  );
};

/**
 * Agent 状态指示器 - Bento 风格标签
 */
const AgentStatusIndicator: React.FC = () => {
  const { agents } = useAgentStore() as { agents: AgentStateItem[] };

  if (agents.length === 0) return null;

  const getAgentIcon = (status: string) => {
    const icons: Record<string, string> = {
      idle: '🟢',
      perceiving: '👁️',
      diagnosing: '🔬',
      remediating: '🔧',
      optimizing: '⚡',
      error: '❌',
    };
    return icons[status] || '🟢';
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      idle: colors.neutral[500],
      perceiving: colors.semantic.info,
      diagnosing: colors.semantic.accent,
      remediating: colors.semantic.warning,
      optimizing: colors.semantic.success,
      error: colors.semantic.error,
    };
    return colorMap[status] || colors.neutral[500];
  };

  return (
    <div style={{
      display: 'flex',
      flexWrap: 'wrap',
      gap: spacing[2],
    }}>
      {agents.map((agent, index) => (
        <div
          key={index}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: spacing[2],
            padding: `${spacing[2]} ${spacing[3]}`,
            background: colors.dark.bgCard,
            border: `1px solid ${getStatusColor(agent.status)}40`,
            borderRadius: radii.full,
            transition: `all ${transitions.durations.fast}`,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = getStatusColor(agent.status);
            e.currentTarget.style.background = `${getStatusColor(agent.status)}10`;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = `${getStatusColor(agent.status)}40`;
            e.currentTarget.style.background = colors.dark.bgCard;
          }}
        >
          <span style={{ fontSize: typography.fontSize.sm }}>{getAgentIcon(agent.status)}</span>
          <span style={{
            color: colors.neutral[300],
            fontSize: typography.fontSize.xs,
            fontWeight: 500,
          }}>
            {agent.name}
          </span>
        </div>
      ))}
    </div>
  );
};

/**
 * 空状态 - Bento 风格
 */
const EmptyState: React.FC<{ onSuggestionClick: (question: string) => void }> = ({ onSuggestionClick }) => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: `${spacing[12]} ${spacing[6]}`,
      textAlign: 'center',
    }}>
      {/* Logo */}
      <div
        style={{
          width: 80,
          height: 80,
          borderRadius: radii.xl,
          background: `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: spacing[5],
          boxShadow: shadows.glow,
          animation: 'pulse 2s ease-in-out infinite',
        }}
      >
        <RobotOutlined style={{ color: '#fff', fontSize: 40 }} />
      </div>

      {/* 标题 */}
      <h2 style={{
        color: colors.neutral[100],
        fontSize: typography.fontSize['2xl'],
        fontWeight: 700,
        margin: `0 0 ${spacing[2]} 0`,
      }}>
        AI 运行态优化助手
      </h2>

      {/* 副标题 */}
      <p style={{
        color: colors.neutral[400],
        fontSize: typography.fontSize.base,
        margin: `0 0 ${spacing[6]} 0`,
        maxWidth: 400,
      }}>
        用自然语言询问系统状态、诊断问题或执行优化
      </p>

      {/* 快捷建议 */}
      <QuickSuggestions onSuggestionClick={onSuggestionClick} />
    </div>
  );
};

/**
 * 输入区域 - Bento 风格
 */
interface InputAreaProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  onSend: () => void;
  isLoading: boolean;
}

const InputArea: React.FC<InputAreaProps> = ({ inputValue, setInputValue, onSend, isLoading }) => {
  return (
    <div style={{
      padding: spacing[4],
      background: colors.dark.bgCard,
      borderRadius: radii.xl,
      border: `1px solid ${colors.dark.border}`,
      boxShadow: shadows.card,
      transition: `all ${transitions.durations.normal}`,
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.borderColor = colors.primary[700];
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.borderColor = colors.dark.border;
    }}
    >
      <TextArea
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyPress={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSend();
          }
        }}
        placeholder="输入问题，例如：'支付服务为什么延迟高？' 或 '帮我诊断系统问题'"
        rows={3}
        disabled={isLoading}
        style={{
          background: 'transparent',
          border: 'none',
          color: colors.neutral[100],
          resize: 'none',
          marginBottom: spacing[3],
          fontSize: typography.fontSize.base,
          padding: 0,
          outline: 'none',
        }}
      />

      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        {/* Agent 状态 */}
        <AgentStatusIndicator />

        {/* 发送按钮 */}
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={onSend}
          loading={isLoading}
          size="large"
          disabled={!inputValue.trim() || isLoading}
          style={{
            background: inputValue.trim() && !isLoading
              ? `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`
              : colors.neutral[700],
            border: 'none',
            borderRadius: radii.full,
            padding: `${spacing[2]} ${spacing[5]}`,
            fontSize: typography.fontSize.base,
            fontWeight: 600,
            boxShadow: inputValue.trim() && !isLoading ? shadows.card : 'none',
            transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
            height: 'auto',
            cursor: inputValue.trim() && !isLoading ? 'pointer' : 'not-allowed',
            opacity: inputValue.trim() && !isLoading ? 1 : 0.5,
          }}
          onMouseEnter={(e) => {
            if (inputValue.trim() && !isLoading) {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = `${shadows.cardHover}, 0 0 20px ${colors.primary[700]}60`;
            }
          }}
          onMouseLeave={(e) => {
            if (inputValue.trim() && !isLoading) {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = shadows.card;
            }
          }}
        >
          发送
        </Button>
      </div>
    </div>
  );
};

/**
 * 主 Chat 组件
 */
const ChatInterface: React.FC<ChatInterfaceProps> = () => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, addMessage, isLoading, setLoading } = useChatStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    addMessage(userMessage);
    setInputValue('');
    setLoading(true);

    try {
      const response = await aiNativeApi.ask(userMessage.content);

      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        confidence: response.confidence,
        actions: response.actions,
      };

      addMessage(aiMessage);
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'system',
        content: `❌ 请求失败：${error instanceof Error ? error.message : '未知错误'}`,
        timestamp: new Date(),
      };
      addMessage(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: colors.dark.bg,
    }}>
      {/* 消息列表 */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: `${spacing[4]} ${spacing[5]}`,
          marginBottom: spacing[4],
        }}
      >
        {messages.length === 0 ? (
          <EmptyState onSuggestionClick={(text) => setInputValue(text)} />
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: spacing[2],
                padding: spacing[3],
                color: colors.neutral[400],
                fontSize: typography.fontSize.sm,
              }}>
                <Spin size="small" />
                <span>AI 正在思考...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* 输入区域 */}
      <div style={{ padding: `0 ${spacing[5]} ${spacing[5]}` }}>
        <InputArea
          inputValue={inputValue}
          setInputValue={setInputValue}
          onSend={handleSend}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};

// Spin 组件导入
const Spin: React.FC<{ size?: 'small' | 'default' | 'large' }> = ({ size = 'default' }) => {
  const sizes = {
    small: 16,
    default: 24,
    large: 32,
  };

  return (
    <div
      style={{
        width: sizes[size],
        height: sizes[size],
        border: `3px solid ${colors.primary[800]}`,
        borderTop: `3px solid ${colors.primary[500]}`,
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
      }}
    />
  );
};

export default ChatInterface;
