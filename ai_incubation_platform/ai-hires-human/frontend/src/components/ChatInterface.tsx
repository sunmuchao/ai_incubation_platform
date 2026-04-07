import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Space, Avatar, Badge, Dropdown, Menu, Tooltip } from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  DeleteOutlined,
  DownloadOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { chatService, ChatMessage, AgentState } from '../services/chatService';
import AgentStatus from './AgentStatus';
import GenerativeUI from './GenerativeUI';
import designTokens from '../styles/designTokens';

const { TextArea } = Input;

interface ChatInterfaceProps {
  userId?: string;
  onActionSelect?: (action: string, data?: any) => void;
  initialMessage?: string;
}

/**
 * AI Native 对话式主界面 - Bento Grid 风格
 *
 * 核心特性：
 * - Chat-first 交互范式
 * - 自然语言意图理解
 * - Agent 状态可视化
 * - 动态 Generative UI
 * - 建议快捷操作
 */
export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  userId = 'default_user',
  onActionSelect,
  initialMessage,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [agentState, setAgentState] = useState<AgentState | undefined>();
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 初始化欢迎消息
  useEffect(() => {
    const welcomeMessage: ChatMessage = {
      id: 'welcome',
      role: 'assistant',
      content: `您好！我是 AI 招聘助手，可以帮助您：

• 发布任务：「帮我发布一个线下采集任务，需要到北京现场拍照」
• 搜索工人：「找会数据标注的工人」
• 匹配工人：「为任务 task-123 匹配合适的工人」
• 查询状态：「查询任务 task-123 的状态」
• 验收交付：「验收任务 task-123 的交付物」

请告诉我您想做什么？`,
      timestamp: new Date(),
      suggestions: [
        '发布一个线下采集任务',
        '搜索数据标注相关的工人',
        '查看我的任务列表',
        '匹配工人到我的任务',
      ],
    };
    setMessages([welcomeMessage]);
    setSuggestions(welcomeMessage.suggestions || []);
  }, []);

  // 处理发送消息
  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isThinking) return;

    // 添加用户消息
    const userMessage = chatService.createUserMessage(content);
    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsThinking(true);
    setAgentState({ thinking: true, executing: false });

    try {
      // 发送消息到后端
      const response = await chatService.sendMessage({
        message: content,
        user_id: userId,
        context: {
          last_message: content,
          conversation_length: messages.length,
        },
      });

      // 更新建议
      if (response.suggestions && response.suggestions.length > 0) {
        setSuggestions(response.suggestions);
      }

      // 添加 AI 响应
      setMessages((prev) => [...prev, response]);
    } catch (error) {
      console.error('发送消息失败:', error);
      const errorMessage: ChatMessage = {
        id: `msg_error_${Date.now()}`,
        role: 'system',
        content: '抱歉，处理您的请求时出现了错误，请稍后重试。',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsThinking(false);
      setAgentState(undefined);
    }
  };

  // 处理建议点击
  const handleSuggestionClick = (suggestion: string) => {
    handleSendMessage(suggestion);
  };

  // 处理 Generative UI 中的操作
  const handleUIAction = (action: string, data?: any) => {
    if (onActionSelect) {
      onActionSelect(action, data);
    } else {
      // 默认行为：将操作转换为自然语言消息
      const actionMessages: Record<string, string> = {
        view_task: `查看任务 ${data?.id}`,
        match_worker: `为任务 ${data?.id} 匹配工人`,
        hire_worker: `雇佣工人 ${data?.name}`,
        assign_worker: `分配工人 ${data?.worker_id} 到任务 ${data?.task_id}`,
        cancel_task: `取消任务 ${data?.id}`,
        approve_task: `批准任务完成`,
        view_worker: `查看工人 ${data?.name} 的详情`,
      };
      const message = actionMessages[action] || `执行操作：${action}`;
      handleSendMessage(message);
    }
  };

  // 清除对话历史
  const handleClearHistory = async () => {
    await chatService.clearHistory(userId);
    setMessages([]);
    setSuggestions([]);
  };

  // 导出对话
  const handleExport = () => {
    const exportData = messages.map((m) => ({
      role: m.role,
      content: m.content,
      timestamp: m.timestamp.toISOString(),
    }));
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat_history_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 下拉菜单
  const menu = (
    <Menu>
      <Menu.Item key="export" onClick={handleExport} icon={<DownloadOutlined />}>
        导出对话
      </Menu.Item>
      <Menu.Item key="clear" onClick={handleClearHistory} danger icon={<DeleteOutlined />}>
        清除历史
      </Menu.Item>
      <Menu.Item key="settings" icon={<SettingOutlined />}>
        设置
      </Menu.Item>
    </Menu>
  );

  return (
    <div style={styles.container}>
      {/* 顶部工具栏 - Bento 卡片风格 */}
      <div style={styles.header}>
        <Space>
          <div style={styles.logoIcon}>
            <RobotOutlined />
          </div>
          <span style={styles.title}>AI 招聘助手</span>
          <Tooltip title="DeerFlow 2.0 驱动">
            <Badge
              count="AI Native"
              style={{
                backgroundColor: designTokens.colors.green[600],
                fontSize: 10,
                fontWeight: 600,
              }}
            />
          </Tooltip>
        </Space>
        <Dropdown overlay={menu} trigger={['click']}>
          <Button
            type="text"
            icon={<SettingOutlined />}
            style={{
              borderRadius: designTokens.radii.md,
              transition: designTokens.transitions.all,
            }}
          />
        </Dropdown>
      </div>

      {/* Agent 状态 - Bento 卡片风格 */}
      <div style={styles.agentStatusContainer}>
        <AgentStatus agentState={agentState} visible={isThinking || !!agentState} />
      </div>

      {/* 消息列表 */}
      <div style={styles.messagesContainer}>
        {messages.map((message) => (
          <div
            key={message.id}
            style={{
              ...styles.messageRow,
              justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            {message.role === 'assistant' && (
              <Avatar
                style={{
                  backgroundColor: designTokens.colors.blue[500],
                  marginRight: 8,
                  boxShadow: designTokens.shadows.card,
                }}
                icon={<RobotOutlined />}
              />
            )}
            <div
              style={{
                ...styles.messageBubble,
                backgroundColor:
                  message.role === 'user'
                    ? designTokens.colors.blue[600]
                    : message.role === 'system'
                    ? designTokens.colors.amber[50]
                    : '#ffffff',
                color: message.role === 'user' ? '#fff' : designTokens.semanticColors.text.primary,
                border: message.role !== 'user' ? `1px solid ${designTokens.semanticColors.border.subtle}` : 'none',
                boxShadow: message.role !== 'user' ? designTokens.shadows.card : 'none',
              }}
            >
              <div style={styles.messageContent}>{message.content}</div>

              {/* Generative UI 渲染 */}
              {message.role === 'assistant' && message.action && (
                <GenerativeUI message={message} onActionSelect={handleUIAction} />
              )}

              {/* 建议操作 */}
              {message.suggestions && message.suggestions.length > 0 && (
                <div style={styles.suggestionsContainer}>
                  <Space wrap size="small">
                    <BulbOutlined style={{ color: designTokens.colors.amber[600] }} />
                    {message.suggestions.map((suggestion, index) => (
                      <Button
                        key={index}
                        type="default"
                        size="small"
                        onClick={() => handleSuggestionClick(suggestion)}
                        style={{
                          border: `1px solid ${designTokens.semanticColors.border.subtle}`,
                          backgroundColor: '#ffffff',
                          borderRadius: designTokens.radii.md,
                          transition: designTokens.transitions.all,
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = designTokens.semanticColors.background.hover;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = '#ffffff';
                        }}
                      >
                        {suggestion}
                      </Button>
                    ))}
                  </Space>
                </div>
              )}

              <div style={styles.messageTime}>
                {message.timestamp.toLocaleTimeString('zh-CN', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>

            {message.role === 'user' && (
              <Avatar
                style={{
                  backgroundColor: designTokens.colors.green[600],
                  marginLeft: 8,
                  boxShadow: designTokens.shadows.card,
                }}
                icon={<UserOutlined />}
              />
            )}
          </div>
        ))}

        {/* 思考中状态 */}
        {isThinking && (
          <div style={styles.messageRow}>
            <Avatar
              style={{
                backgroundColor: designTokens.colors.blue[500],
                marginRight: 8,
                boxShadow: designTokens.shadows.card,
              }}
              icon={<RobotOutlined />}
            />
            <div style={styles.thinkingBubble}>
              <Space>
                <span>AI 正在思考</span>
                <span className="thinking-dots">...</span>
              </Space>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div style={styles.inputContainer}>
        {/* 快捷建议 */}
        {suggestions.length > 0 && (
          <div style={styles.quickSuggestions}>
            <Space wrap size="small">
              <ThunderboltOutlined style={{ color: designTokens.colors.amber[600] }} />
              {suggestions.map((suggestion, index) => (
                <Button
                  key={index}
                  type="link"
                  size="small"
                  onClick={() => handleSuggestionClick(suggestion)}
                  style={{
                    padding: 0,
                    height: 'auto',
                    color: designTokens.colors.blue[600],
                  }}
                >
                  {suggestion}
                </Button>
              ))}
            </Space>
          </div>
        )}

        <div style={styles.inputWrapper}>
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
            placeholder="输入消息... (Shift+Enter 换行)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{
              ...styles.textArea,
              borderRadius: designTokens.radii.lg,
              border: `1px solid ${designTokens.semanticColors.border.default}`,
              transition: designTokens.transitions.all,
            }}
            onFocus={(e) => {
              e.target.style.borderColor = designTokens.colors.blue[400];
              e.target.style.boxShadow = `0 0 0 2px ${designTokens.colors.blue[50]}`;
            }}
            onBlur={(e) => {
              e.target.style.borderColor = designTokens.semanticColors.border.default;
              e.target.style.boxShadow = 'none';
            }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => handleSendMessage(inputValue)}
            loading={isThinking}
            style={{
              ...styles.sendButton,
              borderRadius: designTokens.radii.lg,
              background: `linear-gradient(135deg, ${designTokens.colors.blue[600]}, ${designTokens.colors.blue[500]})`,
              boxShadow: designTokens.shadows.card,
              transition: designTokens.transitions.all,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.boxShadow = designTokens.shadows.cardHover;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = designTokens.shadows.card;
            }}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: 'transparent',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: `${designTokens.spacing.md} ${designTokens.spacing.lg}`,
    backgroundColor: '#ffffff',
    borderBottom: `1px solid ${designTokens.semanticColors.border.subtle}`,
  },
  logoIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 36,
    height: 36,
    borderRadius: designTokens.radii.lg,
    background: `linear-gradient(135deg, ${designTokens.colors.blue[100]}, ${designTokens.colors.blue[50]})`,
    color: designTokens.colors.blue[600],
    fontSize: 20,
  },
  title: {
    fontSize: 16,
    fontWeight: 600,
    color: designTokens.semanticColors.text.primary,
  },
  agentStatusContainer: {
    padding: `${designTokens.spacing.sm} ${designTokens.spacing.lg}`,
    backgroundColor: '#ffffff',
    borderBottom: `1px solid ${designTokens.semanticColors.border.subtle}`,
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: designTokens.spacing.lg,
  },
  messageRow: {
    display: 'flex',
    marginBottom: designTokens.spacing.lg,
  },
  messageBubble: {
    maxWidth: '70%',
    padding: designTokens.spacing.md,
    borderRadius: designTokens.radii.lg,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  messageContent: {
    whiteSpace: 'pre-wrap',
    lineHeight: 1.6,
  },
  suggestionsContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTop: `1px solid ${designTokens.semanticColors.border.subtle}`,
  },
  messageTime: {
    fontSize: 11,
    color: designTokens.semanticColors.text.tertiary,
    marginTop: 8,
    textAlign: 'right',
  },
  thinkingBubble: {
    padding: `${designTokens.spacing.sm} ${designTokens.spacing.md}`,
    backgroundColor: '#ffffff',
    borderRadius: designTokens.radii.lg,
    color: designTokens.semanticColors.text.secondary,
    border: `1px solid ${designTokens.semanticColors.border.subtle}`,
    boxShadow: designTokens.shadows.card,
  },
  inputContainer: {
    padding: designTokens.spacing.lg,
    backgroundColor: '#ffffff',
    borderTop: `1px solid ${designTokens.semanticColors.border.subtle}`,
  },
  quickSuggestions: {
    marginBottom: designTokens.spacing.md,
    padding: `${designTokens.spacing.sm} ${designTokens.spacing.md}`,
    backgroundColor: designTokens.colors.green[50],
    borderRadius: designTokens.radii.lg,
    border: `1px solid ${designTokens.colors.green[200]}`,
  },
  inputWrapper: {
    display: 'flex',
    gap: designTokens.spacing.md,
  },
  textArea: {
    flex: 1,
    resize: 'none',
    padding: `${designTokens.spacing.md} ${designTokens.spacing.lg}`,
    border: `1px solid ${designTokens.semanticColors.border.default}`,
  },
  sendButton: {
    height: 'auto',
    alignSelf: 'flex-end',
    padding: `${designTokens.spacing.sm} ${designTokens.spacing.lg}`,
  },
};

export default ChatInterface;
