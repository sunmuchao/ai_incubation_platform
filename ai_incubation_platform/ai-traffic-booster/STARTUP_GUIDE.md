# AI Traffic Booster 启动指南

## 快速启动

### 前提条件

1. Python 3.9+
2. Node.js 18+
3. 已安装依赖

### 步骤 1: 启动后端

```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform/ai-traffic-booster

# 激活虚拟环境
source venv/bin/activate

# 安装依赖 (如果需要)
pip install -r requirements.txt

# 启动后端服务
python src/main.py

# 后端将运行在 http://localhost:8000
# API 文档：http://localhost:8000/docs
```

### 步骤 2: 启动前端

```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform/ai-traffic-booster/frontend-vue

# 安装依赖 (如果需要)
npm install

# 启动开发服务器
npm run dev

# 前端将运行在 http://localhost:3000
```

### 步骤 3: 访问应用

打开浏览器访问：http://localhost:3000

---

## 功能测试

### 测试 AI 对话

1. 访问 http://localhost:3000
2. 在聊天框输入："分析上周流量为什么下跌"
3. AI 将返回分析结果和可视化图表

### 测试 Agent 可视化

1. 点击侧边栏 "Agent 中心"
2. 查看各 Agent 的工作状态

### 测试主动推送

1. 查看右侧 "AI 主动发现" 面板
2. 查看 AI 推送的异常和机会

---

## API 测试

### 使用 Swagger UI

访问：http://localhost:8000/docs

### 测试 Chat API

```bash
# 发送消息
curl -X POST "http://localhost:8000/api/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "分析上周流量", "user_id": "test_user"}'

# 获取 AI 状态
curl "http://localhost:8000/api/chat/status"

# 获取洞察
curl "http://localhost:8000/api/chat/insights"
```

---

## 常见问题

### 端口被占用

如果 3000 或 8000 端口被占用，可以：

**前端**: 修改 `vite.config.ts` 中的 `port`
**后端**: 修改 `src/core/config.py` 中的端口设置

### 依赖问题

**Python**:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Node.js**:
```bash
cd frontend-vue
rm -rf node_modules package-lock.json
npm install
```

### DeerFlow AI 不可用

如果 DeerFlow AI 服务不可用，系统将自动切换到 fallback 模式（基于规则的引擎）。

---

## 项目结构

```
ai-traffic-booster/
├── src/                    # 后端代码
│   ├── api/               # API 路由
│   │   └── chat.py        # AI 对话 API
│   ├── agents/            # AI Agent
│   │   ├── traffic_agent.py
│   │   └── deerflow_client.py
│   ├── workflows/         # 工作流
│   │   ├── traffic_workflows.py
│   │   └── strategy_workflows.py
│   └── main.py            # 主入口
├── frontend-vue/          # 前端代码
│   ├── src/
│   │   ├── views/
│   │   │   ├── AIChatHome.vue
│   │   │   └── AgentsOverview.vue
│   │   ├── components/generative/
│   │   └── api/chat.ts
│   └── package.json
└── STARTUP_GUIDE.md       # 本文档
```

---

## 开发建议

### 后端开发

1. 使用 `source venv/bin/activate` 激活虚拟环境
2. 使用 `python src/main.py` 启动服务
3. 访问 http://localhost:8000/docs 查看 API 文档

### 前端开发

1. 使用 `npm run dev` 启动开发服务器
2. 支持热重载，修改代码后自动刷新
3. 使用 Chrome DevTools 调试

---

## 联系支持

如有问题，请查看：
- `AI_NATIVE_UI_DESIGN.md` - UI 设计文档
- `IMPLEMENTATION_SUMMARY.md` - 实现总结
- `AI_NATIVE_REDESIGN_WHITEPAPER.md` - 架构白皮书
