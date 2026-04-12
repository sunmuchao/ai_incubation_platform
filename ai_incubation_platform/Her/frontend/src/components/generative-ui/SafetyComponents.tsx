/**
 * 安全相关组件
 */
import React from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  Alert,
  Space,
  Descriptions,
  List
} from 'antd'
import {
  SafetyOutlined,
  WarningOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text } = Typography

/**
 * 安全警报
 */
export const SafetyAlert: React.FC<{ level: string; message: string }> = ({
  level,
  message
}) => {
  const alertType = level === 'high' ? 'error' : level === 'medium' ? 'warning' : 'info'

  return (
    <Alert
      className="safety-alert"
      message={
        <Space>
          <SafetyOutlined />
          安全提醒
        </Space>
      }
      description={message}
      type={alertType}
      showIcon
    />
  )
}

/**
 * 安全状态
 */
export const SafetyStatus: React.FC<{ status: string; details?: any }> = ({ status, details }) => {
  return (
    <Card className="safety-status-card" title={<><SafetyOutlined /> 安全状态</>}>
      <div className="safety-indicator">
        <div className={`status-dot ${status}`}></div>
        <Text strong>当前状态：{status}</Text>
      </div>

      {details && (
        <Descriptions column={1} size="small">
          {Object.entries(details).map(([key, value]) => (
            <Descriptions.Item key={key} label={key}>
              {value}
            </Descriptions.Item>
          ))}
        </Descriptions>
      )}
    </Card>
  )
}

/**
 * 安全紧急情况
 */
export const SafetyEmergency: React.FC<{ message: string; onAction?: (action: GenerativeAction) => void }> = ({
  message,
  onAction
}) => {
  return (
    <Alert
      className="safety-emergency"
      message={
        <Space>
          <WarningOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
          <Title level={4} style={{ margin: 0 }}>紧急安全提醒</Title>
        </Space>
      }
      description={message}
      type="error"
      showIcon
      action={
        <Space>
          <Button danger onClick={() => onAction?.({ type: 'get_help' })}>
            获取帮助
          </Button>
          <Button onClick={() => onAction?.({ type: 'dismiss' })}>我知道了</Button>
        </Space>
      }
    />
  )
}

/**
 * 紧急求助面板
 */
export const EmergencyPanel: React.FC<{
  emergency_type?: string
  status?: string
  contacts_notified?: any[]
  location_shared?: boolean
  onAction?: (action: GenerativeAction) => void
}> = ({ emergency_type, status, contacts_notified, location_shared, onAction }) => {
  const getTypeColor = (type?: string) => {
    const colorMap: Record<string, string> = {
      general: 'blue',
      medical: 'red',
      danger: 'red',
      harassment: 'orange'
    }
    return colorMap[type || 'general'] || 'blue'
  }

  const getTypeLabel = (type?: string) => {
    const labelMap: Record<string, string> = {
      general: '一般求助',
      medical: '医疗急救',
      danger: '人身危险',
      harassment: '骚扰威胁'
    }
    return labelMap[type || 'general'] || '一般求助'
  }

  return (
    <Card className="emergency-panel-card">
      <Alert
        message={
          <Space>
            <WarningOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
            <Title level={4} style={{ margin: 0 }}>紧急求助</Title>
          </Space>
        }
        description={
          <div className="emergency-details">
            <div className="emergency-type">
              <Tag color={getTypeColor(emergency_type)}>{getTypeLabel(emergency_type)}</Tag>
            </div>
            <div className="emergency-status">
              <Text strong>状态：</Text>
              <Text type={status === 'active' ? 'danger' : 'success'}>
                {status === 'active' ? '处理中' : '已处理'}
              </Text>
            </div>
            {contacts_notified && contacts_notified.length > 0 && (
              <div className="contacts-notified">
                <Text strong>已通知联系人：</Text>
                <List
                  size="small"
                  dataSource={contacts_notified}
                  renderItem={(contact: any) => (
                    <List.Item>
                      <Text>{contact.name}</Text>
                      <Tag color={contact.notified ? 'green' : 'gray'}>
                        {contact.notified ? '已通知' : '未通知'}
                      </Tag>
                    </List.Item>
                  )}
                />
              </div>
            )}
            {location_shared && (
              <div className="location-shared">
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <Text>位置已共享</Text>
              </div>
            )}
          </div>
        }
        type="error"
        showIcon
      />
    </Card>
  )
}