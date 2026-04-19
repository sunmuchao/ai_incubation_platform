/**
 * MatchCardList 篮选功能测试组件
 *
 * 用于验证筛选控件是否正常工作
 */

import React from 'react'
import { MatchCardList } from '../components/generative-ui/MatchComponents'

// 模拟候选人数据
const mockCandidates = [
  {
    user_id: 'user_001',
    name: '李雪',
    age: 26,
    location: '上海',
    avatar_url: 'https://api.dicebear.com/7.x/avataars/svg?seed=李雪',
    occupation: '设计师',
    interests: ['阅读', '瑜伽', '旅行'],
    confidence_level: 'high',
    confidence_score: 85,
  },
  {
    user_id: 'user_002',
    name: '周恒',
    age: 28,
    location: '北京',
    avatar_url: 'https://api.dicebear.com/7.x/avataars/svg?seed=周恒',
    occupation: '工程师',
    interests: ['健身', '摄影'],
    confidence_level: 'medium',
    confidence_score: 60,
  },
  {
    user_id: 'user_003',
    name: '王芳',
    age: 25,
    location: '杭州',
    avatar_url: 'https://api.dicebear.com/7.x/avataars/svg?seed=王芳',
    occupation: '产品经理',
    interests: ['美食', '音乐'],
    confidence_level: 'high',
    confidence_score: 78,
  },
  {
    user_id: 'user_004',
    name: '张明',
    age: 32,
    location: '北京',
    avatar_url: 'https://api.dicebear.com/7.x/avataars/svg?seed=张明',
    occupation: '医生',
    interests: ['阅读', '跑步'],
    confidence_level: 'very_high',
    confidence_score: 92,
  },
  {
    user_id: 'user_005',
    name: '刘婷',
    age: 30,
    location: '上海',
    avatar_url: 'https://api.dicebear.com/7.x/avataars/svg?seed=刘婷',
    occupation: '教师',
    interests: ['旅行', '电影'],
    confidence_level: 'medium',
    confidence_score: 55,
  },
]

// Agent 精选的候选人（模拟 Agent 推荐结果）
const mockRecommendedMatches = mockCandidates.slice(0, 3)

const MatchFilterTest: React.FC = () => {
  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <h1>MatchCardList 篮选功能测试</h1>
      <p>测试场景：Agent 返回 5 位候选人，精选 3 位推荐，用户可筛选</p>

      <div style={{ marginTop: 24, border: '1px solid #e8e8e8', borderRadius: 12, padding: 16 }}>
        <MatchCardList
          matches={mockRecommendedMatches}
          allCandidates={mockCandidates}
          totalCandidates={mockCandidates.length}
          userPreferences={{
            user_location: '北京',
            preferred_location: '北京',
          }}
          onAction={(action) => {
            console.log('Action:', action)
            alert(`点击了 ${action.type}: ${action.match?.name}`)
          }}
        />
      </div>

      <div style={{ marginTop: 24 }}>
        <h3>测试步骤：</h3>
        <ol>
          <li>点击"筛选"按钮 → 应展开筛选面板</li>
          <li>点击地区标签"北京" → 应只显示北京的候选人（张明）</li>
          <li>点击地区标签"上海" → 应只显示上海的候选人（李雪、刘婷）</li>
          <li>点击年龄标签"30-35" → 应只显示 30-35 岁的候选人</li>
          <li>点击排序"年龄" → 应按年龄排序</li>
          <li>点击"显示更多(2人)" → 应显示全部 5 位候选人</li>
          <li>点击候选人卡片上的"发起对话"按钮 → 应触发 onAction</li>
        </ol>
      </div>
    </div>
  )
}

export default MatchFilterTest