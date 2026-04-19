---
name: eval-assistant
description: Her 系统智能评估助手。一键执行：1) 分析测试覆盖缺口并补充用例，2) 运行完整测试，3) LLM-as-a-Judge 评估，4) 输出问题点与改进建议。用户只需说"评估系统"、"跑一下测试"、"检查系统质量"即可触发。
---

# Her 系统评估助手 Skill

一键完成系统质量评估，输出问题点和改进建议。

## 触发条件

当用户说以下任意一句话时触发：
- "评估系统"
- "跑一下测试"
- "检查系统质量"
- "系统评估"
- "质量评估"
- "评估一下"

## 执行规则（重要）

### 🔒 进程管理规则

**禁止并行执行测试脚本！** 必须遵守以下规则：

1. **启动前检查**：执行测试前，必须先检查是否有正在运行的 `test_golden_dataset.py` 进程
   ```bash
   pgrep -f "test_golden_dataset.py"
   ```
   如果有进程存在，先清理：
   ```bash
   pkill -f "test_golden_dataset.py"
   sleep 2
   ```

2. **单进程原则**：整个 Skill 执行期间，只启动**一个**测试进程，禁止多次调用

3. **等待完成**：启动测试后，必须等待其完成（timeout 设为 600 秒），禁止在执行中再次启动

4. **进程状态追踪**：使用 `ps` 或 `pgrep` 监控进程状态，避免重复启动

---

## 工作流程

### Phase 1: 环境检查与进程清理

1. **清理已有进程**
   ```bash
   pkill -f "test_golden_dataset.py" 2>/dev/null || true
   sleep 1
   ```

2. **检查后端服务**
   - 访问 `http://localhost:8002/health`
   - 若未运行，提示用户启动服务

3. **读取测试数据集**
   - 分析用例分布和覆盖缺口

### Phase 2: 补充缺失测试场景

**先补充再测试！** 识别缺失场景，直接写入 `golden_dataset.json`：

**必查场景清单**：
- 拒绝推荐后二次推荐
- 追问匹配理由（"为什么推荐TA"）
- 中断后恢复上下文
- 焦虑/沮丧情绪识别
- 节日特殊推荐
- 矛盾条件处理

### Phase 3: 执行测试（单次执行）

**只执行一次！** 使用正确的目录和命令：

```bash
cd /Users/sunmuchao/Downloads/ai_incubation_platform/Her
python tests/eval/test_golden_dataset.py --real
```

**等待完成**，不再次启动。输出文件：
- `tests/eval/evaluation_results.json`
- `tests/eval/evaluation_report.html`

### Phase 4: LLM Judge 评估

测试完成后执行 Judge：

```bash
python tests/eval/llm_judge.py --input tests/eval/evaluation_results.json
```

### Phase 5: 智能分析与根因追溯

基于结果进行五问法分析，输出问题清单。

### Phase 6: 输出报告

使用模板生成结构化报告。

---

## 错误处理

如果测试执行超时或失败：
1. 检查进程状态：`pgrep -f "test_golden_dataset.py"`
2. 查看日志输出
3. 清理进程后重新执行（仅允许一次重试）

---

## 关键文件

```
eval-assistant/
├── SKILL.md                    ← 你正在阅读的文件
└── templates/
    └── report.template.md      ← 评估报告模板
```

依赖：
- `tests/eval/golden_dataset.json`
- `tests/eval/test_golden_dataset.py`
- `tests/eval/llm_judge.py`