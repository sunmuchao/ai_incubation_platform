"""
任务导向阅读路径生成器
根据自然语言任务描述，生成最优的代码阅读顺序和检查清单
"""
from typing import Any, Dict, List, Optional, Tuple, Set
from pathlib import Path
from collections import defaultdict
import re

from ..indexer.base import CodeChunk, CodeSymbol
from ..indexer.pipeline import IndexPipeline
from ..global_map.generator import GlobalMap


class TaskGuideGenerator:
    """
    任务阅读路径生成器
    架构思路：
    1. 语义检索 + 依赖分析 + 架构分层 多维度排序
    2. 基于任务类型的自适应策略（Bug排查、功能新增、重构等）
    3. 可解释的阅读顺序，每个步骤都有明确的阅读目标
    4. 自动生成自检问题清单，确保理解到位
    """

    # 任务类型分类
    TASK_TYPES = {
        "bug_fix": {
            "keywords": ["修复", "bug", "问题", "错误", "异常", "排查", "debug", "crash", "报错"],
            "priority_patterns": ["**/controller/**", "**/service/**", "**/db/**", "**/error/**"],
            "reading_order_weights": {
                "entrypoint": 1.5,
                "error_handling": 2.0,
                "related_code": 1.3,
                "dependency": 1.0
            }
        },
        "feature_add": {
            "keywords": ["新增", "添加", "开发", "实现", "功能", "feature", "add", "implement"],
            "priority_patterns": ["**/api/**", "**/dto/**", "**/service/**", "**/repository/**"],
            "reading_order_weights": {
                "api_definition": 2.0,
                "data_structure": 1.5,
                "business_logic": 1.3,
                "dependency": 1.0
            }
        },
        "refactor": {
            "keywords": ["重构", "优化", "改造", "refactor", "optimize", "improve"],
            "priority_patterns": ["**/core/**", "**/domain/**", "**/common/**", "**/utils/**"],
            "reading_order_weights": {
                "core_module": 2.0,
                "dependency": 1.5,
                "test_code": 1.2,
                "related_code": 1.0
            }
        },
        "performance": {
            "keywords": ["性能", "优化", "慢", "卡顿", "performance", "slow", "optimize"],
            "priority_patterns": ["**/service/**", "**/db/**", "**/query/**", "**/cache/**"],
            "reading_order_weights": {
                "query_logic": 2.0,
                "data_access": 1.8,
                "loop_logic": 1.5,
                "dependency": 1.0
            }
        }
    }

    # 常见的代码风险点关键词
    RISK_KEYWORDS = [
        "TODO", "FIXME", "HACK", "WARNING", "NOTE",
        "deprecated", "legacy", "temp", "temporary",
        "race", "deadlock", "leak", "overflow",
        "security", "auth", "permission", "validate"
    ]

    def __init__(
        self,
        index_pipeline: IndexPipeline,
        global_map: GlobalMap,
        config: Optional[Dict[str, Any]] = None
    ):
        self.index_pipeline = index_pipeline
        self.global_map = global_map
        self.config = config or {}
        self.max_reading_steps = self.config.get('max_reading_steps', 10)
        self.min_similarity_threshold = self.config.get('min_similarity_threshold', 0.5)

    def generate_guide(
        self,
        task_description: str,
        optional_paths: Optional[List[str]] = None,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成任务阅读指南"""
        # 1. 任务类型识别
        task_type, task_keywords = self._classify_task(task_description)
        task_config = self.TASK_TYPES.get(task_type, self.TASK_TYPES["feature_add"])

        # 2. 语义检索相关代码
        related_chunks = self._search_related_code(
            task_description,
            task_keywords,
            optional_paths,
            collection_name
        )

        if not related_chunks:
            return self._generate_empty_guide(task_description, optional_paths)

        # 3. 计算阅读优先级
        scored_chunks = self._score_chunks(related_chunks, task_config, task_keywords)

        # 4. 构建阅读路径
        reading_path = self._build_reading_path(scored_chunks, task_config)

        # 4.5 顶层汇总引用（便于上层/Agent 统一展示与幻觉控制）
        citations = []
        seen = set()
        for step in reading_path:
            for ref in step.get("references", []) or []:
                key = (ref.get("chunk_id"), ref.get("file_path"), ref.get("start_line"), ref.get("end_line"))
                if key in seen:
                    continue
                seen.add(key)
                citations.append(ref)

        # 5. 生成自检问题
        questions = self._generate_questions(task_description, task_type, reading_path)

        # 6. 识别风险点
        risks = self._identify_risks(related_chunks)

        # 7. 生成预估阅读时间
        estimated_time = self._estimate_reading_time(reading_path)

        return {
            "task": task_description,
            "task_type": task_type,
            "scope": optional_paths or [],
            "estimated_reading_time_minutes": estimated_time,
            "related_files_count": len(set(chunk.file_path for chunk in related_chunks)),
            "related_chunks_count": len(related_chunks),
            "suggested_reading_order": reading_path,
            "citations": citations,
            "questions_to_clarify": questions,
            "potential_risks": risks,
            "note": "阅读路径基于语义相似度、代码依赖关系和架构分层综合排序，优先阅读核心相关文件"
        }

    def _classify_task(self, task_description: str) -> Tuple[str, List[str]]:
        """分类任务类型并提取关键词"""
        task_description_lower = task_description.lower()
        task_type = "feature_add"  # 默认类型
        max_matches = 0

        # 匹配任务类型
        for t_type, config in self.TASK_TYPES.items():
            matches = sum(1 for kw in config["keywords"] if kw.lower() in task_description_lower)
            if matches > max_matches:
                max_matches = matches
                task_type = t_type

        # 提取任务关键词（名词和动词短语）
        words = re.findall(r'\b\w+\b', task_description)
        stop_words = {'的', '了', '和', '与', '或', '是', '在', '对', '把', '被', '要', '想',
                     'the', 'a', 'an', 'and', 'or', 'to', 'for', 'of', 'in', 'on', 'at'}
        keywords = [w for w in words if w.lower() not in stop_words and len(w) > 1]

        return task_type, keywords

    def _search_related_code(
        self,
        task_description: str,
        keywords: List[str],
        optional_paths: Optional[List[str]] = None,
        collection_name: Optional[str] = None
    ) -> List[CodeChunk]:
        """搜索相关代码块"""
        def search_with_optional_paths(query: str, top_k: int) -> List[CodeChunk]:
            if optional_paths:
                # 不依赖向量库 where/filter 运算符的细节：
                # 1) 先扩大检索范围取候选；
                # 2) 再在本地按 file_path 做 optional_paths 后处理筛选（OR 语义）。
                # 这样能保证 P0 最小可用且避免 filter 规则不兼容导致空结果。
                candidate_k = max(top_k * 5, top_k)
                chunks = self.index_pipeline.search_code(
                    query,
                    collection_name=collection_name,
                    top_k=candidate_k,
                    filters=None,
                )
                path_tokens = [str(p) for p in optional_paths if p]
                filtered = [
                    c for c in chunks
                    if any(tok in (c.file_path or "") for tok in path_tokens)
                ]

                merged: Dict[str, CodeChunk] = {}
                for c in filtered:
                    existing = merged.get(c.chunk_id)
                    if existing is None:
                        merged[c.chunk_id] = c
                    else:
                        ex_sim = existing.metadata.get("similarity", 0.0) if existing.metadata else 0.0
                        new_sim = c.metadata.get("similarity", 0.0) if c.metadata else 0.0
                        if new_sim > ex_sim:
                            existing.metadata["similarity"] = new_sim

                # 按最大相似度排序截断
                result = list(merged.values())
                result.sort(key=lambda x: x.metadata.get("similarity", 0.0) if x.metadata else 0.0, reverse=True)
                return result[:top_k]

            # 无 optional_paths：直接搜索
            return self.index_pipeline.search_code(
                query,
                collection_name=collection_name,
                top_k=top_k,
                filters=None,
            )

        # 语义搜索
        semantic_chunks = search_with_optional_paths(task_description, top_k=20)

        # 关键词精确匹配作为补充
        keyword_chunks = []
        if keywords:
            keyword_query = " ".join(keywords)
            keyword_chunks = search_with_optional_paths(keyword_query, top_k=10)

        # 合并结果，去重
        all_chunks = {}
        for chunk in semantic_chunks + keyword_chunks:
            if chunk.chunk_id not in all_chunks:
                all_chunks[chunk.chunk_id] = chunk
            else:
                # 合并相似度，取最大值
                existing = all_chunks[chunk.chunk_id]
                existing_similarity = existing.metadata.get('similarity', 0)
                new_similarity = chunk.metadata.get('similarity', 0)
                existing.metadata['similarity'] = max(existing_similarity, new_similarity)

        # 过滤掉相似度太低的
        filtered_chunks = [
            chunk for chunk in all_chunks.values()
            if chunk.metadata.get('similarity', 0) >= self.min_similarity_threshold
        ]

        # 按相似度排序
        filtered_chunks.sort(key=lambda x: x.metadata.get('similarity', 0), reverse=True)

        return filtered_chunks

    def _score_chunks(
        self,
        chunks: List[CodeChunk],
        task_config: Dict[str, Any],
        keywords: List[str]
    ) -> List[Tuple[CodeChunk, float]]:
        """计算代码块的阅读优先级分数"""
        scored = []
        weights = task_config.get("reading_order_weights", {})

        for chunk in chunks:
            base_score = chunk.metadata.get('similarity', 0.5)
            final_score = base_score

            # 1. 关键词匹配加分
            keyword_matches = sum(1 for kw in keywords if kw.lower() in chunk.content.lower())
            final_score *= (1 + keyword_matches * 0.2)

            # 2. 路径模式匹配加分
            for pattern in task_config.get("priority_patterns", []):
                pattern_parts = pattern.strip("*").split("/")
                if all(part in chunk.file_path for part in pattern_parts if part != "**"):
                    final_score *= 1.3
                    break

            # 3. 符号包含加分（包含公开类/函数）
            if chunk.symbols:
                public_symbols = [s for s in chunk.symbols if not s.startswith('_')]
                final_score *= (1 + len(public_symbols) * 0.15)

            # 4. 入口文件加分
            is_entry = any(entry["path"] in chunk.file_path for entry in self.global_map.entrypoints)
            if is_entry:
                final_score *= weights.get("entrypoint", 1.5)

            # 5. 风险点加分（如果是bug修复任务）
            if task_config == self.TASK_TYPES["bug_fix"]:
                has_risk = any(risk_kw in chunk.content for risk_kw in self.RISK_KEYWORDS)
                if has_risk:
                    final_score *= 1.4

            # 6. 依赖权重加分：被更多模块依赖的核心文件优先
            if hasattr(self.global_map, 'dependencies'):
                dependencies = self.global_map.dependencies
                reverse_deps = dependencies.get("reverse_dependencies", {})
                dependency_heatmap = dependencies.get("dependency_heatmap", {})

                # 转换文件路径为模块名
                module_path = Path(chunk.file_path).with_suffix('').as_posix().replace('/', '.')
                # 尝试不同的模块名匹配方式
                module_name = Path(chunk.file_path).stem

                # 检查反向依赖（被哪些模块引用）
                for mod in reverse_deps:
                    if module_name in mod or mod in module_path:
                        ref_count = len(reverse_deps[mod])
                        final_score *= (1 + min(ref_count * 0.1, 0.5))  # 最多加50%
                        break

                # 检查依赖热度
                for mod in dependency_heatmap:
                    if module_name in mod or mod in module_path:
                        heat_score = min(dependency_heatmap[mod] / 10, 1.0)
                        final_score *= (1 + heat_score * 0.3)
                        break

            scored.append((chunk, final_score))

        # 按分数降序排序
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _build_reading_path(
        self,
        scored_chunks: List[Tuple[CodeChunk, float]],
        task_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """构建结构化的阅读路径，考虑依赖关系：先读被依赖的核心模块"""
        reading_path = []
        added_files = set()
        added_symbols = set()

        # 获取依赖关系图
        module_deps = {}
        if hasattr(self.global_map, 'dependencies'):
            module_deps = self.global_map.dependencies.get("module_dependencies", {})

        def module_key_from_file(file_path: str) -> str:
            """将绝对文件路径转换为与 global-map 相同风格的模块 key（形如 core.task_guide.guide_generator）。"""
            try:
                posix = Path(file_path).as_posix()
                if "/src/" in posix:
                    after = posix.split("/src/", 1)[1]
                    return str(Path(after).with_suffix('').as_posix()).replace('/', '.')
            except Exception:
                pass
            # 兜底：退回 stem（可能用于较老依赖图）
            return Path(file_path).stem

        # 首先按分数排序，然后调整依赖顺序
        prioritized_chunks = []
        processed_files = set()

        def add_with_dependencies(chunk: CodeChunk, score: float, depth: int = 0):
            """递归添加依赖模块"""
            if depth > 3 or chunk.file_path in processed_files:
                return

            # 先添加依赖的模块
            module_key = module_key_from_file(chunk.file_path)
            deps = module_deps.get(module_key) or module_deps.get(Path(chunk.file_path).stem, [])
            for dep_module in deps:
                # 查找依赖模块对应的代码块
                for c, s in scored_chunks:
                    c_module_key = module_key_from_file(c.file_path)
                    if dep_module == c_module_key and c.file_path not in processed_files:
                        add_with_dependencies(c, s, depth + 1)
                        break

            processed_files.add(chunk.file_path)
            prioritized_chunks.append((chunk, score))

        # 按优先级处理每个chunk
        for chunk, score in scored_chunks:
            if chunk.file_path not in processed_files:
                add_with_dependencies(chunk, score)

        # 构建最终的阅读路径
        for chunk, score in prioritized_chunks:
            # 避免重复推荐同一个文件
            if chunk.file_path in added_files and len(added_files) > 3:
                continue

            # 提取模块信息
            module_path = Path(chunk.file_path).parent.name
            file_name = Path(chunk.file_path).name

            # 生成阅读目标
            goal = self._generate_reading_goal(chunk, task_config)

            # 生成阅读要点
            key_points = self._extract_key_points(chunk)

            reference = self._chunk_to_reference(chunk)
            layer_name = self._infer_layer_for_file(chunk.file_path)

            # 标记是否是依赖模块
            is_dependency = chunk.file_path not in [c.file_path for c, _ in scored_chunks[:5]]

            step = {
                "order": len(reading_path) + 1,
                "file_path": chunk.file_path,
                "file_name": file_name,
                "module": module_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "relevance_score": round(score, 2),
                "layer": layer_name,
                "reading_goal": goal,
                "key_points": key_points,
                "symbols": chunk.symbols,
                "chunk_type": chunk.chunk_type,
                "is_dependency": is_dependency
                ,
                "references": [reference]
            }

            reading_path.append(step)
            added_files.add(chunk.file_path)
            added_symbols.update(chunk.symbols)

            if len(reading_path) >= self.max_reading_steps:
                break

        return reading_path

    def _chunk_to_reference(self, chunk: CodeChunk) -> Dict[str, Any]:
        """将 chunk 转为可稳定展示/溯源的引用结构（小摘录避免过长）。"""
        similarity = chunk.metadata.get("similarity", 0.0) if chunk.metadata else 0.0
        # 摘录限制：只取前若干行，减少响应体
        lines = (chunk.content or "").splitlines()
        snippet = "\n".join(lines[:18]).strip()
        if len(snippet) > 900:
            snippet = snippet[:900] + "…"
        return {
            "chunk_id": chunk.chunk_id,
            "file_path": chunk.file_path,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "similarity": round(similarity, 4),
            "snippet": snippet,
        }

    def _infer_layer_for_file(self, file_path: str) -> Optional[str]:
        """根据 global-map.layers 的目录路径推断该文件属于哪个架构层。"""
        if not file_path or not getattr(self.global_map, "layers", None):
            return None

        repo_root_name = None
        try:
            if getattr(self.global_map, "module_tree", None):
                repo_root_name = getattr(self.global_map.module_tree, "name", None)
        except Exception:
            repo_root_name = None

        for layer in self.global_map.layers:
            for layer_path in getattr(layer, "paths", []) or []:
                # layer_path 形如 "ai-code-understanding/src/services"
                tokens = [t for t in str(layer_path).split("/") if t and t != repo_root_name]
                if tokens and all(tok in file_path for tok in tokens):
                    return layer.name
        # 兜底：如果该文件是全局地图识别到的入口文件，优先标注到“接入层”。
        if getattr(self.global_map, "entrypoints", None):
            for entry in self.global_map.entrypoints:
                entry_rel_path = entry.get("path") if isinstance(entry, dict) else None
                if entry_rel_path and entry_rel_path in file_path:
                    for preferred in ["接入层", "entrypoint", "入口层"]:
                        for layer in self.global_map.layers:
                            if getattr(layer, "name", None) == preferred:
                                return layer.name
                    # 退一步：取第一层
                    if self.global_map.layers:
                        return self.global_map.layers[0].name

        return None

    def _generate_reading_goal(self, chunk: CodeChunk, task_config: Dict[str, Any]) -> str:
        """生成阅读目标说明"""
        if chunk.symbols:
            symbols_str = "、".join(chunk.symbols[:3])
            if len(chunk.symbols) > 3:
                symbols_str += f"等{len(chunk.symbols)}个符号"
            return f"理解{symbols_str}的实现逻辑与依赖关系"
        elif chunk.chunk_type == "comment":
            return "理解该模块的设计思路与注意事项"
        else:
            return "了解该代码段的功能与执行流程"

    def _extract_key_points(self, chunk: CodeChunk) -> List[str]:
        """提取代码中的关键要点"""
        points = []
        lines = chunk.content.split('\n')

        # 提取注释
        comments = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('#', '//', '/*', '*')):
                comment = stripped.lstrip('#/*/ ').strip()
                if comment and len(comment) > 5:
                    comments.append(comment)
                    if len(comments) >= 3:
                        break

        if comments:
            points.extend(comments)

        # 提取函数签名
        if chunk.symbols:
            for symbol in chunk.symbols:
                # 在内容中查找符号定义行
                for line in lines:
                    if symbol in line and any(kw in line for kw in ['def ', 'function ', 'class ', 'interface ']):
                        points.append(f"定义：{line.strip()}")
                        break

        # 检查是否有关键词
        for risk_kw in self.RISK_KEYWORDS:
            if risk_kw in chunk.content:
                points.append(f"注意：包含{risk_kw}标记，需重点关注")

        return points[:5]  # 最多5个要点

    def _generate_questions(
        self,
        task_description: str,
        task_type: str,
        reading_path: List[Dict[str, Any]]
    ) -> List[str]:
        """生成自检问题清单"""
        questions = []

        # 通用问题
        questions.append("该任务是否跨多个服务或仅本仓库？")
        questions.append("是否有 feature flag / 配置开关影响行为？")
        questions.append("失败路径与幂等性要求是什么？")

        # 按任务类型的特定问题
        if task_type == "bug_fix":
            questions.append("错误的触发条件和输入参数是什么？")
            questions.append("是否有相关的错误日志或堆栈信息？")
            questions.append("该逻辑最近是否有修改记录？")
            questions.append("是否有对应的单元测试覆盖？")
        elif task_type == "feature_add":
            questions.append("新功能的输入输出要求是什么？")
            questions.append("是否需要新增数据库字段或接口？")
            questions.append("如何兼容现有功能和数据？")
            questions.append("需要新增哪些测试用例？")
        elif task_type == "refactor":
            questions.append("重构的目标和范围是什么？")
            questions.append("是否有完整的测试保障重构正确性？")
            questions.append("对外接口是否会发生变化？")
            questions.append("性能是否会受到影响？")
        elif task_type == "performance":
            questions.append("当前的性能瓶颈在哪里？")
            questions.append("性能指标要求是多少？")
            questions.append("是否有可复用的优化方案？")
            questions.append("优化后是否会影响业务逻辑正确性？")

        # 基于相关文件的问题
        related_files = [step["file_name"] for step in reading_path[:3]]
        if related_files:
            questions.append(f"是否理解{', '.join(related_files)}的核心逻辑？")

        return questions[:8]  # 最多8个问题

    def _identify_risks(self, chunks: List[CodeChunk]) -> List[Dict[str, Any]]:
        """识别潜在风险点"""
        risks = []

        for chunk in chunks:
            for risk_kw in self.RISK_KEYWORDS:
                if risk_kw in chunk.content:
                    # 查找风险点所在行
                    lines = chunk.content.split('\n')
                    for i, line in enumerate(lines):
                        if risk_kw in line:
                            risks.append({
                                "type": risk_kw,
                                "file_path": chunk.file_path,
                                "line": chunk.start_line + i,
                                "content": line.strip()
                            })
                            break

        # 去重
        unique_risks = []
        seen = set()
        for risk in risks:
            key = (risk["file_path"], risk["line"])
            if key not in seen:
                seen.add(key)
                unique_risks.append(risk)

        return unique_risks[:10]  # 最多10个风险点

    def _estimate_reading_time(self, reading_path: List[Dict[str, Any]]) -> int:
        """预估阅读时间（分钟）"""
        total_lines = 0
        for step in reading_path:
            total_lines += step["end_line"] - step["start_line"] + 1

        # 按每分钟阅读50行代码估算
        estimated = max(1, round(total_lines / 50))
        return estimated

    def _generate_empty_guide(self, task_description: str, optional_paths: Optional[List[str]]) -> Dict[str, Any]:
        """生成空的引导信息"""
        return {
            "task": task_description,
            "scope": optional_paths or [],
            "suggested_reading_order": [
                "（建议）先阅读项目 README 了解整体架构",
                "（建议）查找相关的 API 定义与入口文件",
                "（建议）从业务相关的服务层代码开始阅读"
            ],
            "citations": [],
            "questions_to_clarify": [
                "是否已正确索引目标代码库？",
                "任务描述是否足够具体？可以尝试补充更多细节",
                "是否需要限定检索的目录范围？"
            ],
            "note": "未找到足够相关的代码，请确保代码库已正确索引且任务描述清晰"
        }
