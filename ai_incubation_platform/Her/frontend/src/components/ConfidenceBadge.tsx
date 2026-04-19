/**
 * ConfidenceBadge - 用户置信度徽章组件
 *
 * 展示用户信息的可信程度，用于：
 * - 匹配卡片：展示对方可信度
 * - 用户资料页：展示自己的置信度详情
 * - 列表页：快速判断用户可信程度
 *
 * 置信度等级：
 * - very_high (80-100%): 极可信 - 金色
 * - high (60-80%): 较可信 - 绿色
 * - medium (40-60%): 普通用户 - 蓝色
 * - low (0-40%): 需谨慎 - 橙色
 */

import React, { useMemo, useState, useEffect } from 'react'
import { Tag, Tooltip, Progress, Modal, Button, List, Spin, Empty } from 'antd'
import {
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  StarFilled,
} from '@ant-design/icons'
import type { ConfidenceSummary, ConfidenceDetail, VerificationRecommendation } from '@/api/confidenceClient'
import confidenceApi from '@/api/confidenceClient'
import './ConfidenceBadge.less'

// ==================== 类型导出 ====================

export type ConfidenceLevel = 'very_high' | 'high' | 'medium' | 'low'

// ==================== 配置 ====================

// 🚀 [改进] 用户友好的置信度配置
const LEVEL_CONFIG = {
  very_high: {
    color: '#faad14',
    bgColor: '#faad14',
    icon: '💎',
    name: '资料已核实',  // 🚀 [改进] 更友好的文案
    description: '资料完整且经过身份认证，可信度极高',  // 🚀 [改进] 更清晰的说明
    antColor: 'gold',
    hint: '已完成实名认证 + 人脸核身',  // 🚀 [改进] 解释说明
  },
  high: {
    color: '#52c41a',
    bgColor: '#52c41a',
    icon: '🌟',
    name: '资料较完整',  // 🚀 [改进] 更友好的文案
    description: '资料完整度良好，建议进一步认证提升可信度',
    antColor: 'success',
    hint: '基本信息已填写完整',
  },
  medium: {
    color: '#1890ff',
    bgColor: '#1890ff',
    icon: '✓',
    name: '基本资料',  // 🚀 [改进] 更友好的文案
    description: '基本信息已填写，建议补充更多资料',
    antColor: 'processing',
    hint: '建议完成认证提升可信度',
  },
  low: {
    color: '#fa8c16',
    bgColor: '#fa8c16',
    icon: '⚠️',
    name: '资料待完善',  // 🚀 [改进] 更友好的文案
    description: '资料不完整，建议先完善基本信息',
    antColor: 'warning',
    hint: '补充资料后可提升匹配质量',
  },
}

const DIMENSION_NAMES: Record<string, string> = {
  identity: '身份验证',
  cross_validation: '信息一致性',
  behavior: '行为一致性',
  social: '社交背书',
  time: '时间积累',
}

// ==================== 组件 ====================

interface ConfidenceBadgeProps {
  /** 用户 ID（查看他人置信度时传入） */
  userId?: string
  /** 置信度数据（已有数据时传入，避免 API 调用） */
  data?: ConfidenceSummary
  /** 尺寸 */
  size?: 'small' | 'default' | 'large'
  /** 是否显示详细提示 */
  showTooltip?: boolean
  /** 是否显示百分比数值 */
  showPercent?: boolean
  /** 是否显示详情弹窗按钮 */
  showDetailButton?: boolean
  /** 自定义样式类 */
  className?: string
  /** 点击回调 */
  onClick?: () => void
}

/**
 * 置信度徽章组件 - 用于匹配卡片等场景
 */
const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  userId,
  data,
  size = 'default',
  showTooltip = true,
  showPercent = false,
  showDetailButton = false,
  className,
  onClick,
}) => {
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState<ConfidenceSummary | null>(data || null)

  // 加载置信度数据
  useEffect(() => {
    if (data) {
      setSummary(data)
      return
    }

    if (!userId) {
      // 获取当前用户置信度
      setLoading(true)
      confidenceApi.getConfidenceSummary()
        .then(setSummary)
        .catch(console.error)
        .finally(() => setLoading(false))
    } else {
      // 获取其他用户置信度
      setLoading(true)
      confidenceApi.getOtherUserConfidenceSummary(userId)
        .then(setSummary)
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [userId, data])

  // 获取等级配置
  const config = useMemo(() => {
    if (!summary) return LEVEL_CONFIG.medium
    return LEVEL_CONFIG[summary.level] || LEVEL_CONFIG.medium
  }, [summary])

  // 尺寸样式
  const sizeStyles = useMemo(() => {
    switch (size) {
      case 'small':
        return { fontSize: 12, padding: '2px 6px' }
      case 'large':
        return { fontSize: 16, padding: '4px 12px' }
      default:
        return { fontSize: 14, padding: '3px 8px' }
    }
  }, [size])

  // 加载中状态
  if (loading) {
    return (
      <Tag className={`confidence-badge loading ${className || ''}`} style={sizeStyles}>
        <Spin size="small" />
      </Tag>
    )
  }

  // 无数据状态
  if (!summary) {
    return null
  }

  // 渲染徽章内容
  const renderBadgeContent = () => (
    <Tag
      className={`confidence-badge ${config.antColor} ${className || ''}`}
      style={{
        backgroundColor: `${config.bgColor}15`,
        borderColor: `${config.bgColor}40`,
        color: config.color,
        ...sizeStyles,
        cursor: onClick ? 'pointer' : 'default',
      }}
      onClick={onClick}
    >
      <span className="badge-icon">{config.icon}</span>
      <span className="badge-level">{config.name}</span>
      {showPercent && (
        <span className="badge-percent">{Math.round(summary.confidence * 100)}%</span>
      )}
    </Tag>
  )

  // 无提示
  if (!showTooltip) {
    return renderBadgeContent()
  }

  // 带提示
  return (
    <Tooltip
      title={
        <div className="confidence-tooltip">
          <div className="tooltip-header">
            <span className="tooltip-icon">{config.icon}</span>
            <span className="tooltip-name">{config.name}</span>
            {/* 🚀 [改进] 可选显示百分比 */}
            {showPercent && (
              <span className="tooltip-percent">{Math.round(summary.confidence * 100)}%</span>
            )}
          </div>
          <div className="tooltip-desc">{config.description}</div>
          {/* 🚀 [改进] 添加解释说明 */}
          <div className="tooltip-hint" style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
            💡 {config.hint}
          </div>
          {summary.flags_count > 0 && (
            <div className="tooltip-warning">
              <WarningOutlined /> {summary.flags_count} 项信息待完善
            </div>
          )}
          {summary.verified && (
            <div className="tooltip-verified">
              <CheckCircleOutlined /> 已通过身份认证
            </div>
          )}
        </div>
      }
      placement="top"
    >
      {renderBadgeContent()}
    </Tooltip>
  )
}

// ==================== 详情弹窗组件 ====================

interface ConfidenceDetailModalProps {
  /** 是否显示 */
  visible: boolean
  /** 关闭回调 */
  onClose: () => void
  /** 用户 ID */
  userId?: string
}

/**
 * 置信度详情弹窗 - 展示完整的置信度分析
 */
export const ConfidenceDetailModal: React.FC<ConfidenceDetailModalProps> = ({
  visible,
  onClose,
  userId,
}) => {
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [detail, setDetail] = useState<ConfidenceDetail | null>(null)
  const [recommendations, setRecommendations] = useState<VerificationRecommendation[]>([])

  // 加载详情
  useEffect(() => {
    if (!visible) return

    setLoading(true)
    Promise.all([
      confidenceApi.getConfidenceDetail(),
      confidenceApi.getVerificationRecommendations(),
    ])
      .then(([detailRes, recRes]) => {
        setDetail(detailRes)
        setRecommendations(recRes.recommendations || [])
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [visible])

  // 刷新评估
  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const result = await confidenceApi.refreshConfidence(true)
      if (result.success) {
        // 重新加载详情
        const newDetail = await confidenceApi.getConfidenceDetail()
        setDetail(newDetail)
      }
    } catch (error) {
      console.error('Refresh failed:', error)
    } finally {
      setRefreshing(false)
    }
  }

  // 渲染维度进度条
  const renderDimensionProgress = (key: string, value: number) => {
    const config = LEVEL_CONFIG[value >= 0.8 ? 'very_high' : value >= 0.6 ? 'high' : value >= 0.4 ? 'medium' : 'low']
    return (
      <div className="dimension-item" key={key}>
        <div className="dimension-header">
          <span className="dimension-name">{DIMENSION_NAMES[key] || key}</span>
          <span className="dimension-value">{Math.round(value * 100)}%</span>
        </div>
        <Progress
          percent={Math.round(value * 100)}
          strokeColor={config.color}
          trailColor="#f0f0f0"
          size="small"
          showInfo={false}
        />
      </div>
    )
  }

  // 渲染异常标记
  const renderFlags = () => {
    if (!detail?.cross_validation_flags) return null

    const flags = Object.entries(detail.cross_validation_flags)
    if (flags.length === 0) {
      return (
        <div className="flags-empty">
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
          <span>无异常标记</span>
        </div>
      )
    }

    return (
      <List
        className="flags-list"
        dataSource={flags}
        renderItem={(item) => {
          const [key, flag] = item
          return (
            <List.Item className={`flag-item ${flag.severity}`}>
              <div className="flag-icon">
                {flag.severity === 'high' ? '🔴' : flag.severity === 'medium' ? '🟡' : '🟢'}
              </div>
              <div className="flag-content">
                <div className="flag-title">
                  {key === 'age_education_mismatch' ? '年龄-学历不匹配' :
                   key === 'occupation_income_mismatch' ? '职业-收入不匹配' :
                   key === 'location_activity_mismatch' ? '地理-活跃时间异常' : key}
                </div>
                <div className="flag-detail">{flag.detail}</div>
              </div>
            </List.Item>
          )
        }}
      />
    )
  }

  // 渲染建议
  const renderRecommendations = () => {
    if (recommendations.length === 0) {
      return (
        <div className="recommendations-empty">
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
          <span>置信度已达较高水平</span>
        </div>
      )
    }

    return (
      <List
        className="recommendations-list"
        dataSource={recommendations}
        renderItem={(rec) => (
          <List.Item className={`recommendation-item ${rec.priority}`}>
            <div className="rec-priority">
              {rec.priority === 'high' ? '🔴' : rec.priority === 'medium' ? '🟡' : '🟢'}
            </div>
            <div className="rec-content">
              <div className="rec-title">
                {rec.type === 'identity_verify' ? '完成实名认证' :
                 rec.type === 'face_verify' ? '人脸核身认证' :
                 rec.type === 'education_verify' ? '学历认证' :
                 rec.type === 'occupation_verify' ? '职业认证' :
                 rec.type === 'profile_complete' ? '完善个人资料' : rec.type}
              </div>
              <div className="rec-reason">{rec.reason}</div>
              <div className="rec-impact">
                <StarFilled style={{ color: '#faad14', fontSize: 12 }} />
                预估提升 +{Math.round(rec.estimated_confidence_boost * 100)}%
              </div>
            </div>
          </List.Item>
        )}
      />
    )
  }

  return (
    <Modal
      title={
        <div className="modal-title">
          <SafetyCertificateOutlined style={{ marginRight: 8 }} />
          用户可信度详情
        </div>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="refresh" icon={<ReloadOutlined />} loading={refreshing} onClick={handleRefresh}>
          重新评估
        </Button>,
        <Button key="close" type="primary" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={600}
      className="confidence-detail-modal"
    >
      {loading ? (
        <div className="loading-container">
          <Spin size="large" />
        </div>
      ) : detail ? (
        <div className="detail-content">
          {/* 总置信度 */}
          <div className="overall-section">
            <div className="overall-header">
              <span className="overall-icon">{LEVEL_CONFIG[detail.confidence_level].icon}</span>
              <span className="overall-level">{detail.confidence_level_name}</span>
              <span className="overall-percent">{Math.round(detail.overall_confidence * 100)}%</span>
            </div>
            <Progress
              percent={Math.round(detail.overall_confidence * 100)}
              strokeColor={LEVEL_CONFIG[detail.confidence_level].color}
              trailColor="#f0f0f0"
              strokeWidth={12}
            />
          </div>

          {/* 各维度置信度 */}
          <div className="dimensions-section">
            <div className="section-title">各维度评估</div>
            <div className="dimensions-grid">
              {Object.entries(detail.dimensions).map(([key, value]) =>
                renderDimensionProgress(key, value)
              )}
            </div>
          </div>

          {/* 异常标记 */}
          <div className="flags-section">
            <div className="section-title">信息一致性检查</div>
            {renderFlags()}
          </div>

          {/* 验证建议 */}
          <div className="recommendations-section">
            <div className="section-title">提升建议</div>
            {renderRecommendations()}
          </div>

          {/* 评估时间 */}
          {detail.last_evaluated_at && (
            <div className="evaluated-time">
              <InfoCircleOutlined />
              上次评估时间：{new Date(detail.last_evaluated_at).toLocaleString()}
            </div>
          )}
        </div>
      ) : (
        <Empty description="暂无置信度数据" />
      )}
    </Modal>
  )
}

// ==================== 简化版标记 ====================

/**
 * 置信度标记 - 用于头像角落等场景
 */
export const ConfidenceMark: React.FC<{
  level?: 'low' | 'medium' | 'high' | 'very_high'
  confidence?: number
  size?: number
}> = ({ level, confidence, size = 14 }) => {
  const resolvedConfidence = confidence ?? 0
  const config = level ? LEVEL_CONFIG[level] :
    resolvedConfidence >= 0.8 ? LEVEL_CONFIG.very_high :
    resolvedConfidence >= 0.6 ? LEVEL_CONFIG.high :
    resolvedConfidence >= 0.4 ? LEVEL_CONFIG.medium : LEVEL_CONFIG.low

  if (!level && !confidence) return null

  return (
    <span
      className="confidence-mark"
      style={{ fontSize: size, color: config.color }}
    >
      {config.icon}
    </span>
  )
}

// ==================== 进度条组件 ====================

/**
 * 置信度进度条 - 用于资料页等场景
 */
export const ConfidenceProgress: React.FC<{
  confidence: number
  showLabel?: boolean
  height?: number
}> = ({ confidence, showLabel = true, height = 8 }) => {
  const level = confidence >= 0.8 ? 'very_high' :
    confidence >= 0.6 ? 'high' :
    confidence >= 0.4 ? 'medium' : 'low'
  const config = LEVEL_CONFIG[level]

  return (
    <div className="confidence-progress-wrapper">
      {showLabel && (
        <div className="progress-label">
          <span className="label-icon">{config.icon}</span>
          <span className="label-text">{config.name}</span>
          <span className="label-percent">{Math.round(confidence * 100)}%</span>
        </div>
      )}
      <Progress
        percent={Math.round(confidence * 100)}
        strokeColor={config.color}
        trailColor="#f0f0f0"
        strokeWidth={height}
        showInfo={false}
      />
    </div>
  )
}

export default ConfidenceBadge