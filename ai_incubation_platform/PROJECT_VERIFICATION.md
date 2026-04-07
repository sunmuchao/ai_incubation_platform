# 项目验证指南

## 问题诊断

如果访问某个端口打开的不是对应的项目，可能是以下原因：

1. **浏览器缓存** - 清除浏览器缓存后重试
2. **前端未运行** - 确保前端开发服务器正在运行
3. **端口冲突** - 检查是否有其他程序占用了端口

## 项目唯一标识

每个项目都有独特的页面标题，可以通过浏览器标题栏确认访问的是正确的项目：

| 项目 | 端口 | 页面标题 |
|------|------|----------|
| ai-community-buying | 3003 | AI 社区团购平台 |
| ai-hires-human | 3004 | AI 雇佣真人平台 |
| ai-employee-platform | 3002 | AI Employee Platform - AI Native |
| human-ai-community | 3000 | Human-AI 社区 |
| matchmaker-agent | 3005 | AI Matchmaker - 智能匹配平台 |
| ai-code-understanding | 3006 | AI Code Understanding - 代码认知基础设施层 |
| ai-opportunity-miner | 3007 | AI Opportunity Miner - AI Native 商业机会挖掘平台 |
| ai-traffic-booster | 3008 | AI Traffic Booster - AI 驱动的增长顾问 |
| ai-runtime-optimizer | 3009 | AI Runtime Optimizer - 智能运行态优化平台 |
| data-agent-connector | 3010 | Data-Agent Connector | AI Native 数据网关平台 |

## 启动命令

### ai-employee-platform (端口 3002)
```bash
cd ai-employee-platform/frontend
npm run dev
# 访问 http://localhost:3002
# 页面标题：AI Employee Platform - AI Native
```

### ai-community-buying (端口 3003)
```bash
cd ai-community-buying/frontend
npm run dev
# 访问 http://localhost:3003
# 页面标题：AI 社区团购平台
```

### ai-hires-human (端口 3004)
```bash
cd ai-hires-human/frontend
npm run dev
# 访问 http://localhost:3004
# 页面标题：AI 雇佣真人平台
```

### human-ai-community (端口 3000)
```bash
cd human-ai-community/frontend-next
npm run dev
# 访问 http://localhost:3000
# 页面标题：Human-AI 社区
```

## 清除浏览器缓存

### Chrome/Edge
1. 按 `Ctrl+Shift+Delete` (Windows) 或 `Cmd+Shift+Delete` (Mac)
2. 选择"缓存的图片和文件"
3. 点击"清除数据"

### 强制刷新
- Windows: `Ctrl+F5`
- Mac: `Cmd+Shift+R`

## 检查端口占用

```bash
# 查看端口占用
lsof -i :3002  # 检查 3002 端口
lsof -i :3003  # 检查 3003 端口
```

## 验证步骤

1. 启动前端开发服务器
2. 等待构建完成（看到 "ready" 或 "Local" 字样）
3. 打开浏览器访问对应端口
4. 检查页面标题是否正确
5. 如果不正确，清除浏览器缓存后重试

---

**更新时间**: 2026-04-06
