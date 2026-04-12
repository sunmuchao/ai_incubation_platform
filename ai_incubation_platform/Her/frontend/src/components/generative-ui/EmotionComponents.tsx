/**
 * 情感分析相关组件
 */
import React from 'react'
import {
  Card,
  Typography,
  Tag,
  Progress,
  Row,
  Col,
  Timeline,
  Divider,
  Empty,
  Alert,
  Space
} from 'antd'
import {
  FireOutlined,
  ThunderboltOutlined,
  HeartOutlined,
  CloudOutlined,
  WarningOutlined
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

/**
 * 情感雷达图
 */
export const EmotionRadar: React.FC<{ emotions: any[]; dominant_emotion?: string; intensity?: number }> = ({
  emotions,
  dominant_emotion,
  intensity
}) => {
  return (
    <Card className="emotion-radar-card" title={<><FireOutlined /> 情感分析</>}>
      <div className="emotion-summary">
        <div className="emotion-dominant">
          <Text strong>主导情绪：</Text>
          <Tag color="red">{dominant_emotion || '未知'}</Tag>
        </div>
        <div className="emotion-intensity">
          <Text strong>强度：</Text>
          <Progress
            percent={Math.round((intensity || 0) * 100)}
            strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
            format={(percent: number) => `${percent}%`}
          />
        </div>
      </div>
      <div className="emotion-chart">
        <Row gutter={[8, 8]}>
          {emotions.map((emotion, i) => (
            <Col span={12} key={i}>
              <div className="emotion-bar">
                <Text>{emotion.name}</Text>
                <Progress
                  percent={Math.round(emotion.value * 100)}
                  strokeColor="#ff6b6b"
                  format={null}
                  size="small"
                />
              </div>
            </Col>
          ))}
        </Row>
      </div>
    </Card>
  )
}

/**
 * 情感空状态
 */
export const EmotionEmpty: React.FC<{ message?: string }> = ({ message }) => {
  return (
    <Card className="emotion-empty-card">
      <Empty
        image={<FireOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        description={message || '暂无情感数据'}
      />
    </Card>
  )
}

/**
 * 爱之语卡片
 */
export const LoveLanguageCard: React.FC<{ profile: any }> = ({ profile }) => {
  return (
    <Card className="love-language-card" title={<><HeartOutlined /> 爱之语画像</>}>
      <div className="love-language-profile">
        <Title level={5}>主要爱之语</Title>
        <Tag color="pink" className="primary-love-language">
          {profile.primary_love_language}
        </Tag>
        <Paragraph type="secondary">{profile.description}</Paragraph>

        <Divider />

        <Title level={5}>五种爱之语得分</Title>
        <Timeline
          items={
            profile.scores?.map((score: any, i: number) => ({
              children: (
                <div className="love-language-score">
                  <Text>{score.name}</Text>
                  <Progress
                    percent={Math.round(score.score * 100)}
                    strokeColor="#ff69b4"
                    format={null}
                    size="small"
                  />
                </div>
              ),
              color: i === 0 ? 'pink' : 'gray'
            })) || []
          }
        />
      </div>
    </Card>
  )
}

/**
 * 爱之语翻译卡片
 */
export const LoveLanguageTranslationCard: React.FC<{
  original_expression?: string
  translated_expression?: string
  love_language_type?: string
  explanation?: string
}> = ({ original_expression, translated_expression, love_language_type, explanation }) => {
  return (
    <Card className="love-language-translation-card">
      <div className="translation-content">
        <div className="translation-original">
          <Text type="secondary">原始表达：</Text>
          <Paragraph>{original_expression}</Paragraph>
        </div>
        <div className="translation-arrow">
          <ThunderboltOutlined style={{ color: '#C88B8B', fontSize: 24 }} />
        </div>
        <div className="translation-translated">
          <Text strong>爱之语表达：</Text>
          <Paragraph className="translated-text">{translated_expression}</Paragraph>
          <Tag color="pink">{love_language_type}</Tag>
        </div>
        {explanation && (
          <div className="translation-explanation">
            <Text type="secondary">解读：</Text>
            <Paragraph type="secondary">{explanation}</Paragraph>
          </div>
        )}
      </div>
    </Card>
  )
}

/**
 * 关系预测空状态
 */
export const PredictionEmpty: React.FC<{ message?: string }> = ({ message }) => {
  return (
    <Card className="prediction-empty-card">
      <Empty
        image={<CloudOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        description={message || '暂无预测数据'}
      />
    </Card>
  )
}

/**
 * 关系天气报告
 */
export const RelationshipWeatherReport: React.FC<{ weather: string; forecast: any }> = ({
  weather,
  forecast
}) => {
  const weatherIcon = {
    sunny: <FireOutlined style={{ fontSize: 48, color: '#faad14' }} />,
    cloudy: <CloudOutlined style={{ fontSize: 48, color: '#8c8c8c' }} />,
    rainy: <ThunderboltOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
    stormy: <WarningOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />
  }

  return (
    <Card className="relationship-weather-card">
      <div className="weather-display">
        <div className="weather-icon">{weatherIcon[weather as keyof typeof weatherIcon]}</div>
        <Title level={3}>关系天气：{weather}</Title>
        <Paragraph type="secondary">{forecast?.description}</Paragraph>
      </div>
      <div className="weather-forecast">
        <Title level={5}>未来趋势</Title>
      </div>
    </Card>
  )
}

/**
 * 沉默状态
 */
export const SilenceStatus: React.FC<{ duration?: number; level?: string }> = ({ duration, level }) => {
  const getColor = (lvl: string) => {
    switch (lvl) {
      case 'minor':
        return 'green'
      case 'moderate':
        return 'orange'
      case 'severe':
      case 'critical':
        return 'red'
      default:
        return 'gray'
    }
  }

  return (
    <Card className="silence-status-card">
      <div className="silence-indicator">
        <div className="silence-info">
          <Title level={4}>沉默检测</Title>
          <Text>已持续 {duration || 0} 秒</Text>
          <Tag color={getColor(level || 'minor')} className="silence-level">
            {level || 'normal'}
          </Tag>
        </div>
      </div>
      {level === 'critical' && (
        <Alert
          message="需要立即破冰！"
          description="沉默时间过长，建议立即发起新话题或互动"
          type="warning"
          showIcon
        />
      )}
    </Card>
  )
}