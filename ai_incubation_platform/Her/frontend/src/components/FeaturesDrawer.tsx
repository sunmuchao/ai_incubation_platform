/**
 * 轻量级功能入口组件
 *
 * 设计原则：
 * 1. 只有一个图标入口，不占空间
 * 2. 点击弹出卡片列表，不是传统菜单
 * 3. 点击某功能后在对话区生成卡片，不跳转页面
 * 4. 视觉风格与 Her 整体玫瑰粉色系统一
 */

import React from 'react'
import { Drawer, List, Space, Typography, Divider, Badge } from 'antd'
import {
  GiftOutlined, PictureOutlined,
  VerifiedOutlined, CrownOutlined, HeartFilled, AppstoreOutlined, SwapOutlined,
  HeartOutlined, SettingOutlined,
  CalendarOutlined, VideoCameraOutlined, SafetyCertificateOutlined
} from '@ant-design/icons'

const { Text, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'
const PRIMARY_GRADIENT = 'linear-gradient(135deg, #D4A59A 0%, #C88B8B 100%)'

export interface Feature {
  icon: React.ReactNode
  name: string
  description: string
  action: string
  badge?: string // 可选徽章，如 "新" 或 "推荐"
}

// 功能列表定义 - 使用统一的图标风格
// 注意：AI 决策类功能（Skill 调用）不应在此列表中，由 AI 主动推送或对话触发
export const FEATURES: Feature[] = [
  // === 用户操作类功能（REST API）===
  {
    icon: <SwapOutlined style={{ color: '#52c41a', fontSize: 20 }} />,
    name: '滑动匹配',
    description: 'Tinder 式滑动浏览推荐',
    action: 'swipe',
    badge: '新'
  },
  {
    icon: <HeartOutlined style={{ color: '#FFD700', fontSize: 20 }} />,
    name: 'Who Likes Me',
    description: '查看喜欢你的人',
    action: 'who_likes_me',
    badge: '会员'
  },
  {
    icon: <PictureOutlined style={{ color: PRIMARY_COLOR, fontSize: 20 }} />,
    name: '照片管理',
    description: '上传和管理你的照片',
    action: 'photos',
    badge: '推荐'
  },
  {
    icon: <VerifiedOutlined style={{ color: '#1890ff', fontSize: 20 }} />,
    name: '人脸认证',
    description: '获得 Blue Star 徽章',
    action: 'face_verification',
    badge: '新'
  },
  {
    icon: <GiftOutlined style={{ color: PRIMARY_COLOR, fontSize: 20 }} />,
    name: '礼物商店',
    description: '送礼物表达心意',
    action: 'gifts',
    badge: '新'
  },
  {
    icon: <SettingOutlined style={{ color: '#1890ff', fontSize: 20 }} />,
    name: '匹配偏好',
    description: '设置你的匹配条件',
    action: 'matching_preference',
  },
  {
    icon: <CalendarOutlined style={{ color: '#fa8c16', fontSize: 20 }} />,
    name: '约会提醒',
    description: '管理约会计划',
    action: 'date_reminder',
  },
  {
    icon: <SafetyCertificateOutlined style={{ color: '#52c41a', fontSize: 20 }} />,
    name: '可信度管理',
    description: '查看你的置信度评估和验证建议',
    action: 'confidence',
    badge: '新'
  },
  {
    icon: <VideoCameraOutlined style={{ color: PRIMARY_COLOR, fontSize: 20 }} />,
    name: '视频片段',
    description: '录制短视频自我介绍',
    action: 'video_clip',
    badge: '新'
  },
  // === 会员相关 ===
  {
    icon: <CrownOutlined style={{ color: PRIMARY_COLOR, fontSize: 20 }} />,
    name: '会员订阅',
    description: '解锁更多高级功能',
    action: 'membership',
  },
  // === 记录类功能 ===
  {
    icon: <HeartFilled style={{ color: '#FF6B8A', fontSize: 20 }} />,
    name: '关系里程碑',
    description: '记录重要时刻',
    action: 'milestones'
  },
  // === 已移除的功能（改由 AI 主动推送或对话触发）===
  // Your Turn → chatAssistantSkill（对话中自动触发回复建议）
  // 消息解读 → chatAssistantSkill（对话中自动触发）
  // 破冰话题 → silenceBreakerSkill（沉默时 AI 主动推送）
  // 活动推荐 → activityDirectorSkill（约会时 AI 主动推送）
  // 压力测试 → relationshipCoachSkill（关系分析时 AI 建议）
  // 安全守护 → safetyGuardianSkill（危险检测时自动触发）
  // 关系分析 → relationshipCoachSkill（定期推送健康报告）
]

interface FeaturesDrawerProps {
  open: boolean
  onClose: () => void
  onFeatureSelect: (feature: Feature) => void
}

/**
 * 功能抽屉组件
 */
export const FeaturesDrawer: React.FC<FeaturesDrawerProps> = ({
  open,
  onClose,
  onFeatureSelect
}) => {
  return (
    <Drawer
      title={
        <Space style={{ color: '#fff' }}>
          <AppstoreOutlined style={{ color: '#fff' }} />
          <span style={{ color: '#fff' }}>我能帮你做的事</span>
        </Space>
      }
      placement="right"
      width={340}
      open={open}
      onClose={onClose}
      closable
      className="features-drawer"
      styles={{
        header: {
          background: PRIMARY_GRADIENT,
          borderBottom: 'none',
        }
      }}
    >
      <List
        dataSource={FEATURES}
        renderItem={(feature) => (
          <List.Item
            onClick={() => {
              onFeatureSelect(feature)
              onClose()
            }}
            style={{
              cursor: 'pointer',
              padding: '16px 0',
              borderBottom: '1px solid #f0f0f0'
            }}
            className="feature-item"
          >
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Space>
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 36,
                    height: 36,
                    borderRadius: 10,
                    background: 'rgba(200, 139, 139, 0.1)',
                  }}>
                    {feature.icon}
                  </span>
                  <Text strong style={{ fontSize: 15 }}>{feature.name}</Text>
                </Space>
                {feature.badge && (
                  <Badge
                    count={feature.badge}
                    style={{
                      backgroundColor: feature.badge === '新' ? '#52c41a'
                        : feature.badge === 'AI' ? '#722ed1'
                        : feature.badge === '会员' ? '#FFD700'
                        : PRIMARY_COLOR
                    }}
                  />
                )}
              </Space>
              <Text type="secondary" style={{ fontSize: 13, marginLeft: 44 }}>
                {feature.description}
              </Text>
            </Space>
          </List.Item>
        )}
      />

      <Divider />

      <div style={{ padding: '8px 0' }}>
        <Paragraph type="secondary" style={{ fontSize: 12, margin: 0 }}>
          💡 小提示：我会主动提醒你使用这些功能，无需刻意来找
        </Paragraph>
      </div>

      <style>{`
        .features-drawer .ant-drawer-body {
          padding: 16px;
        }

        .features-drawer .ant-drawer-header {
          background: linear-gradient(135deg, #D4A59A 0%, #C88B8B 100%);
          border-radius: 0;
        }

        .features-drawer .ant-drawer-title {
          color: #fff !important;
        }

        .features-drawer .ant-drawer-close {
          color: rgba(255, 255, 255, 0.9);
        }

        .features-drawer .ant-drawer-close:hover {
          color: #fff;
          background: rgba(255, 255, 255, 0.2);
        }

        .feature-item:hover {
          background-color: rgba(200, 139, 139, 0.08);
          margin: 0 -16px;
          padding-left: 16px !important;
          padding-right: 16px !important;
          transition: background-color 0.2s;
        }
      `}</style>
    </Drawer>
  )
}

/**
 * 功能按钮组件（放在 Header 右侧）
 */
interface FeaturesButtonProps {
  onClick: () => void
}

export const FeaturesButton: React.FC<FeaturesButtonProps> = ({ onClick }) => {
  return (
    <div
      onClick={onClick}
      style={{
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 32,
        height: 32,
        borderRadius: '50%',
        background: PRIMARY_GRADIENT,
        transition: 'all 0.2s',
        boxShadow: '0 2px 8px rgba(200, 139, 139, 0.3)',
      }}
      className="features-button"
      title="功能"
    >
      <AppstoreOutlined style={{ fontSize: 16, color: '#fff' }} />

      <style>{`
        .features-button:hover {
          transform: scale(1.1);
          box-shadow: 0 4px 12px rgba(200, 139, 139, 0.4);
        }
      `}</style>
    </div>
  )
}

export default FeaturesDrawer