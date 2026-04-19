# Her 系统评估报告

**评估时间**: {{timestamp}}
**评估版本**: {{version}}
**用例总数**: {{total_cases}}
**新增用例**: {{new_cases_count}}

---

## 一、总览

| 指标 | 值 | 状态 |
|------|-----|------|
| 原始用例数 | {{original_cases}} | - |
| 本次新增 | {{new_cases_count}} | ✅ 已补充 |
| 补充后总数 | {{total_cases}} | - |
| 通过率 | {{pass_rate}}% | {{pass_rate_status}} |
| 平均评分 | {{avg_score}} | {{avg_score_status}} |
| 意图识别准确率 | {{intent_accuracy}}% | {{intent_status}} |
| 安全合规通过率 | {{security_rate}}% | {{security_status}} |

**综合评级**: {{overall_rating}}

---

## 二、新增测试用例

本次评估**先补充**了以下缺失场景：

| ID | 类别 | 子类别 | 场景描述 | 输入示例 |
|-----|------|--------|---------|---------|
{{#new_cases}}
| {{new_id}} | {{category}} | {{subcategory}} | {{description}} | "{{input}}" |
{{/new_cases}}

**覆盖缺口修复**: {{coverage_improvement}}

---

## 三、问题清单

### Critical (阻塞级别)

{{#critical_issues}}
#### {{issue_id}}: {{issue_title}}

- **场景**: `{{test_case_id}}` - "{{input_message}}"
- **现象**: {{symptom}}
- **五问法根因分析**:
  ```
  问题现象：{{symptom}}
  ├─ 为什么 1: {{why_1}}
  ├─ 为什么 2: {{why_2}}
  ├─ 为什么 3: {{why_3}}
  ├─ 为什么 4: {{why_4}}
  └─ 为什么 5: {{root_cause}}（根本原因）
  ```
- **根本对策**: {{root_fix}}
- **影响范围**: {{impact}}
- **涉及文件**: {{files}}

{{/critical_issues}}

### Major (主要问题)

{{#major_issues}}
#### {{issue_id}}: {{issue_title}}

- **场景**: `{{test_case_id}}`
- **现象**: {{symptom}}
- **根因**: {{root_cause}}
- **修复建议**: {{fix_suggestion}}
- **涉及文件**: {{files}}

{{/major_issues}}

### Minor (次要问题)

{{#minor_issues}}
- **{{issue_title}}**: {{issue_description}}
  - 建议: {{suggestion}}

{{/minor_issues}}

---

## 四、改进建议

### 短期修复（可立即执行）

| 序号 | 修复项 | 执行步骤 | 涉及文件 | 预期效果 |
|------|--------|---------|---------|---------|
{{#short_term_fixes}}
| {{index}} | {{fix_title}} | {{fix_steps}} | {{files}} | {{expected_effect}} |
{{/short_term_fixes}}

### 长期优化（需架构调整）

{{#long_term_fixes}}
#### {{index}}. {{fix_title}}

- **当前问题**: {{current_problem}}
- **目标架构**: {{target_architecture}}
- **迁移路径**: {{migration_path}}
- **预期收益**: {{expected_benefit}}

{{/long_term_fixes}}

---

## 五、分类详情

### happy_path (正常流程) - {{happy_total}} 用例

| 子类别 | 通过数 | 总数 | 通过率 | 典型问题 |
|--------|--------|------|--------|---------|
{{#happy_path_details}}
| {{subcategory}} | {{passed}} | {{total}} | {{rate}}% | {{typical_issue}} |
{{/happy_path_details}}

### edge_cases (边缘场景) - {{edge_total}} 用例

| 子类别 | 通过数 | 总数 | 通过率 | 典型问题 |
|--------|--------|------|--------|---------|
{{#edge_cases_details}}
| {{subcategory}} | {{passed}} | {{total}} | {{rate}}% | {{typical_issue}} |
{{/edge_cases_details}}

### robustness_security (健壮性与安全) - {{security_total}} 用例

| 子类别 | 通过数 | 总数 | 通过率 | 典型问题 |
|--------|--------|------|--------|---------|
{{#security_details}}
| {{subcategory}} | {{passed}} | {{total}} | {{rate}}% | {{typical_issue}} |
{{/security_details}}

---

## 六、下一步行动（按优先级）

1. **{{priority_1}}** - {{action_1}}（涉及: {{files_1}}）
2. **{{priority_2}}** - {{action_2}}（涉及: {{files_2}}）
3. **{{priority_3}}** - {{action_3}}（涉及: {{files_3}}）

---

**报告生成**: eval-assistant Skill
**执行顺序**: 覆盖分析 → 补充用例 → 执行测试 → LLM Judge → 根因分析 → 输出报告
**数据来源**: evaluation_results.json + judge_results.json