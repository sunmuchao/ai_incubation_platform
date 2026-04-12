/**
 * 视频片段组件
 *
 * 参考 Tinder 的视频片段功能：
 * - 用户录制短视频自我介绍
 * - 视频作为匹配资料的一部分
 * - AI 生成介绍建议
 */

import React, { useState, useEffect, useRef } from 'react'
import { Modal, Button, Space, Typography, Card, List, Tag, Avatar, message, Divider, Progress, Spin } from 'antd'
import {
  VideoCameraOutlined, PlayCircleOutlined, DeleteOutlined, StarFilled,
  CheckCircleOutlined, ClockCircleOutlined, BulbOutlined, ReloadOutlined
} from '@ant-design/icons'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'
const GOLD_COLOR = '#FFD700'

// 视频配置
const VIDEO_CONFIG = {
  maxDuration: 30,
  maxSize: 50,  // MB
  allowedFormats: ['mp4', 'mov', 'webm', 'avi'],
  recommendedDuration: 15
}

interface VideoClip {
  video_id: string
  user_id: string
  video_url: string
  video_thumbnail?: string
  video_duration: number
  video_description?: string
  is_primary: boolean
  view_count: number
  created_at: string
}

interface IntroSuggestion {
  style: string
  outline: string
  filming_tips: string
  expected_effect: string
}

interface VideoClipManagerProps {
  visible: boolean
  userId: string
  onClose: () => void
  onVideoUploaded?: (video: VideoClip) => void
  onPrimaryChanged?: (videoId: string) => void
}

/**
 * 视频片段管理组件
 */
const VideoClipManager: React.FC<VideoClipManagerProps> = ({
  visible,
  userId,
  onClose,
  onVideoUploaded,
  onPrimaryChanged
}) => {
  const [videos, setVideos] = useState<VideoClip[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [recordedDuration, setRecordedDuration] = useState(0)
  const [suggestions, setSuggestions] = useState<IntroSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  // 视频播放器引用
  const videoRef = useRef<HTMLVideoElement>(null)

  // 加载视频列表
  useEffect(() => {
    if (visible && userId) {
      loadVideos()
      loadSuggestions()
    }
  }, [visible, userId])

  const loadVideos = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/video-clips/user/${userId}?limit=10`)
      if (response.ok) {
        const data = await response.json()
        setVideos(data)
      }
    } catch (error) {
      // 静默失败
    } finally {
      setLoading(false)
    }
  }

  const loadSuggestions = async () => {
    try {
      const response = await fetch(`/api/video-clips/intro-suggestions/${userId}`)
      if (response.ok) {
        const data = await response.json()
        setSuggestions(data)
      }
    } catch (error) {
      // 静默失败
    }
  }

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // 检查文件格式
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!VIDEO_CONFIG.allowedFormats.includes(ext || '')) {
      message.error(`不支持的视频格式，允许: ${VIDEO_CONFIG.allowedFormats.join(', ')}`)
      return
    }

    // 检查文件大小
    if (file.size > VIDEO_CONFIG.maxSize * 1024 * 1024) {
      message.error(`视频文件过大（最大 ${VIDEO_CONFIG.maxSize}MB）`)
      return
    }

    setUploading(true)
    try {
      // 上传视频
      const formData = new FormData()
      formData.append('video', file)

      // 获取视频时长（需要前端处理）
      const duration = await getVideoDuration(file)

      const response = await fetch(`/api/video-clips/upload?user_id=${userId}&video_duration=${duration}`, {
        method: 'POST',
        body: formData
      })

      if (response.ok) {
        const data = await response.json()
        message.success('视频上传成功')
        loadVideos()
        if (onVideoUploaded) {
          onVideoUploaded(data)
        }
      } else {
        const error = await response.json()
        message.error(error.detail || '上传失败')
      }
    } catch (error) {
      message.error('上传失败')
    } finally {
      setUploading(false)
      // 清空 input
      event.target.value = ''
    }
  }

  const getVideoDuration = async (file: File): Promise<number> => {
    return new Promise((resolve) => {
      const video = document.createElement('video')
      video.preload = 'metadata'
      video.onloadedmetadata = () => {
        resolve(video.duration)
      }
      video.src = URL.createObjectURL(file)
    })
  }

  const handleSetPrimary = async (videoId: string) => {
    try {
      const response = await fetch(`/api/video-clips/set-primary?user_id=${userId}&video_id=${videoId}`, {
        method: 'POST'
      })

      if (response.ok) {
        message.success('主要视频已设置')
        loadVideos()
        if (onPrimaryChanged) {
          onPrimaryChanged(videoId)
        }
      } else {
        message.error('设置失败')
      }
    } catch (error) {
      message.error('设置失败')
    }
  }

  const handleDelete = async (videoId: string) => {
    try {
      const response = await fetch(`/api/video-clips/${videoId}?user_id=${userId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        message.success('视频已删除')
        loadVideos()
      } else {
        message.error('删除失败')
      }
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handlePlayVideo = (videoUrl: string) => {
    if (videoRef.current) {
      videoRef.current.src = videoUrl
      videoRef.current.play()
    }
  }

  // 渲染介绍建议
  const renderSuggestions = () => {
    if (suggestions.length === 0) return null

    return (
      <div style={{ marginBottom: 16 }}>
        <Divider orientation="left" style={{ fontSize: 12 }}>
          <BulbOutlined style={{ color: '#FFD700' }} /> AI 介绍建议
        </Divider>
        <List
          size="small"
          dataSource={suggestions}
          renderItem={(suggestion) => (
            <Card
              size="small"
              style={{
                marginBottom: 8,
                borderRadius: 12,
              }}
            >
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Tag color={suggestion.style === 'natural' ? 'blue' : suggestion.style === 'light' ? 'green' : 'purple'}>
                  {suggestion.style === 'natural' ? '自然风格' : suggestion.style === 'light' ? '轻松风格' : '深度风格'}
                </Tag>
                <Text strong>介绍大纲：</Text>
                <Text>{suggestion.outline}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  拍摄建议：{suggestion.filming_tips}
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  预期效果：{suggestion.expected_effect}
                </Text>
              </Space>
            </Card>
          )}
        />
      </div>
    )
  }

  // 渲染视频列表
  const renderVideoList = () => {
    if (loading) {
      return <Spin size="small" tip="加载视频..." />
    }

    if (videos.length === 0) {
      return (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <VideoCameraOutlined style={{ fontSize: 48, color: '#ccc' }} />
          <Text type="secondary" style={{ marginTop: 16, display: 'block' }}>
            还没有上传视频
          </Text>
          <Paragraph type="secondary" style={{ fontSize: 12 }}>
            录制一段短视频介绍自己，增加真实感
          </Paragraph>
        </div>
      )
    }

    return (
      <List
        dataSource={videos}
        renderItem={(video) => (
          <Card
            size="small"
            style={{
              marginBottom: 8,
              borderRadius: 12,
              border: video.is_primary ? `2px solid ${GOLD_COLOR}` : '1px solid #f0f0f0',
            }}
          >
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                {/* 视频缩略图 */}
                <div
                  onClick={() => handlePlayVideo(video.video_url)}
                  style={{
                    width: 60,
                    height: 60,
                    borderRadius: 8,
                    overflow: 'hidden',
                    cursor: 'pointer',
                    background: '#f0f0f0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {video.video_thumbnail ? (
                    <img src={video.video_thumbnail} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  ) : (
                    <PlayCircleOutlined style={{ fontSize: 24, color: PRIMARY_COLOR }} />
                  )}
                </div>

                <Space direction="vertical" size={0}>
                  <Text strong style={{ fontSize: 14 }}>
                    {video.video_description || '我的视频'}
                  </Text>
                  <Space size={4}>
                    <ClockCircleOutlined style={{ fontSize: 12, color: '#999' }} />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {Math.round(video.video_duration)}秒
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      | {video.view_count} 次观看
                    </Text>
                  </Space>
                </Space>
              </Space>

              <Space>
                {video.is_primary ? (
                  <Tag color="gold" icon={<StarFilled />}>主要</Tag>
                ) : (
                  <Button
                    type="text"
                    size="small"
                    icon={<StarFilled style={{ color: '#999' }} />}
                    onClick={() => handleSetPrimary(video.video_id)}
                    title="设为主要视频"
                  />
                )}
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleDelete(video.video_id)}
                  disabled={video.is_primary && videos.length === 1}
                />
              </Space>
            </Space>
          </Card>
        )}
      />
    )
  }

  return (
    <Modal
      title={
        <Space>
          <VideoCameraOutlined style={{ color: PRIMARY_COLOR }} />
          <span>视频片段管理</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="suggestions" onClick={() => setShowSuggestions(!showSuggestions)}>
          {showSuggestions ? '隐藏建议' : '查看建议'}
        </Button>,
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={500}
      styles={{
        body: { padding: 16 }
      }}
    >
      {/* 配置提示 */}
      <div style={{
        padding: 12,
        background: 'rgba(200, 139, 139, 0.08)',
        borderRadius: 12,
        marginBottom: 16
      }}>
        <Space split={<Text type="secondary">|</Text>}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <ClockCircleOutlined /> 最大 {VIDEO_CONFIG.maxDuration}秒
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            推荐 {VIDEO_CONFIG.recommendedDuration}秒
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            格式: {VIDEO_CONFIG.allowedFormats.join(',')}
          </Text>
        </Space>
      </div>

      {/* 上传按钮 */}
      <div style={{ marginBottom: 16 }}>
        <input
          type="file"
          accept="video/*"
          onChange={handleUpload}
          style={{ display: 'none' }}
          id="video-upload-input"
        />
        <Button
          type="primary"
          icon={<VideoCameraOutlined />}
          loading={uploading}
          onClick={() => document.getElementById('video-upload-input')?.click()}
          style={{ background: PRIMARY_COLOR, borderColor: PRIMARY_COLOR, width: '100%' }}
        >
          上传视频
        </Button>
      </div>

      {/* AI 建议 */}
      {showSuggestions && renderSuggestions()}

      <Divider />

      {/* 视频列表 */}
      <div>
        <Text strong style={{ marginBottom: 8, display: 'block' }}>
          我的视频 ({videos.length})
        </Text>
        {renderVideoList()}
      </div>

      {/* 隐藏的视频播放器 */}
      <video ref={videoRef} style={{ display: 'none' }} controls />
    </Modal>
  )
}

/**
 * 视频片段展示组件（放在 MatchCard 中）
 */
interface VideoClipDisplayProps {
  videoUrl: string
  videoThumbnail?: string
  videoDuration: number
  onView?: () => void
}

export const VideoClipDisplay: React.FC<VideoClipDisplayProps> = ({
  videoUrl,
  videoThumbnail,
  videoDuration,
  onView
}) => {
  const [playing, setPlaying] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  const handlePlay = () => {
    if (videoRef.current) {
      if (playing) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
        if (onView) {
          onView()
        }
      }
      setPlaying(!playing)
    }
  }

  return (
    <div
      onClick={handlePlay}
      style={{
        position: 'relative',
        width: '100%',
        borderRadius: 12,
        overflow: 'hidden',
        background: '#f0f0f0',
        cursor: 'pointer',
      }}
    >
      {videoThumbnail ? (
        <img src={videoThumbnail} style={{ width: '100%', height: 'auto' }} />
      ) : (
        <div style={{
          height: 120,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <PlayCircleOutlined style={{ fontSize: 48, color: PRIMARY_COLOR }} />
        </div>
      )}

      {/* 视频时长标签 */}
      <Tag
        style={{
          position: 'absolute',
          bottom: 8,
          right: 8,
          background: 'rgba(0, 0, 0, 0.6)',
          color: '#fff',
        }}
      >
        <ClockCircleOutlined /> {Math.round(videoDuration)}秒
      </Tag>

      {/* 实际视频 */}
      <video
        ref={videoRef}
        src={videoUrl}
        style={{
          width: '100%',
          display: playing ? 'block' : 'none',
        }}
        controls
        onEnded={() => setPlaying(false)}
      />
    </div>
  )
}

export default VideoClipManager