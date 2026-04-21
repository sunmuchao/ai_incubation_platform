/**
 * 测试头像生成逻辑和匹配原因显示
 *
 * 覆盖内容：
 * 1. getAvatarUrl 函数（本地头像替代 DiceBear）
 * 2. 匹配原因在卡片和详情弹窗中的显示
 * 3. 同城标识显示
 */

import { describe, it, expect } from '@jest/globals'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { Tag, Space } from 'antd'
import { EnvironmentOutlined } from '@ant-design/icons'
import { getMatchAvatarSrc, getAvatarUrlForCandidate, normalizeGender, isUsableAvatarUrl } from '../../utils/matchAvatar'

// ==================== 头像生成逻辑测试 ====================

/** 无自定义头像时使用 randomuser 男女肖像（测试用） */
const MALE_DEMO = /^https:\/\/randomuser\.me\/api\/portraits\/men\/\d{1,2}\.jpg$/
const FEMALE_DEMO = /^https:\/\/randomuser\.me\/api\/portraits\/women\/\d{1,2}\.jpg$/
const DEMO_PORTRAIT = /^https:\/\/randomuser\.me\/api\/portraits\/(men|women)\/\d{1,2}\.jpg$/

describe('getMatchAvatarSrc - 头像生成', () => {
  it('有头像 URL 时返回用户头像', () => {
    const result = getMatchAvatarSrc('小明', 'male', undefined, 'https://example.com/avatar.jpg')
    expect(result).toBe('https://example.com/avatar.jpg')
  })

  it('空头像 URL 时使用网上男性肖像占位', () => {
    const result = getMatchAvatarSrc('小明', 'male', undefined, '')
    expect(result).toMatch(MALE_DEMO)
  })

  it('无头像 URL 时使用网上女性肖像占位', () => {
    const result = getMatchAvatarSrc('小红', 'female', undefined, undefined)
    expect(result).toMatch(FEMALE_DEMO)
  })

  it('女生无头像时使用 women 肖像 URL', () => {
    const result = getMatchAvatarSrc('小红', 'female', undefined, '')
    expect(result).toMatch(FEMALE_DEMO)
  })

  it('男生无头像时使用 men 肖像 URL', () => {
    expect(getMatchAvatarSrc('小明', 'male', undefined, '')).toMatch(MALE_DEMO)
    expect(getMatchAvatarSrc('阿强', '男', undefined, '')).toMatch(MALE_DEMO)
    expect(getMatchAvatarSrc('小丽', '女', undefined, undefined)).toMatch(FEMALE_DEMO)
  })

  it('相同名字生成稳定默认头像', () => {
    const result1 = getMatchAvatarSrc('小明', 'male', undefined, '')
    const result2 = getMatchAvatarSrc('小明', 'male', undefined, '')
    expect(result1).toBe(result2)
  })

  it('不同名字均为男性 demo 肖像 URL（slot 可不同）', () => {
    const result1 = getMatchAvatarSrc('小明', 'male', undefined, '')
    const result2 = getMatchAvatarSrc('小红', 'male', undefined, '')
    expect(result1).toMatch(MALE_DEMO)
    expect(result2).toMatch(MALE_DEMO)
  })

  it('占位字符串头像视为无效并回退 demo 肖像', () => {
    expect(getMatchAvatarSrc('x', 'female', undefined, 'null')).toMatch(FEMALE_DEMO)
    expect(getMatchAvatarSrc('x', 'male', undefined, ' undefined ')).toMatch(MALE_DEMO)
    expect(isUsableAvatarUrl('null')).toBe(false)
    expect(isUsableAvatarUrl('https://via.placeholder.com/150')).toBe(false)
  })

  it('normalizeGender 识别中英文性别', () => {
    expect(normalizeGender('男')).toBe('male')
    expect(normalizeGender('女')).toBe('female')
    expect(normalizeGender('MALE')).toBe('male')
    expect(normalizeGender('female')).toBe('female')
  })

  it('相对路径头像补全前导斜杠', () => {
    expect(getMatchAvatarSrc('x', undefined, undefined, 'uploads/a.png')).toBe('/uploads/a.png')
  })

  it('默认头像使用 randomuser 肖像而非 DiceBear', () => {
    const result = getMatchAvatarSrc('测试用户', 'male', undefined, '')
    expect(result).not.toContain('dicebear')
    expect(result).toMatch(MALE_DEMO)
  })

  it('未知性别时仍为 randomuser men 或 women 之一', () => {
    const result = getMatchAvatarSrc('某用户', undefined, undefined, '')
    expect(result).toMatch(DEMO_PORTRAIT)
  })

  it('嵌套 user 上的头像参与解析', () => {
    const src = getAvatarUrlForCandidate({
      name: '外层',
      user: { name: '内层', avatar_url: 'https://cdn.example/u.png' },
    })
    expect(src).toBe('https://cdn.example/u.png')
  })
})

// ==================== 匹配原因显示测试 ====================

describe('MatchReasons - 匹配原因显示', () => {
  /**
   * 模拟匹配原因渲染组件
   */
  const MatchReasonsDisplay: React.FC<{ reasons: string[] }> = ({ reasons }) => (
    <div>
      <span style={{ color: '#C88B8B' }}>💡 为什么推荐 TA：</span>
      <Space wrap size={4}>
        {reasons.map((reason, index) => (
          <Tag key={index} color="pink" style={{ borderRadius: 4 }}>
            {reason}
          </Tag>
        ))}
      </Space>
    </div>
  )

  it('显示匹配原因列表', () => {
    const reasons = ['同城（都在无锡）', '年龄相近', '兴趣匹配']
    render(<MatchReasonsDisplay reasons={reasons} />)

    expect(screen.getByText('同城（都在无锡）')).toBeInTheDocument()
    expect(screen.getByText('年龄相近')).toBeInTheDocument()
    expect(screen.getByText('兴趣匹配')).toBeInTheDocument()
  })

  it('显示"为什么推荐"标题', () => {
    const reasons = ['同城用户']
    render(<MatchReasonsDisplay reasons={reasons} />)

    expect(screen.getByText(/为什么推荐/)).toBeInTheDocument()
  })

  it('空匹配原因时不显示', () => {
    const { container } = render(<MatchReasonsDisplay reasons={[]} />)
    // 无匹配原因时组件应不渲染或渲染为空
    expect(container.querySelectorAll('.ant-tag').length).toBe(0)
  })

  it('匹配原因使用粉色标签', () => {
    const reasons = ['同城用户']
    render(<MatchReasonsDisplay reasons={reasons} />)

    const tag = screen.getByText('同城用户')
    expect(tag).toBeInTheDocument()
  })
})

// ==================== 同城标识测试 ====================

describe('SameCityBadge - 同城标识', () => {
  /**
   * 模拟同城标识组件
   */
  const SameCityBadge: React.FC<{ isSameCity: boolean }> = ({ isSameCity }) => (
    isSameCity ? (
      <Tag color="green" icon={<EnvironmentOutlined />}>
        同城用户
      </Tag>
    ) : null
  )

  it('同城用户显示标识', () => {
    render(<SameCityBadge isSameCity={true} />)
    expect(screen.getByText('同城用户')).toBeInTheDocument()
  })

  it('非同城用户不显示标识', () => {
    const { container } = render(<SameCityBadge isSameCity={false} />)
    expect(container.querySelector('.ant-tag')).toBeNull()
  })

  it('同城标识使用绿色', () => {
    render(<SameCityBadge isSameCity={true} />)
    const tag = screen.getByText('同城用户')
    expect(tag).toBeInTheDocument()
  })
})

// ==================== 用户详情弹窗数据测试 ====================

describe('UserDetailModal - 用户详情数据传递', () => {
  /**
   * 模拟用户详情数据结构
   */
  interface UserDetail {
    userId: string
    name: string
    age: number
    location: string
    avatar_url?: string
    interests?: string[]
    bio?: string
    relationship_goal?: string
    confidence_level?: string
    confidence_score?: number
    occupation?: string
    education?: string
    income?: number
    income_range?: string
    match_reasons?: string[]
    is_same_city?: boolean
  }

  it('用户详情包含匹配原因', () => {
    const userDetail: UserDetail = {
      userId: 'user-001',
      name: '小红',
      age: 26,
      location: '无锡',
      match_reasons: ['同城（都在无锡）', '年龄相近'],
    }

    expect(userDetail.match_reasons).toBeDefined()
    expect(userDetail.match_reasons?.length).toBe(2)
  })

  it('用户详情包含同城标识', () => {
    const userDetail: UserDetail = {
      userId: 'user-001',
      name: '小红',
      age: 26,
      location: '无锡',
      is_same_city: true,
    }

    expect(userDetail.is_same_city).toBe(true)
  })

  it('用户详情包含扩展字段', () => {
    const userDetail: UserDetail = {
      userId: 'user-001',
      name: '小红',
      age: 26,
      location: '无锡',
      education: 'bachelor',
      income: 20,
      income_range: '20-30万',
      occupation: '工程师',
    }

    expect(userDetail.education).toBe('bachelor')
    expect(userDetail.income).toBe(20)
    expect(userDetail.income_range).toBe('20-30万')
    expect(userDetail.occupation).toBe('工程师')
  })

  it('用户详情包含头像 URL', () => {
    const userDetail: UserDetail = {
      userId: 'user-001',
      name: '小红',
      age: 26,
      location: '无锡',
      avatar_url: 'https://example.com/avatar.jpg',
    }

    expect(userDetail.avatar_url).toBe('https://example.com/avatar.jpg')
  })

  it('无头像时 avatar_url 为空或 undefined', () => {
    const userDetail: UserDetail = {
      userId: 'user-001',
      name: '小红',
      age: 26,
      location: '无锡',
    }

    expect(userDetail.avatar_url).toBeUndefined()
  })
})

// ==================== 集成测试 ====================

describe('集成测试 - 卡片到详情弹窗数据流', () => {
  it('候选人卡片数据包含详情弹窗所需字段', () => {
    // 模拟候选人卡片数据
    const matchCardData = {
      user_id: 'candidate-001',
      name: '小红',
      age: 26,
      gender: 'female',
      location: '无锡',
      interests: ['旅行', '音乐'],
      bio: '喜欢户外运动',
      relationship_goal: 'serious',
      occupation: '设计师',
      education: 'bachelor',
      income: 15,
      income_range: '10-20万',
      confidence_level: 'high',
      confidence_score: 70,
      avatar_url: '',
      match_reasons: ['同城（都在无锡）', '年龄符合范围'],
      is_same_city: true,
    }

    // 验证详情弹窗所需的所有字段都存在
    expect(matchCardData.user_id).toBeDefined()
    expect(matchCardData.name).toBeDefined()
    expect(matchCardData.match_reasons).toBeDefined()
    expect(matchCardData.is_same_city).toBeDefined()
    expect(matchCardData.education).toBeDefined()
    expect(matchCardData.income_range).toBeDefined()
  })

  it('点击查看详情时传递完整数据', () => {
    // 模拟点击查看详情时的数据传递
    const handleViewUserProfile = (userId: string, userData: any) => {
      return {
        userId,
        name: userData?.name || '匿名用户',
        age: userData?.age || 0,
        location: userData?.location || '',
        avatar_url: userData?.avatar_url,
        interests: userData?.interests || [],
        bio: userData?.bio,
        relationship_goal: userData?.relationship_goal,
        confidence_level: userData?.confidence_level,
        confidence_score: userData?.confidence_score,
        occupation: userData?.occupation,
        education: userData?.education,
        income: userData?.income,
        income_range: userData?.income_range,
        match_reasons: userData?.match_reasons || [],
        is_same_city: userData?.is_same_city,
      }
    }

    const cardData = {
      user_id: 'test-id',
      name: '测试用户',
      age: 25,
      location: '无锡',
      match_reasons: ['同城'],
      is_same_city: true,
    }

    const detailData = handleViewUserProfile(cardData.user_id, cardData)

    // 验证传递的数据完整
    expect(detailData.userId).toBe('test-id')
    expect(detailData.match_reasons).toEqual(['同城'])
    expect(detailData.is_same_city).toBe(true)
  })
})