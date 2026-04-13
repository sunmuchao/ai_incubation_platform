/**
 * AI 动态生成的问题卡片
 *
 * 用于在对话中收集用户信息，AI 自主生成问题和选项
 */

import React from 'react'
import { Card, Button, Space, Typography, Tag, Checkbox, Radio, message, Spin, Input } from 'antd'
import { CheckCircleOutlined, LoadingOutlined, ForwardOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import './ProfileQuestionCard.less'

const { Text, Title } = Typography

interface QuestionOption {
  value: string
  label: string
  icon?: string
}

interface ProfileQuestionCardProps {
  question: string
  subtitle?: string
  questionType: 'single_choice' | 'multiple_choice' | 'tags' | 'input'
  options: QuestionOption[]
  dimension: string
  depth?: number  // 追问深度，0=首次提问，1+=追问
  optional?: boolean  // 是否为可选字段（用户可跳过）
  onAnswer: (dimension: string, value: string | string[], depth: number) => Promise<void>  // 改为 Promise
  onSkip?: (dimension: string) => Promise<void>  // 跳过回调
}

const ProfileQuestionCard: React.FC<ProfileQuestionCardProps> = ({
  question,
  subtitle,
  questionType,
  options,
  dimension,
  depth = 0,
  optional = false,
  onAnswer,
  onSkip,
}) => {
  const { t } = useTranslation()
  const [selectedValues, setSelectedValues] = React.useState<string[]>([])
  const [inputValue, setInputValue] = React.useState('')
  const [submitted, setSubmitted] = React.useState(false)
  const [loading, setLoading] = React.useState(false)  // 新增 loading 状态
  const [skipping, setSkipping] = React.useState(false)  // 跳过 loading 状态
  const [error, setError] = React.useState<string | null>(null)  // 新增 error 状态

  // 单选点击
  const handleSingleSelect = async (value: string) => {
    if (submitted || loading) return
    setSelectedValues([value])
    setSubmitted(true)
    setLoading(true)  // 开始 loading
    setError(null)  // 清除错误

    try {
      await onAnswer(dimension, value, depth)
      setLoading(false)  // 成功后关闭 loading
    } catch (err) {
      console.error('Failed to submit answer:', err)
      setError('提交失败，请重试')
      setSubmitted(false)  // 允许重新选择
      setLoading(false)
    }
  }

  // 输入框提交
  const handleInputSubmit = async () => {
    if (!inputValue.trim()) {
      message.warning('请输入内容')
      return
    }
    if (submitted || loading) return

    setSubmitted(true)
    setLoading(true)
    setError(null)

    try {
      await onAnswer(dimension, inputValue.trim(), depth)
      setLoading(false)  // 成功后关闭 loading
    } catch (err) {
      console.error('Failed to submit answer:', err)
      setError('提交失败，请重试')
      setSubmitted(false)
      setLoading(false)
    }
  }

  // 跳过处理
  const handleSkip = async () => {
    if (skipping || !onSkip) return
    setSkipping(true)
    setError(null)

    try {
      await onSkip(dimension)
    } catch (err) {
      console.error('Failed to skip:', err)
      setError('跳过失败，请重试')
      setSkipping(false)
    }
  }

  // 多选/标签点击
  const handleMultiSelect = (value: string) => {
    if (submitted || loading) return

    setSelectedValues(prev => {
      if (prev.includes(value)) {
        return prev.filter(v => v !== value)
      }
      return [...prev, value]
    })
  }

  // 多选确认
  const handleConfirm = async () => {
    if (selectedValues.length === 0) {
      message.warning('请至少选择一个选项')
      return
    }
    if (submitted || loading) return

    setSubmitted(true)
    setLoading(true)  // 开始 loading
    setError(null)

    try {
      await onAnswer(dimension, selectedValues, depth)
    } catch (err) {
      console.error('Failed to submit answer:', err)
      setError('提交失败，请重试')
      setSubmitted(false)  // 允许重新选择
      setLoading(false)
    }
  }

  // 渲染输入框
  const renderInput = () => (
    <div className="question-options input-choice">
      {loading && (
        <div className="loading-overlay">
          <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
          <Text type="secondary" style={{ marginTop: 12 }}>正在处理...</Text>
        </div>
      )}
      {error && (
        <div className="error-overlay">
          <Text type="danger">{error}</Text>
        </div>
      )}
      <Input
        placeholder={t('conversation.inputPlaceholder')}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onPressEnter={handleInputSubmit}
        disabled={submitted || loading}
        size="large"
        style={{ borderRadius: 12 }}
      />
      {!submitted && inputValue.trim() && (
        <Button
          type="primary"
          block
          onClick={handleInputSubmit}
          style={{
            marginTop: 12,
            background: 'linear-gradient(135deg, #D4A59A 0%, #C88B8B 100%)',
            border: 'none',
            borderRadius: 20,
          }}
        >
          确认
        </Button>
      )}
    </div>
  )

  // 渲染单选
  const renderSingleChoice = () => (
    <div className="question-options single-choice">
      {/* Loading 状态显示 */}
      {loading && (
        <div className="loading-overlay">
          <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
          <Text type="secondary" style={{ marginTop: 12 }}>正在处理...</Text>
        </div>
      )}
      {/* 错误提示 */}
      {error && (
        <div className="error-overlay">
          <Text type="danger">{error}</Text>
        </div>
      )}
      <div className={`options-grid ${loading ? 'hidden' : ''}`}>
        {options.map(opt => (
          <div
            key={opt.value}
            className={`option-card ${selectedValues.includes(opt.value) ? 'selected' : ''} ${submitted ? 'disabled' : ''}`}
            onClick={() => handleSingleSelect(opt.value)}
          >
            {opt.icon && <span className="option-icon">{opt.icon}</span>}
            <span className="option-label">{opt.label}</span>
            {selectedValues.includes(opt.value) && !loading && (
              <CheckCircleOutlined className="check-icon" />
            )}
          </div>
        ))}
      </div>
    </div>
  )

  // 渲染多选
  const renderMultipleChoice = () => (
    <div className="question-options multiple-choice">
      <Checkbox.Group
        value={selectedValues}
        onChange={(vals) => !submitted && setSelectedValues(vals as string[])}
        style={{ width: '100%' }}
        disabled={submitted}
      >
        <div className="options-grid">
          {options.map(opt => (
            <div
              key={opt.value}
              className={`option-card checkbox ${selectedValues.includes(opt.value) ? 'selected' : ''}`}
            >
              <Checkbox value={opt.value}>
                {opt.icon && <span className="option-icon">{opt.icon}</span>}
                {opt.label}
              </Checkbox>
            </div>
          ))}
        </div>
      </Checkbox.Group>

      {!submitted && selectedValues.length > 0 && (
        <Button
          type="primary"
          block
          onClick={handleConfirm}
          style={{
            marginTop: 16,
            background: 'linear-gradient(135deg, #D4A59A 0%, #C88B8B 100%)',
            border: 'none',
            borderRadius: 20,
          }}
        >
          确认选择 ({selectedValues.length})
        </Button>
      )}
    </div>
  )

  // 渲染标签选择
  const renderTags = () => (
    <div className="question-options tags-choice">
      <div className="tags-container">
        {options.map(opt => (
          <Tag
            key={opt.value}
            className={`question-tag ${selectedValues.includes(opt.value) ? 'selected' : ''} ${submitted ? 'disabled' : ''}`}
            onClick={() => handleMultiSelect(opt.value)}
          >
            {opt.icon && <span style={{ marginRight: 4 }}>{opt.icon}</span>}
            {opt.label}
          </Tag>
        ))}
      </div>

      {selectedValues.length > 0 && !submitted && (
        <div className="tags-footer">
          <Text type="secondary">已选择 {selectedValues.length} 个</Text>
          <Button
            type="primary"
            size="small"
            onClick={handleConfirm}
            style={{
              background: 'linear-gradient(135deg, #D4A59A 0%, #C88B8B 100%)',
              border: 'none',
              borderRadius: 16,
            }}
          >
            确认
          </Button>
        </div>
      )}
    </div>
  )

  return (
    <Card className={`profile-question-card ${depth > 0 ? 'follow-up' : ''}`} bordered={false}>
      <div className="question-header">
        {depth > 0 && (
          <Tag color="#D4A59A" style={{ marginBottom: 8, fontSize: 11 }}>
            再说说看~
          </Tag>
        )}
        {optional && (
          <Tag color="#999" style={{ marginBottom: 8, fontSize: 11 }}>
            {t('conversation.qsOptional')}
          </Tag>
        )}
        <Title level={5} className="question-text">{question}</Title>
        {subtitle && (
          <Text type="secondary" className="question-subtitle">{subtitle}</Text>
        )}
      </div>

      <div className="question-body">
        {questionType === 'single_choice' && renderSingleChoice()}
        {questionType === 'multiple_choice' && renderMultipleChoice()}
        {questionType === 'tags' && renderTags()}
        {questionType === 'input' && renderInput()}
      </div>

      {/* 可选字段的跳过按钮 */}
      {optional && !submitted && !loading && !skipping && onSkip && (
        <div className="skip-footer" style={{ marginTop: 12, textAlign: 'center' }}>
          <Button
            type="text"
            onClick={handleSkip}
            icon={<ForwardOutlined />}
            style={{ color: '#999' }}
          >
            {t('conversation.qsSkip')}
          </Button>
        </div>
      )}

      {/* 跳过 loading */}
      {skipping && (
        <div className="loading-overlay" style={{ marginTop: 12 }}>
          <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
          <Text type="secondary" style={{ marginTop: 12 }}>正在跳过...</Text>
        </div>
      )}
    </Card>
  )
}

export default ProfileQuestionCard