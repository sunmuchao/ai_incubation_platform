"""
路径分析和归因分析 API 路由

提供用户行为路径分析、桑基图数据生成、归因分析等能力
"""
from fastapi import APIRouter, Query, Body, Path
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field

from schemas.common import Response
from core.response import success
from core.exceptions import AnalyticsQueryFailedException

from analytics.path_analysis import path_analysis_service
from analytics.attribution_analysis import attribution_analysis_service, AttributionModel

router = APIRouter(prefix="/analytics", tags=["路径与归因分析"])


# ==================== 请求 Schema ====================

class PathAnalysisRequest(BaseModel):
    """路径分析请求"""
    start_date: date = Field(description="开始日期")
    end_date: date = Field(description="结束日期")
    domain: Optional[str] = Field(default=None, description="域名")
    max_paths: int = Field(default=20, description="返回的最大路径数")


class AttributionAnalysisRequest(BaseModel):
    """归因分析请求"""
    start_date: date = Field(description="开始日期")
    end_date: date = Field(description="结束日期")
    model: str = Field(default="last_click", description="归因模型")
    conversion_event: str = Field(default="purchase", description="转化事件")
    domain: Optional[str] = Field(default=None, description="域名")


class PathDropoffRequest(BaseModel):
    """路径流失分析请求"""
    start_date: date = Field(description="开始日期")
    end_date: date = Field(description="结束日期")
    target_path: List[str] = Field(description="目标路径")


# ==================== 路径分析 API ====================

@router.post("/paths/analyze", summary="分析用户行为路径")
async def analyze_user_paths(request: PathAnalysisRequest):
    """
    分析用户行为路径

    - 用户行为路径追踪
    - 常见路径挖掘
    - 路径转化率分析
    - 桑基图数据生成
    """
    if request.start_date > request.end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = path_analysis_service.analyze_user_paths(
        start_date=request.start_date,
        end_date=request.end_date,
        domain=request.domain,
        max_paths=request.max_paths
    )

    return success(data=result)


@router.get("/paths/entry-exit", summary="分析入口和退出路径")
async def analyze_entry_exit_paths(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    domain: Optional[str] = Query(default=None, description="域名")
):
    """
    分析入口和退出页面

    - Top 入口页面（用户首次访问的页面）
    - Top 退出页面（用户最后访问的页面）
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = path_analysis_service.analyze_entry_exit_paths(
        start_date=start_date,
        end_date=end_date,
        domain=domain
    )

    return success(data=result)


@router.get("/paths/conversion", summary="分析转化路径")
async def analyze_conversion_paths(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    conversion_event: str = Query(default="purchase", description="转化事件名称")
):
    """
    分析转化前的用户路径

    - 常见转化路径
    - 平均转化步数
    - 各路径的转化贡献
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = path_analysis_service.analyze_conversion_paths(
        start_date=start_date,
        end_date=end_date,
        conversion_event=conversion_event
    )

    return success(data=result)


@router.post("/paths/dropoff", summary="分析路径流失")
async def analyze_path_dropoff(request: PathDropoffRequest):
    """
    分析特定路径的流失情况

    - 每个步骤的到达人数
    - 每个步骤的流失率
    - 识别流失最严重的步骤
    - 生成优化建议
    """
    if request.start_date > request.end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = path_analysis_service.get_path_drop_off(
        start_date=request.start_date,
        end_date=request.end_date,
        target_path=request.target_path
    )

    return success(data=result)


@router.get("/paths/sankey", summary="获取桑基图数据")
async def get_sankey_data(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    domain: Optional[str] = Query(default=None, description="域名"),
    max_nodes: int = Query(default=50, description="最大节点数")
):
    """
    生成桑基图可视化数据

    返回格式:
    {
        "nodes": [{"id": "0_/home", "label": "/home", "step": 0, "visits": 1000}],
        "links": [{"source": 0, "target": 1, "value": 500}]
    }
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = path_analysis_service.analyze_user_paths(
        start_date=start_date,
        end_date=end_date,
        domain=domain,
        max_paths=100
    )

    return success(data=result.get("sankey_data", {"nodes": [], "links": []}))


# ==================== 归因分析 API ====================

@router.post("/attribution/analyze", summary="执行归因分析")
async def analyze_attribution(request: AttributionAnalysisRequest):
    """
    执行归因分析

    支持的归因模型:
    - first_click: 首次点击归因 - 100% 归因于第一个触点
    - last_click: 末次点击归因 - 100% 归因于最后一个触点
    - linear: 线性归因 - 平均分配给所有触点
    - time_decay: 时间衰减归因 - 越接近转化权重越高
    - u_shaped: U 型归因 - 首末触点各 40%，中间平分 20%
    - position_based: 位置加权归因 - 类似 U 型
    """
    if request.start_date > request.end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    try:
        model = AttributionModel(request.model)
    except ValueError:
        raise AnalyticsQueryFailedException(
            f"无效的归因模型：{request.model}。"
            f"支持的模型：{[m.value for m in AttributionModel]}"
        )

    result = attribution_analysis_service.analyze_attribution(
        start_date=request.start_date,
        end_date=request.end_date,
        model=model,
        conversion_event=request.conversion_event,
        domain=request.domain
    )

    return success(data=result.to_dict())


@router.get("/attribution/compare", summary="对比归因模型")
async def compare_attribution_models(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    conversion_event: str = Query(default="purchase", description="转化事件"),
    domain: Optional[str] = Query(default=None, description="域名")
):
    """
    对比不同归因模型的结果

    对比所有支持的归因模型，帮助理解不同模型下各渠道的贡献差异
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = attribution_analysis_service.compare_models(
        start_date=start_date,
        end_date=end_date,
        conversion_event=conversion_event,
        domain=domain
    )

    return success(data=result)


@router.get("/attribution/channels", summary="分析渠道表现")
async def analyze_channel_performance(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    conversion_event: str = Query(default="purchase", description="转化事件")
):
    """
    分析渠道表现（多模型综合评估）

    - 各渠道的平均贡献
    - 贡献稳定性评估
    - 渠道洞察和建议
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = attribution_analysis_service.analyze_channel_performance(
        start_date=start_date,
        end_date=end_date,
        conversion_event=conversion_event
    )

    return success(data=result)


@router.get("/attribution/assisted", summary="辅助转化分析")
async def analyze_assisted_conversions(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    conversion_event: str = Query(default="purchase", description="转化事件")
):
    """
    分析辅助转化数据

    - 各渠道的辅助转化次数
    - 各渠道的最终转化次数
    - 辅助转化比率
    - 识别高辅助价值渠道
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = attribution_analysis_service.get_path_assisted_conversions(
        start_date=start_date,
        end_date=end_date,
        conversion_event=conversion_event
    )

    return success(data=result)


# ==================== 综合分析报告 API ====================

@router.get("/paths/report", summary="路径分析报告")
async def generate_paths_report(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    domain: Optional[str] = Query(default=None, description="域名")
):
    """
    生成完整的路径分析报告

    包含:
    - 常见路径 Top10
    - 入口/退出页面分析
    - 路径统计信息
    - 桑基图数据
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    # 获取路径分析
    paths_result = path_analysis_service.analyze_user_paths(
        start_date=start_date,
        end_date=end_date,
        domain=domain
    )

    # 获取入口/退出分析
    entry_exit_result = path_analysis_service.analyze_entry_exit_paths(
        start_date=start_date,
        end_date=end_date,
        domain=domain
    )

    # 合并报告
    report = {
        "report_type": "user_paths_analysis",
        "period": {"start": str(start_date), "end": str(end_date)},
        "domain": domain,
        "generated_at": datetime.now().isoformat(),
        "path_overview": {
            "total_sessions": paths_result.get("total_sessions", 0),
            "total_paths": paths_result.get("total_paths", 0),
            "unique_paths": paths_result.get("unique_paths", 0),
            "path_stats": paths_result.get("path_stats", {})
        },
        "common_paths": paths_result.get("common_paths", []),
        "sankey_data": paths_result.get("sankey_data", {"nodes": [], "links": []}),
        "entry_pages": entry_exit_result.get("top_entry_pages", []),
        "exit_pages": entry_exit_result.get("top_exit_pages", [])
    }

    return success(data=report)


@router.get("/attribution/report", summary="归因分析报告")
async def generate_attribution_report(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    conversion_event: str = Query(default="purchase", description="转化事件"),
    domain: Optional[str] = Query(default=None, description="域名")
):
    """
    生成完整的归因分析报告

    包含:
    - 各归因模型结果对比
    - 渠道表现综合评估
    - 辅助转化分析
    - 渠道优化建议
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    # 获取模型对比
    compare_result = attribution_analysis_service.compare_models(
        start_date=start_date,
        end_date=end_date,
        conversion_event=conversion_event,
        domain=domain
    )

    # 获取渠道表现
    channel_result = attribution_analysis_service.analyze_channel_performance(
        start_date=start_date,
        end_date=end_date,
        conversion_event=conversion_event
    )

    # 获取辅助转化
    assisted_result = attribution_analysis_service.get_path_assisted_conversions(
        start_date=start_date,
        end_date=end_date,
        conversion_event=conversion_event
    )

    # 合并报告
    report = {
        "report_type": "attribution_analysis",
        "period": {"start": str(start_date), "end": str(end_date)},
        "domain": domain,
        "conversion_event": conversion_event,
        "generated_at": datetime.now().isoformat(),
        "model_comparison": compare_result,
        "channel_performance": channel_result,
        "assisted_conversions": assisted_result,
        "recommendations": generate_attribution_recommendations(
            channel_result, assisted_result
        )
    }

    return success(data=report)


def generate_attribution_recommendations(
    channel_result: Dict,
    assisted_result: Dict
) -> List[str]:
    """生成归因分析建议"""
    recommendations = []

    # 基于渠道表现的建议
    channel_perf = channel_result.get("channel_performance", {})
    for channel, data in channel_perf.items():
        if data.get("avg_credit", 0) > 0.3:
            recommendations.append(
                f"{channel}是主要贡献渠道（{data['avg_credit']*100:.1f}%），建议保持或增加投入"
            )
        if data.get("stability") == "低":
            recommendations.append(
                f"{channel}的贡献在不同模型间差异较大，建议深入分析其作用机制"
            )

    # 基于辅助转化的建议
    high_assist = assisted_result.get("high_assist_channels", [])
    if high_assist:
        recommendations.append(
            f"渠道 {', '.join(high_assist)} 主要起辅助作用，不应仅基于末次点击评估其价值，"
            f"建议采用多触点归因模型进行评估"
        )

    if not recommendations:
        recommendations.append("当前渠道表现健康，建议持续监控并优化")

    return recommendations
