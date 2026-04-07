"""
输出格式化工具 - 将 API 响应转换为美观的 Markdown 格式
包含置信度可视化和引用溯源
"""
from typing import Any, Dict, List, Optional
from datetime import datetime


class OutputFormatter:
    """输出格式化器，支持多种格式输出"""

    @staticmethod
    def format_confidence_bar(confidence: float, width: int = 20) -> str:
        """
        生成置信度进度条

        Args:
            confidence: 置信度分数 (0-1)
            width: 进度条宽度

        Returns:
            进度条字符串
        """
        filled_width = int(confidence * width)
        empty_width = width - filled_width

        # 根据置信度选择颜色标记
        if confidence >= 0.8:
            indicator = "█"
            status = "高可信"
        elif confidence >= 0.6:
            indicator = "▓"
            status = "中可信"
        elif confidence >= 0.4:
            indicator = "░"
            status = "低可信"
        else:
            indicator = "░"
            status = "需核验"

        bar = indicator * filled_width + "░" * empty_width
        return f"[{bar}] {confidence:.0%} ({status})"

    @staticmethod
    def format_citations(citations: List[Dict[str, Any]], max_citations: int = 10) -> str:
        """
        格式化引用溯源

        Args:
            citations: 引用列表
            max_citations: 最大显示数量

        Returns:
            Markdown 格式的引用列表
        """
        if not citations:
            return "*暂无引用*"

        lines = []
        for i, cit in enumerate(citations[:max_citations], 1):
            file_path = cit.get('file_path', 'unknown')
            start_line = cit.get('start_line', 0)
            end_line = cit.get('end_line', 0)
            similarity = cit.get('similarity', 0)
            content = cit.get('content', '')

            # 创建文件链接（VSCode 格式）
            vsCode_link = f"vscode://file/{file_path}:{start_line}"

            # 格式化引用条目
            lines.append(f"### {i}. {file_path}:{start_line}-{end_line}")
            lines.append(f"   - 相似度：{similarity:.2%}")
            lines.append(f"   - [在 VSCode 中打开]({vsCode_link})")
            if content:
                preview = content[:200].replace('\n', ' ')
                if len(content) > 200:
                    preview += "..."
                lines.append(f"   - 内容预览：`{preview}`")
            lines.append("")

        if len(citations) > max_citations:
            lines.append(f"*... 还有 {len(citations) - max_citations} 条引用*")

        return "\n".join(lines)

    @staticmethod
    def format_validation_result(validation: Dict[str, Any]) -> str:
        """
        格式化幻觉校验结果

        Args:
            validation: 校验结果字典

        Returns:
            Markdown 格式的校验结果
        """
        if not validation:
            return ""

        lines = ["\n---\n", "### 🔍 幻觉校验结果\n"]

        # 置信度
        confidence = validation.get('confidence', 0)
        lines.append(f"**置信度**: {OutputFormatter.format_confidence_bar(confidence)}\n")

        # 有效性
        is_valid = validation.get('is_valid', True)
        status_icon = "✅" if is_valid else "⚠️"
        lines.append(f"**状态**: {status_icon} {'验证通过' if is_valid else '需要关注'}\n")

        # 错误列表
        errors = validation.get('errors', [])
        if errors:
            lines.append("\n**检测到的问题**:")
            for err in errors:
                lines.append(f"- ❌ {err}")

        # 警告列表
        warnings = validation.get('warnings', [])
        if warnings:
            lines.append("\n**注意事项**:")
            for warn in warnings:
                lines.append(f"- ⚠️ {warn}")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def format_explain_response(response: Dict[str, Any]) -> str:
        """
        格式化代码解释响应

        Args:
            response: explain API 的响应

        Returns:
            Markdown 格式的解释结果
        """
        lines = ["# 📝 代码解释\n"]

        # 语言信息
        language = response.get('language', 'unknown')
        lines.append(f"**语言**: {language}\n")

        # 代码预览
        code_preview = response.get('code_preview', '')
        if code_preview:
            lines.append("## 代码预览\n")
            lines.append(f"```{language}\n{code_preview}\n```\n")

        # 符号信息
        symbols = response.get('symbols', [])
        if symbols:
            lines.append("## 包含符号\n")
            for sym in symbols:
                lines.append(f"- `{sym}`")
            lines.append("")

        # 主要解释内容
        summary = response.get('summary', '')
        if summary:
            lines.append("## 解释说明\n")
            lines.append(summary)
            lines.append("")

        # 幻觉校验结果
        validation = response.get('validation', {})
        if validation:
            lines.append(OutputFormatter.format_validation_result(validation))

        # 引用溯源
        if validation and 'citations' in validation:
            lines.append("\n## 📚 引用溯源\n")
            lines.append(OutputFormatter.format_citations(validation['citations']))

        # 提示信息
        hints = response.get('hints', [])
        if hints:
            lines.append("\n---\n")
            lines.append("💡 **提示信息**:")
            for hint in hints:
                lines.append(f"- {hint}")

        return "\n".join(lines)

    @staticmethod
    def format_summarize_response(response: Dict[str, Any]) -> str:
        """
        格式化模块摘要响应

        Args:
            response: summarize API 的响应

        Returns:
            Markdown 格式的摘要结果
        """
        lines = ["# 📦 模块摘要\n"]

        # 模块名称
        module = response.get('module', 'unknown')
        lines.append(f"**模块**: `{module}`\n")

        # 模块职责
        role = response.get('role', '')
        if role:
            lines.append("## 模块职责\n")
            lines.append(role)
            lines.append("")

        # 公共 API
        public_api = response.get('public_api', [])
        if public_api:
            lines.append("## 对外接口\n")
            for api in public_api:
                lines.append(f"- `{api}`")
            lines.append("")

        # 依赖关系
        dependencies = response.get('dependencies', '')
        if dependencies:
            lines.append("## 依赖关系\n")
            lines.append(dependencies)
            lines.append("")

        # 幻觉校验
        validation = response.get('validation', {})
        if validation:
            lines.append(OutputFormatter.format_validation_result(validation))

        # 引用溯源
        if validation and 'citations' in validation:
            lines.append("\n## 📚 引用溯源\n")
            lines.append(OutputFormatter.format_citations(validation['citations']))

        return "\n".join(lines)

    @staticmethod
    def format_ask_response(response: Dict[str, Any]) -> str:
        """
        格式化代码库问答响应

        Args:
            response: ask API 的响应

        Returns:
            Markdown 格式的问答结果
        """
        lines = ["# ❓ 代码库问答\n"]

        # 问题
        question = response.get('question', '')
        lines.append(f"**问题**: {question}\n")

        # 答案
        answer = response.get('answer', '')
        if answer:
            lines.append("\n## 回答\n")
            lines.append(answer)

        # 引用来源
        citations = response.get('citations', [])
        if citations:
            lines.append("\n---\n")
            lines.append("## 📚 引用来源\n")
            lines.append(OutputFormatter.format_citations(citations))

        # 相关信息量
        chunk_count = response.get('related_chunks_count', 0)
        lines.append(f"\n*共检索到 {chunk_count} 个相关代码片段*")

        return "\n".join(lines)

    @staticmethod
    def format_task_guide_response(response: Dict[str, Any]) -> str:
        """
        格式化任务引导响应

        Args:
            response: task-guide API 的响应

        Returns:
            Markdown 格式的任务引导结果
        """
        lines = ["# 🗺️ 任务引导路径\n"]

        # 任务描述
        task = response.get('task', '')
        lines.append(f"**任务**: {task}\n")

        # 任务类型
        task_type = response.get('task_type', 'unknown')
        lines.append(f"**类型**: {task_type}\n")

        # 阅读顺序
        reading_order = response.get('suggested_reading_order', [])
        if reading_order:
            lines.append("\n## 📖 建议阅读顺序\n")
            for i, item in enumerate(reading_order, 1):
                if isinstance(item, dict):
                    path = item.get('file_path', item.get('path', 'unknown'))
                    relevance = item.get('relevance', 0)
                    reason = item.get('reason', '')
                    lines.append(f"### {i}. `{path}`")
                    lines.append(f"   - 相关度：{OutputFormatter.format_confidence_bar(relevance, width=10)}")
                    if reason:
                        lines.append(f"   - 原因：{reason}")
                else:
                    lines.append(f"### {i}. {item}")
            lines.append("")

        # 自检问题
        questions = response.get('questions_to_clarify', [])
        if questions:
            lines.append("\n## ❓ 需要明确的问题\n")
            for q in questions:
                lines.append(f"- {q}")

        # 引用来源
        citations = response.get('citations', [])
        if citations:
            lines.append("\n---\n")
            lines.append("## 📚 参考来源\n")
            lines.append(OutputFormatter.format_citations(citations))

        return "\n".join(lines)

    @staticmethod
    def format_global_map_response(response: Dict[str, Any]) -> str:
        """
        格式化全局地图响应

        Args:
            response: global-map API 的响应

        Returns:
            Markdown 格式的全局地图结果
        """
        lines = ["# 🗺️ 项目全局地图\n"]

        # 项目信息
        project = response.get('project', 'unknown')
        lines.append(f"**项目**: {project}\n")

        # 技术栈
        stack = response.get('stack', {})
        if stack:
            lines.append("\n## 技术栈\n")
            languages = stack.get('languages', [])
            if languages:
                lines.append(f"**语言**: {', '.join(languages)}")
            frameworks = stack.get('frameworks', [])
            if frameworks:
                lines.append(f"**框架**: {', '.join(frameworks)}")

        # 架构分层
        layers = response.get('layers', [])
        if layers:
            lines.append("\n## 架构分层\n")
            for layer in layers:
                layer_name = layer.get('name', 'unknown')
                layer_files = layer.get('files', [])
                lines.append(f"### {layer_name}")
                if layer_files:
                    for f in layer_files[:5]:
                        lines.append(f"- `{f}`")
                    if len(layer_files) > 5:
                        lines.append(f"- ... 共 {len(layer_files)} 个文件")

        # 入口点
        entrypoints = response.get('entrypoints', [])
        if entrypoints:
            lines.append("\n## 🚀 入口点\n")
            for ep in entrypoints:
                path = ep.get('path', 'unknown')
                ep_type = ep.get('type', 'file')
                lines.append(f"- `{path}` ({ep_type})")

        # 依赖关系图（如果有）
        if 'dependency_graph' in response:
            lines.append("\n## 🔗 依赖关系\n")
            lines.append("依赖关系图已生成，请使用 Web UI 查看可视化")

        return "\n".join(lines)

    @classmethod
    def format_response(cls, response: Dict[str, Any], endpoint: str = "") -> str:
        """
        根据端点类型自动选择合适的格式化方法

        Args:
            response: API 响应
            endpoint: API 端点名称

        Returns:
            Markdown 格式的响应
        """
        if 'summary' in response and 'language' in response:
            return cls.format_explain_response(response)
        elif 'role' in response or 'module' in response:
            return cls.format_summarize_response(response)
        elif 'answer' in response and 'question' in response:
            return cls.format_ask_response(response)
        elif 'suggested_reading_order' in response or 'task' in response:
            return cls.format_task_guide_response(response)
        elif 'layers' in response or 'entrypoints' in response:
            return cls.format_global_map_response(response)
        else:
            # 通用格式化
            return cls._format_generic(response)

    @staticmethod
    def _format_generic(response: Dict[str, Any]) -> str:
        """通用格式化方法"""
        lines = ["# API 响应\n"]
        for key, value in response.items():
            if isinstance(value, (dict, list)):
                lines.append(f"## {key}\n")
                lines.append(f"```json\n{value}\n```\n")
            else:
                lines.append(f"**{key}**: {value}\n")
        return "\n".join(lines)

    @staticmethod
    def add_timestamp(content: str) -> str:
        """添加时间戳到内容末尾"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{content}\n\n---\n*生成时间：{timestamp}*"


class Visualizer:
    """可视化工具类"""

    @staticmethod
    def generate_confidence_chart(confidence_data: List[Dict[str, Any]], title: str = "置信度分布") -> str:
        """
        生成置信度分布 ASCII 图表

        Args:
            confidence_data: 包含置信度数据的列表
            title: 图表标题

        Returns:
            ASCII 图表字符串
        """
        # 分桶统计
        buckets = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0
        }

        for item in confidence_data:
            conf = item.get('confidence', 0)
            if conf < 0.2:
                buckets["0.0-0.2"] += 1
            elif conf < 0.4:
                buckets["0.2-0.4"] += 1
            elif conf < 0.6:
                buckets["0.4-0.6"] += 1
            elif conf < 0.8:
                buckets["0.6-0.8"] += 1
            else:
                buckets["0.8-1.0"] += 1

        # 生成图表
        lines = [f"📊 {title}\n"]
        max_count = max(buckets.values()) if buckets.values() else 1
        bar_width = 40

        for bucket, count in buckets.items():
            bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
            bar = "█" * bar_len + "░" * (bar_width - bar_len)
            lines.append(f"  {bucket}: [{bar}] {count}")

        return "\n".join(lines)

    @staticmethod
    def generate_dependency_graph_text(graph_data: Dict[str, Any]) -> str:
        """
        生成依赖关系文本视图

        Args:
            graph_data: 依赖图数据

        Returns:
            文本格式依赖关系
        """
        lines = ["🔗 依赖关系图\n"]

        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])

        # 按入度排序节点（入度高的在前）
        node_info = {}
        for node in nodes:
            node_id = node.get('id', 'unknown')
            node_info[node_id] = {
                'name': node.get('name', node_id),
                'in_degree': 0,
                'out_degree': 0
            }

        for edge in edges:
            source = edge.get('source', '')
            target = edge.get('target', '')
            if target in node_info:
                node_info[target]['in_degree'] += 1
            if source in node_info:
                node_info[source]['out_degree'] += 1

        # 输出核心模块（高入度）
        core_modules = sorted(
            [(k, v) for k, v in node_info.items() if v['in_degree'] > 0],
            key=lambda x: x[1]['in_degree'],
            reverse=True
        )

        if core_modules:
            lines.append("\n## 核心模块（高入度）\n")
            for node_id, info in core_modules[:10]:
                lines.append(f"### {info['name']}")
                lines.append(f"   - 入度：{info['in_degree']} (被依赖次数)")
                lines.append(f"   - 出度：{info['out_degree']} (依赖其他模块数)")

        # 输出入口模块（高出度，低入度）
        entry_modules = sorted(
            [(k, v) for k, v in node_info.items() if v['out_degree'] > 0 and v['in_degree'] <= 1],
            key=lambda x: x[1]['out_degree'],
            reverse=True
        )

        if entry_modules:
            lines.append("\n## 🚀 潜在入口点\n")
            for node_id, info in entry_modules[:5]:
                lines.append(f"### {info['name']}")
                lines.append(f"   - 出度：{info['out_degree']}")

        # 循环依赖检测
        cycles = graph_data.get('cycles', [])
        if cycles:
            lines.append("\n## ⚠️ 检测到的循环依赖\n")
            for cycle in cycles[:5]:
                cycle_str = " -> ".join(cycle)
                lines.append(f"- {cycle_str}")

        return "\n".join(lines)
