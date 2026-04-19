/**
 * 置信度筛选组件
 *
 * 功能：
 * - 按置信度等级筛选匹配列表
 * - 显示当前筛选条件
 * - 支持多选或单选筛选
 */

import React, { useState, useEffect } from 'react'
import { Radio, Space, Tag, Slider, Switch, Typography, Card, Tooltip } from 'antd'
import {
  SafetyCertificateOutlined,
  FilterOutlined,
  ClearOutlined,
} from '@ant-design/icons'
import type { ConfidenceLevel } from './ConfidenceBadge'
import './ConfidenceFilter.less'

const { Text } = Typography

// ============================================
// 置信度等级配置
// ============================================

const LEVEL_CONFIGS: Record<ConfidenceLevel, { color: string; icon: string; name: string; range: string }> = {
  very_high: { color: '#faad14', icon: '💎', name: '极可信', range: '80-100%' },
  high: { color: '#52c41a', icon: '🌟', name: '较可信', range: '60-80%' },
  medium: { color: '#1890ff', icon: '✓', name: '普通用户', range: '40-60%' },
  low: { color: '#fa8c16', icon: '⚠️', name: '需谨慎', range: '0-40%' },
}

// ============================================
// 置信度筛选组件
// ============================================

interface ConfidenceFilterProps {
  /** 筛选变更回调 */
  onChange: (filter: ConfidenceFilterValue) => void
  /** 当前筛选值 */
  value?: ConfidenceFilterValue
  /** 显示模式：simple（等级选择）或 advanced（范围滑块） */
  mode?: 'simple' | 'advanced'
  /** 是否显示已认证筛选 */
  showVerifiedSwitch?: boolean
  /** 是否显示无异常筛选 */
  showNoFlagsSwitch?: boolean
}

export interface ConfidenceFilterValue {
  /** 最小置信度（0-100） */
  minConfidence?: number
  /** 筛选等级列表 */
  levels?: ConfidenceLevel[]
  /** 是否只看已认证用户 */
  verifiedOnly?: boolean
  /** 是否排除有异常标记的用户 */
  noFlagsOnly?: boolean
}

const ConfidenceFilter: React.FC<ConfidenceFilterProps> = ({
  onChange,
  value = {},
  mode = 'simple',
  showVerifiedSwitch = true,
  showNoFlagsSwitch = true,
}) => {
  // 状态
  const [selectedLevel, setSelectedLevel] = useState<ConfidenceLevel | 'all'>(
    value.levels?.[0] || 'all'
  )
  const [minConfidence, setMinConfidence] = useState<number>(
    value.minConfidence || 0
  )
  const [verifiedOnly, setVerifiedOnly] = useState<boolean>(
    value.verifiedOnly || false
  )
  const [noFlagsOnly, setNoFlagsOnly] = useState<boolean>(
    value.noFlagsOnly || false
  )

  // 等级变更处理
  const handleLevelChange = (level: ConfidenceLevel | 'all') => {
    setSelectedLevel(level)
    const newValue: ConfidenceFilterValue = {
      levels: level === 'all' ? undefined : [level],
      minConfidence: level === 'all' ? 0 : getLevelMinValue(level),
      verifiedOnly,
      noFlagsOnly,
    }
    onChange(newValue)
  }

  // 获取等级最小值
  const getLevelMinValue = (level: ConfidenceLevel): number => {
    switch (level) {
      case 'very_high':
        return 80
      case 'high':
        return 60
      case 'medium':
        return 40
      case 'low':
        return 0
      default:
        return 0
    }
  }

  // 滑块变更处理
  const handleSliderChange = (value: number) => {
    setMinConfidence(value)
    const newValue: ConfidenceFilterValue = {
      minConfidence: value,
      verifiedOnly,
      noFlagsOnly,
    }
    onChange(newValue)
  }

  // 已认证开关变更
  const handleVerifiedChange = (checked: boolean) => {
    setVerifiedOnly(checked)
    onChange({
      ...getCurrentValue(),
      verifiedOnly: checked,
    })
  }

  // 无异常开关变更
  const handleNoFlagsChange = (checked: boolean) => {
    setNoFlagsOnly(checked)
    onChange({
      ...getCurrentValue(),
      noFlagsOnly: checked,
    })
  }

  // 获取当前值
  const getCurrentValue = (): ConfidenceFilterValue => {
    if (mode === 'simple') {
      return {
        levels: selectedLevel === 'all' ? undefined : [selectedLevel],
        minConfidence: selectedLevel === 'all' ? 0 : getLevelMinValue(selectedLevel),
        verifiedOnly,
        noFlagsOnly,
      }
    } else {
      return {
        minConfidence,
        verifiedOnly,
        noFlagsOnly,
      }
    }
  }

  // 清除筛选
  const handleClear = () => {
    setSelectedLevel('all')
    setMinConfidence(0)
    setVerifiedOnly(false)
    setNoFlagsOnly(false)
    onChange({
      minConfidence: 0,
      verifiedOnly: false,
      noFlagsOnly: false,
    })
  }

  // 判断是否有筛选条件
  const hasFilter = selectedLevel !== 'all' || minConfidence > 0 || verifiedOnly || noFlagsOnly

  return (
    <Card className="confidence-filter-card" size="small" bordered={false}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* 标题 */}
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
            <Text strong>置信度筛选</Text>
          </Space>
          {hasFilter && (
            <Tooltip title="清除筛选">
              <Tag
                style={{ cursor: 'pointer' }}
                onClick={handleClear}
              >
                <ClearOutlined /> 清除
              </Tag>
            </Tooltip>
          )}
        </Space>

        {/* 等级选择模式 */}
        {mode === 'simple' && (
          <Radio.Group
            value={selectedLevel}
            onChange={(e) => handleLevelChange(e.target.value)}
            className="level-radio-group"
          >
            <Radio.Button value="all">全部</Radio.Button>
            {Object.entries(LEVEL_CONFIGS).map(([level, config]) => (
              <Radio.Button key={level} value={level}>
                <Space size={4}>
                  <span>{config.icon}</span>
                  <span>{config.name}</span>
                </Space>
              </Radio.Button>
            ))}
          </Radio.Group>
        )}

        {/* 高级模式 - 滑块 */}
        {mode === 'advanced' && (
          <div className="slider-container">
            <Text type="secondary">最低置信度：{minConfidence}%</Text>
            <Slider
              value={minConfidence}
              onChange={handleSliderChange}
              min={0}
              max={100}
              marks={{
                0: '0%',
                40: '40%',
                60: '60%',
                80: '80%',
                100: '100%',
              }}
              tooltip={{ formatter: (value) => `${value}%` }}
            />
          </div>
        )}

        {/* 附加筛选开关 */}
        <Space size="middle">
          {showVerifiedSwitch && (
            <Space>
              <Switch
                size="small"
                checked={verifiedOnly}
                onChange={handleVerifiedChange}
              />
              <Text type="secondary">仅已认证</Text>
            </Space>
          )}
          {showNoFlagsSwitch && (
            <Space>
              <Switch
                size="small"
                checked={noFlagsOnly}
                onChange={handleNoFlagsChange}
              />
              <Text type="secondary">无异常标记</Text>
            </Space>
          )}
        </Space>

        {/* 当前筛选摘要 */}
        {hasFilter && (
          <div className="filter-summary">
            <Space size={4}>
              <FilterOutlined style={{ color: '#1890ff' }} />
              <Text type="secondary">
                {mode === 'simple' && selectedLevel !== 'all'
                  ? `筛选：${LEVEL_CONFIGS[selectedLevel].name}（${LEVEL_CONFIGS[selectedLevel].range}）`
                  : mode === 'advanced' && minConfidence > 0
                  ? `置信度 ≥ ${minConfidence}%`
                  : ''}
              </Text>
              {verifiedOnly && (
                <Tag color="blue" style={{ marginLeft: 4 }}>已认证</Tag>
              )}
              {noFlagsOnly && (
                <Tag color="green" style={{ marginLeft: 4 }}>无异常</Tag>
              )}
            </Space>
          </div>
        )}
      </Space>
    </Card>
  )
}

export default ConfidenceFilter