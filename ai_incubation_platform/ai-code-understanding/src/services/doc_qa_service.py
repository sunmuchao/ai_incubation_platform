"""
智能文档问答服务
提供基于文档的语义搜索、QA 问答、答案溯源、代码导航等功能
"""
from typing import Any, Dict, List, Optional, Tuple
import os
import logging
from pathlib import Path
import json
import time
from dataclasses import dataclass, asdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# LLM 客户端支持
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# 向量存储 - LlamaIndex
from core.indexer.vector_stores.chroma_store import LlamaIndexVectorStore
from core.indexer.base import CodeChunk
from core.indexer.embeddings.bge_embedding import BGEEmbedding
from core.indexer.embeddings.hash_embedding import HashEmbedding


@dataclass
class SearchResult:
    """搜索结果"""
    content: str
    file_path: str
    start_line: int
    end_line: int
    similarity: float
    chunk_type: str
    symbols: List[str]
    metadata: Dict[str, Any]


@dataclass
class QAAnswer:
    """问答答案"""
    answer: str
    confidence: float
    sources: List[SearchResult]
    code_references: List[Dict[str, Any]]
    follow_up_questions: List[str]


@dataclass
class DocSearchRequest:
    """文档搜索请求"""
    query: str
    project_name: str
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = None


@dataclass
class SemanticSearchResult:
    """语义搜索结果"""
    query: str
    results: List[SearchResult]
    total_found: int
    search_time_ms: float
    suggestions: List[str]


class DocQAService:
    """
    智能文档问答服务

    功能:
    1. 文档语义搜索 - 基于向量检索的文档搜索
    2. 代码 QA 问答 - 回答关于代码库的问题
    3. 答案溯源引用 - 定位到具体文件/函数
    4. 代码导航辅助 - 跳转到定义/引用
    5. 智能代码解释 - 解释代码片段的功能
    """

    def __init__(self, project_name: str = "default", persist_directory: str = "./data/chroma"):
        self.project_name = project_name
        self.persist_directory = persist_directory

        # 初始化向量存储 - LlamaIndex
        self.vector_store = LlamaIndexVectorStore({
            'persist_directory': persist_directory,
            'allow_reset': True
        })
        self.vector_store.connect({})

        # 初始化嵌入模型
        self.embedder = BGEEmbedding()

        # 初始化 LLM 客户端
        self.llm_client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm_client = OpenAI(api_key=api_key)

        # 缓存代码内容
        self._code_cache: Dict[str, str] = {}

    def search_documents(
        self,
        query: str,
        project_name: Optional[str] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> SemanticSearchResult:
        """
        语义搜索文档

        Args:
            query: 搜索查询
            project_name: 项目名称，默认为当前项目
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            语义搜索结果
        """
        project = project_name or self.project_name
        collection_name = f"{project}_docs"

        start_time = time.time()

        # 生成查询嵌入
        query_embedding = self.embedder.encode_text(query)

        # 执行搜索
        try:
            chunks = self.vector_store.search(
                collection_name=collection_name,
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters
            )
        except Exception as e:
            logger.warning(f"Search failed for collection {collection_name}: {e}")
            chunks = []

        search_time_ms = (time.time() - start_time) * 1000

        # 转换结果
        results = []
        for chunk in chunks:
            result = SearchResult(
                content=chunk.content,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                similarity=chunk.metadata.get('similarity', 0.0),
                chunk_type=chunk.chunk_type,
                symbols=chunk.symbols,
                metadata=chunk.metadata
            )
            results.append(result)

        # 生成搜索建议
        suggestions = self._generate_search_suggestions(query, results)

        return SemanticSearchResult(
            query=query,
            results=results,
            total_found=len(results),
            search_time_ms=search_time_ms,
            suggestions=suggestions
        )

    def ask_question(
        self,
        question: str,
        project_name: Optional[str] = None,
        scope_paths: Optional[List[str]] = None,
        max_context_chunks: int = 5
    ) -> QAAnswer:
        """
        回答关于代码库的问题

        Args:
            question: 问题
            project_name: 项目名称
            scope_paths: 限定搜索范围的路径列表
            max_context_chunks: 最大上下文块数量

        Returns:
            答案和引用来源
        """
        project = project_name or self.project_name

        # 搜索相关文档
        filters = None
        if scope_paths:
            filters = {"file_path": {"$contains": scope_paths[0] if len(scope_paths) == 1 else ""}}

        search_result = self.search_documents(
            query=question,
            project_name=project,
            top_k=max_context_chunks,
            filters=filters
        )

        # 构建上下文
        context_chunks = []
        code_references = []

        for i, result in enumerate(search_result.results):
            context_chunks.append({
                "index": i + 1,
                "content": result.content,
                "file": result.file_path,
                "lines": f"{result.start_line}-{result.end_line}"
            })

            code_references.append({
                "file_path": result.file_path,
                "start_line": result.start_line,
                "end_line": result.end_line,
                "chunk_type": result.chunk_type,
                "symbols": result.symbols,
                "preview": result.content[:200] + "..." if len(result.content) > 200 else result.content
            })

        # 生成答案
        answer, confidence = self._generate_answer(question, context_chunks)

        # 生成后续问题
        follow_up_questions = self._generate_follow_up_questions(question, context_chunks)

        # 转换搜索结果为答案来源
        sources = search_result.results

        return QAAnswer(
            answer=answer,
            confidence=confidence,
            sources=sources,
            code_references=code_references,
            follow_up_questions=follow_up_questions
        )

    def _generate_answer(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Tuple[str, float]:
        """
        基于上下文生成答案

        Returns:
            (答案，置信度)
        """
        if not context_chunks:
            return (
                "抱歉，我没有找到与您的问题相关的代码文档。您可以尝试：\n"
                "1. 使用更具体的关键词\n"
                "2. 检查项目名称是否正确\n"
                "3. 确认项目已被索引",
                0.0
            )

        # 构建上下文文本
        context_text = "\n\n".join([
            f"[{chunk['index']}] 文件：{chunk['file']} (行 {chunk['lines']})\n{chunk['content']}"
            for chunk in context_chunks
        ])

        # 如果有 LLM，使用 LLM 生成答案
        if self.llm_client:
            try:
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是一个专业的代码理解助手。基于提供的代码上下文，"
                                "准确回答用户的问题。如果上下文不足以回答问题，请诚实说明。"
                                "所有引用都必须来自提供的上下文，不要编造信息。"
                            )
                        },
                        {
                            "role": "user",
                            "content": f"上下文:\n{context_text}\n\n问题：{question}"
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )
                answer = response.choices[0].message.content
                confidence = 0.85  # 有 LLM 时的置信度
                return answer, confidence
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                # 降级到基于规则的摘要

        # 无 LLM 时，返回基于上下文的摘要
        answer = self._generate_summary_answer(question, context_chunks)
        confidence = 0.6  # 无 LLM 时的置信度
        return answer, confidence

    def _generate_summary_answer(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]]
    ) -> str:
        """生成基于规则的摘要答案"""
        if not context_chunks:
            return "未找到相关信息"

        # 分析关键字
        question_lower = question.lower()

        # 检测问题类型
        if "如何" in question or "how" in question_lower:
            # 如何做某事
            answer = "根据代码分析，以下是相关实现：\n\n"
            for i, chunk in enumerate(context_chunks[:3], 1):
                answer += f"{i}. **{chunk['file']}** (行 {chunk['lines']}):\n"
                answer += f"   ```\n{chunk['content'][:150]}...\n   ```\n\n"
            return answer

        elif "什么" in question or "what" in question_lower:
            # 是什么
            answer = "根据代码分析：\n\n"
            for i, chunk in enumerate(context_chunks[:3], 1):
                answer += f"{i}. **{chunk['file']}**: {chunk['content'][:200]}...\n\n"
            return answer

        elif "哪里" in question or "where" in question_lower:
            # 在哪里
            answer = "相关代码位置：\n\n"
            for i, chunk in enumerate(context_chunks[:3], 1):
                answer += f"{i}. `{chunk['file']}` (第 {chunk['start_line']}-{chunk['end_line']} 行)\n"
            return answer

        elif any(kw in question_lower for kw in ["define", "定义", "implement", "实现"]):
            # 定义/实现
            answer = "定义位置：\n\n"
            for chunk in context_chunks[:3]:
                symbols = ", ".join(chunk.get('symbols', [])) if chunk.get('symbols') else "N/A"
                answer += f"- **{chunk['file']}**: 符号 [{symbols}]\n"
            return answer

        else:
            # 通用回答
            answer = f"找到 {len(context_chunks)} 个相关代码片段：\n\n"
            for i, chunk in enumerate(context_chunks[:5], 1):
                answer += f"{i}. `{chunk['file']}` (行 {chunk['start_line']}-{chunk['end_line']})\n"
            return answer

    def _generate_follow_up_questions(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """生成后续问题建议"""
        if not context_chunks:
            return []

        suggestions = []

        # 基于找到的文件生成问题
        files = list(set([chunk['file'] for chunk in context_chunks]))

        if files:
            suggestions.append(f"{files[0]} 的主要功能是什么？")
            suggestions.append(f"如何调用 {files[0].split('/')[-1]} 中的函数？")

        # 基于问题类型生成
        if "如何" in question:
            suggestions.append("这个功能有哪些配置选项？")
            suggestions.append("有哪些相关的 API 端点？")

        if len(context_chunks) > 1:
            suggestions.append("这些模块之间的依赖关系是什么？")

        return suggestions[:3]

    def _generate_search_suggestions(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[str]:
        """生成搜索建议"""
        suggestions = []

        # 基于结果类型建议
        chunk_types = set([r.chunk_type for r in results])
        if 'function' in chunk_types:
            suggestions.append("查看相关函数定义")
        if 'class' in chunk_types:
            suggestions.append("查看类结构")
        if 'api' in chunk_types:
            suggestions.append("查看 API 端点")

        # 基于文件建议
        files = list(set([r.file_path for r in results[:5]]))
        for f in files[:2]:
            suggestions.append(f"浏览 {f.split('/')[-1]}")

        return suggestions[:5]

    def get_code_navigation(
        self,
        file_path: str,
        symbol_name: Optional[str] = None,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取代码导航信息

        Args:
            file_path: 文件路径
            symbol_name: 符号名称（可选）
            project_name: 项目名称

        Returns:
            导航信息，包含定义、引用等
        """
        project = project_name or self.project_name

        # 读取文件内容
        full_path = file_path if os.path.isabs(file_path) else os.path.join(
            os.getcwd(), project, file_path
        )

        if not os.path.exists(full_path):
            return {"error": f"文件不存在：{file_path}"}

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析符号
        symbols = self._extract_symbols(content, file_path)

        if symbol_name:
            # 查找特定符号
            symbol_info = next((s for s in symbols if s['name'] == symbol_name), None)
            if not symbol_info:
                return {"error": f"符号未找到：{symbol_name}"}
            return symbol_info

        return {
            "file_path": file_path,
            "symbols": symbols,
            "total_symbols": len(symbols)
        }

    def _extract_symbols(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """从代码中提取符号"""
        symbols = []
        ext = os.path.splitext(file_path)[1]

        if ext == '.py':
            # Python 符号提取
            import re

            # 函数定义
            for match in re.finditer(r'def\s+(\w+)\s*\(', content):
                line_num = content[:match.start()].count('\n') + 1
                symbols.append({
                    "name": match.group(1),
                    "type": "function",
                    "line": line_num,
                    "file": file_path
                })

            # 类定义
            for match in re.finditer(r'class\s+(\w+)', content):
                line_num = content[:match.start()].count('\n') + 1
                symbols.append({
                    "name": match.group(1),
                    "type": "class",
                    "line": line_num,
                    "file": file_path
                })

        return symbols

    def explain_code(
        self,
        code: str,
        language: str = "python",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        智能解释代码

        Args:
            code: 代码片段
            language: 语言标识
            context: 额外上下文

        Returns:
            代码解释
        """
        result = {
            "language": language,
            "code_length": len(code),
            "explanation": "",
            "key_concepts": [],
            "suggestions": []
        }

        # 使用 LLM 解释
        if self.llm_client:
            try:
                prompt = f"请用简洁的中文解释以下{language}代码的功能和关键概念：\n\n```{language}\n{code}\n```"
                if context:
                    prompt += f"\n\n上下文：{context}"

                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是一个专业的代码解释助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800,
                    temperature=0.3
                )
                result["explanation"] = response.choices[0].message.content
                result["confidence"] = 0.9
                return result
            except Exception as e:
                logger.error(f"LLM explanation failed: {e}")

        # 降级到基于规则的解释
        result["explanation"] = self._rule_based_explain(code, language)
        result["confidence"] = 0.5
        return result

    def _rule_based_explain(self, code: str, language: str) -> str:
        """基于规则解释代码"""
        if language == "python":
            import re

            explanations = []

            # 检测函数
            functions = re.findall(r'def\s+(\w+)\s*\((.*?)\)', code)
            if functions:
                for name, params in functions:
                    param_list = [p.strip().split('=')[0].strip().split(':')[0].strip()
                                 for p in params.split(',') if p.strip()]
                    explanations.append(f"- 定义函数 `{name}`，参数：{', '.join(param_list) or '无'}")

            # 检测类
            classes = re.findall(r'class\s+(\w+)', code)
            if classes:
                explanations.append(f"- 定义类：{', '.join(classes)}")

            # 检测导入
            imports = re.findall(r'^(?:from|import)\s+[\w.]+', code, re.MULTILINE)
            if imports:
                explanations.append(f"- 导入模块：{len(imports)} 个")

            if explanations:
                return "代码结构分析：\n" + "\n".join(explanations)

        return f"这是一段{language}代码，长度为{len(code)}字符。"

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取文档集合统计信息"""
        try:
            collections = self.vector_store.list_collections()
            stats = {}
            for col in collections:
                if col.endswith("_docs"):
                    try:
                        col_stats = self.vector_store.get_collection_stats(col)
                        stats[col] = col_stats
                    except Exception:
                        pass
            return {
                "project": self.project_name,
                "collections": stats,
                "total_collections": len(stats)
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}


# 便捷函数
_doc_qa_cache: Dict[str, DocQAService] = {}


def create_doc_qa_service(
    project_name: str = "default",
    persist_directory: str = "./data/chroma"
) -> DocQAService:
    """创建文档问答服务实例"""
    cache_key = f"{project_name}:{persist_directory}"
    if cache_key not in _doc_qa_cache:
        _doc_qa_cache[cache_key] = DocQAService(project_name, persist_directory)
    return _doc_qa_cache[cache_key]


def search_documents(
    query: str,
    project_name: str = "default",
    top_k: int = 10
) -> SemanticSearchResult:
    """快捷搜索文档"""
    service = create_doc_qa_service(project_name)
    return service.search_documents(query, project_name, top_k)


def ask_codebase_question(
    question: str,
    project_name: str = "default",
    scope_paths: Optional[List[str]] = None
) -> QAAnswer:
    """快捷问答"""
    service = create_doc_qa_service(project_name)
    return service.ask_question(question, project_name, scope_paths)
