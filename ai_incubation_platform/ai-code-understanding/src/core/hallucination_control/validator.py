"""
幻觉控制与验证器
通过多维度校验确保AI生成内容的准确性，降低幻觉率
"""
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import re
from difflib import SequenceMatcher

from ..indexer.base import CodeChunk, CodeSymbol
from ..indexer.pipeline import IndexPipeline


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    confidence: float  # 0-1
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    corrected_content: Optional[str] = None


@dataclass
class Citation:
    """引用来源"""
    file_path: str
    start_line: int
    end_line: int
    text: str
    similarity: float
    chunk_id: str


class HallucinationValidator:
    """
    幻觉控制器
    核心设计思路：
    1. 所有生成内容必须可溯源到实际代码
    2. 多层级校验：语法级、语义级、事实级
    3. 置信度评分机制，低置信度内容必须标记
    4. 自动校正常见幻觉模式
    """

    def __init__(
        self,
        index_pipeline: IndexPipeline,
        config: Optional[Dict[str, Any]] = None
    ):
        self.index_pipeline = index_pipeline
        self.config = config or {}
        self.min_citation_similarity = self.config.get('min_citation_similarity', 0.7)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.max_hallucination_ratio = self.config.get('max_hallucination_ratio', 0.2)

        # 常见幻觉模式
        self.hallucination_patterns = [
            # 虚构的函数/类名
            r'(函数|类|方法|接口)\s*["\']?([A-Za-z_][A-Za-z0-9_]*)["\']?\s*(不存在|没有实现)?',
            # 虚构的参数
            r'(参数|入参|出参|返回值)\s*["\']?([A-Za-z_][A-Za-z0-9_]*)["\']?',
            # 虚构的路径
            r'(路径|文件|目录)\s*["\']?([/\w\-\.]+\.\w+)["\']?',
            # 确定的陈述
            r'(肯定|一定|绝对|必然|就是)\s*',
        ]


    def validate_summarization(
        self,
        summary: str,
        module_symbols: List[CodeSymbol],
        related_chunks: List[CodeChunk]
    ) -> ValidationResult:
        """验证模块摘要的准确性"""
        errors = []
        warnings = []
        citations = []
        confidence = 1.0

        # 1. 校验摘要中提到的功能是否与实际符号匹配
        mentioned_symbols = self._extract_mentioned_symbols(summary)
        actual_symbol_names = {s.name for s in module_symbols}

        for symbol in mentioned_symbols:
            if symbol not in actual_symbol_names and not symbol.startswith('_'):
                # 检查是否是拼写错误
                similar = self._find_similar_symbol(symbol, actual_symbol_names)
                if similar:
                    errors.append(f"提到的符号 '{symbol}' 不存在，是否是 '{similar}'？")
                else:
                    errors.append(f"提到的符号 '{symbol}' 在模块中不存在")
                confidence *= 0.8

        # 2. 校验职责描述的准确性
        citations = self._find_citations(summary, related_chunks)
        citation_coverage = len(citations) / max(1, len(summary.split('。')))
        if citation_coverage < 0.3:
            warnings.append("摘要描述的部分内容没有找到代码依据")
            confidence *= (0.7 + citation_coverage * 0.3)

        # 3. 校验API列表的准确性
        if "API" in summary or "接口" in summary:
            public_symbols = {s.name for s in module_symbols if not s.name.startswith('_')}
            mentioned_apis = [s for s in mentioned_symbols if s in public_symbols]
            if len(mentioned_apis) < len(public_symbols) * 0.5 and len(public_symbols) > 3:
                warnings.append("摘要遗漏了部分公开API")

        confidence = max(0.0, min(1.0, confidence))
        is_valid = confidence >= self.confidence_threshold and len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            errors=errors,
            warnings=warnings,
            citations=[self._citation_to_dict(cit) for cit in citations]
        )

    def validate_answer(
        self,
        answer: str,
        question: str,
        related_chunks: List[CodeChunk]
    ) -> ValidationResult:
        """验证代码库问答的准确性"""
        errors = []
        warnings = []
        citations = []
        confidence = 1.0

        # 1. 答案是否有足够的引用支持
        citations = self._find_citations(answer, related_chunks)
        if not citations:
            errors.append("回答没有找到任何代码引用支持，可能完全是幻觉")
            confidence = 0.0
        else:
            # 计算引用覆盖率
            answer_sentences = re.split(r'[。？！\n]', answer)
            answer_sentences = [s.strip() for s in answer_sentences if len(s.strip()) > 10]
            covered_sentences = 0

            for sentence in answer_sentences:
                for cit in citations:
                    if SequenceMatcher(None, sentence, cit.text).ratio() > 0.5:
                        covered_sentences += 1
                        break

            coverage = covered_sentences / max(1, len(answer_sentences))
            if coverage < 0.5:
                warnings.append(f"回答只有 {int(coverage*100)}% 的内容有代码依据")
                confidence *= (0.5 + coverage * 0.5)

        # 2. 检查是否有虚构的确定性陈述
        if any(word in answer.lower() for word in ["肯定", "一定", "绝对", "必然", "就是"]):
            # 检查这些陈述是否有引用支持
            strong_statements = re.findall(r'([^。！？]*?(肯定|一定|绝对|必然|就是)[^。！？]*[。！？])', answer)
            for stmt, _ in strong_statements:
                has_support = any(SequenceMatcher(None, stmt, cit.text).ratio() > 0.6 for cit in citations)
                if not has_support:
                    warnings.append(f"确定性陈述 '{stmt.strip()}' 没有找到代码依据")
                    confidence *= 0.8

        # 3. 检查是否回答了问题
        question_terms = set(re.findall(r'\b\w+\b', question.lower()))
        answer_terms = set(re.findall(r'\b\w+\b', answer.lower()))
        overlap = len(question_terms & answer_terms) / max(1, len(question_terms))
        if overlap < 0.3:
            warnings.append("回答似乎与问题关联度不高")
            confidence *= 0.8

        confidence = max(0.0, min(1.0, confidence))
        is_valid = confidence >= self.confidence_threshold and len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            errors=errors,
            warnings=warnings,
            citations=[self._citation_to_dict(cit) for cit in citations]
        )

    def _validate_symbols(self, text: str, related_chunks: List[CodeChunk]) -> Tuple[List[str], float]:
        """验证文本中提到的符号是否真实存在"""
        errors = []
        all_symbols = set()
        for chunk in related_chunks:
            all_symbols.update(chunk.symbols)

        # 提取可能的符号名（驼峰或蛇形命名）
        mentioned_symbols = self._extract_mentioned_symbols(text)
        confidence = 1.0

        for symbol in mentioned_symbols:
            if len(symbol) < 3:
                continue  # 跳过太短的可能不是符号的词

            if symbol not in all_symbols and not symbol.startswith('_'):
                # 检查是否是大小写问题
                lower_symbol = symbol.lower()
                matched = [s for s in all_symbols if s.lower() == lower_symbol]
                if matched:
                    errors.append(f"符号 '{symbol}' 大小写错误，正确应为 '{matched[0]}'")
                    confidence *= 0.9
                else:
                    # 检查是否是拼写错误
                    similar = self._find_similar_symbol(symbol, all_symbols)
                    if similar:
                        errors.append(f"符号 '{symbol}' 不存在，是否是 '{similar}'？")
                    else:
                        errors.append(f"符号 '{symbol}' 在相关代码中不存在")
                    confidence *= 0.8

        return errors, confidence

    def _extract_mentioned_symbols(self, text: str) -> Set[str]:
        """提取文本中提到的可能的符号名"""
        symbols = set()

        # 匹配驼峰命名
        camel_case = re.findall(r'\b[a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b', text)
        symbols.update(camel_case)

        # 匹配蛇形命名
        snake_case = re.findall(r'\b[a-z][a-z0-9_]*_[a-z0-9_]+\b', text)
        symbols.update(snake_case)

        # 匹配帕斯卡命名
        pascal_case = re.findall(r'\b[A-Z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b', text)
        symbols.update(pascal_case)

        # 匹配引号中的名称
        quoted = re.findall(r'["\']([A-Za-z_][A-Za-z0-9_]*)["\']', text)
        symbols.update(quoted)

        return symbols

    def _find_similar_symbol(self, symbol: str, symbol_set: Set[str], threshold: float = 0.7) -> Optional[str]:
        """查找相似的符号名"""
        best_match = None
        best_ratio = 0.0

        for s in symbol_set:
            ratio = SequenceMatcher(None, symbol.lower(), s.lower()).ratio()
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = s

        return best_match

    def _validate_facts(
        self,
        explanation: str,
        code_context: str,
        related_chunks: List[CodeChunk]
    ) -> Tuple[List[str], float]:
        """验证事实陈述的准确性"""
        errors = []
        confidence = 1.0

        # 检查参数数量是否匹配
        param_matches = re.findall(r'(接受|有|需要|返回)\s*(\d+)\s*个(参数|返回值)', explanation)
        if param_matches:
            # 简单的参数计数校验
            func_defs = re.findall(r'def\s+\w+\s*\(([^)]*)\)', code_context)
            for match in param_matches:
                _, count, _ = match
                expected_count = int(count)
                for def_str in func_defs:
                    actual_params = [p.strip() for p in def_str.split(',') if p.strip()]
                    actual_count = len(actual_params)
                    if 'self' in actual_params:
                        actual_count -= 1
                    if expected_count != actual_count and abs(expected_count - actual_count) <= 2:
                        errors.append(f"参数数量错误：声称有{expected_count}个参数，实际有{actual_count}个")
                        confidence *= 0.8

        # 检查返回值类型陈述
        return_type_matches = re.findall(r'返回\s*(字符串|整数|浮点数|布尔|列表|字典|对象|None)', explanation)
        if return_type_matches:
            return_stmts = re.findall(r'return\s+([^#\n]+)', code_context)
            for expected_type in return_type_matches:
                # 简单的返回值类型推断
                has_match = False
                for stmt in return_stmts:
                    stmt = stmt.strip()
                    if expected_type == "字符串" and (stmt.startswith(('"', "'")) or "str" in stmt):
                        has_match = True
                    elif expected_type == "整数" and (stmt.isdigit() or "int" in stmt):
                        has_match = True
                    elif expected_type == "布尔" and stmt in ["True", "False", "true", "false"]:
                        has_match = True
                    elif expected_type == "列表" and stmt.startswith('['):
                        has_match = True
                    elif expected_type == "字典" and stmt.startswith('{'):
                        has_match = True
                    elif expected_type == "None" and stmt == "None":
                        has_match = True
                if not has_match and return_stmts:
                    errors.append(f"返回值类型描述可能错误：没有找到返回{expected_type}的语句")
                    confidence *= 0.85

        # 检查继承关系陈述
        inherit_matches = re.findall(r'(继承|扩展|实现|继承自)\s*["\']?([A-Za-z_][A-Za-z0-9_]*)["\']?', explanation)
        if inherit_matches:
            class_defs = re.findall(r'class\s+\w+\s*\(([^)]*)\)', code_context)
            base_classes = set()
            for def_str in class_defs:
                bases = [b.strip() for b in def_str.split(',') if b.strip()]
                base_classes.update(bases)

            for match in inherit_matches:
                _, base_class = match
                if base_class not in base_classes:
                    errors.append(f"继承关系错误：类没有继承自{base_class}")
                    confidence *= 0.8

        # 检查异常抛出陈述
        exception_matches = re.findall(r'(抛出|引发|raise)\s*["\']?([A-Za-z_][A-Za-z0-9_]*Error)?["\']?', explanation)
        if exception_matches:
            raise_stmts = re.findall(r'raise\s+([A-Za-z0-9_]*)', code_context)
            raised_exceptions = set(raise_stmts)

            for match in exception_matches:
                _, exc_type = match
                if exc_type and exc_type not in raised_exceptions:
                    errors.append(f"异常描述错误：代码中没有抛出{exc_type}异常")
                    confidence *= 0.8

        # 检查修饰符陈述（public/private/static等）
        modifier_matches = re.findall(r'(公有|私有|公共|private|public|static|静态)\s*(方法|函数|类|属性)', explanation)
        if modifier_matches:
            # 检查Python中的命名约定
            symbols = set()
            for chunk in related_chunks:
                symbols.update(chunk.symbols)

            for match in modifier_matches:
                modifier, _ = match
                if modifier in ['私有', 'private']:
                    # 检查是否有私有符号（下划线开头）
                    has_private = any(s.startswith('_') for s in symbols)
                    if not has_private:
                        warnings.append("提到的私有成员在代码中未找到")
                        confidence *= 0.9

        return errors, confidence

    def _validate_semantic_consistency(
        self,
        explanation: str,
        code_context: str,
        related_chunks: List[CodeChunk]
    ) -> Tuple[List[str], float]:
        """验证解释与代码的语义一致性"""
        errors = []
        confidence = 1.0

        # 提取代码中的关键词
        code_keywords = set()
        # 提取函数名、类名
        func_names = re.findall(r'def\s+(\w+)\s*\(', code_context)
        class_names = re.findall(r'class\s+(\w+)\s*[(:]', code_context)
        var_names = re.findall(r'\b([a-z_][a-z0-9_]*)\s*=', code_context)
        code_keywords.update(func_names)
        code_keywords.update(class_names)
        code_keywords.update(var_names)

        # 提取解释中的关键词
        explanation_keywords = set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', explanation))

        # 检查解释中提到的关键词是否在代码中存在
        mentioned_symbols = self._extract_mentioned_symbols(explanation)
        for symbol in mentioned_symbols:
            if len(symbol) > 2 and symbol not in code_keywords and not symbol.startswith('_'):
                # 检查是否是大小写问题
                lower_symbol = symbol.lower()
                matched = [s for s in code_keywords if s.lower() == lower_symbol]
                if matched:
                    errors.append(f"符号大小写错误：'{symbol}' 应为 '{matched[0]}'")
                    confidence *= 0.9
                else:
                    # 检查是否是拼写错误
                    similar = self._find_similar_symbol(symbol, code_keywords)
                    if similar:
                        errors.append(f"可能的拼写错误：'{symbol}' 是否是 '{similar}'？")
                        confidence *= 0.85
                    else:
                        errors.append(f"提到的符号 '{symbol}' 在代码中不存在")
                        confidence *= 0.8

        # 检查否定陈述
        negative_phrases = ["不支持", "没有", "不会", "不能", "不存在", "无需", "不需要"]
        for phrase in negative_phrases:
            if phrase in explanation:
                # 检查是否真的不存在
                sentences = re.split(r'[。？！\n]', explanation)
                for sent in sentences:
                    if phrase in sent:
                        # 提取陈述的主体
                        subject_match = re.search(rf'{phrase}([^。？！\n]+)', sent)
                        if subject_match:
                            subject = subject_match.group(1).strip()
                            # 检查主体是否真的不存在于代码中
                            subject_keywords = re.findall(r'\b\w+\b', subject)
                            for kw in subject_keywords:
                                if kw in code_keywords:
                                    errors.append(f"否定陈述可能错误：代码中存在'{kw}'，但解释称{phrase}{subject}")
                                    confidence *= 0.75

        return errors, confidence

    def validate_explanation(
        self,
        explanation: str,
        code_context: str,
        related_chunks: List[CodeChunk]
    ) -> ValidationResult:
        """验证代码解释的准确性"""
        errors = []
        warnings = []
        citations = []
        confidence = 1.0

        # 1. 校验解释中提到的符号是否真实存在
        symbol_errors, symbol_confidence = self._validate_symbols(explanation, related_chunks)
        errors.extend(symbol_errors)
        confidence *= symbol_confidence

        # 2. 校验解释中的事实陈述是否与代码一致
        fact_errors, fact_confidence = self._validate_facts(explanation, code_context, related_chunks)
        errors.extend(fact_errors)
        confidence *= fact_confidence

        # 3. 新增：语义一致性校验
        semantic_errors, semantic_confidence = self._validate_semantic_consistency(explanation, code_context, related_chunks)
        errors.extend(semantic_errors)
        confidence *= semantic_confidence

        # 4. 查找引用来源
        citations = self._find_citations(explanation, related_chunks)
        if not citations:
            warnings.append("该解释没有找到明确的代码引用来源，可能存在幻觉风险")
            confidence *= 0.7

        # 5. 检测幻觉模式
        hallucination_warnings = self._detect_hallucination_patterns(explanation)
        warnings.extend(hallucination_warnings)
        if hallucination_warnings:
            confidence *= max(0.8, 1 - len(hallucination_warnings) * 0.05)

        # 6. 计算最终置信度
        confidence = max(0.0, min(1.0, confidence))
        is_valid = confidence >= self.confidence_threshold and len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            errors=errors,
            warnings=warnings,
            citations=[self._citation_to_dict(cit) for cit in citations]
        )
    def _find_citations(self, text: str, related_chunks: List[CodeChunk]) -> List[Citation]:
        """查找文本内容的引用来源（把摘要/解释中的句子映射到相关代码行）"""
        citations: List[Citation] = []
        sentences = re.split(r'[。？！\n]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        for sentence in sentences:
            best_match: Optional[str] = None
            best_ratio: float = 0.0
            best_chunk: Optional[CodeChunk] = None

            for chunk in related_chunks:
                # 分块匹配句子到代码行（用“句子-行”的相似度做最小化对齐）
                chunk_lines = chunk.content.split('\n')
                for line in chunk_lines:
                    line = line.strip()
                    if len(line) < 10:
                        continue
                    ratio = SequenceMatcher(None, sentence, line).ratio()
                    if ratio > best_ratio and ratio >= self.min_citation_similarity:
                        best_ratio = ratio
                        best_match = line
                        best_chunk = chunk

            if best_match and best_chunk:
                citations.append(
                    Citation(
                        file_path=best_chunk.file_path,
                        start_line=best_chunk.start_line,
                        end_line=best_chunk.end_line,
                        text=best_match,
                        similarity=best_ratio,
                        chunk_id=best_chunk.chunk_id,
                    )
                )

        # 去重（同一段引用文本的重复匹配不需要保留）
        unique_citations: List[Citation] = []
        seen: Set[Tuple[str, str]] = set()
        for cit in citations:
            key = (cit.file_path, cit.text[:50])
            if key not in seen:
                seen.add(key)
                unique_citations.append(cit)

        # 按相似度排序
        unique_citations.sort(key=lambda x: x.similarity, reverse=True)
        return unique_citations[:10]  # 最多10个引用

    def _detect_hallucination_patterns(self, text: str) -> List[str]:
        """检测可能的幻觉模式"""
        warnings = []

        # 检查过于确定性的表述
        strong_words = ["肯定", "一定", "绝对", "必然", "就是", "毫无疑问", "毋庸置疑"]
        for word in strong_words:
            if word in text:
                warnings.append(f"包含过于确定的表述 '{word}'，请核实准确性")

        # 检查是否提到不存在的功能
        if "支持" in text or "可以" in text or "能够" in text:
            # 这种陈述需要特别验证
            warnings.append("包含功能承诺类表述，请确保有代码依据")

        return warnings

    def _citation_to_dict(self, citation: Citation) -> Dict[str, Any]:
        """转换引用为可序列化格式"""
        return {
            "file_path": citation.file_path,
            "start_line": citation.start_line,
            "end_line": citation.end_line,
            "text": citation.text,
            "similarity": round(citation.similarity, 2)
        }

    def auto_correct(self, content: str, errors: List[str], related_chunks: List[CodeChunk]) -> str:
        """自动校正常见的幻觉错误"""
        corrected = content

        # 收集所有真实符号
        all_symbols = set()
        for chunk in related_chunks:
            all_symbols.update(chunk.symbols)

        # 修正符号错误
        for error in errors:
            if "大小写错误" in error or "拼写错误" in error:
                # 提取错误的符号和正确的符号
                wrong_match = re.search(r"'([^']+)'", error)
                right_match = re.search(r"'([^']+)'(?:\?|。)?$", error)
                if wrong_match and right_match:
                    wrong_symbol = wrong_match.group(1)
                    right_symbol = right_match.group(1).rstrip('?')
                    # 替换所有出现的错误符号
                    corrected = corrected.replace(wrong_symbol, right_symbol)

        # 修正参数数量错误
        for error in errors:
            if "参数数量错误" in error:
                count_match = re.search(r'(\d+)个参数.*实际有(\d+)个', error)
                if count_match:
                    wrong_count = count_match.group(1)
                    right_count = count_match.group(2)
                    corrected = corrected.replace(f"{wrong_count}个参数", f"{right_count}个参数")

        return corrected

    def add_citations_to_content(self, content: str, citations: List[Dict[str, Any]]) -> str:
        """为内容添加引用标记"""
        if not citations:
            return content

        # 在内容末尾添加引用列表
        citation_text = "\n\n**引用来源：**\n"
        for i, cit in enumerate(citations, 1):
            citation_text += f"{i}. {cit['file_path']}:{cit['start_line']}-{cit['end_line']} (相似度 {cit['similarity']})\n"
            citation_text += f"   ```\n   {cit['text'][:100]}...\n   ```\n"

        return content + citation_text
