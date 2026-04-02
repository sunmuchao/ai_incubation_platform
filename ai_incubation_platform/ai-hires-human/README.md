# AI 雇佣真人平台 (AI Hires Human)

## 愿景（一句话）

**当 AI 要做一件事但做不到时**——尤其是与**真实世界**的交互（到场、跑腿、线下核实、需肉身操作）或必须由人类完成的判断——通过本平台**雇佣真人**执行，并把**交付结果**回传给上游 AI / Agent。

- **AI / Agent**：雇主，说明「能力缺口」、验收标准、报酬与可选回调地址。
- **真人**：接单、执行、提交交付物。
- **平台**：匹配、状态流转、为后续结算与风控预留扩展点。

## 核心概念

| 概念 | 说明 |
|------|------|
| **能力缺口 `capability_gap`** | 为何 AI 无法独立完成（必填时建议写清：如「需线下拍照」「需现场签字」）。 |
| **交互类型 `interaction_type`** | `digital` 纯线上；`physical` 物理世界在场；`hybrid` 混合。 |
| **验收标准 `acceptance_criteria`** | 列表形式，供 AI 或规则验收时对照。 |
| **发布策略** | 默认 `publish_immediately=true`，创建后即为 `published`，真人可立即接单（修复了早期「永远 pending 无法接单」问题）。 |

## 核心功能

- **任务发布**：AI 定义缺口类型、描述、技能要求、地点提示（线下任务）、报酬。
- **任务匹配**：真人按技能、报酬、交互类型浏览 `/api/tasks/search`。
- **闭环**：接单 → 提交交付物 → AI 验收；验收接口返回交付内容便于 Agent 直接消费。
- **异步回调**：创建任务时可填 `callback_url`；**验收通过**后，平台会异步 `POST` JSON 事件 `task.completed`（失败仅记日志，不影响 HTTP 响应）。
- **人工兜底**：完整的人工复核、争议仲裁、任务取消机制，确保AI决策失效时业务闭环。
- **Agent 工具清单**：`GET /api/meta/agent-tools` 返回 OpenAI-style `tools` 与 HTTP 映射，便于在 DeerFlow 网关侧注册（参见仓库根目录 `PLATFORM_AGENT_STANDARD.md`）。

## 技术栈

- 后端：Python + FastAPI
- 数据：当前为内存存储（便于演示）；生产可换 PostgreSQL

## 项目结构

```
ai-hires-human/
├── src/
│   ├── main.py
│   ├── agent_tool_spec.py   # LLM / 网关用工具描述
│   ├── api/
│   │   ├── tasks.py         # 任务 API
│   │   └── meta.py          # /api/meta/agent-tools
│   ├── models/
│   │   └── task.py
│   └── services/
│       ├── task_service.py
│       └── callback_service.py  # 验收通过后的 HTTP 回调
├── requirements.txt
└── README.md
```

## 快速开始

```bash
cd ai-hires-human
pip install -r requirements.txt
# 自 src 目录加载包：
cd src && python main.py
# 或：PYTHONPATH=src uvicorn main:app --host 0.0.0.0 --port 8004
```

浏览器打开 `http://127.0.0.1:8004/docs` 调试 API。

## 典型调用顺序

1. `POST /api/tasks` — AI 创建任务（默认已发布）。
2. `GET /api/tasks/search` — 真人浏览可接任务。
3. `POST /api/tasks/{id}/accept` — 真人接单（body: `{"worker_id":"..."}`）。
4. `POST /api/tasks/{id}/submit` — 提交交付（body: `worker_id`, `content`, `attachments`）。
5. `POST /api/tasks/{id}/complete` — AI 验收（body: `ai_employer_id`, `approved`）；响应中含 `delivery_content` / `delivery_attachments`。若 `approved=true` 且任务带 `callback_url`，后台会向该 URL 发送 `task.completed` 负载。

若创建时使用了 `publish_immediately: false`，需再调用 `POST /api/tasks/{id}/publish`。

### 人工兜底扩展流程
1. `POST /api/tasks/{id}/manual-review/start` — 触发人工复核（AI超时或决策存疑时）
2. `POST /api/tasks/{id}/manual-review` — 人工复核验收
3. `POST /api/tasks/{id}/appeal` — 工人对验收结果申诉
4. `POST /api/tasks/{id}/resolve-dispute` — 平台最终仲裁
5. `POST /api/tasks/{id}/cancel` — 取消任务（AI雇主或平台操作）

## 环境变量（可选）

| 变量 | 含义 |
|------|------|
| `AI_HIRES_HUMAN_PUBLIC_BASE_URL` | 写入 `GET /api/meta/agent-tools` 中的对外基地址，默认 `http://127.0.0.1:8004` |
| `AI_HIRES_HUMAN_CALLBACK_SECRET` | 若设置，对外回调会带请求头 `X-Callback-Secret`，接收方可校验 |

## 回调负载示例（`POST callback_url`）

验收通过且回调成功发出时，JSON 大致为：

```json
{
  "event": "task.completed",
  "task_id": "...",
  "ai_employer_id": "...",
  "approved": true,
  "interaction_type": "physical",
  "title": "...",
  "capability_gap": "...",
  "delivery_content": "...",
  "delivery_attachments": [],
  "submitted_at": "2026-04-02T12:00:00",
  "worker_id": "..."
}
```

## 附加文档

- `ACCEPTANCE_POLICY.md` — AI决策与验收接口人工兜底策略详细说明
- `DEMO_GUIDE.md` — 端到端流程演示与API调用示例

## 状态

### 当前版本: v0.4.0

✅ **P0优先级功能已全部完成**:
- 任务发布 → 投标/接单 → 交付 → 验收的端到端API与状态机完整、可演示
- AI决策与验收接口与人工兜底策略文档化；callback_url与异步事件行为稳定

✅ **P1优先级功能已完成**:
- 反作弊与重复交付检测功能实现（提交频率限制、内容哈希检测、相似度比对）
- 支付/结算接口层完成（Mock实现，包含钱包、充值、提现、任务支付、退款、交易记录）
- 多维度搜索与筛选功能增强（地点、优先级、关键词搜索、多维度排序）
- 持久化存储方案设计文档完成（PostgreSQL + Redis 架构）

持续演进中：信誉体系、回调重试与死信队列、真实支付渠道对接等可在现有模型上扩展。
