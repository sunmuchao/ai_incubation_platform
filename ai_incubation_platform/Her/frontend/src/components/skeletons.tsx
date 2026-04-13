/**
 * 公共骨架屏组件
 *
 * 从 ChatInterface.tsx 提取的骨架屏定义，用于：
 * - 减少主文件代码量
 * - 统一骨架屏样式
 * - 便于复用和扩展
 *
 * 使用方式：
 *   import { SkeletonComponents } from './skeletons';
 *   <Suspense fallback={<SkeletonComponents.featureCard />}>
 */

import React from 'react'
import { Card, Skeleton } from 'antd'

/**
 * 骨架屏组件集合
 */
export const SkeletonComponents = {
  /**
   * 功能卡片骨架屏
   * 用于 FeatureCardRenderer 懒加载时的占位
   */
  featureCard: () => (
    <Card className="feature-card" style={{ marginBottom: 16 }}>
      <div style={{ padding: 16 }}>
        <div
          style={{
            width: 100,
            height: 20,
            background: '#f0f0f0',
            borderRadius: 4,
            marginBottom: 12,
          }}
        />
        <div
          style={{
            width: '100%',
            height: 14,
            background: '#f0f0f0',
            borderRadius: 4,
            marginBottom: 8,
          }}
        />
        <div
          style={{
            width: '80%',
            height: 14,
            background: '#f0f0f0',
            borderRadius: 4,
          }}
        />
      </div>
    </Card>
  ),

  /**
   * 匹配卡片骨架屏
   * 用于 MatchCard 懒加载时的占位
   */
  matchCard: () => (
    <Card className="match-card" style={{ marginBottom: 16, borderRadius: 16 }}>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
          <div
            style={{
              width: 48,
              height: 48,
              background: '#f0f0f0',
              borderRadius: 12,
            }}
          />
          <div style={{ marginLeft: 12 }}>
            <div
              style={{
                width: 120,
                height: 16,
                background: '#f0f0f0',
                borderRadius: 4,
              }}
            />
            <div
              style={{
                width: 80,
                height: 12,
                background: '#f0f0f0',
                borderRadius: 4,
                marginTop: 6,
              }}
            />
          </div>
        </div>
        <div
          style={{
            width: '100%',
            height: 14,
            background: '#f0f0f0',
            borderRadius: 4,
            marginBottom: 8,
          }}
        />
        <div
          style={{
            width: '70%',
            height: 14,
            background: '#f0f0f0',
            borderRadius: 4,
          }}
        />
      </div>
    </Card>
  ),

  /**
   * 问题卡片骨架屏
   * 用于 ProfileQuestionCard 懒加载时的占位
   */
  questionCard: () => (
    <Card style={{ marginBottom: 16, borderRadius: 12 }}>
      <div style={{ padding: 16 }}>
        <div
          style={{
            width: '80%',
            height: 18,
            background: '#f0f0f0',
            borderRadius: 4,
            marginBottom: 8,
          }}
        />
        <div
          style={{
            width: '60%',
            height: 12,
            background: '#f0f0f0',
            borderRadius: 4,
            marginBottom: 16,
          }}
        />
        <div style={{ display: 'flex', gap: 8 }}>
          <div
            style={{
              width: 80,
              height: 32,
              background: '#f0f0f0',
              borderRadius: 8,
            }}
          />
          <div
            style={{
              width: 80,
              height: 32,
              background: '#f0f0f0',
              borderRadius: 8,
            }}
          />
          <div
            style={{
              width: 80,
              height: 32,
              background: '#f0f0f0',
              borderRadius: 8,
            }}
          />
        </div>
      </div>
    </Card>
  ),

  /**
   * 预沟通会话卡片骨架屏
   */
  precommunicationCard: () => (
    <Card style={{ marginBottom: 16, borderRadius: 12 }}>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
          <div
            style={{
              width: 40,
              height: 40,
              background: '#f0f0f0',
              borderRadius: 8,
            }}
          />
          <div style={{ marginLeft: 12 }}>
            <div
              style={{
                width: 100,
                height: 14,
                background: '#f0f0f0',
                borderRadius: 4,
              }}
            />
            <div
              style={{
                width: 60,
                height: 10,
                background: '#f0f0f0',
                borderRadius: 4,
                marginTop: 4,
              }}
            />
          </div>
        </div>
        <div
          style={{
            width: '100%',
            height: 10,
            background: '#f0f0f0',
            borderRadius: 4,
          }}
        />
      </div>
    </Card>
  ),

  /**
   * 简单骨架屏（通用）
   * 使用 Ant Design Skeleton 组件
   */
  simple: () => (
    <Card style={{ marginBottom: 16 }}>
      <Skeleton active />
    </Card>
  ),

  /**
   * 列表骨架屏
   * 用于匹配列表、会话列表等
   */
  list: (count: number = 3) => (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} style={{ marginBottom: 12, borderRadius: 12 }}>
          <Skeleton avatar active paragraph={{ rows: 2 }} />
        </Card>
      ))}
    </>
  ),
}

/**
 * 具名导出（便于按需导入）
 */
export const InlineFeatureCardSkeleton = SkeletonComponents.featureCard
export const InlineMatchCardSkeleton = SkeletonComponents.matchCard
export const InlineQuestionCardSkeleton = SkeletonComponents.questionCard

export default SkeletonComponents