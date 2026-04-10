/**
 * iOS 适配测试报告生成器
 * 自动检测和测试 iOS Safari 适配情况
 */

import { isIOS, isSafari, isIOSSafari, isPWA, getSafeAreaInsets } from '../utils/iosUtils'

interface TestResult {
  name: string
  status: 'pass' | 'fail' | 'warning'
  description: string
  details?: string
}

interface IOSTestReport {
  timestamp: string
  deviceInfo: {
    isIOS: boolean
    isSafari: boolean
    isIOSSafari: boolean
    isPWA: boolean
    userAgent: string
    screenWidth: number
    screenHeight: number
    viewportWidth: number
    viewportHeight: number
  }
  safeAreaInsets: {
    top: number
    bottom: number
    left: number
    right: number
  }
  tests: TestResult[]
  overallStatus: 'pass' | 'fail' | 'warning'
  recommendations: string[]
}

/**
 * 测试视口配置
 */
const testViewportConfig = (): TestResult => {
  const viewportMeta = document.querySelector('meta[name="viewport"]')
  const content = viewportMeta?.getAttribute('content') || ''

  const hasWidth = content.includes('width=device-width')
  const hasViewportFit = content.includes('viewport-fit=cover')
  const hasNoScale = content.includes('user-scalable=no')

  if (hasWidth && hasViewportFit && hasNoScale) {
    return {
      name: '视口配置',
      status: 'pass',
      description: '视口配置正确，适配 iOS 设备',
      details: content
    }
  } else {
    return {
      name: '视口配置',
      status: 'fail',
      description: '视口配置不完整，可能影响 iOS 体验',
      details: `缺少: ${!hasWidth ? 'width=device-width' : ''} ${!hasViewportFit ? 'viewport-fit=cover' : ''} ${!hasNoScale ? 'user-scalable=no' : ''}`
    }
  }
}

/**
 * 测试 iOS meta 标签
 */
const testIOSMetaTags = (): TestResult => {
  const requiredTags = [
    'apple-mobile-web-app-capable',
    'apple-mobile-web-app-status-bar-style',
    'apple-mobile-web-app-title'
  ]

  const missingTags = requiredTags.filter(tag => {
    return !document.querySelector(`meta[name="${tag}"]`)
  })

  if (missingTags.length === 0) {
    return {
      name: 'iOS Meta 标签',
      status: 'pass',
      description: 'iOS Web App meta 标签配置完整',
      details: requiredTags.join(', ')
    }
  } else {
    return {
      name: 'iOS Meta 标签',
      status: 'warning',
      description: '部分 iOS meta 标签缺失',
      details: `缺少: ${missingTags.join(', ')}`
    }
  }
}

/**
 * 测试安全区域适配
 */
const testSafeArea = (): TestResult => {
  const insets = getSafeAreaInsets()

  if (insets.top > 0 || insets.bottom > 0) {
    return {
      name: '安全区域适配',
      status: 'pass',
      description: `安全区域 insets 已应用: top=${insets.top}px, bottom=${insets.bottom}px`,
      details: `left=${insets.left}px, right=${insets.right}px`
    }
  } else {
    // 检查是否有使用 env(safe-area-inset-*) 的样式
    const styles = getComputedStyle(document.documentElement)
    const hasSafeAreaSupport = styles.getPropertyValue('--safe-area-inset-top') !== ''

    return {
      name: '安全区域适配',
      status: 'warning',
      description: '安全区域 insets 未检测到，可能不影响当前设备',
      details: hasSafeAreaSupport ? 'CSS 支持 safe-area-inset' : '未使用 safe-area-inset'
    }
  }
}

/**
 * 测试输入框字体大小
 */
const testInputFontSize = (): TestResult => {
  const inputs = document.querySelectorAll('input, textarea')
  const smallInputs = Array.from(inputs).filter(input => {
    const fontSize = parseInt(getComputedStyle(input).fontSize)
    return fontSize < 16
  })

  if (smallInputs.length === 0) {
    return {
      name: '输入框字体大小',
      status: 'pass',
      description: '所有输入框字体大小 >= 16px，防止 iOS 自动缩放',
      details: `检测到 ${inputs.length} 个输入框`
    }
  } else {
    return {
      name: '输入框字体大小',
      status: 'fail',
      description: `${smallInputs.length} 个输入框字体大小 < 16px，iOS 会自动缩放`,
      details: smallInputs.map(input => `${input.tagName}: ${getComputedStyle(input).fontSize}`).join(', ')
    }
  }
}

/**
 * 测试触摸优化
 */
const testTouchOptimization = (): TestResult => {
  const body = document.body
  const style = getComputedStyle(body)

  const hasTapHighlight = style.webkitTapHighlightColor === 'transparent'
  const hasTouchCallout = style.webkitTouchCallout === 'none'
  const hasOverscrollBehavior = style.overscrollBehavior === 'none'

  if (hasTapHighlight && hasTouchCallout && hasOverscrollBehavior) {
    return {
      name: '触摸优化',
      status: 'pass',
      description: '触摸优化配置正确',
      details: '禁用点击高亮、长按菜单、橡皮筋效果'
    }
  } else {
    return {
      name: '触摸优化',
      status: 'warning',
      description: '部分触摸优化未应用',
      details: `缺少: ${!hasTapHighlight ? 'tap-highlight-color' : ''} ${!hasTouchCallout ? 'touch-callout' : ''} ${!hasOverscrollBehavior ? 'overscroll-behavior' : ''}`
    }
  }
}

/**
 * 测试视口高度
 */
const testViewportHeight = (): TestResult => {
  const vhVar = getComputedStyle(document.documentElement).getPropertyValue('--vh')
  const bodyHeight = document.body.clientHeight
  const windowHeight = window.innerHeight

  if (vhVar) {
    return {
      name: '视口高度',
      status: 'pass',
      description: '使用 CSS 变量 --vh 修复 iOS 视口高度',
      details: `--vh: ${vhVar}, body height: ${bodyHeight}px, window height: ${windowHeight}px`
    }
  } else {
    return {
      name: '视口高度',
      status: 'warning',
      description: '未使用 CSS 变量修复视口高度',
      details: 'iOS Safari 地址栏可能导致布局错乱'
    }
  }
}

/**
 * 测试滚动性能
 */
const testScrollPerformance = (): TestResult => {
  const scrollElements = document.querySelectorAll('.messages-container, .chat-room-messages')
  const optimizedElements = Array.from(scrollElements).filter(el => {
    const style = getComputedStyle(el)
    return style.webkitOverflowScrolling === 'touch' || style.transform.includes('translateZ')
  })

  if (scrollElements.length === 0) {
    return {
      name: '滚动性能',
      status: 'pass',
      description: '未检测到需要滚动的容器',
      details: '当前页面无滚动元素'
    }
  } else if (optimizedElements.length === scrollElements.length) {
    return {
      name: '滚动性能',
      status: 'pass',
      description: '所有滚动容器已优化',
      details: `检测到 ${scrollElements.length} 个滚动容器，全部优化`
    }
  } else {
    return {
      name: '滚动性能',
      status: 'warning',
      description: `${scrollElements.length - optimizedElements.length} 个滚动容器未优化`,
      details: 'iOS Safari 可能出现滚动卡顿'
    }
  }
}

/**
 * 测试 PWA 支持
 */
const testPWASupport = (): TestResult => {
  const manifestLink = document.querySelector('link[rel="manifest"]')
  const serviceWorker = 'serviceWorker' in navigator

  if (manifestLink && serviceWorker) {
    return {
      name: 'PWA 支持',
      status: 'pass',
      description: 'PWA 配置完整，支持离线使用',
      details: 'manifest.json + Service Worker'
    }
  } else {
    return {
      name: 'PWA 支持',
      status: 'warning',
      description: 'PWA 配置不完整',
      details: `缺少: ${!manifestLink ? 'manifest.json' : ''} ${!serviceWorker ? 'Service Worker' : ''}`
    }
  }
}

/**
 * 生成 iOS 测试报告
 */
export const generateIOSTestReport = (): IOSTestReport => {
  const tests: TestResult[] = [
    testViewportConfig(),
    testIOSMetaTags(),
    testSafeArea(),
    testInputFontSize(),
    testTouchOptimization(),
    testViewportHeight(),
    testScrollPerformance(),
    testPWASupport()
  ]

  // 统计测试结果
  const passCount = tests.filter(t => t.status === 'pass').length
  const failCount = tests.filter(t => t.status === 'fail').length
  const warningCount = tests.filter(t => t.status === 'warning').length

  // 判断总体状态
  const overallStatus: 'pass' | 'fail' | 'warning' =
    failCount > 0 ? 'fail' : warningCount > 0 ? 'warning' : 'pass'

  // 生成建议
  const recommendations: string[] = []
  tests.forEach(test => {
    if (test.status === 'fail') {
      recommendations.push(`🔴 ${test.name}: ${test.description}`)
    } else if (test.status === 'warning') {
      recommendations.push(`🟡 ${test.name}: ${test.description}`)
    }
  })

  if (overallStatus === 'pass') {
    recommendations.push('✅ iOS 适配良好，无明显问题')
  }

  return {
    timestamp: new Date().toISOString(),
    deviceInfo: {
      isIOS: isIOS(),
      isSafari: isSafari(),
      isIOSSafari: isIOSSafari(),
      isPWA: isPWA(),
      userAgent: navigator.userAgent,
      screenWidth: screen.width,
      screenHeight: screen.height,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight
    },
    safeAreaInsets: getSafeAreaInsets(),
    tests,
    overallStatus,
    recommendations
  }
}

/**
 * 打印测试报告到控制台
 */
export const printTestReport = (report: IOSTestReport) => {
  console.group('📱 iOS 适配测试报告')
  console.log('时间:', report.timestamp)
  console.log('设备信息:', report.deviceInfo)
  console.log('安全区域:', report.safeAreaInsets)
  console.groupEnd()

  console.group('测试结果')
  report.tests.forEach(test => {
    const icon = test.status === 'pass' ? '✅' : test.status === 'fail' ? '❌' : '⚠️'
    console.log(`${icon} ${test.name}: ${test.description}`)
    if (test.details) {
      console.log(`   详情: ${test.details}`)
    }
  })
  console.groupEnd()

  console.group('总体状态')
  const statusIcon = report.overallStatus === 'pass' ? '✅' : report.overallStatus === 'fail' ? '❌' : '⚠️'
  console.log(`${statusIcon} 总体状态: ${report.overallStatus}`)
  console.groupEnd()

  if (report.recommendations.length > 0) {
    console.group('建议')
    report.recommendations.forEach(rec => console.log(rec))
    console.groupEnd()
  }
}

/**
 * 运行测试并生成报告
 */
export const runIOSTests = () => {
  const report = generateIOSTestReport()
  printTestReport(report)
  return report
}