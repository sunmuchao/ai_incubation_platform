# Anthropic Prompt 与 Tool 定义最佳实践

> **来源**：Anthropic 官方文档 + 官方 Cookbook 最佳实践
>
> **核心原则**：System Prompt 与 Tool Definition 分离，职责边界清晰

---

## 一、分离原则

### 1.1 API 结构

Anthropic Claude API 使用独立参数传递：

```python
client.messages.create(
    model="claude-sonnet-4-20250514",
    system=system_prompt,  # 角色 + 原则 + 安全边界
    tools=tools,           # 工具定义（description 含使用场景）
    messages=messages      # 用户对话历史
)
```

### 1.2 职责划分

| 组件 | API 参数 | 职责 |
|------|---------|------|
| **System Prompt** | `system` | 定义 Agent 角色、行为原则、安全边界 |
| **Tool Definition** | `tools` | 定义工具能力、参数、使用场景、返回格式 |

---

## 二、System Prompt 设计规范

### 2.1 应包含的内容

```
✅ 角色定义（你是谁）
✅ 核心行为原则（如何思考、如何决策）
✅ 安全边界（拒绝什么请求）
✅ 高层指导方针（决策依据）

❌ 工具使用指南（应在 tool description）
❌ 输出格式模板（限制 Agent 自主性）
❌ 触发词映射表（机械化执行）
❌ 流程步骤硬编码（应由 Agent 自主决策）
❌ Skills 参考表（应由 Agent 根据意图自主选择）
```

### 2.2 精简原则

**行数限制**：根据模型能力调整

| 模型等级 | System Prompt 行数上限 |
|---------|----------------------|
| Claude Opus/Sonnet | 200 行 OK |
| Claude Haiku | 80 行 |
| glm-4/DeepSeek | 50 行 |
| glm-5/中小模型 | 30 行 |

**核心原则数量**：不超过 5 条

### 2.3 标准 System Prompt 结构

```markdown
# Agent 角色

你是一位 [角色描述]。

## 核心原则

### 1. [原则名称]
[简洁描述]

### 2. [原则名称]
[简洁描述]

---

## 安全边界

以下请求立即拒绝：
- [拒绝场景 1]
- [拒绝场景 2]
```

---

## 三、Tool Definition 设计规范

### 3.1 应包含的内容

```python
{
    "name": "tool_name",
    "description": "工具能力描述。使用场景：[何时调用]。禁止场景：[何时不调用]",
    "input_schema": {
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string",
                "description": "参数说明（简洁明了）"
            }
        },
        "required": ["必须参数"]
    }
}
```

### 3.2 Description 写法规范

**必须包含**：
1. 工具能力描述（做什么）
2. 使用场景（何时调用）
3. 禁止场景（何时不调用）

**示例**：

```python
# ✅ 正确写法
{
    "name": "her_find_candidates",
    "description": "查询候选匹配对象池。使用场景：用户想要找对象、获取推荐、开始匹配流程时调用。禁止场景：用户只想了解匹配规则或询问一般性问题时不调用。"
}

# ❌ 错误写法（过于模糊）
{
    "name": "her_find_candidates",
    "description": "查找匹配对象"  # 缺少使用场景和禁止场景
}
```

### 3.3 返回值规范

**只返回原始数据**：

```python
# ✅ 正确设计
{
    "success": true,
    "data": {
        "component_type": "MatchCardList",  # 前端渲染需要
        "candidates": [...],
        "total": 3
    }
}

# ❌ 错误设计（包含预加工建议）
{
    "instruction": "请向用户展示匹配结果",  # 给 Agent 的指令
    "output_hint": "为你找到 X 位候选人",   # 模板提示
    "data": {...}
}
```

**禁止字段**：
- `instruction` - 给 Agent 的执行指令
- `output_hint` - 给用户的回复模板
- `summary` - 预加工的摘要

**保留字段**：
- `component_type` - 前端渲染需要的组件类型
- `success` - 执行状态
- `error` - 错误信息

---

## 四、分层架构对比

### 4.1 传统设计 vs 最佳实践

| 维度 | 传统设计（错误） | 最佳实践（正确） |
|------|----------------|-----------------|
| 规则表达 | 代码硬编码 if-else | Prompt 表达 |
| 决策主体 | 规则引擎 | LLM Agent |
| 工具职责 | 包含业务逻辑、预加工建议 | 纯数据查询/执行 |
| 输出方式 | 预设模板 | AI 动态生成 |
| System Prompt | 触发词映射表 + 流程步骤 | 角色 + 原则 + 安全边界 |

### 4.2 Agent Native 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     System Prompt Layer                          │
│  所有决策逻辑通过 Prompt 表达                                     │
│  - 角色定义、核心原则、安全边界                                   │
│  - 不硬编码 if-else，用自然语言描述规则                           │
└─────────────────────────────────────────────────────────────────┘
                           ↓ Agent 自主决策
┌─────────────────────────────────────────────────────────────────┐
│                     Tools Layer (Pure Execution)                 │
│  只做数据查询和执行，不含业务逻辑                                  │
│  - 返回原始数据，不做解读                                         │
│  - Agent 自己解读数据并决策下一步                                 │
└─────────────────────────────────────────────────────────────────┘
                           ↓ 依赖
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer                                   │
│  数据存储，无业务逻辑                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 五、常见反模式

### 5.1 触发词映射表（禁止）

```markdown
# ❌ 禁止在 System Prompt 中
| 用户说的话 | 你立即调用 |
|-----------|-----------|
| "帮我找对象" | `her_find_matches` |
| "聊什么" | `her_get_icebreaker` |

# ✅ 应在 Tool Description 中
{
    "name": "her_find_candidates",
    "description": "使用场景：用户说'找对象'、'帮我找人'、'推荐几个'时调用"
}
```

### 5.2 工具返回预加工（禁止）

```python
# ❌ 禁止
return {
    "instruction": "请向用户展示...",  # Agent 可能直接输出
    "output_hint": "找到 X 位候选人",   # 模板化输出
    "data": {...}
}

# ✅ 正确
return {
    "success": true,
    "data": {
        "component_type": "MatchCardList",
        "candidates": [...]
    }
}
```

### 5.3 工具包含业务逻辑（禁止）

```python
# ❌ 禁止（筛选逻辑在代码中）
def her_find_matches(user_id):
    candidates = query_all()
    filtered = [c for c in candidates if c.age >= min_age]  # 硬编码筛选
    return filtered

# ✅ 正确（返回原始数据，Agent 决策筛选）
def her_find_matches(user_id):
    return {"candidates": query_all(), "total": len(...)}
```

---

## 六、Her 项目重构对照

### 6.1 SOUL.md 重构前后

| 重构前（125行） | 重构后（35行） |
|----------------|---------------|
| 意图映射表 | ❌ 移除 |
| Skills 参考表 + 流程图 | ❌ 移除 |
| 工具使用指南 | ❌ 移除 |
| 展示候选人格式 | ❌ 移除 |
| 角色定义 | ✅ 保留 |
| 4条核心原则 | ✅ 简化保留 |
| 安全边界 | ✅ 保留 |

### 6.2 职责分离结果

```
SOUL.md (System Prompt)     → 角色 + 4条原则 + 安全边界
Skill SKILL.md              → 场景描述 + 工具组合 + 执行建议
Tool description            → 能力 + 使用场景 + 禁止场景 + 参数
```

---

## 七、检查清单

### System Prompt 检查

- [ ] 是否只包含角色 + 原则 + 安全边界？
- [ ] 是否没有触发词映射表？
- [ ] 是否没有工具使用指南？
- [ ] 是否没有流程步骤硬编码？
- [ ] 是否没有输出格式模板？
- [ ] 核心原则是否不超过 5 条？
- [ ] 行数是否在模型能力范围内？

### Tool Definition 检查

- [ ] description 是否包含使用场景？
- [ ] description 是否包含禁止场景？
- [ ] 返回值是否只有原始数据？
- [ ] 是否没有 instruction/output_hint？
- [ ] 是否没有业务逻辑（筛选、排序）？

### 架构检查

- [ ] System Prompt 和 Tools 是否通过独立参数传递？
- [ ] 职责边界是否清晰？
- [ ] 规则是否只在一处定义（单一真相来源）？

---

## 八、参考资料

- [Anthropic Tool Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering)
- [Anthropic Cookbook - Tool Use Best Practices](https://github.com/anthropics/anthropic-cookbook)

---

## 九、版本记录

| 版本 | 日期 | 更改内容 |
|------|------|---------|
| v1.0 | 2026-04-18 | 基于 Anthropic 官方文档整理最佳实践 |

---

> **一句话总结**：System Prompt 定义"是谁、怎么思考"，Tool Definition 定义"能做什么、何时用"。职责分离，Agent 自主决策。