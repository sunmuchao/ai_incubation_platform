# Writing Effective Tools for Agents — with Agents

> **来源**: Anthropic Engineering Blog
> **发布日期**: Sep 11, 2025
> **作者**: Ken Aizawa 及 Anthropic 团队

---

## 核心观点

Agents 的有效性取决于我们给它们的工具。本文分享如何编写高质量工具和评估，以及如何使用 Claude 来优化其自身的工具。

---

## 一、什么是工具？

### 1.1 传统软件 vs Agent 工具

| 类型 | 特点 | 示例 |
|------|------|------|
| **传统软件** | 确定性系统，相同输入 → 相同输出 | `getWeather("NYC")` 每次调用方式相同 |
| **Agent 工具** | 确定性系统与非确定性 Agent 之间的契约 | 用户问"今天要带伞吗？"，Agent 可能调用天气工具、用通用知识回答、或先问澄清问题 |

### 1.2 设计思维转变

**核心转变**: 不能像为开发者写 API 那样写工具，需要为 Agent 设计工具。

**目标**: 增加 Agent 有效解决问题的"面积"，让工具支持多种成功策略。

**发现**: 最"适合 Agent"的工具，人类也觉得直观易懂。

---

## 二、如何编写工具

### 2.1 流程概览

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: 快速原型 → 本地测试                                      │
│  Step 2: 创建评估 → 测量性能                                      │
│  Step 3: 与 Agent 协作 → 改进工具                                 │
│  Step 4: 循环迭代 → 达到强性能                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 构建原型

**要点**:
- 快速站立原型，亲手测试
- 给 Claude 相关库/API/SDK 的文档（LLM-friendly 文档如 `llms.txt`）
- 封装为 MCP Server 或 DXT 进行本地测试

**连接方式**:
```bash
# Claude Code
claude mcp add <name> <command> [args...]

# Claude Desktop
Settings > Developer 或 Settings > Extensions
```

**收集反馈**: 测试工具，收集用户反馈，建立直觉。

---

### 2.3 运行评估

#### 生成评估任务

**强任务示例**（多工具调用、真实复杂度）:
```
下周安排与 Jane 的会议讨论 Acme Corp 项目。附上上次项目规划会议的笔记并预定会议室。

客户 ID 9182 报告单次购买被扣款三次。查找所有相关日志条目并确定是否有其他客户受影响。

客户 Sarah Chen 提交取消请求。准备挽留方案：确定(1)为什么离开、(2)什么挽留方案最有效、(3)风险因素。
```

**弱任务示例**（过于简单）:
```
下周与 jane@acme.corp 安排会议。
搜索 payment logs 中的 purchase_complete 和 customer_id=9182。
查找客户 ID 45892 的取消请求。
```

#### 验证器设计

| 类型 | 说明 |
|------|------|
| **简单验证** | 字符串精确匹配 |
| **高级验证** | Claude 判断响应 |
| **避免过度严格** | 不要因格式/标点/有效替代表述拒绝正确答案 |

#### 运行评估

**推荐方式**:
- 使用直接 LLM API 调用运行评估
- 简单 agentic loop（while-loop 包装 LLM API 和 tool call）

**系统提示建议**:
```
要求 Agent 输出：
1. structured response blocks（用于验证）
2. reasoning and feedback blocks（用于分析）
3. 在 tool call/response blocks 之前输出 → 触发 chain-of-thought
```

**可开启 interleaved thinking（Claude）获得类似功能**。

#### 收集指标

| 指标 | 用途 |
|------|------|
| 总运行时间 | 性能分析 |
| tool call 数量 | 识别冗余调用 |
| token 消耗 | 效率分析 |
| tool errors | 识别参数问题 |

---

### 2.4 分析结果

**Agent 作为分析伙伴**:
- 发现矛盾的工具描述
- 识别低效实现
- 发现混乱的工具 schema

**重要**: Agent 省略的内容往往比包含的更重要。LLM 不总是说出它的意思。

**分析方法**:
1. 观察 Agent 被卡住的地方
2. 阅读 reasoning/feedback/CoT
3. 查看原始 transcript（tool calls + responses）
4. 分析 tool calling 指标

**案例**: Claude Web Search 工具发布时，发现 Claude 无谓地给 query 参数加 "2025"，导致搜索结果偏差 → 通过改进工具描述解决。

---

### 2.5 与 Agent 协作改进

**方法**: 将评估 transcript 拼接后粘贴到 Claude Code，让 Claude 分析并批量重构工具。

**效果**: 本文大部分建议来自用 Claude Code 反复优化内部工具。

---

## 三、编写有效工具的原则

### 3.1 选择正确的工具

#### 核心洞察

**工具数量 ≠ 更好结果**

常见错误：仅仅封装现有 API 功能，不考虑是否适合 Agent。

#### Agent vs 传统软件的"affordances"

| 维度 | 传统软件 | Agent |
|------|----------|-------|
| **内存/上下文** | 内存便宜且充足 | 上下文有限（token 限制） |
| **处理方式** | 可逐条处理所有数据 | 逐 token 读取浪费上下文 |

**示例**: 地址簿搜索
- ❌ `list_contacts` → 返回所有联系人 → Agent 逐个读取（暴力搜索）
- ✅ `search_contacts` → 只返回相关联系人 → Agent 直接跳到相关页面

#### 建议策略

**构建少量精心的工具，针对高影响工作流**，然后根据评估扩展。

#### 工具合并示例

| 原方案（多个工具） | 合并方案（单一工具） |
|-------------------|---------------------|
| `list_users` + `list_events` + `create_event` | `schedule_event`（查找可用时间并安排） |
| `read_logs` | `search_logs`（只返回相关日志行+上下文） |
| `get_customer_by_id` + `list_transactions` + `list_notes` | `get_customer_context`（编译客户所有相关信息） |

#### 工具边界

- 每个工具有明确、独特的目的
- 工具应让 Agent 像人类一样分解和解决任务
- 减少 intermediate outputs 消耗的上下文

---

### 3.2 Namespacing 工具

#### 问题

Agent 可能获得数十个 MCP servers 和数百个工具。工具功能重叠或目的模糊时，Agent 会困惑。

#### 解决方案：命名空间

**按服务命名**:
```
asana_search, jira_search
```

**按资源命名**:
```
asana_projects_search, asana_users_search
```

#### 发现

- prefix-based vs suffix-based namespacing 对评估有**非平凡影响**
- 效果因 LLM 而异
- 需根据自己的评估选择命名方案

#### 好处

- 减少 Agent 选择错误工具的风险
- 减少 context 中加载的工具数量
- 将计算从 Agent context 转移到 tool call 内部

---

### 3.3 返回有意义的上下文

#### 核心原则

**优先返回高信号信息，而非低级技术标识符**

| 低信号（避免） | 高信号（推荐） |
|---------------|---------------|
| `uuid`, `256px_image_url`, `mime_type` | `name`, `image_url`, `file_type` |

#### UUID vs 自然语言

Agent 处理自然语言名称比处理 cryptic identifiers 更成功。

**发现**: 将任意 UUID 解析为语义上有意义的语言（甚至 0-indexed ID），显著提高 Claude 的检索精度，减少幻觉。

#### 灵活性方案

当 Agent 需要同时处理自然语言和技术标识符（用于触发下游 tool call）时：

```python
enum ResponseFormat {
    DETAILED = "detailed",  # 包含 ID，用于下游 tool call
    CONCISE = "concise",    # 只返回内容，排除 ID
}
```

**类似 GraphQL**: 可选择需要的信息片段。

#### 示例

| 格式 | Token 数量 |
|------|-----------|
| Detailed response | 206 tokens |
| Concise response | 72 tokens（约 1/3） |

#### Response 结构影响

XML、JSON、Markdown 等结构对评估性能有影响，无一刀切方案。

原因：LLM 基于 next-token prediction 训练，与训练数据匹配的格式表现更好。

---

### 3.4 Token 效率优化

#### 核心措施

| 方法 | 说明 |
|------|------|
| **Pagination** | 分页返回 |
| **Range selection** | 范围选择 |
| **Filtering** | 过滤 |
| **Truncation** | 截断 + 默认值 |

**Claude Code 默认限制**: 25,000 tokens

#### Truncation 最佳实践

**截断响应需包含指导性指令**:

```
Results truncated. Use filters or pagination for more targeted searches.
Example: search_logs(query="error", time_range="last_hour")
```

#### 错误响应最佳实践

| 类型 | 示例 |
|------|------|
| **无帮助** | `Error: Invalid parameter` |
| **有帮助** | `Error: 'date' parameter must be ISO 8601 format (e.g., '2025-01-15'). Received: 'Jan 15'` |

---

### 3.5 Prompt-engineering 工具描述

#### 最有效方法之一

工具描述和 specs 加载到 Agent context，可引导有效工具调用行为。

#### 编写原则

**像向新员工描述工具一样思考**:
- 隐含的 context → 显式化
- 专业化查询格式
- 术语定义
- 资源间关系

**避免歧义**:
- 清晰描述预期输入/输出
- 用严格数据模型强制执行

**参数命名**:
- ❌ `user`
- ✅ `user_id`

#### 案例：SWE-bench Verified

Claude Sonnet 3.5 在 SWE-bench Verified 达到 SOTA，仅通过**精确改进工具描述**，显著降低错误率并提高任务完成率。

#### 资源

- [Developer Guide](https://docs.anthropic.com) - 工具定义最佳实践
- [动态加载机制](https://docs.anthropic.com) - 工具如何加载到 system prompt
- MCP tool annotations - 标注需要开放世界访问或破坏性变更的工具

---

## 四、展望

### 核心转变

从可预测的确定性模式 → 非确定性模式

### 成功工具的特征

1. **有意且清晰定义**
2. **谨慎使用 Agent context**
3. **可在多样工作流中组合**
4. **让 Agent 直观解决真实任务**

### 未来预期

- MCP 协议更新
- 底层 LLM 升级
- 系统化、评估驱动的方法确保工具与 Agent 共同演进

---

## 五、关键要点总结

### 工具设计核心原则

| 原则 | 实践 |
|------|------|
| **选择正确工具** | 少量精心工具 → 合并相关功能 → 明确目的 |
| **命名空间** | 按服务/资源分组 → 减少选择困惑 |
| **返回有意义上下文** | 高信号信息 → 自然语言优先 → UUID 转语义 |
| **Token 效率** | Pagination/Filtering/Truncation → 默认值 → 指导性指令 |
| **Prompt-engineering 描述** | 显式化隐含 context → 无歧义参数 → 向新员工描述一样 |

### 评估驱动流程

```
原型 → 评估任务 → 运行评估 → 分析结果 → 改进工具 → 循环
```

### 关键洞察

> **工具数量 ≠ 更好结果**
> **Agent context 是稀缺资源**
> **Agent 省略的内容比包含的更重要**
> **最"适合 Agent"的工具，人类也觉得直观**