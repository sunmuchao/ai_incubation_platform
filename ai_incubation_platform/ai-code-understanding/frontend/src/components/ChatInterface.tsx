// AI Native Chat 聊天界面 - Bento Grid 风格
import React, { useState, useRef, useCallback } from 'react';
import { Send, StopCircle, Sparkles, Bot, User, Zap, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { ChatMessage, StreamEvent, AgentStatus } from '@/types/chat';
import { chatStream } from '@/services/chatApi';
import DependencyGraph from './DependencyGraph';
import AgentStatusDisplay from './AgentStatusDisplay';

interface ChatInterfaceProps {
  initialProject?: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ initialProject = 'default' }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>({
    status: 'idle',
    current_step: '',
    progress: 0,
    steps: [],
  });
  const [project] = useState(initialProject);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 生成消息 ID
  const generateId = () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  // 更新 Agent 状态
  const updateAgentStatus = (type: StreamEvent['type']) => {
    switch (type) {
      case 'thinking':
        setAgentStatus({
          status: 'thinking',
          current_step: '正在理解问题...',
          progress: 20,
          steps: [
            { name: '理解问题', status: 'running' },
            { name: '检索代码', status: 'pending' },
            { name: '分析依赖', status: 'pending' },
            { name: '生成回答', status: 'pending' },
          ],
        });
        break;
      case 'discovery':
        setAgentStatus({
          status: 'searching',
          current_step: '发现相关代码...',
          progress: 50,
          steps: [
            { name: '理解问题', status: 'completed' },
            { name: '检索代码', status: 'running' },
            { name: '分析依赖', status: 'pending' },
            { name: '生成回答', status: 'pending' },
          ],
        });
        break;
      case 'explanation':
        setAgentStatus({
          status: 'analyzing',
          current_step: '生成解释...',
          progress: 75,
          steps: [
            { name: '理解问题', status: 'completed' },
            { name: '检索代码', status: 'completed' },
            { name: '分析依赖', status: 'running' },
            { name: '生成回答', status: 'pending' },
          ],
        });
        break;
      case 'visualization':
        setAgentStatus({
          status: 'generating',
          current_step: '生成可视化...',
          progress: 90,
          steps: [
            { name: '理解问题', status: 'completed' },
            { name: '检索代码', status: 'completed' },
            { name: '分析依赖', status: 'completed' },
            { name: '生成回答', status: 'running' },
          ],
        });
        break;
      case 'suggestion':
        break;
      case 'error':
        setAgentStatus({
          status: 'error',
          current_step: '请求失败',
          progress: 0,
          steps: [],
        });
        break;
      default:
        setAgentStatus({
          status: 'complete',
          current_step: '完成',
          progress: 100,
          steps: [
            { name: '理解问题', status: 'completed' },
            { name: '检索代码', status: 'completed' },
            { name: '分析依赖', status: 'completed' },
            { name: '生成回答', status: 'completed' },
          ],
        });
    }
  };

  // 处理流式响应
  const handleStream = useCallback(async (userMessage: string) => {
    const assistantMsgId = generateId();

    // 添加用户消息
    const userMsg: ChatMessage = {
      id: generateId(),
      type: 'user',
      content: userMessage,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);

    // 添加空的助手消息
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      type: 'explanation',
      content: '',
      timestamp: Date.now(),
      metadata: {
        citations: [],
        code_snippets: [],
        thinking_steps: [],
      },
    };
    setMessages(prev => [...prev, assistantMsg]);

    setIsStreaming(true);

    try {
      for await (const event of chatStream({
        message: userMessage,
        project,
        context: {},
      })) {
        updateAgentStatus(event.type);

        setMessages(prev => {
          const newMessages = [...prev];
          const lastMsgIndex = newMessages.findIndex(m => m.id === assistantMsgId);

          if (lastMsgIndex === -1) return prev;

          const lastMsg = { ...newMessages[lastMsgIndex] };

          switch (event.type) {
            case 'thinking':
              lastMsg.metadata = {
                ...lastMsg.metadata,
                thinking_steps: [
                  ...(lastMsg.metadata?.thinking_steps || []),
                  event.content,
                ],
              };
              break;
            case 'discovery':
            case 'explanation':
            case 'suggestion':
              lastMsg.content = event.content;
              lastMsg.metadata = {
                ...lastMsg.metadata,
                ...event.metadata,
              };
              break;
            case 'visualization':
              lastMsg.metadata = {
                ...lastMsg.metadata,
                visualization: event.content,
              };
              break;
            case 'error':
              lastMsg.type = 'error';
              lastMsg.content = event.content;
              break;
          }

          newMessages[lastMsgIndex] = lastMsg;
          return newMessages;
        });
      }
      updateAgentStatus('done' as any);
    } catch (error: any) {
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsgIndex = newMessages.findIndex(m => m.id === assistantMsgId);

        if (lastMsgIndex === -1) return prev;

        newMessages[lastMsgIndex] = {
          ...newMessages[lastMsgIndex],
          type: 'error',
          content: error.message || '发生未知错误',
        };
        return newMessages;
      });

      setAgentStatus({
        status: 'error',
        current_step: '请求失败',
        progress: 0,
        steps: [],
      });
    } finally {
      setIsStreaming(false);
    }
  }, [project]);

  // 发送消息
  const handleSend = () => {
    const message = input.trim();
    if (!message || isStreaming) return;

    setInput('');
    handleStream(message);
  };

  // 停止生成
  const handleStop = () => {
    setIsStreaming(false);
    setAgentStatus(prev => ({
      ...prev,
      status: 'idle',
      current_step: '已停止',
    }));
  };

  // 按键处理
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 建议问题
  const suggestedQuestions = [
    "这个项目是怎么组织的？",
    "认证逻辑在哪里实现？",
    "帮我画出主要模块的依赖关系",
    "这个代码库使用了哪些设计模式？",
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Agent 状态显示 */}
      {agentStatus.status !== 'idle' && (
        <div className="border-b border-border-light bg-surface/50 backdrop-blur-bento">
          <AgentStatusDisplay status={agentStatus} />
        </div>
      )}

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center">
            {/* Logo 区域 */}
            <div className="mb-8 relative">
              <div className="w-24 h-24 rounded-2xl gradient-accent flex items-center justify-center shadow-glow-accent float">
                <Bot className="w-12 h-12 text-white" />
              </div>
              <div className="absolute -top-2 -right-2 w-8 h-8 rounded-lg bg-surface-lighter border border-border-light flex items-center justify-center animate-pulse">
                <Zap className="w-4 h-4 text-accent" />
              </div>
            </div>

            {/* 标题 */}
            <h2 className="text-2xl font-bold text-text-primary mb-2">AI 代码理解助手</h2>
            <p className="text-text-muted text-center max-w-md mb-8">
              问我任何关于代码的问题，我会帮你理解项目结构、依赖关系和核心逻辑
            </p>

            {/* 建议问题 - Bento Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl w-full">
              {suggestedQuestions.map((question, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(question);
                    inputRef.current?.focus();
                  }}
                  className="group bento-card p-4 text-left hover:border-accent/50 transition-all duration-200 hover:translate-y-[-2px]"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center flex-shrink-0 group-hover:bg-accent/30 transition-colors">
                      <Sparkles className="w-4 h-4 text-accent" />
                    </div>
                    <span className="text-sm text-text-secondary group-hover:text-text-primary transition-colors">
                      {question}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="border-t border-border-light bg-surface/80 backdrop-blur-bento p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <div className="bento-card p-1">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="问我任何关于代码的问题..."
                  className="w-full bg-surface-lighter border border-border-light rounded-xl px-4 py-3 pr-14 resize-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all duration-200 text-text-primary placeholder-text-muted text-sm min-h-[80px] max-h-32"
                  rows={3}
                  disabled={isStreaming}
                />
                <div className="absolute right-2 bottom-2 flex items-center gap-2">
                  {isStreaming ? (
                    <button
                      onClick={handleStop}
                      className="p-2.5 bg-error/20 text-error rounded-lg hover:bg-error/30 transition-colors"
                      title="停止生成"
                    >
                      <StopCircle className="w-5 h-5" />
                    </button>
                  ) : (
                    <button
                      onClick={handleSend}
                      disabled={!input.trim()}
                      className="p-2.5 gradient-accent text-white rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-glow-accent"
                      title="发送消息"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
          <div className="mt-3 text-center">
            <p className="text-xs text-text-muted flex items-center justify-center gap-2">
              <MessageSquare className="w-3 h-3" />
              按 Enter 发送，Shift+Enter 换行
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// 消息气泡组件
const MessageBubble: React.FC<{ message: ChatMessage }> = ({ message }) => {
  const isUser = message.type === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} animate-slide-up`}>
      {/* 头像 */}
      <div className={`flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center ${
        isUser
          ? 'gradient-accent shadow-glow-accent'
          : 'bg-purple-500/20 border border-purple-500/30'
      }`}>
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-purple-400" />
        )}
      </div>

      {/* 消息内容 */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'text-right' : ''}`}>
        <div className={`inline-block text-left px-5 py-4 rounded-2xl ${
          isUser
            ? 'bg-accent/20 border border-accent/30'
            : 'bento-card'
        }`}>
          {message.type === 'user' ? (
            <p className="whitespace-pre-wrap text-text-primary">{message.content}</p>
          ) : (
            <MessageContent message={message} />
          )}
        </div>

        {/* 置信度 */}
        {!isUser && message.metadata?.confidence !== undefined && (
          <div className="mt-2 flex items-center gap-3 text-xs">
            <span className={`flex items-center gap-1 ${
              message.metadata.confidence >= 0.8 ? 'text-success' :
              message.metadata.confidence >= 0.5 ? 'text-warning' : 'text-error'
            }`}>
              <Zap className="w-3 h-3" />
              置信度：{(message.metadata.confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

// 消息内容渲染
const MessageContent: React.FC<{ message: ChatMessage }> = ({ message }) => {
  // 渲染可视化
  if (message.metadata?.visualization) {
    return (
      <div className="space-y-4">
        <VisualizationRenderer data={message.metadata.visualization} />
        {message.content && (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');
                return match ? (
                  <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    );
  }

  // 渲染代码片段
  if (message.metadata?.code_snippets && message.metadata.code_snippets.length > 0) {
    return (
      <div className="space-y-4">
        {message.content && (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        )}
        {message.metadata.code_snippets.map((snippet, i) => (
          <CodeBlock key={i} snippet={snippet} />
        ))}
      </div>
    );
  }

  // 普通文本
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ node, className, children, ...props }: any) {
          const match = /language-(\w+)/.exec(className || '');
          return match ? (
            <SyntaxHighlighter
              style={vscDarkPlus}
              language={match[1]}
              PreTag="div"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          ) : (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
      }}
    >
      {message.content}
    </ReactMarkdown>
  );
};

// 代码块组件
const CodeBlock: React.FC<{ snippet: any }> = ({ snippet }) => {
  return (
    <div className="bento-card overflow-hidden">
      <pre className="bg-base-950 p-4 overflow-auto">
        <code className="text-sm text-text-primary">{snippet.code}</code>
      </pre>
    </div>
  );
};

// 可视化渲染器
const VisualizationRenderer: React.FC<{ data: any }> = ({ data }) => {
  if (!data) return null;

  switch (data.view_type) {
    case 'dependency_graph_view':
    case 'architecture_map_view':
      return <DependencyGraph data={data.data} config={data.config} />;
    default:
      return (
        <pre className="bento-card p-4 overflow-auto text-xs">
          <code className="text-text-secondary">{JSON.stringify(data, null, 2)}</code>
        </pre>
      );
  }
};

export default ChatInterface;
