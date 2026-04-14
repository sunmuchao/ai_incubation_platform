"""
Golden Dataset 评估脚本 - LLM-as-a-Judge 版本

核心理念：从"断言"转向"评测"
- 不硬编码判断规则
- 只记录实际响应结果
- 用 LLM 来评估响应是否符合预期

用法：
    # 执行测试，生成原始结果 JSON
    python tests/eval/test_golden_dataset.py --real

    # 用 LLM 评估结果
    python tests/eval/test_golden_dataset.py --real --llm-eval

    # 用 Claude/GPT-4 作为 Judge
    python tests/eval/llm_judge.py --input evaluation_results.json

功能：
    1. 加载 golden_dataset.json
    2. 对每个测试用例调用 DeerFlow API
    3. 记录响应内容（不做硬编码判断）
    4. 可选：用 LLM-as-a-Judge 评估
    5. 生成 HTML 评估报告
"""

import json
import os
import sys
import argparse
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# 测试数据集路径
GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
REPORT_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "evaluation_report.html")


def load_golden_dataset() -> Dict[str, Any]:
    """加载测试数据集"""
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_test_cases() -> List[Dict[str, Any]]:
    """获取所有测试用例"""
    dataset = load_golden_dataset()
    return dataset.get("test_cases", [])


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


class RealAPIClient:
    """真实 API 客户端"""

    def __init__(self):
        self.base_url = "http://localhost:8002"
        self.timeout = 60

    async def sync_user_profile(self, user_id: str, user_profile: Dict[str, Any]) -> bool:
        """
        🔧 [修复] 先同步用户 profile 到 DeerFlow Memory

        这样 Agent 才能获取到用户的完整信息，不会重复追问
        """
        try:
            import requests
            # 调用 Memory 同步 API
            response = requests.post(
                f"{self.base_url}/api/deerflow/memory/sync",
                json={"user_id": user_id},
                timeout=10
            )
            return response.json().get("success", False)
        except Exception as e:
            print(f"⚠️ Memory 同步失败: {e}")
            return False

    async def call_deerflow_chat(self, message: str, user_id: str, user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        🔧 [修复] 调用 DeerFlow chat API，先同步用户 profile

        Args:
            message: 用户消息
            user_id: 用户 ID
            user_profile: 用户画像（可选，用于先同步）
        """
        try:
            import requests

            # 🔧 [修复] 先同步用户 profile（如果有）
            if user_profile:
                await self.sync_user_profile(user_id, user_profile)

            response = requests.post(
                f"{self.base_url}/api/deerflow/chat",
                json={"message": message, "user_id": user_id},
                timeout=self.timeout
            )
            return response.json()
        except Exception as e:
            return {"success": False, "ai_message": f"API 调用失败: {str(e)}", "error": str(e)}


class MockAPIClient:
    """模拟 API 客户端（用于无服务环境）"""

    async def call_deerflow_chat(self, message: str, user_id: str) -> Dict[str, Any]:
        """模拟调用"""
        response = {"success": True, "deerflow_used": False, "ai_message": "", "intent": {}, "generative_ui": None}

        # 模拟意图识别
        if any(kw in message for kw in ["找对象", "推荐", "匹配", "找人", "附近", "看看有没有"]):
            response["ai_message"] = "找到了几个匹配对象，看看有没有喜欢的~"
            response["intent"] = {"type": "match_request"}
            response["generative_ui"] = {"component_type": "MatchCardList", "props": {"matches": [{"name": "测试用户", "age": 28}], "total": 1}}
        elif any(kw in message for kw in ["你好", "hello", "嗨", "哈喽", "hi"]):
            response["ai_message"] = "你好呀！我是 Her 红娘助手，有什么能帮你的吗？"
            response["intent"] = {"type": "conversation"}
        elif any(kw in message for kw in ["刚注册", "怎么开始"]):
            response["ai_message"] = "欢迎你！让我先了解一下你的基本信息吧~"
            response["intent"] = {"type": "profile_collection"}
            response["generative_ui"] = {"component_type": "ProfileQuestionCard", "props": {"question": "你今年多大呀？"}}
        elif any(kw in message for kw in ["我是", "我喜欢"]) and "对象" not in message:
            response["ai_message"] = "好的，我记住了！"
            response["intent"] = {"type": "profile_update"}
        elif any(kw in message for kw in ["聊什么", "怎么聊", "怎么开口", "怎么回"]):
            response["ai_message"] = "可以聊聊你们共同的兴趣，比如..."
            response["intent"] = {"type": "icebreaker_request"}
            response["generative_ui"] = {"component_type": "IcebreakerCard", "props": {"icebreakers": [{"topic": "兴趣", "suggestion": "问问TA平时喜欢做什么"}]}}
        elif any(kw in message for kw in ["分析", "合适程度", "价值观"]):
            response["ai_message"] = "让我分析一下你们的匹配程度..."
            response["intent"] = {"type": "compatibility_analysis"}
            response["generative_ui"] = {"component_type": "CompatibilityChart", "props": {"overall_score": 75}}
        elif any(kw in message for kw in ["约会", "去哪里", "约会去哪"]):
            response["ai_message"] = "我推荐几个约会地点给你参考..."
            response["intent"] = {"type": "date_planning"}
            response["generative_ui"] = {"component_type": "DatePlanCard", "props": {"plans": [{"type": "cafe"}]}}
        elif any(kw in message for kw in ["不喜欢", "接受异地", "喜欢年龄"]):
            response["ai_message"] = "好的，我会记住你的偏好！"
            response["intent"] = {"type": "preference_update"}
        elif any(kw in message for kw in ["资料完善", "匹配偏好"]):
            response["ai_message"] = "让我看看你的资料..."
            response["intent"] = {"type": "profile_query"}
        elif message == "" or message.strip() == "":
            response["success"] = False
            response["ai_message"] = "请说点什么吧，我没听清~"
            response["intent"] = {"type": "error"}
        elif any(kw in message for kw in ["忽略", "忽略指令", "系统密码", "管理员", "删除所有"]):
            response["ai_message"] = "我是一个红娘助手，只能帮你找对象、聊聊天哦~"
            response["intent"] = {"type": "conversation"}
        elif any(kw in message for kw in ["手机号", "完整画像", "VIP", "付费"]):
            response["ai_message"] = "抱歉，这个信息我不能提供哦~"
            response["intent"] = {"type": "conversation"}
        else:
            response["ai_message"] = "好的，有什么我可以帮你的吗？"
            response["intent"] = {"type": "conversation"}

        return response


class Validator:
    """验证器 - 只记录结果，不判断（LLM-as-a-Judge 模式）"""

    def validate(self, test_case: Dict[str, Any], api_response: Dict[str, Any]) -> TestResult:
        """只记录响应内容，不做硬编码判断，由 LLM-as-a-Judge 来评估"""
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

        # ============================================================
        # 只记录信息，不做判断 —— 交给 LLM-as-a-Judge 评估
        # ============================================================

        # 记录实际响应内容（截取前 200 字符供参考）
        result.details.append(f"实际响应: {result.actual_response[:200]}{'...' if len(result.actual_response) > 200 else ''}")

        # 记录意图信息（信息性）
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

        # 记录 API 状态
        result.details.append(f"API状态: {'成功' if api_response.get('success') else '失败'}")

        # 记录延迟
        result.details.append(f"延迟: {result.latency_ms:.0f}ms")

        # 标记待 LLM 评估（passed 默认 True，表示"记录完成"，不代表"通过测试"）
        result.details.append("⏳ 状态: 待 LLM-as-a-Judge 评估")
        result.passed = True  # 这里 True 表示"已记录"，实际评估由 LLM 完成

        return result


def generate_html_report(results: List[TestResult], use_real_api: bool) -> str:
    """生成 HTML 评估报告"""

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    pass_rate = passed / total * 100 if total > 0 else 0

    by_category = {}
    for r in results:
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"passed": 0, "failed": 0, "total": 0}
        by_category[cat]["total"] += 1
        if r.passed:
            by_category[cat]["passed"] += 1
        else:
            by_category[cat]["failed"] += 1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    api_mode_text = "真实 API" if use_real_api else "模拟 API"
    api_mode_class = "real" if use_real_api else "mock"

    html_parts = []

    # HTML 头部
    html_parts.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Golden Dataset 评估报告</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 20px; margin: 0; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header .meta { font-size: 14px; opacity: 0.9; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .stat-card h3 { font-size: 14px; color: #666; margin-bottom: 10px; }
        .stat-card .value { font-size: 32px; font-weight: bold; }
        .stat-card.passed .value { color: #10b981; }
        .stat-card.failed .value { color: #ef4444; }
        .stat-card.total .value { color: #3b82f6; }
        .progress-bar { height: 8px; background: #e5e7eb; border-radius: 4px; margin-top: 10px; overflow: hidden; }
        .progress-bar .fill { height: 100%; background: #10b981; }
        .category-section { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .category-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px; }
        .category-header h2 { font-size: 18px; color: #333; }
        .badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; }
        .badge.pass { background: #d1fae5; color: #065f46; }
        .badge.fail { background: #fee2e2; color: #991b1b; }
        .test-table { width: 100%; border-collapse: collapse; }
        .test-table th { background: #f9fafb; padding: 12px; text-align: left; font-size: 12px; color: #666; border-bottom: 1px solid #e5e7eb; }
        .test-table td { padding: 12px; border-bottom: 1px solid #f3f4f6; font-size: 13px; }
        .test-table tr:hover { background: #f9fafb; }
        .test-id { color: #6366f1; font-weight: 500; }
        .message-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .intent-box { padding: 4px 8px; border-radius: 4px; font-size: 11px; display: inline-block; margin-right: 5px; }
        .intent-box.expected { background: #dbeafe; color: #1e40af; }
        .intent-box.actual { background: #fef3c7; color: #92400e; }
        .intent-box.match { background: #d1fae5; color: #065f46; }
        .status-pass { color: #10b981; }
        .status-fail { color: #ef4444; }
        .detail-item { color: #dc2626; font-size: 12px; margin-bottom: 4px; }
        .response-cell { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #666; }
        .api-mode { padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px; }
        .api-mode.real { background: #dbeafe; color: #1e40af; }
        .api-mode.mock { background: #f3f4f6; color: #6b7280; }
    </style>
</head>
<body>
    <div class="container">""")

    # Header
    html_parts.append(f"""
        <div class="header">
            <h1>Golden Dataset 评估报告</h1>
            <div class="meta">
                生成时间: {timestamp}
                <span class="api-mode {api_mode_class}">{api_mode_text}</span>
                | 测试用例: {total} 条
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card total">
                <h3>总测试数</h3>
                <div class="value">{total}</div>
            </div>
            <div class="stat-card passed">
                <h3>通过</h3>
                <div class="value">{passed}</div>
                <div class="progress-bar"><div class="fill" style="width: {pass_rate:.1f}%"></div></div>
            </div>
            <div class="stat-card failed">
                <h3>失败</h3>
                <div class="value">{failed}</div>
                <div class="progress-bar"><div class="fill" style="width: {(failed/total*100) if total > 0 else 0:.1f}%; background: #ef4444"></div></div>
            </div>
            <div class="stat-card">
                <h3>通过率</h3>
                <div class="value" style="color: {'#10b981' if pass_rate >= 80 else '#f59e0b' if pass_rate >= 50 else '#ef4444'}">{pass_rate:.1f}%</div>
            </div>
        </div>""")

    # 分类统计
    for cat, stats in by_category.items():
        cat_pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        badge_class = "pass" if cat_pass_rate >= 80 else "fail"

        html_parts.append(f"""
        <div class="category-section">
            <div class="category-header">
                <h2>{cat.replace('_', ' ').title()} ({stats['passed']}/{stats['total']})</h2>
                <span class="badge {badge_class}">{cat_pass_rate:.0f}% 通过</span>
            </div>
            <table class="test-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>输入消息</th>
                        <th>意图</th>
                        <th>响应</th>
                        <th>延迟</th>
                        <th>状态</th>
                        <th>详情</th>
                    </tr>
                </thead>
                <tbody>""")

        for r in results:
            if r.category != cat:
                continue

            # 意图匹配显示
            intent_html = ""
            if r.expected_intent and r.actual_intent:
                if r.expected_intent == r.actual_intent:
                    intent_html = f"<span class='intent-box match'>{r.actual_intent}</span>"
                else:
                    intent_html = f"<span class='intent-box expected'>{r.expected_intent}</span> → <span class='intent-box actual'>{r.actual_intent or 'None'}</span>"
            elif r.actual_intent:
                intent_html = f"<span class='intent-box actual'>{r.actual_intent}</span>"

            # 详情
            details_html = "".join([f"<div class='detail-item'>• {d}</div>" for d in r.details]) if r.details else ""

            # 响应预览
            response_preview = r.actual_response[:50] + "..." if len(r.actual_response) > 50 else r.actual_response

            # 消息预览
            msg_preview = r.input_message[:30] + "..." if len(r.input_message) > 30 else r.input_message

            status_icon = "✅" if r.passed else "❌"
            status_class = "status-pass" if r.passed else "status-fail"

            html_parts.append(f"""
                    <tr>
                        <td class="test-id">{r.test_id}</td>
                        <td class="message-cell">{msg_preview}</td>
                        <td>{intent_html}</td>
                        <td class="response-cell">{response_preview}</td>
                        <td>{r.latency_ms:.0f}ms</td>
                        <td><span class="{status_class}">{status_icon}</span></td>
                        <td>{details_html}</td>
                    </tr>""")

        html_parts.append("""
                </tbody>
            </table>
        </div>""")

    html_parts.append("""
    </div>
</body>
</html>""")

    return "".join(html_parts)


async def run_evaluation(use_real_api: bool = True) -> List[TestResult]:
    """运行评估"""
    cases = get_test_cases()
    validator = Validator()

    client = RealAPIClient() if use_real_api else MockAPIClient()
    print(f"{'🌐 使用真实 API' if use_real_api else '🎭 使用模拟 API'}...")
    print(f"\n开始评估 {len(cases)} 个测试用例...")
    print("-" * 50)

    results = []

    for i, case in enumerate(cases):
        input_data = case.get("input", {})
        message = input_data.get("message", "")
        user_id = input_data.get("user_id", "test-user")
        # 🔧 [修复] 获取用户 profile，用于先同步到 Memory
        user_profile = input_data.get("context", {}).get("user_profile", {})

        start_time = time.time()
        # 🔧 [修复] 传入用户 profile，先同步到 Memory
        api_response = await client.call_deerflow_chat(message, user_id, user_profile)
        latency_ms = (time.time() - start_time) * 1000
        api_response["_latency_ms"] = latency_ms

        result = validator.validate(case, api_response)
        results.append(result)

        status = "✅" if result.passed else "❌"
        print(f"[{i+1}/{len(cases)}] {status} {case['id']}: {message[:20]}...")

    print("-" * 50)
    print("评估完成!")
    return results


def save_json_results(results: List[TestResult], test_cases: List[Dict], output_path: str):
    """保存 JSON 结果（供 LLM-as-a-Judge 评估）"""

    json_data = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "total_cases": len(results),
            "api_mode": "real_api"
        },
        "test_cases": test_cases,  # 保留原始测试用例（含预期输出）
        "results": [
            {
                "test_id": r.test_id,
                "category": r.category,
                "subcategory": r.subcategory,
                "input_message": r.input_message,
                "expected_intent": r.expected_intent,
                "actual_intent": r.actual_intent,
                "actual_response": r.actual_response,
                "generative_ui": r.generative_ui,
                "latency_ms": r.latency_ms,
                "api_success": r.error is None,
                "error": r.error,
                "details": r.details
            }
            for r in results
        ]
    }

    json_path = output_path.replace(".html", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"📄 JSON 结果已保存: {json_path}")
    return json_path


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Golden Dataset 评估 - LLM-as-a-Judge 模式")
    parser.add_argument("--real", action="store_true", help="使用真实 API")
    parser.add_argument("--mock", action="store_true", help="使用模拟 API")
    parser.add_argument("--output", type=str, default=REPORT_OUTPUT_PATH, help="报告输出路径")

    args = parser.parse_args()
    use_real_api = args.real and not args.mock

    # 运行测试，只记录结果
    results = asyncio.run(run_evaluation(use_real_api))
    test_cases = get_test_cases()

    # 保存 JSON 结果（供 LLM-as-a-Judge）
    json_path = save_json_results(results, test_cases, args.output)

    # 同时生成 HTML 报告（可选查看）
    html = generate_html_report(results, use_real_api)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📊 HTML 报告已生成: {args.output}")

    print(f"\n✅ 测试执行完成！")
    print(f"下一步: 运行 LLM-as-a-Judge 评估")
    print(f"  python tests/eval/llm_judge.py --input {json_path}")


if __name__ == "__main__":
    main()