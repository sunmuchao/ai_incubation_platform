/**
 * 帖子详情组件
 */
'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Post, Comment } from '@/types';
import { api } from '@/lib/api';
import { formatDate, formatNumber } from '@/lib/utils';
import { MessageSquare, Eye, Heart, Share2, ArrowLeft } from 'lucide-react';

interface PostDetailProps {
  post: Post;
  onBack?: () => void;
}

export function PostDetail({ post, onBack }: PostDetailProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentContent, setCommentContent] = useState('');
  const [loading, setLoading] = useState(false);
  const isAI = post.authorType === 'ai';

  // 加载评论
  useEffect(() => {
    const loadComments = async () => {
      try {
        const data = await api.posts.getComments(post.id);
        setComments(data);
      } catch (error) {
        console.error('加载评论失败:', error);
      }
    };
    loadComments();
  }, [post.id]);

  // 发表评论
  const handleSubmitComment = async () => {
    if (!commentContent.trim()) return;

    setLoading(true);
    try {
      const newComment = await api.comments.create({
        post_id: post.id,
        content: commentContent,
        author_id: '1', // TODO: 从当前用户获取
      });
      setComments([newComment, ...comments]);
      setCommentContent('');
    } catch (error) {
      console.error('发表评论失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 返回按钮 */}
      <Button variant="ghost" onClick={onBack} className="gap-2">
        <ArrowLeft className="h-4 w-4" />
        返回
      </Button>

      {/* 帖子详情 */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={isAI ? 'ai' : 'human'}>
                {isAI ? '🤖 AI' : '👤 人类'}
              </Badge>
              <span className="text-sm font-medium text-muted-foreground">
                {post.authorName || `用户${post.authorId}`}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatDate(post.createdAt)}
              </span>
            </div>

            {post.channelName && (
              <Badge variant="outline">{post.channelName}</Badge>
            )}
          </div>

          <h1 className="text-2xl font-bold mt-4">{post.title}</h1>

          {post.tags && post.tags.length > 0 && (
            <div className="flex gap-1 flex-wrap mt-2">
              {post.tags.map((tag, index) => (
                <span key={index} className="text-tag text-sm text-primary">
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </CardHeader>

        <CardContent>
          <p className="text-base text-foreground whitespace-pre-wrap leading-relaxed">
            {post.content}
          </p>

          {/* 统计信息 */}
          <div className="flex items-center gap-4 mt-6 pt-4 border-t border-border text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Heart className="h-4 w-4" />
              {formatNumber(post.upvotes)}
            </span>
            <span className="flex items-center gap-1">
              <MessageSquare className="h-4 w-4" />
              {formatNumber(post.commentCount)}
            </span>
            <span className="flex items-center gap-1">
              <Eye className="h-4 w-4" />
              {formatNumber(post.views)}
            </span>
            <Button variant="ghost" size="sm" className="gap-1">
              <Share2 className="h-4 w-4" />
              分享
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 评论区 */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            评论 ({comments.length})
          </h2>
        </CardHeader>

        <CardContent>
          {/* 发表评论 */}
          <div className="mb-6 space-y-2">
            <Textarea
              placeholder="写下你的评论..."
              value={commentContent}
              onChange={(e) => setCommentContent(e.target.value)}
              className="min-h-[100px]"
            />
            <Button onClick={handleSubmitComment} isLoading={loading}>
              发表评论
            </Button>
          </div>

          {/* 评论列表 */}
          <div className="space-y-4">
            {comments.map((comment) => (
              <div
                key={comment.id}
                className="p-4 rounded-lg bg-secondary/50 border border-border"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant={comment.authorType === 'ai' ? 'ai' : 'human'} className="text-xs">
                    {comment.authorType === 'ai' ? 'AI' : '人类'}
                  </Badge>
                  <span className="text-sm font-medium">
                    {comment.authorName || `用户${comment.authorId}`}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(comment.createdAt)}
                  </span>
                </div>
                <p className="text-sm text-foreground whitespace-pre-wrap">
                  {comment.content}
                </p>
              </div>
            ))}

            {comments.length === 0 && (
              <p className="text-center text-muted-foreground py-8">
                暂无评论，快来抢沙发吧！
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
