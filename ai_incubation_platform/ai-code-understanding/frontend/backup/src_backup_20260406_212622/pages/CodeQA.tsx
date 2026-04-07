// 智能问答页面
import React, { useState } from 'react';
import { Send, Bot, User, BookOpen, Sparkles, ChevronRight } from 'lucide-react';
import { docQaApi } from '@/services/api';
import ReactMarkdown from 'react-markdown';
import { toast } from 'sonner';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  confidence?: number;
  followUpQuestions?: string[];
}

const CodeQA: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [projectName, setProjectName] = useState('ai-code-understanding');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  const handleAsk = async () => {
    if (!question.trim()) {
      toast.warning('请输入问题');
      return;
    }

    const userMessage: Message = {
      role: 'user',
      content: question,
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuestion('');
    setLoading(true);

    try {
      const response = await docQaApi.ask({
        question: userMessage.content,
        project_name: projectName,
        max_context_chunks: 5,
      });

      if (response.success && response.data) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: response.data.answer,
          sources: response.data.sources,
          confidence: response.data.confidence,
          followUpQuestions: response.data.follow_up_questions,
        };
        setMessages((prev) => [...prev, assistantMessage]);
        toast.success('答案生成成功');
      }
    } catch (error: any) {
      toast.error('回答失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <div className="h-[calc(100vh-12rem)] flex gap-4">
      {/* 左侧：问答区域 */}
      <div className="flex-1 bg-surface border border-border rounded-xl flex flex-col">
        {/* 消息列表 */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-muted">
              <Bot className="w-16 h-16 mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">智能代码助手</p>
              <p className="text-sm">询问关于代码库的任何问题</p>
              <div className="mt-6 grid grid-cols-2 gap-2 max-w-md">
                {[
                  '项目的整体架构是怎样的？',
                  '用户认证流程是怎样的？',
                  '有哪些主要的入口点？',
                  '解释一下核心模块的职责',
                ].map((suggestion, i) => (
                  <button
                    key={i}
                    onClick={() => setQuestion(suggestion)}
                    className="p-3 bg-card hover:bg-card/80 rounded-lg text-sm text-left transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-accent" />
                      {suggestion}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    message.role === 'user' ? 'bg-accent' : 'bg-purple-500'
                  }`}
                >
                  {message.role === 'user' ? (
                    <User className="w-5 h-5" />
                  ) : (
                    <Bot className="w-5 h-5" />
                  )}
                </div>
                <div
                  className={`flex-1 rounded-xl p-4 ${
                    message.role === 'user' ? 'bg-accent text-white' : 'bg-card'
                  }`}
                >
                  {message.role === 'assistant' ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p>{message.content}</p>
                  )}

                  {/* 置信度 */}
                  {message.confidence !== undefined && (
                    <div className="mt-3 flex items-center gap-2 text-xs opacity-70">
                      <span>置信度:</span>
                      <div className="w-24 h-2 bg-black/30 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            message.confidence >= 0.8
                              ? 'bg-green-500'
                              : message.confidence >= 0.6
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${message.confidence * 100}%` }}
                        />
                      </div>
                      <span>{Math.round(message.confidence * 100)}%</span>
                    </div>
                  )}

                  {/* 来源引用 */}
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-white/10">
                      <p className="text-xs opacity-70 mb-2 flex items-center gap-1">
                        <BookOpen className="w-3 h-3" />
                        来源引用:
                      </p>
                      <div className="space-y-1">
                        {message.sources.slice(0, 3).map((source, i) => (
                          <div
                            key={i}
                            className="text-xs opacity-70 font-mono bg-black/20 rounded px-2 py-1"
                          >
                            {source.file_path}:{source.start_line}-{source.end_line}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 后续问题 */}
                  {message.followUpQuestions && message.followUpQuestions.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-white/10">
                      <p className="text-xs opacity-70 mb-2">相关问题:</p>
                      <div className="flex flex-wrap gap-2">
                        {message.followUpQuestions.map((q, i) => (
                          <button
                            key={i}
                            onClick={() => setQuestion(q)}
                            className="text-xs bg-white/10 hover:bg-white/20 px-2 py-1 rounded transition-colors flex items-center gap-1"
                          >
                            {q}
                            <ChevronRight className="w-3 h-3" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center">
                <Bot className="w-5 h-5" />
              </div>
              <div className="bg-card rounded-xl p-4">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 输入区 */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-2 mb-2">
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-accent"
              placeholder="项目名称"
            />
          </div>
          <div className="flex gap-2">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1 bg-background border border-border rounded-lg px-4 py-3 focus:border-accent resize-none"
              placeholder="询问关于代码库的问题..."
              rows={2}
            />
            <button
              onClick={handleAsk}
              disabled={loading || !question.trim()}
              className="bg-accent hover:bg-accent/90 text-white rounded-lg px-6 transition-colors disabled:opacity-50 flex items-center justify-center"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CodeQA;
