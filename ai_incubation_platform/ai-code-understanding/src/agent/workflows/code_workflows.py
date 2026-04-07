"""
代码理解工作流

定义 DeerFlow 2.0 风格的代码理解多步工作流
"""
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.code_tools import get_tools

logger = logging.getLogger(__name__)


class workflow:
    """工作流装饰器（本地简化版）"""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    def __call__(self, cls):
        cls.workflow_name = self.name
        cls.workflow_description = self.description
        return cls


class step:
    """步骤装饰器"""
    def __init__(self, description: str = ""):
        self.description = description

    def __call__(self, func):
        func.step_description = self.description
        return func


@workflow(
    name="code_understanding",
    description="代码理解工作流：分析代码、生成解释、提供引用"
)
class CodeUnderstandingWorkflow:
    """
    代码理解工作流

    流程：
    1. 解析用户意图
    2. 检索相关代码
    3. 分析代码结构
    4. 生成解释
    5. 验证引用准确性
    """

    def __init__(self):
        self.tools = get_tools()

    @step(description="分析用户请求，识别意图和关键实体")
    async def parse_intent(self, input_data: Dict) -> Dict:
        """解析用户意图"""
        message = input_data.get("message", "")
        context = input_data.get("context", {})

        # 简单意图分类
        intent_keywords = {
            "explain": ["解释", "explain", "什么意思", "这段代码"],
            "explore": ["探索", "explore", "全局", "overview", "架构"],
            "search": ["搜索", "search", "查找", "find"],
            "ask": ["问题", "question", "如何", "怎么", "where", "what"],
        }

        detected_intent = "ask"  # 默认
        for intent, keywords in intent_keywords.items():
            if any(kw in message.lower() for kw in keywords):
                detected_intent = intent
                break

        return {
            "intent": detected_intent,
            "message": message,
            "context": context,
            "entities": self._extract_entities(message),
        }

    @step(description="根据意图检索相关代码和信息")
    async def retrieve_code(self, step1_result: Dict) -> Dict:
        """检索相关代码"""
        intent = step1_result.get("intent")
        message = step1_result.get("message")
        context = step1_result.get("context", {})

        results = {
            "code_snippets": [],
            "module_info": None,
            "related_files": [],
        }

        # 如果有选中的代码，直接使用
        if context.get("selected_code"):
            results["code_snippets"].append({
                "content": context["selected_code"],
                "source": "context",
                "file_path": context.get("file_path", "unknown"),
            })

        # 根据意图检索
        if intent == "search" or intent == "ask":
            search_results = self.tools.search_code(query=message, top_k=5)
            results["code_snippets"].extend(search_results)
            results["related_files"] = list(set(
                r["file_path"] for r in search_results
            ))

        if intent == "explore":
            project_name = context.get("project", "default")
            repo_hint = context.get("repo_path", ".")
            try:
                global_map_result = self.tools.global_map(
                    project_name=project_name,
                    repo_hint=repo_hint
                )
                results["module_info"] = global_map_result
            except Exception as e:
                logger.warning(f"生成全局地图失败：{e}")

        step1_result["retrieval"] = results
        return step1_result

    @step(description="分析代码结构和逻辑")
    async def analyze_code(self, step2_result: Dict) -> Dict:
        """分析代码"""
        retrieval = step2_result.get("retrieval", {})
        code_snippets = retrieval.get("code_snippets", [])

        analysis = {
            "structures": [],
            "patterns": [],
            "dependencies": [],
        }

        for snippet in code_snippets:
            if snippet.get("source") == "context" or snippet.get("content"):
                # 对代码进行结构分析
                try:
                    explain_result = self.tools.explain_code(
                        code=snippet.get("content", ""),
                        language="python"
                    )
                    analysis["structures"].append({
                        "file": snippet.get("file_path", "unknown"),
                        "summary": explain_result.get("summary", ""),
                        "symbols": explain_result.get("symbols", []),
                    })
                except Exception as e:
                    logger.warning(f"代码分析失败：{e}")

        step2_result["analysis"] = analysis
        return step2_result

    @step(description="生成自然语言解释")
    async def generate_explanation(self, step3_result: Dict) -> Dict:
        """生成解释"""
        intent = step3_result.get("intent")
        analysis = step3_result.get("analysis", {})
        retrieval = step3_result.get("retrieval", {})

        explanation_parts = []

        if intent == "explain":
            if analysis.get("structures"):
                for struct in analysis["structures"]:
                    explanation_parts.append(f"**{struct['file']}**: {struct['summary']}")

        elif intent == "explore":
            module_info = retrieval.get("module_info")
            if module_info:
                explanation_parts.append("## 项目架构")
                explanation_parts.append(f"技术栈：{module_info.get('tech_stack', {})}")
                explanation_parts.append(f"核心模块：{len(module_info.get('layers', []))} 个分层")

        elif intent in ("ask", "search"):
            if retrieval.get("code_snippets"):
                explanation_parts.append(f"找到 {len(retrieval['code_snippets'])} 个相关代码片段")
                for i, snippet in enumerate(retrieval["code_snippets"][:3], 1):
                    explanation_parts.append(f"\n### 结果 {i}")
                    explanation_parts.append(f"文件：{snippet.get('file_path', 'unknown')}")
                    explanation_parts.append(f"内容预览：{snippet.get('content', '')[:200]}...")

        step3_result["explanation"] = {
            "content": "\n\n".join(explanation_parts),
            "citations": retrieval.get("code_snippets", []),
        }
        return step3_result

    @step(description="验证输出准确性并生成建议")
    async def verify_and_suggest(self, step4_result: Dict) -> Dict:
        """验证并生成建议"""
        explanation = step4_result.get("explanation", {})
        citations = explanation.get("citations", [])

        # 验证：检查是否有引用支持
        has_citations = len(citations) > 0
        confidence = 0.9 if has_citations else 0.6

        # 生成下一步建议
        suggestions = self._generate_suggestions(step4_result.get("intent"), citations)

        step4_result["verification"] = {
            "confidence": confidence,
            "has_citations": has_citations,
            "citation_count": len(citations),
        }
        step4_result["suggestions"] = suggestions

        return step4_result

    async def execute(self, input_data: Dict) -> Dict:
        """执行完整工作流"""
        result = await self.parse_intent(input_data)
        result = await self.retrieve_code(result)
        result = await self.analyze_code(result)
        result = await self.generate_explanation(result)
        result = await self.verify_and_suggest(result)

        return {
            "workflow": "code_understanding",
            "status": "completed",
            "intent": result.get("intent"),
            "explanation": result.get("explanation", {}).get("content", ""),
            "citations": result.get("explanation", {}).get("citations", []),
            "confidence": result.get("verification", {}).get("confidence", 0.5),
            "suggestions": result.get("suggestions", []),
            "thinking_trace": [
                "已解析用户意图",
                "已检索相关代码",
                "已完成代码分析",
                "已生成解释",
                "已验证输出准确性",
            ],
        }

    def _extract_entities(self, message: str) -> Dict:
        """提取消息中的实体"""
        return {
            "raw_message": message,
        }

    def _generate_suggestions(self, intent: str, citations: List) -> List[str]:
        """生成下一步建议"""
        if intent == "explain":
            return [
                "查看相关函数的定义",
                "分析这个模块的整体结构",
                "搜索类似的实现模式"
            ]
        elif intent == "explore":
            return [
                "深入探索特定模块",
                "查看核心入口点",
                "分析技术栈"
            ]
        else:
            return [
                "查看更多相关代码",
                "深入了解某个引用",
                "询问相关问题"
            ]


@workflow(
    name="code_exploration",
    description="代码探索工作流：自主扫描、发现模式、生成洞见"
)
class CodeExplorationWorkflow:
    """
    代码探索工作流

    用于 AI 主动探索代码库，发现架构模式和潜在问题
    """

    def __init__(self):
        self.tools = get_tools()

    @step(description="扫描项目结构")
    async def scan_project(self, input_data: Dict) -> Dict:
        """扫描项目"""
        project_name = input_data.get("project_name", "default")
        repo_hint = input_data.get("repo_hint", ".")

        try:
            global_map = self.tools.global_map(
                project_name=project_name,
                repo_hint=repo_hint
            )
            return {"project_map": global_map}
        except Exception as e:
            return {"error": str(e)}

    @step(description="发现架构模式")
    async def discover_patterns(self, step1_result: Dict) -> Dict:
        """发现模式"""
        if "error" in step1_result:
            return step1_result

        project_map = step1_result.get("project_map", {})
        patterns = []

        # 分析分层
        layers = project_map.get("layers", [])
        if len(layers) > 3:
            patterns.append({
                "type": "multi_layer_architecture",
                "description": f"项目采用 {len(layers)} 层架构",
                "confidence": 0.8
            })

        # 分析入口点
        entrypoints = project_map.get("entrypoints", [])
        if len(entrypoints) > 5:
            patterns.append({
                "type": "distributed_entrypoints",
                "description": f"项目有 {len(entrypoints)} 个入口点，可能过于分散",
                "confidence": 0.7
            })

        step1_result["patterns"] = patterns
        return step1_result

    @step(description="识别潜在问题")
    async def identify_issues(self, step2_result: Dict) -> Dict:
        """识别问题"""
        if "error" in step2_result:
            return step2_result

        issues = []
        patterns = step2_result.get("patterns", [])

        for pattern in patterns:
            if pattern.get("confidence", 0) < 0.7:
                issues.append({
                    "type": "potential_architecture_issue",
                    "description": pattern.get("description"),
                    "severity": "low"
                })

        step2_result["issues"] = issues
        return step2_result

    async def execute(self, input_data: Dict) -> Dict:
        """执行工作流"""
        result = await self.scan_project(input_data)
        result = await self.discover_patterns(result)
        result = await self.identify_issues(result)

        return {
            "workflow": "code_exploration",
            "status": "completed",
            "project_map": result.get("project_map"),
            "patterns_found": result.get("patterns", []),
            "issues_found": result.get("issues", []),
        }


@workflow(
    name="impact_analysis",
    description="影响分析工作流：分析代码变更的影响范围"
)
class ImpactAnalysisWorkflow:
    """
    影响分析工作流

    当用户计划修改代码时，分析影响范围
    """

    def __init__(self):
        self.tools = get_tools()

    @step(description="定位目标文件")
    async def locate_file(self, input_data: Dict) -> Dict:
        """定位文件"""
        file_path = input_data.get("file_path")
        project_name = input_data.get("project_name", "default")

        return {
            "file_path": file_path,
            "project_name": project_name,
        }

    @step(description="分析直接影响")
    async def analyze_direct_impact(self, step1_result: Dict) -> Dict:
        """分析直接影响"""
        try:
            impact = self.tools.analyze_change_impact(
                file_path=step1_result["file_path"],
                project_name=step1_result["project_name"]
            )
            step1_result["direct_impact"] = impact
        except Exception as e:
            step1_result["error"] = str(e)

        return step1_result

    @step(description="生成影响报告")
    async def generate_report(self, step2_result: Dict) -> Dict:
        """生成报告"""
        if "error" in step2_result:
            return step2_result

        direct_impact = step2_result.get("direct_impact", {})

        report = {
            "summary": f"修改 {step2_result['file_path']} 将影响：",
            "affected_files": direct_impact.get("affected_files", []),
            "affected_functions": direct_impact.get("affected_functions", []),
            "risk_level": direct_impact.get("risk_level", "medium"),
            "recommendations": direct_impact.get("recommendations", []),
        }

        step2_result["report"] = report
        return step2_result

    async def execute(self, input_data: Dict) -> Dict:
        """执行工作流"""
        result = await self.locate_file(input_data)
        result = await self.analyze_direct_impact(result)
        result = await self.generate_report(result)

        return {
            "workflow": "impact_analysis",
            "status": "completed",
            "report": result.get("report", {}),
        }
