/**
 * 置信度管理页面
 *
 * 功能：
 * - 显示用户完整置信度分析
 * - 各维度评估详情
 * - 异常标记列表
 * - 验证建议和提升路径
 * - 置信度变化历史
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Progress,
  Tag,
  List,
  Button,
  Tabs,
  Empty,
  Spin,
  Modal,
  Typography,
  Space,
  Tooltip,
  Statistic,
  Row,
  Col,
  Alert,
  Badge,
} from 'antd'
import {
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  StarFilled,
  ReloadOutlined,
  QuestionCircleOutlined,
  InfoCircleOutlined,
  TrophyOutlined,
  RiseOutlined,
  FallOutlined,
  ClockCircleOutlined,
  UserOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import type { AxiosResponse } from 'axios'

import confidenceApi, {
  ConfidenceDetail,
  ConfidenceSummary,
  VerificationRecommendation,
  ConfidenceExplanation,
} from '@/api/confidenceClient'
import './ConfidenceManagementPage.less'

const { Title, Text, Paragraph } = Typography

// ============================================
// 置信度管理页面
// ============================================

interface ConfidenceManagementPageProps {
  onBack?: () => void
}

const ConfidenceManagementPage: React.FC<ConfidenceManagementPageProps> = ({ onBack }) => {
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [detail, setDetail] = useState<ConfidenceDetail | null>(null)
  const [recommendations, setRecommendations] = useState<VerificationRecommendation[]>([])
  const [explainVisible, setExplainVisible] = useState(false)
  const [explainData, setExplainData] = useState<ConfidenceExplanation | null>(null)

  // 加载置信度数据
  const loadConfidenceData = useCallback(async () => {
    setLoading(true)
    try {
      const [detailRes, recRes, explainRes] = await Promise.all([
        confidenceApi.getConfidenceDetail(),
        confidenceApi.getVerificationRecommendations(),
        confidenceApi.getConfidenceExplanation(),
      ])

      setDetail(detailRes)
      setRecommendations(recRes.recommendations || [])
      setExplainData(explainRes)
    } catch (error) {
      console.error('Failed to load confidence data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadConfidenceData()
  }, [loadConfidenceData])

  // 刷新置信度评估
  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const refreshResult = await confidenceApi.refreshConfidence(true)
      if (refreshResult.success) {
        await loadConfidenceData()
      }
    } catch (error) {
      console.error('Refresh failed:', error)
    } finally {
      setRefreshing(false)
    }
  }

  // 加载中状态
  if (loading) {
    return (
      <div className="confidence-management-page loading-state">
        <Spin size="large" tip="正在加载置信度数据...">
          <div style={{ padding: 50 }} />
        </Spin>
      </div>
    )
  }

  // 无数据状态
  if (!detail) {
    return (
      <div className="confidence-management-page">
        <Empty description="暂无置信度数据" />
        <Button type="primary" onClick={loadConfidenceData}>
          开始评估
        </Button>
      </div>
    )
  }

  // 获取等级配置
  const getLevelConfig = (level: string): { color: string; icon: string; name: string; bgColor: string } => {
    const configs: Record<string, { color: string; icon: string; name: string; bgColor: string }> = {
      very_high: { color: '#faad14', icon: '💎', name: '极可信', bgColor: '#fff7e6' },
      high: { color: '#52c41a', icon: '🌟', name: '较可信', bgColor: '#f6ffed' },
      medium: { color: '#1890ff', icon: '✓', name: '普通用户', bgColor: '#e6f7ff' },
      low: { color: '#fa8c16', icon: '⚠️', name: '需谨慎', bgColor: '#fffbe6' },
    }
    return configs[level] || configs.medium
  }

  const levelConfig = getLevelConfig(detail.confidence_level)

  // 维度名称映射
  const dimensionNames: Record<string, string> = {
    identity: '身份验证',
    cross_validation: '信息一致性',
    behavior: '行为一致性',
    social: '社交背书',
    time: '时间积累',
  }

  // 异常标记名称映射
  const flagNames: Record<string, string> = {
    age_education_mismatch: '年龄与学历不匹配',
    occupation_income_mismatch: '职业与收入不匹配',
    location_activity_mismatch: '地理与活跃时间异常',
    interest_browse_mismatch: '兴趣与浏览行为不一致',
    age_self_declared_mismatch: '年龄与语言风格不一致',
    photo_personality_mismatch: '照片与性格风格不一致',
    user_reported_fake_info: '用户举报虚假信息',
    llm_detected: 'AI分析发现异常',
  }

  // 建议名称映射
  const recommendationNames: Record<string, string> = {
    identity_verify: '完成实名认证',
    face_verify: '人脸核身认证',
    education_verify: '学历认证',
    occupation_verify: '职业认证',
    income_verify: '收入认证',
    profile_complete: '完善个人资料',
    behavior_confirm: '通过行为确认兴趣',
  }

  return (
    <div className="confidence-management-page">
      {/* 返回按钮 */}
      {onBack && (
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={onBack}
          className="back-button"
          style={{ marginBottom: 16 }}
        >
          返回
        </Button>
      )}

      {/* 总置信度卡片 */}
      <Card className="overall-card" variant="borderless">
        <Row gutter={[24, 24]} align="middle">
          <Col flex="auto">
            <Space direction="vertical" size="small">
              <Title level={3} style={{ marginBottom: 0 }}>
                我的可信度
              </Title>
              <Space size="middle">
                <Badge
                  count={
                    <span className="level-badge" style={{ backgroundColor: levelConfig.bgColor, color: levelConfig.color }}>
                      {levelConfig.icon} {levelConfig.name}
                    </span>
                  }
                />
                <Text type="secondary">
                  {Math.round(detail.overall_confidence * 100)}%
                </Text>
              </Space>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              loading={refreshing}
              onClick={handleRefresh}
            >
              重新评估
            </Button>
          </Col>
        </Row>

        <Progress
          percent={Math.round(detail.overall_confidence * 100)}
          strokeColor={{
            '0%': levelConfig.color,
            '100%': levelConfig.color,
          }}
          trailColor="#f0f0f0"
          strokeWidth={12}
          format={(percent) => (
            <Space>
              <span className="progress-icon">{levelConfig.icon}</span>
              <span>{percent}%</span>
            </Space>
          )}
          className="overall-progress"
        />

        {/* 异常标记提示 */}
        {Object.keys(detail.cross_validation_flags).length > 0 && (
          <Alert
            type="warning"
            showIcon
            icon={<WarningOutlined />}
            message={`发现 ${Object.keys(detail.cross_validation_flags).length} 项信息异常标记`}
            description="建议查看详情并完成相关验证以消除异常"
            className="flags-alert"
          />
        )}
      </Card>

      {/* 各维度评估 */}
      <Card title="各维度评估" className="dimensions-card">
        <Row gutter={[16, 16]}>
          {Object.entries(detail.dimensions).map(([key, value]) => {
            const dimLevelConfig = getLevelConfig(
              value >= 0.8 ? 'very_high' :
              value >= 0.6 ? 'high' :
              value >= 0.4 ? 'medium' : 'low'
            )

            return (
              <Col xs={24} sm={12} md={8} key={key}>
                <Card
                  size="small"
                  className={`dimension-item dimension-${key}`}
                  variant="borderless"
                >
                  <Statistic
                    title={dimensionNames[key]}
                    value={Math.round(value * 100)}
                    suffix="%"
                    valueStyle={{ color: dimLevelConfig.color }}
                    prefix={<span className="dim-icon">{dimLevelConfig.icon}</span>}
                  />
                  <Progress
                    percent={Math.round(value * 100)}
                    strokeColor={dimLevelConfig.color}
                    trailColor="#f0f0f0"
                    size="small"
                    showInfo={false}
                  />
                </Card>
              </Col>
            )
          })}
        </Row>
      </Card>

      {/* 异常标记详情 */}
      <Card
        title={
          <Space>
            <span>信息一致性检查</span>
            {Object.keys(detail.cross_validation_flags).length > 0 && (
              <Tag color="warning">
                {Object.keys(detail.cross_validation_flags).length} 项异常
              </Tag>
            )}
          </Space>
        }
        className="flags-card"
      >
        {Object.keys(detail.cross_validation_flags).length === 0 ? (
          <div className="flags-empty">
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />
            <Text type="secondary">无异常标记，信息一致性良好</Text>
          </div>
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={Object.entries(detail.cross_validation_flags)}
            renderItem={(item) => {
              const [key, flag] = item
              const severityColors: Record<string, string> = {
                high: '#ff4d4f',
                medium: '#faad14',
                low: '#fa8c16',
              }
              const severityIcons: Record<string, string> = {
                high: '🔴',
                medium: '🟡',
                low: '🟢',
              }

              return (
                <List.Item className={`flag-item flag-${flag.severity}`}>
                  <List.Item.Meta
                    avatar={
                      <span className="flag-icon">
                        {severityIcons[flag.severity]}
                      </span>
                    }
                    title={
                      <Space>
                        <span>{flagNames[key] || key}</span>
                        <Tag color={severityColors[flag.severity]}>
                          {flag.severity === 'high' ? '高异常' :
                           flag.severity === 'medium' ? '中异常' : '低异常'}
                        </Tag>
                      </Space>
                    }
                    description={flag.detail}
                  />
                </List.Item>
              )
            }}
          />
        )}
      </Card>

      {/* 验证建议 */}
      <Card title="提升建议" className="recommendations-card">
        {recommendations.length === 0 ? (
          <div className="recommendations-empty">
            <TrophyOutlined style={{ color: '#52c41a', fontSize: 24 }} />
            <Text type="secondary">置信度已达较高水平，继续保持！</Text>
          </div>
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={recommendations}
            renderItem={(rec) => {
              const priorityColors: Record<'high' | 'medium' | 'low', string> = {
                high: '#ff4d4f',
                medium: '#faad14',
                low: '#52c41a',
              }
              const priorityIcons: Record<'high' | 'medium' | 'low', string> = {
                high: '🔴',
                medium: '🟡',
                low: '🟢',
              }

              return (
                <List.Item className={`recommendation-item rec-${rec.priority}`}>
                  <List.Item.Meta
                    avatar={
                      <span className="rec-icon">
                        {priorityIcons[rec.priority]}
                      </span>
                    }
                    title={
                      <Space>
                        <span>{recommendationNames[rec.type] || rec.type}</span>
                        <Tag color={priorityColors[rec.priority]}>
                          {rec.priority === 'high' ? '优先' :
                           rec.priority === 'medium' ? '建议' : '可选'}
                        </Tag>
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size="small">
                        <Text>{rec.reason}</Text>
                        <Space>
                          <StarFilled style={{ color: '#faad14', fontSize: 12 }} />
                          <Text type="success">
                            预估提升 +{Math.round(rec.estimated_confidence_boost * 100)}%
                          </Text>
                        </Space>
                      </Space>
                    }
                  />
                  <Button size="small" type="primary">
                    立即完成
                  </Button>
                </List.Item>
              )
            }}
          />
        )}
      </Card>

      {/* 系统解释 */}
      <Card className="explain-card" variant="borderless">
        <Button
          type="link"
          icon={<QuestionCircleOutlined />}
          onClick={() => setExplainVisible(true)}
          block
        >
          置信度系统是如何工作的？
        </Button>
      </Card>

      {/* 系统解释弹窗 */}
      <ExplainSystemModal
        visible={explainVisible}
        onClose={() => setExplainVisible(false)}
        data={explainData}
      />

      {/* 上次评估时间 */}
      {detail.last_evaluated_at && (
        <Text type="secondary" className="last-evaluated">
          <ClockCircleOutlined style={{ marginRight: 4 }} />
          上次评估时间：{new Date(detail.last_evaluated_at).toLocaleString()}
        </Text>
      )}
    </div>
  )
}

// ============================================
// 系统解释弹窗
// ============================================

const ExplainSystemModal: React.FC<{
  visible: boolean
  onClose: () => void
  data: ConfidenceExplanation | null
}> = ({ visible, onClose, data }) => {
  if (!data || !data.explanation) {
    return null
  }

  const { explanation } = data

  return (
    <Modal
      title={
        <Space>
          <SafetyCertificateOutlined />
          <span>置信度系统说明</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={600}
      className="explain-modal"
    >
      <Paragraph>{explanation.description}</Paragraph>

      <Title level={5}>评估维度</Title>
      <List
        dataSource={explanation.dimensions}
        renderItem={(dim) => (
          <List.Item>
            <List.Item.Meta
              title={`${dim.name}（权重 ${dim.weight}）`}
              description={dim.description}
            />
            <Text type="secondary">{dim.how_to_improve}</Text>
          </List.Item>
        )}
      />

      <Title level={5}>置信度等级</Title>
      <Row gutter={[16, 16]}>
        {explanation.levels.map((level) => (
          <Col span={6} key={level.name}>
            <Tag
              color={level.color}
              style={{ width: '100%', textAlign: 'center', padding: '8px 0' }}
            >
              {level.name}
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {level.range}
              </Text>
            </Tag>
          </Col>
        ))}
      </Row>

      <Alert
        type="info"
        showIcon
        message={explanation.privacy_note}
        className="privacy-note"
      />
    </Modal>
  )
}

export default ConfidenceManagementPage