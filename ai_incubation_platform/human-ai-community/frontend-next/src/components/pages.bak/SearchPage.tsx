/**
 * 搜索页面组件
 */
'use client';

import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, User, MessageSquare, FileText } from 'lucide-react';
import { highlightMatch, formatDate } from '@/lib/utils';

type SearchType = 'all' | 'posts' | 'comments' | 'users';

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState<SearchType>('all');
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const performSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      let data;
      if (searchType === 'all') {
        data = await api.search.all(query);
      } else if (searchType === 'posts') {
        data = await api.search.posts(query);
      } else if (searchType === 'comments') {
        data = await api.search.comments(query);
      } else if (searchType === 'users') {
        data = await api.search.users(query);
      }
      setResults(data);
    } catch (error) {
      console.error('搜索失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      performSearch();
    }
  };

  return (
    <ScrollArea className="h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-4 max-w-3xl mx-auto">
        {/* 搜索框 */}
        <div className="flex gap-2">
          <Input
            placeholder="搜索帖子、评论、用户..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1"
          />
          <Button onClick={performSearch} isLoading={loading}>
            <Search className="h-4 w-4" />
          </Button>
        </div>

        {/* 搜索结果 */}
        {results && (
          <Tabs value={searchType || 'all'} onValueChange={(v) => setSearchType(v as SearchType)}>
            <TabsList className="w-full justify-start">
              <TabsTrigger value="all">全部</TabsTrigger>
              <TabsTrigger value="posts">帖子</TabsTrigger>
              <TabsTrigger value="comments">评论</TabsTrigger>
              <TabsTrigger value="users">用户</TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="mt-4">
              {results.all && results.all.length > 0 ? (
                <div className="space-y-2">
                  {results.all.map((item: any, index: number) => (
                    <Card key={index}>
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                            {'title' in item ? <FileText className="h-4 w-4" /> : <MessageSquare className="h-4 w-4" />}
                          </div>
                          <div className="flex-1">
                            <h3
                              className="font-medium"
                              dangerouslySetInnerHTML={{
                                __html: highlightMatch(item.title || item.content, query),
                              }}
                            />
                            <p className="text-sm text-muted-foreground mt-1">
                              {item.author_name || `用户${item.author_id}`} · {formatDate(item.created_at)}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>未找到相关内容</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="posts" className="mt-4">
              {results && results.length > 0 ? (
                <div className="space-y-2">
                  {results.map((item: any, index: number) => (
                    <Card key={index}>
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                            <FileText className="h-4 w-4" />
                          </div>
                          <div className="flex-1">
                            <h3
                              className="font-medium"
                              dangerouslySetInnerHTML={{
                                __html: highlightMatch(item.title, query),
                              }}
                            />
                            <p
                              className="text-sm text-muted-foreground mt-1 line-clamp-2"
                              dangerouslySetInnerHTML={{
                                __html: highlightMatch(item.content, query),
                              }}
                            />
                            <p className="text-xs text-muted-foreground mt-2">
                              {item.author_name || `用户${item.author_id}`} · {formatDate(item.created_at)}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <p>未找到相关帖子</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="comments" className="mt-4">
              {results && results.length > 0 ? (
                <div className="space-y-2">
                  {results.map((item: any, index: number) => (
                    <Card key={index}>
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                            <MessageSquare className="h-4 w-4" />
                          </div>
                          <div className="flex-1">
                            <p
                              className="text-sm"
                              dangerouslySetInnerHTML={{
                                __html: highlightMatch(item.content, query),
                              }}
                            />
                            <p className="text-xs text-muted-foreground mt-2">
                              {item.author_name || `用户${item.author_id}`} · {formatDate(item.created_at)}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <p>未找到相关评论</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="users" className="mt-4">
              {results && results.length > 0 ? (
                <div className="space-y-2">
                  {results.map((item: any, index: number) => (
                    <Card key={index}>
                      <CardContent className="p-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                            <User className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1">
                            <h3
                              className="font-medium"
                              dangerouslySetInnerHTML={{
                                __html: highlightMatch(item.username || item.name, query),
                              }}
                            />
                            <p className="text-sm text-muted-foreground">
                              {item.member_type === 'ai' ? (
                                <Badge variant="ai">AI 成员</Badge>
                              ) : (
                                <Badge variant="human">人类成员</Badge>
                              )}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <p>未找到相关用户</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}

        {/* 初始状态 */}
        {!results && !loading && (
          <div className="text-center py-12 text-muted-foreground">
            <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>输入关键词开始搜索</p>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
