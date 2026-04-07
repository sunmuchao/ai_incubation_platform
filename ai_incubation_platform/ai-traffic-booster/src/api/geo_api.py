"""
地理分布 API 路由 - P7

提供地理位置查询、地域分布统计、地图可视化等 API 端点
"""
from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
import logging

from schemas.common import Response, ErrorCode
from analytics.geo_analytics import geo_analytics_service, GeoLocation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geo", tags=["geo-analytics"])


@router.get("/ip/{ip_address}", response_model=Response)
async def lookup_ip(ip_address: str):
    """
    查询 IP 地理位置

    Args:
        ip_address: IP 地址

    Returns:
        IP 地理位置信息
    """
    try:
        location = geo_analytics_service.lookup_ip(ip_address)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "ip": location.ip,
                "country": location.country,
                "country_code": location.country_code,
                "region": location.region,
                "city": location.city,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "timezone": location.timezone,
                "isp": location.isp
            }
        )

    except Exception as e:
        logger.error(f"Error looking up IP: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to lookup IP: {str(e)}"
        )


@router.post("/ip/batch", response_model=Response)
async def lookup_ip_batch(
    ips: List[str] = Body(..., embed=True, description="IP 地址列表")
):
    """
    批量查询 IP 地理位置

    Args:
        ips: IP 地址列表

    Returns:
        IP 地理位置信息列表
    """
    try:
        if len(ips) > 1000:
            return Response(
                code=ErrorCode.VALIDATION_ERROR,
                message="Maximum 1000 IPs per batch"
            )

        locations = geo_analytics_service.lookup_batch(ips)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "count": len(locations),
                "locations": [
                    {
                        "ip": loc.ip,
                        "country": loc.country,
                        "country_code": loc.country_code,
                        "region": loc.region,
                        "city": loc.city
                    }
                    for loc in locations
                ]
            }
        )

    except Exception as e:
        logger.error(f"Error looking up IPs in batch: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to lookup IPs: {str(e)}"
        )


@router.post("/distribution/analyze", response_model=Response)
async def analyze_distribution(
    ips: List[str] = Body(..., embed=True, description="IP 地址列表"),
    dimension: str = Body(default="country", description="分析维度：country/region/city")
):
    """
    分析地域分布

    Args:
        ips: IP 地址列表
        dimension: 分析维度

    Returns:
        地域分布分析结果
    """
    try:
        result = geo_analytics_service.analyze_traffic_distribution(ips, dimension)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data=result
        )

    except Exception as e:
        logger.error(f"Error analyzing distribution: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to analyze distribution: {str(e)}"
        )


@router.get("/distribution/summary", response_model=Response)
async def get_distribution_summary():
    """
    获取地域分布摘要

    基于已记录的事件数据生成分布摘要

    Returns:
        地域分布摘要
    """
    try:
        # 从已记录的事件中获取 IP 数据
        event_geo_data = geo_analytics_service._event_geo_data
        ips = [loc.ip for loc in event_geo_data.values()]

        if not ips:
            return Response(
                code=ErrorCode.SUCCESS,
                message="No data available",
                data={
                    "total_ips": 0,
                    "unique_countries": 0,
                    "top_regions": []
                }
            )

        result = geo_analytics_service.analyze_traffic_distribution(ips)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "total_ips": result["summary"]["total_ips"],
                "unique_countries": result["summary"]["unique_countries"],
                "top_regions": result["top_regions"][:10]
            }
        )

    except Exception as e:
        logger.error(f"Error getting distribution summary: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get distribution summary: {str(e)}"
        )


@router.get("/map/world", response_model=Response)
async def get_world_map_data(
    ips: Optional[List[str]] = Body(None, description="IP 地址列表（可选，不提供则使用已记录的数据）")
):
    """
    获取世界地图可视化数据

    Args:
        ips: IP 地址列表（可选）

    Returns:
        GeoJSON 格式的世界地图数据
    """
    try:
        if ips is None:
            ips = [loc.ip for loc in geo_analytics_service._event_geo_data.values()]

        if not ips:
            return Response(
                code=ErrorCode.SUCCESS,
                message="No data available",
                data={"type": "FeatureCollection", "features": []}
            )

        distribution = geo_analytics_service._analyzer.analyze_distribution(ips)
        map_data = geo_analytics_service._analyzer.get_geo_json_data(distribution)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data=map_data
        )

    except Exception as e:
        logger.error(f"Error generating world map data: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to generate world map data: {str(e)}"
        )


@router.get("/map/china", response_model=Response)
async def get_china_map_data(
    ips: Optional[List[str]] = Body(None, description="IP 地址列表（可选）")
):
    """
    获取中国地图可视化数据

    Args:
        ips: IP 地址列表（可选）

    Returns:
        GeoJSON 格式的中国地图数据
    """
    try:
        if ips is None:
            ips = [loc.ip for loc in geo_analytics_service._event_geo_data.values()]

        if not ips:
            return Response(
                code=ErrorCode.SUCCESS,
                message="No data available",
                data={"type": "FeatureCollection", "features": []}
            )

        map_data = geo_analytics_service.get_china_map_data(ips)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data=map_data
        )

    except Exception as e:
        logger.error(f"Error generating China map data: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to generate China map data: {str(e)}"
        )


@router.get("/insights", response_model=Response)
async def get_geo_insights(
    ips: Optional[List[str]] = Body(None, description="IP 地址列表（可选）")
):
    """
    获取地理洞察

    基于地域分布数据生成智能洞察

    Args:
        ips: IP 地址列表（可选）

    Returns:
        地理洞察列表
    """
    try:
        if ips is None:
            ips = [loc.ip for loc in geo_analytics_service._event_geo_data.values()]

        if not ips:
            return Response(
                code=ErrorCode.SUCCESS,
                message="No data available",
                data={"insights": []}
            )

        insights = geo_analytics_service.get_geo_insights(ips)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "insights": insights,
                "count": len(insights)
            }
        )

    except Exception as e:
        logger.error(f"Error generating geo insights: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to generate geo insights: {str(e)}"
        )


@router.post("/event/location", response_model=Response)
async def record_event_location(
    event_id: str = Body(..., embed=True),
    ip_address: str = Body(..., embed=True)
):
    """
    记录事件的地理位置

    Args:
        event_id: 事件 ID
        ip_address: IP 地址

    Returns:
        记录结果
    """
    try:
        geo_analytics_service.record_event_location(event_id, ip_address)

        location = geo_analytics_service.get_event_location(event_id)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Event location recorded",
            data={
                "event_id": event_id,
                "location": {
                    "country": location.country,
                    "region": location.region,
                    "city": location.city
                } if location else None
            }
        )

    except Exception as e:
        logger.error(f"Error recording event location: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to record event location: {str(e)}"
        )


@router.get("/event/{event_id}/location", response_model=Response)
async def get_event_location(event_id: str):
    """
    获取事件的地理位置

    Args:
        event_id: 事件 ID

    Returns:
        事件地理位置信息
    """
    try:
        location = geo_analytics_service.get_event_location(event_id)

        if location is None:
            return Response(
                code=ErrorCode.NOT_FOUND,
                message="Event location not found"
            )

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "event_id": event_id,
                "ip": location.ip,
                "country": location.country,
                "country_code": location.country_code,
                "region": location.region,
                "city": location.city,
                "latitude": location.latitude,
                "longitude": location.longitude
            }
        )

    except Exception as e:
        logger.error(f"Error getting event location: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get event location: {str(e)}"
        )
