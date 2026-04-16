---
name: autonomous_test
description: 自主对话测试框架 - AI自动生成多轮对话测试场景，模拟用户行为，记录完整对话链，发现系统问题
license: MIT
category: testing
allowed-tools:
  - bash
---

# 自主对话测试框架

AI 驱动的自主对话测试系统，能够自动生成测试场景、模拟用户多轮对话行为、记录完整对话链并生成测试报告。

## 能力

- **场景自动生成**：根据测试目标自动生成多样化测试场景（匹配、画像收集、约会策划、安全测试等）
- **多轮对话模拟**：模拟真实用户的多轮对话行为，包括追问、澄清、纠错等
- **完整对话记录**：记录每轮的用户输入、Agent响应、意图识别、UI组件、延迟等
- **问题自动发现**：通过对话链分析发现系统问题（意图误识别、死循环、安全漏洞等）
- **HTML报告生成**：生成可视化的测试报告，便于分析

## 使用场景

用户说：
- "跑一下测试"
- "测试匹配功能"
- "帮我测3个场景"
- "运行5个测试用例"
- "并行执行10个场景"
- "查看测试结果"

## 🎯 口语化指令映射

| 用户说 | 执行命令 |
|--------|---------|
| "跑一下测试" | `python tests/eval/autonomous_conversation_test.py --scenarios 3 --real` |
| "测试N个场景" | `python tests/eval/autonomous_conversation_test.py --scenarios N --real` |
| "并行测试" | `python tests/eval/autonomous_conversation_test.py --scenarios 5 --real --max-concurrent 3` |
| "串行测试（调试）" | `python tests/eval/autonomous_conversation_test.py --scenarios 3 --real --serial` |
| "测试匹配功能" | `python tests/eval/autonomous_conversation_test.py --scenario-type match_request --real` |
| "测试安全边界" | `python tests/eval/autonomous_conversation_test.py --scenario-type security_test --real` |
| "快速Mock测试" | `python tests/eval/autonomous_conversation_test.py --scenarios 5 --mock` |

## 🔧 执行参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--scenarios N` | 生成N个测试场景 | 3 |
| `--scenario-type TYPE` | 指定场景类型（match_request, profile_completion, date_planning, security_test等） | 随机 |
| `--real` | 使用真实API（调用后端服务） | Mock模式 |
| `--mock` | 使用Mock模式（内置规则引擎） | - |
| `--parallel` | 并行执行（默认） | 开启 |
| `--serial` | 串行执行（调试用） | - |
| `--max-concurrent N` | 最大并发数 | 3 |

## 📊 输出文件位置

测试完成后，结果保存在 `Her/tests/eval/autonomous_results/`：

- `session-*.json` - 每个会话的完整对话记录
- `test_summary.json` - 测试摘要统计
- `test_report.html` - 可视化HTML报告

## ⚠️ 执行要求

1. **真实API模式**：需要后端服务运行（`http://localhost:8002`）
2. **Mock模式**：无需后端服务，但模拟用户行为仍需LLM API配置
3. **并行执行**：默认并发数为3，避免API过载
4. **结果查看**：测试完成后查看 `test_report.html` 报告

## 场景类型列表

| 类型 | 描述 | 预期轮次 |
|------|------|---------|
| `profile_completion` | 新用户画像收集流程 | 3-6轮 |
| `match_request` | 用户请求匹配推荐 | 2-4轮 |
| `compatibility_analysis` | 分析匹配兼容度 | 2-3轮 |
| `date_planning` | 约会方案规划 | 3-5轮 |
| `icebreaker_request` | 破冰话题请求 | 2-3轮 |
| `preference_update` | 更新匹配偏好 | 2-4轮 |
| `edge_case` | 边缘情况测试 | 2-3轮 |
| `security_test` | 安全边界测试 | 1-2轮 |

## 示例执行

```bash
# 在Her目录下执行
cd Her

# 并行测试5个场景
python tests/eval/autonomous_conversation_test.py --scenarios 5 --real --max-concurrent 3

# 测试安全边界
python tests/eval/autonomous_conversation_test.py --scenario-type security_test --scenarios 3 --real
```