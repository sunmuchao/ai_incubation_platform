/**
 * 首次功能引导弹窗
 *
 * 问题 17 方案 B：新用户首次进入时显示功能引导，告知用户如何使用 Her
 *
 * 设计原则：
 * 1. 简洁明了，告诉用户能做什么
 * 2. 对话触发 + 按钮入口两种方式都说明
 * 3. 不打扰用户，只在首次进入显示一次
 */

import React from 'react'
import { Modal, Typography, Space, Divider, Button, List, Tag } from 'antd'
import {
  MessageOutlined,
  AppstoreOutlined,
  ThunderboltOutlined,
  HeartOutlined,
  SwapOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import './FeatureGuideModal.less'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'

interface FeatureGuideModalProps {
  open: boolean
  onClose: () => void
}

/**
 * 功能引导弹窗组件
 */
const FeatureGuideModal: React.FC<FeatureGuideModalProps> = ({
  open,
  onClose,
}) => {
  const { t } = useTranslation()

  // 对话触发的功能列表
  const chatTriggerFeatures = [
    {
      icon: <MessageOutlined style={{ color: PRIMARY_COLOR }} />,
      phrase: '"帮我找对象"',
      description: '获取匹配推荐',
    },
    {
      icon: <HeartOutlined style={{ color: '#FFD700' }} />,
      phrase: '"谁喜欢我"',
      description: '查看喜欢你的人',
    },
    {
      icon: <ThunderboltOutlined style={{ color: '#52c41a' }} />,
      phrase: '"更新我的偏好"',
      description: '设置匹配条件',
    },
    {
      icon: <SafetyCertificateOutlined style={{ color: '#1890ff' }} />,
      phrase: '"我的置信度"',
      description: '查看资料可信度',
    },
  ]

  // 按钮入口的功能列表
  const buttonTriggerFeatures = [
    {
      icon: <SwapOutlined style={{ color: '#52c41a' }} />,
      name: '滑动匹配',
      description: 'Tinder 式快速筛选',
      badge: '新',
    },
    {
      icon: <HeartOutlined style={{ color: '#FFD700' }} />,
      name: 'Who Likes Me',
      description: '查看喜欢你的人',
      badge: '会员',
    },
    {
      icon: <SafetyCertificateOutlined style={{ color: '#1890ff' }} />,
      name: '置信度管理',
      description: '提升资料可信度',
      badge: '新',
    },
  ]

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      centered
      width={420}
      className="feature-guide-modal"
      styles={{
        mask: { background: 'rgba(0, 0, 0, 0.45)' },
      }}
    >
      <div className="guide-content">
        {/* 头部 */}
        <div className="guide-header">
          <Title level={4} style={{ marginBottom: 8, textAlign: 'center' }}>
            你可以这样使用 Her
          </Title>
          <Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 16 }}>
            Her 是你的智能红娘，帮你找对象、聊天建议、匹配分析
          </Paragraph>
        </div>

        {/* 对话触发 */}
        <div className="guide-section">
          <div className="section-title">
            <MessageOutlined style={{ color: PRIMARY_COLOR, marginRight: 8 }} />
            <Text strong>直接对话触发</Text>
            <Tag color="pink" style={{ marginLeft: 8 }}>最简单</Tag>
          </div>
          <List
            dataSource={chatTriggerFeatures}
            renderItem={(item) => (
              <List.Item style={{ padding: '8px 0', border: 'none' }}>
                <Space style={{ width: '100%' }}>
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 28,
                    height: 28,
                    borderRadius: 8,
                    background: 'rgba(200, 139, 139, 0.1)',
                  }}>
                    {item.icon}
                  </span>
                  <Text code style={{ fontSize: 13 }}>{item.phrase}</Text>
                  <Text type="secondary" style={{ fontSize: 13 }}>→ {item.description}</Text>
                </Space>
              </List.Item>
            )}
          />
        </div>

        <Divider style={{ margin: '16px 0' }} />

        {/* 按钮入口 */}
        <div className="guide-section">
          <div className="section-title">
            <AppstoreOutlined style={{ color: PRIMARY_COLOR, marginRight: 8 }} />
            <Text strong>右上角功能按钮</Text>
            <Space size={4} style={{ marginLeft: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>点击右上角</Text>
              <AppstoreOutlined style={{ fontSize: 12, color: PRIMARY_COLOR }} />
            </Space>
          </div>
          <List
            dataSource={buttonTriggerFeatures}
            renderItem={(item) => (
              <List.Item style={{ padding: '8px 0', border: 'none' }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Space>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 28,
                      height: 28,
                      borderRadius: 8,
                      background: 'rgba(200, 139, 139, 0.1)',
                    }}>
                      {item.icon}
                    </span>
                    <Text strong style={{ fontSize: 13 }}>{item.name}</Text>
                  </Space>
                  <Space>
                    <Text type="secondary" style={{ fontSize: 13 }}>{item.description}</Text>
                    {item.badge && (
                      <Tag
                        style={{
                          fontSize: 11,
                          background: item.badge === '新' ? '#52c41a'
                            : item.badge === '会员' ? '#FFD700'
                            : PRIMARY_COLOR,
                          color: '#fff',
                          border: 'none',
                        }}
                      >
                        {item.badge}
                      </Tag>
                    )}
                  </Space>
                </Space>
              </List.Item>
            )}
          />
        </div>

        {/* 底部提示 */}
        <div className="guide-footer">
          <Text type="secondary" style={{ fontSize: 12, textAlign: 'center', display: 'block' }}>
            Her 还会主动提醒你使用这些功能，无需刻意去找
          </Text>
        </div>

        {/* 开始按钮 */}
        <Button
          type="primary"
          block
          size="large"
          onClick={onClose}
          style={{
            marginTop: 16,
            background: `linear-gradient(135deg, #D4A59A 0%, ${PRIMARY_COLOR} 100%)`,
            border: 'none',
            borderRadius: 20,
            height: 44,
          }}
        >
          开始使用
        </Button>
      </div>

      <style>{`
        .feature-guide-modal .ant-modal-content {
          border-radius: 16px;
          overflow: hidden;
        }

        .feature-guide-modal .ant-modal-header {
          display: none;
        }

        .feature-guide-modal .ant-modal-body {
          padding: 24px;
        }

        .guide-header {
          margin-bottom: 8px;
        }

        .guide-section {
          margin-bottom: 8px;
        }

        .section-title {
          display: flex;
          align-items: center;
          margin-bottom: 8px;
        }

        .guide-footer {
          margin-top: 8px;
        }
      `}</style>
    </Modal>
  )
}

export default FeatureGuideModal