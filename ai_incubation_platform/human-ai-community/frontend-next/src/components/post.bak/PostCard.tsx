/**
 * 帖子卡片组件
 */
'use client';

import React from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Post } from '@/types';
import { formatDate, formatNumber, truncate } from '@/lib/utils';
import { MessageSquare, Eye, Heart, Flame, Share2, Bookmark } from 'lucide-react';

interface PostCardProps {
  post: Post;
  onClick?: (post: Post) => void;
  onLike?: (post: Post) => void;
  onBookmark?: (post: Post) => void;
  onShare?: (post: Post) => void;
}

export function PostCard({ post, onClick, onLike, onBookmark, onShare }: PostCardProps) {
  const isAI = post.authorType === 'ai';
  const isHybrid = post.authorType === 'hybrid';

  return (
    <Card
      className="group cursor-pointer transition-all duration-200 hover:border-primary/50 hover:shadow-lg touch-feedback"
      onClick={() => onClick?.(post)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            {/* 作者类型标识 */}
            <Badge variant={isAI ? 'ai' : isHybrid ? 'secondary' : 'human'} className={isAI ? 'ai-badge' : 'human-badge'}>
              {isAI ? '🤖 AI' : isHybrid ? '👤 + AI' : '👤 人类'}
            </Badge>

            {/* 作者名称 */}
            <span className="text-sm font-medium text-muted-foreground">
              {post.authorName || `用户${post.authorId}`}
            </span>

            {/* 发布时间 */}
            <span className="text-xs text-muted-foreground">
              {formatDate(post.createdAt)}
            </span>

            {/* AI 置信度 (如果有) */}
            {post.aiConfidence !== undefined && (
              <span className="text-xs text-blue-400">
                AI 置信度：{Math.round(post.aiConfidence * 100)}%
              </span>
            )}
          </div>

          {/* 频道标签 */}
          {post.channelName && (
            <Badge variant="outline" className="shrink-0">
              {post.channelName}
            </Badge>
          )}
        </div>

        {/* 帖子标题 */}
        <h3 className="text-lg font-semibold line-clamp-2 group-hover:text-primary transition-colors">
          {post.title}
        </h3>

        {/* 标签 */}
        {post.tags && post.tags.length > 0 && (
          <div className="flex gap-1 flex-wrap">
            {post.tags.slice(0, 5).map((tag, index) => (
              <span key={index} className="text-tag text-xs text-primary">
                #{tag}
              </span>
            ))}
          </div>
        )}
      </CardHeader>

      <CardContent>
        {/* 帖子内容预览 */}
        <p className="text-sm text-muted-foreground line-clamp-3 mb-4 whitespace-pre-wrap">
          {truncate(post.content, 300)}
        </p>

        {/* 底部统计和操作 */}
        <div className="flex items-center justify-between gap-2 pt-3 border-t border-border">
          {/* 统计信息 */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Heart className="h-3.5 w-3.5" />
              {formatNumber(post.upvotes)}
            </span>
            <span className="flex items-center gap-1">
              <MessageSquare className="h-3.5 w-3.5" />
              {formatNumber(post.commentCount)}
            </span>
            <span className="flex items-center gap-1">
              <Eye className="h-3.5 w-3.5" />
              {formatNumber(post.views)}
            </span>
            {post.heatScore !== undefined && post.heatScore > 0 && (
              <span className="flex items-center gap-1 text-orange-500 heat-indicator">
                <Flame className="h-3.5 w-3.5" />
                {formatNumber(post.heatScore)}
              </span>
            )}
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center gap-1 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={(e) => {
                e.stopPropagation();
                onLike?.(post);
              }}
            >
              <Heart className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={(e) => {
                e.stopPropagation();
                onBookmark?.(post);
              }}
            >
              <Bookmark className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 hidden sm:flex"
              onClick={(e) => {
                e.stopPropagation();
                onShare?.(post);
              }}
            >
              <Share2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
