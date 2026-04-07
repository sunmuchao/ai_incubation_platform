/**
 * 帖子列表组件 - 支持无限滚动
 */
'use client';

import React, { useCallback, useEffect, useRef } from 'react';
import { PostCard } from './PostCard';
import { Post, FeedSort } from '@/types';
import { useAppStore, appActions } from '@/stores/useAppStore';
import { Skeleton } from '@/components/ui/skeleton';

interface PostListProps {
  sort?: FeedSort;
  onPostClick?: (post: Post) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

export function PostList({ sort = 'hot', onPostClick, onLoadMore, hasMore = true }: PostListProps) {
  const posts = useAppStore((state) => state.posts);
  const loading = useAppStore((state) => state.loading);
  const setFeedSort = useAppStore((state) => state.setFeedSort);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // 切换排序时重新加载
  useEffect(() => {
    setFeedSort(sort);
    appActions.loadFeed(sort);
  }, [sort, setFeedSort]);

  // 无限滚动加载
  const handleObserver = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;
      if (entry.isIntersecting && hasMore && !loading && onLoadMore) {
        onLoadMore();
      }
    },
    [hasMore, loading, onLoadMore]
  );

  useEffect(() => {
    const observer = new IntersectionObserver(handleObserver, {
      root: null,
      rootMargin: '100px',
      threshold: 0.1,
    });

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => {
      if (loadMoreRef.current) {
        observer.unobserve(loadMoreRef.current);
      }
    };
  }, [handleObserver]);

  if (loading && posts.length === 0) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-40 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (posts.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p className="text-lg">暂无内容，快来发布第一个帖子吧！</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {posts.map((post) => (
        <PostCard
          key={post.id}
          post={post}
          onClick={onPostClick}
        />
      ))}

      {/* 无限滚动加载触发器 */}
      {hasMore && (
        <div ref={loadMoreRef} className="infinite-scroll-loading">
          {loading && <span>加载中...</span>}
        </div>
      )}
    </div>
  );
}
