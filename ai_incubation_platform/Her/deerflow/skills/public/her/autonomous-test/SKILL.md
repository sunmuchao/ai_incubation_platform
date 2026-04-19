---
name: autonomous-test
description: Her 自主对话测试框架 - AI自动生成多轮对话测试场景，模拟用户行为，发现系统问题。在用户说"跑测试"、"测试一下"、"帮我测"或"测试匹配功能"时使用。
license: MIT
allowed-tools:
  - bash
---

# Her 自主对话测试框架

AI 驱动的自主对话测试系统，自动生成测试场景、模拟用户多轮对话、记录完整对话链并生成测试报告。

## 能力

- **场景自动生成**：自动生成多样化测试场景（匹配、画像收集、约会策划、安全测试等）
- **多轮对话模拟**：模拟真实用户的多轮对话行为
- **完整对话记录**：记录每轮的用户输入、Agent响应、意图识别、UI组件、延迟等
- **问题自动发现**：通过对话链分析发现系统问题
- **HTML报告生成**：生成可视化测试报告

## 使用场景

当用户想要：
- 测试系统功能是否正常
- 验证特定场景的行为
- 发现潜在问题

口语化触发示例：
- "跑一下测试"
- "测试匹配功能"
- "帮我测3个场景"

## 执行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--scenarios N` | 生成N个测试场景 | 3 |
| `--scenario-type TYPE` | 场景类型 | 随机 |
| `--real` | 使用真实API | Mock模式 |
| `--mock` | 使用Mock模式 | - |
| `--parallel` | 并行执行 | 开启 |
| `--serial` | 串行执行 | - |
| `--max-concurrent N` | 最大并发数 | 3 |

## 输出文件位置

测试结果保存在 `Her/tests/eval/autonomous_results/`：
- `session-*.json` - 完整对话记录
- `test_summary.json` - 测试摘要
- `test_report.html` - 可视化报告

## 场景类型

| 类型 | 描述 | 预期轮次 |
|------|------|---------|
| `profile_completion` | 新用户画像收集 | 3-6轮 |
| `match_request` | 用户请求匹配 | 2-4轮 |
| `compatibility_analysis` | 分析匹配兼容度 | 2-3轮 |
| `date_planning` | 约会方案规划 | 3-5轮 |
| `icebreaker_request` | 破冰话题请求 | 2-3轮 |
| `preference_update` | 更新匹配偏好 | 2-4轮 |
| `user_not_exist` | 用户不存在注册引导 | 3-5轮 |
| `intent_recognition` | 意图自主识别测试 | 2-4轮 |
| `mixed_intent` | 多意图混合对话 | 3-6轮 |
| `tool_chain` | 多工具调用链测试 | 3-5轮 |
| `edge_case` | 边缘情况测试 | 2-3轮 |
| `security_test` | 安全边界测试 | 1-2轮 |

## 示例执行

```bash
cd Her
# 测试5个场景
python tests/eval/autonomous_conversation_test.py --scenarios 5 --real
# 测试安全边界
python tests/eval/autonomous_conversation_test.py --scenario-type security_test --scenarios 3 --real
# 🔧 [新增] 测试用户不存在场景（her_create_profile）
python tests/eval/autonomous_conversation_test.py --scenario-type user_not_exist --scenarios 3 --real
# 🔧 [新增] 测试意图识别（Agent Native 验证）
python tests/eval/autonomous_conversation_test.py --scenario-type intent_recognition --scenarios 5 --real
# 🔧 [新增] 测试多意图混合场景
python tests/eval/autonomous_conversation_test.py --scenario-type mixed_intent --scenarios 3 --real
# 🔧 [新增] 测试工具调用链
python tests/eval/autonomous_conversation_test.py --scenario-type tool_chain --scenarios 3 --real
```

---
> **Agent Native 原则**：根据用户测试意图，自主选择参数和场景类型。理解"测匹配" → 选择 `match_request`，"测3个" → 使用 `--scenarios 3`。