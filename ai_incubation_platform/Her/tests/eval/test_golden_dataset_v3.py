"""
Golden Dataset 评估脚本 - 增量执行版本 (v3)

核心优化：
1. 断点续传：读取已有结果，跳过已执行的用例
2. 增量写入：每执行一个用例就写入结果文件
3. 容错机制：单个失败不影响其他用例继续执行
4. 实时进度：显示已完成/总数/跳过数

用法：
    # 执行测试（自动跳过已完成的用例）
    python tests/eval/test_golden_dataset_v3.py --real

    # 强制重新执行所有用例
    python tests/eval/test_golden_dataset_v3.py --real --force

    # 只执行指定分类
    python tests/eval/test_golden_dataset_v3.py --real --category happy_path

    # 用 LLM 评估结果
    python tests/eval/llm_judge.py --input evaluation_results.json
"""

import json
import os
import sys
import argparse
import asyncio
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field, asdict

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# 测试数据集路径
GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
REPORT_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "evaluation_report.html")


def load_golden_dataset() -> Dict[str, Any]:
    """加载测试数据集"""
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_test_cases(category_filter: str = None) -> List[Dict[str, Any]]:
    """获取测试用例（可选按分类过滤）"""
    dataset = load_golden_dataset()
    cases = dataset.get("test_cases", [])

    if category_filter:
        cases = [c for c in cases if c.get("category") == category_filter]

    return cases


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    category: str
    subcategory: str
    input_message: str
    expected_intent: Optional[str] = None
    actual_intent: Optional[str] = None
    actual_response: str = ""
    generative_ui: Optional[Dict] = None
    passed: bool = True
    details: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    error: Optional[str] = None
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class IncrementalResultWriter:
    """增量结果写入器 - 支持断点续传（每个用例单独文件）"""

    def __init__(self, results_dir: str, test_cases: List[Dict], force_restart: bool = False):
        self.results_dir = results_dir
        self.test_cases = test_cases
        self.force_restart = force_restart
        self.completed_ids: Set[str] = set()
        self.results: List[TestResult] = []
        self.meta: Dict[str, Any] = {}

        # 确保结果目录存在
        os.makedirs(results_dir, exist_ok=True)

        # 汇总文件路径
        self.summary_path = os.path.join(results_dir, "evaluation_results.json")

        # 初始化：读取已有结果
        self._initialize()

    def _initialize(self):
        """初始化：扫描已有结果文件"""
        if self.force_restart:
            print("🔄 强制重新执行，忽略已有结果")
            return

        # 扫描 results 目录下的所有 TC*.json 文件
        existing_files = [f for f in os.listdir(self.results_dir) if f.startswith("TC") and f.endswith(".json")]

        for filename in existing_files:
            test_id = filename.replace(".json", "")
            filepath = os.path.join(self.results_dir, filename)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.completed_ids.add(test_id)
                # 恢复已有的结果
                result_data = data.get("result", data)
                self.results.append(TestResult(
                    test_id=test_id,
                    category=result_data.get("category"),
                    subcategory=result_data.get("subcategory"),
                    input_message=result_data.get("input_message"),
                    expected_intent=result_data.get("expected_intent"),
                    actual_intent=result_data.get("actual_intent"),
                    actual_response=result_data.get("actual_response", ""),
                    generative_ui=result_data.get("generative_ui"),
                    passed=result_data.get("passed", True),
                    details=result_data.get("details", []),
                    latency_ms=result_data.get("latency_ms", 0),
                    error=result_data.get("error"),
                    executed_at=result_data.get("executed_at", ""),
                ))
            except Exception as e:
                print(f"⚠️ 读取 {filename} 失败: {e}")

        if self.completed_ids:
            print(f"📂 已读取 {len(self.completed_ids)} 个已完成用例")
        else:
            print("📝 未找到已有结果文件，将从头开始")

    def should_execute(self, test_id: str) -> bool:
        """判断是否应该执行此用例"""
        return test_id not in self.completed_ids

    def add_result(self, result: TestResult):
        """添加新结果并立即写入单独文件"""
        self.results.append(result)
        self.completed_ids.add(result.test_id)

        # 🔴 立即写入单独文件（每个用例一个文件）
        self._save_single_result(result)

        # 同时更新汇总文件
        self._save_summary_file()

        print(f"💾 已保存结果: {result.test_id}")

    def _save_single_result(self, result: TestResult):
        """保存单个结果到单独文件"""
        filepath = os.path.join(self.results_dir, f"{result.test_id}.json")

        json_data = {
            "test_id": result.test_id,
            "category": result.category,
            "subcategory": result.subcategory,
            "input_message": result.input_message,
            "expected_intent": result.expected_intent,
            "actual_intent": result.actual_intent,
            "actual_response": result.actual_response,
            "generative_ui": result.generative_ui,
            "passed": result.passed,
            "details": result.details,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "executed_at": result.executed_at,
        }

        # 原子写入
        temp_path = filepath + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, filepath)

    def _save_summary_file(self):
        """保存汇总文件（用于 HTML 报告生成）"""
        json_data = {
            "meta": {
                "total_cases": len(self.test_cases),
                "completed_count": len(self.completed_ids),
                "last_updated": datetime.now().isoformat(),
                "version": "v3_incremental_per_file"
            },
            "results": [asdict(r) for r in self.results]
        }

        temp_path = self.summary_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.summary_path)

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "total": len(self.test_cases),
            "completed": len(self.completed_ids),
            "pending": len(self.test_cases) - len(self.completed_ids),
        }


class RealAPIClient:
    """真实 API 客户端"""

    def __init__(self):
        # 支持多个端口尝试
        self.base_urls = [
            "http://localhost:8000",  # Her Backend 默认端口
            "http://localhost:8002",  # 测试端口
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
                    print(f"✅ API 端点可用: {url}")
                    return url
            except:
                continue

        # 默认返回第一个
        print(f"⚠️ 无法检测到可用的 API，使用默认: {self.base_urls[0]}")
        return self.base_urls[0]

    async def sync_user_profile(self, user_id: str, user_profile: Dict[str, Any]) -> bool:
        """同步用户 profile 到 DeerFlow Memory"""
        try:
            import requests
            base_url = self._detect_working_url()
            response = requests.post(
                f"{base_url}/api/deerflow/memory/sync",
                json={"user_id": user_id},
                timeout=10
            )
            return response.json().get("success", False)
        except Exception as e:
            print(f"⚠️ Memory 同步失败: {e}")
            return False

    async def call_deerflow_chat(self, message: str, user_id: str, user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用 DeerFlow chat API"""
        try:
            import requests
            base_url = self._detect_working_url()

            # 先同步用户 profile（如果有）
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


class Validator:
    """验证器 - 只记录结果，不判断（LLM-as-a-Judge 模式）"""

    def validate(self, test_case: Dict[str, Any], api_response: Dict[str, Any]) -> TestResult:
        """只记录响应内容，不做硬编码判断"""
        expected = test_case.get("expected_output", {})
        input_data = test_case.get("input", {})

        result = TestResult(
            test_id=test_case.get("id"),
            category=test_case.get("category"),
            subcategory=test_case.get("subcategory"),
            input_message=input_data.get("message", ""),
            expected_intent=expected.get("intent_type"),
            actual_intent=api_response.get("intent", {}).get("type") if api_response.get("intent") else None,
            actual_response=api_response.get("ai_message", ""),
            generative_ui=api_response.get("generative_ui"),
            latency_ms=api_response.get("_latency_ms", 0)
        )

        # 记录 API 调用状态
        if not api_response.get("success"):
            result.error = "API 返回失败"
            result.details.append(f"API 错误: {api_response.get('error', '未知错误')}")
            result.passed = False  # API 失败标记为失败

        # 记录实际响应内容
        result.details.append(f"实际响应: {result.actual_response[:200]}{'...' if len(result.actual_response) > 200 else ''}")

        # 记录意图信息
        expected_intent = expected.get("intent_type")
        if expected_intent and result.actual_intent:
            if expected_intent == result.actual_intent:
                result.details.append(f"意图: 预期 '{expected_intent}' = 实际 '{result.actual_intent}'")
            else:
                result.details.append(f"意图: 预期 '{expected_intent}' vs 实际 '{result.actual_intent}'")
        elif expected_intent:
            result.details.append(f"意图: 预期 '{expected_intent}'，API 未返回意图字段")
        else:
            result.details.append(f"意图: 无预期，实际 '{result.actual_intent or '未返回'}'")

        # 记录 Generative UI 信息
        if result.generative_ui:
            ui_type = result.generative_ui.get("component_type", "unknown")
            result.details.append(f"UI组件: {ui_type}")
        elif expected.get("generative_ui"):
            result.details.append(f"UI组件: 预期 '{expected['generative_ui'].get('component_type')}'，实际未返回")
        else:
            result.details.append(f"UI组件: 无")

        # 记录延迟
        result.details.append(f"延迟: {result.latency_ms:.0f}ms")

        return result


def generate_html_report(results: List[TestResult], use_real_api: bool) -> str:
    """生成 HTML 评估报告"""

    total = len(results)
    passed = sum(1 for r in results if r.passed and not r.error)
    failed = sum(1 for r in results if not r.passed or r.error)
    api_errors = sum(1 for r in results if r.error)
    pass_rate = passed / total * 100 if total > 0 else 0

    by_category = {}
    for r in results:
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"passed": 0, "failed": 0, "total": 0}
        by_category[cat]["total"] += 1
        if r.passed and not r.error:
            by_category[cat]["passed"] += 1
        else:
            by_category[cat]["failed"] += 1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    api_mode_text = "真实 API" if use_real_api else "模拟 API"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Golden Dataset 评估报告 (增量版)</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 20px; margin: 0; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header .meta {{ font-size: 14px; opacity: 0.9; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .stat-card h3 {{ font-size: 14px; color: #666; margin-bottom: 10px; }}
        .stat-card .value {{ font-size: 32px; font-weight: bold; }}
        .stat-card.passed .value {{ color: #10b981; }}
        .stat-card.failed .value {{ color: #ef4444; }}
        .stat-card.error .value {{ color: #f59e0b; }}
        .progress-bar {{ height: 8px; background: #e5e7eb; border-radius: 4px; margin-top: 10px; overflow: hidden; }}
        .progress-bar .fill {{ height: 100%; background: #10b981; }}
        .category-section {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; }}
        .status-pass {{ color: #10b981; }}
        .status-fail {{ color: #ef4444; }}
        .status-error {{ color: #f59e0b; }}
        .test-id {{ font-weight: 600; color: #667eea; }}
        .message-cell {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; }}
        .response-cell {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; }}
        .detail-item {{ font-size: 12px; color: #666; margin: 4px 0; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📊 Golden Dataset 评估报告</h1>
        <div class="meta">
            生成时间: {timestamp} | API 模式: {api_mode_text} | 增量执行版本 v3
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card total">
            <h3>总用例数</h3>
            <div class="value">{total}</div>
        </div>
        <div class="stat-card passed">
            <h3>执行成功</h3>
            <div class="value">{passed}</div>
            <div class="progress-bar"><div class="fill" style="width: {pass_rate}%"></div></div>
        </div>
        <div class="stat-card failed">
            <h3>执行失败</h3>
            <div class="value">{failed}</div>
        </div>
        <div class="stat-card error">
            <h3>API 错误</h3>
            <div class="value">{api_errors}</div>
        </div>
    </div>
"""

    # 按分类展示
    for cat, stats in by_category.items():
        cat_pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        html += f"""
    <div class="category-section">
        <div class="category-header">
            <h2>{cat}</h2>
            <div>
                <span class="status-pass">✅ {stats['passed']}</span>
                <span class="status-fail">❌ {stats['failed']}</span>
                <span style="color: #666;">({cat_pass_rate:.1f}%)</span>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>输入</th>
                    <th>意图</th>
                    <th>响应</th>
                    <th>延迟</th>
                    <th>状态</th>
                    <th>详情</th>
                </tr>
            </thead>
            <tbody>
"""

        for r in results:
            if r.category != cat:
                continue

            status_icon = "✅" if r.passed and not r.error else ("⚠️" if r.error else "❌")
            status_class = "status-pass" if r.passed and not r.error else ("status-error" if r.error else "status-fail")

            msg_preview = r.input_message[:30] + "..." if len(r.input_message) > 30 else r.input_message
            response_preview = r.actual_response[:50] + "..." if len(r.actual_response) > 50 else r.actual_response
            details_html = "".join([f"<div class='detail-item'>• {d}</div>" for d in r.details[:5]])

            intent_html = f"{r.actual_intent or '-'}"
            if r.expected_intent and r.actual_intent:
                match = "✓" if r.expected_intent == r.actual_intent else "≠"
                intent_html = f"{match} {r.actual_intent}"

            html += f"""
                <tr>
                    <td class="test-id">{r.test_id}</td>
                    <td class="message-cell">{msg_preview}</td>
                    <td>{intent_html}</td>
                    <td class="response-cell">{response_preview}</td>
                    <td>{r.latency_ms:.0f}ms</td>
                    <td><span class="{status_class}">{status_icon}</span></td>
                    <td>{details_html}</td>
                </tr>"""

        html += """
            </tbody>
        </table>
    </div>"""

    html += """
</div>
</body>
</html>"""

    return html


async def run_evaluation(
    use_real_api: bool = True,
    force_restart: bool = False,
    category_filter: str = None
) -> List[TestResult]:
    """运行评估 - 增量版本（每个用例单独文件）"""

    test_cases = get_test_cases(category_filter)
    validator = Validator()
    client = RealAPIClient() if use_real_api else MockAPIClient()

    # 初始化增量写入器（传入目录路径）
    result_writer = IncrementalResultWriter(RESULTS_DIR, test_cases, force_restart)
    stats = result_writer.get_stats()

    print(f"\n{'🌐 使用真实 API' if use_real_api else '🎭 使用模拟 API'}...")
    print(f"📊 总用例: {stats['total']} | 已完成: {stats['completed']} | 待执行: {stats['pending']}")
    print("-" * 60)

    executed_count = 0
    skipped_count = 0
    error_count = 0

    for i, case in enumerate(test_cases):
        test_id = case.get("id")

        # 断点续传：跳过已执行的用例
        if not result_writer.should_execute(test_id):
            skipped_count += 1
            print(f"[{i+1}/{len(test_cases)}] ⏭️ 跳过 {test_id} (已完成)")
            continue

        input_data = case.get("input", {})
        message = input_data.get("message", "")
        user_id = input_data.get("user_id", "test-user")
        user_profile = input_data.get("context", {}).get("user_profile", {})

        # 容错执行
        try:
            start_time = time.time()
            api_response = await client.call_deerflow_chat(message, user_id, user_profile)
            latency_ms = (time.time() - start_time) * 1000
            api_response["_latency_ms"] = latency_ms

            result = validator.validate(case, api_response)

            # 增量写入
            result_writer.add_result(result)
            executed_count += 1

            status = "✅" if result.passed and not result.error else ("⚠️" if result.error else "❌")
            print(f"[{i+1}/{len(test_cases)}] {status} {test_id}: {message[:25]}...")

            if result.error:
                error_count += 1

        except Exception as e:
            # 记录失败但不中断
            error_count += 1
            print(f"[{i+1}/{len(test_cases)}] ❌ {test_id}: 执行失败 - {str(e)[:50]}")

            # 写入失败结果
            failed_result = TestResult(
                test_id=test_id,
                category=case.get("category"),
                subcategory=case.get("subcategory"),
                input_message=message,
                error=str(e),
                passed=False,
                details=[f"执行异常: {str(e)}"]
            )
            result_writer.add_result(failed_result)

    print("-" * 60)
    print(f"✅ 评估完成!")
    print(f"   本次执行: {executed_count} | 跳过: {skipped_count} | 错误: {error_count}")

    return result_writer.results


class MockAPIClient:
    """模拟 API 客户端（用于无服务环境）"""

    async def call_deerflow_chat(self, message: str, user_id: str, user_profile: Dict = None) -> Dict:
        """模拟调用"""
        response = {"success": True, "deerflow_used": False, "ai_message": "", "intent": {}, "generative_ui": None}

        # 简化的意图识别
        if any(kw in message for kw in ["找对象", "推荐", "匹配"]):
            response["ai_message"] = "找到了几个匹配对象~"
            response["intent"] = {"type": "match_request"}
            response["generative_ui"] = {"component_type": "MatchCardList", "props": {"matches": [], "total": 1}}
        elif any(kw in message for kw in ["你好", "hello"]):
            response["ai_message"] = "你好呀！我是 Her 红娘助手~"
            response["intent"] = {"type": "conversation"}
        elif any(kw in message for kw in ["聊什么", "怎么开口"]):
            response["ai_message"] = "可以聊聊共同的兴趣~"
            response["intent"] = {"type": "icebreaker_request"}
        else:
            response["ai_message"] = "好的，有什么可以帮你的？"
            response["intent"] = {"type": "conversation"}

        return response


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Golden Dataset 评估 - 增量版本 v3")
    parser.add_argument("--real", action="store_true", help="使用真实 API")
    parser.add_argument("--mock", action="store_true", help="使用模拟 API")
    parser.add_argument("--force", action="store_true", help="强制重新执行所有用例")
    parser.add_argument("--category", type=str, default=None, help="只执行指定分类")
    parser.add_argument("--output", type=str, default=REPORT_OUTPUT_PATH, help="报告输出路径")

    args = parser.parse_args()
    use_real_api = args.real and not args.mock

    # 运行测试（增量执行）
    results = asyncio.run(run_evaluation(
        use_real_api=use_real_api,
        force_restart=args.force,
        category_filter=args.category
    ))

    # 生成 HTML 报告
    html = generate_html_report(results, use_real_api)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n📊 HTML 报告已生成: {args.output}")
    print(f"📄 单独结果文件目录: {RESULTS_DIR}")
    print(f"📄 汇总结果文件: {os.path.join(RESULTS_DIR, 'evaluation_results.json')}")

    print(f"\n下一步: 运行 LLM-as-a-Judge 评估")
    print(f"  python tests/eval/llm_judge.py --input {os.path.join(RESULTS_DIR, 'evaluation_results.json')}")


if __name__ == "__main__":
    main()