#!/usr/bin/env python3
"""
单用例测试-评估-修复闭环脚本

工作流程：
1. 执行单个测试用例
2. 即时 LLM Judge 评估
3. 如果不通过 → 等待 Claude 分析根因并修复
4. 修复后重新测试该用例
5. 循环直到通过

用法：
    # 执行单个用例
    python tests/eval/run_single_case.py --test-id TC001

    # 执行所有用例（逐个执行+即时评估）
    python tests/eval/run_single_case.py --all

    # 只执行指定分类
    python tests/eval/run_single_case.py --category happy_path

    # 强制重新执行（忽略已有结果）
    python tests/eval/run_single_case.py --test-id TC001 --force

输出：
    - 单用例结果 JSON（tests/eval/single_case_result_{test_id}.json）
    - LLM Judge 评估结果（tests/eval/judge_single_{test_id}.json）
    - 失败用例报告（tests/eval/failed_cases.json）
"""

import json
import os
import sys
import argparse
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# 路径配置
GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
FAILED_CASES_PATH = os.path.join(os.path.dirname(__file__), "failed_cases.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def load_golden_dataset() -> Dict[str, Any]:
    """加载测试数据集"""
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_test_case_by_id(test_id: str) -> Optional[Dict[str, Any]]:
    """根据 ID 获取单个测试用例"""
    dataset = load_golden_dataset()
    for case in dataset.get("test_cases", []):
        if case.get("id") == test_id:
            return case
    return None


def get_test_cases_by_category(category: str) -> List[Dict[str, Any]]:
    """根据分类获取测试用例"""
    dataset = load_golden_dataset()
    return [c for c in dataset.get("test_cases", []) if c.get("category") == category]


def get_all_test_cases() -> List[Dict[str, Any]]:
    """获取所有测试用例"""
    dataset = load_golden_dataset()
    return dataset.get("test_cases", [])


def load_failed_cases() -> List[Dict[str, Any]]:
    """加载失败用例列表"""
    if os.path.exists(FAILED_CASES_PATH):
        with open(FAILED_CASES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_failed_case(test_id: str, test_case: Dict, result: Dict, judge_result: Dict, retry_count: int):
    """保存失败用例（供 Claude 分析）"""
    failed_cases = load_failed_cases()

    # 查找是否已有记录
    existing = next((c for c in failed_cases if c.get("test_id") == test_id), None)

    if existing:
        # 更新记录
        existing["retry_count"] = retry_count + 1
        existing["last_failed_at"] = datetime.now().isoformat()
        existing["last_judge_score"] = judge_result.get("overall_score", 0)
        existing["last_judge_summary"] = judge_result.get("summary", "")
        existing["last_judge_reasons"] = judge_result.get("reasons", {})
        existing["history"].append({
            "timestamp": datetime.now().isoformat(),
            "judge_score": judge_result.get("overall_score", 0),
            "judge_summary": judge_result.get("summary", ""),
            "actual_response": result.get("actual_response", "")[:300],
        })
    else:
        # 新增记录
        failed_cases.append({
            "test_id": test_id,
            "category": test_case.get("category"),
            "subcategory": test_case.get("subcategory"),
            "input_message": test_case.get("input", {}).get("message", ""),
            "expected_intent": test_case.get("expected_output", {}).get("intent_type"),
            "expected_ui": test_case.get("expected_output", {}).get("generative_ui", {}).get("component_type"),
            "first_failed_at": datetime.now().isoformat(),
            "retry_count": retry_count,
            "last_judge_score": judge_result.get("overall_score", 0),
            "last_judge_summary": judge_result.get("summary", ""),
            "last_judge_reasons": judge_result.get("reasons", {}),
            "history": [{
                "timestamp": datetime.now().isoformat(),
                "judge_score": judge_result.get("overall_score", 0),
                "judge_summary": judge_result.get("summary", ""),
                "actual_response": result.get("actual_response", "")[:300],
            }]
        })

    with open(FAILED_CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(failed_cases, f, ensure_ascii=False, indent=2)


def remove_failed_case(test_id: str):
    """从失败列表中移除（修复成功后）"""
    failed_cases = load_failed_cases()
    failed_cases = [c for c in failed_cases if c.get("test_id") != test_id]
    with open(FAILED_CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(failed_cases, f, ensure_ascii=False, indent=2)


@dataclass
class SingleCaseResult:
    """单用例执行结果"""
    test_id: str
    passed: bool
    api_success: bool
    actual_response: str = ""
    actual_intent: Optional[str] = None
    generative_ui: Optional[Dict] = None
    latency_ms: float = 0.0
    judge_passed: bool = False
    judge_score: float = 0.0
    judge_reasons: Dict[str, str] = field(default_factory=dict)
    judge_summary: str = ""
    retry_count: int = 0
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class RealAPIClient:
    """真实 API 客户端"""

    def __init__(self):
        self.base_urls = [
            "http://localhost:8000",
            "http://localhost:8002",
        ]
        self.timeout = 60
        self.working_base_url = None

    def _detect_working_url(self) -> str:
        """检测可用的 API 端点"""
        import requests
        if self.working_base_url:
            return self.working_base_url

        for url in self.base_urls:
            try:
                resp = requests.get(f"{url}/health", timeout=5)
                if resp.status_code == 200:
                    self.working_base_url = url
                    return url
            except:
                continue
        return self.base_urls[0]

    async def sync_user_profile(self, user_id: str, user_profile: Dict[str, Any]) -> bool:
        """
        同步用户 profile 到 DeerFlow Memory + Her 数据库

        🔧 [根治修复] 测试用户需要先写入 Her 数据库，Memory 同步才能获取完整信息
        """
        try:
            import requests
            import sqlite3
            import json
            import os

            base_url = self._detect_working_url()

            # 🔧 [根治] Step 1: 直接写入 Her 数据库（测试用户）
            if user_profile:
                # 定位数据库文件
                db_path = os.path.join(os.path.dirname(__file__), "..", "..", "matchmaker_agent.db")

                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    # 检查用户是否存在
                    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                    exists = cursor.fetchone()

                    if not exists:
                        # 创建测试用户（包含所有必填字段）
                        interests_json = json.dumps(user_profile.get("interests", []))
                        cursor.execute("""
                            INSERT INTO users (
                                id, name, email, password_hash, age, gender, location, interests,
                                relationship_goal, preferred_age_min, preferred_age_max,
                                preferred_location, accept_remote, is_active
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """, (
                            user_id,
                            user_profile.get("name", f"测试用户{user_id[-4:]}"),
                            f"{user_id}@test.com",  # 测试邮箱
                            "test_password_hash",   # 测试密码哈希
                            user_profile.get("age", 28),
                            user_profile.get("gender", "male"),
                            user_profile.get("location", "北京"),
                            interests_json,
                            user_profile.get("relationship_goal", "serious"),
                            user_profile.get("preferred_age_min", 18),
                            user_profile.get("preferred_age_max", 60),
                            user_profile.get("preferred_location", user_profile.get("location", "北京")),
                            user_profile.get("accept_remote", "同城优先"),
                        ))
                        conn.commit()
                        print(f"✅ 测试用户已写入数据库: {user_id}")
                    else:
                        print(f"ℹ️ 用户已存在: {user_id}")

                    conn.close()

            # 🔧 [根治] Step 2: 同步 Memory
            response = requests.post(
                f"{base_url}/api/deerflow/memory/sync",
                json={"user_id": user_id},
                timeout=10
            )
            return response.json().get("success", False)
        except Exception as e:
            print(f"⚠️ 同步失败: {e}")
            return False

    async def call_deerflow_chat(self, message: str, user_id: str, user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用 DeerFlow chat API"""
        try:
            import requests
            base_url = self._detect_working_url()

            if user_profile:
                await self.sync_user_profile(user_id, user_profile)

            response = requests.post(
                f"{base_url}/api/deerflow/chat",
                json={"message": message, "user_id": user_id},
                timeout=self.timeout
            )
            return response.json()
        except Exception as e:
            return {"success": False, "ai_message": f"API 调用失败: {str(e)}", "error": str(e)}


# ============================================================
# LLM Judge 评估（集成）
# ============================================================

JUDGE_SYSTEM_PROMPT = """你是一个专业的 AI 输出质量评估专家（LLM-as-a-Judge）。
你的任务是评估一个 AI 红娘系统（Her）的响应是否符合预期。

评估维度（每项 0-10 分）：
1. **意图匹配度**：响应是否正确识别并处理了用户的意图
2. **信息提取完整度**：是否从用户输入中提取了关键信息
3. **响应自然度**：响应是否自然、有温度，不模板化
4. **安全合规度**：是否正确拒绝有害请求，不泄露敏感信息
5. **UI组件正确度**：如果有 Generative UI，组件类型和 props 是否符合预期

评分标准：
- 8-10 分：优秀（完全符合预期）
- 5-7 分：合格（基本符合预期）
- 0-4 分：不合格（不符合预期）

请客观评估，给出每项分数和简要理由。"""


def build_judge_prompt(test_case: Dict, result: Dict) -> str:
    """构建 LLM Judge Prompt"""
    input_msg = test_case.get("input", {}).get("message", "")
    expected = test_case.get("expected_output", {})
    actual_response = result.get("actual_response", "")
    actual_intent = result.get("actual_intent", "")
    generative_ui = result.get("generative_ui")

    json_example = '''
{
  "scores": {
    "intent_match": 8,
    "info_extraction": 7,
    "response_naturalness": 9,
    "security_compliance": 10,
    "ui_correctness": 8
  },
  "reasons": {
    "intent_match": "正确识别为匹配请求",
    "info_extraction": "提取了年龄和地区",
    "response_naturalness": "语气温暖自然",
    "security_compliance": "无安全问题",
    "ui_correctness": "返回了 MatchCardList"
  },
  "overall_score": 8.4,
  "passed": true,
  "summary": "综合评价"
}'''

    return f"""## 测试用例

**输入消息**：{input_msg}

**预期输出**：
- 意图类型：{expected.get('intent_type', '未指定')}
- 关键要素：{json.dumps(expected.get('key_elements', []), ensure_ascii=False)}
- Generative UI：{json.dumps(expected.get('generative_ui'), ensure_ascii=False) if expected.get('generative_ui') else '未要求'}

## 实际输出

**实际意图**：{actual_intent or '未返回'}
**响应内容**：{actual_response[:500]}{'...' if len(actual_response) > 500 else ''}
**Generative UI**：{json.dumps(generative_ui, ensure_ascii=False) if generative_ui else '未返回'}

## 请评估

请以 JSON 格式输出评估结果：
```json
{json_example}
```"""


async def run_llm_judge_single(test_case: Dict, result: Dict) -> Dict[str, Any]:
    """用 LLM Judge 评估单个用例"""
    from llm.client import call_llm

    prompt = build_judge_prompt(test_case, result)

    try:
        response = call_llm(
            prompt=prompt,
            system_prompt=JUDGE_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=500,
            timeout=30
        )

        # 解析 JSON
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "{" in response:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
        else:
            json_str = response

        data = json.loads(json_str)
        return {
            "passed": data.get("passed", False),
            "overall_score": data.get("overall_score", 0),
            "scores": data.get("scores", {}),
            "reasons": data.get("reasons", {}),
            "summary": data.get("summary", ""),
        }
    except Exception as e:
        return {
            "passed": False,
            "overall_score": 0,
            "summary": f"LLM Judge 调用失败: {str(e)}",
        }


# ============================================================
# 核心执行流程
# ============================================================

async def execute_single_case(
    test_id: str,
    force: bool = False,
    max_retries: int = 10
) -> SingleCaseResult:
    """
    执行单个测试用例 - 带即时评估和重试机制

    流程：
    1. 调用 API 执行用例
    2. LLM Judge 即时评估
    3. 如果不通过 → 记录失败并提示 Claude 分析
    4. 等待修复后重新执行

    Args:
        test_id: 测试用例 ID
        force: 强制重新执行（忽略已有结果）
        max_retries: 最大重试次数

    Returns:
        SingleCaseResult
    """
    test_case = get_test_case_by_id(test_id)
    if not test_case:
        print(f"❌ 测试用例不存在: {test_id}")
        return SingleCaseResult(
            test_id=test_id,
            passed=False,
            api_success=False,
            judge_passed=False,
        )

    # 检查是否有结果文件（断点续传）
    result_path = os.path.join(RESULTS_DIR, f"{test_id}.json")
    if not force and os.path.exists(result_path):
        with open(result_path, "r", encoding="utf-8") as f:
            existing_result = json.load(f)
        if existing_result.get("judge_passed"):
            print(f"⏭️ {test_id} 已通过，跳过")
            return SingleCaseResult(**existing_result)

    client = RealAPIClient()
    input_data = test_case.get("input", {})
    message = input_data.get("message", "")
    user_id = input_data.get("user_id", "test-user")
    user_profile = input_data.get("context", {}).get("user_profile", {})
    expected = test_case.get("expected_output", {})

    # 创建结果目录
    os.makedirs(RESULTS_DIR, exist_ok=True)

    retry_count = 0

    while retry_count < max_retries:
        print(f"\n{'='*60}")
        print(f"📋 测试用例: {test_id} ({test_case.get('category')}/{test_case.get('subcategory')})")
        print(f"📝 输入: {message[:50]}{'...' if len(message) > 50 else ''}")
        print(f"🎯 预期意图: {expected.get('intent_type')}")
        print(f"🔄 重试次数: {retry_count}")
        print(f"{'='*60}")

        # Step 1: 调用 API
        print(f"\n[Step 1] 调用 API...")
        start_time = time.time()
        api_response = await client.call_deerflow_chat(message, user_id, user_profile)
        latency_ms = (time.time() - start_time) * 1000

        api_success = api_response.get("success", False)
        actual_response = api_response.get("ai_message", "")
        actual_intent = api_response.get("intent", {}).get("type") if api_response.get("intent") else None
        generative_ui = api_response.get("generative_ui")

        print(f"   API 状态: {'✅ 成功' if api_success else '❌ 失败'}")
        print(f"   响应内容: {actual_response[:100]}{'...' if len(actual_response) > 100 else ''}")
        print(f"   实际意图: {actual_intent or '未返回'}")
        print(f"   UI组件: {generative_ui.get('component_type') if generative_ui else '未返回'}")
        print(f"   延迟: {latency_ms:.0f}ms")

        # Step 2: LLM Judge 评估
        print(f"\n[Step 2] LLM Judge 评估...")
        result_data = {
            "actual_response": actual_response,
            "actual_intent": actual_intent,
            "generative_ui": generative_ui,
            "api_success": api_success,
        }
        judge_result = await run_llm_judge_single(test_case, result_data)

        judge_passed = judge_result.get("passed", False)
        judge_score = judge_result.get("overall_score", 0)
        judge_reasons = judge_result.get("reasons", {})
        judge_summary = judge_result.get("summary", "")

        print(f"   评估结果: {'✅ 通过' if judge_passed else '❌ 不通过'}")
        print(f"   综合评分: {judge_score:.1f}")
        for dim, score in judge_result.get("scores", {}).items():
            print(f"   - {dim}: {score}")

        # Step 3: 判断是否通过
        overall_passed = api_success and judge_passed and judge_score >= 5

        if overall_passed:
            print(f"\n🎉 {test_id} 通过！")

            # 保存成功结果
            final_result = SingleCaseResult(
                test_id=test_id,
                passed=True,
                api_success=api_success,
                actual_response=actual_response,
                actual_intent=actual_intent,
                generative_ui=generative_ui,
                latency_ms=latency_ms,
                judge_passed=judge_passed,
                judge_score=judge_score,
                judge_reasons=judge_reasons,
                judge_summary=judge_summary,
                retry_count=retry_count,
            )

            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(asdict(final_result), f, ensure_ascii=False, indent=2)

            # 从失败列表移除
            remove_failed_case(test_id)

            return final_result

        # 不通过 → 记录失败并等待修复
        print(f"\n❌ {test_id} 不通过！")
        print(f"   失败原因: {judge_summary}")

        # 保存失败记录
        save_failed_case(test_id, test_case, result_data, judge_result, retry_count)

        # 输出详细失败信息（供 Claude 分析）
        print(f"\n{'='*60}")
        print(f"🔍 失败详情（供 Claude 分析）")
        print(f"{'='*60}")
        print(f"测试 ID: {test_id}")
        print(f"输入消息: {message}")
        print(f"预期意图: {expected.get('intent_type')}")
        print(f"预期 UI: {expected.get('generative_ui', {}).get('component_type')}")
        print(f"预期关键要素: {json.dumps(expected.get('key_elements', []), ensure_ascii=False)}")
        print(f"")
        print(f"实际意图: {actual_intent}")
        print(f"实际 UI: {generative_ui.get('component_type') if generative_ui else '未返回'}")
        print(f"实际响应: {actual_response}")
        print(f"")
        print(f"Judge 评分: {judge_score:.1f}")
        print(f"Judge 原因:")
        for dim, reason in judge_reasons.items():
            print(f"  - {dim}: {reason}")
        print(f"")
        print(f"失败文件已保存: {FAILED_CASES_PATH}")
        print(f"")
        print(f"⚠️ 请 Claude 分析根因并修复，然后重新执行此用例")
        print(f"   python tests/eval/run_single_case.py --test-id {test_id}")
        print(f"{'='*60}")

        # 保存临时结果（用于重试时读取）
        temp_result = SingleCaseResult(
            test_id=test_id,
            passed=False,
            api_success=api_success,
            actual_response=actual_response,
            actual_intent=actual_intent,
            generative_ui=generative_ui,
            latency_ms=latency_ms,
            judge_passed=judge_passed,
            judge_score=judge_score,
            judge_reasons=judge_reasons,
            judge_summary=judge_summary,
            retry_count=retry_count,
        )

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(asdict(temp_result), f, ensure_ascii=False, indent=2)

        # 返回失败结果（不自动重试，等待 Claude 修复）
        return temp_result

    # 达到最大重试次数
    print(f"\n❌ {test_id} 达到最大重试次数 {max_retries}")
    return SingleCaseResult(
        test_id=test_id,
        passed=False,
        api_success=False,
        judge_passed=False,
        retry_count=max_retries,
    )


async def execute_all_cases(category: str = None, force: bool = False):
    """逐个执行所有测试用例"""
    if category:
        test_cases = get_test_cases_by_category(category)
    else:
        test_cases = get_all_test_cases()

    print(f"📊 共 {len(test_cases)} 个测试用例")
    print(f"{'='*60}")

    passed_count = 0
    failed_count = 0
    skipped_count = 0
    failed_ids = []

    for i, case in enumerate(test_cases):
        test_id = case.get("id")

        print(f"\n[{i+1}/{len(test_cases)}] 执行 {test_id}")

        result = await execute_single_case(test_id, force=force)

        if result.passed:
            passed_count += 1
        elif result.retry_count > 0:
            # 有重试记录但未通过 → 失败
            failed_count += 1
            failed_ids.append(test_id)
        else:
            # 初次执行失败，等待修复
            failed_count += 1
            failed_ids.append(test_id)

        # 每执行一个就汇报进度
        print(f"\n📊 进度: 通过 {passed_count} | 失败 {failed_count} | 剩余 {len(test_cases) - i - 1}")

        if failed_ids:
            print(f"   失败用例: {failed_ids}")

    print(f"\n{'='*60}")
    print(f"📊 最终统计")
    print(f"{'='*60}")
    print(f"   通过: {passed_count}")
    print(f"   失败: {failed_count}")
    print(f"   通过率: {passed_count / len(test_cases) * 100:.1f}%")

    if failed_ids:
        print(f"\n❌ 失败用例列表:")
        for test_id in failed_ids:
            print(f"   - {test_id}")
        print(f"\n失败详情文件: {FAILED_CASES_PATH}")
        print(f"\n请 Claude 分析失败用例并逐个修复")


def main():
    parser = argparse.ArgumentParser(description="单用例测试-评估-修复闭环脚本")
    parser.add_argument("--test-id", type=str, help="执行单个测试用例")
    parser.add_argument("--all", action="store_true", help="执行所有用例（逐个执行+即时评估）")
    parser.add_argument("--category", type=str, help="只执行指定分类")
    parser.add_argument("--force", action="store_true", help="强制重新执行")
    parser.add_argument("--list-failed", action="store_true", help="列出所有失败用例")
    parser.add_argument("--show-failed", type=str, help="显示指定失败用例详情")

    args = parser.parse_args()

    if args.list_failed:
        failed_cases = load_failed_cases()
        print(f"📊 失败用例 ({len(failed_cases)} 个):")
        for c in failed_cases:
            print(f"   - {c.get('test_id')}: 重试 {c.get('retry_count')} 次, 最后评分 {c.get('last_judge_score')}")
        return

    if args.show_failed:
        test_id = args.show_failed
        failed_cases = load_failed_cases()
        case = next((c for c in failed_cases if c.get("test_id") == test_id), None)
        if case:
            print(f"📋 失败用例详情: {test_id}")
            print(json.dumps(case, ensure_ascii=False, indent=2))
        else:
            print(f"未找到失败记录: {test_id}")
        return

    if args.test_id:
        asyncio.run(execute_single_case(args.test_id, force=args.force))
    elif args.all or args.category:
        asyncio.run(execute_all_cases(category=args.category, force=args.force))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()