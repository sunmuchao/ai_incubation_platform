"""
事件检测引擎
从文本中检测和分类商业事件，如融资、并购、产品发布、人事变动等
参考 CB Insights 的事件检测能力
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """事件类型定义"""
    # 融资相关
    FUNDING = "funding"  # 融资事件
    INVESTMENT = "investment"  # 投资事件
    IPO = "ipo"  # IPO/上市
    ACQUISITION = "acquisition"  # 并购/收购

    # 产品/技术相关
    PRODUCT_LAUNCH = "product_launch"  # 产品发布
    TECHNOLOGY_BREAKTHROUGH = "technology_breakthrough"  # 技术突破
    PATENT = "patent"  # 专利申请/授权

    # 企业运营相关
    PARTNERSHIP = "partnership"  # 战略合作
    EXPANSION = "expansion"  # 业务扩张
    LAYOFF = "layoff"  # 裁员
    BANKRUPTCY = "bankruptcy"  # 破产

    # 人事相关
    EXECUTIVE_CHANGE = "executive_change"  # 高管变动
    NEW_HIRE = "new_hire"  # 重要招聘

    # 政策/监管相关
    POLICY_CHANGE = "policy_change"  # 政策变化
    REGULATORY_ACTION = "regulatory_action"  # 监管行动

    # 市场相关
    MARKET_ENTRY = "market_entry"  # 进入新市场
    PRICE_CHANGE = "price_change"  # 价格调整


class EventSeverity(str, Enum):
    """事件重要性等级"""
    LOW = "low"  # 低重要性
    MEDIUM = "medium"  # 中等重要性
    HIGH = "high"  # 高重要性
    CRITICAL = "critical"  # 关键事件


class BusinessEvent:
    """商业事件模型"""

    def __init__(
        self,
        event_type: EventType,
        title: str,
        summary: str,
        companies: List[str] = None,
        persons: List[str] = None,
        amount: Optional[float] = None,
        currency: str = "CNY",
        publish_date: Optional[datetime] = None,
        source: str = "",
        source_url: str = "",
        severity: EventSeverity = EventSeverity.MEDIUM,
        confidence: float = 0.8,
        raw_text: str = "",
        extra: Dict = None
    ):
        self.id = f"{event_type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.event_type = event_type
        self.title = title
        self.summary = summary
        self.companies = companies or []
        self.persons = persons or []
        self.amount = amount
        self.currency = currency
        self.publish_date = publish_date or datetime.now()
        self.source = source
        self.source_url = source_url
        self.severity = severity
        self.confidence = confidence
        self.raw_text = raw_text
        self.extra = extra or {}
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "title": self.title,
            "summary": self.summary,
            "companies": self.companies,
            "persons": self.persons,
            "amount": self.amount,
            "currency": self.currency,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "source": self.source,
            "source_url": self.source_url,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat()
        }


class EventDetector:
    """事件检测器"""

    def __init__(self):
        # 事件类型关键词模式
        self.event_patterns = {
            EventType.FUNDING: {
                "keywords": [
                    r'融资\s*(\d+(\.\d+)?)?\s*(亿 | 万 | 美元 | 人民币)?',
                    r'获得\s*(投资 | 融资)',
                    r'(天使轮 |A 轮 |B 轮 |C 轮 |D 轮 |E 轮 | Pre-IPO| 战略融资)',
                    r'领投\s*(\d+(\.\d+)?)?\s*(亿 | 万)?',
                    r'跟投\s*(\d+(\.\d+)?)?\s*(亿 | 万)?',
                    r'完成\s*(\d+(\.\d+)?)?\s*(亿 | 万)\s*(元 | 美元)?\s*融资',
                ],
                "severity_keywords": [
                    (r'数亿 | 数十亿 | 超\d+亿', EventSeverity.CRITICAL),
                    (r'\d+亿美元', EventSeverity.HIGH),
                    (r'\d+亿人民币', EventSeverity.HIGH),
                    (r'\d+亿元', EventSeverity.MEDIUM),
                    (r'\d+万元', EventSeverity.LOW),
                ]
            },
            EventType.ACQUISITION: {
                "keywords": [
                    r'收购\s*(\d+%)?',
                    r'并购',
                    r'被\s*\S+\s*收购',
                    r'全资收购',
                    r'控股\s*(\d+%)?',
                    r'战略投资\s*(\d+%)?',
                    r'并购重组',
                ],
                "severity_keywords": [
                    (r'全资收购 |100% 收购 | 控股', EventSeverity.HIGH),
                    (r'战略投资 | 少数股权', EventSeverity.MEDIUM),
                ]
            },
            EventType.IPO: {
                "keywords": [
                    r'IPO',
                    r'上市',
                    r'招股书',
                    r'过会',
                    r'科创板',
                    r'创业板',
                    r'纳斯达克',
                    r'纽交所',
                    r'港交所',
                    r'挂牌交易',
                ],
                "severity_keywords": [
                    (r'成功上市 | 正式挂牌', EventSeverity.CRITICAL),
                    (r'提交招股书 | 过会', EventSeverity.HIGH),
                    (r'拟上市 | 计划 IPO', EventSeverity.MEDIUM),
                ]
            },
            EventType.PRODUCT_LAUNCH: {
                "keywords": [
                    r'发布\s*(新 | 首款 | 新一代)?\s*产品',
                    r'推出\s*(新 | 首款)?\s*(产品 | 服务 | 平台 | 系统)',
                    r'正式上线',
                    r'发布会',
                    r'新品发布',
                ],
                "severity_keywords": [
                    (r'首款 | 革命性 | 突破性', EventSeverity.HIGH),
                    (r'新一代 | 重大升级', EventSeverity.MEDIUM),
                    (r'小升级 | 迭代', EventSeverity.LOW),
                ]
            },
            EventType.TECHNOLOGY_BREAKTHROUGH: {
                "keywords": [
                    r'技术突破',
                    r'重大进展',
                    r'研发成功',
                    r'专利申请',
                    r'获得专利',
                    r'技术创新',
                    r'填补空白',
                    r'国际领先',
                ],
                "severity_keywords": [
                    (r'国际领先 | 填补空白 | 首创', EventSeverity.CRITICAL),
                    (r'重大突破 | 核心技术', EventSeverity.HIGH),
                    (r'技术升级 | 改进', EventSeverity.MEDIUM),
                ]
            },
            EventType.PARTNERSHIP: {
                "keywords": [
                    r'战略合作',
                    r'签署协议',
                    r'达成合作',
                    r'联合\s*(开发 | 发布 | 推出)',
                    r'生态合作',
                    r'战略联盟',
                ],
                "severity_keywords": [
                    (r'战略合作 | 深度合 | 独家合作', EventSeverity.HIGH),
                    (r'一般合作 | 框架协', EventSeverity.MEDIUM),
                ]
            },
            EventType.EXECUTIVE_CHANGE: {
                "keywords": [
                    r'任命\s*(CEO| 总裁 | 董事长 | 总经理 |CFO|CTO)',
                    r'(CEO| 总裁 | 董事长 | 总经理)\s*(离职 | 卸任 | 辞去)',
                    r'新任\s*(CEO| 总裁 | 董事长)',
                    r'创始人\s*(卸任 | 退出)',
                    r'高管\s*(变动 | 调整)',
                ],
                "severity_keywords": [
                    (r'创始人 | 董事长|CEO', EventSeverity.HIGH),
                    (r'高管 | 总裁 | 总经理', EventSeverity.MEDIUM),
                ]
            },
            EventType.POLICY_CHANGE: {
                "keywords": [
                    r'发布\s*(政策 | 规定 | 办法 | 意见)',
                    r'(政策 | 规定)\s*(出台 | 实施 | 生效)',
                    r'工信部 | 发改委 | 市场监管总局',
                    r'十四五\s*规划',
                    r'产业\s*(政策 | 指导)',
                ],
                "severity_keywords": [
                    (r'国家级 | 国务院 | 重磅', EventSeverity.CRITICAL),
                    (r'部委 | 省级', EventSeverity.HIGH),
                    (r'地方 | 市级', EventSeverity.MEDIUM),
                ]
            },
            EventType.EXPANSION: {
                "keywords": [
                    r'扩张',
                    r'新建\s*(工厂 | 基地 | 中心)',
                    r'产能\s*(扩张 | 提升 | 翻倍)',
                    r'进军\s*(新市场 | 海外)',
                    r'开设\s*(分公司 | 门店)',
                ],
                "severity_keywords": [
                    (r'海外扩张 | 全球布局', EventSeverity.HIGH),
                    (r'产能翻倍 | 大规模', EventSeverity.HIGH),
                    (r'新建 | 扩张', EventSeverity.MEDIUM),
                ]
            },
            EventType.LAYOFF: {
                "keywords": [
                    r'裁员',
                    r'优化\s*(人员 | 组织)',
                    r'人员\s*(缩减 | 调整)',
                    r'降薪',
                    r'业务\s*(收缩 | 调整)',
                ],
                "severity_keywords": [
                    (r'大规模裁员 | 裁员\d+%| 裁员\d+人', EventSeverity.CRITICAL),
                    (r'人员优化 | 组织调整', EventSeverity.MEDIUM),
                ]
            },
        }

        # 金额提取模式
        self.amount_patterns = [
            re.compile(r'(\d+(\.\d+)?)\s*(亿 | 万|百万)\s*(元 | 美元 | 人民币 |CNY|USD)?'),
            re.compile(r'(数 | 超 | 近 | 约)?\s*(\d+(\.\d+)?)\s*(亿 | 万)'),
        ]

        # 公司名提取模式（简化版）
        self.company_pattern = re.compile(r'([^\s，。；：]+)(股份 | 有限责任 | 集团 | 公司 | 企业 | 科技 | 网络)')

    def detect_events(self, text: str, metadata: Dict = None) -> List[BusinessEvent]:
        """从文本中检测事件"""
        events = []
        metadata = metadata or {}

        for event_type, config in self.event_patterns.items():
            for pattern in config["keywords"]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # 检测到事件，创建事件对象
                    event = self._create_event(
                        event_type=event_type,
                        text=text,
                        match_text=match.group(),
                        metadata=metadata,
                        severity_keywords=config.get("severity_keywords", [])
                    )
                    if event and event.confidence >= 0.5:  # 置信度阈值
                        events.append(event)
                    break  # 同一类型只检测一次

        # 按严重性排序
        events.sort(key=lambda e: (
            {"critical": 4, "high": 3, "medium": 2, "low": 1}[e.severity.value],
            e.confidence
        ), reverse=True)

        return events

    def _create_event(
        self,
        event_type: EventType,
        text: str,
        match_text: str,
        metadata: Dict,
        severity_keywords: List[Tuple[str, EventSeverity]]
    ) -> Optional[BusinessEvent]:
        """创建事件对象"""
        # 提取公司名
        companies = self._extract_companies(text)

        # 提取金额
        amount, currency = self._extract_amount(text)

        # 提取日期（如果有）
        publish_date = metadata.get("publish_date")

        # 确定严重性
        severity = self._determine_severity(text, severity_keywords)

        # 生成标题和摘要
        title = self._generate_title(event_type, match_text, companies)
        summary = self._generate_summary(event_type, text, amount, currency)

        # 计算置信度
        confidence = self._calculate_confidence(event_type, text, companies, amount)

        return BusinessEvent(
            event_type=event_type,
            title=title,
            summary=summary,
            companies=companies,
            amount=amount,
            currency=currency,
            publish_date=publish_date,
            source=metadata.get("source", ""),
            source_url=metadata.get("source_url", ""),
            severity=severity,
            confidence=confidence,
            raw_text=text
        )

    def _extract_companies(self, text: str) -> List[str]:
        """提取公司名"""
        matches = self.company_pattern.findall(text)
        companies = list(set([match[0] + match[1] for match in matches]))
        return companies[:5]  # 最多 5 个公司

    def _extract_amount(self, text: str) -> Tuple[Optional[float], str]:
        """提取金额"""
        for pattern in self.amount_patterns:
            match = pattern.search(text)
            if match:
                try:
                    value_str = match.group(1) or match.group(2)
                    unit = match.group(3) or match.group(4) or ""
                    currency = match.group(4) or match.group(5) or "CNY"

                    value = float(value_str)

                    # 单位转换
                    if "亿" in unit:
                        value *= 100000000
                    elif "万" in unit:
                        value *= 10000
                    elif "百万" in unit:
                        value *= 1000000

                    # 货币标准化
                    if "美元" in currency or "USD" in currency:
                        currency = "USD"
                    else:
                        currency = "CNY"

                    return value, currency
                except Exception as e:
                    logger.warning(f"Failed to extract amount: {e}")

        return None, "CNY"

    def _determine_severity(
        self,
        text: str,
        severity_keywords: List[Tuple[str, EventSeverity]]
    ) -> EventSeverity:
        """确定事件严重性"""
        for pattern, severity in severity_keywords:
            if re.search(pattern, text, re.IGNORECASE):
                return severity
        return EventSeverity.MEDIUM  # 默认中等重要性

    def _generate_title(
        self,
        event_type: EventType,
        match_text: str,
        companies: List[str]
    ) -> str:
        """生成事件标题"""
        company_str = companies[0] if companies else "相关企业"

        title_templates = {
            EventType.FUNDING: f"{company_str}完成融资",
            EventType.ACQUISITION: f"{company_str}收购/并购事件",
            EventType.IPO: f"{company_str}IPO/上市",
            EventType.PRODUCT_LAUNCH: f"{company_str}发布新产品",
            EventType.TECHNOLOGY_BREAKTHROUGH: f"{company_str}技术突破",
            EventType.PARTNERSHIP: f"{company_str}达成战略合作",
            EventType.EXECUTIVE_CHANGE: f"{company_str}高管变动",
            EventType.POLICY_CHANGE: f"行业政策变化",
            EventType.EXPANSION: f"{company_str}业务扩张",
            EventType.LAYOFF: f"{company_str}人员调整",
        }

        return title_templates.get(event_type, f"商业事件：{match_text[:20]}")

    def _generate_summary(
        self,
        event_type: EventType,
        text: str,
        amount: Optional[float],
        currency: str
    ) -> str:
        """生成事件摘要"""
        # 截取原文前 100 字作为摘要
        summary = text[:100] + "..." if len(text) > 100 else text

        # 如果有金额信息，添加到摘要
        if amount:
            amount_str = f"{amount/100000000:.2f}亿" if amount >= 100000000 else f"{amount/10000:.2f}万"
            summary = f"金额：{amount_str}{currency}。{summary}"

        return summary

    def _calculate_confidence(
        self,
        event_type: EventType,
        text: str,
        companies: List[str],
        amount: Optional[float]
    ) -> float:
        """计算事件置信度"""
        confidence = 0.5  # 基础置信度

        # 有公司名增加置信度
        if companies:
            confidence += 0.15

        # 有金额信息增加置信度
        if amount:
            confidence += 0.15

        # 文本长度适中增加置信度
        if 50 <= len(text) <= 500:
            confidence += 0.1

        # 事件类型特定关键词增加置信度
        type_keywords = {
            EventType.FUNDING: ["轮", "投资", "融资", "领投", "跟投"],
            EventType.ACQUISITION: ["收购", "并购", "控股"],
            EventType.IPO: ["IPO", "上市", "招股", "挂牌"],
            EventType.PRODUCT_LAUNCH: ["发布", "推出", "上线"],
        }

        keywords = type_keywords.get(event_type, [])
        if any(kw in text for kw in keywords):
            confidence += 0.1

        return min(confidence, 1.0)

    def detect_from_articles(self, articles: List[Dict]) -> List[BusinessEvent]:
        """从文章列表中检测事件"""
        all_events = []

        for article in articles:
            text = article.get("content", "") or article.get("summary", "")
            if not text:
                continue

            metadata = {
                "publish_date": article.get("published_at") or article.get("publish_date"),
                "source": article.get("source") or article.get("publisher", ""),
                "source_url": article.get("url", ""),
            }

            events = self.detect_events(text, metadata)
            all_events.extend(events)

        # 去重（基于事件类型和公司）
        seen = set()
        unique_events = []
        for event in all_events:
            key = (event.event_type, tuple(sorted(event.companies)))
            if key not in seen:
                seen.add(key)
                unique_events.append(event)

        return unique_events

    def get_event_statistics(self, events: List[BusinessEvent]) -> Dict:
        """获取事件统计"""
        if not events:
            return {}

        # 按类型统计
        type_counts = Counter(e.event_type.value for e in events)

        # 按严重性统计
        severity_counts = Counter(e.severity.value for e in events)

        # 按公司统计
        company_counts = Counter()
        for event in events:
            for company in event.companies:
                company_counts[company] += 1

        # 高价值事件（融资金额大的）
        high_value_events = [
            e for e in events
            if e.event_type == EventType.FUNDING and e.amount and e.amount >= 100000000  # 1 亿+
        ]

        return {
            "total_events": len(events),
            "by_type": dict(type_counts),
            "by_severity": dict(severity_counts),
            "top_companies": dict(company_counts.most_common(10)),
            "high_value_funding_count": len(high_value_events),
        }


# 全局单例
event_detector = EventDetector()
