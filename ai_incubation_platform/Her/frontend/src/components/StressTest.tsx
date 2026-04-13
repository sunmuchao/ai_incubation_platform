/**
 * 关系压力测试组件
 *
 * 模拟场景测试关系韧性：
 * - 价值观冲突
 * - 生活习惯差异
 * - 经济观念差异
 * - 家庭关系
 * - 沟通方式差异
 */

import React, { useState, useEffect } from 'react'
import {
  Modal, Button, Space, Typography, Card, Radio, Progress, Tag,
  Divider, message, Spin, List, Avatar, Result
} from 'antd'
import {
  ExperimentOutlined, WarningOutlined, CheckCircleOutlined,
  HeartOutlined, HomeOutlined, DollarOutlined, CommentOutlined,
  ArrowRightOutlined, ReloadOutlined
} from '@ant-design/icons'
import { deerflowClient } from '../api/deerflowClient'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'

// 场景类型配置
const SCENARIO_TYPES = [
  {
    type: 'value_conflict',
    name: '价值观冲突',
    icon: <HeartOutlined style={{ color: '#eb2f96' }} />,
    description: '价值观差异引发的情况',
    color: 'pink'
  },
  {
    type: 'lifestyle_difference',
    name: '生活习惯差异',
    icon: <HomeOutlined style={{ color: '#1890ff' }} />,
    description: '生活习惯不同引发的情况',
    color: 'blue'
  },
  {
    type: 'economic_disagreement',
    name: '经济观念差异',
    icon: <DollarOutlined style={{ color: '#fa8c16' }} />,
    description: '金钱观念不同引发的情况',
    color: 'orange'
  },
  {
    type: 'family_relation',
    name: '家庭关系',
    icon: <ExperimentOutlined style={{ color: '#722ed1' }} />,
    description: '家庭因素引发的情况',
    color: 'purple'
  },
  {
    type: 'communication_style',
    name: '沟通方式差异',
    icon: <CommentOutlined style={{ color: '#52c41a' }} />,
    description: '沟通方式不同引发的情况',
    color: 'green'
  },
]

interface Question {
  question_id: string
  scenario_description: string
  options: Array<{ id: string; content: string; consequence: string }>
  difficulty: number
  key_insight: string
}

interface StressTestProps {
  visible: boolean
  userId: string
  partnerId: string
  onClose: () => void
  onComplete?: (summary: any) => void
}

/**
 * 关系压力测试弹窗
 */
const StressTest: React.FC<StressTestProps> = ({
  visible,
  userId,
  partnerId,
  onClose,
  onComplete
}) => {
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [testId, setTestId] = useState<string | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState<any[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [analysis, setAnalysis] = useState<any>(null)
  const [summary, setSummary] = useState<any>(null)

  // 重置测试状态
  useEffect(() => {
    if (!visible) {
      setSelectedScenario(null)
      setTestId(null)
      setQuestions([])
      setCurrentQuestionIndex(0)
      setAnswers([])
      setAnalysis(null)
      setSummary(null)
    }
  }, [visible])

  // 创建测试
  const handleCreateTest = async () => {
    if (!selectedScenario) {
      message.warning('请先选择场景类型')
      return
    }

    setCreating(true)
    try {
      // 使用 DeerFlow Agent 替代已删除的 REST API
      const result = await deerflowClient.chat(
        `帮我创建一个关系压力测试，场景类型：${selectedScenario}`,
        `her-stress-test-${userId}`
      )

      if (result.success) {
        const testData = result.tool_result?.data || {}
        setTestId(testData.test_id || `test-${Date.now()}`)
        setQuestions(testData.questions || [{
          question_id: 'q1',
          scenario_description: '假设你们在周末安排上有分歧，你想去户外运动，对方想在家休息，你会怎么做？',
          options: [
            { id: 'a1', content: '尊重对方意愿，在家休息', consequence: '体现理解和包容' },
            { id: 'a2', content: '邀请对方一起户外运动', consequence: '积极引导尝试新体验' },
            { id: 'a3', content: '各自做自己喜欢的事', consequence: '保持独立空间' },
          ],
          difficulty: 1,
          key_insight: '生活方式差异的处理'
        }])
        setCurrentQuestionIndex(0)
        message.success('测试已创建')
      } else {
        message.error(result.ai_message || '创建失败')
      }
    } catch (error) {
      message.error('创建失败')
    } finally {
      setCreating(false)
    }
  }

  // 提交答案
  const handleSubmitAnswer = async (optionId: string) => {
    if (!testId) return

    const currentQuestion = questions[currentQuestionIndex]
    setSubmitting(true)

    try {
      // 使用 DeerFlow Agent 替代已删除的 REST API
      const result = await deerflowClient.chat(
        `分析我的回答：${currentQuestion.options.find(o => o.id === optionId)?.content}，并给出建议`,
        `her-stress-test-${userId}`
      )

      if (result.success) {
        const analysisData = result.tool_result?.data?.analysis || result.ai_message
        setAnalysis(analysisData)
        setAnswers(prev => [...prev, {
          question_id: currentQuestion.question_id,
          selected_option: optionId,
          analysis: analysisData
        }])

        // 下一题或完成
        if (currentQuestionIndex < questions.length - 1) {
          setCurrentQuestionIndex(prev => prev + 1)
          setAnalysis(null)
        } else {
          // 完成测试，获取总结
          await loadSummary()
        }
      }
    } catch (error) {
      message.error('提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  // 获取总结
  const loadSummary = async () => {
    if (!testId) return

    try {
      // 使用 DeerFlow Agent 替代已删除的 REST API
      const result = await deerflowClient.chat(
        `总结我的关系压力测试结果，给出改善建议`,
        `her-stress-test-${userId}`
      )

      if (result.success) {
        const summaryData = result.tool_result?.data?.summary || { overall_score: 75, insights: [result.ai_message] }
        setSummary(summaryData)
        if (onComplete) {
          onComplete(summaryData)
        }
      }
    } catch (error) {
      message.error('获取总结失败')
    }
  }

  // 渲染场景选择
  const renderScenarioSelection = () => {
    return (
      <div>
        <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
          选择你想测试的场景类型
        </Text>

        <List
          dataSource={SCENARIO_TYPES}
          renderItem={(scenario) => (
            <Card
              size="small"
              style={{
                marginBottom: 8,
                borderRadius: 12,
                cursor: 'pointer',
                border: selectedScenario === scenario.type ? `2px solid ${PRIMARY_COLOR}` : '1px solid #f0f0f0',
              }}
              onClick={() => setSelectedScenario(scenario.type)}
            >
              <Space>
                {scenario.icon}
                <Text strong>{scenario.name}</Text>
                <Tag color={scenario.color} style={{ fontSize: 10 }}>
                  {scenario.description}
                </Tag>
              </Space>
            </Card>
          )}
        />

        <Button
          type="primary"
          block
          icon={<ExperimentOutlined />}
          loading={creating}
          onClick={handleCreateTest}
          style={{
            marginTop: 16,
            background: PRIMARY_COLOR,
            borderColor: PRIMARY_COLOR,
            borderRadius: 12
          }}
        >
          开始测试
        </Button>
      </div>
    )
  }

  // 渲染问题
  const renderQuestion = () => {
    if (questions.length === 0) {
      return <Spin size="large" tip="加载问题..." />
    }

    const currentQuestion = questions[currentQuestionIndex]

    return (
      <div>
        {/* 进度 */}
        <div style={{ marginBottom: 16 }}>
          <Progress
            percent={(currentQuestionIndex + 1) / questions.length * 100}
            strokeColor={PRIMARY_COLOR}
            showInfo={false}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            问题 {currentQuestionIndex + 1} / {questions.length}
          </Text>
          <Tag style={{ marginLeft: 8 }}>
            难度：{currentQuestion.difficulty}
          </Tag>
        </div>

        {/* 场景描述 */}
        <Card
          size="small"
          style={{
            marginBottom: 16,
            borderRadius: 12,
            background: 'rgba(200, 139, 139, 0.08)'
          }}
        >
          <Paragraph style={{ fontSize: 15, margin: 0 }}>
            {currentQuestion.scenario_description}
          </Paragraph>
        </Card>

        {/* 选项 */}
        <Radio.Group
          style={{ width: '100%' }}
          disabled={submitting}
        >
          <List
            dataSource={currentQuestion.options}
            renderItem={(option) => (
              <Card
                size="small"
                style={{
                  marginBottom: 8,
                  borderRadius: 12,
                  cursor: submitting ? 'not-allowed' : 'pointer',
                }}
                onClick={() => !submitting && handleSubmitAnswer(option.id)}
              >
                <Radio value={option.id} style={{ width: '100%' }}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Text>{option.content}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      潜在后果：{option.consequence}
                    </Text>
                  </Space>
                </Radio>
              </Card>
            )}
          />
        </Radio.Group>

        {/* 分析结果 */}
        {analysis && (
          <Card
            size="small"
            style={{
              marginTop: 16,
              borderRadius: 12,
              background: 'rgba(255, 215, 0, 0.1)'
            }}
          >
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text strong style={{ color: '#FFD700' }}>
                AI 分析
              </Text>
              <Text>{analysis.attitude_analysis}</Text>
              <Text type="secondary">建议：{analysis.communication_advice}</Text>
              <Tag color={analysis.resilience_score >= 70 ? 'green' : analysis.resilience_score >= 50 ? 'orange' : 'red'}>
                韧性评分：{analysis.resilience_score}
              </Tag>
            </Space>
          </Card>
        )}

        {/* 关键洞察 */}
        <div style={{ marginTop: 16, textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            💡 {currentQuestion.key_insight}
          </Text>
        </div>
      </div>
    )
  }

  // 渲染总结
  const renderSummary = () => {
    if (!summary) return <Spin size="large" tip="生成总结..." />

    const scoreColor = summary.average_resilience_score >= 80 ? '#52c41a'
      : summary.average_resilience_score >= 60 ? '#faad14'
      : '#ff4d4f'

    return (
      <div>
        {/* 总体评分 */}
        <Result
          icon={<CheckCircleOutlined style={{ color: scoreColor }} />}
          title={<span style={{ color: scoreColor }}>测试完成</span>}
          subTitle={`平均韧性评分：${Math.round(summary.average_resilience_score)}`}
          extra={[
            <Tag key="risk" color={scoreColor}>
              {summary.overall_risk_level}
            </Tag>,
          ]}
        />

        {/* 详细发现 */}
        <Card
          size="small"
          style={{ borderRadius: 12, marginBottom: 16 }}
        >
          <Text strong style={{ marginBottom: 8, display: 'block' }}>
            关键发现
          </Text>
          <List
            size="small"
            dataSource={summary.key_findings.slice(0, 5)}
            renderItem={(finding) => (
              <List.Item>
                <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
                <Text>{finding}</Text>
              </List.Item>
            )}
          />
        </Card>

        {/* 建议 */}
        <Card
          size="small"
          style={{ borderRadius: 12 }}
        >
          <Text strong style={{ marginBottom: 8, display: 'block' }}>
            改进建议
          </Text>
          <List
            size="small"
            dataSource={summary.recommendations.slice(0, 5)}
            renderItem={(rec) => (
              <List.Item>
                <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                <Text>{rec}</Text>
              </List.Item>
            )}
          />
        </Card>

        <Button
          type="primary"
          block
          icon={<ReloadOutlined />}
          onClick={() => {
            setSelectedScenario(null)
            setTestId(null)
            setQuestions([])
            setSummary(null)
          }}
          style={{
            marginTop: 16,
            background: PRIMARY_COLOR,
            borderColor: PRIMARY_COLOR,
            borderRadius: 12
          }}
        >
          重新测试
        </Button>
      </div>
    )
  }

  // 确定当前渲染内容
  const renderContent = () => {
    if (summary) {
      return renderSummary()
    }

    if (questions.length > 0) {
      return renderQuestion()
    }

    return renderScenarioSelection()
  }

  return (
    <Modal
      title={
        <Space>
          <ExperimentOutlined style={{ color: PRIMARY_COLOR }} />
          <span>关系压力测试</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={summary ? [
        <Button key="close" type="primary" onClick={onClose}>
          完成
        </Button>,
      ] : [
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={500}
      styles={{ body: { padding: 16 } }}
    >
      {renderContent()}
    </Modal>
  )
}

/**
 * 压力测试按钮
 */
export const StressTestButton: React.FC<{
  userId: string
  partnerId: string
  onComplete?: (summary: any) => void
}> = ({
  userId,
  partnerId,
  onComplete
}) => {
  const [modalVisible, setModalVisible] = useState(false)

  return (
    <>
      <Button
        type="text"
        icon={<ExperimentOutlined style={{ color: PRIMARY_COLOR }} />}
        onClick={() => setModalVisible(true)}
        title="关系压力测试"
      />
      <StressTest
        visible={modalVisible}
        userId={userId}
        partnerId={partnerId}
        onClose={() => setModalVisible(false)}
        onComplete={onComplete}
      />
    </>
  )
}

export default StressTest