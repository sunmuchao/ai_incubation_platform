/**
 * 高级匹配偏好设置组件
 *
 * 提供细化的匹配条件设置：
 * - 年龄范围
 * - 身高范围
 * - 教育程度
 * - 职业/行业
 * - 生活习惯
 * - 兴趣爱好
 * - 地理位置
 * - 交友目的
 * - 雷区设置
 */

import React, { useState, useEffect } from 'react'
import {
  Modal, Button, Space, Typography, Slider, Select, Tag, Input, Card,
  Divider, message, Spin, Checkbox, Row, Col, Tooltip, Badge
} from 'antd'
import {
  SettingOutlined, AgeOutlined, HeightOutlined, EducationOutlined,
  EnvironmentOutlined, HeartOutlined, WarningOutlined, BulbOutlined, SaveOutlined
} from '@ant-design/icons'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'

// 偏好维度配置
const PREFERENCE_DIMENSIONS = [
  {
    name: 'age_range',
    label: '年龄范围',
    icon: <AgeOutlined style={{ color: '#1890ff' }} />,
    type: 'range',
    default: { min: 18, max: 45 },
    marks: { 18: '18', 30: '30', 40: '40', 50: '50', 60: '60+' }
  },
  {
    name: 'height_range',
    label: '身高范围',
    icon: <HeightOutlined style={{ color: '#52c41a' }} />,
    type: 'range',
    default: { min: 150, max: 200 },
    marks: { 150: '150cm', 160: '160cm', 170: '170cm', 180: '180cm', 190: '190cm', 200: '200cm' },
    unit: 'cm'
  },
  {
    name: 'education',
    label: '教育程度',
    icon: <EducationOutlined style={{ color: '#722ed1' }} />,
    type: 'multi_select',
    options: ['高中', '大专', '本科', '硕士', '博士', '不限']
  },
  {
    name: 'occupation',
    label: '职业/行业',
    icon: <SettingOutlined style={{ color: '#fa8c16' }} />,
    type: 'multi_select',
    options: ['互联网', '金融', '教育', '医疗', '艺术', '公务员', '学生', '其他']
  },
  {
    name: 'lifestyle',
    label: '生活习惯',
    icon: <HeartOutlined style={{ color: '#eb2f96' }} />,
    type: 'multi_select',
    options: ['早睡早起', '熬夜党', '运动达人', '宅家派', '吃货', '健康饮食']
  },
  {
    name: 'location',
    label: '地理位置',
    icon: <EnvironmentOutlined style={{ color: '#13c2c2' }} />,
    type: 'location',
    default: { max_distance: 50 }
  },
  {
    name: 'relationship_goal',
    label: '交友目的',
    icon: <HeartOutlined style={{ color: PRIMARY_COLOR }} />,
    type: 'single_select',
    options: ['寻找伴侣', '结交朋友', '拓展人脉', '随缘']
  },
  {
    name: 'deal_breakers',
    label: '雷区（不接受）',
    icon: <WarningOutlined style={{ color: '#ff4d4f' }} />,
    type: 'tags',
    placeholder: '例如：抽烟、酗酒...',
    max_count: 5
  }
]

interface MatchingPreferenceProps {
  visible: boolean
  userId: string
  onClose: () => void
  onSave?: (preferences: any) => void
}

/**
 * 高级匹配偏好设置弹窗
 */
const MatchingPreference: React.FC<MatchingPreferenceProps> = ({
  visible,
  userId,
  onClose,
  onSave
}) => {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [preferences, setPreferences] = useState<any>({
    age_min: 18,
    age_max: 45,
    height_min: 150,
    height_max: 200,
    education: [],
    occupation: [],
    lifestyle: [],
    interests: [],
    location_city: '',
    max_distance: 50,
    relationship_goal: '',
    deal_breakers: []
  })
  const [suggestions, setSuggestions] = useState<any>(null)
  const [showSuggestions, setShowSuggestions] = useState(false)

  // 加载已保存的偏好
  useEffect(() => {
    if (visible && userId) {
      loadPreferences()
      loadSuggestions()
    }
  }, [visible, userId])

  const loadPreferences = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/matching-preferences/get/${userId}`)
      if (response.ok) {
        const data = await response.json()
        if (data) {
          setPreferences(data)
        }
      }
    } catch (error) {
      // 静默失败
    } finally {
      setLoading(false)
    }
  }

  const loadSuggestions = async () => {
    try {
      const response = await fetch(`/api/matching-preferences/suggestions/${userId}`)
      if (response.ok) {
        const data = await response.json()
        setSuggestions(data)
      }
    } catch (error) {
      // 静默失败
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await fetch(`/api/matching-preferences/save?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences)
      })

      if (response.ok) {
        message.success('偏好已保存')
        if (onSave) {
          onSave(preferences)
        }
        onClose()
      } else {
        message.error('保存失败')
      }
    } catch (error) {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const applySuggestions = () => {
    if (!suggestions) return

    // 应用 AI 建议
    if (suggestions.age_range) {
      setPreferences(prev => ({
        ...prev,
        age_min: suggestions.age_range.min,
        age_max: suggestions.age_range.max
      }))
    }
    if (suggestions.max_distance) {
      setPreferences(prev => ({
        ...prev,
        max_distance: suggestions.max_distance
      }))
    }
    message.success('已应用 AI 建议')
    setShowSuggestions(false)
  }

  // 渲染范围选择器
  const renderRangeSelector = (dimension: any) => {
    const minKey = `${dimension.name}_min`
    const maxKey = `${dimension.name}_max`

    return (
      <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space>
            {dimension.icon}
            <Text strong>{dimension.label}</Text>
          </Space>

          <Row gutter={16}>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12 }}>最小值</Text>
              <Slider
                min={dimension.default.min}
                max={dimension.default.max}
                value={preferences[minKey] || dimension.default.min}
                onChange={(value) => setPreferences(prev => ({ ...prev, [minKey]: value }))}
                marks={dimension.marks}
              />
            </Col>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12 }}>最大值</Text>
              <Slider
                min={dimension.default.min}
                max={dimension.default.max}
                value={preferences[maxKey] || dimension.default.max}
                onChange={(value) => setPreferences(prev => ({ ...prev, [maxKey]: value }))}
                marks={dimension.marks}
              />
            </Col>
          </Row>

          <Text style={{ textAlign: 'center', color: PRIMARY_COLOR }}>
            {preferences[minKey] || dimension.default.min} - {preferences[maxKey] || dimension.default.max} {dimension.unit || ''}
          </Text>
        </Space>
      </Card>
    )
  }

  // 渲染多选选择器
  const renderMultiSelector = (dimension: any) => {
    return (
      <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space>
            {dimension.icon}
            <Text strong>{dimension.label}</Text>
            {dimension.type === 'multi_select' && (
              <Checkbox
                checked={preferences[dimension.name]?.includes('不限') || preferences[dimension.name]?.length === 0}
                onChange={(e) => {
                  if (e.target.checked) {
                    setPreferences(prev => ({ ...prev, [dimension.name]: ['不限'] }))
                  } else {
                    setPreferences(prev => ({ ...prev, [dimension.name]: [] }))
                  }
                }}
              >
                不限
              </Checkbox>
            )}
          </Space>

          <Select
            mode="multiple"
            style={{ width: '100%' }}
            value={preferences[dimension.name] || []}
            onChange={(value) => setPreferences(prev => ({ ...prev, [dimension.name]: value }))}
            options={dimension.options.map(opt => ({ label: opt, value: opt }))}
            placeholder={`选择${dimension.label}`}
            maxTagCount={3}
          />
        </Space>
      </Card>
    )
  }

  // 渲染单选选择器
  const renderSingleSelector = (dimension: any) => {
    return (
      <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space>
            {dimension.icon}
            <Text strong>{dimension.label}</Text>
          </Space>

          <Select
            style={{ width: '100%' }}
            value={preferences[dimension.name] || undefined}
            onChange={(value) => setPreferences(prev => ({ ...prev, [dimension.name]: value }))}
            options={dimension.options.map(opt => ({ label: opt, value: opt }))}
            placeholder={`选择${dimension.label}`}
          />
        </Space>
      </Card>
    )
  }

  // 渲染地理位置设置
  const renderLocationSetting = () => {
    return (
      <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space>
            <EnvironmentOutlined style={{ color: '#13c2c2' }} />
            <Text strong>地理位置偏好</Text>
          </Space>

          <Input
            placeholder="输入城市名称"
            value={preferences.location_city || ''}
            onChange={(e) => setPreferences(prev => ({ ...prev, location_city: e.target.value }))}
          />

          <Text type="secondary" style={{ fontSize: 12 }}>最大匹配距离</Text>
          <Slider
            min={5}
            max={200}
            value={preferences.max_distance || 50}
            onChange={(value) => setPreferences(prev => ({ ...prev, max_distance: value }))}
            marks={{ 5: '5km', 50: '50km', 100: '100km', 200: '200km' }}
          />
          <Text style={{ textAlign: 'center', color: PRIMARY_COLOR }}>
            {preferences.max_distance || 50} km
          </Text>
        </Space>
      </Card>
    )
  }

  // 渲染标签输入（雷区）
  const renderTagsInput = (dimension: any) => {
    const tags = preferences[dimension.name] || []

    const handleAddTag = (e: any) => {
      const value = e.target.value
      if (value && !tags.includes(value) && tags.length < dimension.max_count) {
        setPreferences(prev => ({ ...prev, [dimension.name]: [...tags, value] }))
        e.target.value = ''
      }
    }

    const handleRemoveTag = (tag: string) => {
      setPreferences(prev => ({
        ...prev,
        [dimension.name]: tags.filter(t => t !== tag)
      }))
    }

    return (
      <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space>
            {dimension.icon}
            <Text strong>{dimension.label}</Text>
            <Badge count={`${tags.length}/${dimension.max_count}`} style={{ backgroundColor: '#ff4d4f' }} />
          </Space>

          <div>
            {tags.map((tag: string) => (
              <Tag
                key={tag}
                closable
                onClose={() => handleRemoveTag(tag)}
                style={{ marginBottom: 4 }}
                color="red"
              >
                {tag}
              </Tag>
            ))}
          </div>

          <Input
            placeholder={dimension.placeholder}
            onPressEnter={handleAddTag}
            disabled={tags.length >= dimension.max_count}
          />

          <Text type="secondary" style={{ fontSize: 12 }}>
            {dimension.max_count} 个以内的雷区关键词
          </Text>
        </Space>
      </Card>
    )
  }

  // 渲染 AI 建议
  const renderSuggestions = () => {
    if (!suggestions) return null

    return (
      <Card
        size="small"
        style={{
          marginBottom: 16,
          borderRadius: 12,
          background: 'rgba(255, 215, 0, 0.1)'
        }}
      >
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space>
              <BulbOutlined style={{ color: '#FFD700' }} />
              <Text strong style={{ color: '#FFD700' }}>AI 建议偏好</Text>
            </Space>
            <Button size="small" type="primary" onClick={applySuggestions}>
              应用建议
            </Button>
          </Space>

          {suggestions.age_range && (
            <Text type="secondary">
              年龄范围：{suggestions.age_range.min} - {suggestions.age_range.max}
              <Text style={{ fontSize: 10, marginLeft: 8 }}>{suggestions.age_range.reason}</Text>
            </Text>
          )}

          {suggestions.max_distance && (
            <Text type="secondary">
              推荐距离：{suggestions.max_distance} km
            </Text>
          )}

          {suggestions.lifestyle_compatibility && (
            <Text type="secondary">
              期望习惯：{suggestions.lifestyle_compatibility.join(', ')}
            </Text>
          )}
        </Space>
      </Card>
    )
  }

  // 渲染维度设置
  const renderDimensionSettings = () => {
    return PREFERENCE_DIMENSIONS.map(dimension => {
      switch (dimension.type) {
        case 'range':
          return renderRangeSelector(dimension)
        case 'multi_select':
          return renderMultiSelector(dimension)
        case 'single_select':
          return renderSingleSelector(dimension)
        case 'location':
          return renderLocationSetting()
        case 'tags':
          return renderTagsInput(dimension)
        default:
          return null
      }
    })
  }

  return (
    <Modal
      title={
        <Space>
          <SettingOutlined style={{ color: PRIMARY_COLOR }} />
          <span>匹配偏好设置</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="suggestions" onClick={() => setShowSuggestions(!showSuggestions)}>
          {showSuggestions ? '隐藏建议' : 'AI 建议'}
        </Button>,
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button
          key="save"
          type="primary"
          icon={<SaveOutlined />}
          loading={saving}
          onClick={handleSave}
          style={{ background: PRIMARY_COLOR, borderColor: PRIMARY_COLOR }}
        >
          保存偏好
        </Button>,
      ]}
      width={600}
      styles={{ body: { padding: 16, maxHeight: '60vh', overflowY: 'auto' } }}
    >
      {loading ? (
        <Spin size="large" tip="加载偏好设置..." />
      ) : (
        <div>
          {/* AI 建议 */}
          {showSuggestions && renderSuggestions()}

          {/* 偏好设置 */}
          {renderDimensionSettings()}

          {/* 底部提示 */}
          <Divider />
          <Paragraph type="secondary" style={{ fontSize: 12, textAlign: 'center' }}>
            💡 更精确的偏好设置可以帮你找到更合适的匹配对象
          </Paragraph>
        </div>
      )}
    </Modal>
  )
}

/**
 * 匹配偏好按钮（放在 Header）
 */
export const PreferenceButton: React.FC<{ userId: string; onSave?: (preferences: any) => void }> = ({
  userId,
  onSave
}) => {
  const [modalVisible, setModalVisible] = useState(false)

  return (
    <>
      <Tooltip title="匹配偏好">
        <Button
          type="text"
          icon={<SettingOutlined style={{ color: PRIMARY_COLOR }} />}
          onClick={() => setModalVisible(true)}
        />
      </Tooltip>
      <MatchingPreference
        visible={modalVisible}
        userId={userId}
        onClose={() => setModalVisible(false)}
        onSave={onSave}
      />
    </>
  )
}

export default MatchingPreference