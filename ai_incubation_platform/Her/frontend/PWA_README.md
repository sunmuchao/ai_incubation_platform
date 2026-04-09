# Her PWA - iOS/Android 移动应用适配

## 📱 快速开始

### 开发模式

```bash
cd Her/frontend

# 安装依赖（如果还没有安装）
npm install

# 启动开发服务器
npm run dev
```

### 生产构建

```bash
# 构建 PWA 版本
npm run build

# 预览构建结果
npm run preview
```

---

## 📲 安装到手机

### iOS (iPhone)

1. 在 Safari 中访问应用地址
2. 点击底部分享按钮（⬆️）
3. 选择「添加到主屏幕」
4. 点击右上角「添加」

### Android

1. 在 Chrome 中访问应用地址
2. 点击浏览器菜单（三个点）
3. 选择「添加到主屏幕」
4. 确认添加

或者等待自动弹出的安装提示。

---

## 🎯 PWA 特性

### 离线支持
- 应用外壳缓存
- 字体资源缓存
- 静态资源缓存

### 移动端优化
- 安全区域适配（刘海屏/灵动岛）
- 触摸反馈优化
- 禁用双击缩放
- 16px+ 输入框字体

### 全屏体验
- 独立 App 图标
- 无浏览器地址栏
- 原生般流畅动画

---

## 📁 新增文件说明

```
Her/frontend/
├── public/
│   ├── manifest.webmanifest      # PWA 清单文件
│   ├── favicon.svg               # App 图标（SVG）
│   ├── pwa-192x192.png          # PWA 图标（待生成）
│   ├── pwa-512x512.png          # PWA 图标（待生成）
│   └── apple-touch-icon.png     # iOS 图标（待生成）
├── src/
│   ├── components/
│   │   └── PWAInstallPrompt.tsx  # PWA 安装提示组件
│   └── styles/
│       └── pwa-global.less       # PWA 全局样式
└── iOS_INSTALL_GUIDE.md          # iOS 安装指南
```

---

## 🔧 配置说明

### Vite PWA 插件配置

在 `vite.config.ts` 中配置了：
- manifest 生成
- Service Worker 缓存策略
- 离线资源缓存

### manifest.webmanifest

定义了：
- App 名称和描述
- 主题颜色
- 图标尺寸
- 显示模式（standalone）

### index.html

添加了：
- iOS 专用 meta 标签
- 视口优化配置
- PWA 相关 link

---

## 🎨 图标资源

### 需要的图标尺寸

| 文件名 | 尺寸 | 用途 |
|--------|------|------|
| pwa-192x192.png | 192x192 | Android 主屏幕 |
| pwa-512x512.png | 512x512 | PWA 通用 |
| apple-touch-icon.png | 180x180 | iOS 主屏幕 |
| favicon.svg | 任意 | 浏览器标签 |

### 生成图标

可以使用在线工具：
- [PWA Icon Generator](https://realfavicongenerator.net/)
- [Figma](https://figma.com) 导出

---

## 📱 移动端适配检查清单

- [x] 视口配置（禁用缩放）
- [x] 安全区域适配（env(safe-area-inset)）
- [x] 触摸反馈优化
- [x] 输入框字体大小（16px+）
- [x] 按钮最小点击区域（44x44）
- [x] 禁用长按菜单
- [x] 禁用图片保存
- [x] 状态栏样式
- [x] 横屏适配
- [x] 暗黑模式支持

---

## 🐛 已知问题

### iOS Safari
- 地址栏高度变化可能导致布局抖动
  - 解决：使用 `100dvh` 代替 `100vh`

### Android Chrome
- 部分设备底部导航栏遮挡
  - 解决：`padding-bottom: env(safe-area-inset-bottom)`

---

## 📊 性能优化建议

1. **图片优化**
   - 使用 WebP 格式
   - 懒加载长列表图片

2. **缓存策略**
   - Service Worker 缓存静态资源
   - API 响应使用网络优先

3. **代码分割**
   - 路由级别代码分割
   - 组件懒加载

---

## 🔗 相关文档

- [iOS_INSTALL_GUIDE.md](./iOS_INSTALL_GUIDE.md) - 详细安装指南
- [PWA_BEST_PRACTICES.md](https://web.dev/pwa-best-practices/) - PWA 最佳实践

---

*最后更新：2026-04-08*