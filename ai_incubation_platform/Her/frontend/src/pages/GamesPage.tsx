/**
 * P10 双人互动游戏页面
 * 功能：
 * 1. 创建双人游戏
 * 2. 参与游戏
 * 3. 查看游戏结果和洞察
 */

import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Space,
  Typography,
  Spin,
  Empty,
  Row,
  Col,
  Tag,
  Modal,
  Form,
  Select,
  Progress,
  Statistic,
  Divider,
  message,
  Timeline,
  Avatar,
} from 'antd'
import {
  ExperimentOutlined,
  PlayCircleOutlined,
  TrophyOutlined,
  TeamOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import type { CoupleGame, GameType } from '../types/p10_types'
import { coupleGameApi } from '../api/p10_api'
import AgentFloatingBall from '../components/AgentFloatingBall'
import { authStorage } from '../utils/storage'
import './GamesPage.less'

const { Text, Title } = Typography

const GAME_TYPES: { value: GameType; label: string; description: string; icon: string }[] = [
  { value: 'qna_mutual', label: '互相问答', description: '轮流提问回答问题，了解彼此的内心世界', icon: '💬' },
  { value: 'values_quiz', label: '价值观测试', description: '通过极端场景测试，了解双方的价值观是否契合', icon: '⚖️' },
  { value: 'preference_match', label: '偏好匹配', description: '猜测对方的喜好，测试你们的默契程度', icon: '🎯' },
  { value: 'personality_quiz', label: '性格测试', description: '通过情景选择题，了解双方的性格特点', icon: '🧩' },
  { value: 'love_language', label: '爱之语测试', description: '发现你们表达和接收爱的方式', icon: '💝' },
]

const GAMES_PAGE_STYLES = {
  container: {
    padding: '24px',
    minHeight: '100%',
    background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: '32px',
    color: '#fff',
  },
  card: {
    marginBottom: '16px',
    borderRadius: '12px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
  },
  gameTypeCard: {
    textAlign: 'center' as const,
    padding: '20px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    border: '2px solid transparent',
  },
  gameTypeCardSelected: {
    borderColor: '#11998e',
    background: '#f0f9f7',
  },
  gameIcon: {
    fontSize: '48px',
    marginBottom: '12px',
  },
}

interface GamesPageProps {
  userId?: string
}

const GamesPage: React.FC<GamesPageProps> = ({ userId }) => {
  const [loading, setLoading] = useState(false)
  const [games, setGames] = useState<CoupleGame[]>([])
  const [modalVisible, setModalVisible] = useState(false)
  const [selectedGameType, setSelectedGameType] = useState<GameType | null>(null)
  const [createForm] = Form.useForm()
  const [unreadCount, setUnreadCount] = useState(0)
  const [hasNewMessage, setHasNewMessage] = useState(false)

  const currentUserId = userId || authStorage.getUserId()

  useEffect(() => {
    loadGames()
  }, [])

  const loadGames = async () => {
    setLoading(true)
    try {
      const result = await coupleGameApi.getUserGames(currentUserId, undefined, 10)
      setGames(result.games || [])
    } catch (error) {
      console.error('Failed to load games:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateGame = async (values: any) => {
    if (!selectedGameType) {
      message.error('请选择游戏类型')
      return
    }

    try {
      setLoading(true)
      const result = await coupleGameApi.createCoupleGame(
        currentUserId,
        values.partner_id,
        selectedGameType,
        {
          difficulty: values.difficulty || 'normal',
          question_count: values.question_count || 10,
        },
        values.difficulty || 'normal'
      )
      message.success('游戏创建成功！邀请对方一起玩吧～')
      setModalVisible(false)
      createForm.resetFields()
      if (result.game) {
        setGames([result.game, ...games])
      }
    } catch (error) {
      console.error('Failed to create game:', error)
      message.error('创建游戏失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleStartGame = async (gameId: string) => {
    try {
      setLoading(true)
      await coupleGameApi.startGame(gameId, currentUserId)
      message.success('游戏已开始！')
      loadGames()
    } catch (error) {
      console.error('Failed to start game:', error)
      message.error('开始游戏失败')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'orange',
      in_progress: 'blue',
      completed: 'green',
    }
    return colorMap[status] || 'default'
  }

  const getStatusText = (status: string) => {
    const textMap: Record<string, string> = {
      pending: '等待开始',
      in_progress: '进行中',
      completed: '已完成',
    }
    return textMap[status] || status
  }

  const renderGameCard = (game: CoupleGame) => (
    <Card
      key={game.id}
      style={GAMES_PAGE_STYLES.card}
      title={
        <Space>
          <span style={{ fontSize: '24px' }}>
            {GAME_TYPES.find((t) => t.value === game.game_type)?.icon || '🎮'}
          </span>
          <span>{GAME_TYPES.find((t) => t.value === game.game_type)?.label || game.game_type}</span>
        </Space>
      }
      extra={<Tag color={getStatusColor(game.status)}>{getStatusText(game.status)}</Tag>}
      actions={[
        game.status === 'pending' && (
          <Button
            key="start"
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => handleStartGame(game.id)}
          >
            开始游戏
          </Button>
        ),
        game.status === 'in_progress' && (
          <Button
            key="continue"
            type="primary"
            icon={<PlayCircleOutlined />}
          >
            继续游戏
          </Button>
        ),
        game.status === 'completed' && (
          <Button
            key="result"
            icon={<TrophyOutlined />}
          >
            查看结果
          </Button>
        ),
      ].filter(Boolean)}
    >
      <Row gutter={16}>
        <Col span={12}>
          <Statistic
            title="当前轮次"
            value={game.current_round}
            suffix={`/ ${game.total_rounds}`}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title="难度"
            value={game.game_config?.difficulty || 'normal'}
          />
        </Col>
      </Row>

      {game.status === 'completed' && game.insights && (
        <>
          <Divider />
          <div>
            <Text strong>兼容性评分：</Text>
            <Progress
              percent={(game.insights.compatibility_score || 0) * 100}
              strokeColor="#52c41a"
            />
          </div>
          {game.insights.ai_summary && (
            <Paragraph ellipsis={{ rows: 2 }}>{game.insights.ai_summary}</Paragraph>
          )}
        </>
      )}
    </Card>
  )

  return (
    <div style={GAMES_PAGE_STYLES.container}>
      <div style={GAMES_PAGE_STYLES.header}>
        <Title style={{ color: '#fff', marginBottom: 8 }}>
          <ExperimentOutlined /> 双人互动游戏
        </Title>
        <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
          在轻松的氛围中加深了解
        </Text>
      </div>

      <div style={{ marginBottom: '24px', textAlign: 'center' }}>
        <Button
          type="primary"
          size="large"
          icon={<PlusOutlined />}
          onClick={() => setModalVisible(true)}
          style={{ background: '#fff', color: '#11998e', border: 'none' }}
        >
          创建新游戏
        </Button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px' }}>
          <Spin size="large" tip="加载游戏..." />
        </div>
      ) : games.length > 0 ? (
        <Row gutter={16}>
          {games.map((game) => (
            <Col xs={24} md={12} lg={8} key={game.id}>
              {renderGameCard(game)}
            </Col>
          ))}
        </Row>
      ) : (
        <Empty
          description="暂无游戏记录"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" onClick={() => setModalVisible(true)}>
            创建第一个游戏
          </Button>
        </Empty>
      )}

      {/* 创建游戏弹窗 */}
      <Modal
        title="创建双人互动游戏"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={700}
      >
        <div style={{ marginBottom: '24px' }}>
          <Title level={5}>选择游戏类型</Title>
          <Row gutter={16}>
            {GAME_TYPES.map((type) => (
              <Col xs={24} sm={12} md={8} key={type.value}>
                <Card
                  size="small"
                  style={{
                    ...GAMES_PAGE_STYLES.gameTypeCard,
                    ...(selectedGameType === type.value ? GAMES_PAGE_STYLES.gameTypeCardSelected : {}),
                  }}
                  onClick={() => setSelectedGameType(type.value)}
                >
                  <div style={GAMES_PAGE_STYLES.gameIcon}>{type.icon}</div>
                  <Text strong>{type.label}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: '12px' }}>{type.description}</Text>
                </Card>
              </Col>
            ))}
          </Row>
        </div>

        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateGame}
        >
          <Form.Item
            name="partner_id"
            label="游戏伙伴"
            rules={[{ required: true, message: '请选择游戏伙伴' }]}
          >
            <Select placeholder="选择你想邀请的人">
              {/* TODO: 加载匹配对象列表 */}
              <Select.Option value="user_001">示例用户</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="difficulty"
            label="难度等级"
            initialValue="normal"
          >
            <Select>
              <Select.Option value="easy">简单</Select.Option>
              <Select.Option value="normal">普通</Select.Option>
              <Select.Option value="hard">困难</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                disabled={!selectedGameType}
                icon={<CheckCircleOutlined />}
              >
                创建游戏
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 悬浮球 - 快速对话入口 */}
      <AgentFloatingBall
        visible={true}
        unreadCount={unreadCount}
        hasNewMessage={hasNewMessage}
      />
    </div>
  )
}

export default GamesPage
