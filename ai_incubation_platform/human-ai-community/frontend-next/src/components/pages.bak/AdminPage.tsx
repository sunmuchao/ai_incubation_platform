/**
 * 管理后台页面组件
 */
'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/lib/api';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Users,
  FileText,
  AlertCircle,
  CheckCircle,
  Activity,
  Shield,
} from 'lucide-react';
import { formatDate } from '@/lib/utils';

interface GovernanceStats {
  total_users: number;
  total_posts: number;
  pending_reviews: number;
  auto_approval_rate: number;
}

interface ReviewItem {
  id: string;
  content_type: string;
  content_id: string;
  reason: string;
  status: string;
  created_at: string;
}

export function AdminPage() {
  const [stats, setStats] = useState<GovernanceStats | null>(null);
  const [reviewQueue, setReviewQueue] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statsData, queueData] = await Promise.all([
          api.governance.getStats(),
          api.governance.getReviewQueue(),
        ]);
        setStats(statsData);
        setReviewQueue(queueData.pending || []);
      } catch (error) {
        console.error('加载数据失败:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const handleApprove = async (contentType: string, contentId: string) => {
    try {
      // TODO: 实现审核通过逻辑
      console.log('Approving:', contentType, contentId);
    } catch (error) {
      console.error('审核失败:', error);
    }
  };

  const handleReject = async (contentType: string, contentId: string) => {
    try {
      // TODO: 实现审核拒绝逻辑
      console.log('Rejecting:', contentType, contentId);
    } catch (error) {
      console.error('审核失败:', error);
    }
  };

  if (loading) {
    return (
      <ScrollArea className="h-[calc(100vh-4rem)]">
        <div className="p-4 text-center text-muted-foreground">加载中...</div>
      </ScrollArea>
    );
  }

  return (
    <ScrollArea className="h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-4 max-w-5xl mx-auto">
        {/* 页面头部 */}
        <div className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">管理后台</h1>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Users className="h-4 w-4" />
                <span className="text-xs">总用户数</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_users || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2 text-muted-foreground">
                <FileText className="h-4 w-4" />
                <span className="text-xs">总帖子数</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_posts || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2 text-muted-foreground">
                <AlertCircle className="h-4 w-4" />
                <span className="text-xs">待审核</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-500">
                {stats?.pending_reviews || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2 text-muted-foreground">
                <CheckCircle className="h-4 w-4" />
                <span className="text-xs">自动审核率</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-500">
                {stats?.auto_approval_rate || 0}%
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 标签页 */}
        <Tabs defaultValue="review">
          <TabsList>
            <TabsTrigger value="review">审核队列</TabsTrigger>
            <TabsTrigger value="stats">数据统计</TabsTrigger>
            <TabsTrigger value="settings">系统设置</TabsTrigger>
          </TabsList>

          <TabsContent value="review" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5" />
                  待审核内容
                </CardTitle>
              </CardHeader>
              <CardContent>
                {reviewQueue.length > 0 ? (
                  <div className="space-y-3">
                    {reviewQueue.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between p-4 rounded-lg bg-secondary"
                      >
                        <div className="flex items-center gap-3">
                          <Badge variant="outline">{item.content_type}</Badge>
                          <span className="text-sm">{item.reason}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(item.created_at)}
                          </span>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="default"
                            onClick={() =>
                              handleApprove(item.content_type, item.content_id)
                            }
                          >
                            通过
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() =>
                              handleReject(item.content_type, item.content_id)
                            }
                          >
                            拒绝
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <CheckCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>暂无待审核内容</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="stats" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  详细统计
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">统计功能开发中...</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="settings" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle>系统设置</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">设置功能开发中...</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </ScrollArea>
  );
}
