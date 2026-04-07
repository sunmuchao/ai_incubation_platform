# AI Incubation Platform - Portal

**版本**: v3.0.0 AI Native (DeerFlow 2.0)
**状态**: 已完成

AI 孵化平台统一入口门户，通过自然语言对话访问所有子项目能力。

---

## 快速开始

### 安装

```bash
cd platform-portal
pip install -e .
```

### 运行

```bash
python -m uvicorn src.main:app --reload --port 8000
```

访问 API 文档：http://localhost:8000/docs

### 测试

```bash
python test_ai_native.py
```

---

## 核心功能

### 1. 对话式交互

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "我想发布一个线下数据采集任务", "user_id": "user_001"}'
```

### 2. 跨项目工作流

```bash
curl -X POST http://localhost:8000/api/v1/workflows/startup_journey/execute \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "input_data": {"industry": "电商"}}'
```

---

## 架构

```
用户 -> 自然语言对话 -> PortalAgent -> 意图识别 -> 路由/编排 -> 子项目
```

### 组件

- **PortalAgent**: 门户智能体，核心决策引擎
- **Tools**: 意图识别、路由分发、结果聚合、跨项目编排
- **Workflows**: 预定义的跨项目工作流模板
- **API**: 对话式交互接口

### 子项目 (12 个)

| 项目 | 端口 | 功能 |
|------|------|------|
| ai-hires-human | 8001 | AI 雇佣真人平台 |
| ai-employee-platform | 8002 | AI 员工平台 |
| human-ai-community | 8003 | 人类-AI 社区 |
| ai-community-buying | 8004 | AI 社区团购 |
| ai-opportunity-miner | 8005 | AI 商机挖掘 |
| ai-code-understanding | 8008 | AI 代码理解 |
| ... | ... | ... |

---

## 文档

- [AI Native 重设计白皮书](AI_NATIVE_REDESIGN_WHITEPAPER.md)
- [AI Native 完成报告](AI_NATIVE_COMPLETION_REPORT.md)

---

## 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| PORT | 服务端口 | 8000 |
| DEBUG | 调试模式 | false |
| DEERFLOW_API_KEY | DeerFlow API 密钥 | None |

---

*AI Native 成熟度：L2 (助手级)*
