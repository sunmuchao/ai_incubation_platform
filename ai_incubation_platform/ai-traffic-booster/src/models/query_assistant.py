"""
AI 查询助手数据模型

提供自然语言查询、查询历史、收藏管理、报告生成等数据实体
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class QueryIntent(Enum):
    """查询意图类型"""
    # 流量查询
    TRAFFIC_QUERY = "traffic_query"      # "上周流量是多少？"
    TREND_QUERY = "trend_query"          # "流量趋势如何？"
    COMPARISON_QUERY = "comparison"      # "这个月和上个月比怎么样？"

    # 页面/内容查询
    PAGE_QUERY = "page_query"            # "哪个页面流量最高？"
    CONTENT_QUERY = "content_query"      # "什么内容最受欢迎？"

    # 用户查询
    USER_QUERY = "user_query"            # "用户留存率如何？"
    SEGMENT_QUERY = "segment_query"      # "高价值用户有什么特征？"

    # 竞品查询
    COMPETITOR_QUERY = "competitor"      # "竞品流量怎么样？"
    BENCHMARK_QUERY = "benchmark"        # "我们在行业中的位置？"

    # 异常/根因查询
    ANOMALY_QUERY = "anomaly_query"      # "为什么流量下跌？"
    ROOT_CAUSE_QUERY = "root_cause"      # "转化率下降的原因？"

    # 建议查询
    RECOMMENDATION_QUERY = "recommendation"  # "我该如何提升流量？"
    OPTIMIZATION_QUERY = "optimization"      # "有什么优化建议？"

    # 通用查询
    GENERAL_QUERY = "general_query"


class QueryStatus(Enum):
    """查询状态"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TimeRange:
    """时间范围"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    relative_period: Optional[str] = None  # "last_7_days", "last_30_days", "last_week", "last_month"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "relative_period": self.relative_period
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeRange":
        return cls(
            start_date=datetime.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            end_date=datetime.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            relative_period=data.get("relative_period")
        )


@dataclass
class Filter:
    """查询筛选条件"""
    field: str
    operator: str  # "equals", "contains", "greater_than", "less_than", "in"
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Filter":
        return cls(
            field=data["field"],
            operator=data["operator"],
            value=data["value"]
        )


@dataclass
class Comparison:
    """比较配置"""
    compare_type: str  # "previous_period", "same_period_last_year", "competitor", "benchmark"
    compare_target: Optional[str] = None  # 竞品 ID 或基准名称

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compare_type": self.compare_type,
            "compare_target": self.compare_target
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Comparison":
        return cls(
            compare_type=data["compare_type"],
            compare_target=data.get("compare_target")
        )


@dataclass
class QueryEntities:
    """查询实体 - 从自然语言中提取的结构化信息"""
    # 时间范围
    time_range: Optional[TimeRange] = None

    # 指标
    metrics: List[str] = field(default_factory=list)  # 流量/PV/UV/跳出率/转化率

    # 维度
    dimensions: List[str] = field(default_factory=list)  # 页面/来源/设备/地区

    # 筛选条件
    filters: List[Filter] = field(default_factory=list)

    # 比较对象
    comparison: Optional[Comparison] = None

    # 排序
    order_by: Optional[str] = None
    order_direction: str = "desc"  # "asc" or "desc"

    # 限制
    limit: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_range": self.time_range.to_dict() if self.time_range else None,
            "metrics": self.metrics,
            "dimensions": self.dimensions,
            "filters": [f.to_dict() for f in self.filters],
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "order_by": self.order_by,
            "order_direction": self.order_direction,
            "limit": self.limit
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryEntities":
        entities = cls(
            metrics=data.get("metrics", []),
            dimensions=data.get("dimensions", []),
            order_by=data.get("order_by"),
            order_direction=data.get("order_direction", "desc"),
            limit=data.get("limit", 10)
        )

        if data.get("time_range"):
            entities.time_range = TimeRange.from_dict(data["time_range"])

        if data.get("filters"):
            entities.filters = [Filter.from_dict(f) for f in data["filters"]]

        if data.get("comparison"):
            entities.comparison = Comparison.from_dict(data["comparison"])

        return entities


@dataclass
class QueryHistory:
    """查询历史"""
    query_id: str
    session_id: str
    user_id: Optional[str]
    query_text: str                    # 原始自然语言查询
    query_intent: QueryIntent          # 查询意图
    query_entities: QueryEntities      # 提取的实体
    sql_generated: Optional[str]       # 生成的 SQL（如适用）
    result_summary: Dict[str, Any]     # 结果摘要
    ai_interpretation: Optional[str]   # AI 解读
    execution_time_ms: int             # 执行耗时
    status: QueryStatus = QueryStatus.COMPLETED
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "query_text": self.query_text,
            "query_intent": self.query_intent.value,
            "query_entities": self.query_entities.to_dict(),
            "sql_generated": self.sql_generated,
            "result_summary": self.result_summary,
            "ai_interpretation": self.ai_interpretation,
            "execution_time_ms": self.execution_time_ms,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryHistory":
        return cls(
            query_id=data["query_id"],
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            query_text=data["query_text"],
            query_intent=QueryIntent(data["query_intent"]),
            query_entities=QueryEntities.from_dict(data["query_entities"]),
            sql_generated=data.get("sql_generated"),
            result_summary=data.get("result_summary", {}),
            ai_interpretation=data.get("ai_interpretation"),
            execution_time_ms=data.get("execution_time_ms", 0),
            status=QueryStatus(data.get("status", "completed")),
            error_message=data.get("error_message"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )

    @classmethod
    def create(
        cls,
        query_text: str,
        session_id: str,
        user_id: Optional[str] = None,
        query_intent: QueryIntent = QueryIntent.GENERAL_QUERY
    ) -> "QueryHistory":
        return cls(
            query_id=f"qry_{uuid.uuid4().hex[:16]}",
            session_id=session_id,
            user_id=user_id,
            query_text=query_text,
            query_intent=query_intent,
            query_entities=QueryEntities(),
            sql_generated=None,
            result_summary={},
            ai_interpretation=None,
            execution_time_ms=0,
            status=QueryStatus.PENDING
        )


@dataclass
class QueryFavorite:
    """查询收藏"""
    favorite_id: str
    user_id: str
    query_id: Optional[str]                # 关联的历史查询 ID
    query_text: str                        # 查询文本
    custom_name: Optional[str]             # 自定义名称
    category: Optional[str]                # 流量/转化/用户/竞品
    tags: List[str] = field(default_factory=list)
    is_public: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "favorite_id": self.favorite_id,
            "user_id": self.user_id,
            "query_id": self.query_id,
            "query_text": self.query_text,
            "custom_name": self.custom_name,
            "category": self.category,
            "tags": self.tags,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryFavorite":
        return cls(
            favorite_id=data["favorite_id"],
            user_id=data["user_id"],
            query_id=data.get("query_id"),
            query_text=data["query_text"],
            custom_name=data.get("custom_name"),
            category=data.get("category"),
            tags=data.get("tags", []),
            is_public=data.get("is_public", False),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )

    @classmethod
    def create(
        cls,
        query_text: str,
        user_id: str,
        query_id: Optional[str] = None,
        custom_name: Optional[str] = None
    ) -> "QueryFavorite":
        return cls(
            favorite_id=f"fav_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            query_id=query_id,
            query_text=query_text,
            custom_name=custom_name,
            category=None,
            tags=[],
            is_public=False
        )


@dataclass
class SavedReport:
    """保存的报告"""
    report_id: str
    user_id: str
    report_title: str
    report_type: str                    # weekly/monthly/custom/anomaly
    report_content: Dict[str, Any]      # 报告内容
    query_ids: List[str] = field(default_factory=list)
    is_scheduled: bool = False
    schedule_config: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "user_id": self.user_id,
            "report_title": self.report_title,
            "report_type": self.report_type,
            "report_content": self.report_content,
            "query_ids": self.query_ids,
            "is_scheduled": self.is_scheduled,
            "schedule_config": self.schedule_config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedReport":
        return cls(
            report_id=data["report_id"],
            user_id=data["user_id"],
            report_title=data["report_title"],
            report_type=data["report_type"],
            report_content=data["report_content"],
            query_ids=data.get("query_ids", []),
            is_scheduled=data.get("is_scheduled", False),
            schedule_config=data.get("schedule_config"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )

    @classmethod
    def create(
        cls,
        report_title: str,
        report_type: str,
        report_content: Dict[str, Any],
        user_id: str
    ) -> "SavedReport":
        now = datetime.now()
        return cls(
            report_id=f"rpt_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            report_title=report_title,
            report_type=report_type,
            report_content=report_content,
            query_ids=[],
            is_scheduled=False,
            schedule_config=None,
            created_at=now,
            updated_at=now
        )


@dataclass
class QueryTemplate:
    """查询模板 - 推荐的常用查询"""
    template_id: str
    category: str                       # traffic/conversion/user/competitor
    template_name: str
    template_text: str                  # 模板查询文本
    template_intent: QueryIntent
    example_entities: Dict[str, Any]
    usage_count: int = 0
    is_recommended: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "category": self.category,
            "template_name": self.template_name,
            "template_text": self.template_text,
            "template_intent": self.template_intent.value,
            "example_entities": self.example_entities,
            "usage_count": self.usage_count,
            "is_recommended": self.is_recommended,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryTemplate":
        return cls(
            template_id=data["template_id"],
            category=data["category"],
            template_name=data["template_name"],
            template_text=data["template_text"],
            template_intent=QueryIntent(data["template_intent"]),
            example_entities=data.get("example_entities", {}),
            usage_count=data.get("usage_count", 0),
            is_recommended=data.get("is_recommended", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )


# 预定义的查询模板
DEFAULT_QUERY_TEMPLATES = [
    {
        "category": "traffic",
        "template_name": "上周流量概览",
        "template_text": "上周的流量数据如何？",
        "template_intent": QueryIntent.TRAFFIC_QUERY.value,
        "example_entities": {
            "time_range": {"relative_period": "last_7_days"},
            "metrics": ["pv", "uv", "sessions"]
        }
    },
    {
        "category": "traffic",
        "template_name": "流量趋势分析",
        "template_text": "最近 30 天的流量趋势如何？",
        "template_intent": QueryIntent.TREND_QUERY.value,
        "example_entities": {
            "time_range": {"relative_period": "last_30_days"},
            "metrics": ["sessions"],
            "order_by": "date",
            "order_direction": "asc"
        }
    },
    {
        "category": "page",
        "template_name": "热门页面排行",
        "template_text": "上周哪个页面流量最高？",
        "template_intent": QueryIntent.PAGE_QUERY.value,
        "example_entities": {
            "time_range": {"relative_period": "last_7_days"},
            "metrics": ["pv", "uv"],
            "dimensions": ["page_path"],
            "order_by": "pv",
            "order_direction": "desc",
            "limit": 10
        }
    },
    {
        "category": "conversion",
        "template_name": "转化率分析",
        "template_text": "最近的转化率怎么样？",
        "template_intent": QueryIntent.USER_QUERY.value,
        "example_entities": {
            "time_range": {"relative_period": "last_7_days"},
            "metrics": ["conversion_rate", "conversions"]
        }
    },
    {
        "category": "anomaly",
        "template_name": "异常检测",
        "template_text": "为什么流量下跌了？",
        "template_intent": QueryIntent.ANOMALY_QUERY.value,
        "example_entities": {
            "time_range": {"relative_period": "last_7_days"},
            "metrics": ["sessions"],
            "dimensions": ["source", "page_path"]
        }
    },
    {
        "category": "recommendation",
        "template_name": "优化建议",
        "template_text": "我该如何提升流量？",
        "template_intent": QueryIntent.RECOMMENDATION_QUERY.value,
        "example_entities": {
            "metrics": ["sessions", "bounce_rate"]
        }
    },
    {
        "category": "comparison",
        "template_name": "环比对比",
        "template_text": "这个月和上个月比怎么样？",
        "template_intent": QueryIntent.COMPARISON_QUERY.value,
        "example_entities": {
            "time_range": {"relative_period": "last_30_days"},
            "metrics": ["sessions", "pv", "uv"],
            "comparison": {"compare_type": "previous_period"}
        }
    },
    {
        "category": "user",
        "template_name": "用户留存分析",
        "template_text": "用户留存率如何？",
        "template_intent": QueryIntent.USER_QUERY.value,
        "example_entities": {
            "time_range": {"relative_period": "last_30_days"},
            "metrics": ["retention_rate", "retained_users"]
        }
    }
]
