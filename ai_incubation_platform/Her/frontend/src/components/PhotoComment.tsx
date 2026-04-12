/**
 * 照片评论组件
 *
 * 参考 Hinge 的照片评论功能：
 * - 用户可以对照片发表评论
 * - 评论作为破冰话题
 * - AI 生成评论建议
 */

import React, { useState, useEffect } from 'react'
import { Modal, Button, Space, Typography, Card, Tag, List, Avatar, Input, message, Divider, Spin, Badge } from 'antd'
import {
  PictureOutlined, CommentOutlined, BulbOutlined, QuestionCircleOutlined,
  LikeOutlined, BookOutlined, SearchOutlined, SendOutlined, CopyOutlined, EyeOutlined
} from '@ant-design/icons'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'

// 评论类型配置
const COMMENT_TYPES = [
  { name: 'observation', description: '观察', icon: <SearchOutlined style={{ color: '#1890ff' }} />, example: '照片里的那只猫看起来好可爱！' },
  { name: 'question', description: '询问', icon: <QuestionCircleOutlined style={{ color: '#52c41a' }} />, example: '这是在哪里拍的？风景真美！' },
  { name: 'compliment', description: '赞美', icon: <LikeOutlined style={{ color: '#FFD700' }} />, example: '这张照片拍得太棒了！' },
  { name: 'shared_interest', description: '共同兴趣', icon: <BulbOutlined style={{ color: '#722ed1' }} />, example: '你也喜欢徒步吗？看起来我们兴趣相似！' },
  { name: 'story', description: '故事', icon: <BookOutlined style={{ color: '#fa8c16' }} />, example: '看到这张照片想起了我也去过那里...' },
]

interface CommentSuggestion {
  comment_type: string
  comment_content: string
  expected_effect: string
  confidence: number
  photo_id: string
  is_ai_generated: boolean
}

interface PhotoComment {
  comment_id: string
  photo_id: string
  user_id: string
  user_name: string
  user_avatar?: string
  comment_content: string
  comment_type: string
  is_ai_generated: boolean
  replies_count: number
  created_at: string
}

interface PhotoCommentModalProps {
  visible: boolean
  photoId: string
  photoOwnerId: string
  photoUrl: string
  photoDescription?: string
  userId: string
  onClose: () => void
  onCommentSent?: (comment: PhotoComment) => void
  onStartChat?: () => void
}

/**
 * 照片评论弹窗组件
 */
const PhotoCommentModal: React.FC<PhotoCommentModalProps> = ({
  visible,
  photoId,
  photoOwnerId,
  photoUrl,
  photoDescription,
  userId,
  onClose,
  onCommentSent,
  onStartChat
}) => {
  const [comments, setComments] = useState<PhotoComment[]>([])
  const [suggestions, setSuggestions] = useState<CommentSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [commentContent, setCommentContent] = useState('')
  const [selectedType, setSelectedType] = useState('observation')
  const [sending, setSending] = useState(false)

  // 加载已有评论
  useEffect(() => {
    if (visible && photoId) {
      loadComments()
      loadSuggestions()
    }
  }, [visible, photoId])

  const loadComments = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/photo-comments/photo/${photoId}?limit=20`)
      if (response.ok) {
        const data = await response.json()
        setComments(data)
      }
    } catch (error) {
      // 静默失败
    } finally {
      setLoading(false)
    }
  }

  const loadSuggestions = async () => {
    setLoadingSuggestions(true)
    try {
      const desc = photoDescription || '这是一张照片'
      const response = await fetch(`/api/photo-comments/suggestions/${photoId}?user_id=${userId}&photo_description=${encodeURIComponent(desc)}`)
      if (response.ok) {
        const data = await response.json()
        setSuggestions(data)
      }
    } catch (error) {
      // 静默失败，使用默认建议
      setSuggestions([
        {
          comment_type: 'question',
          comment_content: '这张照片是在哪里拍的？看起来很棒！',
          expected_effect: '引发地点讨论',
          confidence: 0.7,
          photo_id: photoId,
          is_ai_generated: true
        }
      ])
    } finally {
      setLoadingSuggestions(false)
    }
  }

  const handleSendComment = async () => {
    if (!commentContent.trim()) {
      message.warning('请输入评论内容')
      return
    }

    setSending(true)
    try {
      const response = await fetch(`/api/photo-comments/create?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          photo_id: photoId,
          photo_owner_id: photoOwnerId,
          comment_content: commentContent,
          comment_type: selectedType
        })
      })

      if (response.ok) {
        const data = await response.json()
        message.success('评论已发送')
        setCommentContent('')
        // 刷新评论列表
        loadComments()
        // 回调
        if (onCommentSent) {
          onCommentSent(data)
        }
      } else {
        message.error('发送失败')
      }
    } catch (error) {
      message.error('发送失败')
    } finally {
      setSending(false)
    }
  }

  const handleUseSuggestion = (suggestion: CommentSuggestion) => {
    setCommentContent(suggestion.comment_content)
    setSelectedType(suggestion.comment_type)
  }

  const handleStartChat = () => {
    if (onStartChat) {
      onStartChat()
    }
    onClose()
  }

  // 渲染照片
  const renderPhoto = () => {
    return (
      <div style={{
        position: 'relative',
        marginBottom: 16,
        borderRadius: 12,
        overflow: 'hidden'
      }}>
        <img
          src={photoUrl}
          alt="照片"
          style={{
            width: '100%',
            maxHeight: 300,
            objectFit: 'cover'
          }}
        />
      </div>
    )
  }

  // 渲染评论类型选择
  const renderTypeSelector = () => {
    return (
      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
          选择评论类型
        </Text>
        <Space wrap size="small">
          {COMMENT_TYPES.map(type => (
            <Tag
              key={type.name}
              color={selectedType === type.name ? PRIMARY_COLOR : 'default'}
              style={{
                cursor: 'pointer',
                borderRadius: 8,
                padding: '4px 12px',
              }}
              onClick={() => setSelectedType(type.name)}
            >
              {type.icon} {type.description}
            </Tag>
          ))}
        </Space>
      </div>
    )
  }

  // 渲染 AI 建议
  const renderSuggestions = () => {
    if (loadingSuggestions) {
      return <Spin size="small" tip="AI 正在生成建议..." />
    }

    if (suggestions.length === 0) return null

    return (
      <div style={{ marginBottom: 16 }}>
        <Divider orientation="left" style={{ fontSize: 12 }}>
          <BulbOutlined style={{ color: '#FFD700' }} /> AI 评论建议
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
                cursor: 'pointer',
              }}
              onClick={() => handleUseSuggestion(suggestion)}
              className="suggestion-card"
            >
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Tag color="blue" style={{ fontSize: 10 }}>
                    {COMMENT_TYPES.find(t => t.name === suggestion.comment_type)?.description || suggestion.comment_type}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 10 }}>
                    {Math.round(suggestion.confidence * 100)}% 匹配
                  </Text>
                </Space>
                <Text>{suggestion.comment_content}</Text>
                <Text type="secondary" style={{ fontSize: 10 }}>
                  效果：{suggestion.expected_effect}
                </Text>
              </Space>
            </Card>
          )}
        />
      </div>
    )
  }

  // 渲染已有评论
  const renderComments = () => {
    if (loading) {
      return <Spin size="small" />
    }

    if (comments.length === 0) {
      return (
        <div style={{ padding: 16, textAlign: 'center' }}>
          <Text type="secondary">暂无评论，成为第一个评论者吧！</Text>
        </div>
      )
    }

    return (
      <div style={{ marginBottom: 16 }}>
        <Divider orientation="left" style={{ fontSize: 12 }}>
          <CommentOutlined style={{ color: PRIMARY_COLOR }} /> 已有评论 ({comments.length})
        </Divider>
        <List
          size="small"
          dataSource={comments}
          renderItem={(comment) => (
            <div style={{
              padding: '8px 0',
              borderBottom: '1px solid #f0f0f0'
            }}>
              <Space>
                <Avatar size={32} src={comment.user_avatar} icon={<PictureOutlined />} />
                <div>
                  <Space>
                    <Text strong style={{ fontSize: 14 }}>{comment.user_name}</Text>
                    <Tag style={{ fontSize: 10 }}>
                      {COMMENT_TYPES.find(t => t.name === comment.comment_type)?.description || comment.comment_type}
                    </Tag>
                    {comment.is_ai_generated && <Badge count="AI" style={{ fontSize: 8 }} />}
                  </Space>
                  <Text style={{ fontSize: 13, marginLeft: 8 }}>{comment.comment_content}</Text>
                </div>
              </Space>
            </div>
          )}
        />
      </div>
    )
  }

  return (
    <Modal
      title={
        <Space>
          <CommentOutlined style={{ color: PRIMARY_COLOR }} />
          <span>照片评论</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="chat" type="default" icon={<CommentOutlined />} onClick={handleStartChat}>
          发起对话
        </Button>,
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="send"
          type="primary"
          icon={<SendOutlined />}
          loading={sending}
          onClick={handleSendComment}
          style={{ background: PRIMARY_COLOR, borderColor: PRIMARY_COLOR }}
        >
          发送评论
        </Button>,
      ]}
      width={500}
      styles={{
        body: { padding: 16 }
      }}
    >
      {/* 照片 */}
      {renderPhoto()}

      {/* AI 建议 */}
      {renderSuggestions()}

      <Divider />

      {/* 评论输入 */}
      <div>
        {renderTypeSelector()}
        <Input.TextArea
          value={commentContent}
          onChange={(e) => setCommentContent(e.target.value)}
          placeholder="写下你对这张照片的看法..."
          autoSize={{ minRows: 2, maxRows: 4 }}
          style={{ borderRadius: 12, marginBottom: 8 }}
        />
        <Text type="secondary" style={{ fontSize: 11 }}>
          💡 提示：真诚的评论更容易引发对话
        </Text>
      </div>

      <Divider />

      {/* 已有评论 */}
      {renderComments()}

      <style>{`
        .suggestion-card:hover {
          box-shadow: 0 2px 8px rgba(200, 139, 139, 0.15);
          transition: box-shadow 0.2s;
        }
      `}</style>
    </Modal>
  )
}

/**
 * 照片评论按钮（放在照片上）
 */
interface PhotoCommentButtonProps {
  photoId: string
  photoOwnerId: string
  photoUrl: string
  photoDescription?: string
  userId: string
  commentsCount?: number
  onCommentSent?: (comment: PhotoComment) => void
  onStartChat?: () => void
}

export const PhotoCommentButton: React.FC<PhotoCommentButtonProps> = ({
  photoId,
  photoOwnerId,
  photoUrl,
  photoDescription,
  userId,
  commentsCount = 0,
  onCommentSent,
  onStartChat
}) => {
  const [modalVisible, setModalVisible] = useState(false)

  return (
    <>
      <div
        onClick={() => setModalVisible(true)}
        style={{
          position: 'absolute',
          bottom: 8,
          right: 8,
          cursor: 'pointer',
          padding: '4px 12px',
          borderRadius: 16,
          background: 'rgba(255, 255, 255, 0.9)',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        }}
      >
        <Space size={4}>
          <CommentOutlined style={{ color: PRIMARY_COLOR }} />
          <Text style={{ fontSize: 12, color: PRIMARY_COLOR }}>{commentsCount}</Text>
        </Space>
      </div>
      <PhotoCommentModal
        visible={modalVisible}
        photoId={photoId}
        photoOwnerId={photoOwnerId}
        photoUrl={photoUrl}
        photoDescription={photoDescription}
        userId={userId}
        onClose={() => setModalVisible(false)}
        onCommentSent={onCommentSent}
        onStartChat={onStartChat}
      />
    </>
  )
}

export default PhotoCommentModal