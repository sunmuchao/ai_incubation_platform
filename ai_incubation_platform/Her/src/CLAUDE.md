# 调试与纠错协议 (Debugging & Iteration Protocol)

当你（Claude）在同一个 BUG 或逻辑上尝试超过 2 次仍未解决时，必须停止自动修复，并执行以下排查流程：

### 1. 自我审计 (Self-Audit)
- **回溯逻辑**：立即停止当前的修改方案。重新阅读报错信息，对比当前代码与原始稳定版本的差异。
- **定位盲区**：思考是否存在样式污染（CSS）、异步竞态（Race Condition）或生命周期错乱（Hooks）等隐性问题。

### 2. 诊断优先 (Diagnosis Over Fix)
- **禁止盲目尝试**：不要在未确定根因的情况下继续修改代码。
- **添加日志**：在关键路径处插入详细的 `console.log`（包含变量值、执行顺序、时间戳）。
- **隔离测试**：如果是一个复杂组件，尝试提取出最简复现 Demo (Minimal Reproducible Example)。

### 3. 交互请求 (Interaction Requirements)
- **请求视觉/环境信息**：如果代码逻辑看似正确但结果错误，请主动询问我：
  - 浏览器的 Computed Style（计算样式）。
  - DevTools 中的 Network 请求状态。
  - 组件实际渲染后的 DOM 结构截图描述。
- **陈述假设**：向我解释你目前认为的 2 个最可能的错误原因，并询问我更倾向于哪一个。

### 4. 强制重置 (Hard Reset)
- 如果修改导致了连锁反应（引入了新 BUG），请主动建议我使用 `git restore` 回滚，并从全新的视角（Clean Slate）重新分析。
