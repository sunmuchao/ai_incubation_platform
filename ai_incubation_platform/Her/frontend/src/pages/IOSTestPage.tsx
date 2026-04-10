/**
 * iOS 适配测试页面
 * 用于手动测试 iOS Safari 适配情况
 */

import React, { useState, useEffect } from 'react'
import { Card, Button, Typography, Space, Divider, Tag, List, Alert, Spin } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  MobileOutlined,
  AppleOutlined,
  ReloadOutlined,
  SendOutlined
} from '@ant-design/icons'
import { generateIOSTestReport, printTestReport } from '../tests/iosTest'
import type { IOSTestReport } from '../tests/iosTest'
import { isIOS, isIOSSafari, isPWA } from '../utils/iosUtils'

const { Title, Text, Paragraph } = Typography

const IOSTestPage: React.FC = () => {
  const [report, setReport] = useState<IOSTestReport | null>(null)
  const [testInputValue, setTestInputValue] = useState('')
  const [messages, setMessages] = useState<string[]>([])

  // 运行测试
  const runTests = () => {
    const newReport = generateIOSTestReport()
    setReport(newReport)
    printTestReport(newReport)
  }

  // 初始化测试
  useEffect(() => {
    runTests()
  }, [])

  // 测试输入框
  const handleTestInput = () => {
    if (testInputValue.trim()) {
      setMessages(prev => [...prev, testInputValue])
      setTestInputValue('')
    }
  }

  // 测试图片上传
  const handleTestImage = () => {
    setMessages(prev => [...prev, '图片上传测试: ✅ (模拟)'])
  }

  // 测试滚动
  const handleTestScroll = () => {
    // 添加多条消息测试滚动
    const testMessages = Array.from({ length: 20 }, (_, i) => `测试消息 ${i + 1}`)
    setMessages(prev => [...prev, ...testMessages])
  }

  if (!report) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin />
        <Text type="secondary">正在运行测试...</Text>
      </div>
    )
  }

  return (
    <div style={{
      padding: 'max(24px, env(safe-area-inset-top, 24px))',
      paddingBottom: 'max(24px, env(safe-area-inset-bottom, 24px))',
      maxWidth: 800,
      margin: '0 auto'
    }}>
      {/* 设备信息 */}
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" size="large">
          <div>
            <Title level={4}>
              <MobileOutlined style={{ marginRight: 8 }} />
              设备信息
            </Title>
            <Space>
              <Tag color={isIOS() ? 'blue' : 'default'}>
                <AppleOutlined style={{ marginRight: 4 }} />
                {isIOS() ? 'iOS 设备' : '非 iOS 设备'}
              </Tag>
              <Tag color={isIOSSafari() ? 'green' : 'default'}>
                {isIOSSafari() ? 'iOS Safari' : '其他浏览器'}
              </Tag>
              <Tag color={isPWA() ? 'purple' : 'default'}>
                {isPWA() ? 'PWA 模式' : '浏览器模式'}
              </Tag>
            </Space>
          </div>

          <div>
            <Text type="secondary">视口尺寸:</Text>
            <br />
            <Text>
              {report.deviceInfo.viewportWidth} x {report.deviceInfo.viewportHeight}
            </Text>
          </div>

          <div>
            <Text type="secondary">安全区域:</Text>
            <br />
            <Text>
              Top: {report.safeAreaInsets.top}px,
              Bottom: {report.safeAreaInsets.bottom}px
            </Text>
          </div>
        </Space>
      </Card>

      {/* 测试结果 */}
      <Card style={{ marginBottom: 16 }}>
        <Title level={4}>
          {report.overallStatus === 'pass' && <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />}
          {report.overallStatus === 'fail' && <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />}
          {report.overallStatus === 'warning' && <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />}
          测试结果
        </Title>

        <List
          dataSource={report.tests}
          renderItem={test => (
            <List.Item>
              <List.Item.Meta
                avatar={
                  test.status === 'pass' ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                  test.status === 'fail' ? <CloseCircleOutlined style={{ color: '#ff4d4f' }} /> :
                  <WarningOutlined style={{ color: '#faad14' }} />
                }
                title={test.name}
                description={test.description}
              />
              {test.details && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {test.details}
                </Text>
              )}
            </List.Item>
          )}
        />
      </Card>

      {/* 功能测试 */}
      <Card style={{ marginBottom: 16 }}>
        <Title level={4}>功能测试</Title>

        <Space direction="vertical" size="large">
          {/* 输入框测试 */}
          <div>
            <Text>输入框测试 (字体大小 {'>='} 16px):</Text>
            <div style={{ marginTop: 8 }}>
              <input
                type="text"
                value={testInputValue}
                onChange={(e) => setTestInputValue(e.target.value)}
                placeholder="测试输入框..."
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  fontSize: '16px',  // iOS 要求 >= 16px
                  borderRadius: '12px',
                  border: '1px solid #d9d9d9',
                  marginBottom: 8
                }}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleTestInput}
                disabled={!testInputValue.trim()}
              >
                发送
              </Button>
            </div>
          </div>

          <Divider />

          {/* 其他测试按钮 */}
          <Space wrap>
            <Button onClick={handleTestImage}>
              测试图片上传
            </Button>
            <Button onClick={handleTestScroll}>
              测试滚动性能
            </Button>
            <Button onClick={() => setMessages([])}>
              清空消息
            </Button>
          </Space>

          {/* 消息列表 (测试滚动) */}
          {messages.length > 0 && (
            <div
              style={{
                maxHeight: 200,
                overflowY: 'auto',
                border: '1px solid #f0f0f0',
                borderRadius: 8,
                padding: 12,
                WebkitOverflowScrolling: 'touch'  // iOS 平滑滚动
              }}
            >
              {messages.map((msg, idx) => (
                <div key={idx} style={{ padding: 4 }}>
                  <Text>{msg}</Text>
                </div>
              ))}
            </div>
          )}
        </Space>
      </Card>

      {/* 建议 */}
      {report.recommendations.length > 0 && (
        <Card>
          <Title level={4}>建议</Title>
          <List
            dataSource={report.recommendations}
            renderItem={rec => (
              <List.Item>
                <Text>{rec}</Text>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 重新测试按钮 */}
      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <Button
          type="primary"
          size="large"
          icon={<ReloadOutlined />}
          onClick={runTests}
        >
          重新测试
        </Button>
      </div>
    </div>
  )
}

export default IOSTestPage