/**
 * 登录/注册页面 - 企业级设计
 * 参考：Ant Design Pro, Material-UI, Modern Authentication Patterns
 */

import React, { useState, useRef } from 'react'
import {
  Form,
  Input,
  Button,
  Card,
  Typography,
  Tabs,
  message,
  Divider,
  Select,
  Modal,
  Space,
  Checkbox,
  ConfigProvider,
  theme,
} from 'antd'
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  PhoneOutlined,
  HeartOutlined,
  GoogleOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import { userApi } from '../api'
import CryptoJS from 'crypto-js'
import './LoginPage.less'

const { Title, Text, Link } = Typography
const { Option } = Select

// ==================== 类型定义 ====================

interface LoginFormData {
  username: string
  password: string
  remember?: boolean
}

interface RegisterFormData {
  username: string
  password: string
  email: string
  name: string
  age: number
  gender: string
  location: string
  bio: string
  interests: string
  sexual_orientation: string
}

interface ForgotPasswordFormData {
  email: string
}

// ==================== 主组件 ====================

const LoginPage: React.FC<{ onLoginSuccess?: () => void }> = ({ onLoginSuccess }) => {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login')

  // 忘记密码状态
  const [forgotModalOpen, setForgotModalOpen] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotLoading, setForgotLoading] = useState(false)
  const [forgotStep, setForgotStep] = useState<'input' | 'sent'>('input')

  const formRef = useRef<any>(null)

  // 处理登录
  const handleLogin = async (values: LoginFormData) => {
    setLoading(true)
    try {
      // 客户端 SHA-256 哈希，防止密码明文传输
      // SHA-256 是确定性哈希，相同密码总是产生相同输出
      const passwordHash = CryptoJS.SHA256(values.password).toString()

      const response = await userApi.login(values.username, passwordHash)
      if (response.access_token) {
        localStorage.setItem('jwt_token', response.access_token)
        localStorage.setItem('user_info', JSON.stringify(response.user))
        message.success('登录成功！')
        onLoginSuccess?.()
      }
    } catch (error: unknown) {
      // 根据错误类型显示不同提示
      let errorMsg = '登录失败，请稍后重试'

      if (error && typeof error === 'object') {
        const err = error as Record<string, unknown>
        const detail = err.detail as string | undefined
        const status = err.status as number | undefined

        if (detail) {
          if (detail.includes('Invalid credentials') || detail.includes('incorrect password')) {
            errorMsg = '账号或密码错误，请检查后重试'
          } else if (detail.includes('not found') || detail.includes('User does not exist')) {
            errorMsg = '用户不存在，请先注册账号'
          } else if (detail.includes('inactive') || detail.includes('disabled')) {
            errorMsg = '账号已被禁用，请联系客服'
          } else {
            errorMsg = detail
          }
        } else if (status === 401) {
          errorMsg = '账号或密码错误，请检查后重试'
        } else if (status === 403) {
          errorMsg = '账号已被禁用，请联系客服'
        } else if (status === 404) {
          errorMsg = '用户不存在，请先注册账号'
        }
      } else if (error instanceof Error) {
        errorMsg = error.message
      }

      message.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  // 处理注册
  const handleRegister = async (values: RegisterFormData) => {
    setLoading(true)
    try {
      const interestsArray = (values.interests || '')
        .split(',')
        .map((i) => i.trim())
        .filter((i) => i)

      // 客户端 SHA-256 哈希，防止密码明文传输
      const passwordHash = CryptoJS.SHA256(values.password).toString()

      const response = await userApi.register({
        username: values.username,
        password: passwordHash,
        email: values.email,
        name: values.name,
        age: values.age,
        gender: values.gender,
        location: values.location,
        bio: values.bio,
        interests: interestsArray,
        sexual_orientation: values.sexual_orientation || 'heterosexual',
      })

      if (response.id || response.email) {
        // 注册成功后自动登录（使用哈希后的密码）
        try {
          const loginResponse = await userApi.login(values.email, passwordHash)
          if (loginResponse.access_token) {
            localStorage.setItem('jwt_token', loginResponse.access_token)
            localStorage.setItem('user_info', JSON.stringify(loginResponse.user))
            localStorage.removeItem('has_completed_registration_conversation')
            message.success('注册并登录成功！')
            onLoginSuccess?.()
            return
          }
        } catch (loginError) {
          console.warn('Auto-login after registration failed:', loginError)
          // 自动登录失败，提示用户手动登录
        }

        // 如果自动登录失败，只保存用户信息并提示手动登录
        const userInfo = {
          id: response.id,
          username: values.username,
          name: values.name,
          email: values.email,
        }
        localStorage.setItem('user_info', JSON.stringify(userInfo))
        localStorage.removeItem('has_completed_registration_conversation')
        message.success('注册成功！请使用邮箱登录')
        setActiveTab('login')
      }
    } catch (error: unknown) {
      console.error('Register error:', error)
      const errorMsg = error instanceof Error ? error.message : '注册失败，请稍后重试'
      message.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  // 打开忘记密码弹窗
  const handleOpenForgot = () => {
    setForgotEmail('')
    setForgotStep('input')
    setForgotModalOpen(true)
  }

  // 处理忘记密码提交
  const handleForgotSubmit = async () => {
    if (!forgotEmail.trim()) {
      message.warning('请输入邮箱地址')
      return
    }

    // 邮箱格式验证
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(forgotEmail)) {
      message.warning('请输入有效的邮箱格式')
      return
    }

    setForgotLoading(true)
    try {
      // TODO: 调用后端忘记密码 API
      // await userApi.forgotPassword(forgotEmail)

      // 模拟 API 调用
      await new Promise((resolve) => setTimeout(resolve, 1500))

      setForgotStep('sent')
      message.success('重置邮件已发送，请查收！')
    } catch (error: unknown) {
      const errorMsg = error instanceof Error ? error.message : '发送失败，请稍后重试'
      message.error(errorMsg)
    } finally {
      setForgotLoading(false)
    }
  }

  // 关闭弹窗
  const handleForgotClose = () => {
    setForgotModalOpen(false)
    setForgotStep('input')
    setForgotEmail('')
  }

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#D4A59A',
          borderRadius: 8,
        },
      }}
    >
      <div className="login-page-v2">
        {/* 背景装饰 */}
        <div className="login-bg-decoration">
          <div className="bg-circle circle-1" />
          <div className="bg-circle circle-2" />
          <div className="bg-circle circle-3" />
        </div>

        <div className="login-wrapper">
          {/* 左侧品牌区 */}
          <div className="login-brand-section">
            <div className="brand-content">
              <div className="brand-logo">
                <HeartOutlined />
              </div>
              <Title level={2} className="brand-title">
                Her
              </Title>
              <Text className="brand-subtitle">
                遇见懂你的 TA
              </Text>

              <div className="brand-features">
                <div className="feature-item">
                  <div className="feature-icon">🎯</div>
                  <div className="feature-text">
                    <div className="feature-title">AI 智能匹配</div>
                    <div className="feature-desc">深度学习你的偏好</div>
                  </div>
                </div>
                <div className="feature-item">
                  <div className="feature-icon">🔒</div>
                  <div className="feature-text">
                    <div className="feature-title">安全隐私</div>
                    <div className="feature-desc">严格保护个人信息</div>
                  </div>
                </div>
                <div className="feature-item">
                  <div className="feature-icon">💕</div>
                  <div className="feature-text">
                    <div className="feature-title">真实认证</div>
                    <div className="feature-desc">实名认证更放心</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 右侧表单区 */}
          <div className="login-form-section">
            <Card className="login-form-card" variant="borderless">
              <Tabs
                activeKey={activeTab}
                onChange={(key) => setActiveTab(key as 'login' | 'register')}
                centered
                items={[
                  {
                    key: 'login',
                    label: '账号登录',
                    children: (
                      <div className="tab-content-wrapper">
                        <LoginForm
                          ref={formRef}
                          onFinish={handleLogin}
                          loading={loading}
                          onForgotPassword={handleOpenForgot}
                        />
                      </div>
                    ),
                  },
                  {
                    key: 'register',
                    label: '注册账号',
                    children: (
                      <div className="tab-content-wrapper">
                        <RegisterForm
                          onFinish={handleRegister}
                          loading={loading}
                        />
                      </div>
                    ),
                  },
                ]}
              />

              <Divider style={{ margin: '16px 0 8px' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  其他登录方式
                </Text>
              </Divider>

              <div className="social-login">
                <Button
                  icon={<GoogleOutlined />}
                  size="large"
                  className="social-btn"
                  onClick={() => message.info('第三方登录功能开发中')}
                >
                  Google
                </Button>
              </div>

              <div className="quick-experience">
                <Button
                  type="link"
                  size="small"
                  onClick={() => {
                    localStorage.setItem('jwt_token', 'dev-token')
                    localStorage.setItem('user_info', JSON.stringify({
                      id: 'user-anonymous-dev',
                      username: 'user-anonymous-dev',
                      name: '体验用户'
                    }))
                    message.success('已进入体验模式')
                    onLoginSuccess?.()
                  }}
                >
                  游客体验模式
                </Button>
              </div>
            </Card>

            <div className="login-terms">
              <Text type="secondary" style={{ fontSize: 12 }}>
                登录即表示你同意我们的{' '}
                <Link href="#">用户协议</Link>
                {' '}和{' '}
                <Link href="#">隐私政策</Link>
              </Text>
            </div>
          </div>
        </div>

        {/* 忘记密码弹窗 */}
        <Modal
          title={
            <Space>
              <ArrowLeftOutlined
                style={{ cursor: forgotStep === 'sent' ? 'pointer' : 'default' }}
                onClick={forgotStep === 'sent' ? () => setForgotStep('input') : undefined}
              />
              {forgotStep === 'input' ? '忘记密码' : '检查邮箱'}
            </Space>
          }
          open={forgotModalOpen}
          onCancel={handleForgotClose}
          onOk={forgotStep === 'input' ? handleForgotSubmit : handleForgotClose}
          confirmLoading={forgotLoading}
          okText={forgotStep === 'input' ? '发送重置邮件' : '完成'}
          cancelText="取消"
          width={420}
          destroyOnHidden
        >
          {forgotStep === 'input' ? (
            <div className="forgot-password-content">
              <div className="forgot-hint">
                <MailOutlined className="hint-icon" />
                <Text>
                  请输入您的注册邮箱，我们将发送密码重置链接到您的邮箱。
                </Text>
              </div>
              <Input
                ref={(input) => input?.focus()}
                placeholder="请输入邮箱地址"
                value={forgotEmail}
                onChange={(e) => setForgotEmail(e.target.value)}
                onPressEnter={handleForgotSubmit}
                size="large"
                prefix={<MailOutlined />}
                autoComplete="email"
                allowClear
              />
            </div>
          ) : (
            <div className="forgot-password-sent">
              <div className="sent-icon">✉️</div>
              <Title level={5} style={{ textAlign: 'center', marginBottom: 16 }}>
                重置邮件已发送
              </Title>
              <Text type="secondary" style={{ display: 'block', textAlign: 'center' }}>
                请前往 <Text strong>{forgotEmail}</Text> 查看重置链接
              </Text>
              <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginTop: 8, fontSize: 12 }}>
                如果没有收到邮件，请检查垃圾邮件箱
              </Text>
            </div>
          )}
        </Modal>
      </div>
    </ConfigProvider>
  )
}

// ==================== 登录表单组件 ====================

const LoginForm = React.forwardRef<any, {
  onFinish: (values: LoginFormData) => void
  loading: boolean
  onForgotPassword?: () => void
}>(({ onFinish, loading, onForgotPassword }, ref) => {
  const [form] = Form.useForm()
  React.useImperativeHandle(ref, () => ({
    resetFields: () => form.resetFields(),
  }))

  return (
    <Form
      form={form}
      name="login"
      onFinish={onFinish}
      autoComplete="off"
      size="large"
      layout="vertical"
      requiredMark={false}
    >
      <Form.Item
        label={<Text type="secondary">用户名</Text>}
        name="username"
        rules={[{ required: true, message: '请输入用户名' }]}
      >
        <Input
          prefix={<UserOutlined />}
          placeholder="用户名/手机号/邮箱"
          size="large"
          autoComplete="username"
        />
      </Form.Item>

      <Form.Item
        label={<Text type="secondary">密码</Text>}
        name="password"
        rules={[{ required: true, message: '请输入密码' }]}
      >
        <Input.Password
          prefix={<LockOutlined />}
          placeholder="密码"
          size="large"
          autoComplete="current-password"
          iconRender={({ visible }) => visible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
        />
      </Form.Item>

      <Form.Item className="login-form-options">
        <Space className="login-form-options-inner">
          <Form.Item name="remember" valuePropName="checked" noStyle>
            <Checkbox>记住我</Checkbox>
          </Form.Item>
          <Button type="link" size="small" onClick={onForgotPassword} style={{ padding: 0 }}>
            忘记密码？
          </Button>
        </Space>
      </Form.Item>

      <Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          loading={loading}
          size="large"
          block
          className="login-submit-btn"
        >
          登录
        </Button>
      </Form.Item>
    </Form>
  )
})

// ==================== 注册表单组件 ====================

const RegisterForm: React.FC<{
  onFinish: (values: RegisterFormData) => void
  loading: boolean
}> = ({ onFinish, loading }) => {
  const [form] = Form.useForm()

  return (
    <div className="register-form-container">
      <Form
        form={form}
        name="register"
        onFinish={onFinish}
        autoComplete="off"
        size="large"
        layout="vertical"
        requiredMark={false}
        scrollToFirstError
      >
        <Form.Item
          label={<Text type="secondary">用户名</Text>}
          name="username"
          rules={[
            { required: true, message: '请输入用户名' },
            { min: 3, message: '用户名至少 3 个字符' },
          ]}
        >
          <Input prefix={<UserOutlined />} placeholder="至少 3 个字符" />
        </Form.Item>

        <Form.Item
          label={<Text type="secondary">密码</Text>}
          name="password"
          rules={[
            { required: true, message: '请输入密码' },
            { min: 6, message: '密码至少 6 个字符' },
          ]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="至少 6 个字符"
            iconRender={({ visible }) => visible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
          />
        </Form.Item>

        <Form.Item
          label={<Text type="secondary">邮箱</Text>}
          name="email"
          rules={[
            { required: true, message: '请输入邮箱' },
            { type: 'email', message: '请输入有效的邮箱格式' },
          ]}
        >
          <Input prefix={<MailOutlined />} placeholder="用于接收通知" />
        </Form.Item>

        <Form.Item
          label={<Text type="secondary">昵称</Text>}
          name="name"
          rules={[{ required: true, message: '请输入昵称' }]}
        >
          <Input prefix={<UserOutlined />} placeholder="显示给其他用户的名称" />
        </Form.Item>

        <div className="register-row">
          <Form.Item
            label={<Text type="secondary">年龄</Text>}
            name="age"
            rules={[{ required: true, message: '请输入年龄' }]}
            style={{ flex: 1, marginRight: 12 }}
          >
            <Input type="number" prefix={<UserOutlined />} placeholder="年龄" />
          </Form.Item>

          <Form.Item
            label={<Text type="secondary">性别</Text>}
            name="gender"
            rules={[{ required: true, message: '请选择性别' }]}
            style={{ flex: 1, marginLeft: 12 }}
          >
            <Select placeholder="选择">
              <Option value="male">男</Option>
              <Option value="female">女</Option>
            </Select>
          </Form.Item>
        </div>

        <Form.Item
          label={<Text type="secondary">性取向</Text>}
          name="sexual_orientation"
          rules={[{ required: true, message: '请选择性取向' }]}
          initialValue="heterosexual"
        >
          <Select placeholder="选择偏好">
            <Option value="heterosexual">异性（默认）</Option>
            <Option value="homosexual">同性</Option>
            <Option value="bisexual">双性</Option>
          </Select>
        </Form.Item>

        <Form.Item
          label={<Text type="secondary">所在地</Text>}
          name="location"
          rules={[{ required: true, message: '请输入所在地' }]}
        >
          <Input prefix={<MailOutlined />} placeholder="城市/地区" />
        </Form.Item>

        <Form.Item
          label={<Text type="secondary">个人简介</Text>}
          name="bio"
        >
          <Input.TextArea
            rows={2}
            placeholder="介绍一下自己（选填）"
            showCount
            maxLength={500}
          />
        </Form.Item>

        <Form.Item
          label={<Text type="secondary">兴趣爱好</Text>}
          name="interests"
        >
          <Input.TextArea
            rows={2}
            placeholder="用逗号分隔，如：旅行，电影，美食"
          />
        </Form.Item>

        <Form.Item style={{ marginBottom: 8 }}>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            size="large"
            block
            className="login-submit-btn"
          >
            注册
          </Button>
        </Form.Item>
      </Form>
    </div>
  )
}

export default LoginPage
