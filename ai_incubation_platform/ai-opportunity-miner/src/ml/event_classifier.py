"""
事件分类 ML 模型

使用机器学习对商业事件进行分类
支持规则引擎和 ML 模型混合分类
"""
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """事件类型"""
    # 融资事件
    FUNDING = "funding"
    # 并购事件
    M_A = "m_a"
    # IPO 事件
    IPO = "ipo"
    # 高管变动
    EXECUTIVE_CHANGE = "executive_change"
    # 产品发布
    PRODUCT_LAUNCH = "product_launch"
    # 战略合作
    PARTNERSHIP = "partnership"
    # 专利发布
    PATENT = "patent"
    # 负面新闻
    NEGATIVE_NEWS = "negative_news"
    # 扩张事件
    EXPANSION = "expansion"
    # 获奖事件
    AWARD = "award"
    # 未知事件
    UNKNOWN = "unknown"


@dataclass
class ClassifiedEvent:
    """已分类的事件"""
    id: str
    title: str
    content: str
    event_type: EventType
    confidence: float
    source: str
    source_url: str
    published_date: Optional[datetime]
    entities: Dict[str, str]
    keywords: List[str]
    sentiment: str
    created_at: datetime

    class Config:
        arbitrary_types_allowed = True


class EventClassifier:
    """
    事件分类器

    结合规则引擎和机器学习进行事件分类
    """

    def __init__(self):
        self._rules: Dict[EventType, List[re.Pattern]] = self._init_rules()
        self._keywords: Dict[EventType, List[str]] = self._init_keywords()
        self._model = None
        self._is_trained = False

    def _init_rules(self) -> Dict[EventType, List[re.Pattern]]:
        """初始化规则库"""
        rules = {
            EventType.FUNDING: [
                re.compile(r'获得.*(?:融资 | 轮投资)'),
                re.compile(r'(?:融资 | 投资 | 注资).*(?:\d+.*亿 | 万)'),
                re.compile(r'(?:完成 | 宣布).{0,30}(?:融资 | 轮投资)'),
                re.compile(r'领投 | 跟投 | 投资方'),
            ],
            EventType.M_A: [
                re.compile(r'(?:收购 | 并购 | 合并 | 兼并)'),
                re.compile(r'(?:全资 | 控股).{0,20}收购'),
            ],
            EventType.IPO: [
                re.compile(r'(?:上市 | IPO| 招股 | 挂牌)'),
                re.compile(r'(?:通过 | 提交).{0,30}上市申请'),
                re.compile(r'(?:科创板 | 创业板 | 主板 | 纳斯达克 | 港交所)'),
            ],
            EventType.EXECUTIVE_CHANGE: [
                re.compile(r'(?:任命 | 聘请 | 聘任).{0,20}(?:CEO|总裁 | 总经理 | 董事长)'),
                re.compile(r'(?:离职 | 卸任 | 辞去).{0,20}(?:CEO|总裁 | 总经理 | 董事长)'),
                re.compile(r'(?:高管 | 管理层).{0,20}(?:变动 | 调整)'),
            ],
            EventType.PRODUCT_LAUNCH: [
                re.compile(r'(?:发布 | 推出 | 上线).{0,20}(?:新产品 | 新品 | 服务)'),
                re.compile(r'(?:正式发布 | 隆重推出 | 首发)'),
            ],
            EventType.PARTNERSHIP: [
                re.compile(r'(?:合作 | 联手 | 携手 | 战略合作)'),
                re.compile(r'(?:达成 | 签署).{0,30}(?:合作协议 | 战略合作)'),
            ],
            EventType.PATENT: [
                re.compile(r'(?:获得 | 申请 | 公布).{0,20}专利'),
                re.compile(r'(?:发明专利 | 实用新型 | 外观设计)'),
            ],
            EventType.NEGATIVE_NEWS: [
                re.compile(r'(?:涉嫌 | 调查 | 处罚 | 违规 | 诉讼 | 纠纷)'),
                re.compile(r'(?:裁员 | 倒闭 | 破产 | 资金链断裂)'),
            ],
            EventType.EXPANSION: [
                re.compile(r'(?:扩张 | 拓展 | 入驻 | 落地)'),
                re.compile(r'(?:新总部 | 新分公司 | 新门店 | 新中心)'),
            ],
            EventType.AWARD: [
                re.compile(r'(?:获得 | 荣获 | 斩获).{0,20}(?:奖项 | 大奖 | 荣誉)'),
                re.compile(r'(?:入选 | 上榜).{0,20}(?:榜单 | 500 强 | 独角兽)'),
            ],
        }
        return rules

    def _init_keywords(self) -> Dict[EventType, List[str]]:
        """初始化关键词库"""
        keywords = {
            EventType.FUNDING: [
                '融资', '投资', '注资', '轮投', '领投', '跟投', '投资方',
                '红杉', 'IDG', '高瓴', '腾讯投资', '阿里战投', '字节投资'
            ],
            EventType.M_A: [
                '收购', '并购', '合并', '兼并', '全资', '控股', '股权收购',
                '资产收购', '私有化', '要约收购'
            ],
            EventType.IPO: [
                '上市', 'IPO', '招股', '挂牌', '科创板', '创业板',
                '纳斯达克', '纽交所', '港交所', '主板'
            ],
            EventType.EXECUTIVE_CHANGE: [
                '任命', '离职', '卸任', '辞职', '高管', 'CEO', '总裁',
                '总经理', '董事长', '董事会', '管理层'
            ],
            EventType.PRODUCT_LAUNCH: [
                '发布', '推出', '上线', '新产品', '新品', '首发',
                '正式版', '公测', '内测'
            ],
            EventType.PARTNERSHIP: [
                '合作', '联手', '携手', '战略合作', '合作伙伴', '生态合作',
                '联合', '共建', '签署协议'
            ],
            EventType.PATENT: [
                '专利', '知识产权', '发明专利', '实用新型', '外观设计',
                '商标', '著作权', '软著'
            ],
            EventType.NEGATIVE_NEWS: [
                '涉嫌', '调查', '处罚', '违规', '诉讼', '纠纷', '裁员',
                '倒闭', '破产', '负面', '丑闻', '欺诈', '资金链'
            ],
            EventType.EXPANSION: [
                '扩张', '拓展', '入驻', '落地', '新总部', '分公司',
                '门店', '中心', '基地', '工厂'
            ],
            EventType.AWARD: [
                '获奖', '荣获', '斩获', '入选', '上榜', '榜单', '独角兽',
                '500 强', '最佳', '优秀', '领先'
            ],
        }
        return keywords

    def classify_by_rules(self, title: str, content: str = "") -> Tuple[EventType, float]:
        """基于规则分类事件"""
        text = f"{title} {content}".lower()

        scores = {}
        for event_type, patterns in self._rules.items():
            for pattern in patterns:
                if pattern.search(text):
                    scores[event_type] = scores.get(event_type, 0) + 1

        # 关键词加分
        for event_type, keywords in self._keywords.items():
            for kw in keywords:
                if kw.lower() in text:
                    scores[event_type] = scores.get(event_type, 0) + 0.5

        if not scores:
            return EventType.UNKNOWN, 0.0

        # 返回最高分的事件类型
        best_type = max(scores.keys(), key=lambda k: scores[k])
        confidence = min(1.0, scores[best_type] / 3)

        return best_type, confidence

    def _extract_entities(self, title: str, content: str) -> Dict[str, str]:
        """提取事件实体"""
        text = f"{title} {content}"
        entities = {}

        # 提取公司名
        company_patterns = [
            r'([A-Za-z0-9 一二三四五六七八九十]+(?: 公司 | 集团 | 科技 | 网络 | 有限 | 股份))',
        ]
        for pattern in company_patterns:
            try:
                matches = re.findall(pattern, text)
                if matches:
                    entities['company'] = matches[0]
                    break
            except:
                continue

        # 提取金额
        amount_patterns = [
            r'(\d+\.?\d* 亿 [美元人民币]?)',
            r'(\d+\.?\d* 万 [美元人民币]?)',
        ]
        for pattern in amount_patterns:
            try:
                matches = re.findall(pattern, text)
                if matches:
                    entities['amount'] = matches[0]
                    break
            except:
                continue

        return entities

    def _extract_keywords(self, title: str, content: str, event_type: EventType) -> List[str]:
        """提取关键词"""
        text = f"{title} {content}"
        keywords = []

        for kw in self._keywords.get(event_type, []):
            if kw.lower() in text.lower():
                keywords.append(kw)

        return keywords[:10]

    def _analyze_sentiment(self, title: str, content: str) -> str:
        """简单情感分析"""
        text = f"{title} {content}".lower()

        positive_words = ['成功', '领先', '突破', '增长', '优秀', '获奖', '首发', '创新', '战略', '重磅', '强势', '携手', '共赢']
        negative_words = ['涉嫌', '调查', '处罚', '违规', '诉讼', '纠纷', '裁员', '倒闭', '破产', '负面', '丑闻', '欺诈', '下滑', '亏损', '风险']

        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)

        if neg_count > pos_count:
            return "negative"
        elif pos_count > neg_count:
            return "positive"
        else:
            return "neutral"

    def classify(
        self,
        title: str,
        content: str = "",
        source: str = "",
        source_url: str = "",
        published_date: Optional[datetime] = None
    ) -> ClassifiedEvent:
        """分类单个事件"""
        import uuid

        event_type, confidence = self.classify_by_rules(title, content)
        entities = self._extract_entities(title, content)
        keywords = self._extract_keywords(title, content, event_type)
        sentiment = self._analyze_sentiment(title, content)

        return ClassifiedEvent(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            event_type=event_type,
            confidence=confidence,
            source=source,
            source_url=source_url,
            published_date=published_date or datetime.now(),
            entities=entities,
            keywords=keywords,
            sentiment=sentiment,
            created_at=datetime.now()
        )

    def classify_batch(self, events: List[Dict]) -> List[ClassifiedEvent]:
        """批量分类事件"""
        return [self.classify(**event) for event in events]

    def get_event_statistics(self, events: List[ClassifiedEvent]) -> Dict[str, Any]:
        """获取事件统计信息"""
        from collections import defaultdict

        type_count = defaultdict(int)
        sentiment_count = defaultdict(int)

        for event in events:
            type_count[event.event_type.value] += 1
            sentiment_count[event.sentiment] += 1

        return {
            "total_events": len(events),
            "by_type": dict(type_count),
            "by_sentiment": dict(sentiment_count),
            "avg_confidence": sum(e.confidence for e in events) / len(events) if events else 0
        }


event_classifier = EventClassifier()
