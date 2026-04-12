/**
 * Who Likes Me 页面
 *
 * 参考 Tinder Gold 功能：
 * - 显示喜欢你的人列表
 * - 会员可查看完整信息并直接匹配
 * - 靼会员只能看模糊预览（数量提示）
 * - 引导非会员订阅
 */

import React, { useState, useEffect } from 'react'
import {
  Avatar, Badge, Button, Card, Empty, List, Modal, Space, Spin, Typography, message, Tooltip, Progress
} from 'antd'
import {
  HeartOutlined, HeartFilled, CrownOutlined, EyeOutlined, LockOutlined, UserOutlined, StarFilled
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { whoLikesMeApi, WhoLikesMeResponse, LikeUser } from '../api/whoLikesMeApi'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'
const GOLD_COLOR = '#FFD700'

interface WhoLikesMePageProps {
  userId: string
  onMatch?: (matchId: string, matchData: any) => void
}

/**
 * Who Likes Me 页面组件
 */
const WhoLikesMePage: React.FC<WhoLikesMePageProps> = ({
  userId,
  onMatch
}) => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<WhoLikesMeResponse | null>(null)
  const [sortBy, setSortBy] = useState<'time' | 'compatibility'>('time')
  const [likingBack, setLikingBack] = useState<string | null>(null)
  const [showMembershipModal, setShowMembershipModal] = useState(false)

  // 加载数据
  useEffect(() => {
    loadWhoLikesMe()
    // 每 30 秒刷新一次
    const interval = setInterval(loadWhoLikesMe, 30 * 1000)
    return () => clearInterval(interval)
  }, [userId, sortBy])

  const loadWhoLikesMe = async () => {
    try {
      setLoading(true)
      const result = await whoLikesMeApi.getWhoLikesMe(userId, 20, 0, sortBy)
      setData(result)
    } catch (error) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleLikeBack = async (targetUserId: string) => {
    // 检查会员状态
    if (!data?.is_member) {
      setShowMembershipModal(true)
      return
    }

    try {
      setLikingBack(targetUserId)
      const result = await whoLikesMeApi.likeBack(userId, targetUserId)

      if (result.matched) {
        message.success('🎉 匹配成功！')
        // 刷新列表
        loadWhoLikesMe()
        // 回调匹配成功
        if (onMatch && result.match_id) {
          onMatch(result.match_id, { targetUserId })
        }
      } else if (result.success) {
        message.success('已喜欢')
        loadWhoLikesMe()
      } else {
        message.warning(result.message)
      }
    } catch (error) {
      message.error('操作失败')
    } finally {
      setLikingBack(null)
    }
  }

  const handleSortChange = (newSort: 'time' | 'compatibility') => {
    setSortBy(newSort)
  }

  const formatTime = (isoString: string): string => {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

    if (diffHours < 1) {
      return '刚刚'
    } else if (diffHours < 24) {
      return `${diffHours}小时前`
    } else {
      const diffDays = Math.floor(diffHours / 24)
      return `${diffDays}天前`
    }
  }

  // 非会员引导视图
  const renderNonMemberView = () => {
    if (!data) return null

    const previewCount = data.free_preview_count

    return (
      <div className="who-likes-me-non-member">
        {/* 数量提示卡片 */}
        <Card
          style={{
            borderRadius: 16,
            background: `linear-gradient(135deg, ${GOLD_COLOR}20 0%, ${PRIMARY_COLOR}20 100%)`,
            marginBottom: 24
          }}
        >
          <Space direction="vertical" size="middle" style={{ width: '100%', textAlign: 'center' }}>
            <Badge count={data.total_count} style={{ backgroundColor: GOLD_COLOR }}>
              <HeartFilled style={{ fontSize: 48, color: GOLD_COLOR }} />
            </Badge>
            <Title level={4} style={{ margin: 0 }}>
              {data.total_count} 人喜欢你
            </Title>
            <Text type="secondary">
              升级会员即可查看完整列表并直接匹配
            </Text>
            <Button
              type="primary"
              size="large"
              icon={<CrownOutlined />}
              onClick={() => navigate('/membership')}
              style={{
                background: GOLD_COLOR,
                borderColor: GOLD_COLOR,
                borderRadius: 12,
                minWidth: 200
              }}
            >
              升级会员解锁
            </Button>
          </Space>
        </Card>

        {/* 模糊预览卡片 */}
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            🔒 仅会员可见完整信息
          </Text>
        </div>

        <List
          dataSource={data.likes.slice(0, previewCount)}
          renderItem={(like: LikeUser) => (
            <Card
              size="small"
              style={{
                marginBottom: 12,
                borderRadius: 12,
                opacity: 0.8,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {/* 模糊头像 */}
                <div style={{
                  filter: 'blur(8px)',
                  overflow: 'hidden',
                  borderRadius: '50%',
                }}>
                  <Avatar
                    size={48}
                    icon={<UserOutlined />}
                    src={like.avatar_blurred}
                  />
                </div>

                {/* 模糊名称 */}
                <div style={{ flex: 1 }}>
                  <Text strong style={{ fontSize: 16 }}>
                    {like.name}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                    {formatTime(like.liked_at)}
                  </Text>
                </div>

                {/* 锁定图标 */}
                <LockOutlined style={{ fontSize: 20, color: '#999' }} />
              </div>
            </Card>
          )}
        />

        {/* 更多提示 */}
        {data.total_count > previewCount && (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <Text type="secondary">
              还有 {data.total_count - previewCount} 人...
            </Text>
            <br />
            <Button
              type="link"
              icon={<CrownOutlined style={{ color: GOLD_COLOR }} />}
              onClick={() => navigate('/membership')}
              style={{ color: GOLD_COLOR }}
            >
              升级会员查看全部
            </Button>
          </div>
        )}
      </div>
    )
  }

  // 会员完整视图
  const renderMemberView = () => {
    if (!data) return null

    return (
      <div className="who-likes-me-member">
        {/* 标题栏 */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16
        }}>
          <Space>
            <HeartFilled style={{ fontSize: 24, color: PRIMARY_COLOR }} />
            <Title level={5} style={{ margin: 0 }}>
              {data.total_count} 人喜欢你
            </Title>
            <Badge
              count="会员"
              style={{
                backgroundColor: GOLD_COLOR,
                fontSize: 10,
                height: 18,
                lineHeight: '18px'
              }}
            />
          </Space>

          {/* 排序选择 */}
          <Space size="small">
            <Button
              size="small"
              type={sortBy === 'time' ? 'primary' : 'default'}
              onClick={() => handleSortChange('time')}
              style={{ borderRadius: 8 }}
            >
              按时间
            </Button>
            <Button
              size="small"
              type={sortBy === 'compatibility' ? 'primary' : 'default'}
              onClick={() => handleSortChange('compatibility')}
              style={{ borderRadius: 8 }}
            >
              按匹配度
            </Button>
          </Space>
        </div>

        {/* 用户列表 */}
        <List
          dataSource={data.likes}
          renderItem={(like: LikeUser) => (
            <Card
              size="small"
              style={{
                marginBottom: 12,
                borderRadius: 12,
                border: `1px solid rgba(200, 139, 139, 0.2)`,
              }}
              className="who-likes-card"
              hoverable
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {/* 头像 */}
                <Avatar
                  size={56}
                  icon={<UserOutlined />}
                  src={like.avatar}
                  style={{ border: `2px solid ${PRIMARY_COLOR}` }}
                />

                {/* 信息 */}
                <div style={{ flex: 1 }}>
                  <Space direction="vertical" size={4} style={{ width: '100%' }}>
                    <Space>
                      <Text strong style={{ fontSize: 16 }}>{like.name}</Text>
                      <StarFilled style={{ fontSize: 12, color: GOLD_COLOR }} />
                    </Space>

                    {/* 匹配度（会员可见） */}
                    {like.compatibility_score !== undefined && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Progress
                          percent={Math.round(like.compatibility_score * 100)}
                          size="small"
                          strokeColor={PRIMARY_COLOR}
                          showInfo={false}
                          style={{ width: 80 }}
                        />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {Math.round(like.compatibility_score * 100)}% 匹配
                        </Text>
                      </div>
                    )}

                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {formatTime(like.liked_at)} 喜欢了你
                    </Text>
                  </Space>
                </div>

                {/* 操作按钮 */}
                <Button
                  type="primary"
                  icon={<HeartFilled />}
                  loading={likingBack === like.user_id}
                  onClick={() => handleLikeBack(like.user_id)}
                  style={{
                    background: PRIMARY_COLOR,
                    borderColor: PRIMARY_COLOR,
                    borderRadius: 8,
                  }}
                >
                  喜欢
                </Button>
              </div>
            </Card>
          )}
        />

        {/* 加载更多 */}
        {data.has_more && (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <Button onClick={() => message.info('已显示全部')}>
              加载更多
            </Button>
          </div>
        )}
      </div>
    )
  }

  // 加载状态
  if (loading && !data) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <Spin size="large" tip="加载喜欢你的人..." />
      </div>
    )
  }

  // 空状态
  if (!loading && data && data.total_count === 0) {
    return (
      <div style={{ padding: 48 }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical" size="small">
              <Text>暂无人喜欢你</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                继续完善资料，增加吸引力
              </Text>
              <Button
                type="primary"
                icon={<EyeOutlined />}
                onClick={() => navigate('/profile')}
                style={{
                  background: PRIMARY_COLOR,
                  borderColor: PRIMARY_COLOR,
                  borderRadius: 8,
                }}
              >
                优化资料
              </Button>
            </Space>
          }
        />
      </div>
    )
  }

  return (
    <div className="who-likes-me-page" style={{ padding: 16, maxWidth: 480, margin: '0 auto' }}>
      {data?.is_member ? renderMemberView() : renderNonMemberView()}

      {/* 会员引导弹窗 */}
      <Modal
        title={
          <Space>
            <CrownOutlined style={{ color: GOLD_COLOR }} />
            <span>升级会员解锁</span>
          </Space>
        }
        open={showMembershipModal}
        onCancel={() => setShowMembershipModal(false)}
        footer={[
          <Button key="cancel" onClick={() => setShowMembershipModal(false)}>
            取消
          </Button>,
          <Button
            key="subscribe"
            type="primary"
            icon={<CrownOutlined />}
            onClick={() => {
              setShowMembershipModal(false)
              navigate('/membership')
            }}
            style={{
              background: GOLD_COLOR,
              borderColor: GOLD_COLOR,
            }}
          >
            立即订阅
          </Button>,
        ]}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Paragraph>
            升级会员后，你可以：
          </Paragraph>
          <ul style={{ paddingLeft: 20 }}>
            <li>查看喜欢你的人完整列表</li>
            <li>直接匹配，无需等待</li>
            <li>无限滑动次数</li>
            <li>更多高级功能</li>
          </ul>
        </Space>
      </Modal>

      <style>{`
        .who-likes-me-page .who-likes-card:hover {
          box-shadow: 0 4px 12px rgba(200, 139, 139, 0.2);
          transition: box-shadow 0.2s;
        }
      `}</style>
    </div>
  )
}

export default WhoLikesMePage