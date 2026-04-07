/**
 * 通知页面组件
 */
'use client';

import React, { useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAppStore, appActions } from '@/stores/useAppStore';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Bell, CheckCheck, Mail, Heart, MessageSquare, User, AlertCircle } from 'lucide-react';
import { formatDate } from '@/lib/utils';

const iconMap: Record<string, React.ReactNode> = {
  reply: <MessageSquare className="h-4 w-4" />,
  like: <Heart className="h-4 w-4" />,
  mention: <User className="h-4 w-4" />,
  system: <Bell className="h-4 w-4" />,
  approval: <CheckCheck className="h-4 w-4" />,
  rejection: <AlertCircle className="h-4 w-4" />,
  warning: <AlertCircle className="h-4 w-4" />,
};

export function NotificationsPage() {
  const notifications = useAppStore((state) => state.notifications);
  const markAllAsRead = useAppStore((state) => state.markAllNotificationsAsRead);
  const unreadCount = useAppStore((state) => state.notifications.filter((n) => !n.isRead).length);

  useEffect(() => {
    appActions.loadNotifications();
  }, []);

  const handleMarkAllAsRead = async () => {
    await appActions.markAllAsRead();
  };

  return (
    <ScrollArea className="h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-4 max-w-3xl mx-auto">
        {/* 页面头部 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold">通知中心</h1>
            {unreadCount > 0 && (
              <Badge variant="destructive">{unreadCount} 未读</Badge>
            )}
          </div>
          {unreadCount > 0 && (
            <Button variant="outline" size="sm" onClick={handleMarkAllAsRead}>
              全部标记已读
            </Button>
          )}
        </div>

        {/* 通知列表 */}
        {notifications.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>暂无通知</p>
          </div>
        ) : (
          <div className="space-y-2">
            {notifications.map((notification) => (
              <Card
                key={notification.id}
                className={`transition-all touch-feedback ${
                  !notification.isRead ? 'border-primary/50 bg-primary/5' : ''
                }`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center ${
                        !notification.isRead ? 'bg-primary text-primary-foreground' : 'bg-secondary'
                      }`}
                    >
                      {iconMap[notification.type] || <Mail className="h-4 w-4" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">{notification.content}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatDate(notification.createdAt)}
                      </p>
                    </div>
                    {!notification.isRead && (
                      <div className="w-2 h-2 rounded-full bg-primary shrink-0" />
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
