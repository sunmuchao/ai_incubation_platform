/**
 * 频道页面组件
 */
'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Folder, Plus, Users, MessageSquare } from 'lucide-react';

interface Channel {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  category_id?: number;
  category_name?: string;
  member_count: number;
  post_count: number;
}

interface Category {
  id: number;
  name: string;
}

export function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // 新建频道表单
  const [newChannel, setNewChannel] = useState({
    name: '',
    description: '',
    category_id: '',
  });

  // 加载频道
  const loadChannels = async () => {
    try {
      const [channelsData, categoriesData] = await Promise.all([
        api.channels.list(),
        api.channels.getCategories(),
      ]);
      setChannels(channelsData);
      setCategories(categoriesData);
    } catch (error) {
      console.error('加载频道失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChannels();
  }, []);

  // 创建频道
  const handleCreate = async () => {
    try {
      await api.channels.create({
        name: newChannel.name,
        description: newChannel.description,
        category_id: newChannel.category_id ? parseInt(newChannel.category_id) : undefined,
      });
      setCreateDialogOpen(false);
      setNewChannel({ name: '', description: '', category_id: '' });
      loadChannels();
    } catch (error) {
      console.error('创建频道失败:', error);
    }
  };

  // 按分类分组
  const channelsByCategory = channels.reduce((acc, channel) => {
    const category = channel.category_name || '未分类';
    if (!acc[category]) acc[category] = [];
    acc[category].push(channel);
    return acc;
  }, {} as Record<string, Channel[]>);

  return (
    <ScrollArea className="h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-4 max-w-5xl mx-auto">
        {/* 页面头部 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Folder className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold">频道广场</h1>
          </div>
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                创建频道
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>创建新频道</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>频道名称</Label>
                  <Input
                    placeholder="请输入频道名称"
                    value={newChannel.name}
                    onChange={(e) =>
                      setNewChannel({ ...newChannel, name: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>频道描述</Label>
                  <Textarea
                    placeholder="请输入频道描述"
                    value={newChannel.description}
                    onChange={(e) =>
                      setNewChannel({ ...newChannel, description: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>所属分类</Label>
                  <select
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    value={newChannel.category_id}
                    onChange={(e) =>
                      setNewChannel({ ...newChannel, category_id: e.target.value })
                    }
                  >
                    <option value="">选择分类</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
                <Button onClick={handleCreate} className="w-full">
                  创建频道
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* 频道列表 */}
        {loading ? (
          <div className="text-center py-12 text-muted-foreground">
            加载中...
          </div>
        ) : channels.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <Folder className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>暂无频道，快来创建第一个频道吧！</p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(channelsByCategory).map(([category, categoryChannels]) => (
              <div key={category}>
                <h2 className="text-lg font-semibold mb-3 text-muted-foreground">
                  {category}
                </h2>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {categoryChannels.map((channel) => (
                    <Card key={channel.id} className="cursor-pointer hover:border-primary/50 transition-all touch-feedback">
                      <CardHeader className="pb-3">
                        <div className="flex items-start gap-3">
                          <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center text-2xl">
                            {channel.icon || '📁'}
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold truncate">{channel.name}</h3>
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {channel.description || '暂无描述'}
                            </p>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {channel.member_count}
                          </span>
                          <span className="flex items-center gap-1">
                            <MessageSquare className="h-3 w-3" />
                            {channel.post_count}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
