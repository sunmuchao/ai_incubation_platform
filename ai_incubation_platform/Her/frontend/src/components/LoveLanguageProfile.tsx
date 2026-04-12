/**
 * P13 爱之语画像组件 - AI Native Generative UI
 */

import React, { useState, useEffect } from 'react'
import { Card, Progress, Tag, Space, Typography, Spin, Empty, Button, Row, Col, Tooltip } from 'antd'
import {
  HeartOutlined,
  ClockCircleOutlined,
  GiftOutlined,
  ToolOutlined,
  UserAddOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  MessageOutlined,
} from '@ant-design/icons'
import type {
  LoveLanguageProfile,
  LoveLanguageType,
  LoveLanguageDescription,
} from '../types/loveLanguageTypes'
import { loveLanguageProfileApi } from '../api/loveLanguageProfileApi'
import './LoveLanguageProfile.less'

const { Text, Paragraph, Title } = Typography

const LOVE_LANGUAGE_ICONS: Record<LoveLanguageType, JSX.Element> = {
  words_of_affirmation: <MessageOutlined />,
  quality_time: <ClockCircleOutlined />,
  receiving_gifts: <GiftOutlined />,
  acts_of_service: <ToolOutlined />,
  physical_touch: <UserAddOutlined />,
}

const LOVE_LANGUAGE_NAMES: Record<LoveLanguageType, string> = {
  words_of_affirmation: '肯定的言辞',
  quality_time: '精心时刻',
  receiving_gifts: '接受礼物',
  acts_of_service: '服务的行动',
  physical_touch: '身体的接触',
}

const LOVE_LANGUAGE_COLORS: Record<LoveLanguageType, string> = {
  words_of_affirmation: '#1890ff',
  quality_time: '#52c41a',
  receiving_gifts: '#faad14',
  acts_of_service: '#722ed1',
  physical_touch: '#eb2f96',
}

interface LoveLanguageProfileCardProps {
  userId: string
  onProfileLoaded?: (profile: LoveLanguageProfile) => void
}

const LoveLanguageProfileCard: React.FC<LoveLanguageProfileCardProps> = ({
  userId,
  onProfileLoaded,
}) => {
  const [loading, setLoading] = useState(false)
  const [profile, setProfile] = useState<LoveLanguageProfile | null>(null)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    loadProfile()
  }, [userId])

  const loadProfile = async () => {
    setLoading(true)
    try {
      const result = await loveLanguageProfileApi.getUserLoveLanguageProfile(userId)
      if (result.profile) {
        setProfile(result.profile)
        onProfileLoaded?.(result.profile)
      }
    } catch (error) {
      console.error('Failed to load love language profile:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const result = await loveLanguageProfileApi.analyzeUserLoveLanguage(userId)
      setProfile(result.profile)
      onProfileLoaded?.(result.profile)
    } catch (error) {
      console.error('Failed to analyze love language:', error)
    } finally {
      setAnalyzing(false)
    }
  }

  if (loading) {
    return (
      <div className="love-language-loading">
        <Spin size="large" tip="加载爱之语画像..." />
      </div>
    )
  }

  if (!profile) {
    return (
      <Card className="love-language-profile-card">
        <Empty
          description="暂无爱之语画像"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
        <div className="analyze-action">
          <Button
            type="primary"
            size="large"
            icon={<ThunderboltOutlined />}
            onClick={handleAnalyze}
            loading={analyzing}
          >
            AI 分析我的爱之语
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="love-language-profile-card">
      <div className="profile-header">
        <Title level={4} style={{ margin: 0 }}>
          <HeartOutlined style={{ color: '#eb2f96', marginRight: 8 }} />
          爱之语画像
        </Title>
        <Tag color="purple">主要：{LOVE_LANGUAGE_NAMES[profile.primary_love_language]}</Tag>
      </div>

      <div className="profile-content">
        {/* 爱之语分数雷达 */}
        <div className="language-scores">
          <Title level={5}>爱之语分数</Title>
          {Object.entries(profile.language_scores).map(([language, score]) => {
            const type = language as LoveLanguageType
            const isPrimary = type === profile.primary_love_language
            return (
              <div key={language} className={`language-score-item ${isPrimary ? 'primary' : ''}`}>
                <div className="language-label">
                  <span className="language-icon" style={{ color: LOVE_LANGUAGE_COLORS[type] }}>
                    {LOVE_LANGUAGE_ICONS[type]}
                  </span>
                  <Text strong>{LOVE_LANGUAGE_NAMES[type]}</Text>
                  {isPrimary && (
                    <Tag color="purple" size="small">主要</Tag>
                  )}
                </div>
                <Progress
                  percent={Math.round(score * 100)}
                  strokeColor={LOVE_LANGUAGE_COLORS[type]}
                  size="small"
                  format={(percent) => `${percent}%`}
                />
              </div>
            )
          })}
        </div>

        {/* AI 分析 */}
        <div className="ai-analysis-section">
          <Title level={5}>
            <InfoCircleOutlined /> AI 分析
          </Title>
          <Card className="ai-analysis-content" size="small">
            <Paragraph>{profile.ai_analysis}</Paragraph>
          </Card>
        </div>

        {/* 爱之语说明 */}
        <LoveLanguageDescriptionCard languageType={profile.primary_love_language} />
      </div>
    </Card>
  )
}

// 爱之语说明卡片
interface LoveLanguageDescriptionCardProps {
  languageType: LoveLanguageType
}

const LoveLanguageDescriptionCard: React.FC<LoveLanguageDescriptionCardProps> = ({
  languageType,
}) => {
  const [description, setDescription] = useState<LoveLanguageDescription | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadDescription()
  }, [languageType])

  const loadDescription = async () => {
    setLoading(true)
    try {
      const result = await loveLanguageProfileApi.getLoveLanguageDescription(languageType)
      setDescription(result.description)
    } catch (error) {
      console.error('Failed to load love language description:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <Spin tip="加载中..." />
  }

  if (!description) {
    return null
  }

  return (
    <Card className="love-language-description" size="small">
      <Title level={5}>{description.name}</Title>
      <Paragraph className="description-text">{description.description}</Paragraph>

      <div className="characteristics">
        <Text strong>特征：</Text>
        <Space wrap>
          {description.characteristics.map((char, index) => (
            <Tag key={index} color="blue">{char}</Tag>
          ))}
        </Space>
      </div>

      <div className="tips">
        <Text strong>相处建议：</Text>
        <ul>
          {description.tips.map((tip, index) => (
            <li key={index}>{tip}</li>
          ))}
        </ul>
      </div>
    </Card>
  )
}

export default LoveLanguageProfileCard
