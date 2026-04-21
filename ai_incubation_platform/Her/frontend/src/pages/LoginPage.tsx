/**
 * 登录/注册页面 - 企业级设计
 * 参考：Ant Design Pro, Material-UI, Modern Authentication Patterns
 */

import React, { useState, useRef, useEffect } from 'react'
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
  QRCode,
  Spin,
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
  WechatOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { userApi } from '../api'
import { authStorage, registrationStorage } from '../utils/storage'
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
  email: string
  password: string
  name: string
  age: number
  gender: string
  location: string
  bio?: string
  interests?: string
}

interface ForgotPasswordFormData {
  email: string
}

// ==================== 密码强度验证 ====================

interface PasswordStrength {
  score: number
  label: string
  color: string
  checks: {
    length: boolean
    types: boolean
    weak: boolean
    username: boolean
  }
}

const validatePasswordStrength = (
  password: string,
  username?: string,
  email?: string
): PasswordStrength => {
  const checks = {
    length: password.length >= 8,
    types: countCharTypes(password) >= 2,
    weak: !isWeakPassword(password),
    username: !containsUserInfo(password, username, email),
  }

  let score = 0
  if (checks.length) score += 25
  if (password.length >= 12) score += 10
  if (checks.types) score += 30
  if (checks.weak) score += 20
  if (checks.username) score += 15

  let label = '极弱'
  let color = '#ff4d4f'
  if (score >= 80) {
    label = '强'
    color = '#52c41a'
  } else if (score >= 50) {
    label = '中'
    color = '#faad14'
  } else if (score >= 30) {
    label = '弱'
    color = '#ff7a45'
  }

  return { score, label, color, checks }
}

const countCharTypes = (password: string): number => {
  let count = 0
  if (/[a-z]/.test(password)) count++
  if (/[A-Z]/.test(password)) count++
  if (/\d/.test(password)) count++
  if (/[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/`~]/.test(password)) count++
  return count
}

const COMMON_WEAK_PASSWORDS = new Set([
  'password', 'password123', '123456', '12345678', '123456789',
  'qwerty', 'qwerty123', 'abc123', 'admin', 'root', 'test',
  'welcome', 'monkey', 'dragon', 'master', 'letmein', 'iloveyou',
])

const isWeakPassword = (password: string): boolean => {
  const lower = password.toLowerCase()
  if (COMMON_WEAK_PASSWORDS.has(lower)) return true
  for (const weak of COMMON_WEAK_PASSWORDS) {
    if (weak.length >= 5 && lower.includes(weak)) return true
  }
  return false
}

const containsUserInfo = (password: string, username?: string, email?: string): boolean => {
  const lower = password.toLowerCase()
  if (username && username.length >= 3 && lower.includes(username.toLowerCase())) return true
  if (email) {
    const prefix = email.split('@')[0].toLowerCase()
    if (prefix.length >= 3 && lower.includes(prefix)) return true
  }
  return false
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

  // 微信登录状态
  const [wechatModalOpen, setWechatModalOpen] = useState(false)
  const [wechatQrUrl, setWechatQrUrl] = useState('')
  const [wechatState, setWechatState] = useState('')
  const [wechatLoading, setWechatLoading] = useState(false)
  const [wechatStatus, setWechatStatus] = useState<'pending' | 'scanned' | 'confirmed' | 'expired'>('pending')
  const wechatPollingRef = useRef<NodeJS.Timeout | null>(null)

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
        // 🔧 [修复] 存储 access_token + refresh_token
        authStorage.saveAuth({
          access_token: response.access_token,
          refresh_token: response.refresh_token,
          user: response.user
        })
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
        email: values.email,
        password: passwordHash,
        name: values.name,
        age: values.age,
        gender: values.gender,
        location: values.location,
        bio: values.bio || '',
        interests: interestsArray,
      })

      // 🔧 [优化] 注册后直接返回 token，不再二次登录（减少 ~0.5s bcrypt 时间）
      if (response.access_token) {
        // 保存完整的用户信息
        const fullUserInfo = {
          id: response.user?.id || response.id,
          username: values.username,
          name: values.name,
          email: values.email,
          age: values.age,
          gender: values.gender,
          location: values.location,
          ...(response.user || {}),
        }

        authStorage.saveAuth({
          access_token: response.access_token,
          refresh_token: response.refresh_token || '',
          user: fullUserInfo
        })
        registrationStorage.reset()
        message.success('注册成功！')
        onLoginSuccess?.()
        return
      }

      // 兼容旧格式：如果没有 token，尝试自动登录
      if (response.id || response.email) {
        try {
          const loginResponse = await userApi.login(values.email, passwordHash)
          if (loginResponse.access_token) {
            const fullUserInfo = {
              id: response.id,
              username: values.username,
              name: values.name,
              email: values.email,
              age: values.age,
              gender: values.gender,
              location: values.location,
            }
            authStorage.saveAuth({
              access_token: loginResponse.access_token,
              refresh_token: loginResponse.refresh_token,
              user: fullUserInfo
            })
            registrationStorage.reset()
            message.success('注册并登录成功！')
            onLoginSuccess?.()
            return
          }
        } catch (loginError) {
          console.warn('Auto-login after registration failed:', loginError)
        }

        // 如果自动登录失败，保存完整用户信息并提示手动登录
        const fullUserInfo = {
          id: response.id,
          username: values.username,
          name: values.name,
          email: values.email,
          age: values.age,
          gender: values.gender,
          location: values.location,
        }
        authStorage.setUser(fullUserInfo)
        registrationStorage.reset()
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
      // 调用后端忘记密码 API
      await userApi.forgotPassword(forgotEmail)

      setForgotStep('sent')
      message.success('重置邮件已发送，请查收！')
    } catch (error: unknown) {
      // 安全考虑：无论成功失败都显示相同信息，避免枚举攻击
      setForgotStep('sent')
      message.success('如果该邮箱已注册，重置邮件将在几分钟内送达')
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

  // ========== 微信登录 ==========

  // 打开微信登录弹窗
  const handleWechatLogin = async () => {
    setWechatLoading(true)
    setWechatModalOpen(true)
    setWechatStatus('pending')

    try {
      const response = await fetch('/api/wechat/qrcode')
      if (!response.ok) {
        throw new Error('获取二维码失败')
      }

      const data = await response.json()
      setWechatQrUrl(data.qrcode_url)
      setWechatState(data.state)

      // 开始轮询检查登录状态
      startWechatPolling(data.state)
    } catch (error) {
      console.error('Failed to get WeChat QR code:', error)
      message.error('微信登录暂不可用，请使用账号登录')
      setWechatModalOpen(false)
    } finally {
      setWechatLoading(false)
    }
  }

  // 开始轮询检查登录状态
  const startWechatPolling = (state: string) => {
    // 清理之前的轮询
    if (wechatPollingRef.current) {
      clearInterval(wechatPollingRef.current)
    }

    // 每 2 秒检查一次
    wechatPollingRef.current = setInterval(async () => {
      try {
        const response = await fetch(`/api/wechat/status?state=${state}`)
        if (!response.ok) return

        const data = await response.json()
        setWechatStatus(data.status)

        // 登录成功
        if (data.status === 'confirmed' && (data.token || data.access_token)) {
          // 停止轮询
          if (wechatPollingRef.current) {
            clearInterval(wechatPollingRef.current)
            wechatPollingRef.current = null
          }

          // 🔧 [修复] 兼容旧格式 token 和新格式 access_token
          authStorage.saveAuth({
            access_token: data.access_token || data.token,
            refresh_token: data.refresh_token || '', // 微信登录可能没有 refresh_token
            user: { id: data.user_id },
          })

          message.success('微信登录成功！')
          setWechatModalOpen(false)

          // 获取完整用户信息
          try {
            const accessToken = data.access_token || data.token
            const userResponse = await fetch('/api/users/me', {
              headers: { Authorization: `Bearer ${accessToken}` },
            })
            if (userResponse.ok) {
              const userData = await userResponse.json()
              authStorage.setUser(userData)
            }
          } catch (e) {
            console.warn('Failed to fetch user info:', e)
          }

          onLoginSuccess?.()
        }

        // 过期或无效
        if (data.status === 'expired' || data.status === 'invalid') {
          if (wechatPollingRef.current) {
            clearInterval(wechatPollingRef.current)
            wechatPollingRef.current = null
          }
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }, 2000)
  }

  // 刷新二维码
  const handleRefreshWechatQr = async () => {
    setWechatStatus('pending')
    setWechatQrUrl('')
    await handleWechatLogin()
  }

  // 关闭微信登录弹窗
  const handleWechatModalClose = () => {
    setWechatModalOpen(false)
    if (wechatPollingRef.current) {
      clearInterval(wechatPollingRef.current)
      wechatPollingRef.current = null
    }
  }

  // 清理轮询
  useEffect(() => {
    return () => {
      if (wechatPollingRef.current) {
        clearInterval(wechatPollingRef.current)
      }
    }
  }, [])

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

              {/* 第三方登录 */}
              <div className="social-login">
                <Button
                  icon={<WechatOutlined />}
                  size="large"
                  className="social-btn wechat-btn"
                  onClick={handleWechatLogin}
                >
                  微信登录
                </Button>
              </div>

              {/* 游客体验模式 - 仅开发环境可用 */}
              {import.meta.env.DEV && (
                <div className="quick-experience">
                  <Button
                    type="link"
                    size="small"
                    onClick={() => {
                      // 🔧 [修复] 开发环境使用兼容格式
                      authStorage.saveAuth({
                        access_token: 'dev-token',
                        refresh_token: 'dev-refresh-token',
                        user: {
                          id: 'user-anonymous-dev',
                          username: 'user-anonymous-dev',
                          name: '体验用户'
                        }
                      })
                      message.success('已进入体验模式（仅开发环境）')
                      onLoginSuccess?.()
                    }}
                  >
                    🧪 游客体验模式（开发环境）
                  </Button>
                </div>
              )}
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

        {/* 微信登录弹窗 */}
        <Modal
          title={
            <Space>
              <WechatOutlined style={{ color: '#07C160' }} />
              微信扫码登录
            </Space>
          }
          open={wechatModalOpen}
          onCancel={handleWechatModalClose}
          footer={null}
          width={360}
          centered
          destroyOnHidden
        >
          <div className="wechat-login-content">
            {wechatLoading ? (
              <div className="wechat-loading">
                <Spin size="large" />
                <Text type="secondary" style={{ marginTop: 16 }}>
                  正在生成二维码...
                </Text>
              </div>
            ) : wechatStatus === 'expired' ? (
              <div className="wechat-expired">
                <Text type="secondary">二维码已过期</Text>
                <Button
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={handleRefreshWechatQr}
                  style={{ marginTop: 16 }}
                >
                  刷新二维码
                </Button>
              </div>
            ) : wechatStatus === 'confirmed' ? (
              <div className="wechat-success">
                <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a' }} />
                <Text style={{ marginTop: 16, color: '#52c41a' }}>
                  登录成功！
                </Text>
              </div>
            ) : (
              <>
                <div className="wechat-qrcode">
                  {wechatQrUrl && (
                    <iframe
                      src={wechatQrUrl}
                      width="200"
                      height="200"
                      frameBorder="0"
                      style={{ border: 'none' }}
                      title="微信登录二维码"
                    />
                  )}
                </div>
                <div className="wechat-status">
                  {wechatStatus === 'scanned' ? (
                    <Text style={{ color: '#07C160' }}>
                      <CheckCircleOutlined /> 已扫描，请在手机上确认
                    </Text>
                  ) : (
                    <Text type="secondary">
                      请使用微信扫描二维码登录
                    </Text>
                  )}
                </div>
                <div className="wechat-tips">
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    首次使用微信登录将自动创建账号
                  </Text>
                </div>
              </>
            )}
          </div>
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
  const [passwordStrength, setPasswordStrength] = useState<PasswordStrength | null>(null)
  const [password, setPassword] = useState('')

  // 监听密码变化，实时计算强度
  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setPassword(value)
    if (value) {
      const username = form.getFieldValue('username')
      const email = form.getFieldValue('email')
      setPasswordStrength(validatePasswordStrength(value, username, email))
    } else {
      setPasswordStrength(null)
    }
  }

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
        {/* 1. 用户名 - 唯一标识 */}
        <Form.Item
          label={<Text type="secondary">用户名</Text>}
          name="username"
          rules={[
            { required: true, message: '请输入用户名' },
            { min: 3, message: '用户名至少 3 个字符' },
            { max: 20, message: '用户名最多 20 个字符' },
            { pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/, message: '用户名只能包含字母、数字、下划线或中文' },
          ]}
        >
          <Input prefix={<UserOutlined />} placeholder="用于登录的唯一标识" />
        </Form.Item>

        {/* 2. 邮箱 - 用于通知和找回密码 */}
        <Form.Item
          label={<Text type="secondary">邮箱</Text>}
          name="email"
          rules={[
            { required: true, message: '请输入邮箱' },
            { type: 'email', message: '请输入有效的邮箱格式' },
          ]}
        >
          <Input prefix={<MailOutlined />} placeholder="用于接收通知和找回密码" />
        </Form.Item>

        {/* 3. 密码 */}
        <Form.Item
          label={<Text type="secondary">密码</Text>}
          name="password"
          rules={[
            { required: true, message: '请输入密码' },
            { min: 8, message: '密码至少 8 个字符' },
            {
              validator: (_, value) => {
                if (!value) return Promise.resolve()
                const result = validatePasswordStrength(value)
                if (result.score < 30) {
                  return Promise.reject(new Error('密码强度不足'))
                }
                return Promise.resolve()
              }
            }
          ]}
        >
          <div>
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="至少 8 个字符，建议包含大小写字母、数字、特殊字符"
              autoComplete="new-password"
              iconRender={(visible) => visible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
              value={password}
              onChange={handlePasswordChange}
            />
            {passwordStrength && (
              <div style={{ marginTop: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    flex: 1,
                    height: 4,
                    background: '#f0f0f0',
                    borderRadius: 2,
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${passwordStrength.score}%`,
                      height: '100%',
                      background: passwordStrength.color,
                      transition: 'width 0.3s'
                    }} />
                  </div>
                  <Text style={{ fontSize: 12, color: passwordStrength.color }}>
                    {passwordStrength.label}
                  </Text>
                </div>
                <div style={{ marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {[!passwordStrength.checks.length && '至少8字符',
                      !passwordStrength.checks.types && '需多种字符类型',
                      !passwordStrength.checks.weak && '避免常见弱密码',
                      !passwordStrength.checks.username && '不要包含用户名/邮箱'
                    ].filter(Boolean).join(' · ') || '✓ 密码强度良好'}
                  </Text>
                </div>
              </div>
            )}
          </div>
        </Form.Item>

        {/* 4. 昵称 - 显示名称 */}
        <Form.Item
          label={<Text type="secondary">昵称</Text>}
          name="name"
          rules={[{ required: true, message: '请输入昵称' }]}
        >
          <Input prefix={<UserOutlined />} placeholder="显示给其他用户的名称" />
        </Form.Item>

        {/* 5. 年龄 + 性别 */}
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
