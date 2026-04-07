"""
代码理解业务层
集成索引管线、全局地图、任务引导、幻觉控制等核心能力
"""
from typing import Any, Dict, List, Optional
import os
import logging
from pathlib import Path
import json
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# LLM客户端支持
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from core.indexer.pipeline import IndexPipeline
from core.indexer.parsers.tree_sitter_parser import TreeSitterParser
from core.indexer.embeddings.bge_embedding import BGEEmbedding
from core.indexer.embeddings.hash_embedding import HashEmbedding
from core.indexer.embeddings.resilient_embedding import ResilientEmbedding
from core.indexer.vector_stores.chroma_store import LlamaIndexVectorStore
from core.global_map.generator import GlobalMapGenerator
from core.task_guide.guide_generator import TaskGuideGenerator
from core.hallucination_control.validator import HallucinationValidator
from core.indexer.base import CodeSymbol
# P3 新增功能
from core.dependency_graph import DependencyGraphGenerator, generate_dependency_graph
from core.git_integration import GitIntegration, DiffIndexer, create_diff_indexer
from core.impact_analyzer import ChangeImpactAnalyzer, create_impact_analyzer
from core.lsp_integration import SymbolResolver, create_symbol_resolver, resolve_file_symbols
# P6 知识图谱功能
from core.knowledge_graph import KnowledgeGraph, KnowledgeGraphBuilder, KnowledgeGraphQuery
# P8 代码审查功能
from services.code_review_service import CodeReviewService


class UnderstandingService:
    def __init__(self):
        # 初始化核心组件（单例模式）
        self._index_pipeline = None
        self._global_map_generator = None
        self._task_guide_generator = None
        self._hallucination_validator = None
        self._config = {
            "vector_store": {
                "persist_directory": "./data/chroma"
            },
            "embedding": {
                "model_name": "BAAI/bge-small-code-v1.5",
                "device": "cpu"
            },
            # 索引状态持久化，用于 global-map 复用已索引文件清单（避免重复 os.walk+解析）
            "index_state_dir": "./data/index_state",
            # embedding 选择：
            # - "bge"：强制使用 BGE（可能需要模型下载）
            # - "hash"：离线兜底（不下载模型）
            # - "auto"：BGE 失败自动降级到 hash（本地最小可用版本）
            "embedding_mode": os.getenv("AI_CODE_UNDERSTANDING_EMBEDDING_MODE", "auto").strip().lower(),
            "hash_embedding": {
                "normalize_embeddings": True
            }
        }

        # 缓存已生成的全局地图
        self._global_maps = {}
        # 缓存项目索引状态
        self._indexed_projects = set()
        # P3 新增：缓存依赖关系图
        self._dependency_graphs = {}
        # P3 新增：Git 集成和符号解析器
        self._git_integrations = {}
        self._symbol_resolvers = {}
        self._impact_analyzers = {}
        # P6 知识图谱：缓存知识图谱
        self._knowledge_graphs = {}
        # P8 代码审查：缓存审查服务
        self._code_review_service = None

        # LLM配置
        self.llm_config = self._config.get('llm', {
            "enabled": False,
            "api_key": None,
            "base_url": None,
            "model": "gpt-3.5-turbo"
        })
        self.llm_client = None
        if self.llm_config.get('enabled') and OPENAI_AVAILABLE:
            try:
                self.llm_client = OpenAI(
                    api_key=self.llm_config.get('api_key'),
                    base_url=self.llm_config.get('base_url')
                )
            except Exception as e:
                print(f"LLM客户端初始化失败: {str(e)}")
                self.llm_config['enabled'] = False

        logger.info("UnderstandingService initialized")

    @staticmethod
    def _validate_path_safety(path: str, base_dir: Optional[str] = None) -> bool:
        """Validate path safety to prevent directory traversal attacks"""
        try:
            resolved_path = Path(path).resolve()
            path_str = str(resolved_path)

            # 始终检查路径是否在允许的范围内
            if base_dir:
                base_resolved = Path(base_dir).resolve()
                if not path_str.startswith(str(base_resolved)):
                    logger.warning(f"Path outside base_dir: {path}")
                    return False
            else:
                work_dir = Path.cwd().resolve()
                if not path_str.startswith(str(work_dir)):
                    logger.warning(f"Path outside work_dir: {path}")
                    return False

            # 检查符号链接循环
            if resolved_path.is_symlink():
                try:
                    resolved_path.resolve(strict=True)
                except (RuntimeError, OSError):
                    logger.warning(f"Symlink loop detected: {path}")
                    return False

            return True
        except Exception as e:
            logger.error(f"Path validation failed {path}: {str(e)}")
            return False


    @property
    def index_pipeline(self) -> IndexPipeline:
        """懒加载索引管线"""
        if self._index_pipeline is None:
            # 初始化默认组件
            parsers = [TreeSitterParser()]

            primary_embedding = BGEEmbedding(self._config.get("embedding", {}))
            embedding_mode = self._config.get("embedding_mode", "auto")

            # 为确保向量维度一致：hash_embedding 的 dimension 跟 primary 一致
            hash_embedding = HashEmbedding(
                {
                    "dimension": primary_embedding.get_dimension(),
                    **self._config.get("hash_embedding", {}),
                }
            )

            if embedding_mode == "hash":
                embedding = hash_embedding
            elif embedding_mode == "bge":
                embedding = primary_embedding
            else:
                embedding = ResilientEmbedding(primary_embedding, hash_embedding)

            vector_store = LlamaIndexVectorStore(self._config.get("vector_store", {}))

            self._index_pipeline = IndexPipeline(
                parsers=parsers,
                embedding=embedding,
                vector_store=vector_store,
                config=self._config
            )

        return self._index_pipeline

    @property
    def global_map_generator(self) -> GlobalMapGenerator:
        """懒加载全局地图生成器"""
        if self._global_map_generator is None:
            self._global_map_generator = GlobalMapGenerator()
        return self._global_map_generator

    def get_task_guide_generator(self, project_name: str) -> Optional[TaskGuideGenerator]:
        """获取指定项目的任务引导生成器"""
        if project_name not in self._global_maps:
            return None
        return TaskGuideGenerator(
            index_pipeline=self.index_pipeline,
            global_map=self._global_maps[project_name],
            # P0 最小可用版本：使用离线 embedding（hash）时相似度分布较低
            # 将阈值适当下调，避免返回空阅读路径。
            config={"min_similarity_threshold": -1.0},
        )

    @property
    def hallucination_validator(self) -> HallucinationValidator:
        """懒加载幻觉验证器"""
        if self._hallucination_validator is None:
            self._hallucination_validator = HallucinationValidator(
                index_pipeline=self.index_pipeline,
                # P0 最小可用版本：降低引用匹配阈值，让“引用溯源字段”在离线模式下也能尽量生成
                config={"min_citation_similarity": 0.35, "confidence_threshold": 0.4},
            )
        return self._hallucination_validator

    def index_project(
        self,
        project_name: str,
        repo_path: str,
        incremental: bool = True
    ) -> Dict[str, Any]:
        """索引整个项目"""
        # Path safety validation
        if not self._validate_path_safety(repo_path):
            return {"success": False, "error": f"Path safety check failed: {repo_path}"}

        logger.info(f"Starting index: project={project_name}, repo={repo_path}")
        start_time = time.time()

        if not os.path.exists(repo_path):
            return {
                "success": False,
                "error": f"仓库路径不存在: {repo_path}"
            }

        try:
            # 执行索引
            stats = self.index_pipeline.index_directory(
                dir_path=repo_path,
                collection_name=project_name,
                incremental=incremental
            )

            self._indexed_projects.add(project_name)
            elapsed = time.time() - start_time
            logger.info(f"Index completed: project={project_name}, elapsed={elapsed:.2f}s")

            # 自动生成全局地图
            self.global_map(
                project_name=project_name,
                repo_hint=repo_path,
                regenerate=True
            )

            return {
                "success": True,
                "stats": stats,
                "project_name": project_name,
                "repo_path": repo_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"索引失败: {str(e)}"
            }
    def explain(
        self, code: str, language: str, context: Optional[str]
    ) -> Dict[str, Any]:
        """对代码片段生成解释"""
        logger.debug(f"Explaining code: language={language}, code_len={len(code)}")
        preview = (code[:500] + "…") if len(code) > 500 else code

        # 1. 解析代码片段
        parser = self.index_pipeline.get_parser_for_language(language)
        if parser:
            parse_result = parser.parse_content(code, language)
            symbols = [s.name for s in parse_result.symbols]
            chunks = parse_result.chunks
        else:
            symbols = []
            chunks = []

        # 1. 生成代码解释
        summary = ""
        if self.llm_config.get('enabled') and self.llm_client:
            try:
                # 构建提示词
                prompt = f"""
                请解释以下{language}代码的功能和逻辑：

                ```{language}
                {code}
                ```

                {"额外上下文：" + context if context else ""}
                {"包含的符号：" + ', '.join(symbols) if symbols else ""}

                请按照以下结构解释：
                1. 功能概述：一句话说明这段代码的作用
                2. 核心逻辑：解释主要的执行流程和关键点
                3. 注意事项：潜在的问题、边界情况或使用建议

                回答要简洁准确，不要编造信息。
                """

                response = self.llm_client.chat.completions.create(
                    model=self.llm_config.get('model', 'gpt-3.5-turbo'),
                    messages=[
                        {"role": "system", "content": "你是一个专业的代码解释助手，擅长清晰准确地解释代码逻辑。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                summary = response.choices[0].message.content.strip()
            except Exception as e:
                summary = f"生成解释时出错: {str(e)}\n\n代码结构信息：\n"
                if symbols:
                    summary += f"包含符号：{', '.join(symbols)}\n"
                if chunks:
                    summary += f"代码分块数：{len(chunks)}块\n"
        else:
            summary = "代码解释功能需要配置LLM服务，当前返回结构信息：\n"
            if symbols:
                summary += f"包含符号：{', '.join(symbols)}\n"
            if chunks:
                summary += f"代码分块数：{len(chunks)}块\n"

        # 2. 幻觉校验和自动校正
        validation = None
        if chunks:
            validation = self.hallucination_validator.validate_explanation(
                explanation=summary,
                code_context=code,
                related_chunks=chunks
            )

            # 自动校正错误
            if validation and not validation.is_valid and validation.errors:
                summary = self.hallucination_validator.auto_correct(summary, validation.errors, chunks)
                # 重新校验校正后的内容
                validation = self.hallucination_validator.validate_explanation(
                    explanation=summary,
                    code_context=code,
                    related_chunks=chunks
                )

            # 添加引用
            if validation and validation.citations:
                summary = self.hallucination_validator.add_citations_to_content(summary, validation.citations)

        return {
            "language": language,
            "summary": summary,
            "code_preview": preview,
            "context_used": bool(context),
            "symbols": symbols,
            "chunk_count": len(chunks),
            "validation": {
                "confidence": validation.confidence if validation else 1.0,
                "is_valid": validation.is_valid if validation else True,
                "warnings": validation.warnings if validation else [],
                "errors": validation.errors if validation else [],
                "citations": validation.citations if validation else [],
                "corrected_content": validation.corrected_content if validation else None,
            } if validation else None,
            "hints": [
                "已接入 tree-sitter 解析器进行语法分析",
                "幻觉校验机制已启用，低置信度内容会自动标记",
            ],
        }

    def summarize_module(
        self,
        module_name: str,
        symbols: Optional[List[str]],
        raw_outline: Optional[str],
    ) -> Dict[str, Any]:
        """对模块生成高层摘要"""
        logger.debug(f"Summarizing module: module={module_name}, symbols_count={len(symbols) if symbols else 0}")
        role = ""
        dependencies = "依赖分析功能开发中"
        public_api = symbols or []

        if self.llm_config.get('enabled') and self.llm_client and public_api:
            try:
                # 构建提示词
                prompt = f"""
                请为以下{module_name}模块生成高层摘要：

                模块名: {module_name}
                包含的符号: {', '.join(public_api)}
                {"结构概要: " + raw_outline if raw_outline else ""}

                请按照以下结构生成摘要：
                1. 模块职责：一句话说明这个模块的核心作用
                2. 主要功能：列出3-5个核心功能点
                3. 对外接口：主要的公开API或类

                回答要简洁准确，基于提供的信息，不要编造。
                """

                response = self.llm_client.chat.completions.create(
                    model=self.llm_config.get('model', 'gpt-3.5-turbo'),
                    messages=[
                        {"role": "system", "content": "你是一个专业的架构师，擅长总结模块的职责和接口。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                role = response.choices[0].message.content.strip()
            except Exception as e:
                role = f"生成摘要时出错: {str(e)}"
        else:
            role = "模块摘要功能需要配置LLM服务，当前返回基础信息：\n"
            if public_api:
                role += f"包含符号：{', '.join(public_api)}"

        # 片段摘要稳定 API：为 role 生成置信度/引用信息（即使未接入 LLM，也会退化为“空引用”）
        related_chunks = []
        try:
            # 如果用户已经做过 index-project，则这里可以直接复用向量索引做引用溯源
            keyword_query = " ".join(public_api[:10]) if public_api else module_name
            search_query = f"{module_name}\n{keyword_query}".strip()

            # P0：summarize endpoint 没有显式 project_name 参数；这里优先使用当前已缓存的全局地图所属 collection。
            collection_name = next(iter(self._global_maps.keys()), None)
            related_chunks = self.index_pipeline.search_code(
                query=search_query,
                top_k=10,
                collection_name=collection_name,
            )
        except Exception:
            related_chunks = []

        module_symbols = [
            CodeSymbol(
                name=s,
                symbol_type="symbol",
                file_path="",
                start_line=0,
                end_line=0,
            )
            for s in public_api
        ]

        validation = None
        try:
            validation = self.hallucination_validator.validate_summarization(
                summary=role,
                module_symbols=module_symbols,
                related_chunks=related_chunks,
            )
            if validation and validation.citations:
                role = self.hallucination_validator.add_citations_to_content(
                    role, validation.citations
                )
        except Exception:
            validation = None

        return {
            "module": module_name,
            "role": role,
            "public_api": public_api,
            "outline_present": bool(raw_outline),
            "dependencies": dependencies,
            "citations": validation.citations if validation else [],
            "validation": {
                "confidence": validation.confidence if validation else 1.0,
                "is_valid": validation.is_valid if validation else True,
                "warnings": validation.warnings if validation else [],
                "errors": validation.errors if validation else [],
                "citations": validation.citations if validation else [],
                "corrected_content": validation.corrected_content if validation else None,
            } if validation else None,
            "hints": [
                "模块摘要功能已支持LLM生成，配置API_KEY后即可使用"
            ],
        }

    def ask(
        self, question: str, scope_paths: Optional[List[str]]
    ) -> Dict[str, Any]:
        """针对代码库的问答"""
        logger.info(f"Answering question: question_len={len(question)}, scope={scope_paths}")
        # 先检索相关代码
        # P0：ask 没有显式 project_name，因此优先使用当前已缓存的全局地图所属 collection，
        # 让索引/问答在同一项目上下文内闭环。
        collection_name = next(iter(self._global_maps.keys()), None)
        related_chunks = self.index_pipeline.search_code(
            query=question,
            top_k=10,
            collection_name=collection_name
        )

        # scope_paths 是“用户限定检索范围”的关键参数；P0 最小可用版本：
        # 在得到候选 chunks 后做本地 OR 过滤（避免依赖向量库过滤算子差异）。
        if scope_paths:
            path_tokens = [str(p) for p in scope_paths if p]
            if path_tokens:
                filtered = [
                    c for c in related_chunks
                    if any(tok in (c.file_path or "") for tok in path_tokens)
                ]
                # 避免过滤过严导致完全无结果：退回到原候选
                if filtered:
                    related_chunks = filtered

        citations = []
        for chunk in related_chunks:
            citations.append({
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "similarity": chunk.metadata.get('similarity', 0),
                "content": chunk.content
            })

        # 生成回答
        answer = ""
        if self.llm_config.get('enabled') and self.llm_client and related_chunks:
            try:
                # 构建上下文
                context = ""
                for i, chunk in enumerate(related_chunks[:5], 1):
                    context += f"\n=== 相关代码片段 {i} (文件: {chunk.file_path}, 相似度: {chunk.metadata.get('similarity', 0):.2f}) ===\n"
                    context += chunk.content[:1000] + "\n"

                # 构建提示词
                prompt = f"""
                请基于以下相关代码片段回答用户的问题：

                用户问题: {question}

                相关代码片段:
                {context}

                回答要求：
                1. 只基于提供的代码片段回答，不要编造信息
                2. 如果信息不足，说明无法回答并建议查看更多相关代码
                3. 回答中需要引用来源，格式为：[引用X]，X是片段编号
                4. 回答要简洁准确，重点突出
                """

                response = self.llm_client.chat.completions.create(
                    model=self.llm_config.get('model', 'gpt-3.5-turbo'),
                    messages=[
                        {"role": "system", "content": "你是一个专业的代码问答助手，基于提供的代码片段准确回答用户问题。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1500
                )
                answer = response.choices[0].message.content.strip()

                # 幻觉校验
                validation = self.hallucination_validator.validate_answer(
                    answer=answer,
                    question=question,
                    related_chunks=related_chunks
                )

                # 添加验证信息
                if not validation.is_valid:
                    answer += f"\n\n⚠️ 警告：回答置信度较低 ({validation.confidence:.2f})，请谨慎参考。"
                    if validation.errors:
                        answer += "\n检测到的问题：\n" + "\n".join([f"- {err}" for err in validation.errors])
                    if validation.warnings:
                        answer += "\n注意事项：\n" + "\n".join([f"- {warn}" for warn in validation.warnings])

                # 添加引用
                answer += "\n\n**引用来源：**\n"
                for i, cit in enumerate(citations[:5], 1):
                    answer += f"{i}. {cit['file_path']}:{cit['start_line']}-{cit['end_line']} (相似度 {cit['similarity']:.2f})\n"

            except Exception as e:
                answer = f"生成回答时出错: {str(e)}\n\n相关代码片段：\n"
                for i, chunk in enumerate(related_chunks[:3], 1):
                    answer += f"\n{i}. {chunk.file_path}:{chunk.start_line}-{chunk.end_line}\n"
                    answer += f"   相似度: {chunk.metadata.get('similarity', 0):.2f}\n"
                    answer += f"   ```{chunk.language}\n   {chunk.content[:200]}...\n   ```\n"
        else:
            answer = "代码库问答功能需要配置LLM服务，当前返回相关代码片段：\n"
            for i, chunk in enumerate(related_chunks[:3], 1):
                answer += f"\n{i}. {chunk.file_path}:{chunk.start_line}-{chunk.end_line}\n"
                answer += f"   相似度: {chunk.metadata.get('similarity', 0):.2f}\n"
                answer += f"   ```{chunk.language}\n   {chunk.content[:200]}...\n   ```\n"

        return {
            "question": question,
            "scope": scope_paths or [],
            "answer": answer,
            "citations": citations,
            "related_chunks_count": len(related_chunks),
            "hints": [
                "已接入向量检索功能，返回最相关的代码片段",
                "完整的RAG问答功能正在开发中"
            ]
        }

    def global_map(
        self,
        project_name: str,
        repo_hint: Optional[str],
        stack_hint: Optional[str] = None,
        regenerate: bool = False,
        format: str = "json"
    ) -> Any:
        """
        全局地图：缓解大仓库 + IDE AI 局部编辑带来的「黑盒感」。
        自动扫描目录结构、识别架构分层、提取入口点与技术栈。
        """
        logger.info(f"Generating global map: project={project_name}, regenerate={regenerate}")
        start_time = time.time()
        # 检查缓存 (只在 regenerate=False 且 format="json" 时使用缓存)
        if not regenerate and format.lower() == "json" and project_name in self._global_maps:
            return self.global_map_generator.to_dict(self._global_maps[project_name])

        if not repo_hint or not os.path.exists(repo_hint):
            return {
                "project": project_name,
                "repo": repo_hint,
                "stack": stack_hint,
                "error": "仓库路径不存在或未指定，请提供有效的repo_hint参数",
                "problem_solved": (
                    "在 Cursor/Claude Code 等工具里局部改代码很快，但仓库一大容易失去全局图景；"
                    "本接口用于聚合「一眼能看懂的系统地图」。"
                ),
                "integration_with_ide": [
                    "导出本结构为 Markdown，粘贴到 Cursor/Claude 作项目级上下文",
                    "对子路径建索引后，问答与「从哪读起」可接 RAG",
                ]
            }

        try:
            # P0：global-map 与索引管线最小闭环
            # - 若 project 已完成 index-project：优先复用索引状态中的“已索引文件清单”
            # - 否则退化到 os.walk + 仅解析 supported languages
            file_results = []
            parser = TreeSitterParser()

            indexed_files: List[str] = []
            try:
                state = self.index_pipeline.file_index_state.get(project_name, {})
                if isinstance(state, dict) and state:
                    indexed_files = list(state.keys())
            except Exception:
                indexed_files = []

            if indexed_files:
                for file_path in indexed_files:
                    try:
                        fp = Path(file_path)
                        if parser._detect_language(fp) in parser.supported_languages:
                            result = parser.parse_file(fp)
                            file_results.append(result)
                    except Exception:
                        continue
            else:
                for root, _, files in os.walk(repo_hint):
                    for file in files:
                        file_path = Path(root) / file
                        if parser._detect_language(file_path) in parser.supported_languages:
                            try:
                                result = parser.parse_file(file_path)
                                file_results.append(result)
                            except Exception:
                                continue

            # 生成全局地图
            global_map = self.global_map_generator.generate(
                project_name=project_name,
                repo_path=repo_hint,
                file_results=file_results,
                stack_hint=stack_hint
            )

            # 缓存结果
            self._global_maps[project_name] = global_map

            elapsed = time.time() - start_time
            logger.info(f"Global map generated: project={project_name}, elapsed={elapsed:.2f}s")
            if format.lower() == "markdown":
                return {
                    "project": project_name,
                    "repo": repo_hint,
                    "markdown": self.global_map_generator.to_markdown(global_map)
                }
            else:
                return self.global_map_generator.to_dict(global_map)

        except Exception as e:
            return {
                "project": project_name,
                "repo": repo_hint,
                "stack": stack_hint,
                "error": f"生成全局地图失败: {str(e)}",
                "problem_solved": (
                    "在 Cursor/Claude Code 等工具里局部改代码很快，但仓库一大容易失去全局图景；"
                    "本接口用于聚合「一眼能看懂的系统地图」。"
                ),
                "integration_with_ide": [
                    "导出本结构为 Markdown，粘贴到 Cursor/Claude 作项目级上下文",
                    "对子路径建索引后，问答与「从哪读起」可接 RAG",
                ]
            }

    def task_guide(
        self,
        task_description: str,
        optional_paths: Optional[List[str]],
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        给定自然语言任务，建议阅读顺序与自检问题。
        基于语义检索、依赖分析和架构分层综合排序。
        """
        logger.info(f"Generating task guide: task={task_description[:50]}..., project={project_name}")
        start_time = time.time()
        # 如果没有指定项目，返回通用引导
        if not project_name or project_name not in self._global_maps:
            return {
                "task": task_description,
                "scope": optional_paths or [],
                "suggested_reading_order": [
                    "请先调用 /api/understanding/global-map 生成项目全局地图",
                    "或通过 /api/understanding/index-project 索引项目代码",
                    "然后再调用本接口获取个性化阅读路径"
                ],
                "questions_to_clarify": [
                    "是否已索引目标项目代码？",
                    "是否能提供项目名称以便获取上下文？",
                    "任务描述是否可以更具体些？"
                ],
                "note": "需要先索引项目并生成全局地图才能使用智能引导功能"
            }

        try:
            guide_generator = self.get_task_guide_generator(project_name)
            if not guide_generator:
                return {
                    "task": task_description,
                    "error": "项目未找到或未生成全局地图"
                }

            guide = guide_generator.generate_guide(
                task_description=task_description,
                optional_paths=optional_paths,
                collection_name=project_name
            )
            elapsed = time.time() - start_time
            logger.info(f"Task guide generated: project={project_name}, elapsed={elapsed:.2f}s")
            return guide

        except Exception as e:
            return {
                "task": task_description,
                "scope": optional_paths or [],
                "error": f"生成阅读路径失败: {str(e)}",
                "suggested_reading_order": [
                    "（建议）先阅读项目 README 了解整体架构",
                    "（建议）查找相关的 API 定义与入口文件",
                    "（建议）从业务相关的服务层代码开始阅读"
                ],
                "questions_to_clarify": [
                    "该任务是否跨多个服务或仅本仓库？",
                    "是否有 feature flag / 配置开关影响行为？",
                    "失败路径与幂等性要求是什么？",
                ]
            }

    def get_diff_indexer(self, project_name: str, repo_path: str) -> DiffIndexer:
        """P3: 获取 Diff 索引器"""
        return DiffIndexer(
            index_pipeline=self.index_pipeline,
            repo_path=repo_path,
            project_name=project_name
        )

    def dependency_graph(
        self,
        project_name: str,
        repo_path: str,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """P3: 生成项目依赖关系图"""
        logger.info(f"Generating dependency graph: project={project_name}")

        if project_name in self._dependency_graphs:
            graph = self._dependency_graphs[project_name]
            if output_format == "dot":
                return {"dot": graph.to_dot()}
            return graph.to_dict()

        try:
            generator = DependencyGraphGenerator()
            file_results = []
            if project_name in self._indexed_projects:
                try:
                    state = self.index_pipeline.file_index_state.get(project_name, {})
                    if isinstance(state, dict) and state:
                        parser = TreeSitterParser()
                        for file_path in list(state.keys())[:100]:
                            try:
                                fp = Path(file_path)
                                if parser._detect_language(fp) in parser.supported_languages:
                                    result = parser.parse_file(fp)
                                    file_results.append(result)
                            except Exception:
                                continue
                except Exception:
                    pass

            graph = generator.generate(
                project_name=project_name,
                project_root=repo_path,
                file_results=file_results if file_results else None
            )
            self._dependency_graphs[project_name] = graph

            if output_format == "dot":
                return {"dot": graph.to_dot()}
            return graph.to_dict()

        except Exception as e:
            return {"error": f"生成依赖关系图失败：{str(e)}", "project_name": project_name}

    def index_git_diff(
        self,
        project_name: str,
        repo_path: str,
        base: str = "HEAD~1",
        target: str = "HEAD"
    ) -> Dict[str, Any]:
        """P3: 索引 Git 变更文件"""
        logger.info(f"Indexing git diff: project={project_name}, base={base}, target={target}")

        try:
            diff_indexer = DiffIndexer(
                index_pipeline=self.index_pipeline,
                repo_path=repo_path,
                project_name=project_name
            )
            stats = diff_indexer.index_changed_files(base=base, target=target)
            return {"success": True, "stats": stats, "project_name": project_name}
        except Exception as e:
            return {"success": False, "error": f"索引 Git 变更失败：{str(e)}"}

    def analyze_change_impact(
        self,
        project_name: str,
        repo_path: str,
        changed_files: Optional[List[Dict[str, Any]]] = None,
        base: str = "HEAD~1",
        target: str = "HEAD"
    ) -> Dict[str, Any]:
        """P3: 分析代码变更的影响"""
        logger.info(f"Analyzing change impact: project={project_name}")

        try:
            if project_name not in self._dependency_graphs:
                self.dependency_graph(project_name, repo_path)

            graph = self._dependency_graphs.get(project_name)
            if not graph:
                return {"error": "依赖图生成失败"}

            if project_name not in self._impact_analyzers:
                self._impact_analyzers[project_name] = ChangeImpactAnalyzer(
                    dependency_graph=graph,
                    index_pipeline=self.index_pipeline
                )

            analyzer = self._impact_analyzers[project_name]

            if not changed_files:
                if project_name not in self._git_integrations:
                    self._git_integrations[project_name] = GitIntegration(repo_path)
                git = self._git_integrations[project_name]
                diff_files = git.get_diff_stats(base, target)
                changed_files = [f.to_dict() for f in diff_files]

            result = analyzer.analyze_batch(changed_files)
            return {"success": True, "analysis": result, "project_name": project_name}

        except Exception as e:
            return {"success": False, "error": f"变更影响分析失败：{str(e)}"}

    def resolve_symbols(
        self,
        file_path: str,
        symbol_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """P3: 解析文件符号或查找符号定义"""
        logger.info(f"Resolving symbols: file={file_path}, symbol={symbol_name}")

        try:
            resolver = SymbolResolver()

            if symbol_name:
                definitions = resolver.find_symbol_definition(symbol_name, scope_paths=[file_path])
                if not definitions:
                    dir_path = str(Path(file_path).parent)
                    definitions = resolver.find_symbol_definition(symbol_name, scope_paths=[dir_path])

                return {
                    "symbol_name": symbol_name,
                    "file_path": file_path,
                    "definitions": [d.to_dict() for d in definitions],
                    "found": len(definitions) > 0
                }
            else:
                symbols = resolver.resolve_symbols(file_path)
                doc_symbols = resolver.get_document_symbols(file_path)
                return {
                    "file_path": file_path,
                    "symbols": [s.to_dict() for s in symbols],
                    "document_symbols": doc_symbols,
                    "total_symbols": len(symbols)
                }

        except Exception as e:
            return {"error": f"符号解析失败：{str(e)}", "file_path": file_path}

    def find_symbol_references(
        self,
        project_name: str,
        repo_path: str,
        symbol_name: str,
        scope_paths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """P3: 查找符号的所有引用位置"""
        logger.info(f"Finding symbol references: symbol={symbol_name}, project={project_name}")

        try:
            resolver = SymbolResolver()
            definitions = resolver.find_symbol_definition(symbol_name, scope_paths=[repo_path])
            if not definitions:
                return {
                    "symbol_name": symbol_name,
                    "references": [],
                    "definitions": [],
                    "found": False
                }

            search_paths = scope_paths or [repo_path]
            references = []
            for definition in definitions:
                refs = resolver.find_references(definition, scope_paths=search_paths)
                references.extend(refs)

            return {
                "symbol_name": symbol_name,
                "definitions": [d.to_dict() for d in definitions],
                "references": [r.to_dict() for r in references[:100]],
                "total_references": len(references),
                "found": True
            }

        except Exception as e:
            return {"error": f"查找引用失败：{str(e)}", "symbol_name": symbol_name}


    # ============= P6 知识图谱功能 =============

    def build_knowledge_graph(
        self,
        project_name: str,
        repo_path: str,
        save: bool = True
    ) -> Dict[str, Any]:
        """P6: 构建代码知识图谱"""
        logger.info(f"Building knowledge graph: project={project_name}")
        start_time = time.time()

        try:
            # 检查缓存
            if project_name in self._knowledge_graphs:
                graph = self._knowledge_graphs[project_name]
                return {
                    "success": True,
                    "project_name": project_name,
                    "stats": graph.get_stats().to_dict(),
                    "cached": True
                }

            # 创建构建器
            builder = KnowledgeGraphBuilder(project_name=project_name)

            # 获取已索引的文件结果（如果有）
            file_results = []
            if project_name in self._indexed_projects:
                try:
                    parser = TreeSitterParser()
                    state = self.index_pipeline.file_index_state.get(project_name, {})
                    if isinstance(state, dict) and state:
                        for file_path in list(state.keys())[:200]:  # 限制文件数量
                            try:
                                fp = Path(file_path)
                                if parser._detect_language(fp) in parser.supported_languages:
                                    result = parser.parse_file(fp)
                                    file_results.append(result)
                            except Exception:
                                continue
                except Exception:
                    pass

            # 构建图谱
            graph = builder.build(project_root=repo_path, file_results=file_results if file_results else None)

            # 保存图谱
            if save:
                save_path = f"./data/knowledge_graphs/{project_name}.json"
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                graph.save(save_path)

            # 缓存
            self._knowledge_graphs[project_name] = graph

            elapsed = time.time() - start_time
            stats = graph.get_stats()

            return {
                "success": True,
                "project_name": project_name,
                "stats": stats.to_dict(),
                "elapsed_seconds": elapsed,
                "saved_path": save_path if save else None
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"构建知识图谱失败：{str(e)}",
                "project_name": project_name
            }

    def query_knowledge_graph(
        self,
        project_name: str,
        query_type: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """P6: 查询知识图谱"""
        params = params or {}

        logger.info(f"Querying knowledge graph: project={project_name}, query_type={query_type}")

        # 获取图谱
        if project_name not in self._knowledge_graphs:
            # 尝试从文件加载
            save_path = f"./data/knowledge_graphs/{project_name}.json"
            if os.path.exists(save_path):
                try:
                    graph = KnowledgeGraph.load(save_path)
                    self._knowledge_graphs[project_name] = graph
                except Exception:
                    return {
                        "error": f"项目 {project_name} 的知识图谱不存在，请先调用 build_knowledge_graph",
                        "project_name": project_name
                    }
            else:
                return {
                    "error": f"项目 {project_name} 的知识图谱不存在，请先调用 build_knowledge_graph",
                    "project_name": project_name
                }

        graph = self._knowledge_graphs[project_name]
        query = KnowledgeGraphQuery(graph)

        try:
            if query_type == "impact_analysis":
                # 影响分析
                node_id = params.get("node_id")
                file_path = params.get("file_path")

                if file_path:
                    result = query.get_change_impact(file_path)
                elif node_id:
                    result = query.analyze_impact(node_id)
                else:
                    return {"error": "缺少 node_id 或 file_path 参数"}

            elif query_type == "call_chain":
                # 调用链分析
                node_id = params.get("node_id")
                direction = params.get("direction", "downstream")
                max_depth = params.get("max_depth", 5)

                if not node_id:
                    return {"error": "缺少 node_id 参数"}

                result = query.get_call_chain(node_id, direction=direction, max_depth=max_depth)

            elif query_type == "dependency_tree":
                # 依赖树
                node_id = params.get("node_id")
                direction = params.get("direction", "dependencies")

                if not node_id:
                    return {"error": "缺少 node_id 参数"}

                if direction == "dependencies":
                    result = query.get_dependency_tree(node_id)
                else:
                    result = query.get_reverse_dependency_tree(node_id)

            elif query_type == "search":
                # 搜索
                query_str = params.get("query", "")
                node_type = params.get("node_type")
                fuzzy = params.get("fuzzy", True)

                result = {"results": query.search(query_str, node_type=node_type, fuzzy=fuzzy)}

            elif query_type == "symbol_info":
                # 符号信息
                symbol_name = params.get("symbol_name")
                if not symbol_name:
                    return {"error": "缺少 symbol_name 参数"}

                result = query.get_symbol_info(symbol_name)

            elif query_type == "core_modules":
                # 核心模块
                top_n = params.get("top_n", 10)
                result = {"core_modules": query.find_core_modules(top_n)}

            elif query_type == "cycles":
                # 循环检测
                result = {"cycles": query.find_cycles()}

            elif query_type == "stats":
                # 图谱统计
                result = query.get_stats()

            elif query_type == "summary":
                # 图谱摘要
                result = query.get_summary()

            elif query_type == "file_overview":
                # 文件概览
                file_path = params.get("file_path")
                if not file_path:
                    return {"error": "缺少 file_path 参数"}
                result = query.get_file_overview(file_path)

            else:
                return {"error": f"未知的查询类型：{query_type}"}

            return {
                "success": True,
                "project_name": project_name,
                "query_type": query_type,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"查询失败：{str(e)}",
                "query_type": query_type
            }

    def graph_impact_analysis(
        self,
        project_name: str,
        node_id: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """P6: 基于知识图谱的影响分析"""
        logger.info(f"Graph impact analysis: project={project_name}, node_id={node_id}, file_path={file_path}")

        # 获取图谱
        if project_name not in self._knowledge_graphs:
            save_path = f"./data/knowledge_graphs/{project_name}.json"
            if os.path.exists(save_path):
                try:
                    graph = KnowledgeGraph.load(save_path)
                    self._knowledge_graphs[project_name] = graph
                except Exception:
                    return {"error": f"知识图谱不存在：{project_name}"}
            else:
                return {"error": f"知识图谱不存在：{project_name}"}

        graph = self._knowledge_graphs[project_name]
        query = KnowledgeGraphQuery(graph)

        try:
            if node_id:
                result = query.analyze_impact(node_id)
            elif file_path:
                result = query.get_change_impact(file_path)
            else:
                return {"error": "必须提供 node_id 或 file_path"}

            return {
                "success": True,
                "project_name": project_name,
                "analysis": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"影响分析失败：{str(e)}"
            }

    def knowledge_graph_viz(
        self,
        project_name: str,
        repo_path: str,
        layout: str = "force",
        max_nodes: int = 100
    ) -> Dict[str, Any]:
        """P7: 获取知识图谱可视化数据"""
        logger.info(f"Knowledge graph viz: project={project_name}, layout={layout}, max_nodes={max_nodes}")

        # 获取图谱
        if project_name not in self._knowledge_graphs:
            save_path = f"./data/knowledge_graphs/{project_name}.json"
            if os.path.exists(save_path):
                try:
                    graph = KnowledgeGraph.load(save_path)
                    self._knowledge_graphs[project_name] = graph
                except Exception:
                    return {"error": f"知识图谱不存在：{project_name}"}
            else:
                # 尝试构建图谱
                build_result = self.build_knowledge_graph(project_name, repo_path, save=True)
                if not build_result.get("success"):
                    return {"error": f"构建图谱失败：{build_result.get('error', '未知错误')}"}

        graph = self._knowledge_graphs[project_name]
        query = KnowledgeGraphQuery(graph)

        try:
            # 获取图谱数据
            graph_dict = graph.to_dict()
            nodes = graph_dict.get("nodes", [])
            edges = graph_dict.get("edges", [])

            # 限制节点数量
            if len(nodes) > max_nodes:
                # 优先保留核心节点
                core_modules = query.find_core_modules(top_n=max_nodes)
                core_ids = set(m["id"] for m in core_modules)
                nodes = [n for n in nodes if n["id"] in core_ids][:max_nodes]
                node_ids = set(n["id"] for n in nodes)
                edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

            # 计算节点样式
            for node in nodes:
                node_type = node.get("node_type", "unknown")
                # 根据节点类型设置颜色和形状
                style_config = {
                    "PROJECT": {"color": "#FF6B6B", "size": 40, "shape": "diamond"},
                    "PACKAGE": {"color": "#4ECDC4", "size": 30, "shape": "box"},
                    "MODULE": {"color": "#45B7D1", "size": 25, "shape": "ellipse"},
                    "CLASS": {"color": "#96CEB4", "size": 20, "shape": "ellipse"},
                    "FUNCTION": {"color": "#FFEAA7", "size": 15, "shape": "circle"},
                    "VARIABLE": {"color": "#DDA0DD", "size": 10, "shape": "circle"},
                    "INTERFACE": {"color": "#98D8C8", "size": 22, "shape": "box"},
                    "ENUM": {"color": "#F7DC6F", "size": 18, "shape": "circle"},
                }.get(node_type, {"color": "#CCCCCC", "size": 15, "shape": "circle"})

                node["viz_color"] = style_config["color"]
                node["viz_size"] = style_config["size"]
                node["viz_shape"] = style_config["shape"]

            # 计算节点度数（用于可视化）
            for node in nodes:
                node_id = node["id"]
                in_degree = sum(1 for e in edges if e["target"] == node_id)
                out_degree = sum(1 for e in edges if e["source"] == node_id)
                node["in_degree"] = in_degree
                node["out_degree"] = out_degree
                node["is_core"] = in_degree >= 3  # 核心节点标记

            # 设置边样式
            for edge in edges:
                edge_type = edge.get("edge_type", "unknown")
                style_config = {
                    "CONTAINS": {"color": "#CCCCCC", "width": 1, "style": "solid"},
                    "BELONGS_TO": {"color": "#CCCCCC", "width": 1, "style": "solid"},
                    "IMPORTS": {"color": "#FFA07A", "width": 2, "style": "dashed"},
                    "DEPENDS_ON": {"color": "#FFA07A", "width": 2, "style": "dashed"},
                    "CALLS": {"color": "#87CEEB", "width": 1.5, "style": "solid"},
                    "EXTENDS": {"color": "#98FB98", "width": 2, "style": "solid"},
                    "IMPLEMENTS": {"color": "#90EE90", "width": 2, "style": "solid"},
                    "REFERENCES": {"color": "#DDA0DD", "width": 1, "style": "dotted"},
                    "DEFINES": {"color": "#F0E68C", "width": 1, "style": "solid"},
                    "USED_BY": {"color": "#E6E6FA", "width": 1, "style": "dotted"},
                    "ACCESSES": {"color": "#B0C4DE", "width": 1, "style": "solid"},
                }.get(edge_type, {"color": "#999999", "width": 1, "style": "solid"})

                edge["viz_color"] = style_config["color"]
                edge["viz_width"] = style_config["width"]
                edge["viz_style"] = style_config["style"]

            # 布局提示
            layout_info = {
                "type": layout,
                "suggestions": {
                    "force": "力导向布局，适合一般展示",
                    "dag": "有向无环图布局，适合展示依赖关系",
                    "circular": "环形布局，适合展示循环依赖"
                }
            }

            return {
                "success": True,
                "project_name": project_name,
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "layout": layout_info,
                "legend": {
                    "node_types": {
                        "PROJECT": {"color": "#FF6B6B", "label": "项目"},
                        "PACKAGE": {"color": "#4ECDC4", "label": "包"},
                        "MODULE": {"color": "#45B7D1", "label": "模块"},
                        "CLASS": {"color": "#96CEB4", "label": "类"},
                        "FUNCTION": {"color": "#FFEAA7", "label": "函数"},
                        "INTERFACE": {"color": "#98D8C8", "label": "接口"},
                    },
                    "edge_types": {
                        "CALLS": {"color": "#87CEEB", "label": "调用"},
                        "IMPORTS": {"color": "#FFA07A", "label": "导入"},
                        "EXTENDS": {"color": "#98FB98", "label": "继承"},
                        "DEPENDS_ON": {"color": "#FFA07A", "label": "依赖"}
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"可视化数据生成失败：{str(e)}"
            }


    # ============= F-008 Git 变更自动同步功能 =============

    def git_sync_install(
        self,
        project_name: str,
        repo_path: str
    ) -> Dict[str, Any]:
        """F-008: 安装 Git 变更自动同步"""
        logger.info(f"安装 Git 变更同步：project={project_name}, repo={repo_path}")

        try:
            from core.git_integration import GitChangeSynchronizer

            syncer = GitChangeSynchronizer(
                repo_path=repo_path,
                project_name=project_name,
                index_pipeline=self.index_pipeline,
                knowledge_graph=self._knowledge_graphs.get(project_name)
            )

            result = syncer.install()

            # 缓存 syncer
            if not hasattr(self, '_git_syncers'):
                self._git_syncers = {}
            self._git_syncers[project_name] = syncer

            return {
                "success": True,
                "project_name": project_name,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"安装失败：{str(e)}"
            }

    def git_sync_uninstall(
        self,
        project_name: str,
        repo_path: str
    ) -> Dict[str, Any]:
        """F-008: 卸载 Git 变更自动同步"""
        logger.info(f"卸载 Git 变更同步：project={project_name}, repo={repo_path}")

        try:
            from core.git_integration import GitChangeSynchronizer

            syncer = GitChangeSynchronizer(
                repo_path=repo_path,
                project_name=project_name,
                index_pipeline=self.index_pipeline,
                knowledge_graph=self._knowledge_graphs.get(project_name)
            )

            result = syncer.uninstall()

            # 移除缓存
            if hasattr(self, '_git_syncers') and project_name in self._git_syncers:
                del self._git_syncers[project_name]

            return {
                "success": True,
                "project_name": project_name,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"卸载失败：{str(e)}"
            }

    def git_sync_status(
        self,
        project_name: str,
        repo_path: str
    ) -> Dict[str, Any]:
        """F-008: 获取 Git 变更同步状态"""
        try:
            from core.git_integration import GitChangeSynchronizer

            # 先从缓存获取
            syncer = getattr(self, '_git_syncers', {}).get(project_name)
            if not syncer:
                syncer = GitChangeSynchronizer(
                    repo_path=repo_path,
                    project_name=project_name,
                    index_pipeline=self.index_pipeline,
                    knowledge_graph=self._knowledge_graphs.get(project_name)
                )

            return syncer.get_sync_status()

        except Exception as e:
            return {
                "error": f"获取状态失败：{str(e)}"
            }

    def git_sync_trigger(
        self,
        project_name: str,
        repo_path: str,
        trigger_type: str = "manual",
        base: Optional[str] = "HEAD~1",
        target: Optional[str] = "HEAD"
    ) -> Dict[str, Any]:
        """F-008: 触发 Git 变更同步"""
        logger.info(f"触发 Git 同步：project={project_name}, type={trigger_type}")

        try:
            from core.git_integration import GitChangeSynchronizer

            syncer = getattr(self, '_git_syncers', {}).get(project_name)
            if not syncer:
                syncer = GitChangeSynchronizer(
                    repo_path=repo_path,
                    project_name=project_name,
                    index_pipeline=self.index_pipeline,
                    knowledge_graph=self._knowledge_graphs.get(project_name)
                )

            # 获取 commit hash
            commit_hash = None
            if trigger_type == "git_hook" and target:
                try:
                    from core.git_integration import GitIntegration
                    git = GitIntegration(repo_path)
                    commit_hash = git.get_current_commit()
                except:
                    commit_hash = target

            event = syncer.trigger_sync(
                trigger_type=trigger_type,
                commit_hash=commit_hash
            )

            return {
                "success": event.status == "completed",
                "project_name": project_name,
                "event": event.to_dict()
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"触发同步失败：{str(e)}"
            }

    def git_sync_watch_start(
        self,
        project_name: str,
        repo_path: str,
        background: bool = True
    ) -> Dict[str, Any]:
        """F-008: 启动文件系统监听"""
        logger.info(f"启动文件监听：project={project_name}")

        try:
            from core.git_integration import GitChangeSynchronizer

            syncer = getattr(self, '_git_syncers', {}).get(project_name)
            if not syncer:
                syncer = GitChangeSynchronizer(
                    repo_path=repo_path,
                    project_name=project_name,
                    index_pipeline=self.index_pipeline,
                    knowledge_graph=self._knowledge_graphs.get(project_name)
                )
                self._git_syncers[project_name] = syncer

            result = syncer.start_watching(background=background)

            return {
                "success": result.get("success", False),
                "project_name": project_name,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"启动监听失败：{str(e)}"
            }

    def git_sync_watch_stop(
        self,
        project_name: str,
        repo_path: str
    ) -> Dict[str, Any]:
        """F-008: 停止文件系统监听"""
        logger.info(f"停止文件监听：project={project_name}")

        try:
            from core.git_integration import GitChangeSynchronizer

            syncer = getattr(self, '_git_syncers', {}).get(project_name)
            if not syncer:
                syncer = GitChangeSynchronizer(
                    repo_path=repo_path,
                    project_name=project_name,
                    index_pipeline=self.index_pipeline,
                    knowledge_graph=self._knowledge_graphs.get(project_name)
                )

            result = syncer.stop_watching()

            return {
                "success": result.get("success", False),
                "project_name": project_name,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"停止监听失败：{str(e)}"
            }

    def git_sync_history(
        self,
        project_name: str,
        repo_path: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """F-008: 获取 Git 变更同步历史"""
        try:
            from core.git_integration import GitChangeSynchronizer

            syncer = getattr(self, '_git_syncers', {}).get(project_name)
            if not syncer:
                syncer = GitChangeSynchronizer(
                    repo_path=repo_path,
                    project_name=project_name,
                    index_pipeline=self.index_pipeline,
                    knowledge_graph=self._knowledge_graphs.get(project_name)
                )

            history = syncer.get_sync_history(limit=limit)

            return {
                "success": True,
                "project_name": project_name,
                "history": history
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"获取历史失败：{str(e)}"
            }

    # ============= P8 代码审查功能 =============

    def review_code(
        self,
        code: str,
        language: str = "python",
        file_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        P8: 智能代码审查

        功能:
        1. 代码异味检测 (Code Smell Detection)
        2. 最佳实践建议 (Best Practice Suggestions)
        3. 安全风险识别 (Security Risk Detection)
        4. 性能问题分析 (Performance Analysis)
        5. 代码风格检查 (Style Checking)

        Args:
            code: 待审查的代码
            language: 语言标识 (python, javascript, typescript 等)
            file_path: 文件路径 (可选)
            config: 审查配置 (可选)

        Returns:
            审查报告，包含:
            - issues: 问题列表
            - quality_score: 质量评分 (0-100)
            - stats: 统计信息
            - fix_suggestions: 修复建议
            - summary: 审查摘要
        """
        logger.info(f"Starting code review: language={language}, file={file_path}")

        if self._code_review_service is None:
            self._code_review_service = CodeReviewService()

        return self._code_review_service.review_code(code, language, file_path, config)

    def review_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        P8: 审查文件

        Args:
            file_path: 文件路径
            language: 语言标识 (可选，自动从文件扩展名推断)
            config: 审查配置

        Returns:
            审查报告
        """
        logger.info(f"Reviewing file: {file_path}")

        # 验证路径安全
        if not self._validate_path_safety(file_path):
            return {
                "success": False,
                "error": f"路径安全检查失败：{file_path}"
            }

        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在：{file_path}"
            }

        # 自动推断语言
        if language is None:
            ext_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.jsx': 'javascript',
                '.tsx': 'typescript',
                '.java': 'java',
                '.go': 'go',
                '.rs': 'rust',
                '.cpp': 'cpp',
                '.c': 'c',
                '.h': 'cpp',
            }
            ext = os.path.splitext(file_path)[1].lower()
            language = ext_map.get(ext, 'python')

        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return {
                "success": False,
                "error": f"读取文件失败：{str(e)}"
            }

        return self.review_code(code, language, file_path, config)


understanding_service = UnderstandingService()