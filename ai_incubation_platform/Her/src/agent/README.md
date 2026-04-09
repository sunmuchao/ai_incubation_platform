# Agent 模块架构说明

## 目录结构

```
src/agent/
├── skills/           # AI 能力层（继承 BaseSkill）
│   ├── base.py       # 基类定义
│   ├── registry.py   # 技能注册中心
│   └── *_skill.py    # 具体技能实现
├── tools/            # 底层工具层
│   ├── registry.py   # 工具注册中心
│   └── *_tool.py     # 具体工具实现
└── workflows/        # 工作流编排
    └── *_workflow.py # 工作流定义
```

## 职责边界

### Skills（技能层）

**定位**：AI 能力封装，处理用户意图和生成响应

**特征**：
- 继承 `BaseSkill` 基类
- 实现意图理解、响应生成、UI 选择
- 可以调用 Tools 获取数据
- 可以调用外部 LLM 服务

**示例**：
- `matchmaking_skill.py` - 匹配推荐能力
- `safety_guardian_skill.py` - 安全守护能力
- `geo_location_skill.py` - 地理位置能力

### Tools（工具层）

**定位**：底层操作封装，提供原子能力

**特征**：
- 纯函数或简单类
- 不涉及 AI 逻辑
- 提供数据查询、计算、外部服务调用
- 可被多个 Skills 复用

**示例**：
- `geo_tool.py` - 地理计算（距离、坐标转换）
- `safety_tool.py` - 安全检测（关键词过滤、风险评估）
- `icebreaker_tool.py` - 破冰话题生成

### 关系图

```
用户请求 → Skill（AI 能力）→ Tool（原子操作）→ 数据库/外部服务
                ↓
         LLM 服务
                ↓
         Generative UI
```

## 命名规范

| 类型 | 命名格式 | 示例 |
|------|---------|------|
| Skill 文件 | `*_skill.py` | `matchmaking_skill.py` |
| Skill 类 | `*Skill` | `MatchmakingAgentSkill` |
| Tool 文件 | `*_tool.py` | `geo_tool.py` |
| Tool 类 | `*Tool` 或数据类 | `GeoTool`, `Location` |
| Workflow 文件 | `*_workflow.py` | `match_workflow.py` |

## 添加新功能指南

### 添加新 Skill

1. 在 `skills/` 目录创建 `xxx_skill.py`
2. 继承 `BaseSkill` 类
3. 在 `skills/__init__.py` 中注册
4. 在 `skills/registry.py` 中添加元数据

### 添加新 Tool

1. 在 `tools/` 目录创建 `xxx_tool.py`
2. 实现纯函数或工具类
3. 在 `tools/__init__.py` 中导出

## 迁移建议

如果发现以下情况，应考虑重构：

1. **Skill 包含大量数据处理逻辑** → 提取为 Tool
2. **Tool 包含 AI 推理逻辑** → 迁移到 Skill
3. **多个 Skill 共享相同逻辑** → 提取为公共 Tool