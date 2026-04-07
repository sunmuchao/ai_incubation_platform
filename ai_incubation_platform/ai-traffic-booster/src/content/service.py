"""
内容优化服务实现
"""
from typing import List, Dict
import random
import re
from schemas.content import (
    ContentOptimizationRequest,
    ContentOptimizationResult,
    ContentGenerationRequest,
    ContentGenerationResult,
    ContentType,
    ContentTone
)
from seo.service import seo_service
from schemas.seo import SEOAnalysisRequest
import logging

logger = logging.getLogger(__name__)


class ContentService:
    """内容优化服务"""

    def __init__(self):
        self._synonym_dict = {
            "很好": ["优秀", "出色", "优异", "卓越", "杰出", "很棒"],
            "不错": ["良好", "挺好", "还可以", "不赖", "令人满意"],
            "使用": ["使用", "利用", "采用", "运用", "借助"],
            "方法": ["方法", "方式", "手段", "途径", "策略"],
            "重要": ["重要", "关键", "核心", "主要", "首要"],
            "优秀": ["出色", "卓越", "杰出", "优异", "优秀"],
            "提升": ["提升", "提高", "增强", "加强", "改进"],
            "增加": ["增加", "提升", "提高", "增多", "扩充"],
            "减少": ["减少", "降低", "削减", "减轻", "缩短"],
            "改善": ["改善", "改进", "优化", "完善", "升级"],
            "实现": ["实现", "达成", "完成", "达到", "取得"],
            "提供": ["提供", "供给", "供应", "给予", "呈现"],
            "支持": ["支持", "支撑", "赞同", "拥护", " backing"],
            "发展": ["发展", "进展", "进步", "成长", "演进"],
            "效果": ["效果", "成效", "成果", "结果", "效应"]
        }

        self._title_templates = {
            ContentType.ARTICLE: [
                "{keyword}完全指南：从入门到精通",
                "2024年最新{keyword}技巧大全",
                "深度解析：{keyword}的原理与应用",
                "{keyword}常见问题及解决方案汇总",
                "如何高效使用{keyword}：实战经验分享"
            ],
            ContentType.BLOG_POST: [
                "我为什么推荐你使用{keyword}？",
                "{keyword}踩坑记：这些错误别再犯了",
                "{keyword}的{number}个隐藏功能，你知道几个？",
                "从0到1：{keyword}入门完全指南",
                "{keyword}对比：哪款更适合你？"
            ],
            ContentType.PRODUCT_DESCRIPTION: [
                "{keyword}：为{audience}打造的专业解决方案",
                "全新{keyword}，{benefit}从未如此简单",
                "{keyword} - {feature}，{benefit}的最佳选择",
                "选择{keyword}的{number}大理由",
                "{keyword}：{benefit}黑科技，颠覆你的想象"
            ],
            ContentType.SOCIAL_MEDIA: [
                "🔥 必看！{keyword}的正确打开方式",
                "💡 {keyword}小技巧，让你效率翻倍",
                "⚠️ 使用{keyword}一定要注意这几点",
                "🚀 {keyword}最新玩法，赶紧收藏",
                "😭 用了{keyword}才知道，以前都白费劲了"
            ]
        }

    def optimize_content(self, request: ContentOptimizationRequest) -> ContentOptimizationResult:
        """优化内容"""
        # 先分析原始内容SEO
        seo_request = SEOAnalysisRequest(
            content=request.content,
            target_keywords=request.target_keywords
        )
        original_analysis = seo_service.analyze_content(seo_request)
        original_score = original_analysis.overall_score

        # 生成优化后的内容
        optimized_content = self._generate_optimized_content(request)

        # 分析优化后内容SEO
        optimized_seo_request = SEOAnalysisRequest(
            content=optimized_content,
            target_keywords=request.target_keywords
        )
        optimized_analysis = seo_service.analyze_content(optimized_seo_request)
        optimized_score = optimized_analysis.overall_score

        # 生成修改说明
        changes = self._generate_change_summary(
            request.content,
            optimized_content,
            original_analysis,
            optimized_analysis
        )

        # 计算关键词密度改进
        keyword_improvements = {}
        for kw in request.target_keywords:
            original_density = original_analysis.keyword_density.get(kw, 0)
            optimized_density = optimized_analysis.keyword_density.get(kw, 0)
            keyword_improvements[kw] = round(optimized_density - original_density, 2)

        # 生成进一步优化建议
        suggestions = []
        if optimized_score < 80:
            suggestions.extend(optimized_analysis.suggestions)
        else:
            suggestions.append("内容SEO质量优秀，可直接发布")
            suggestions.append("建议配合图片和视频等多媒体内容提升用户体验")
            suggestions.append("可以考虑定期更新内容，保持信息时效性")

        return ContentOptimizationResult(
            original_score=original_score,
            optimized_score=optimized_score,
            optimized_content=optimized_content,
            changes=changes,
            suggestions=suggestions,
            keyword_improvements=keyword_improvements
        )

    def generate_content(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        """生成内容"""
        # 生成标题
        title = self._generate_title(request)

        # 生成大纲
        outline = request.outline or self._generate_outline(request)

        # 生成内容
        content = self._generate_content_body(request, outline)

        # 生成Meta描述
        meta_description = self._generate_meta_description(title, request.target_keywords)

        # 分析SEO分数
        seo_request = SEOAnalysisRequest(
            content=content,
            target_keywords=request.target_keywords,
            title=title,
            meta_description=meta_description
        )
        seo_analysis = seo_service.analyze_content(seo_request)

        return ContentGenerationResult(
            content=content,
            title=title,
            meta_description=meta_description,
            outline=outline,
            seo_score=seo_analysis.overall_score,
            keyword_density=seo_analysis.keyword_density,
            suggestions=seo_analysis.suggestions
        )

    def _generate_optimized_content(self, request: ContentOptimizationRequest) -> str:
        """生成优化后的内容"""
        content = request.content
        keywords = request.target_keywords

        # 1. 适当插入关键词（如果密度太低）
        for kw in keywords:
            count = content.lower().count(kw.lower())
            if count < 2:
                # 在开头插入
                first_paragraph_end = content.find('。')
                if first_paragraph_end != -1:
                    insert_pos = first_paragraph_end + 1
                    content = content[:insert_pos] + f" 本文将重点介绍{kw}的相关内容。" + content[insert_pos:]

                # 在结尾插入
                content += f"\n\n总体而言，{kw}在相关领域具有重要应用价值。"

        # 2. 同义词替换，增加内容丰富度
        words = list(content)
        i = 0
        while i < len(words):
            # 尝试匹配2字词
            if i + 1 < len(words):
                two_word = ''.join(words[i:i+2])
                if two_word in self._synonym_dict and random.random() < 0.3:
                    synonym = random.choice(self._synonym_dict[two_word])
                    words[i:i+2] = list(synonym)
                    i += len(synonym)
                    continue
            i += 1
        content = ''.join(words)

        # 3. 优化段落结构，增加小标题
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        if len(paragraphs) > 3 and not re.search(r'^#{1,3}\s', content):
            optimized_paragraphs = []
            for j, para in enumerate(paragraphs):
                if j > 0 and j % 3 == 0 and len(para) > 50:
                    # 添加小标题
                    kw = random.choice(keywords) if keywords else "内容"
                    optimized_paragraphs.append(f"### {kw}的第{j//3 + 1}个要点\n")
                optimized_paragraphs.append(para)
            content = '\n\n'.join(optimized_paragraphs)

        # 4. 增加内容长度如果太短
        word_count = len(re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', content))
        if word_count < request.min_length if request.min_length else 300:
            additional_content = self._generate_additional_content(request, word_count)
            content += f"\n\n{additional_content}"

        return content

    def _generate_title(self, request: ContentGenerationRequest) -> str:
        """生成标题"""
        templates = self._title_templates.get(request.content_type, self._title_templates[ContentType.ARTICLE])
        template = random.choice(templates)

        main_keyword = request.target_keywords[0] if request.target_keywords else "内容"

        title = template.format(
            keyword=main_keyword,
            number=random.randint(5, 15),
            audience=request.target_audience or "用户",
            benefit=random.choice(["提升效率", "节省时间", "提高效果", "降低成本"]),
            feature=random.choice(["功能强大", "简单易用", "性能卓越", "安全可靠"])
        )

        return title

    def _generate_outline(self, request: ContentGenerationRequest) -> List[str]:
        """生成内容大纲"""
        main_keyword = request.target_keywords[0] if request.target_keywords else "主题"
        outline_count = min(6, max(3, request.length // 200))

        outline = [
            f"一、{main_keyword}概述",
            f"二、{main_keyword}的核心优势",
            f"三、{main_keyword}的应用场景"
        ]

        if outline_count >= 4:
            outline.append(f"四、{main_keyword}的使用方法和技巧")
        if outline_count >= 5:
            outline.append(f"五、{main_keyword}常见问题解答")
        if outline_count >= 6:
            outline.append(f"六、{main_keyword}未来发展趋势")

        return outline[:outline_count]

    def _generate_content_body(self, request: ContentGenerationRequest, outline: List[str]) -> str:
        """生成内容主体"""
        content_parts = []
        main_keyword = request.target_keywords[0] if request.target_keywords else "内容"
        length_per_section = request.length // len(outline)

        tone_prefixes = {
            ContentTone.PROFESSIONAL: "专业角度来看，",
            ContentTone.FRIENDLY: "大家好，今天我们来聊聊",
            ContentTone.CASUAL: "说到",
            ContentTone.AUTHORITATIVE: "根据行业研究表明，",
            ContentTone.PERSUASIVE: "如果你想要提升相关效果，那么",
            ContentTone.INFORMATIVE: "关于"
        }

        prefix = tone_prefixes.get(request.tone, tone_prefixes[ContentTone.INFORMATIVE])

        # 引言
        intro = f"{prefix}{main_keyword}，相信很多人都不陌生。在当今数字化时代，{main_keyword}已经成为了越来越多人关注的话题。本文将为大家详细介绍{main_keyword}的相关知识，希望对大家有所帮助。"
        content_parts.append(intro)

        # 每个大纲部分生成内容
        for section in outline:
            section_title = section.split('、', 1)[1] if '、' in section else section
            section_content = self._generate_section_content(
                section_title,
                request.target_keywords,
                length_per_section,
                request.tone
            )
            content_parts.append(f"\n## {section}\n\n{section_content}")

        # 结语
        conclusion = f"\n## 总结\n\n总的来说，{main_keyword}是一个非常有价值的领域，值得大家深入了解和学习。希望本文介绍的内容能够对大家有所启发，如果有任何问题或者想法，欢迎在评论区留言讨论。"
        content_parts.append(conclusion)

        return '\n\n'.join(content_parts)

    def _generate_section_content(self, title: str, keywords: List[str], length: int, tone: ContentTone) -> str:
        """生成章节内容"""
        main_kw = keywords[0] if keywords else "相关内容"
        content = []

        sentences = [
            f"{title}是{main_kw}领域中非常重要的一个方面。",
            f"很多人在接触{main_kw}的时候，首先会关注{title}的相关内容。",
            f"根据相关数据统计，重视{title}的用户通常能够获得更好的使用体验。",
            f"在实际应用中，{title}主要体现在以下几个方面：首先是功能层面，能够帮助用户解决实际问题；其次是体验层面，能够提升整体的使用感受；最后是价值层面，能够为用户创造实际的收益。",
            f"如果你想要更好地掌握{title}，建议多进行实践操作，在实际使用中积累经验。",
            f"目前市场上有很多关于{title}的教程和资料，大家可以根据自己的需求选择适合的学习路径。",
            f"值得注意的是，{title}并不是一成不变的，随着技术的发展和需求的变化，相关的内容也会不断更新和完善。",
            f"很多成功的案例都表明，合理利用{title}能够显著提升整体的效果和效率。"
        ]

        # 随机选择句子组合
        selected_sentences = random.sample(sentences, min(len(sentences), length // 50))
        content.extend(selected_sentences)

        # 插入其他关键词
        for kw in keywords[1:]:
            if random.random() > 0.5:
                content.append(f"此外，{kw}与{title}也有着密切的联系，在实际应用中需要综合考虑。")

        return ' '.join(content)

    def _generate_meta_description(self, title: str, keywords: List[str]) -> str:
        """生成Meta描述"""
        main_kw = keywords[0] if keywords else "内容"
        other_kws = '、'.join(keywords[1:3]) if len(keywords) > 1 else ""

        meta_templates = [
            f"本文详细介绍了{main_kw}{'，包括' + other_kws if other_kws else ''}的相关知识，帮助你快速掌握相关技巧，提升实际应用能力。",
            f"{title}。本文从多个角度深入解析{main_kw}的核心要点，提供实用的方法和建议，值得收藏。",
            f"想要了解{main_kw}的相关内容？这篇文章详细讲解了{main_kw}的原理、方法和应用场景，干货满满。"
        ]

        return random.choice(meta_templates)[:160]  # 控制在160字符以内

    def _generate_additional_content(self, request: ContentOptimizationRequest, current_length: int) -> str:
        """生成补充内容"""
        main_kw = request.target_keywords[0] if request.target_keywords else "内容"
        target_length = request.min_length if request.min_length else 500
        additional_needed = target_length - current_length

        additional_content = [
            f"除了前面提到的内容，{main_kw}还有很多值得深入探讨的方面。",
            f"在实际使用过程中，很多用户都会遇到各种各样的问题，这时候就需要我们具备一定的问题解决能力。",
            f"建议大家在学习{main_kw}的时候，多参考官方文档和权威资料，这样能够少走很多弯路。",
            f"同时，积极参与社区讨论，与其他用户交流经验，也是提升自己水平的好方法。",
            f"随着技术的不断发展，{main_kw}相关的功能和应用也在不断更新，我们需要保持学习的态度，跟上时代的步伐。",
            f"总的来说，{main_kw}是一个非常有前景的领域，投入时间和精力去学习是非常值得的。"
        ]

        return ' '.join(additional_content[:max(1, additional_needed // 50)])

    def _generate_change_summary(
        self,
        original: str,
        optimized: str,
        original_analysis,
        optimized_analysis
    ) -> List[Dict[str, str]]:
        """生成修改说明"""
        changes = []

        # 内容长度变化
        original_len = original_analysis.content_length
        optimized_len = optimized_analysis.content_length
        if optimized_len > original_len:
            changes.append({
                "type": "内容扩展",
                "description": f"内容长度从 {original_len} 字增加到 {optimized_len} 字，更有利于SEO"
            })

        # SEO分数变化
        score_improvement = optimized_analysis.overall_score - original_analysis.overall_score
        if score_improvement > 0:
            changes.append({
                "type": "SEO优化",
                "description": f"SEO分数从 {original_analysis.overall_score} 提升到 {optimized_analysis.overall_score}，提升了 {score_improvement} 分"
            })

        # 关键词优化
        for kw, original_density in original_analysis.keyword_density.items():
            optimized_density = optimized_analysis.keyword_density.get(kw, 0)
            if optimized_density > original_density and original_density < 1:
                changes.append({
                    "type": "关键词优化",
                    "description": f"关键词 '{kw}' 密度从 {original_density}% 提升到 {optimized_density}%，达到合理范围"
                })
            elif optimized_density < original_density and original_density > 5:
                changes.append({
                    "type": "关键词优化",
                    "description": f"关键词 '{kw}' 密度从 {original_density}% 降低到 {optimized_density}%，避免了关键词堆砌"
                })

        # 问题修复
        if original_analysis.issues and not optimized_analysis.issues:
            changes.append({
                "type": "问题修复",
                "description": f"修复了所有检测到的 {len(original_analysis.issues)} 个SEO问题"
            })
        elif len(optimized_analysis.issues) < len(original_analysis.issues):
            fixed_count = len(original_analysis.issues) - len(optimized_analysis.issues)
            changes.append({
                "type": "问题修复",
                "description": f"修复了 {fixed_count} 个SEO问题，剩余 {len(optimized_analysis.issues)} 个问题需要进一步优化"
            })

        # 结构优化
        original_has_headings = '<h' in original.lower() or '# ' in original
        optimized_has_headings = '<h' in optimized.lower() or '# ' in optimized
        if not original_has_headings and optimized_has_headings:
            changes.append({
                "type": "结构优化",
                "description": "添加了标题标签结构，提升内容可读性和SEO效果"
            })

        if not changes:
            changes.append({
                "type": "内容优化",
                "description": "对内容进行了同义词替换和表述优化，提升内容丰富度和可读性"
            })

        return changes


# 全局服务实例
content_service = ContentService()
