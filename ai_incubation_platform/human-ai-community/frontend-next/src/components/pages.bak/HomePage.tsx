/**
 * 首页组件 - Feed 流
 */
'use client';

import React, { useState } from 'react';
import { PostList } from '@/components/post/PostList';
import { PostDetail } from '@/components/post/PostDetail';
import { SortTabs } from '@/components/post/SortTabs';
import { Post, FeedSort } from '@/types';
import { useAppStore } from '@/stores/useAppStore';
import { ScrollArea } from '@/components/ui/scroll-area';

export function HomePage() {
  const [sort, setSort] = useState<FeedSort>('hot');
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);

  return (
    <ScrollArea className="h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-4 max-w-3xl mx-auto">
        {!selectedPost ? (
          <>
            {/* 排序标签 */}
            <div className="sticky top-0 z-10 bg-background/95 backdrop-blur py-2 -mx-4 px-4 border-b border-border">
              <SortTabs value={sort} onChange={setSort} />
            </div>

            {/* 帖子列表 */}
            <PostList
              sort={sort}
              onPostClick={setSelectedPost}
            />
          </>
        ) : (
          <PostDetail
            post={selectedPost}
            onBack={() => setSelectedPost(null)}
          />
        )}
      </div>
    </ScrollArea>
  );
}
