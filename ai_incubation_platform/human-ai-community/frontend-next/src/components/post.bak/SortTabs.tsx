/**
 * 排序标签组件
 */
'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { Flame, Clock, TrendingUp, Zap } from 'lucide-react';
import { FeedSort } from '@/types';

interface SortTabsProps {
  value: FeedSort;
  onChange: (sort: FeedSort) => void;
}

const sortOptions: { value: FeedSort; label: string; icon: React.ReactNode }[] = [
  { value: 'hot', label: '热门', icon: <Flame className="h-4 w-4" /> },
  { value: 'new', label: '最新', icon: <Clock className="h-4 w-4" /> },
  { value: 'top', label: '上升', icon: <TrendingUp className="h-4 w-4" /> },
  { value: 'rising', label: '新兴', icon: <Zap className="h-4 w-4" /> },
];

export function SortTabs({ value, onChange }: SortTabsProps) {
  return (
    <div className="flex gap-2 overflow-x-auto scrollbar-hide">
      {sortOptions.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            'flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap touch-feedback',
            value === option.value
              ? 'bg-primary text-primary-foreground shadow-md'
              : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
          )}
        >
          {option.icon}
          {option.label}
        </button>
      ))}
    </div>
  );
}
