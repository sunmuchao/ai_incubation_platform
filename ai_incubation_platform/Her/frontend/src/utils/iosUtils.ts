/**
 * 移动设备适配工具
 * 处理 iOS、Android、WebView 等特有问题
 */

/**
 * 检测是否为 iOS 设备
 */
export const isIOS = (): boolean => {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

/**
 * 检测是否为 Android 设备
 */
export const isAndroid = (): boolean => {
  return /Android/i.test(navigator.userAgent)
}

/**
 * 检测是否为移动设备
 */
export const isMobile = (): boolean => {
  return isIOS() || isAndroid() || /Mobile|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
}

/**
 * 检测是否为平板设备
 */
export const isTablet = (): boolean => {
  const ua = navigator.userAgent
  const isIPad = /iPad/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  const isAndroidTablet = /Android/i.test(ua) && !/Mobile/i.test(ua)
  const isLargeScreen = window.innerWidth >= 768
  const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0

  return isIPad || isAndroidTablet || (isLargeScreen && isTouchDevice)
}

/**
 * 检测是否为 Safari 浏览器
 */
export const isSafari = (): boolean => {
  return /^((?!chrome|android).)*safari/i.test(navigator.userAgent)
}

/**
 * 检测是否为 iOS Safari
 */
export const isIOSSafari = (): boolean => {
  return isIOS() && isSafari()
}

/**
 * 检测是否为 Android Chrome
 */
export const isAndroidChrome = (): boolean => {
  return isAndroid() && /Chrome/i.test(navigator.userAgent)
}

/**
 * 检测是否为微信内置浏览器
 */
export const isWechat = (): boolean => {
  return /MicroMessenger/i.test(navigator.userAgent)
}

/**
 * 检测是否为支付宝内置浏览器
 */
export const isAlipay = (): boolean => {
  return /AlipayClient/i.test(navigator.userAgent)
}

/**
 * 检测是否为 QQ 内置浏览器
 */
export const isQQ = (): boolean => {
  return /\sQQ/i.test(navigator.userAgent)
}

/**
 * 检测是否为微博内置浏览器
 */
export const isWeibo = (): boolean => {
  return /Weibo/i.test(navigator.userAgent)
}

/**
 * 检测是否为 UC 浏览器
 */
export const isUC = (): boolean => {
  return /UCBrowser/i.test(navigator.userAgent)
}

/**
 * 检测是否为 360 浏览器
 */
export const is360 = (): boolean => {
  return /360/i.test(navigator.userAgent)
}

/**
 * 检测是否为 WebView 模式
 */
export const isWebView = (): boolean => {
  return isWechat() || isAlipay() || isQQ() || isWeibo()
}

/**
 * 检测是否为 PWA 模式
 */
export const isPWA = (): boolean => {
  return window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as any).standalone === true
}

/**
 * 检测屏幕方向
 */
export const getOrientation = (): 'portrait' | 'landscape' => {
  return window.innerWidth > window.innerHeight ? 'landscape' : 'portrait'
}

/**
 * 检测设备类型
 */
export const getDeviceType = (): 'phone' | 'tablet' | 'desktop' => {
  if (isTablet()) return 'tablet'
  if (isMobile()) return 'phone'
  return 'desktop'
}

/**
 * 检测浏览器类型
 */
export const getBrowserType = (): string => {
  if (isWechat()) return 'wechat'
  if (isAlipay()) return 'alipay'
  if (isQQ()) return 'qq'
  if (isWeibo()) return 'weibo'
  if (isUC()) return 'uc'
  if (is360()) return '360'
  if (isIOSSafari()) return 'ios-safari'
  if (isAndroidChrome()) return 'android-chrome'
  if (isSafari()) return 'safari'
  return 'unknown'
}

/**
 * 获取设备完整信息
 */
export const getDeviceInfo = () => {
  return {
    // 设备类型
    isIOS: isIOS(),
    isAndroid: isAndroid(),
    isMobile: isMobile(),
    isTablet: isTablet(),
    deviceType: getDeviceType(),

    // 浏览器类型
    isSafari: isSafari(),
    isIOSSafari: isIOSSafari(),
    isAndroidChrome: isAndroidChrome(),
    browserType: getBrowserType(),

    // WebView
    isWechat: isWechat(),
    isAlipay: isAlipay(),
    isQQ: isQQ(),
    isWeibo: isWeibo(),
    isWebView: isWebView(),

    // 其他
    isPWA: isPWA(),
    orientation: getOrientation(),

    // 屏幕信息
    screenWidth: screen.width,
    screenHeight: screen.height,
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
    devicePixelRatio: window.devicePixelRatio,

    // User Agent
    userAgent: navigator.userAgent
  }
}

/**
 * iOS 键盘弹起处理
 * 解决 iOS Safari 键盘弹起时布局错乱问题
 */
export class IOSKeyboardHandler {
  private originalHeight: number = 0
  private isKeyboardVisible: boolean = false
  private listeners: Array<() => void> = []

  constructor() {
    if (isIOS()) {
      this.init()
    }
  }

  private init() {
    // 记录原始视口高度
    this.originalHeight = window.innerHeight

    // 监听视口大小变化（键盘弹起/收起）
    window.addEventListener('resize', this.handleResize.bind(this))

    // 监听输入框焦点
    document.addEventListener('focusin', this.handleFocusIn.bind(this))
    document.addEventListener('focusout', this.handleFocusOut.bind(this))
  }

  private handleResize() {
    const currentHeight = window.innerHeight
    const heightDiff = this.originalHeight - currentHeight

    // 判断键盘是否弹起（高度差超过 100px）
    if (heightDiff > 100) {
      this.isKeyboardVisible = true
      this.adjustLayoutForKeyboard(heightDiff)
    } else {
      this.isKeyboardVisible = false
      this.resetLayout()
    }
  }

  private handleFocusIn(e: Event) {
    const target = e.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
      // 输入框聚焦时，滚动到可见区域
      setTimeout(() => {
        target.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }, 100)
    }
  }

  private handleFocusOut() {
    // 输入框失焦时，延迟重置布局（等待键盘收起动画）
    setTimeout(() => {
      if (!this.isKeyboardVisible) {
        this.resetLayout()
      }
    }, 300)
  }

  private adjustLayoutForKeyboard(keyboardHeight: number) {
    // 调整固定元素位置
    const fixedElements = document.querySelectorAll('.chat-room-input-area, .input-area')
    fixedElements.forEach(el => {
      const element = el as HTMLElement
      // 将输入区域向下移动，避免被键盘遮挡
      element.style.transform = `translateY(-${keyboardHeight}px)`
    })

    // 触发键盘状态变化事件
    this.notifyListeners(true, keyboardHeight)
  }

  private resetLayout() {
    // 重置固定元素位置
    const fixedElements = document.querySelectorAll('.chat-room-input-area, .input-area')
    fixedElements.forEach(el => {
      const element = el as HTMLElement
      element.style.transform = ''
    })

    // 触发键盘状态变化事件
    this.notifyListeners(false, 0)
  }

  /**
   * 添加键盘状态监听器
   */
  addListener(listener: () => void) {
    this.listeners.push(listener)
  }

  /**
   * 移除键盘状态监听器
   */
  removeListener(listener: () => void) {
    this.listeners = this.listeners.filter(l => l !== listener)
  }

  private notifyListeners(isVisible: boolean, height: number) {
    this.listeners.forEach(listener => listener())
  }

  /**
   * 销毁处理器
   */
  destroy() {
    window.removeEventListener('resize', this.handleResize.bind(this))
    document.removeEventListener('focusin', this.handleFocusIn.bind(this))
    document.removeEventListener('focusout', this.handleFocusOut.bind(this))
    this.listeners = []
  }

  /**
   * 获取键盘状态
   */
  getKeyboardState() {
    return {
      isVisible: this.isKeyboardVisible,
      height: this.originalHeight - window.innerHeight
    }
  }
}

/**
 * iOS 视口高度修复
 * 解决 iOS Safari 地址栏导致的视口高度问题
 */
export const fixIOSViewportHeight = () => {
  if (!isIOSSafari()) return

  // 使用 -webkit-fill-available 修复视口高度
  const setViewportHeight = () => {
    const vh = window.innerHeight * 0.01
    document.documentElement.style.setProperty('--vh', `${vh}px`)
  }

  // 初始化
  setViewportHeight()

  // 监听视口变化
  window.addEventListener('resize', setViewportHeight)
  window.addEventListener('orientationchange', () => {
    setTimeout(setViewportHeight, 100)
  })
}

/**
 * iOS 安全区域适配
 */
export const getSafeAreaInsets = () => {
  const style = getComputedStyle(document.documentElement)
  return {
    top: parseInt(style.getPropertyValue('--safe-area-inset-top') || '0'),
    bottom: parseInt(style.getPropertyValue('--safe-area-inset-bottom') || '0'),
    left: parseInt(style.getPropertyValue('--safe-area-inset-left') || '0'),
    right: parseInt(style.getPropertyValue('--safe-area-inset-right') || '0')
  }
}

/**
 * iOS 输入框优化
 * 防止自动缩放，处理焦点问题
 */
export const optimizeIOSInput = (inputElement: HTMLInputElement | HTMLTextAreaElement) => {
  if (!isIOS()) return

  // 设置字体大小为 16px，防止 iOS 自动缩放
  inputElement.style.fontSize = '16px'

  // 处理焦点时的滚动
  inputElement.addEventListener('focus', () => {
    setTimeout(() => {
      inputElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, 100)
  })
}

/**
 * iOS 触摸优化
 * 防止双击缩放，优化点击响应
 */
export const optimizeIOSTouch = () => {
  if (!isIOS()) return

  // 防止双击缩放
  document.addEventListener('touchend', (e) => {
    const now = Date.now()
    const DOUBLE_TAP_DELAY = 300

    if (now - (window as any).lastTouchEnd <= DOUBLE_TAP_DELAY) {
      e.preventDefault()
    }
    (window as any).lastTouchEnd = now
  }, { passive: false })

  // 优化点击响应
  document.addEventListener('touchstart', () => {
    // 快速响应触摸
  }, { passive: true })
}

/**
 * iOS 滚动优化
 * 修复 iOS 滚动卡顿问题
 */
export const optimizeIOSScroll = (scrollElement: HTMLElement) => {
  if (!isIOS()) return

  // 使用 -webkit-overflow-scrolling: touch
  scrollElement.style.webkitOverflowScrolling = 'touch'

  // 防止滚动卡顿
  scrollElement.style.transform = 'translateZ(0)'
}

/**
 * iOS 全局初始化
 */
export const initIOSOptimizations = () => {
  // 修复视口高度
  fixIOSViewportHeight()

  // 优化触摸
  optimizeIOSTouch()

  // 创建键盘处理器
  const keyboardHandler = new IOSKeyboardHandler()

  return {
    keyboardHandler,
    isIOS: isIOS(),
    isSafari: isSafari(),
    isPWA: isPWA()
  }
}

// 导出单例
export const iosUtils = {
  isIOS,
  isSafari,
  isIOSSafari,
  isPWA,
  fixIOSViewportHeight,
  getSafeAreaInsets,
  optimizeIOSInput,
  optimizeIOSTouch,
  optimizeIOSScroll,
  initIOSOptimizations
}