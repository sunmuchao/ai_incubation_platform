"""
智能验收助手服务。

使用 NLP 和规则引擎自动检查交付内容是否符合验收标准，提供：
1. 语义相似度匹配
2. 关键词检查
3. 格式验证
4. 内容质量分析
5. 验收报告生成
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from models.intelligent_acceptance import (
    AcceptanceCheckItem,
    AcceptanceConfig,
    AcceptanceReport,
    AcceptanceRequest,
    AcceptanceResponse,
    CheckItemType,
    CheckResult,
)

logger = logging.getLogger(__name__)


class IntelligentAcceptanceService:
    """
    智能验收助手服务。

    核心功能：
    1. NLP 语义相似度匹配 - 比较交付内容与验收标准的语义相似度
    2. 关键词检查 - 检查是否包含必要的关键词
    3. 格式验证 - 验证交付内容的格式是否正确
    4. 内容质量分析 - 分析内容的完整性和质量
    5. 验收报告生成 - 生成详细的验收报告和建议
    """

    # 常见格式检查模式
    FORMAT_PATTERNS = {
        "json": r'^\s*[\{\[]',
        "xml": r'^\s*<\?xml',
        "markdown": r'^\s*(#|\*|\-|\[)',
        "email": r'^[\w\.-]+@[\w\.-]+\.\w+$',
        "url": r'^https?://',
        "phone_cn": r'^1[3-9]\d{9}$',
        "id_card_cn": r'^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$',
    }

    # 内容质量检查配置
    CONTENT_QUALITY_CONFIG = {
        "min_word_count": 50,
        "min_sentence_count": 3,
        "max_repetition_ratio": 0.5,
        "required_punctuation": [".", ",", "。", "，"],
    }

    def __init__(self, config: Optional[AcceptanceConfig] = None):
        self.config = config or AcceptanceConfig()
        self._reports: Dict[str, AcceptanceReport] = {}
        self._task_reports: Dict[str, List[str]] = {}

    def check_acceptance(self, request: AcceptanceRequest) -> AcceptanceResponse:
        """执行智能验收检查。"""
        try:
            check_items = self._create_check_items(request)
            for item in check_items:
                self._execute_check(item, request)
            report = self._create_report(request, check_items)
            recommendation = self._generate_recommendation(report)
            self._reports[report.id] = report
            if request.task_id not in self._task_reports:
                self._task_reports[request.task_id] = []
            self._task_reports[request.task_id].append(report.id)

            logger.info(
                "Acceptance check completed: report_id=%s, task_id=%s, result=%s, score=%.2f",
                report.id, request.task_id, report.overall_result.value, report.overall_score,
            )

            return AcceptanceResponse(
                success=True,
                report_id=report.id,
                overall_result=report.overall_result,
                overall_score=report.overall_score,
                confidence=report.confidence,
                recommendation=recommendation,
                message=self._generate_message(report, recommendation),
                check_summary={
                    "pass": report.passed_count,
                    "fail": report.failed_count,
                    "warning": report.warning_count,
                },
            )
        except Exception as e:
            logger.exception("Acceptance check failed: %s", e)
            return AcceptanceResponse(
                success=False,
                overall_result=CheckResult.FAIL,
                message=f"验收检查失败：{str(e)}",
                recommendation="manual_review",
            )

    def _create_check_items(self, request: AcceptanceRequest) -> List[AcceptanceCheckItem]:
        """根据验收标准创建检查项。"""
        check_items = []
        for i, criterion in enumerate(request.acceptance_criteria):
            check_type = self._analyze_criterion_type(criterion)
            item = AcceptanceCheckItem(
                criterion=criterion,
                check_type=check_type,
                config=self._extract_check_config(criterion, check_type),
            )
            check_items.append(item)

        if self.config.enable_content_quality_check:
            check_items.append(
                AcceptanceCheckItem(
                    criterion="内容质量检查",
                    check_type=CheckItemType.CUSTOM,
                    config={"type": "quality"},
                )
            )

        for custom_check in request.custom_checks:
            check_items.append(
                AcceptanceCheckItem(
                    criterion=custom_check.get("criterion", "自定义检查"),
                    check_type=CheckItemType(custom_check.get("check_type", "custom")),
                    config=custom_check.get("config", {}),
                )
            )
        return check_items

    def _analyze_criterion_type(self, criterion: str) -> CheckItemType:
        """分析验收标准的类型。"""
        criterion_lower = criterion.lower()
        if any(kw in criterion_lower for kw in ["格式", "format", "json", "xml", "csv"]):
            return CheckItemType.FORMAT_CHECK
        if any(kw in criterion_lower for kw in ["图片", "照片", "image", "photo"]):
            return CheckItemType.IMAGE_CHECK
        if any(kw in criterion_lower for kw in ["文件", "附件", "file", "document"]):
            return CheckItemType.FILE_CHECK
        if any(kw in criterion_lower for kw in ["包含", "必须出现", "关键词", "keyword"]):
            return CheckItemType.KEYWORD_CHECK
        return CheckItemType.TEXT_MATCH

    def _extract_check_config(self, criterion: str, check_type: CheckItemType) -> Dict[str, Any]:
        """从验收标准中提取检查配置。"""
        config = {}
        if check_type == CheckItemType.TEXT_MATCH:
            config["threshold"] = self.config.semantic_similarity_threshold
            config["method"] = "semantic"
        elif check_type == CheckItemType.KEYWORD_CHECK:
            keywords = self._extract_keywords_from_criterion(criterion)
            config["keywords"] = keywords
            config["match_all"] = "全部" in criterion or "all" in criterion.lower()
        elif check_type == CheckItemType.FORMAT_CHECK:
            for fmt in self.FORMAT_PATTERNS.keys():
                if fmt in criterion.lower():
                    config["format"] = fmt
                    break
        elif check_type == CheckItemType.IMAGE_CHECK:
            if "清晰" in criterion or "clear" in criterion.lower():
                config["min_quality"] = "high"
        return config

    def _extract_keywords_from_criterion(self, criterion: str) -> List[str]:
        """从验收标准中提取关键词。"""
        stopwords = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个"}
        chars = re.findall(r'[\u4e00-\u9fa5]|[a-zA-Z]+', criterion)
        words = []
        i = 0
        while i < len(chars):
            if chars[i] not in stopwords:
                for length in range(2, 5):
                    if i + length <= len(chars):
                        phrase = "".join(chars[i : i + length])
                        if len(phrase) >= 2:
                            words.append(phrase)
            i += 1
        return list(set(words))[:10]

    def _execute_check(self, item: AcceptanceCheckItem, request: AcceptanceRequest) -> None:
        """执行单个检查项。"""
        try:
            if item.check_type == CheckItemType.TEXT_MATCH:
                self._execute_text_match_check(item, request)
            elif item.check_type == CheckItemType.KEYWORD_CHECK:
                self._execute_keyword_check(item, request)
            elif item.check_type == CheckItemType.FORMAT_CHECK:
                self._execute_format_check(item, request)
            elif item.check_type == CheckItemType.IMAGE_CHECK:
                self._execute_image_check(item, request)
            elif item.check_type == CheckItemType.FILE_CHECK:
                self._execute_file_check(item, request)
            elif item.check_type == CheckItemType.CUSTOM:
                self._execute_custom_check(item, request)
        except Exception as e:
            logger.exception("Check execution failed: %s", e)
            item.result = CheckResult.FAIL
            item.details = f"检查执行失败：{str(e)}"

    def _execute_text_match_check(self, item: AcceptanceCheckItem, request: AcceptanceRequest) -> None:
        """执行文本匹配检查（语义相似度）。"""
        content = request.delivery_content
        criterion = item.criterion
        if not content or not criterion:
            item.result = CheckResult.FAIL
            item.details = "内容或验收标准为空"
            return
        similarity = self._calculate_semantic_similarity(content, criterion)
        item.score = similarity
        threshold = item.config.get("threshold", self.config.semantic_similarity_threshold)
        if similarity >= threshold:
            item.result = CheckResult.PASS
            item.details = f"语义相似度{similarity:.1%}，达到阈值{threshold:.1%}"
            item.evidence = self._find_matching_snippet(content, criterion)
        elif similarity >= threshold * 0.8:
            item.result = CheckResult.WARNING
            item.details = f"语义相似度{similarity:.1%}，接近阈值{threshold:.1%}"
        else:
            item.result = CheckResult.FAIL
            item.details = f"语义相似度{similarity:.1%}，未达到阈值{threshold:.1%}"

    def _execute_keyword_check(self, item: AcceptanceCheckItem, request: AcceptanceRequest) -> None:
        """执行关键词检查。"""
        content = request.delivery_content.lower()
        keywords = item.config.get("keywords", [])
        match_all = item.config.get("match_all", False)
        if not keywords:
            item.result = CheckResult.SKIPPED
            item.details = "未指定关键词"
            return
        matched = [kw for kw in keywords if kw.lower() in content]
        match_ratio = len(matched) / len(keywords) if keywords else 0
        item.score = match_ratio
        threshold = self.config.keyword_match_ratio
        if match_all:
            if len(matched) == len(keywords):
                item.result = CheckResult.PASS
                item.details = f"所有关键词均匹配 ({len(matched)}/{len(keywords)})"
            else:
                item.result = CheckResult.FAIL
                item.details = f"缺少关键词：{set(keywords) - set(matched)}"
        else:
            if match_ratio >= threshold:
                item.result = CheckResult.PASS
                item.details = f"关键词匹配率{match_ratio:.1%}，达到阈值{threshold:.1%}"
            elif match_ratio >= threshold * 0.5:
                item.result = CheckResult.WARNING
                item.details = f"关键词匹配率{match_ratio:.1%}，低于阈值{threshold:.1%}"
            else:
                item.result = CheckResult.FAIL
                item.details = f"关键词匹配率{match_ratio:.1%}，远低于阈值{threshold:.1%}"
        item.evidence = ", ".join(matched) if matched else ""

    def _execute_format_check(self, item: AcceptanceCheckItem, request: AcceptanceRequest) -> None:
        """执行格式检查。"""
        content = request.delivery_content
        fmt = item.config.get("format")
        if not fmt:
            item.result = CheckResult.SKIPPED
            item.details = "未指定格式类型"
            return
        pattern = self.FORMAT_PATTERNS.get(fmt)
        if not pattern:
            item.result = CheckResult.SKIPPED
            item.details = f"未知的格式类型：{fmt}"
            return
        if re.match(pattern, content.strip(), re.IGNORECASE):
            item.result = CheckResult.PASS
            item.details = f"内容格式符合 {fmt} 规范"
            item.score = 1.0
        else:
            item.result = CheckResult.FAIL
            item.details = f"内容格式不符合 {fmt} 规范"
            item.score = 0.0

    def _execute_image_check(self, item: AcceptanceCheckItem, request: AcceptanceRequest) -> None:
        """执行图片检查。"""
        attachments = request.delivery_attachments
        if not attachments:
            item.result = CheckResult.FAIL
            item.details = "未提供图片附件"
            item.score = 0.0
            return
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
        image_attachments = [
            att for att in attachments
            if any(att.lower().endswith(ext) for ext in image_extensions)
        ]
        if image_attachments:
            item.result = CheckResult.PASS
            item.details = f"找到 {len(image_attachments)} 个图片附件"
            item.score = 1.0
            item.evidence = ", ".join(image_attachments)
        else:
            item.result = CheckResult.WARNING
            item.details = "未检测到标准图片格式附件"
            item.score = 0.5

    def _execute_file_check(self, item: AcceptanceCheckItem, request: AcceptanceRequest) -> None:
        """执行文件检查。"""
        attachments = request.delivery_attachments
        if not attachments:
            item.result = CheckResult.FAIL
            item.details = "未提供任何附件"
            item.score = 0.0
            return
        required_file = item.config.get("required_file")
        if required_file:
            matched = [att for att in attachments if required_file.lower() in att.lower()]
            if matched:
                item.result = CheckResult.PASS
                item.details = f"找到必需文件：{matched[0]}"
                item.score = 1.0
            else:
                item.result = CheckResult.FAIL
                item.details = f"未找到必需文件：{required_file}"
                item.score = 0.0
        else:
            item.result = CheckResult.PASS
            item.details = f"找到 {len(attachments)} 个附件"
            item.score = 1.0

    def _execute_custom_check(self, item: AcceptanceCheckItem, request: AcceptanceRequest) -> None:
        """执行自定义检查（内容质量检查等）。"""
        check_type = item.config.get("type")
        if check_type == "quality":
            self._execute_quality_check(item, request)
        else:
            item.result = CheckResult.SKIPPED
            item.details = f"未知的自定义检查类型：{check_type}"

    def _execute_quality_check(self, item: AcceptanceCheckItem, request: AcceptanceRequest) -> None:
        """执行内容质量检查。"""
        content = request.delivery_content
        config = self.CONTENT_QUALITY_CONFIG

        issues = []
        score = 1.0

        # 检查字数
        word_count = len(content)
        if word_count < config["min_word_count"]:
            issues.append(f"字数{word_count}少于最小要求{config['min_word_count']}")
            score -= 0.2

        # 检查句子数
        sentence_count = len(re.split(r'[。！？.!?]', content))
        if sentence_count < config["min_sentence_count"]:
            issues.append(f"句子数{sentence_count}少于最小要求{config['min_sentence_count']}")
            score -= 0.2

        # 检查重复率
        words = content.split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < (1 - config["max_repetition_ratio"]):
                issues.append(f"内容重复率过高 (唯一词比例{unique_ratio:.1%})")
                score -= 0.2

        # 检查标点符号
        has_punctuation = any(p in content for p in config["required_punctuation"])
        if not has_punctuation:
            issues.append("内容缺少标点符号")
            score -= 0.1

        item.score = max(0, score)
        item.evidence = f"字数:{word_count}, 句子数:{sentence_count}"

        if not issues:
            item.result = CheckResult.PASS
            item.details = "内容质量良好"
        elif len(issues) == 1:
            item.result = CheckResult.WARNING
            item.details = "内容质量一般：" + "; ".join(issues)
        else:
            item.result = CheckResult.FAIL
            item.details = "内容质量差：" + "; ".join(issues)

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的语义相似度。
        简化实现：使用 Jaccard 相似度 + 重叠词比例。
        生产环境应使用 sentence transformer 等嵌入模型。
        """
        if not text1 or not text2:
            return 0.0

        # 分词（简化版）
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))

        if not words1 or not words2:
            return 0.0

        # Jaccard 相似度
        intersection = words1 & words2
        union = words1 | words2
        jaccard = len(intersection) / len(union) if union else 0.0

        # 重叠词比例（更关注短句种的完全匹配）
        overlap_ratio = len(intersection) / min(len(words1), len(words2))

        # 综合得分（Jaccard 占 60%，重叠比占 40%）
        similarity = 0.6 * jaccard + 0.4 * overlap_ratio
        return min(similarity, 1.0)

    def _tokenize(self, text: str) -> List[str]:
        """简单的文本分词。"""
        # 中文字符按字分，英文按空格分
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]+', text)
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        return list(chinese_chars) + english_words

    def _find_matching_snippet(self, content: str, criterion: str, max_length: int = 50) -> Optional[str]:
        """查找内容中与验收标准最匹配的片段。"""
        words = self._tokenize(criterion)
        if not words:
            return None

        # 查找包含最多关键词的句子
        sentences = re.split(r'[。！？.!?]', content)
        best_snippet = ""
        best_score = 0

        for sentence in sentences:
            sentence_words = set(self._tokenize(sentence))
            match_count = sum(1 for w in words if w in sentence_words)
            if match_count > best_score:
                best_score = match_count
                best_snippet = sentence[:max_length]

        return best_snippet if best_snippet else None

    def _create_report(self, request: AcceptanceRequest, check_items: List[AcceptanceCheckItem]) -> AcceptanceReport:
        """创建验收报告。"""
        passed = sum(1 for item in check_items if item.result == CheckResult.PASS)
        failed = sum(1 for item in check_items if item.result == CheckResult.FAIL)
        warning = sum(1 for item in check_items if item.result == CheckResult.WARNING)
        skipped = sum(1 for item in check_items if item.result == CheckResult.SKIPPED)

        # 计算总体得分（排除跳过的项）
        valid_items = [item for item in check_items if item.result != CheckResult.SKIPPED]
        overall_score = sum(item.score for item in valid_items) / len(valid_items) if valid_items else 0.0

        # 确定总体结果
        if failed > 0 and self.config.strict_mode:
            overall_result = CheckResult.FAIL
        elif failed > len(valid_items) * 0.3:
            overall_result = CheckResult.FAIL
        elif warning > len(valid_items) * 0.3:
            overall_result = CheckResult.WARNING
        elif passed >= len(valid_items) * 0.8:
            overall_result = CheckResult.PASS
        else:
            overall_result = CheckResult.WARNING

        # 内容分析
        content_analysis = self._analyze_content(request.delivery_content)

        report = AcceptanceReport(
            task_id=request.task_id,
            worker_id=request.worker_id,
            submission_id=str(datetime.now().timestamp()),
            overall_result=overall_result,
            overall_score=round(overall_score, 2),
            confidence=self._calculate_confidence(check_items),
            check_items=check_items,
            passed_count=passed,
            failed_count=failed,
            warning_count=warning,
            ai_analysis=self._generate_ai_analysis(check_items, content_analysis),
            ai_recommendation="approve" if overall_result == CheckResult.PASS else "manual_review" if overall_result == CheckResult.WARNING else "reject",
            content_analysis=content_analysis,
        )
        return report

    def _analyze_content(self, content: str) -> Dict[str, Any]:
        """分析交付内容。"""
        words = content.split()
        sentences = re.split(r'[。！？.!?]', content)

        return {
            "word_count": len(content),
            "word_count_en": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "paragraph_count": len(content.split("\n\n")),
            "avg_sentence_length": len(content) / len(sentences) if sentences else 0,
            "unique_word_ratio": len(set(words)) / len(words) if words else 0,
        }

    def _calculate_confidence(self, check_items: List[AcceptanceCheckItem]) -> float:
        """计算 AI 置信度。"""
        if not check_items:
            return 0.0

        # 基于检查项数量和一致性计算置信度
        valid_items = [item for item in check_items if item.result != CheckResult.SKIPPED]
        if len(valid_items) < 2:
            return 0.5

        # 计算结果一致性
        results = [item.result.value for item in valid_items]
        result_counts = {r: results.count(r) for r in set(results)}
        max_count = max(result_counts.values())
        consistency = max_count / len(results)

        # 置信度 = 基础置信度 + 检查项数量奖励 + 一致性奖励
        base_confidence = 0.6
        quantity_bonus = min(0.2, len(valid_items) * 0.05)
        consistency_bonus = consistency * 0.2

        return min(base_confidence + quantity_bonus + consistency_bonus, 1.0)

    def _generate_ai_analysis(self, check_items: List[AcceptanceCheckItem], content_analysis: Dict[str, Any]) -> str:
        """生成 AI 分析报告。"""
        passed = sum(1 for item in check_items if item.result == CheckResult.PASS)
        failed = sum(1 for item in check_items if item.result == CheckResult.FAIL)
        warning = sum(1 for item in check_items if item.result == CheckResult.WARNING)

        analysis = f"本次验收共执行 {len(check_items)} 项检查，"
        analysis += f"其中 {passed} 项通过，{failed} 项失败，{warning} 项警告。"

        if content_analysis.get("word_count", 0) < 50:
            analysis += " 交付内容字数偏少，建议补充更多细节。"
        if content_analysis.get("unique_word_ratio", 1) < 0.5:
            analysis += " 内容重复率较高，建议提高内容多样性。"

        failed_items = [item for item in check_items if item.result == CheckResult.FAIL]
        if failed_items:
            analysis += " 失败项：" + ", ".join(item.criterion for item in failed_items)

        return analysis

    def _generate_recommendation(self, report: AcceptanceReport) -> str:
        """生成验收建议。"""
        if report.overall_result == CheckResult.PASS and report.confidence >= 0.8:
            return "approve"
        elif report.overall_result == CheckResult.FAIL:
            return "reject"
        else:
            return "manual_review"

    def _generate_message(self, report: AcceptanceReport, recommendation: str) -> str:
        """生成响应消息。"""
        rec_map = {
            "approve": "建议自动通过验收",
            "reject": "建议拒绝，交付内容未达验收标准",
            "manual_review": "建议人工复核，AI 无法确定是否达标",
        }
        return f"验收完成：{report.passed_count}项通过/{report.failed_count}项失败/{report.warning_count}项警告。{rec_map.get(recommendation, '')}"

    def get_report(self, report_id: str) -> Optional[AcceptanceReport]:
        """获取验收报告。"""
        return self._reports.get(report_id)

    def get_reports_by_task(self, task_id: str) -> List[AcceptanceReport]:
        """获取任务的所有验收报告。"""
        report_ids = self._task_reports.get(task_id, [])
        return [self._reports[rid] for rid in report_ids if rid in self._reports]


# 全局单例
intelligent_acceptance_service = IntelligentAcceptanceService()