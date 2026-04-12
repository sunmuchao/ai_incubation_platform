// FaceVerificationPage - 人脸认证页面
// 参考 Tinder Blue Star 认证流程

import React, { useState, useCallback, useEffect, useRef } from 'react'
import {
  Typography,
  Button,
  Steps,
  Card,
  Avatar,
  Progress,
  message,
  Result,
  Space,
  Modal,
  Spin,
} from 'antd'
import {
  CameraOutlined,
  CheckCircleOutlined,
  SafetyCertificateOutlined,
  InfoCircleOutlined,
  RedoOutlined,
  StarFilled,
} from '@ant-design/icons'
import VerificationBadge from '../components/VerificationBadge'
import { faceVerificationApi } from '../api/faceVerificationApi'
import { VERIFICATION_BADGE_CONFIG } from '../types/faceVerification'
import './FaceVerificationPage.less'

const { Text, Title, Paragraph } = Typography

interface FaceVerificationPageProps {
  onBack?: () => void
  onComplete?: (badgeType: string) => void
}

const FaceVerificationPage: React.FC<FaceVerificationPageProps> = ({
  onBack,
  onComplete,
}) => {
  // 状态
  const [loading, setLoading] = useState(true)
  const [currentStep, setCurrentStep] = useState(0)
  const [verificationStatus, setVerificationStatus] = useState<{
    face_verified: boolean
    current_badge?: string
    badge_display_icon?: string
    badge_display_name?: string
    trust_score: number
  } | null>(null)
  const [verificationId, setVerificationId] = useState<string | null>(null)
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [verificationResult, setVerificationResult] = useState<{
    success: boolean
    similarity_score?: number
    liveness_score?: number
    badge_type?: string
    message: string
  } | null>(null)

  // 视频流引用
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [cameraActive, setCameraActive] = useState(false)

  // 加载认证状态
  useEffect(() => {
    loadVerificationStatus()
  }, [])

  const loadVerificationStatus = useCallback(async () => {
    setLoading(true)
    try {
      const status = await faceVerificationApi.getStatus()
      setVerificationStatus(status)

      if (status.face_verified) {
        setCurrentStep(3) // 已完成认证
      }
    } catch (error) {
      console.error('Failed to load verification status:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // 开始认证流程
  const handleStartVerification = useCallback(async () => {
    try {
      const result = await faceVerificationApi.startVerification('id_card_compare')

      if (result.success) {
        setVerificationId(result.verification_id)
        setCurrentStep(1)
        message.success('认证流程已开始')
      } else {
        message.error(result.message)
      }
    } catch (error: any) {
      message.error(error?.message || '开始认证失败')
    }
  }, [])

  // 启动摄像头
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: 640, height: 480 },
      })

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
        setCameraActive(true)
      }
    } catch (error) {
      message.error('无法访问摄像头，请检查权限设置')
      console.error('Camera error:', error)
    }
  }, [])

  // 停止摄像头
  const stopCamera = useCallback(() => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream
      stream.getTracks().forEach((track) => track.stop())
      videoRef.current.srcObject = null
      setCameraActive(false)
    }
  }, [])

  // 拍照
  const handleCapturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')

    if (!context) return

    // 设置画布尺寸
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // 绘制视频帧到画布
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    // 获取 Base64 图片数据
    const photoBase64 = canvas.toDataURL('image/jpeg', 0.8)
    setCapturedPhoto(photoBase64)

    // 停止摄像头
    stopCamera()
    setCurrentStep(2)
  }, [stopCamera])

  // 重拍
  const handleRetake = useCallback(() => {
    setCapturedPhoto(null)
    setCurrentStep(1)
    startCamera()
  }, [startCamera])

  // 提交认证
  const handleSubmit = useCallback(async () => {
    if (!capturedPhoto) {
      message.error('请先拍照')
      return
    }

    setSubmitting(true)

    try {
      // 移除 Base64 前缀
      const photoBase64 = capturedPhoto.split(',')[1]

      const result = await faceVerificationApi.submitPhoto({
        photo_base64: photoBase64,
        method: 'id_card_compare',
      })

      setVerificationResult({
        success: result.success,
        similarity_score: result.similarity_score,
        liveness_score: result.liveness_score,
        badge_type: result.badge_type,
        message: result.message,
      })

      if (result.success) {
        setCurrentStep(3)
        message.success('人脸认证成功！')

        // 更新状态
        await loadVerificationStatus()

        // 回调
        if (result.badge_type) {
          onComplete?.(result.badge_type)
        }
      } else {
        message.error(result.message)
      }
    } catch (error: any) {
      message.error(error?.message || '提交认证失败')
    } finally {
      setSubmitting(false)
    }
  }, [capturedPhoto, loadVerificationStatus, onComplete])

  // 渲染步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        // 步骤 0：介绍和开始
        return (
          <div className="step-intro">
            <div className="intro-header">
              <SafetyCertificateOutlined className="intro-icon" />
              <Title level={4}>人脸认证</Title>
            </div>

            <Paragraph className="intro-desc">
              完成人脸认证后，您的资料将展示认证徽章，增加可信度，获得更多匹配机会。
            </Paragraph>

            <div className="badge-preview">
              <Text className="preview-label">认证后可获得：</Text>
              <VerificationBadge badgeType="blue_star" showText />
            </div>

            <div className="verification-benefits">
              <Card className="benefit-card">
                <CheckCircleOutlined className="benefit-icon" />
                <Text>提升可信度，获得 Blue Star 徽章</Text>
              </Card>
              <Card className="benefit-card">
                <StarFilled className="benefit-icon" />
                <Text>优先展示，更多匹配机会</Text>
              </Card>
              <Card className="benefit-card">
                <SafetyCertificateOutlined className="benefit-icon" />
                <Text>增加信任分，解锁更多功能</Text>
              </Card>
            </div>

            <Button
              type="primary"
              size="large"
              icon={<CameraOutlined />}
              onClick={handleStartVerification}
              className="start-btn"
            >
              开始认证
            </Button>
          </div>
        )

      case 1:
        // 步骤 1：拍照
        return (
          <div className="step-capture">
            <Title level={5}>请拍摄清晰的人脸照片</Title>

            <div className="camera-container">
              <video
                ref={videoRef}
                className="camera-video"
                autoPlay
                playsInline
                muted
              />
              <canvas ref={canvasRef} className="camera-canvas" style={{ display: 'none' }} />

              {!cameraActive && (
                <div className="camera-placeholder">
                  <CameraOutlined className="placeholder-icon" />
                  <Text>点击下方按钮启动摄像头</Text>
                </div>
              )}
            </div>

            <div className="capture-tips">
              <InfoCircleOutlined />
              <Text type="secondary">
                请确保光线充足、正脸拍摄、无遮挡
              </Text>
            </div>

            <div className="capture-actions">
              {!cameraActive ? (
                <Button
                  type="primary"
                  size="large"
                  icon={<CameraOutlined />}
                  onClick={startCamera}
                >
                  启动摄像头
                </Button>
              ) : (
                <Button
                  type="primary"
                  size="large"
                  icon={<CameraOutlined />}
                  onClick={handleCapturePhoto}
                >
                  拍照
                </Button>
              )}
            </div>
          </div>
        )

      case 2:
        // 步骤 2：确认并提交
        return (
          <div className="step-confirm">
            <Title level={5}>确认照片</Title>

            <div className="photo-preview">
              {capturedPhoto && (
                <img src={capturedPhoto} alt="Captured photo" className="preview-image" />
              )}
            </div>

            <div className="confirm-actions">
              <Button
                size="large"
                icon={<RedoOutlined />}
                onClick={handleRetake}
              >
                重拍
              </Button>
              <Button
                type="primary"
                size="large"
                icon={<CheckCircleOutlined />}
                loading={submitting}
                onClick={handleSubmit}
              >
                提交认证
              </Button>
            </div>

            {verificationResult && !verificationResult.success && (
              <div className="verification-failed">
                <Result
                  status="error"
                  title="认证失败"
                  subTitle={verificationResult.message}
                  extra={
                    <Button type="primary" onClick={() => faceVerificationApi.retryVerification()}>
                      重试认证
                    </Button>
                  }
                />
              </div>
            )}
          </div>
        )

      case 3:
        // 步骤 3：完成
        return (
          <div className="step-complete">
            <Result
              status="success"
              title="认证成功！"
              subTitle="您已获得认证徽章，资料将优先展示"
              extra={[
                <VerificationBadge
                  key="badge"
                  badgeType={verificationStatus?.current_badge || 'blue_star'}
                  showText
                  size="large"
                />,
                <Button key="back" type="primary" onClick={onBack}>
                  返回
                </Button>,
              ]}
            />

            {verificationResult?.similarity_score && (
              <Card className="result-details">
                <div className="detail-item">
                  <Text className="detail-label">人脸相似度</Text>
                  <Progress
                    percent={Math.round(verificationResult.similarity_score)}
                    strokeColor={{ '0%': '#1890ff', '100%': '#52c41a' }}
                  />
                </div>
                {verificationResult.liveness_score && (
                  <div className="detail-item">
                    <Text className="detail-label">活体检测</Text>
                    <Progress
                      percent={Math.round(verificationResult.liveness_score)}
                      strokeColor={{ '0%': '#faad14', '100%': '#52c41a' }}
                    />
                  </div>
                )}
                <div className="detail-item">
                  <Text className="detail-label">信任分</Text>
                  <Text className="detail-value">{verificationStatus?.trust_score || 0}</Text>
                </div>
              </Card>
            )}
          </div>
        )

      default:
        return null
    }
  }

  // 步骤配置
  const steps = [
    {
      title: '开始认证',
      icon: <SafetyCertificateOutlined />,
    },
    {
      title: '拍照',
      icon: <CameraOutlined />,
    },
    {
      title: '提交',
      icon: <CheckCircleOutlined />,
    },
    {
      title: '完成',
      icon: <StarFilled />,
    },
  ]

  if (loading) {
    return (
      <div className="face-verification-page loading">
        <Spin size="large" tip="加载认证状态..." />
      </div>
    )
  }

  // 已完成认证
  if (verificationStatus?.face_verified && currentStep === 3) {
    return (
      <div className="face-verification-page">
        <div className="page-header">
          <Title level={4}>认证状态</Title>
        </div>

        <div className="page-content">
          <Result
            status="success"
            title="您已完成认证"
            subTitle={`${verificationStatus.badge_display_name || '蓝星认证'} - 信任分：${verificationStatus.trust_score}`}
            extra={[
              <VerificationBadge
                key="badge"
                badgeType={verificationStatus.current_badge}
                showText
                size="large"
              />,
              <Button key="back" onClick={onBack}>
                返回
              </Button>,
            ]}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="face-verification-page">
      <div className="page-header">
        <Title level={4}>人脸认证</Title>
        <Text type="secondary">完成认证获得 Blue Star 徽章</Text>
      </div>

      <div className="page-content">
        {/* 进度步骤 */}
        <Steps
          current={currentStep}
          items={steps}
          className="verification-steps"
        />

        {/* 步骤内容 */}
        <div className="step-content">
          {renderStepContent()}
        </div>
      </div>
    </div>
  )
}

export default FaceVerificationPage