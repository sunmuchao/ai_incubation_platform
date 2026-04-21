/**
 * 匹配相关组件
 *
 * 🚀 [改进 v2] 篮选改为实时查询（而非前端过滤已有数据）
 */
import React, { useState, useMemo, useCallback, useEffect } from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  Avatar,
  Space,
  Empty,
  Spin
} from 'antd'
import {
  HeartOutlined,
  EnvironmentOutlined,
  FilterOutlined,
  MessageOutlined,
  UserOutlined
} from '@ant-design/icons'
import type { GenerativeAction } from './types'
import ConfidenceBadge from '../ConfidenceBadge'
import { getAvatarUrlForCandidate, getFallbackAvatarUrlForCandidate } from '../../utils/matchAvatar'
import './MatchComponents.less'

const { Title, Text, Paragraph } = Typography

/** 远程/臆造 URL 裂图时回退到本地性别占位图 */
const MatchCandidateAvatar: React.FC<{
  match: Record<string, any>
  size: number
  className?: string
  style?: React.CSSProperties
}> = ({ match, size, className, style }) => {
  const primary = getAvatarUrlForCandidate(match)
  const fallback = getFallbackAvatarUrlForCandidate(match)
  const [useFallback, setUseFallback] = useState(false)
  useEffect(() => {
    setUseFallback(false)
  }, [primary])
  return (
    <Avatar
      size={size}
      className={className}
      style={style}
      src={useFallback ? fallback : primary}
      icon={<UserOutlined />}
      onError={() => {
        setUseFallback(true)
        return false
      }}
    />
  )
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
        <MatchCandidateAvatar match={match} size={120} />
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
 * 🚀 [改进 v2] 篮选改为实时查询（而非前端过滤已有数据）
 *
 * 设计原则：
 * - 篮选点击 → 调用后端 API → 重新查询 → 返回新的精选结果
 * - 不再传入 all_candidates（全部候选池）
 * - 每次筛选都是"实时查询"，数据新鲜
 *
 * Agent Native 设计原则：
 * - 只负责渲染 UI（卡片列表），不输出文字内容
 * - 组件接收数据后静默渲染，不添加默认标题或描述
 */
export const MatchCardList: React.FC<{
  matches: any[]
  userPreferences?: {         // 用户偏好（显示当前筛选状态）
    preferred_location?: string
    preferred_age_min?: number
    preferred_age_max?: number
    user_location?: string
  }
  filterOptions?: {           // 筛选项元数据（供前端渲染筛选控件）
    locations?: string[]
    age_ranges?: string[]
    relationship_goals?: string[]
    selected?: {
      location?: string
      age_range?: string
      relationship_goal?: string
    }
  }
  onAction?: (action: GenerativeAction) => void
  onFilterChange?: (filters: { location?: string; ageRange?: string; relationshipGoal?: string }) => void  // 篮选回调（触发 API 查询）
}> = ({
  matches,
  userPreferences,
  filterOptions,
  onAction,
  onFilterChange
}) => {
  // ===== 篮选状态 =====
  const [selectedLocation, setSelectedLocation] = useState<string>('全部')
  const [selectedAgeRange, setSelectedAgeRange] = useState<string>('全部')
  const [selectedRelationshipGoal, setSelectedRelationshipGoal] = useState<string>('全部')
  const [isFiltering, setIsFiltering] = useState<boolean>(false)  // 篮选中状态（显示骨架屏）
  const [showFilters, setShowFilters] = useState<boolean>(false)  // 是否展开筛选面板

  // 🚀 [改进] 监听 matches 变化，关闭筛选骨架屏
  useEffect(() => {
    if (isFiltering) {
      setIsFiltering(false)
    }
  }, [matches, isFiltering])

  // 后端返回 selected_filters / filter_options.selected 后，同步到 UI 选中态
  useEffect(() => {
    const selectedFromBackend = filterOptions?.selected || {}
    const selectedFromPreferences = (userPreferences as any)?.selected_filters || {}

    const nextLocation =
      selectedFromBackend.location ||
      selectedFromPreferences.location ||
      userPreferences?.preferred_location ||
      userPreferences?.user_location ||
      '全部'
    const nextAgeRange =
      selectedFromBackend.age_range ||
      selectedFromPreferences.age_range ||
      '全部'
    const nextGoal =
      selectedFromBackend.relationship_goal ||
      selectedFromPreferences.relationship_goal ||
      '全部'

    setSelectedLocation(nextLocation)
    setSelectedAgeRange(nextAgeRange)
    setSelectedRelationshipGoal(nextGoal)
  }, [filterOptions, userPreferences])

  // ===== 筛选选项（从 filterOptions 或默认配置）=====
  const locationOptions = useMemo(() => {
    const options = filterOptions?.locations?.length ? filterOptions.locations : DEFAULT_FILTER_CONFIG.regions
    if (!options.includes(selectedLocation)) return [selectedLocation, ...options]
    return options
  }, [filterOptions, selectedLocation])

  const ageRangeOptions = useMemo(() => {
    const options = filterOptions?.age_ranges?.length ? filterOptions.age_ranges : DEFAULT_FILTER_CONFIG.ageRanges
    if (!options.includes(selectedAgeRange)) return [selectedAgeRange, ...options]
    return options
  }, [filterOptions, selectedAgeRange])

  const relationshipGoalOptions = useMemo(() => {
    const defaults = ['全部', '认真恋爱', '奔着结婚', '轻松交友', '随便聊聊']
    const options = filterOptions?.relationship_goals?.length ? filterOptions.relationship_goals : defaults
    if (!options.includes(selectedRelationshipGoal)) return [selectedRelationshipGoal, ...options]
    return options
  }, [filterOptions, selectedRelationshipGoal])

  // ===== 篮选变化回调（触发 API 查询）=====
  const handleFilterChange = useCallback((location: string, ageRange: string, relationshipGoal: string) => {
    setSelectedLocation(location)
    setSelectedAgeRange(ageRange)
    setSelectedRelationshipGoal(relationshipGoal)

    // 🚀 [关键改动] 篮选触发 API 查询，而非前端过滤
    if (onFilterChange) {
      setIsFiltering(true)  // 显示骨架屏
      onFilterChange({
        location: location === '全部' ? undefined : location,
        ageRange: ageRange === '全部' ? undefined : ageRange,
        relationshipGoal: relationshipGoal === '全部' ? undefined : relationshipGoal,
      })
    }
  }, [onFilterChange])

  // Agent Native：组件只渲染数据，不添加默认文字
  if (!matches || matches.length === 0) {
    return null
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
        <MatchCandidateAvatar
          match={match}
          size={56}
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
            {/* 🚀 [场景3方案1] 显示匹配原因 - 用户看懂"为什么推荐TA" */}
            {match.match_reasons && match.match_reasons.length > 0 && (
              <div style={{ marginTop: 6, marginBottom: 4 }}>
                <Text type="secondary" style={{ fontSize: 12, marginRight: 4 }}>💡 为什么推荐：</Text>
                <Space wrap size={2}>
                  {match.match_reasons.map((reason: string, i: number) => (
                    <Tag key={i} color="pink" style={{ fontSize: 11, borderRadius: 4 }}>
                      {reason}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
            {match.vector_match_highlights && (
              <div style={{ marginTop: 4 }}>
                <Space wrap size={2}>
                  {match.vector_match_highlights.relationship_goal && (
                    <Tag style={{ fontSize: 11 }}>关系目标：{match.vector_match_highlights.relationship_goal}</Tag>
                  )}
                  {match.vector_match_highlights.want_children && (
                    <Tag style={{ fontSize: 11 }}>生育观：{match.vector_match_highlights.want_children}</Tag>
                  )}
                  {match.vector_match_highlights.spending_style && (
                    <Tag style={{ fontSize: 11 }}>消费观：{match.vector_match_highlights.spending_style}</Tag>
                  )}
                </Space>
              </div>
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
      {/* ===== 筛选控件 ===== */}
      <div className="filter-controls-container">
        {/* 筛选入口按钮 */}
        <div className="filter-toggle-row">
          <Button
            type="text"
            icon={<FilterOutlined />}
            onClick={() => setShowFilters(!showFilters)}
            style={{ color: showFilters ? '#C88B8B' : '#8c8c8c' }}
          >
            筛选 {isFiltering && <Spin size="small" style={{ marginLeft: 4 }} />}
          </Button>
        </div>

        {/* 筛选面板（可折叠） */}
        {showFilters && (
          <div className="filter-panel">
            {/* 地区筛选 */}
            <div className="filter-row">
              <Text type="secondary" style={{ fontSize: 13, minWidth: 60 }}>地区：</Text>
              <div className="filter-tags">
                {locationOptions.slice(0, 8).map(location => (
                  <Tag
                    key={location}
                    className={`filter-tag ${selectedLocation === location ? 'selected' : ''}`}
                    onClick={() => handleFilterChange(location, selectedAgeRange, selectedRelationshipGoal)}
                  >
                    {location}
                  </Tag>
                ))}
              </div>
            </div>
            {/* 年龄筛选 */}
            <div className="filter-row">
              <Text type="secondary" style={{ fontSize: 13, minWidth: 60 }}>年龄：</Text>
              <div className="filter-tags">
                {ageRangeOptions.map(range => (
                  <Tag
                    key={range}
                    className={`filter-tag ${selectedAgeRange === range ? 'selected' : ''}`}
                    onClick={() => handleFilterChange(selectedLocation, range, selectedRelationshipGoal)}
                  >
                    {range}
                  </Tag>
                ))}
              </div>
            </div>
            {/* 关系目标筛选 */}
            <div className="filter-row">
              <Text type="secondary" style={{ fontSize: 13, minWidth: 60 }}>目标：</Text>
              <div className="filter-tags">
                {relationshipGoalOptions.slice(0, 5).map(goal => (
                  <Tag
                    key={goal}
                    className={`filter-tag ${selectedRelationshipGoal === goal ? 'selected' : ''}`}
                    onClick={() => handleFilterChange(selectedLocation, selectedAgeRange, goal)}
                  >
                    {goal}
                  </Tag>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ===== 候选人列表 ===== */}
      {/* 🚀 [改进] 篮选中显示骨架屏（而非在已有数据里过滤） */}
      {isFiltering ? (
        <div className="match-cards-loading">
          <Spin size="small" style={{ marginBottom: 8 }} />
          <Text type="secondary">正在查询符合条件的候选人...</Text>
          {/* 骨架屏卡片占位 */}
          {[1, 2, 3].map(i => (
            <Card key={i} style={{ borderRadius: 12, marginBottom: 12 }}>
              <Space align="start" style={{ width: '100%' }}>
                <Avatar size={56} style={{ borderRadius: 12 }} icon={<UserOutlined />} />
                <div style={{ flex: 1 }}>
                  <div style={{ height: 20, width: '60%', background: '#f5f5f5', borderRadius: 4, marginBottom: 8 }} />
                  <div style={{ height: 14, width: '40%', background: '#f5f5f5', borderRadius: 4 }} />
                </div>
              </Space>
            </Card>
          ))}
        </div>
      ) : (
        <div className="match-cards-scrollable">
          {matches.map(renderMatchCard)}
        </div>
      )}

      {/* ===== 底部提示 ===== */}
      {!isFiltering && matches.length > 0 && (
        <div className="match-list-footer">
          <Text type="secondary" style={{ fontSize: 12 }}>
            💬 点击筛选按钮可重新查询符合条件的候选人
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
          <MatchCandidateAvatar match={current} size={100} />
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