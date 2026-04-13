/**
 * 功能卡片组件库
 *
 * 在对话区生成的功能卡片，不是跳转到新页面
 *
 * AI Native 设计原则：
 * 1. 用户在卡片上直接操作
 * 2. 不跳转到新页面
 * 3. 操作结果即时反馈
 *
 * 性能优化：
 * 1. 骨架屏立即显示，提升感知速度
 * 2. API 并行加载，不阻塞渲染
 * 3. 使用 React.memo 减少不必要重渲染
 */

import React, { useState, useEffect, useMemo, memo, Suspense, lazy } from 'react'
import {
  Card,
  Typography,
  Button,
  Space,
  Upload,
  Progress,
  Tag,
  List,
  Avatar,
  Divider,
  Alert,
  Input,
  Rate,
  Empty,
  Spin,
  message,
  Image,
  Modal,
  Steps,
} from 'antd'
import {
  CameraOutlined,
  SafetyCertificateOutlined,
  CrownOutlined,
  HeartOutlined,
  GiftOutlined,
  SecurityScanOutlined,
  BarChartOutlined,
  MessageOutlined,
  UploadOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  PlusOutlined,
  IdcardOutlined,
  TrophyOutlined,
  StarFilled,
  CalendarOutlined,
  BulbOutlined,
  ExperimentOutlined,
  CompassOutlined,
  CommentOutlined,
} from '@ant-design/icons'

import photosApi from '../api/photosApi'
import { SkeletonCard, SkeletonText } from './Skeleton'
import { deerflowClient } from '../api/deerflowClient'
import { authStorage } from '../utils/storage'

const { Title, Text, Paragraph } = Typography

// ========== 骨架屏占位组件 ==========

// 🚀 [性能优化] 导出骨架屏组件，供 Suspense fallback 使用
export const FeatureCardSkeleton: React.FC<{ title?: string }> = ({ title = '加载中...' }) => (
  <Card className="feature-card">
    <div className="card-header">
      <div className="skeleton-icon" style={{ width: 24, height: 24, background: '#f0f0f0', borderRadius: 4 }} />
      <div className="skeleton-title" style={{ width: 100, height: 20, background: '#f0f0f0', borderRadius: 4, marginLeft: 8 }} />
    </div>
    <Divider />
    <SkeletonCard showAvatar={false} contentLines={3} />
  </Card>
)

// ========== 照片管理卡片 ==========

interface Photo {
  id: string
  photo_url: string
  photo_type: string
  moderation_status: string
  is_verified: boolean
}

interface PhotoManageCardProps {
  onPhotoUploaded?: () => void
}

// 🚀 [性能优化] 使用 memo 防止不必要的重渲染
export const PhotoManageCard: React.FC<PhotoManageCardProps> = memo(({ onPhotoUploaded }) => {
  const [photos, setPhotos] = useState<Photo[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const maxPhotos = 9

  // 加载照片列表
  useEffect(() => {
    loadPhotos()
  }, [])

  const loadPhotos = async () => {
    try {
      setLoading(true)
      const data = await photosApi.getMyPhotos()
      setPhotos(data)
    } catch (error) {
      console.error('Failed to load photos:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (file: File) => {
    // 验证文件
    const isImage = file.type.startsWith('image/')
    if (!isImage) {
      message.error('只能上传图片文件')
      return
    }

    const isLt5M = file.size / 1024 / 1024 < 5
    if (!isLt5M) {
      message.error('图片大小不能超过 5MB')
      return
    }

    if (photos.length >= maxPhotos) {
      message.warning('最多只能上传 9 张照片')
      return
    }

    setUploading(true)
    try {
      await photosApi.uploadPhotoFile(file, 'profile')
      message.success('照片上传成功')
      await loadPhotos()
      onPhotoUploaded?.()
    } catch (error) {
      message.error('上传失败，请重试')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (photoId: string) => {
    try {
      await photosApi.deletePhoto(photoId)
      message.success('照片已删除')
      await loadPhotos()
    } catch (error) {
      message.error('删除失败')
    }
  }

  // 🚀 [性能优化] 骨架屏立即显示，提升感知速度
  if (loading) {
    return <FeatureCardSkeleton title="照片管理" />
  }

  return (
    <Card className="feature-card photo-card">
      <div className="card-header">
        <CameraOutlined style={{ fontSize: 24, color: '#1890ff' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>照片管理</Title>
      </div>

      <Divider />

      {/* 照片统计 */}
      <div className="photo-stats" style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text>当前照片：<Text strong>{photos.length}</Text> / {maxPhotos}</Text>
          {photos.length < 3 && (
            <Tag color="orange">建议上传 3 张以上</Tag>
          )}
        </Space>
        <Progress
          percent={(photos.length / maxPhotos) * 100}
          showInfo={false}
          strokeColor={photos.length >= 3 ? '#52c41a' : '#faad14'}
        />
      </div>

      {/* 照片网格 */}
      <div className="photo-grid" style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 8,
        marginBottom: 16
      }}>
        {photos.map(photo => (
          <div
            key={photo.id}
            style={{
              position: 'relative',
              aspectRatio: '1',
              borderRadius: 8,
              overflow: 'hidden'
            }}
          >
            <Image
              src={photo.photo_url}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            />
            {/* 状态标签 */}
            {photo.moderation_status === 'pending' && (
              <Tag color="blue" style={{ position: 'absolute', top: 4, left: 4 }}>
                审核中
              </Tag>
            )}
            {photo.is_verified && (
              <Tag color="green" style={{ position: 'absolute', top: 4, left: 4 }}>
                已验证
              </Tag>
            )}
            {/* 删除按钮 */}
            <Button
              type="primary"
              danger
              size="small"
              icon={<DeleteOutlined />}
              style={{ position: 'absolute', bottom: 4, right: 4 }}
              onClick={() => handleDelete(photo.id)}
            />
          </div>
        ))}

        {/* 上传按钮 */}
        {photos.length < maxPhotos && (
          <Upload
            beforeUpload={(file) => {
              handleUpload(file)
              return false
            }}
            showUploadList={false}
            accept="image/*"
          >
            <div
              style={{
                aspectRatio: '1',
                border: '2px dashed #d9d9d9',
                borderRadius: 8,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'border-color 0.3s'
              }}
            >
              {uploading ? (
                <Spin />
              ) : (
                <>
                  <PlusOutlined style={{ fontSize: 24, color: '#999' }} />
                  <Text type="secondary" style={{ fontSize: 12, marginTop: 4 }}>上传</Text>
                </>
              )}
            </div>
          </Upload>
        )}
      </div>

      {/* 提示信息 */}
      {photos.length < 3 ? (
        <Alert
          type="info"
          message="上传更多照片能让更多人了解你，匹配成功率提升 40%"
          showIcon
        />
      ) : (
        <Alert
          type="success"
          message="照片数量充足，继续保持~"
          showIcon
        />
      )}
    </Card>
  )
})

// ========== 身份认证卡片 ==========

interface IdentityVerifyCardProps {
  verifyStatus?: 'none' | 'pending' | 'verified'
  onStartVerify?: () => void
}

// 🚀 [性能优化] 使用 memo 防止不必要的重渲染
export const IdentityVerifyCard: React.FC<IdentityVerifyCardProps> = memo(({
  verifyStatus = 'none',
  onStartVerify
}) => {
  const [modalVisible, setModalVisible] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [uploading, setUploading] = useState(false)

  const statusConfig = {
    none: { color: '#faad14', text: '未认证', icon: <SafetyCertificateOutlined /> },
    pending: { color: '#1890ff', text: '审核中', icon: <ClockCircleOutlined /> },
    verified: { color: '#52c41a', text: '已认证', icon: <CheckCircleOutlined /> },
  }

  const config = statusConfig[verifyStatus]

  const handleUploadIdCard = async (file: File) => {
    setUploading(true)
    try {
      // 证件上传（当前为模拟流程，集成 identityApi 后可对接真实认证）
      await new Promise(resolve => setTimeout(resolve, 1500))
      message.success('证件上传成功')
      setCurrentStep(1)
    } catch (error) {
      message.error('上传失败，请重试')
    } finally {
      setUploading(false)
    }
  }

  const handleUploadSelfie = async (file: File) => {
    setUploading(true)
    try {
      // 证件上传（当前为模拟流程，集成 identityApi 后可对接真实认证）
      await new Promise(resolve => setTimeout(resolve, 1500))
      message.success('自拍上传成功')
      setCurrentStep(2)
      // 模拟审核
      setTimeout(() => {
        setModalVisible(false)
        onStartVerify?.()
      }, 1000)
    } catch (error) {
      message.error('上传失败，请重试')
    } finally {
      setUploading(false)
    }
  }

  return (
    <>
      <Card className="feature-card verify-card">
        <div className="card-header">
          <IdcardOutlined style={{ fontSize: 24, color: '#52c41a' }} />
          <Title level={4} style={{ margin: '0 0 0 8px' }}>身份认证</Title>
        </div>

        <Divider />

        <div className="verify-status" style={{ textAlign: 'center', marginBottom: 16 }}>
          <Tag color={config.color} style={{ fontSize: 14, padding: '4px 16px' }}>
            {config.icon} {config.text}
          </Tag>
        </div>

        {verifyStatus === 'none' && (
          <>
            <Paragraph type="secondary">
              完成身份认证可以：
            </Paragraph>
            <List
              size="small"
              dataSource={[
                '增加个人资料可信度',
                '获得认证徽章标识',
                '匹配成功率提升 30%',
                '解锁更多高级功能',
              ]}
              renderItem={(item) => (
                <List.Item>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  {item}
                </List.Item>
              )}
            />
            <Button
              type="primary"
              block
              onClick={() => setModalVisible(true)}
              style={{ marginTop: 16 }}
            >
              开始认证
            </Button>
          </>
        )}

        {verifyStatus === 'pending' && (
          <Alert
            type="info"
            message="认证申请已提交，预计 1-3 个工作日内完成审核"
            showIcon
          />
        )}

        {verifyStatus === 'verified' && (
          <Alert
            type="success"
            message="恭喜！你已完成身份认证"
            showIcon
            description="你的资料已获得认证徽章，匹配成功率已提升"
          />
        )}
      </Card>

      {/* 认证流程弹窗 */}
      <Modal
        title="身份认证"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={400}
      >
        <Steps
          current={currentStep}
          items={[
            { title: '上传证件' },
            { title: '人脸验证' },
            { title: '完成' },
          ]}
          style={{ marginBottom: 24 }}
        />

        {currentStep === 0 && (
          <div style={{ textAlign: 'center' }}>
            <Paragraph type="secondary">
              请上传身份证正面照片
            </Paragraph>
            <Upload
              beforeUpload={(file) => {
                handleUploadIdCard(file)
                return false
              }}
              showUploadList={false}
              accept="image/*"
            >
              <Button icon={<UploadOutlined />} loading={uploading}>
                选择证件照片
              </Button>
            </Upload>
          </div>
        )}

        {currentStep === 1 && (
          <div style={{ textAlign: 'center' }}>
            <Paragraph type="secondary">
              请上传手持证件的自拍照片
            </Paragraph>
            <Upload
              beforeUpload={(file) => {
                handleUploadSelfie(file)
                return false
              }}
              showUploadList={false}
              accept="image/*"
            >
              <Button icon={<CameraOutlined />} loading={uploading}>
                拍摄自拍照片
              </Button>
            </Upload>
          </div>
        )}

        {currentStep === 2 && (
          <div style={{ textAlign: 'center' }}>
            <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
            <Paragraph style={{ marginTop: 16 }}>
              认证资料已提交，等待审核...
            </Paragraph>
          </div>
        )}
      </Modal>
    </>
  )
})

// ========== 会员订阅卡片 ==========

interface MembershipCardProps {
  currentPlan?: 'free' | 'premium' | 'vip'
  onUpgrade?: (plan: string) => void
}

// 🚀 [性能优化] 使用 memo 防止不必要的重渲染
export const MembershipCard: React.FC<MembershipCardProps> = memo(({
  currentPlan = 'free',
  onUpgrade
}) => {
  const plans = [
    {
      key: 'free',
      name: '免费版',
      price: 0,
      features: ['每日 5 次匹配', '基础聊天功能', '查看匹配列表'],
    },
    {
      key: 'premium',
      name: '高级会员',
      price: 29,
      features: ['无限次匹配', '高级筛选功能', '查看谁喜欢你', '优先客服'],
      popular: true,
    },
    {
      key: 'vip',
      name: 'VIP会员',
      price: 99,
      features: ['全部高级功能', '专属身份标识', '超级曝光特权', '一对一红娘服务'],
    },
  ]

  const handleSelectPlan = (planKey: string) => {
    if (planKey === currentPlan) return
    onUpgrade?.(planKey)
  }

  return (
    <Card className="feature-card membership-card">
      <div className="card-header">
        <CrownOutlined style={{ fontSize: 24, color: '#faad14' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>会员订阅</Title>
      </div>

      <Divider />

      <List
        grid={{ column: 1 }}
        dataSource={plans}
        renderItem={(plan) => (
          <List.Item>
            <Card
              size="small"
              className={plan.popular ? 'plan-card popular' : 'plan-card'}
              style={{
                border: currentPlan === plan.key ? '2px solid #1890ff' : undefined,
                background: currentPlan === plan.key ? '#f6ffed' : undefined
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space>
                  <Text strong style={{ fontSize: 16 }}>{plan.name}</Text>
                  {plan.popular && <Tag color="red">热门</Tag>}
                  {currentPlan === plan.key && <Tag color="green">当前</Tag>}
                </Space>
                <Text strong style={{ fontSize: 20 }}>
                  {plan.price === 0 ? '免费' : `¥${plan.price}/月`}
                </Text>
              </div>
              <List
                size="small"
                dataSource={plan.features}
                renderItem={(item) => (
                  <List.Item style={{ border: 'none', padding: '4px 0' }}>
                    <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8, fontSize: 12 }} />
                    <Text type="secondary" style={{ fontSize: 12 }}>{item}</Text>
                  </List.Item>
                )}
              />
              {plan.key !== 'free' && currentPlan !== plan.key && (
                <Button
                  type={plan.popular ? 'primary' : 'default'}
                  block
                  size="small"
                  onClick={() => handleSelectPlan(plan.key)}
                  style={{ marginTop: 8 }}
                >
                  立即开通
                </Button>
              )}
            </Card>
          </List.Item>
        )}
      />
    </Card>
  )
})

// ========== 礼物推荐卡片 ==========

interface GiftRecommendCardProps {
  gifts?: Array<{
    name: string
    price: number
    reason: string
    image?: string
  }>
  onSelect?: (gift: any) => void
}

// 🚀 [性能优化] 使用 memo 防止不必要的重渲染
export const GiftRecommendCard: React.FC<GiftRecommendCardProps> = memo(({
  gifts = [
    { name: '玫瑰花束', price: 199, reason: '浪漫经典，表达心意' },
    { name: '巧克力礼盒', price: 88, reason: '甜蜜温馨，适合初识' },
    { name: '定制相册', price: 128, reason: '纪念你们的故事' },
  ],
  onSelect
}) => {
  return (
    <Card className="feature-card gift-card">
      <div className="card-header">
        <GiftOutlined style={{ fontSize: 24, color: '#ff69b4' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>礼物推荐</Title>
      </div>

      <Divider />

      <List
        dataSource={gifts}
        renderItem={(gift) => (
          <List.Item
            actions={[
              <Button key="select" type="link" onClick={() => onSelect?.(gift)}>
                选择
              </Button>
            ]}
          >
            <List.Item.Meta
              avatar={
                <Avatar style={{ backgroundColor: '#fff0f6' }}>
                  <GiftOutlined style={{ color: '#ff69b4' }} />
                </Avatar>
              }
              title={gift.name}
              description={
                <>
                  <Text type="secondary">{gift.reason}</Text>
                  <br />
                  <Text strong style={{ color: '#ff4d4f' }}>¥{gift.price}</Text>
                </>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  )
})

// ========== 关系分析卡片 ==========

interface RelationshipAnalysisCardProps {
  score?: number
  stage?: string
  suggestions?: string[]
  onViewDetails?: () => void
}

// 🚀 [性能优化] 使用 memo 防止不必要的重渲染
export const RelationshipAnalysisCard: React.FC<RelationshipAnalysisCardProps> = memo(({
  score = 0,
  stage = '未知',
  suggestions = [],
  onViewDetails
}) => {
  const getScoreColor = (s: number) => {
    if (s >= 80) return '#52c41a'
    if (s >= 60) return '#1890ff'
    if (s >= 40) return '#faad14'
    return '#ff4d4f'
  }

  return (
    <Card className="feature-card analysis-card">
      <div className="card-header">
        <BarChartOutlined style={{ fontSize: 24, color: '#1890ff' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>关系分析</Title>
      </div>

      <Divider />

      <div className="score-display" style={{ textAlign: 'center', marginBottom: 16 }}>
        <Progress
          type="circle"
          percent={score}
          strokeColor={getScoreColor(score)}
          format={(percent) => (
            <span style={{ fontSize: 24, fontWeight: 'bold' }}>{percent}分</span>
          )}
        />
        <div style={{ marginTop: 8 }}>
          <Tag color="blue">{stage}</Tag>
        </div>
      </div>

      {suggestions.length > 0 && (
        <>
          <Title level={5}>改进建议</Title>
          <List
            size="small"
            dataSource={suggestions.slice(0, 3)}
            renderItem={(item) => (
              <List.Item style={{ border: 'none', padding: '4px 0' }}>
                <Text type="secondary">• {item}</Text>
              </List.Item>
            )}
          />
        </>
      )}

      <Button type="primary" block onClick={onViewDetails} style={{ marginTop: 16 }}>
        查看详细分析
      </Button>
    </Card>
  )
})

// ========== 安全守护卡片 ==========

interface SafetyGuardianCardProps {
  emergencyContacts?: number
  safetyScore?: number
  onAddContact?: () => void
  onEmergency?: () => void
}

// 🚀 [性能优化] 使用 memo 防止不必要的重渲染
export const SafetyGuardianCard: React.FC<SafetyGuardianCardProps> = memo(({
  emergencyContacts = 0,
  safetyScore = 100,
  onAddContact,
  onEmergency
}) => {
  return (
    <Card className="feature-card safety-card">
      <div className="card-header">
        <SecurityScanOutlined style={{ fontSize: 24, color: '#52c41a' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>安全守护</Title>
      </div>

      <Divider />

      <div className="safety-status" style={{ textAlign: 'center' }}>
        <Progress
          type="dashboard"
          percent={safetyScore}
          strokeColor="#52c41a"
          format={() => '安全'}
          size={80}
        />
      </div>

      <div className="emergency-info" style={{ margin: '16px 0' }}>
        <Text>紧急联系人：<Text strong>{emergencyContacts}</Text> 人</Text>
        {emergencyContacts < 2 && (
          <Tag color="orange" style={{ marginLeft: 8 }}>建议添加</Tag>
        )}
      </div>

      <Space direction="vertical" style={{ width: '100%' }}>
        <Button block onClick={onAddContact}>
          添加紧急联系人
        </Button>
        <Button danger block onClick={onEmergency}>
          紧急求助
        </Button>
      </Space>

      <Alert
        type="info"
        message="建议添加至少 2 位紧急联系人，关键时刻我们会在第一时间通知他们"
        style={{ marginTop: 16 }}
        showIcon
      />
    </Card>
  )
})

// ========== 里程碑卡片 ==========

interface MilestoneFeatureCardProps {
  milestones?: Array<{
    id: string
    title: string
    milestone_type: string
    milestone_date: string
    description?: string
    achieved?: boolean
  }>
  partnerId?: string
  partnerName?: string
  onAddMilestone?: () => void
  onViewAll?: () => void
}

// 🚀 [性能优化] 使用 memo 防止不必要的重渲染
export const MilestoneFeatureCard: React.FC<MilestoneFeatureCardProps> = memo(({
  milestones = [],
  partnerId,
  partnerName,
  onAddMilestone,
  onViewAll
}) => {
  const [loading, setLoading] = useState(false)

  // 获取里程碑图标
  const getMilestoneIcon = (type: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      first_match: '💕',
      first_chat: '💬',
      first_date: '☕',
      relationship_start: '❤️',
      anniversary: '🎁',
      engaged: '💍',
      married: '💒',
    }
    return iconMap[type] || '🎯'
  }

  // 加载里程碑数据
  useEffect(() => {
    if (partnerId) {
      loadMilestones()
    }
  }, [partnerId])

  const loadMilestones = async () => {
    if (!partnerId) return
    try {
      setLoading(true)
      // 里程碑加载（当前为 placeholder，集成 milestoneApi 后可获取真实数据）
      // const data = await milestoneApi.getMilestoneTimeline(currentUserId, partnerId)
    } catch (error) {
      console.error('Failed to load milestones:', error)
    } finally {
      setLoading(false)
    }
  }

  // 没有伴侣时的提示
  if (!partnerId) {
    return (
      <Card className="feature-card milestone-card">
        <div className="card-header">
          <TrophyOutlined style={{ fontSize: 24, color: '#D4A59A' }} />
          <Title level={4} style={{ margin: '0 0 0 8px' }}>关系里程碑</Title>
        </div>

        <Divider />

        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical" size="small">
              <Text type="secondary">还没有匹配对象</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>匹配成功后可以记录你们的重要时刻</Text>
            </Space>
          }
        />

        <Button block type="primary" style={{ marginTop: 16, background: 'linear-gradient(135deg, #D4A59A 0%, #C88B8B 100%)', border: 'none' }}>
          去匹配
        </Button>
      </Card>
    )
  }

  return (
    <Card className="feature-card milestone-card">
      <div className="card-header">
        <TrophyOutlined style={{ fontSize: 24, color: '#D4A59A' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>
          与 {partnerName || 'TA'} 的里程碑
        </Title>
      </div>

      <Divider />

      {loading ? (
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin tip="加载中..." />
        </div>
      ) : milestones.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="还没有记录里程碑"
        />
      ) : (
        <List
          dataSource={milestones.slice(0, 5)}
          renderItem={(milestone) => (
            <List.Item style={{ padding: '8px 0' }}>
              <List.Item.Meta
                avatar={
                  <span style={{ fontSize: 20 }}>{getMilestoneIcon(milestone.milestone_type)}</span>
                }
                title={
                  <Space>
                    <Text strong style={{ fontSize: 14 }}>{milestone.title}</Text>
                    {milestone.achieved && <StarFilled style={{ color: '#faad14', fontSize: 12 }} />}
                  </Space>
                }
                description={
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <CalendarOutlined style={{ marginRight: 4 }} />
                    {new Date(milestone.milestone_date).toLocaleDateString()}
                  </Text>
                }
              />
            </List.Item>
          )}
        />
      )}

      <Space direction="vertical" style={{ width: '100%', marginTop: 16 }}>
        <Button
          block
          icon={<PlusOutlined />}
          onClick={onAddMilestone}
          style={{ borderRadius: 8 }}
        >
          记录新里程碑
        </Button>
        {milestones.length > 0 && (
          <Button block type="link" onClick={onViewAll}>
            查看全部 {milestones.length} 个里程碑
          </Button>
        )}
      </Space>
    </Card>
  )
})

// ========== AI 功能卡片（使用 Skill 调用）==========

// 破冰话题卡片
interface DeepIcebreakerCardProps {
  onTopicSelect?: (topic: string) => void
}

const DeepIcebreakerCard: React.FC<DeepIcebreakerCardProps> = ({ onTopicSelect }) => {
  const [loading, setLoading] = useState(false)
  const [topics, setTopics] = useState<any[]>([])

  const generateTopics = async () => {
    setLoading(true)
    try {
      const userId = authStorage.getUserId()
      const result = await deerflowClient.chat("帮我生成一些破冰话题，让我可以和匹配对象开启对话")

      // Agent Native 架构：优先从 ai_message 解析 JSON
      const parsed = deerflowClient.parseToolResult(result)
      if (parsed?.type === 'topics' && parsed.data.topics?.length > 0) {
        setTopics(parsed.data.topics)
      } else if (result.success && result.tool_result?.data?.topics) {
        // 降级：从 tool_result.data 获取（兼容旧架构）
        setTopics(result.tool_result.data.topics)
      } else {
        // 如果没有结构化数据，从 AI 消息中解析
        setTopics([{ topic_content: result.ai_message }])
      }
    } catch (error) {
      message.error('生成话题失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="feature-card">
      <div className="card-header">
        <BulbOutlined style={{ fontSize: 24, color: '#FFD700' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>破冰话题</Title>
        <Tag color="purple" style={{ marginLeft: 8 }}>AI</Tag>
      </div>
      <Divider />
      <Button
        type="primary"
        block
        icon={<BulbOutlined />}
        loading={loading}
        onClick={generateTopics}
        style={{ marginBottom: 16, borderRadius: 8 }}
      >
        AI 生成话题
      </Button>
      {topics.length > 0 && (
        <List
          dataSource={topics.slice(0, 5)}
          renderItem={(topic: any) => (
            <List.Item
              onClick={() => onTopicSelect?.(topic.topic_content || topic.content)}
              style={{ cursor: 'pointer', padding: '8px 0' }}
            >
              <Text>{topic.topic_content || topic.content}</Text>
            </List.Item>
          )}
        />
      )}
    </Card>
  )
}

// 消息解读卡片
interface MessageInterpretationCardProps {
  messageContent: string
  messageId: string
  partnerId: string
  onUseSuggestion?: (suggestion: string) => void
}

const MessageInterpretationCard: React.FC<MessageInterpretationCardProps> = ({
  messageContent,
  messageId,
  partnerId,
  onUseSuggestion
}) => {
  const [loading, setLoading] = useState(false)
  const [interpretation, setInterpretation] = useState<any>(null)

  const interpret = async () => {
    if (!messageContent) {
      message.warning('请先选择一条消息')
      return
    }
    setLoading(true)
    try {
      const userId = authStorage.getUserId()
      const result = await deerflowClient.chat(`帮我解读这条消息的含义并给出回复建议："${messageContent}"`)
      if (result.success) {
        const suggestions = result.tool_result?.data?.suggestions || [result.ai_message]
        setInterpretation({
          meaning: result.tool_result?.data?.meaning || '对方想要继续对话',
          suggestions
        })
      }
    } catch (error) {
      message.error('解读失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="feature-card">
      <div className="card-header">
        <CommentOutlined style={{ fontSize: 24, color: '#722ed1' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>消息解读</Title>
        <Tag color="purple" style={{ marginLeft: 8 }}>AI</Tag>
      </div>
      <Divider />
      {messageContent && (
        <Card size="small" style={{ marginBottom: 12, borderRadius: 8 }}>
          <Text type="secondary">原消息：</Text>
          <Paragraph style={{ margin: '4px 0' }}>{messageContent}</Paragraph>
        </Card>
      )}
      <Button
        type="primary"
        block
        loading={loading}
        onClick={interpret}
        style={{ marginBottom: 16, borderRadius: 8 }}
      >
        AI 解读
      </Button>
      {interpretation && (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text strong>含义：{interpretation.meaning}</Text>
          <Divider />
          <Text type="secondary">回复建议：</Text>
          {interpretation.suggestions?.map((s: string, i: number) => (
            <Button
              key={i}
              block
              size="small"
              onClick={() => onUseSuggestion?.(s)}
              style={{ borderRadius: 8 }}
            >
              {s}
            </Button>
          ))}
        </Space>
      )}
    </Card>
  )
}

// 活动推荐卡片
interface JointActivityCardProps {
  userProfile?: any
  partnerProfile?: any
  onActivitySelect?: (activity: any) => void
}

const JointActivityCard: React.FC<JointActivityCardProps> = ({
  userProfile,
  partnerProfile,
  onActivitySelect
}) => {
  const [loading, setLoading] = useState(false)
  const [activities, setActivities] = useState<any[]>([])

  const recommendActivities = async () => {
    setLoading(true)
    try {
      const userId = authStorage.getUserId()
      const result = await deerflowClient.chat("推荐一些适合我们两个人的约会活动")

      // Agent Native 架构：优先从 ai_message 解析 JSON
      const parsed = deerflowClient.parseToolResult(result)
      if (parsed?.type === 'date_plans' && parsed.data.plans?.length > 0) {
        setActivities(parsed.data.plans)
      } else if (parsed?.type === 'activities' && parsed.data.activities?.length > 0) {
        setActivities(parsed.data.activities)
      } else if (result.success && result.tool_result?.data?.activities) {
        // 降级：从 tool_result.data 获取（兼容旧架构）
        setActivities(result.tool_result.data.activities)
      } else if (result.success && result.tool_result?.data?.plans) {
        setActivities(result.tool_result.data.plans)
      } else {
        // 如果没有结构化数据，从 AI 消息中解析
        setActivities([{ activity_name: 'AI推荐', description: result.ai_message }])
      }
    } catch (error) {
      message.error('推荐失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="feature-card">
      <div className="card-header">
        <CompassOutlined style={{ fontSize: 24, color: '#13c2c2' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>活动推荐</Title>
        <Tag color="purple" style={{ marginLeft: 8 }}>AI</Tag>
      </div>
      <Divider />
      <Button
        type="primary"
        block
        icon={<CompassOutlined />}
        loading={loading}
        onClick={recommendActivities}
        style={{ marginBottom: 16, borderRadius: 8 }}
      >
        AI 推荐活动
      </Button>
      {activities.length > 0 && (
        <List
          dataSource={activities.slice(0, 5)}
          renderItem={(activity: any) => (
            <List.Item
              onClick={() => onActivitySelect?.(activity)}
              style={{ cursor: 'pointer', padding: '8px 0' }}
            >
              <Space direction="vertical" size={0}>
                <Text strong>{activity.activity_name || activity.name}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {activity.description}
                </Text>
              </Space>
            </List.Item>
          )}
        />
      )}
    </Card>
  )
}

// 压力测试卡片（简化版，完整版在 StressTest.tsx）
interface StressTestCardProps {
  userId: string
  partnerId: string
  onComplete?: (summary: any) => void
}

const StressTestCard: React.FC<StressTestCardProps> = ({
  userId,
  partnerId,
  onComplete
}) => {
  const [loading, setLoading] = useState(false)

  const startTest = async () => {
    setLoading(true)
    try {
      const result = await deerflowClient.chat("帮我创建一个关系压力测试，测试我们的价值观冲突应对能力")
      if (result.success) {
        message.success('测试已创建，请在弹窗中完成测试')
        onComplete?.({ testId: result.tool_result?.data?.test_id || 'test-' + Date.now() })
      }
    } catch (error) {
      message.error('创建测试失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="feature-card">
      <div className="card-header">
        <ExperimentOutlined style={{ fontSize: 24, color: '#eb2f96' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>压力测试</Title>
        <Tag color="green" style={{ marginLeft: 8 }}>新</Tag>
      </div>
      <Divider />
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        通过模拟场景测试你们的关系韧性，了解如何更好地应对冲突。
      </Paragraph>
      <Button
        type="primary"
        block
        icon={<ExperimentOutlined />}
        loading={loading}
        onClick={startTest}
        style={{ borderRadius: 8 }}
      >
        开始测试
      </Button>
    </Card>
  )
}

// Your Turn 功能卡片
interface YourTurnFeatureCardProps {
  pendingReminders?: any[]
  onMarkReplied?: (matchId: string) => void
}

const YourTurnFeatureCard: React.FC<YourTurnFeatureCardProps> = ({
  pendingReminders,
  onMarkReplied
}) => {
  return (
    <Card className="feature-card">
      <div className="card-header">
        <ClockCircleOutlined style={{ fontSize: 24, color: '#C88B8B' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>Your Turn</Title>
        <Tag color="green" style={{ marginLeft: 8 }}>新</Tag>
      </div>
      <Divider />
      {pendingReminders && pendingReminders.length > 0 ? (
        <List
          dataSource={pendingReminders}
          renderItem={(reminder: any) => (
            <List.Item
              actions={[
                <Button
                  key="reply"
                  size="small"
                  type="primary"
                  onClick={() => onMarkReplied?.(reminder.match_id)}
                  style={{ borderRadius: 8 }}
                >
                  已回复
                </Button>
              ]}
            >
              <List.Item.Meta
                avatar={<Avatar>{reminder.partner_name?.[0] || 'T'}</Avatar>}
                title={reminder.partner_name}
                description={`等待你的回复...`}
              />
            </List.Item>
          )}
        />
      ) : (
        <Empty description="暂无待回复的对话" />
      )}
    </Card>
  )
}

// 匹配偏好卡片
interface MatchingPreferenceCardProps {
  currentPreferences?: any
  onSave?: (preferences: any) => void
}

const MatchingPreferenceCard: React.FC<MatchingPreferenceCardProps> = ({
  currentPreferences,
  onSave
}) => {
  const [ageMin, setAgeMin] = useState(currentPreferences?.age_min || 18)
  const [ageMax, setAgeMax] = useState(currentPreferences?.age_max || 40)

  return (
    <Card className="feature-card">
      <div className="card-header">
        <SettingOutlined style={{ fontSize: 24, color: '#1890ff' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>匹配偏好</Title>
      </div>
      <Divider />
      <Space direction="vertical" style={{ width: '100%' }}>
        <Text strong>年龄范围：{ageMin} - {ageMax}</Text>
        <Input.Group compact>
          <Input style={{ width: 100 }} placeholder="最小年龄" value={ageMin} onChange={(e) => setAgeMin(Number(e.target.value))} />
          <Input style={{ width: 100 }} placeholder="最大年龄" value={ageMax} onChange={(e) => setAgeMax(Number(e.target.value))} />
        </Input.Group>
        <Button block type="primary" onClick={() => onSave?.({ age_min: ageMin, age_max: ageMax })} style={{ borderRadius: 8 }}>
          保存偏好
        </Button>
      </Space>
    </Card>
  )
}

// 约会提醒卡片
interface DateReminderCardProps {
  reminders?: any[]
  onCreateReminder?: () => void
}

const DateReminderCard: React.FC<DateReminderCardProps> = ({
  reminders,
  onCreateReminder
}) => {
  return (
    <Card className="feature-card">
      <div className="card-header">
        <CalendarOutlined style={{ fontSize: 24, color: '#fa8c16' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>约会提醒</Title>
      </div>
      <Divider />
      {reminders && reminders.length > 0 ? (
        <List
          dataSource={reminders}
          renderItem={(reminder: any) => (
            <List.Item>
              <List.Item.Meta
                avatar={<CalendarOutlined style={{ color: '#fa8c16' }} />}
                title={reminder.title}
                description={new Date(reminder.date).toLocaleDateString()}
              />
            </List.Item>
          )}
        />
      ) : (
        <Empty description="暂无约会计划" />
      )}
      <Button block icon={<PlusOutlined />} onClick={onCreateReminder} style={{ marginTop: 16, borderRadius: 8 }}>
        创建约会提醒
      </Button>
    </Card>
  )
}

// 视频片段卡片
interface VideoClipCardProps {
  clips?: any[]
  onRecord?: () => void
}

const VideoClipCard: React.FC<VideoClipCardProps> = ({
  clips,
  onRecord
}) => {
  return (
    <Card className="feature-card">
      <div className="card-header">
        <VideoCameraOutlined style={{ fontSize: 24, color: '#C88B8B' }} />
        <Title level={4} style={{ margin: '0 0 0 8px' }}>视频片段</Title>
        <Tag color="green" style={{ marginLeft: 8 }}>新</Tag>
      </div>
      <Divider />
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        录制一段短视频自我介绍，让对方更了解你。
      </Paragraph>
      {clips && clips.length > 0 ? (
        <List
          dataSource={clips}
          renderItem={(clip: any) => (
            <List.Item>
              <Text>{clip.title || '我的视频'}</Text>
            </List.Item>
          )}
        />
      ) : (
        <Empty description="暂无视频" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}
      <Button block type="primary" icon={<VideoCameraOutlined />} onClick={onRecord} style={{ marginTop: 16, borderRadius: 8 }}>
        录制视频
      </Button>
    </Card>
  )
}

// ========== 功能卡片渲染器 ==========

interface FeatureCardRendererProps {
  featureAction: string
  data?: any
  onAction?: (action: string, data?: any) => void
}

/**
 * 功能卡片渲染器
 *
 * 性能优化：
 * 1. 使用 memo 防止父组件重渲染导致的重复渲染
 * 2. 使用 useMemo 缓存渲染结果
 * 3. 统一的骨架屏占位
 */
export const FeatureCardRenderer: React.FC<FeatureCardRendererProps> = memo(({
  featureAction,
  data,
  onAction
}) => {
  // 🚀 [性能优化] 使用 useMemo 缓存渲染结果
  const renderedCard = useMemo(() => {
    switch (featureAction) {
      case 'photos':
        return (
          <PhotoManageCard
            onPhotoUploaded={() => onAction?.('photo_uploaded')}
          />
        )

      case 'verify':
        return (
          <IdentityVerifyCard
            verifyStatus={data?.verifyStatus}
            onStartVerify={() => onAction?.('start_verify')}
          />
        )

      case 'membership':
        return (
          <MembershipCard
            currentPlan={data?.currentPlan}
            onUpgrade={(plan) => onAction?.('upgrade_membership', plan)}
          />
        )

      case 'gifts':
        return (
          <GiftRecommendCard
            gifts={data?.gifts}
            onSelect={(gift) => onAction?.('select_gift', gift)}
          />
        )

      case 'analysis':
        return (
          <RelationshipAnalysisCard
            score={data?.score}
            stage={data?.stage}
            suggestions={data?.suggestions}
            onViewDetails={() => onAction?.('view_analysis')}
          />
        )

      case 'safety':
        return (
          <SafetyGuardianCard
            emergencyContacts={data?.emergencyContacts}
            safetyScore={data?.safetyScore}
            onAddContact={() => onAction?.('add_contact')}
            onEmergency={() => onAction?.('emergency')}
          />
        )

      case 'milestones':
        return (
          <MilestoneFeatureCard
            milestones={data?.milestones}
            partnerId={data?.partnerId}
            partnerName={data?.partnerName}
            onAddMilestone={() => onAction?.('add_milestone')}
            onViewAll={() => onAction?.('view_all_milestones')}
          />
        )

      // ========== AI 功能卡片（改用 Skill 调用）==========

      case 'deep_icebreaker':
        return (
          <DeepIcebreakerCard
            onTopicSelect={(topic) => onAction?.('select_topic', topic)}
          />
        )

      case 'message_interpretation':
        return (
          <MessageInterpretationCard
            messageContent={data?.messageContent || ''}
            messageId={data?.messageId || ''}
            partnerId={data?.partnerId || ''}
            onUseSuggestion={(suggestion) => onAction?.('use_suggestion', suggestion)}
          />
        )

      case 'joint_activity':
        return (
          <JointActivityCard
            userProfile={data?.userProfile}
            partnerProfile={data?.partnerProfile}
            onActivitySelect={(activity) => onAction?.('select_activity', activity)}
          />
        )

      case 'stress_test':
        return (
          <StressTestCard
            userId={authStorage.getUserId()}
            partnerId={data?.partnerId || ''}
            onComplete={(summary) => onAction?.('stress_test_complete', summary)}
          />
        )

      case 'your_turn':
        return (
          <YourTurnFeatureCard
            pendingReminders={data?.pendingReminders}
            onMarkReplied={(matchId) => onAction?.('mark_replied', matchId)}
          />
        )

      case 'matching_preference':
        return (
          <MatchingPreferenceCard
            currentPreferences={data?.preferences}
            onSave={(prefs) => onAction?.('save_preferences', prefs)}
          />
        )

      case 'date_reminder':
        return (
          <DateReminderCard
            reminders={data?.reminders}
            onCreateReminder={() => onAction?.('create_reminder')}
          />
        )

      case 'video_clip':
        return (
          <VideoClipCard
            clips={data?.clips}
            onRecord={() => onAction?.('record_clip')}
          />
        )

      default:
        return (
          <Card>
            <Empty description="功能开发中，敬请期待..." />
          </Card>
        )
    }
  }, [featureAction, data?.verifyStatus, data?.currentPlan, data?.gifts, data?.score, data?.stage, data?.suggestions, data?.emergencyContacts, data?.safetyScore, data?.milestones, data?.partnerId, data?.partnerName, onAction])

  return renderedCard
})

export default FeatureCardRenderer