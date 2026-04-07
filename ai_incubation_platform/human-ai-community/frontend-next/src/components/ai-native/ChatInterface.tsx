/**
 * AI Agent Chat 组件
 * 对话式交互主界面
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useAINativeStore } from '@/stores/useAINativeStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import {
  Send,
  Bot,
  User,
  Sparkles,
  Loader2,
  X,
  Trash2,
  MessageSquare,
} from 'lucide-react';
import type { ChatMessage, SuggestedAction } from '@/types/ai-native';

interface ChatInterfaceProps {
  onNavigate?: (page: string, params?: Record<string, any>) => void;
}

export function ChatInterface({ onNavigate }: ChatInterfaceProps) {
  const {
    conversations,
    activeConversationId,
    agents,
    agentsLoading,
    currentUserId,
    sendMessage,
    loadConversation,
    clearConversation,
    setActiveConversation,
  } = useAINativeStore();

  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const activeConversation = activeConversationId
    ? conversations.get(activeConversationId)
    : null;

  const messages = activeConversation?.messages || [];

  // 滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // 加载 Agents
  useEffect(() => {
    if (agents.length === 0 && !agentsLoading) {
      // 延迟加载 agents
    }
  }, [agents, agentsLoading]);

  // 处理发送消息
  const handleSend = async () => {
    if (!inputValue.trim() || isSending) return;

    const message = inputValue.trim();
    setInputValue('');
    setIsSending(true);

    try {
      await sendMessage(message);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };

  // 处理建议操作
  const handleSuggestedAction = async (action: SuggestedAction) => {
    if (action.action === 'select_topic' && action.topics) {
      // 显示主题选择
      setInputValue(`我想了解关于 ${action.topics[0]} 的内容`);
    } else if (action.action === 'view_report') {
      onNavigate?.('governance');
    } else if (action.action === 'view_stats') {
      onNavigate?.('stats');
    } else {
      // 默认处理：发送建议的文本
      if (action.label) {
        setInputValue(action.label);
      }
    }
  };

  // 处理按键
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 获取 AI Agent 头像
  const getAgentAvatar = () => {
    if (agents.length > 0) {
      return agents[0].avatar || '🤖';
    }
    return '🤖';
  };

  // 格式化时间
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  // 获取最后一个消息的建议操作
  const lastMessage = messages[messages.length - 1];
  const suggestedActions = lastMessage?.suggestedActions || [];

  return (
    <div className="flex flex-col h-full">
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-card">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-xl">
            {getAgentAvatar()}
          </div>
          <div>
            <h2 className="font-semibold text-foreground">
              {agents.length > 0 ? agents[0].name : '社区 AI 助手'}
            </h2>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs text-muted-foreground">在线</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {activeConversationId && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => clearConversation(activeConversationId)}
              className="text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setActiveConversation(null)}
            className="text-muted-foreground"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 消息列表 */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        <div className="space-y-4 max-w-3xl mx-auto">
          {messages.length === 0 && (
            <WelcomeMessage onSuggestionClick={handleSuggestedAction} />
          )}

          {messages.map((message, index) => (
            <ChatMessageItem
              key={index}
              message={message}
              isUser={message.role === 'user'}
              onActionClick={handleSuggestedAction}
            />
          ))}

          {isSending && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>AI 正在思考...</span>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* 建议操作 */}
      {suggestedActions.length > 0 && (
        <div className="p-4 border-t border-border bg-card/50">
          <div className="flex flex-wrap gap-2 max-w-3xl mx-auto">
            {suggestedActions.map((action, index) => (
              <Badge
                key={index}
                variant="secondary"
                className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                onClick={() => handleSuggestedAction(action)}
              >
                <Sparkles className="h-3 w-3 mr-1" />
                {action.label}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* 输入区域 */}
      <div className="p-4 border-t border-border bg-card">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="与 AI 助手对话，询问任何问题..."
            className="flex-1"
            disabled={isSending}
          />
          <Button
            onClick={handleSend}
            disabled={!inputValue.trim() || isSending}
            size="icon"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

// 欢迎消息组件
function WelcomeMessage({
  onSuggestionClick,
}: {
  onSuggestionClick: (action: SuggestedAction) => void;
}) {
  const suggestions: SuggestedAction[] = [
    {
      action: 'find_members',
      label: '找志同道合的人',
    },
    {
      action: 'get_recommendations',
      label: '获取内容推荐',
    },
    {
      action: 'report_issue',
      label: '举报问题',
    },
    {
      action: 'ask_rules',
      label: '了解社区规则',
    },
  ];

  return (
    <Card className="p-6 bg-gradient-to-br from-primary/10 to-blue-500/10 border-primary/20">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center text-2xl flex-shrink-0">
          🤖
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-lg mb-2">欢迎来到 Human-AI Community</h3>
          <p className="text-muted-foreground mb-4">
            我是社区 AI 助手，可以帮您：
          </p>
          <ul className="space-y-2 text-sm text-muted-foreground mb-4">
            <li className="flex items-center gap-2">
              <span className="text-primary">•</span>
              推荐志同道合的社区成员
            </li>
            <li className="flex items-center gap-2">
              <span className="text-primary">•</span>
              推荐相关内容和活动
            </li>
            <li className="flex items-center gap-2">
              <span className="text-primary">•</span>
              处理违规内容举报
            </li>
            <li className="flex items-center gap-2">
              <span className="text-primary">•</span>
              解答社区规则问题
            </li>
          </ul>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion, index) => (
              <Badge
                key={index}
                variant="outline"
                className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                onClick={() => onSuggestionClick(suggestion)}
              >
                {suggestion.label}
              </Badge>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

// 聊天消息项组件
interface ChatMessageItemProps {
  message: ChatMessage;
  isUser: boolean;
  onActionClick: (action: SuggestedAction) => void;
}

function ChatMessageItem({ message, isUser, onActionClick }: ChatMessageItemProps) {
  return (
    <div
      className={cn(
        'flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* 头像 */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          isUser ? 'bg-blue-500 text-white' : 'bg-primary/20 text-primary'
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* 消息内容 */}
      <div
        className={cn(
          'max-w-[80%] rounded-2xl p-4',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-secondary text-secondary-foreground'
        )}
      >
        <div className="whitespace-pre-wrap text-sm">{message.content}</div>
        <div
          className={cn(
            'text-xs mt-2',
            isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
          )}
        >
          {formatTime(message.timestamp)}
        </div>

        {/* 渲染建议操作 */}
        {!isUser && message.suggestedActions && message.suggestedActions.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3 pt-3 border-t border-border/50">
            {message.suggestedActions.map((action, index) => (
              <button
                key={index}
                onClick={() => onActionClick(action)}
                className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
              >
                <Sparkles className="h-3 w-3 inline mr-1" />
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function formatTime(timestamp: string) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}
