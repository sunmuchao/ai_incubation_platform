/**
 * 完整的移动端适配测试框架
 * 支持 iOS、Android、WebView、平板等设备测试
 */

import { getDeviceInfo, isIOS, isAndroid, isTablet, isWebView, isPWA, getSafeAreaInsets } from '../utils/iosUtils'

interface TestResult {
  name: string
  status: 'pass' | 'fail' | 'warning'
  description: string
  details?: string
  category: 'ios' | 'android' | 'webview' | 'tablet' | 'general'
}

interface MobileTestReport {
  timestamp: string
  deviceInfo: ReturnType<typeof getDeviceInfo>
  safeAreaInsets: ReturnType<typeof getSafeAreaInsets>
  tests: TestResult[]
  overallStatus: 'pass' | 'fail' | 'warning'
  recommendations: string[]
  summary: {
    total: number
    passed: number
    failed: number
    warnings: number
  }
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
  const hasShrinkToFit = content.includes('shrink-to-fit=no')

  if (hasWidth && hasViewportFit && hasNoScale && hasShrinkToFit) {
    return {
      name: '视口配置',
      status: 'pass',
      description: '视口配置完整，适配所有移动设备',
      details: content,
      category: 'general'
    }
  } else {
    return {
      name: '视口配置',
      status: 'fail',
      description: '视口配置不完整，影响移动端体验',
      details: `缺少: ${!hasWidth ? 'width=device-width' : ''} ${!hasViewportFit ? 'viewport-fit=cover' : ''} ${!hasNoScale ? 'user-scalable=no' : ''} ${!hasShrinkToFit ? 'shrink-to-fit=no' : ''}`,
      category: 'general'
    }
  }
}

/**
 * 测试 iOS Meta 标签
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
      details: requiredTags.join(', '),
      category: 'ios'
    }
  } else {
    return {
      name: 'iOS Meta 标签',
      status: 'warning',
      description: '部分 iOS meta 标签缺失',
      details: `缺少: ${missingTags.join(', ')}`,
      category: 'ios'
    }
  }
}

/**
 * 测试安全区域适配
 */
const testSafeArea = (): TestResult => {
  const insets = getSafeAreaInsets()
  const deviceInfo = getDeviceInfo()

  if (deviceInfo.isIOS || deviceInfo.isAndroid) {
    if (insets.top > 0 || insets.bottom > 0) {
      return {
        name: '安全区域适配',
        status: 'pass',
        description: `安全区域已应用: top=${insets.top}px, bottom=${insets.bottom}px`,
        details: `left=${insets.left}px, right=${insets.right}px`,
        category: 'general'
      }
    } else {
      // 检查是否有使用 env(safe-area-inset-*) 的样式
      const styles = getComputedStyle(document.documentElement)
      const hasSafeAreaSupport = styles.getPropertyValue('--safe-area-inset-top') !== ''

      return {
        name: '安全区域适配',
        status: 'warning',
        description: '安全区域未检测到，可能不影响当前设备',
        details: hasSafeAreaSupport ? 'CSS 支持 safe-area-inset' : '未使用 safe-area-inset',
        category: 'general'
      }
    }
  } else {
    return {
      name: '安全区域适配',
      status: 'pass',
      description: '桌面设备无需安全区域适配',
      category: 'general'
    }
  }
}

/**
 * 测试输入框字体大小
 */
const testInputFontSize = (): TestResult => {
  const inputs = document.querySelectorAll('input, textarea')
  const deviceInfo = getDeviceInfo()

  if (inputs.length === 0) {
    return {
      name: '输入框字体大小',
      status: 'pass',
      description: '当前页面无输入框',
      category: 'general'
    }
  }

  const smallInputs = Array.from(inputs).filter(input => {
    const fontSize = parseInt(getComputedStyle(input).fontSize)
    return fontSize < 16
  })

  if (smallInputs.length === 0) {
    return {
      name: '输入框字体大小',
      status: 'pass',
      description: '所有输入框字体大小 >= 16px，防止移动端自动缩放',
      details: `检测到 ${inputs.length} 个输入框`,
      category: 'general'
    }
  } else {
    return {
      name: '输入框字体大小',
      status: 'fail',
      description: `${smallInputs.length} 个输入框字体大小 < 16px，移动端会自动缩放`,
      details: smallInputs.map(input => `${input.tagName}: ${getComputedStyle(input).fontSize}`).join(', '),
      category: 'general'
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
      details: '禁用点击高亮、长按菜单、橡皮筋效果',
      category: 'general'
    }
  } else {
    return {
      name: '触摸优化',
      status: 'warning',
      description: '部分触摸优化未应用',
      details: `缺少: ${!hasTapHighlight ? 'tap-highlight-color' : ''} ${!hasTouchCallout ? 'touch-callout' : ''} ${!hasOverscrollBehavior ? 'overscroll-behavior' : ''}`,
      category: 'general'
    }
  }
}

/**
 * 测试视口高度
 */
const testViewportHeight = (): TestResult => {
  const vhVar = getComputedStyle(document.documentElement).getPropertyValue('--vh')

  if (vhVar) {
    return {
      name: '视口高度',
      status: 'pass',
      description: '使用 CSS 变量 --vh 修复移动端视口高度',
      details: `--vh: ${vhVar}`,
      category: 'general'
    }
  } else {
    return {
      name: '视口高度',
      status: 'warning',
      description: '未使用 CSS 变量修复视口高度',
      details: '移动端浏览器地址栏可能导致布局错乱',
      category: 'general'
    }
  }
}

/**
 * 测试滚动性能
 */
const testScrollPerformance = (): TestResult => {
  const scrollElements = document.querySelectorAll('.messages-container, .chat-room-messages, .scrollable-container')
  const optimizedElements = Array.from(scrollElements).filter(el => {
    const style = getComputedStyle(el)
    return style.webkitOverflowScrolling === 'touch' || style.transform.includes('translateZ')
  })

  if (scrollElements.length === 0) {
    return {
      name: '滚动性能',
      status: 'pass',
      description: '当前页面无滚动容器',
      details: '当前页面无滚动元素',
      category: 'general'
    }
  } else if (optimizedElements.length === scrollElements.length) {
    return {
      name: '滚动性能',
      status: 'pass',
      description: '所有滚动容器已优化',
      details: `检测到 ${scrollElements.length} 个滚动容器，全部优化`,
      category: 'general'
    }
  } else {
    return {
      name: '滚动性能',
      status: 'warning',
      description: `${scrollElements.length - optimizedElements.length} 个滚动容器未优化`,
      details: '移动端可能出现滚动卡顿',
      category: 'general'
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
      details: 'manifest.json + Service Worker',
      category: 'general'
    }
  } else {
    return {
      name: 'PWA 支持',
      status: 'warning',
      description: 'PWA 配置不完整',
      details: `缺少: ${!manifestLink ? 'manifest.json' : ''} ${!serviceWorker ? 'Service Worker' : ''}`,
      category: 'general'
    }
  }
}

/**
 * 测试 iOS 特定问题
 */
const testIOSSpecific = (): TestResult[] => {
  const results: TestResult[] = []
  const deviceInfo = getDeviceInfo()

  if (!deviceInfo.isIOS) {
    results.push({
      name: 'iOS 设备检测',
      status: 'pass',
      description: '非 iOS 设备，跳过 iOS 特定测试',
      category: 'ios'
    })
    return results
  }

  // 测试 iOS Safari 地址栏问题
  const homeLayout = document.querySelector('.home-layout') as HTMLElement
  if (homeLayout) {
    const style = getComputedStyle(homeLayout)
    const hasWebkitFillAvailable = style.height.includes('-webkit-fill-available') ||
      homeLayout.style.height.includes('-webkit-fill-available')

    if (hasWebkitFillAvailable) {
      results.push({
        name: 'iOS 视口高度修复',
        status: 'pass',
        description: '使用 -webkit-fill-available 修复 iOS Safari 地址栏问题',
        category: 'ios'
      })
    } else {
      results.push({
        name: 'iOS 视口高度修复',
        status: 'warning',
        description: '未使用 -webkit-fill-available 修复视口高度',
        details: 'iOS Safari 地址栏可能导致布局问题',
        category: 'ios'
      })
    }
  }

  // 测试 iOS 输入框内阴影
  const inputs = document.querySelectorAll('input, textarea')
  const hasInnerShadow = Array.from(inputs).some(input => {
    const style = getComputedStyle(input)
    return style.webkitBoxShadow !== 'none' && style.boxShadow !== 'none'
  })

  if (hasInnerShadow) {
    results.push({
      name: 'iOS 输入框样式',
      status: 'warning',
      description: '部分输入框仍有内阴影',
      details: 'iOS Safari 默认内阴影可能影响美观',
      category: 'ios'
    })
  } else {
    results.push({
      name: 'iOS 输入框样式',
      status: 'pass',
      description: '已移除 iOS 输入框默认内阴影',
      category: 'ios'
    })
  }

  return results
}

/**
 * 测试 Android 特定问题
 */
const testAndroidSpecific = (): TestResult[] => {
  const results: TestResult[] = []
  const deviceInfo = getDeviceInfo()

  if (!deviceInfo.isAndroid) {
    results.push({
      name: 'Android 设备检测',
      status: 'pass',
      description: '非 Android 设备，跳过 Android 特定测试',
      category: 'android'
    })
    return results
  }

  // 测试 Android Chrome 工具栏
  const inputArea = document.querySelector('.chat-room-input-area') as HTMLElement
  if (inputArea) {
    const style = getComputedStyle(inputArea)
    const hasSticky = style.position === 'sticky'
    const hasTransform = style.transform.includes('translateZ')

    if (hasSticky || hasTransform) {
      results.push({
        name: 'Android 键盘适配',
        status: 'pass',
        description: 'Android Chrome 键盘弹起时布局已优化',
        category: 'android'
      })
    } else {
      results.push({
        name: 'Android 键盘适配',
        status: 'warning',
        description: 'Android Chrome 键盘弹起时可能遮挡内容',
        category: 'android'
      })
    }
  }

  // 测试 Android 触摸反馈
  const buttons = document.querySelectorAll('button, .ant-btn')
  const hasTouchAction = Array.from(buttons).some(btn => {
    const style = getComputedStyle(btn)
    return style.touchAction === 'manipulation'
  })

  if (hasTouchAction) {
    results.push({
      name: 'Android 触摸优化',
      status: 'pass',
      description: 'Android 触摸响应已优化',
      category: 'android'
    })
  } else {
    results.push({
      name: 'Android 触摸优化',
      status: 'warning',
      description: 'Android 触摸响应可能存在延迟',
      category: 'android'
    })
  }

  return results
}

/**
 * 测试 WebView 特定问题
 */
const testWebViewSpecific = (): TestResult[] => {
  const results: TestResult[] = []
  const deviceInfo = getDeviceInfo()

  if (!deviceInfo.isWebView) {
    results.push({
      name: 'WebView 检测',
      status: 'pass',
      description: '非 WebView 环境，跳过 WebView 测试',
      details: `浏览器类型: ${deviceInfo.browserType}`,
      category: 'webview'
    })
    return results
  }

  // 测试 WebView 下拉刷新
  const body = document.body
  const style = getComputedStyle(body)
  const hasOverscrollBehavior = style.overscrollBehavior === 'none' || style.overscrollBehaviorY === 'contain'

  if (hasOverscrollBehavior) {
    results.push({
      name: 'WebView 下拉刷新',
      status: 'pass',
      description: '已禁用 WebView 下拉刷新',
      details: `WebView 类型: ${deviceInfo.browserType}`,
      category: 'webview'
    })
  } else {
    results.push({
      name: 'WebView 下拉刷新',
      status: 'warning',
      description: 'WebView 可能触发下拉刷新',
      details: '建议添加 overscroll-behavior: contain',
      category: 'webview'
    })
  }

  // 测试 WebView 长按菜单
  const hasTouchCallout = style.webkitTouchCallout === 'none'

  if (hasTouchCallout) {
    results.push({
      name: 'WebView 长按菜单',
      status: 'pass',
      description: '已禁用 WebView 长按菜单',
      category: 'webview'
    })
  } else {
    results.push({
      name: 'WebView 长按菜单',
      status: 'warning',
      description: 'WebView 长按可能弹出系统菜单',
      category: 'webview'
    })
  }

  // 测试 PWA 安装提示
  const pwaPrompt = document.querySelector('.pwa-install-prompt')
  if (pwaPrompt) {
    const style = getComputedStyle(pwaPrompt)
    if (style.display === 'none') {
      results.push({
        name: 'WebView PWA 提示',
        status: 'pass',
        description: 'WebView 模式下已隐藏 PWA 安装提示',
        category: 'webview'
      })
    } else {
      results.push({
        name: 'WebView PWA 提示',
        status: 'warning',
        description: 'WebView 模式下应隐藏 PWA 安装提示',
        category: 'webview'
      })
    }
  } else {
    results.push({
      name: 'WebView PWA 提示',
      status: 'pass',
      description: '未检测到 PWA 安装提示组件',
      category: 'webview'
    })
  }

  return results
}

/**
 * 测试平板设备特定问题
 */
const testTabletSpecific = (): TestResult[] => {
  const results: TestResult[] = []
  const deviceInfo = getDeviceInfo()

  if (!deviceInfo.isTablet) {
    results.push({
      name: '平板设备检测',
      status: 'pass',
      description: '非平板设备，跳过平板测试',
      category: 'tablet'
    })
    return results
  }

  // 测试平板布局适配
  const chatInterface = document.querySelector('.chat-interface') as HTMLElement
  if (chatInterface) {
    const style = getComputedStyle(chatInterface)
    const maxWidth = parseInt(style.maxWidth)

    if (maxWidth > 0 && maxWidth < window.innerWidth) {
      results.push({
        name: '平板布局适配',
        status: 'pass',
        description: `平板布局已居中，最大宽度: ${maxWidth}px`,
        category: 'tablet'
      })
    } else {
      results.push({
        name: '平板布局适配',
        status: 'warning',
        description: '平板布局可能未优化',
        details: '建议设置最大宽度并居中显示',
        category: 'tablet'
      })
    }
  }

  // 测试平板触摸区域
  const buttons = document.querySelectorAll('button, .ant-btn')
  const smallButtons = Array.from(buttons).filter(btn => {
    const style = getComputedStyle(btn)
    const height = parseInt(style.height)
    const width = parseInt(style.width)
    return height < 48 || width < 48
  })

  if (smallButtons.length === 0) {
    results.push({
      name: '平板触摸区域',
      status: 'pass',
      description: '所有按钮触摸区域 >= 48px',
      category: 'tablet'
    })
  } else {
    results.push({
      name: '平板触摸区域',
      status: 'warning',
      description: `${smallButtons.length} 个按钮触摸区域 < 48px`,
      details: '平板设备建议按钮尺寸 >= 48px',
      category: 'tablet'
    })
  }

  return results
}

/**
 * 生成完整的移动端测试报告
 */
export const generateMobileTestReport = (): MobileTestReport => {
  const deviceInfo = getDeviceInfo()

  // 通用测试
  const generalTests: TestResult[] = [
    testViewportConfig(),
    testSafeArea(),
    testInputFontSize(),
    testTouchOptimization(),
    testViewportHeight(),
    testScrollPerformance(),
    testPWASupport()
  ]

  // iOS 特定测试
  const iosTests = testIOSSpecific()

  // Android 特定测试
  const androidTests = testAndroidSpecific()

  // WebView 特定测试
  const webviewTests = testWebViewSpecific()

  // 平板设备测试
  const tabletTests = testTabletSpecific()

  // 合并所有测试
  const allTests: TestResult[] = [
    ...generalTests,
    testIOSMetaTags(),
    ...iosTests,
    ...androidTests,
    ...webviewTests,
    ...tabletTests
  ]

  // 统计测试结果
  const passed = allTests.filter(t => t.status === 'pass').length
  const failed = allTests.filter(t => t.status === 'fail').length
  const warnings = allTests.filter(t => t.status === 'warning').length

  // 判断总体状态
  const overallStatus: 'pass' | 'fail' | 'warning' =
    failed > 0 ? 'fail' : warnings > 0 ? 'warning' : 'pass'

  // 生成建议
  const recommendations: string[] = []
  allTests.forEach(test => {
    if (test.status === 'fail') {
      recommendations.push(`🔴 [${test.category.toUpperCase()}] ${test.name}: ${test.description}`)
    } else if (test.status === 'warning') {
      recommendations.push(`🟡 [${test.category.toUpperCase()}] ${test.name}: ${test.description}`)
    }
  })

  if (overallStatus === 'pass') {
    recommendations.push('✅ 所有测试通过，移动端适配良好')
  }

  return {
    timestamp: new Date().toISOString(),
    deviceInfo,
    safeAreaInsets: getSafeAreaInsets(),
    tests: allTests,
    overallStatus,
    recommendations,
    summary: {
      total: allTests.length,
      passed,
      failed,
      warnings
    }
  }
}

/**
 * 打印测试报告到控制台
 */
export const printTestReport = (report: MobileTestReport) => {
  console.group('📱 移动端适配测试报告')
  console.log('时间:', report.timestamp)
  console.groupEnd()

  console.group('设备信息')
  console.log('设备类型:', report.deviceInfo.deviceType)
  console.log('操作系统:', report.deviceInfo.isIOS ? 'iOS' : report.deviceInfo.isAndroid ? 'Android' : '其他')
  console.log('浏览器:', report.deviceInfo.browserType)
  console.log('WebView:', report.deviceInfo.isWebView ? '是' : '否')
  console.log('PWA 模式:', report.deviceInfo.isPWA ? '是' : '否')
  console.log('屏幕:', `${report.deviceInfo.screenWidth}x${report.deviceInfo.screenHeight}`)
  console.log('视口:', `${report.deviceInfo.viewportWidth}x${report.deviceInfo.viewportHeight}`)
  console.groupEnd()

  console.group('测试结果汇总')
  console.log(`总计: ${report.summary.total} 项`)
  console.log(`✅ 通过: ${report.summary.passed} 项`)
  console.log(`❌ 失败: ${report.summary.failed} 项`)
  console.log(`⚠️ 警告: ${report.summary.warnings} 项`)
  console.groupEnd()

  console.group('详细测试结果')
  report.tests.forEach(test => {
    const icon = test.status === 'pass' ? '✅' : test.status === 'fail' ? '❌' : '⚠️'
    console.log(`${icon} [${test.category.toUpperCase()}] ${test.name}: ${test.description}`)
    if (test.details) {
      console.log(`   详情: ${test.details}`)
    }
  })
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
export const runMobileTests = () => {
  const report = generateMobileTestReport()
  printTestReport(report)
  return report
}

// 自动运行测试（开发环境）
if (process.env.NODE_ENV === 'development') {
  // 延迟执行，确保 DOM 完全加载
  setTimeout(() => {
    console.log('\n🔍 自动运行移动端适配测试...')
    runMobileTests()
  }, 1000)
}