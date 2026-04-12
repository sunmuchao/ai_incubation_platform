/**
 * 快速入门页面 - 30秒开始匹配
 *
 * 传统红娘模式：
 * 1. 快速了解（年龄、性别、城市、关系目标）
 * 2. 立即推荐
 * 3. 观察反馈
 * 4. 渐进调整
 */

import React, { useState, useEffect } from 'react'
import { Card, Button, Typography, Space, Avatar, Tag, Spin, Modal, Input, message } from 'antd'
import {
  HeartOutlined,
  CloseOutlined,
  RightOutlined,
  UserOutlined,
  EnvironmentOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { quickStartApi, type QuickStartMatch, type RelationshipGoalOption } from '../api/quickStartApi'
import { authStorage } from '../utils/storage'
import './QuickStartPage.less'

const { Title, Text } = Typography

// ==================== 步骤定义 ====================

type Step = 'welcome' | 'age' | 'gender' | 'location' | 'goal' | 'matches' | 'feedback'

// ==================== 组件 ====================

const QuickStartPage: React.FC<{
  onComplete?: (userId: string) => void
}> = ({ onComplete }) => {
  // 状态
  const [currentStep, setCurrentStep] = useState<Step>('welcome')
  const [loading, setLoading] = useState(false)
  const [options, setOptions] = useState<{
    relationship_goal_options: RelationshipGoalOption[]
    dislike_reason_options: any[]
  } | null>(null)

  // 用户输入 - 优先从已存储的用户信息中读取
  const [age, setAge] = useState<number | null>(() => {
    const user = authStorage.getUser()
    return user?.age ?? null
  })
  const [gender, setGender] = useState<string | null>(() => {
    const user = authStorage.getUser()
    return user?.gender ?? null
  })
  const [location, setLocation] = useState<string>(() => {
    const user = authStorage.getUser()
    return user?.location ?? ''
  })
  const [relationshipGoal, setRelationshipGoal] = useState<string | null>(null)

  // 匹配结果
  const [userId, setUserId] = useState<string>('')
  const [matches, setMatches] = useState<QuickStartMatch[]>([])
  const [aiMessage, setAiMessage] = useState<string>('')
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0)

  // 统计
  const [viewedCount, setViewedCount] = useState(0)
  const [likedCount, setLikedCount] = useState(0)
  const [dislikedCount, setDislikedCount] = useState(0)
  const [skippedCount, setSkippedCount] = useState(0)

  // 反馈追问
  const [showFeedbackModal, setShowFeedbackModal] = useState(false)
  const [feedbackMatchId, setFeedbackMatchId] = useState<string>('')
  const [showNextMatches, setShowNextMatches] = useState(false)
  const [nextMatches, setNextMatches] = useState<QuickStartMatch[]>([])
  const [feedbackAiResponse, setFeedbackAiResponse] = useState<string>('')

  // 初始化选项
  useEffect(() => {
    loadOptions()
  }, [])

  const loadOptions = async () => {
    try {
      const opts = await quickStartApi.getOptions()
      setOptions(opts)
    } catch (e) {
      console.error('Failed to load options:', e)
    }
  }

  // ==================== 步骤处理 ====================

  /**
   * 根据已收集的信息决定跳转到哪个步骤
   * 跳过策略：年龄 → 性别 → 所在地 → 关系目标
   */
  const handleStart = () => {
    // 如果年龄已收集，跳过年龄步骤
    if (age) {
      // 如果性别已收集，跳过性别步骤
      if (gender) {
        // 如果所在地已收集，跳过所在地步骤
        if (location.trim()) {
          // 所需信息都已收集，直接跳到关系目标步骤
          setCurrentStep('goal')
        } else {
          setCurrentStep('location')
        }
      } else {
        setCurrentStep('gender')
      }
    } else {
      setCurrentStep('age')
    }
  }

  const handleSelectAge = (selectedAge: number) => {
    setAge(selectedAge)
    // 如果性别已收集，跳过性别步骤
    if (gender) {
      // 如果所在地已收集，跳过所在地步骤
      if (location.trim()) {
        setCurrentStep('goal')
      } else {
        setCurrentStep('location')
      }
    } else {
      setCurrentStep('gender')
    }
  }

  const handleSelectGender = (selectedGender: string) => {
    setGender(selectedGender)
    // 如果所在地已收集，跳过所在地步骤
    if (location.trim()) {
      setCurrentStep('goal')
    } else {
      setCurrentStep('location')
    }
  }

  const handleInputLocation = () => {
    if (!location.trim()) {
      message.warning('请输入所在城市')
      return
    }
    setCurrentStep('goal')
  }

  const handleSelectGoal = async (selectedGoal: string) => {
    setRelationshipGoal(selectedGoal)
    // 直接使用 selectedGoal 而不是等待 state 更新
    await submitQuickStart(selectedGoal)
  }

  const submitQuickStart = async (goal?: string) => {
    // 使用传入的 goal 参数或 state 中的 relationshipGoal
    const effectiveGoal = goal || relationshipGoal

    // 验证必填字段
    if (!age) {
      message.error('请先选择年龄')
      setCurrentStep('age')
      setLoading(false)
      return
    }
    if (!gender) {
      message.error('请先选择性别')
      setCurrentStep('gender')
      setLoading(false)
      return
    }
    if (!location.trim()) {
      message.error('请先输入所在地')
      setCurrentStep('location')
      setLoading(false)
      return
    }
    if (!effectiveGoal) {
      message.error('请先选择关系目标')
      setCurrentStep('goal')
      setLoading(false)
      return
    }

    setLoading(true)

    try {
      // 获取已登录用户ID（如果有）
      const existingUser = authStorage.getUser()
      const existingUserId = existingUser?.id || existingUser?.username

      const response = await quickStartApi.quickRegister({
        user_id: existingUserId,
        age: age,
        gender: gender,
        location: location,
        relationship_goal: effectiveGoal,
      })

      if (response.success) {
        setUserId(response.data.user_id)
        setMatches(response.data.initial_matches)
        setAiMessage(response.data.ai_message)
        setCurrentStep('matches')
        setCurrentMatchIndex(0)
      } else {
        message.error('快速入门失败')
      }
    } catch (e) {
      console.error('Quick start failed:', e)
      message.error('快速入门失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  // ==================== 匹配反馈处理 ====================

  const handleLike = async () => {
    if (!matches[currentMatchIndex]) return

    const match = matches[currentMatchIndex]
    setLikedCount(prev => prev + 1)
    setViewedCount(prev => prev + 1)

    // 发送反馈
    try {
      await quickStartApi.processFeedback({
        user_id: userId,
        match_id: match.user_id,
        feedback_type: 'like',
      })

      message.success('已记录，可以开始聊天了~')

      // 保存用户ID
      authStorage.setUser({ id: userId, username: userId })

      // 更新统计
      await quickStartApi.updateStats({
        user_id: userId,
        viewed_count: viewedCount + 1,
        liked_count: likedCount + 1,
        disliked_count: dislikedCount,
        skipped_count: skippedCount,
      })

      // 完成
      if (onComplete) {
        onComplete(userId)
      }
    } catch (e) {
      console.error('Feedback failed:', e)
    }
  }

  const handleDislike = () => {
    if (!matches[currentMatchIndex]) return

    const match = matches[currentMatchIndex]
    setFeedbackMatchId(match.user_id)
    setShowFeedbackModal(true)
  }

  const handleSelectDislikeReason = async (reason: string) => {
    setShowFeedbackModal(false)
    setDislikedCount(prev => prev + 1)
    setViewedCount(prev => prev + 1)

    try {
      const response = await quickStartApi.processFeedback({
        user_id: userId,
        match_id: feedbackMatchId,
        feedback_type: 'dislike',
        dislike_reason: reason,
      })

      if (response.success) {
        setFeedbackAiResponse(response.data.ai_response)
        setNextMatches(response.data.next_matches)
        setShowNextMatches(true)
      }
    } catch (e) {
      console.error('Feedback failed:', e)
    }
  }

  const handleSkip = async () => {
    if (!matches[currentMatchIndex]) return

    const match = matches[currentMatchIndex]
    setSkippedCount(prev => prev + 1)
    setViewedCount(prev => prev + 1)

    try {
      await quickStartApi.processFeedback({
        user_id: userId,
        match_id: match.user_id,
        feedback_type: 'skip',
      })
    } catch (e) {
      console.error('Feedback failed:', e)
    }

    // 下一个
    goToNextMatch()
  }

  const goToNextMatch = () => {
    if (currentMatchIndex < matches.length - 1) {
      setCurrentMatchIndex(prev => prev + 1)
      setShowNextMatches(false)
    } else if (nextMatches.length > 0) {
      // 使用新的推荐
      setMatches(nextMatches)
      setCurrentMatchIndex(0)
      setNextMatches([])
      setShowNextMatches(false)
    } else {
      message.info('暂时没有更多推荐了，稍后再来~')
    }
  }

  const handleContinueWithNextMatches = () => {
    setMatches(nextMatches)
    setCurrentMatchIndex(0)
    setNextMatches([])
    setShowNextMatches(false)
  }

  // ==================== 渲染 ====================

  const currentMatch = matches[currentMatchIndex]

  // 计算已收集的信息数量
  const collectedInfoCount = [age, gender, location.trim()].filter(Boolean).length
  const hasCollectedInfo = collectedInfoCount > 0

  return (
    <div className="quick-start-page">
      {/* 欢迎步骤 */}
      {currentStep === 'welcome' && (
        <Card className="welcome-card">
          <Space direction="vertical" size="large" align="center">
            <Avatar size={80} src="/her-avatar.svg" />
            <Title level={3}>你好！我是 Her，帮你找对象的朋友</Title>
            {hasCollectedInfo ? (
              <>
                <Text type="secondary">
                  我已经知道一些你的信息了，只需再确认一下关系目标~
                </Text>
                <Space size="small">
                  {age && <Tag color="green">年龄: {age}岁</Tag>}
                  {gender && <Tag color="green">性别: {gender === 'male' ? '男' : '女'}</Tag>}
                  {location.trim() && <Tag color="green">所在地: {location}</Tag>}
                </Space>
              </>
            ) : (
              <Text type="secondary">
                先了解几个关键信息，马上给你推荐~
              </Text>
            )}
            <Button type="primary" size="large" onClick={handleStart}>
              开始 <RightOutlined />
            </Button>
          </Space>
        </Card>
      )}

      {/* 年龄步骤 */}
      {currentStep === 'age' && (
        <Card className="step-card">
          <Title level={4}>你多大啦？</Title>
          <div className="age-options">
            {[18, 20, 25, 30, 35, 40, 45, 50].map(a => (
              <Button
                key={a}
                className="option-btn"
                onClick={() => handleSelectAge(a)}
              >
                {a}岁
              </Button>
            ))}
          </div>
        </Card>
      )}

      {/* 性别步骤 */}
      {currentStep === 'gender' && (
        <Card className="step-card">
          <Title level={4}>你是男生还是女生？</Title>
          <div className="gender-options">
            <Button className="option-btn gender-btn" onClick={() => handleSelectGender('male')}>
              男生 👨
            </Button>
            <Button className="option-btn gender-btn" onClick={() => handleSelectGender('female')}>
              女生 👩
            </Button>
          </div>
        </Card>
      )}

      {/* 城市步骤 */}
      {currentStep === 'location' && (
        <Card className="step-card">
          <Title level={4}>你在哪个城市？</Title>
          <Input
            placeholder="输入城市名，如：北京"
            value={location}
            onChange={e => setLocation(e.target.value)}
            size="large"
            prefix={<EnvironmentOutlined />}
          />
          <div className="hot-cities">
            {['北京', '上海', '广州', '深圳', '杭州', '成都'].map(city => (
              <Tag key={city} onClick={() => setLocation(city)} className="city-tag">
                {city}
              </Tag>
            ))}
          </div>
          <Button type="primary" size="large" onClick={handleInputLocation}>
            下一步 <RightOutlined />
          </Button>
        </Card>
      )}

      {/* 关系目标步骤 */}
      {currentStep === 'goal' && (
        <Card className="step-card">
          <Title level={4}>想找什么样的关系？</Title>
          {loading ? (
            <Spin size="large" />
          ) : (
            <div className="goal-options">
              {options?.relationship_goal_options.map(opt => (
                <Button
                  key={opt.value}
                  className="option-btn goal-btn"
                  onClick={() => handleSelectGoal(opt.value)}
                >
                  {opt.icon} {opt.label}
                </Button>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* 匹配结果步骤 */}
      {currentStep === 'matches' && (
        <div className="matches-container">
          {/* AI 开场白 */}
          <div className="ai-message">
            <Avatar size={40} src="/her-avatar.svg" />
            <Text>{aiMessage}</Text>
          </div>

          {/* 当前匹配 */}
          {currentMatch && !showNextMatches && (
            <Card className="match-card">
              <div className="match-header">
                <Avatar size={60} icon={<UserOutlined />} src={currentMatch.avatar_url} />
                <div className="match-info">
                  <Title level={4}>{currentMatch.name}</Title>
                  <Space>
                    <Tag><CalendarOutlined /> {currentMatch.age}岁</Tag>
                    <Tag><EnvironmentOutlined /> {currentMatch.location}</Tag>
                  </Space>
                </div>
              </div>

              {/* 匹配预览 */}
              <div className="match-preview">
                <Text type="secondary">{currentMatch.compatibility_preview}</Text>
              </div>

              {/* 社会认同 */}
              {currentMatch.social_proof?.elements?.length > 0 && (
                <div className="social-proof">
                  {currentMatch.social_proof.elements.map((el, idx) => (
                    <Tag key={idx} color="green">{el}</Tag>
                  ))}
                </div>
              )}

              {/* 操作按钮 */}
              <div className="match-actions">
                <Button
                  type="primary"
                  size="large"
                  icon={<HeartOutlined />}
                  onClick={handleLike}
                >
                  喜欢
                </Button>
                <Button
                  size="large"
                  icon={<CloseOutlined />}
                  onClick={handleDislike}
                >
                  不喜欢
                </Button>
                <Button
                  size="large"
                  onClick={handleSkip}
                >
                  跳过 <RightOutlined />
                </Button>
              </div>
            </Card>
          )}

          {/* 新推荐提示 */}
          {showNextMatches && nextMatches.length > 0 && (
            <Card className="next-matches-card">
              <div className="feedback-response">
                <Avatar size={40} src="/her-avatar.svg" />
                <Text>{feedbackAiResponse}</Text>
              </div>
              <Button type="primary" size="large" onClick={handleContinueWithNextMatches}>
                看看新的推荐 <RightOutlined />
              </Button>
            </Card>
          )}
        </div>
      )}

      {/* 不喜欢追问弹窗 */}
      <Modal
        open={showFeedbackModal}
        title="不喜欢的原因是什么？"
        footer={null}
        onCancel={() => setShowFeedbackModal(false)}
        className="feedback-modal"
      >
        <Text type="secondary">告诉我，下次帮你调整~</Text>
        <div className="dislike-options">
          {options?.dislike_reason_options.map(opt => (
            <Button
              key={opt.value}
              className="dislike-btn"
              onClick={() => handleSelectDislikeReason(opt.value)}
            >
              {opt.icon} {opt.label}
            </Button>
          ))}
        </div>
      </Modal>
    </div>
  )
}

export default QuickStartPage