/**
 * AI 动态生成的问题卡片
 *
 * 用于在对话中收集用户信息，AI 自主生成问题和选项
 */

import React from 'react'
import { Card, Button, Space, Typography, Tag, Checkbox, Radio, message } from 'antd'
import { CheckCircleOutlined } from '@ant-design/icons'
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
  questionType: 'single_choice' | 'multiple_choice' | 'tags'
  options: QuestionOption[]
  dimension: string
  depth?: number  // 追问深度，0=首次提问，1+=追问
  onAnswer: (dimension: string, value: string | string[], depth: number) => void
}

const ProfileQuestionCard: React.FC<ProfileQuestionCardProps> = ({
  question,
  subtitle,
  questionType,
  options,
  dimension,
  depth = 0,
  onAnswer,
}) => {
  const [selectedValues, setSelectedValues] = React.useState<string[]>([])
  const [submitted, setSubmitted] = React.useState(false)

  // 单选点击
  const handleSingleSelect = (value: string) => {
    if (submitted) return
    setSelectedValues([value])
    // 单选自动提交
    setTimeout(() => {
      setSubmitted(true)
      onAnswer(dimension, value, depth)
    }, 200)
  }

  // 多选/标签点击
  const handleMultiSelect = (value: string) => {
    if (submitted) return

    setSelectedValues(prev => {
      if (prev.includes(value)) {
        return prev.filter(v => v !== value)
      }
      return [...prev, value]
    })
  }

  // 多选确认
  const handleConfirm = () => {
    if (selectedValues.length === 0) {
      message.warning('请至少选择一个选项')
      return
    }
    setSubmitted(true)
    onAnswer(dimension, selectedValues, depth)
  }

  // 渲染单选
  const renderSingleChoice = () => (
    <div className="question-options single-choice">
      <div className="options-grid">
        {options.map(opt => (
          <div
            key={opt.value}
            className={`option-card ${selectedValues.includes(opt.value) ? 'selected' : ''} ${submitted ? 'disabled' : ''}`}
            onClick={() => handleSingleSelect(opt.value)}
          >
            {opt.icon && <span className="option-icon">{opt.icon}</span>}
            <span className="option-label">{opt.label}</span>
            {selectedValues.includes(opt.value) && (
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
        <Title level={5} className="question-text">{question}</Title>
        {subtitle && (
          <Text type="secondary" className="question-subtitle">{subtitle}</Text>
        )}
      </div>

      <div className="question-body">
        {questionType === 'single_choice' && renderSingleChoice()}
        {questionType === 'multiple_choice' && renderMultipleChoice()}
        {questionType === 'tags' && renderTags()}
      </div>
    </Card>
  )
}

export default ProfileQuestionCard