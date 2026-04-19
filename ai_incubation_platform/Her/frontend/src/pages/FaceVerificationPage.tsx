/**
 * 人脸认证页面
 *
 * 参考 Tinder Blue Star 认证流程：
 * 1. 介绍认证好处
 * 2. 拍摄人脸照片
 * 3. 确认并提交
 * 4. 显示认证结果和徽章
 *
 * AI Native 设计原则：
 * - 用户在页面直接操作，无需跳转
 * - 实时反馈认证进度
 * - 认证成功立即展示徽章
 */

import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Card,
  Steps,
  Button,
  Typography,
  Space,
  Progress,
  Tag,
  Alert,
  Spin,
  Empty,
  Result,
  Divider,
  message,
  Modal,
} from 'antd'
import {
  CameraOutlined,
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  StarFilled,
  ArrowLeftOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  TrophyOutlined,
} from '@ant-design/icons'

import faceVerificationApi, {
  VerificationStatusResponse,
  FaceVerificationResponse,
  VerificationMethod,
} from '@/api/faceVerificationApi'
import './FaceVerificationPage.less'

const { Title, Text, Paragraph } = Typography

// ============================================
// 人脸认证页面
// ============================================

interface FaceVerificationPageProps {
  onBack?: () => void
  onComplete?: (badge: any) => void
}

const FaceVerificationPage: React.FC<FaceVerificationPageProps> = ({ onBack, onComplete }) => {
  // 状态
  const [loading, setLoading] = useState(true)
  const [currentStep, setCurrentStep] = useState(0)
  const [status, setStatus] = useState<VerificationStatusResponse | null>(null)
  const [methods, setMethods] = useState<VerificationMethod[]>([])
  const [selectedMethod, setSelectedMethod] = useState<string>('id_card_compare')

  // 摄像头状态
  const [cameraActive, setCameraActive] = useState(false)
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // 认证结果
  const [verificationResult, setVerificationResult] = useState<FaceVerificationResponse | null>(null)

  // 摄像头引用
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  // 加载初始数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [statusRes, methodsRes] = await Promise.all([
        faceVerificationApi.getVerificationStatus(),
        faceVerificationApi.getVerificationMethods(),
      ])

      setStatus(statusRes)
      setMethods(methodsRes.methods || [])

      // 如果已认证，直接显示结果
      if (statusRes.face_verified) {
        setCurrentStep(3)
      }
    } catch (error) {
      console.error('Failed to load verification data:', error)
      message.error('加载认证数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 清理摄像头
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  // 启动摄像头
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
      })

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      streamRef.current = stream
      setCameraActive(true)
    } catch (error) {
      console.error('Camera access failed:', error)
      message.error('无法访问摄像头，请检查权限设置')
    }
  }

  // 停止摄像头
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    setCameraActive(false)
  }

  // 拍照
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')

    if (!ctx) return

    // 设置 canvas 尺寸与视频一致
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // 绘制视频帧到 canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    // 获取 Base64 图片
    const photoBase64 = canvas.toDataURL('image/jpeg', 0.8).split(',')[1]
    setCapturedPhoto(photoBase64)

    // 停止摄像头
    stopCamera()

    // 进入确认步骤
    setCurrentStep(2)
  }

  // 重新拍照
  const retakePhoto = () => {
    setCapturedPhoto(null)
    setCurrentStep(1)
    startCamera()
  }

  // 提交认证
  const submitVerification = async () => {
    if (!capturedPhoto) {
      message.error('请先拍摄照片')
      return
    }

    setSubmitting(true)
    try {
      // 先开始认证流程
      await faceVerificationApi.startVerification(selectedMethod as any)

      // 提交照片
      const result = await faceVerificationApi.submitVerification(
        capturedPhoto,
        selectedMethod as any
      )

      setVerificationResult(result)

      if (result.success) {
        setCurrentStep(3)
        message.success('人脸认证成功！')
        onComplete?.({
          type: result.badge_type,
          icon: '⭐',
        })
      } else {
        message.error(result.message || '认证失败，请重试')
      }
    } catch (error: any) {
      console.error('Verification failed:', error)
      message.error(error.message || '认证失败，请重试')
      setVerificationResult({
        success: false,
        message: error.message || '认证失败',
        status: 'failed',
      })
    } finally {
      setSubmitting(false)
    }
  }

  // 重试认证
  const retryVerification = async () => {
    try {
      const result = await faceVerificationApi.retryVerification()
      if (result.success) {
        setCapturedPhoto(null)
        setVerificationResult(null)
        setCurrentStep(1)
        startCamera()
      } else {
        message.error(result.message)
      }
    } catch (error: any) {
      message.error(error.message || '重试失败')
    }
  }

  // 加载中状态
  if (loading) {
    return (
      <div className="face-verification-page loading">
        <Spin size="large" tip="正在加载认证数据...">
          <div style={{ padding: 50 }} />
        </Spin>
      </div>
    )
  }

  // 步骤配置
  const stepItems = [
    { title: '介绍', icon: <InfoCircleOutlined /> },
    { title: '拍照', icon: <CameraOutlined /> },
    { title: '确认', icon: <CheckCircleOutlined /> },
    { title: '完成', icon: <SafetyCertificateOutlined /> },
  ]

  return (
    <div className="face-verification-page">
      {/* 返回按钮 */}
      {onBack && (
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={onBack}
          style={{ marginBottom: 16 }}
        >
          返回
        </Button>
      )}

      {/* 页面头部 */}
      <div className="page-header">
        <Title level={3}>人脸认证</Title>
        <Text type="secondary">完成认证获得专属徽章，提升可信度</Text>
      </div>

      {/* 认证步骤 */}
      <div className="verification-steps">
        <Steps current={currentStep} items={stepItems} />
      </div>

      {/* 页面内容 */}
      <div className="page-content">
        {/* 步骤 0：介绍 */}
        {currentStep === 0 && (
          <div className="step-content">
            <StepIntro
              status={status}
              methods={methods}
              selectedMethod={selectedMethod}
              onMethodChange={setSelectedMethod}
              onStart={() => {
                setCurrentStep(1)
                startCamera()
              }}
            />
          </div>
        )}

        {/* 步骤 1：拍照 */}
        {currentStep === 1 && (
          <div className="step-content">
            <StepCapture
              videoRef={videoRef}
              canvasRef={canvasRef}
              cameraActive={cameraActive}
              onCapture={capturePhoto}
              onCancel={() => {
                stopCamera()
                setCurrentStep(0)
              }}
            />
          </div>
        )}

        {/* 步骤 2：确认 */}
        {currentStep === 2 && (
          <div className="step-content">
            <StepConfirm
              capturedPhoto={capturedPhoto}
              submitting={submitting}
              onConfirm={submitVerification}
              onRetake={retakePhoto}
            />
          </div>
        )}

        {/* 步骤 3：完成 */}
        {currentStep === 3 && (
          <div className="step-content">
            <StepComplete
              status={status}
              result={verificationResult}
              onRetry={retryVerification}
              onBack={onBack}
            />
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================
// 步骤 0：介绍组件
// ============================================

interface StepIntroProps {
  status: VerificationStatusResponse | null
  methods: VerificationMethod[]
  selectedMethod: string
  onMethodChange: (method: string) => void
  onStart: () => void
}

const StepIntro: React.FC<StepIntroProps> = ({
  status,
  methods,
  selectedMethod,
  onMethodChange,
  onStart,
}) => {
  return (
    <div className="step-intro">
      {/* 介绍头部 */}
      <div className="intro-header">
        <SafetyCertificateOutlined className="intro-icon" />
        <Title level={4}>人脸认证</Title>
      </div>

      {/* 徽章预览 */}
      <div className="badge-preview">
        <Text type="secondary" className="preview-label">
          认证成功后获得
        </Text>
        <Tag color="#1890ff" style={{ fontSize: 16, padding: '8px 16px' }}>
          <StarFilled style={{ marginRight: 4 }} />
          蓝星认证
        </Tag>
      </div>

      {/* 认证好处 */}
      <div className="verification-benefits">
        <Card size="small" className="benefit-card">
          <TrophyOutlined className="benefit-icon" />
          <Text>获得认证徽章，展示真实身份</Text>
        </Card>
        <Card size="small" className="benefit-card">
          <CheckCircleOutlined className="benefit-icon" />
          <Text>匹配成功率提升 30%</Text>
        </Card>
        <Card size="small" className="benefit-card">
          <SafetyCertificateOutlined className="benefit-icon" />
          <Text>建立信任，获得更多关注</Text>
        </Card>
      </div>

      {/* 认证方式选择 */}
      {methods.length > 0 && (
        <Card size="small" style={{ marginTop: 16, width: '100%' }}>
          <Text strong>选择认证方式</Text>
          <div style={{ marginTop: 8 }}>
            {methods.map((method) => (
              <Button
                key={method.type}
                type={selectedMethod === method.type ? 'primary' : 'default'}
                block
                style={{ marginBottom: 8 }}
                onClick={() => onMethodChange(method.type)}
              >
                {method.name}
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                  ({method.estimated_time})
                </Text>
              </Button>
            ))}
          </div>
        </Card>
      )}

      {/* 当前认证状态 */}
      {status?.face_verified && (
        <Alert
          type="success"
          showIcon
          message="您已完成人脸认证"
          description={`认证时间：${status.face_verification_date ? new Date(status.face_verification_date).toLocaleDateString() : '未知'}`}
          style={{ marginTop: 16, width: '100%' }}
        />
      )}

      {/* 开始按钮 */}
      {!status?.face_verified && (
        <Button
          type="primary"
          size="large"
          icon={<CameraOutlined />}
          onClick={onStart}
          className="start-btn"
        >
          开始认证
        </Button>
      )}
    </div>
  )
}

// ============================================
// 步骤 1：拍照组件
// ============================================

interface StepCaptureProps {
  videoRef: React.RefObject<HTMLVideoElement>
  canvasRef: React.RefObject<HTMLCanvasElement>
  cameraActive: boolean
  onCapture: () => void
  onCancel: () => void
}

const StepCapture: React.FC<StepCaptureProps> = ({
  videoRef,
  canvasRef,
  cameraActive,
  onCapture,
  onCancel,
}) => {
  return (
    <div className="step-capture">
      {/* 摄像头容器 */}
      <div className="camera-container">
        <video
          ref={videoRef}
          className="camera-video"
          autoPlay
          playsInline
          muted
        />
        <canvas ref={canvasRef} className="camera-canvas" />

        {/* 摄像头未启动时的占位 */}
        {!cameraActive && (
          <div className="camera-placeholder">
            <CameraOutlined className="placeholder-icon" />
            <Text>正在启动摄像头...</Text>
          </div>
        )}
      </div>

      {/* 拍照提示 */}
      <div className="capture-tips">
        <InfoCircleOutlined style={{ color: '#1890ff' }} />
        <Text>请将面部置于画面中央，保持光线充足</Text>
      </div>

      {/* 操作按钮 */}
      <div className="capture-actions">
        <Button onClick={onCancel}>取消</Button>
        <Button
          type="primary"
          icon={<CameraOutlined />}
          onClick={onCapture}
          disabled={!cameraActive}
        >
          拍照
        </Button>
      </div>
    </div>
  )
}

// ============================================
// 步骤 2：确认组件
// ============================================

interface StepConfirmProps {
  capturedPhoto: string | null
  submitting: boolean
  onConfirm: () => void
  onRetake: () => void
}

const StepConfirm: React.FC<StepConfirmProps> = ({
  capturedPhoto,
  submitting,
  onConfirm,
  onRetake,
}) => {
  return (
    <div className="step-confirm">
      {/* 照片预览 */}
      <div className="photo-preview">
        {capturedPhoto ? (
          <img
            src={`data:image/jpeg;base64,${capturedPhoto}`}
            alt="Captured photo"
            className="preview-image"
          />
        ) : (
          <Empty description="未拍摄照片" />
        )}
      </div>

      {/* 确认提示 */}
      <Text type="secondary">请确认照片清晰、面部完整可见</Text>

      {/* 操作按钮 */}
      <div className="confirm-actions">
        <Button onClick={onRetake} disabled={submitting}>
          重新拍摄
        </Button>
        <Button
          type="primary"
          icon={<CheckCircleOutlined />}
          loading={submitting}
          onClick={onConfirm}
        >
          提交认证
        </Button>
      </div>
    </div>
  )
}

// ============================================
// 步骤 3：完成组件
// ============================================

interface StepCompleteProps {
  status: VerificationStatusResponse | null
  result: FaceVerificationResponse | null
  onRetry: () => void
  onBack?: () => void
}

const StepComplete: React.FC<StepCompleteProps> = ({
  status,
  result,
  onRetry,
  onBack,
}) => {
  const isSuccess = result?.success || status?.face_verified

  if (isSuccess) {
    // 成功状态
    const badgeConfig = {
      blue_star: { icon: '⭐', color: '#1890ff', name: '蓝星认证' },
      gold_star: { icon: '🌟', color: '#faad14', name: '金星认证' },
      platinum_star: { icon: '✨', color: '#95de64', name: '铂金星认证' },
      diamond_star: { icon: '💎', color: '#D4A59A', name: '钻石星认证' },
    }

    const badgeType = result?.badge_type || status?.current_badge || 'blue_star'
    const badge = badgeConfig[badgeType as keyof typeof badgeConfig] || badgeConfig.blue_star

    return (
      <div className="step-complete">
        <Result
          status="success"
          icon={<SafetyCertificateOutlined style={{ color: badge.color }} />}
          title="人脸认证成功！"
          subTitle={`您已获得 ${badge.name}`}
          extra={[
            <Button type="primary" key="done" onClick={onBack}>
              完成
            </Button>,
          ]}
        />

        {/* 徽章展示 */}
        <Card className="badge-display" variant="borderless">
          <div style={{ textAlign: 'center' }}>
            <Tag
              color={badge.color}
              style={{
                fontSize: 24,
                padding: '16px 32px',
                borderRadius: 16,
              }}
            >
              <span style={{ fontSize: 28 }}>{badge.icon}</span>
              <span style={{ marginLeft: 8 }}>{badge.name}</span>
            </Tag>
          </div>
        </Card>

        {/* 认证详情 */}
        {(result?.similarity_score || result?.liveness_score) && (
          <Card className="result-details" title="认证详情">
            {result?.similarity_score && (
              <div className="detail-item">
                <Text className="detail-label">相似度</Text>
                <Progress
                  percent={Math.round(result.similarity_score)}
                  strokeColor="#52c41a"
                />
              </div>
            )}
            {result?.liveness_score && (
              <div className="detail-item">
                <Text className="detail-label">活体检测</Text>
                <Progress
                  percent={Math.round(result.liveness_score)}
                  strokeColor="#1890ff"
                />
              </div>
            )}
          </Card>
        )}

        {/* 信任分展示 */}
        {status?.trust_score && (
          <Card className="trust-score-card" variant="borderless">
            <Space>
              <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
              <Text>当前信任分：<Text strong style={{ color: '#52c41a' }}>{status.trust_score}</Text></Text>
            </Space>
          </Card>
        )}
      </div>
    )
  } else {
    // 失败状态
    return (
      <div className="step-complete">
        <Result
          status="warning"
          icon={<WarningOutlined />}
          title="认证未通过"
          subTitle={result?.message || '请重新尝试认证'}
          extra={[
            <Button type="primary" key="retry" icon={<ReloadOutlined />} onClick={onRetry}>
              重新认证
            </Button>,
            <Button key="back" onClick={onBack}>
              返回
            </Button>,
          ]}
        />

        {/* 失败详情 */}
        {result?.failure_reason && (
          <Alert
            type="warning"
            showIcon
            message="失败原因"
            description={result.failure_reason}
            className="verification-failed"
          />
        )}
      </div>
    )
  }
}

export default FaceVerificationPage