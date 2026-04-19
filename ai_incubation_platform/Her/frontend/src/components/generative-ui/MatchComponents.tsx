/**
 * 匹配相关组件
 *
 * 🚀 [改进] 添加筛选控件（地区、年龄、排序）+ 更多按钮
 */
import React, { useState, useMemo, useCallback } from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  Avatar,
  Space,
  Empty,
  Segmented,
  message
} from 'antd'
import {
  HeartOutlined,
  EnvironmentOutlined,
  FilterOutlined,
  MessageOutlined,
  PlusOutlined
} from '@ant-design/icons'
import type { GenerativeAction } from './types'
import ConfidenceBadge from '../ConfidenceBadge'
import './MatchComponents.less'

const { Title, Text, Paragraph } = Typography

/**
 * 获取用户头像 URL，若为空则使用 DiceBear 生成随机头像
 */
const getAvatarUrl = (name: string, avatarUrl?: string): string => {
  if (avatarUrl && avatarUrl.trim()) return avatarUrl
  // 使用 DiceBear 的 avataars 风格，根据名字生成头像
  return `https://api.dicebear.com/7.x/avataars/svg?seed=${encodeURIComponent(name)}`
}

/**
 * 篮选配置类型
 */
interface FilterConfig {
  regions: string[]       // 可选地区列表
  ageRanges: string[]     // 年龄范围选项
  sortOptions: string[]   // 排序选项
}

/**
 * 默认筛选配置
 */
const DEFAULT_FILTER_CONFIG: FilterConfig = {
  regions: ['全部', '北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '西安'],
  ageRanges: ['全部', '20-25', '26-30', '31-35', '36-40', '40+'],
  sortOptions: ['匹配度', '年龄', '活跃度'],
}

/**
 * 匹配聚焦卡片 - 展示单个高匹配对象
 */
export const MatchSpotlight: React.FC<{ match: any; onAction?: (action: GenerativeAction) => void }> = ({
  match,
  onAction
}) => {
  return (
    <div className="match-spotlight-card">
      <div className="match-avatar-section">
        <Avatar size={120} src={getAvatarUrl(match.name, match.avatar_url)} />
        <div className="match-score-badge">{Math.round(match.score * 100)}%</div>
      </div>
      <div className="match-info-section">
        <Title level={3}>{match.name}</Title>
        <Text type="secondary">{match.age}岁 · {match.location}</Text>
        <Paragraph className="match-reasoning">
          <HeartOutlined /> {match.reasoning}
        </Paragraph>
        <div className="common-interests">
          <Text strong>共同兴趣：</Text>
          <Space wrap>
            {match.common_interests?.map((interest: string, i: number) => (
              <Tag key={i} color="blue">{interest}</Tag>
            ))}
          </Space>
        </div>
      </div>
      <div className="match-actions">
        <Space>
          <Button type="primary" onClick={() => onAction?.({ type: 'view_profile', match })}>
            查看详细资料
          </Button>
          <Button onClick={() => onAction?.({ type: 'start_chat', match })}>
            开始聊天
          </Button>
        </Space>
      </div>
    </div>
  )
}

/**
 * 带筛选功能的匹配卡片列表
 *
 * 🚀 [改进] 添加筛选控件，用户可自主筛选（地区、年龄、排序）
 *
 * Agent Native 设计原则：
 * - 只负责渲染 UI（卡片列表），不输出文字内容
 * - 篮选功能由组件本地执行，不重新调用 Agent
 * - "找到 X 位候选人"等文字由 Agent 自主生成，不在此组件显示
 * - 组件接收数据后静默渲染，不添加默认标题或描述
 */
export const MatchCardList: React.FC<{
  matches: any[]
  allCandidates?: any[]       // 🚀 [新增] 全部候选池（用于"显示更多"）
  totalCandidates?: number    // 🚀 [新增] 候选池总数
  userPreferences?: {         // 🚀 [新增] 用户偏好（用于智能筛选）
    preferred_location?: string
    preferred_age_min?: number
    preferred_age_max?: number
    user_location?: string
  }
  onAction?: (action: GenerativeAction) => void
  onFilterChange?: (filters: { region: string; ageRange: string; sort: string }) => void
}> = ({
  matches,
  allCandidates,
  totalCandidates,
  userPreferences,
  onAction,
  onFilterChange
}) => {
  // ===== 篮选状态 =====
  const [selectedRegion, setSelectedRegion] = useState<string>('全部')
  const [selectedAgeRange, setSelectedAgeRange] = useState<string>('全部')
  const [selectedSort, setSelectedSort] = useState<string>('匹配度')
  const [showAll, setShowAll] = useState<boolean>(false)  // 是否显示全部候选人
  const [showFilters, setShowFilters] = useState<boolean>(false)  // 是否展开筛选面板

  // ===== 智能提取筛选选项 =====
  // 从候选池中提取地区选项（如果没有全部候选池，使用默认配置）
  const regionOptions = useMemo(() => {
    if (allCandidates && allCandidates.length > 0) {
      const regions = new Set<string>()
      allCandidates.forEach(c => {
        if (c.location) regions.add(c.location)
      })
      return ['全部', ...Array.from(regions)]
    }
    // 使用默认配置
    return DEFAULT_FILTER_CONFIG.regions
  }, [allCandidates])

  // ===== 篮选逻辑 =====
  const filteredMatches = useMemo(() => {
    // 数据源：如果开启"显示更多"，使用全部候选池；否则使用 Agent 精选的 matches
    const dataSource = showAll && allCandidates ? allCandidates : matches

    if (!dataSource || dataSource.length === 0) return []

    // 1. 地区筛选
    let filtered = dataSource
    if (selectedRegion !== '全部') {
      filtered = filtered.filter(c => c.location === selectedRegion)
    }

    // 2. 年龄筛选
    if (selectedAgeRange !== '全部') {
      const [min, max] = selectedAgeRange.split('-').map(n => parseInt(n.replace('+', '')))
      filtered = filtered.filter(c => {
        const age = c.age || 0
        if (selectedAgeRange.includes('+')) {
          return age >= min
        }
        return age >= min && age <= max
      })
    }

    // 3. 排序
    if (selectedSort === '匹配度') {
      filtered.sort((a, b) => (b.confidence_score || b.score || 0) - (a.confidence_score || a.score || 0))
    } else if (selectedSort === '年龄') {
      filtered.sort((a, b) => (a.age || 0) - (b.age || 0))
    } else if (selectedSort === '活跃度') {
      // 活跃度暂无数据，使用置信度作为替代
      filtered.sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0))
    }

    return filtered
  }, [matches, allCandidates, showAll, selectedRegion, selectedAgeRange, selectedSort])

  // ===== 篮选变化回调 =====
  const handleFilterChange = useCallback((region: string, ageRange: string, sort: string) => {
    setSelectedRegion(region)
    setSelectedAgeRange(ageRange)
    setSelectedSort(sort)
    onFilterChange?.({ region, ageRange, sort })
  }, [onFilterChange])

  // Agent Native：组件只渲染数据，不添加默认文字
  // 如果数据为空，显示简单的加载状态（等待 Agent 输出）
  if (!matches || matches.length === 0) {
    return null  // 不显示"找到 0 位"等默认文字，让 Agent 决定输出内容
  }

  // ===== 渲染单个候选人卡片 =====
  const renderMatchCard = (match: any) => (
    <Card
      key={match.user_id || match.id}
      className="match-list-item match-filterable-card"
      hoverable
      style={{
        borderRadius: 12,
        marginBottom: 12,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      }}
    >
      <Space align="start" style={{ width: '100%' }}>
        <Avatar
          size={56}
          src={getAvatarUrl(match.name, match.avatar_url)}
          style={{ borderRadius: 12 }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Space>
              <Text strong style={{ fontSize: 16 }}>{match.name}</Text>
              <Text type="secondary">{match.age}岁</Text>
            </Space>
            <Space size={4}>
              <EnvironmentOutlined style={{ fontSize: 12, color: '#8c8c8c' }} />
              <Text type="secondary" style={{ fontSize: 13 }}>{match.location}</Text>
              {match.occupation && (
                <Tag style={{ marginLeft: 8, fontSize: 12 }}>{match.occupation}</Tag>
              )}
            </Space>
            {/* 兴趣标签 */}
            {match.interests && match.interests.length > 0 && (
              <Space wrap size={4} style={{ marginTop: 4 }}>
                {match.interests.slice(0, 3).map((interest: string, i: number) => (
                  <Tag key={i} color="blue" style={{ fontSize: 12 }}>{interest}</Tag>
                ))}
              </Space>
            )}
          </Space>
        </div>
        {/* 置信度 */}
        <div style={{ textAlign: 'right' }}>
          <ConfidenceBadge
            data={{
              level: match.confidence_level || 'medium',
              confidence: (match.confidence_score || match.score || 40) / 100,
              verified: match.confidence_level === 'very_high',
              flags_count: 0,
            }}
            size="small"
            showPercent={true}
          />
        </div>
      </Space>
      {/* 操作按钮 */}
      <div style={{ marginTop: 12, textAlign: 'right' }}>
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => onAction?.({ type: 'view_profile', match })}
          >
            查看详情
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<MessageOutlined />}
            onClick={() => onAction?.({ type: 'start_chat', match })}
            style={{ borderRadius: 6 }}
          >
            发起对话
          </Button>
        </Space>
      </div>
    </Card>
  )

  return (
    <div className="match-card-list-filterable">
      {/* ===== 篮选控件 ===== */}
      <div className="filter-controls-container">
        {/* 篛选入口按钮 */}
        <div className="filter-toggle-row">
          <Button
            type="text"
            icon={<FilterOutlined />}
            onClick={() => setShowFilters(!showFilters)}
            style={{ color: showFilters ? '#C88B8B' : '#8c8c8c' }}
          >
            篛选 {filteredMatches.length !== (showAll && allCandidates ? allCandidates.length : matches.length) && (
              <Tag color="pink" style={{ marginLeft: 4 }}>
                {filteredMatches.length}人
              </Tag>
            )}
          </Button>
          {/* 显示更多按钮 */}
          {allCandidates && allCandidates.length > matches.length && (
            <Button
              type="text"
              icon={<PlusOutlined />}
              onClick={() => {
                setShowAll(!showAll)
                if (!showAll) {
                  message.info(`已展开全部 ${allCandidates.length} 位候选人`)
                }
              }}
              style={{ color: showAll ? '#C88B8B' : '#8c8c8c' }}
            >
              {showAll ? '只看精选' : `显示更多(${allCandidates.length - matches.length}人)`}
            </Button>
          )}
        </div>

        {/* 篛选面板（可折叠） */}
        {showFilters && (
          <div className="filter-panel">
            {/* 地区筛选 */}
            <div className="filter-row">
              <Text type="secondary" style={{ fontSize: 13, minWidth: 60 }}>地区：</Text>
              <div className="filter-tags">
                {regionOptions.slice(0, 8).map(region => (
                  <Tag
                    key={region}
                    className={`filter-tag ${selectedRegion === region ? 'selected' : ''}`}
                    onClick={() => handleFilterChange(region, selectedAgeRange, selectedSort)}
                  >
                    {region}
                  </Tag>
                ))}
              </div>
            </div>
            {/* 年龄筛选 */}
            <div className="filter-row">
              <Text type="secondary" style={{ fontSize: 13, minWidth: 60 }}>年龄：</Text>
              <div className="filter-tags">
                {DEFAULT_FILTER_CONFIG.ageRanges.map(range => (
                  <Tag
                    key={range}
                    className={`filter-tag ${selectedAgeRange === range ? 'selected' : ''}`}
                    onClick={() => handleFilterChange(selectedRegion, range, selectedSort)}
                  >
                    {range}
                  </Tag>
                ))}
              </div>
            </div>
            {/* 排序 */}
            <div className="filter-row">
              <Text type="secondary" style={{ fontSize: 13, minWidth: 60 }}>排序：</Text>
              <Segmented
                size="small"
                options={DEFAULT_FILTER_CONFIG.sortOptions.map(opt => ({ label: opt, value: opt }))}
                value={selectedSort}
                onChange={(val) => handleFilterChange(selectedRegion, selectedAgeRange, val as string)}
                style={{ background: '#f5f5f5' }}
              />
            </div>
          </div>
        )}
      </div>

      {/* ===== 候选人列表 ===== */}
      <div className="match-cards-scrollable">
        {filteredMatches.length === 0 ? (
          <Empty
            description={
              <Space direction="vertical" size={4}>
                <Text type="secondary">没有符合条件的候选人</Text>
                <Button type="link" onClick={() => handleFilterChange('全部', '全部', '匹配度')}>
                  清除筛选
                </Button>
              </Space>
            }
            style={{ padding: 24 }}
          />
        ) : (
          filteredMatches.map(renderMatchCard)
        )}
      </div>

      {/* ===== 底部提示 ===== */}
      {filteredMatches.length > 0 && (
        <div className="match-list-footer">
          <Text type="secondary" style={{ fontSize: 12 }}>
            💬 想看更多？继续对话告诉我"看更多北京的"或点击上方筛选
          </Text>
        </div>
      )}
    </div>
  )
}

/**
 * 匹配轮播卡片
 */
export const MatchCarousel: React.FC<{ matches: any[]; onAction?: (action: GenerativeAction) => void }> = ({
  matches,
  onAction
}) => {
  const [currentIndex, setCurrentIndex] = useState(0)

  const current = matches[currentIndex]
  if (!current) return <Empty description="暂无匹配" />

  return (
    <div className="match-carousel">
      <Card className="match-carousel-card">
        <div className="match-carousel-content">
          <Avatar size={100} src={getAvatarUrl(current.name, current.avatar_url)} />
          <div className="match-carousel-info">
            <Title level={4}>{current.name}</Title>
            <Text>{current.reasoning}</Text>
            <div className="match-interests">
              <Space wrap>
                {current.common_interests?.map((interest: string, i: number) => (
                  <Tag key={i} color="blue">{interest}</Tag>
                ))}
              </Space>
            </div>
          </div>
        </div>
        <div className="match-carousel-nav">
          <Button disabled={currentIndex === 0} onClick={() => setCurrentIndex(i => i - 1)}>
            上一个
          </Button>
          <Text>
            {currentIndex + 1} / {matches.length}
          </Text>
          <Button
            disabled={currentIndex === matches.length - 1}
            onClick={() => setCurrentIndex(i => i + 1)}
          >
            下一个
          </Button>
        </div>
        <div className="match-carousel-actions">
          <Space>
            <Button type="primary" onClick={() => onAction?.({ type: 'view_profile', match: current })}>
              查看详细资料
            </Button>
            <Button onClick={() => onAction?.({ type: 'start_chat', match: current })}>
              开始聊天
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  )
}