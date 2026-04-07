"""
文本分析器
用于从新闻和报告中提取关键信息、实体和情感分析
"""
from typing import List, Dict, Tuple
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

class TextAnalyzer:
    """文本分析器"""

    def __init__(self):
        # 加载关键词词典
        self.keyword_patterns = {
            "market_size": re.compile(r'(市场规模|营收规模|产值)\s*[达到约为]*\s*(\d+(\.\d+)?)\s*(亿|万元|美元|CNY|人民币)?'),
            "growth_rate": re.compile(r'(增长率|增速|同比增长|环比增长)\s*[达到约为]*\s*(\d+(\.\d+)?)\s*%'),
            "policy": re.compile(r'(政策|规划|指导意见|十四五|补贴|支持|鼓励|扶持)'),
            "technology": re.compile(r'(技术|专利|研发|突破|创新|迭代|升级|工艺|材料)'),
            "competition": re.compile(r'(竞争|市场份额|CR\d+|集中度|头部企业|龙头|竞品|竞争对手)'),
            "investment": re.compile(r'(投资|融资|并购|重组|上市|IPO|估值|PE|市盈率)'),
            "demand": re.compile(r'(需求|增长|爆发|旺盛|紧缺|供不应求|订单|产能)')
        }

        # 实体提取正则
        self.entity_patterns = {
            "company": re.compile(r'([^\s，。；：]+)(股份|有限责任|集团|公司|企业)'),
            "person": re.compile(r'([^\s，。；：]+)(先生|女士|博士|教授|CEO|董事长|总经理)'),
            "product": re.compile(r'([^\s，。；：]+)(产品|系统|平台|解决方案|服务)')
        }

    def extract_keywords(self, text: str, top_n: int = 10) -> List[Tuple[str, int]]:
        """提取关键词"""
        # 简单实现：统计高频词
        words = re.findall(r'[\w\u4e00-\u9fa5]+', text)
        # 过滤停用词（简化版）
        stop_words = set(['的', '是', '在', '和', '了', '有', '为', '对', '等', '可以', '通过', '根据', '目前', '相关', '进行'])
        filtered_words = [w for w in words if len(w) > 1 and w not in stop_words]
        counter = Counter(filtered_words)
        return counter.most_common(top_n)

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """提取实体"""
        entities = {
            "companies": [],
            "persons": [],
            "products": []
        }

        # 提取公司
        company_matches = self.entity_patterns["company"].findall(text)
        entities["companies"] = list(set([match[0] + match[1] for match in company_matches]))

        # 提取人物
        person_matches = self.entity_patterns["person"].findall(text)
        entities["persons"] = list(set([match[0] + match[1] for match in person_matches]))

        # 提取产品
        product_matches = self.entity_patterns["product"].findall(text)
        entities["products"] = list(set([match[0] + match[1] for match in product_matches]))

        return entities

    def extract_indicators(self, text: str) -> Dict[str, any]:
        """提取行业指标"""
        indicators = {}

        # 提取市场规模
        market_size_match = self.keyword_patterns["market_size"].search(text)
        if market_size_match:
            value = float(market_size_match.group(2))
            unit = market_size_match.group(4) or "亿"
            indicators["market_size"] = {
                "value": value,
                "unit": unit,
                "original": market_size_match.group(0)
            }

        # 提取增长率
        growth_rate_match = self.keyword_patterns["growth_rate"].search(text)
        if growth_rate_match:
            value = float(growth_rate_match.group(2))
            indicators["growth_rate"] = {
                "value": value / 100,
                "original": growth_rate_match.group(0)
            }

        # 提取标签
        tags = []
        for tag, pattern in self.keyword_patterns.items():
            if pattern.search(text):
                tags.append(tag)
        indicators["tags"] = tags

        return indicators

    def calculate_confidence(self, indicators: Dict, source_type: str) -> float:
        """计算信息置信度"""
        score = 0.0

        # 来源权重
        source_weights = {
            "government_data": 0.9,
            "industry_report": 0.8,
            "news": 0.6,
            "social_media": 0.4,
            "ai_analysis": 0.5
        }
        score += source_weights.get(source_type, 0.5) * 0.4

        # 指标完整性
        indicator_count = len([k for k in indicators.keys() if k != "tags"])
        score += min(indicator_count / 3.0, 1.0) * 0.3

        # 标签丰富度
        tag_count = len(indicators.get("tags", []))
        score += min(tag_count / 4.0, 1.0) * 0.3

        return min(score, 1.0)

    def extract_opportunity_signals(self, text: str) -> Dict:
        """提取商机信号"""
        signals = {
            "positive": [],
            "negative": [],
            "opportunity_type": []
        }

        # 正向信号
        positive_patterns = [
            (r'增长|上升|提高|增加|扩大|突破|爆发|旺盛|需求|利好|支持|鼓励', "positive"),
            (r'政策支持|补贴|规划|指导意见', "policy"),
            (r'技术突破|创新|专利|研发', "technology"),
            (r'市场规模|增长|需求旺盛', "market"),
            (r'投资|融资|并购', "investment")
        ]

        # 负向信号
        negative_patterns = [
            # 映射到风险标签中的 "market"：市场下行/竞争激烈/供过于求 等
            (r'下降|减少|萎缩|放缓|低迷|过剩|竞争激烈|价格战', "market"),
            (r'监管|限制|禁令|风险|挑战', "regulatory"),
            (r'技术瓶颈|壁垒高|人才短缺', "technological")
        ]

        for pattern, signal_type in positive_patterns:
            if re.search(pattern, text):
                if signal_type == "positive":
                    signals["positive"].append(pattern)
                else:
                    signals["opportunity_type"].append(signal_type)

        for pattern, signal_type in negative_patterns:
            if re.search(pattern, text):
                # 这里存放的是语义类别（如 regulatory/technological/market），
                # 供下游计算风险标签时按类别判断。
                signals["negative"].append(signal_type)

        return signals

text_analyzer = TextAnalyzer()
