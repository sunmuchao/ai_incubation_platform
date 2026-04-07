"""
SEO 服务实现
"""
from typing import List, Dict, Optional
import re
from collections import Counter
from schemas.seo import SEOAnalysisRequest, SEOAnalysisResult, SEOKeywordSuggestion, SEOTipsResponse
from core.config import settings
from data_sources import keyword_adapter
import logging

logger = logging.getLogger(__name__)


class SEOService:
    """SEO 优化服务"""

    def __init__(self):
        self._stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '与', '也', '很', '都',
            '要', '会', '对', '来说', '这个', '那个', '这些', '那些', '可以', '就是', '还有',
            '因为', '所以', '但是', '而且', '如果', '那么', '虽然', '但是', '一个', '一些'
        }
        self._seo_tips = {
            "content": [
                "内容长度建议 1000 字以上，至少不低于 300 字",
                "关键词密度保持在 1-3% 之间，避免堆砌",
                "第一段和最后一段自然融入目标关键词",
                "内容要具有原创性和价值，避免抄袭",
                "使用简洁明了的语言，易于阅读和理解"
            ],
            "structure": [
                "使用 H1/H2/H3 标签清晰组织内容结构",
                "每个页面只有一个 H1 标签",
                "H2 标签用于主要章节，H3 用于子章节",
                "使用段落分隔内容，避免大段文字",
                "适当使用列表、表格等结构化内容"
            ],
            "meta": [
                "确保标题包含目标关键词，长度控制在 50-60 字符",
                "Meta 描述要吸引人且包含关键词，长度 150-160 字符",
                "URL 简短且包含关键词，使用连字符分隔",
                "图片添加包含关键词的 alt 属性",
                "合理使用标签和分类"
            ],
            "technical": [
                "确保页面加载速度在 3 秒以内",
                "网站适配移动端设备，响应式设计",
                "使用 HTTPS 协议",
                "优化网站内部链接结构",
                "添加合适的外部引用链接",
                "创建 XML 网站地图"
            ],
            "user_experience": [
                "降低页面跳出率，提高用户停留时间",
                "提升内容可读性，使用合适的字体和行高",
                "添加相关内容推荐，增加页面浏览深度",
                "确保网站导航清晰易用",
                "减少不必要的弹窗和广告"
            ]
        }

    def analyze_content(self, request: SEOAnalysisRequest) -> SEOAnalysisResult:
        """分析内容 SEO"""
        content = request.content
        target_keywords = request.target_keywords

        # 内容基础分析
        word_count = self._count_words(content)
        words = self._tokenize(content)

        # 关键词密度分析
        keyword_density = {}
        for kw in target_keywords:
            count = content.lower().count(kw.lower())
            keyword_density[kw] = round(count / max(word_count, 1) * 100, 2)

        # 可读性分析
        readability_score = self._calculate_readability(content, word_count)

        # 生成建议和问题
        suggestions = []
        issues = []
        strengths = []

        # 内容长度检查
        if word_count >= 1000:
            strengths.append("内容长度充足，有利于SEO")
        elif word_count >= 500:
            suggestions.append("内容长度尚可，建议进一步丰富到1000字以获得更好排名")
        else:
            issues.append(f"内容长度过短（{word_count}字），建议至少达到300字，最好1000字以上")

        # 关键词密度检查
        all_density_ok = True
        for kw, density in keyword_density.items():
            if density < settings.MIN_KEYWORD_DENSITY:
                issues.append(f"关键词 '{kw}' 密度过低（{density}%），建议适当增加出现频率")
                all_density_ok = False
            elif density > settings.MAX_KEYWORD_DENSITY:
                issues.append(f"关键词 '{kw}' 密度过高（{density}%），可能被搜索引擎视为堆砌")
                all_density_ok = False
            elif settings.OPTIMAL_KEYWORD_DENSITY_MIN <= density <= settings.OPTIMAL_KEYWORD_DENSITY_MAX:
                strengths.append(f"关键词 '{kw}' 密度合理（{density}%）")

        if all_density_ok and keyword_density:
            strengths.append("所有关键词密度都在合理范围内")

        # 标题检查
        if request.title:
            title_words = self._tokenize(request.title)
            has_keyword = any(kw.lower() in request.title.lower() for kw in target_keywords)
            if has_keyword:
                strengths.append("标题包含目标关键词")
            else:
                issues.append("标题未包含目标关键词")

            if 50 <= len(request.title) <= 60:
                strengths.append("标题长度符合最佳实践（50-60字符）")
            else:
                suggestions.append(f"标题长度建议控制在50-60字符，当前为{len(request.title)}字符")

        # Meta描述检查
        if request.meta_description:
            has_keyword = any(kw.lower() in request.meta_description.lower() for kw in target_keywords)
            if has_keyword:
                strengths.append("Meta描述包含目标关键词")
            else:
                issues.append("Meta描述未包含目标关键词")

            if 150 <= len(request.meta_description) <= 160:
                strengths.append("Meta描述长度符合最佳实践（150-160字符）")
            else:
                suggestions.append(f"Meta描述长度建议控制在150-160字符，当前为{len(request.meta_description)}字符")

        # 内容结构检查
        heading_tags = re.findall(r'<h[1-6][^>]*>', content.lower())
        if heading_tags:
            h1_count = sum(1 for tag in heading_tags if 'h1' in tag)
            if h1_count == 1:
                strengths.append("页面有且仅有一个H1标签")
            elif h1_count > 1:
                issues.append(f"页面有多个H1标签（{h1_count}个），建议只保留一个")
            else:
                issues.append("页面缺少H1标签")
            strengths.append(f"页面使用了合理的标题标签结构，共{len(heading_tags)}个标题")
        else:
            suggestions.append("建议使用H1-H3标签组织内容结构，提升可读性和SEO效果")

        # 计算总分
        overall_score = self._calculate_overall_score(
            word_count,
            keyword_density,
            readability_score,
            len(issues),
            len(strengths)
        )

        return SEOAnalysisResult(
            overall_score=overall_score,
            keyword_density=keyword_density,
            content_length=word_count,
            readability_score=readability_score,
            suggestions=suggestions,
            issues=issues,
            strengths=strengths
        )

    def get_keyword_suggestions(self, seed_keywords: List[str]) -> List[SEOKeywordSuggestion]:
        """获取关键词建议"""
        # 使用可替换的数据源适配器（mock/第三方均可降级）
        suggestions = keyword_adapter.get_keyword_suggestions(seed_keywords)
        return [
            SEOKeywordSuggestion(
                keyword=s["keyword"],
                search_volume=int(s.get("search_volume", 0)),
                competition=float(s.get("competition", 0.0)),
                difficulty=float(s.get("difficulty", 0.0)),
                relevance=float(s.get("relevance", 0.0)),
            )
            for s in suggestions
        ][:20]

    def get_seo_tips(self) -> SEOTipsResponse:
        """获取SEO优化建议"""
        all_tips = []
        for tips in self._seo_tips.values():
            all_tips.extend(tips)

        return SEOTipsResponse(
            tips=all_tips,
            categories=self._seo_tips
        )

    def _count_words(self, text: str) -> int:
        """计算中文字数"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 统计中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        # 统计英文单词
        english_words = re.findall(r'[a-zA-Z]+', text)
        return len(chinese_chars) + len(english_words)

    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        words = []
        current = ""

        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                # 中文字符单独成词
                if current:
                    if current not in self._stop_words:
                        words.append(current)
                    current = ""
                words.append(char)
            elif char.isalpha():
                current += char.lower()
            else:
                if current and current not in self._stop_words:
                    words.append(current)
                current = ""

        if current and current not in self._stop_words:
            words.append(current)

        return words

    def _calculate_readability(self, content: str, word_count: int) -> float:
        """计算可读性分数"""
        if word_count == 0:
            return 0.0

        # 平均句长
        sentences = re.split(r'[。！？.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_sentence_length = word_count / max(len(sentences), 1)

        # 段落数
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        avg_paragraph_length = word_count / max(len(paragraphs), 1)

        # 评分
        score = 100.0

        # 句长惩罚
        if avg_sentence_length > 25:
            score -= min(20, (avg_sentence_length - 25) * 2)
        elif avg_sentence_length < 8:
            score -= min(10, (8 - avg_sentence_length) * 1.5)

        # 段落长度惩罚
        if avg_paragraph_length > 200:
            score -= min(20, (avg_paragraph_length - 200) * 0.1)
        elif avg_paragraph_length < 30:
            score -= min(10, (30 - avg_paragraph_length) * 0.3)

        # 标点符号丰富度
        punctuation_count = len(re.findall(r'[，。、；：""''（）【】《》,.;:\'\"()\[\]<>]', content))
        punctuation_density = punctuation_count / max(word_count, 1)
        if punctuation_density < 0.05:
            score -= min(15, (0.05 - punctuation_density) * 500)

        return max(0.0, round(score, 1))

    def _calculate_overall_score(
        self,
        word_count: int,
        keyword_density: Dict[str, float],
        readability_score: float,
        issue_count: int,
        strength_count: int
    ) -> float:
        """计算整体SEO分数"""
        score = 0.0

        # 内容长度权重 30%
        if word_count >= 1000:
            score += 30
        elif word_count >= 800:
            score += 25
        elif word_count >= 500:
            score += 20
        elif word_count >= 300:
            score += 15
        else:
            score += max(0, 10 * word_count / 300)

        # 关键词密度权重 30%
        if keyword_density:
            optimal_count = sum(
                1 for d in keyword_density.values()
                if settings.OPTIMAL_KEYWORD_DENSITY_MIN <= d <= settings.OPTIMAL_KEYWORD_DENSITY_MAX
            )
            total_keywords = len(keyword_density)
            score += 30 * (optimal_count / total_keywords)
        else:
            score += 10  # 没有提供关键词的基础分

        # 可读性权重 20%
        score += 20 * (readability_score / 100)

        # 问题和优势 20%
        score += max(0, 10 - issue_count * 2)  # 每个问题扣2分，最多扣10分
        score += min(10, strength_count * 2)   # 每个优势加2分，最多加10分

        return round(min(100.0, max(0.0, score)), 1)


# 全局服务实例
seo_service = SEOService()
