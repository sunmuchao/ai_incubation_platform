"""
活动推荐 API 路由 - P3

提供基于地图 API 的地点推荐相关接口
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List

from db.database import get_db
from db.repositories import UserRepository
from services.activity_recommendation_service import activity_recommendation_service
from utils.logger import logger

router = APIRouter(prefix="/api/activities", tags=["activities"])


def get_user_service(db=Depends(get_db)):
    """获取用户服务依赖注入"""
    return UserRepository(db)


@router.get("/recommend/{user_id}")
async def get_activity_recommendations(
    user_id: str,
    target_user_id: Optional[str] = None,
    location_type: Optional[str] = None,
    occasion: Optional[str] = None,
    limit: int = 10
):
    """
    获取约会地点推荐

    Args:
        user_id: 用户 ID
        target_user_id: 对方用户 ID（可选，用于计算中间点）
        location_type: 地点类型 (cafe, restaurant, park, cinema, etc.)
        occasion: 场合 (first_date, weekend, special, casual)
        limit: 返回数量
    """
    if occasion:
        # 基于场合的推荐
        result = activity_recommendation_service.get_activity_recommendations(
            user_id=user_id,
            occasion=occasion
        )
    else:
        # 普通推荐
        result = activity_recommendation_service.recommend_date_locations(
            user_id=user_id,
            target_user_id=target_user_id,
            location_type=location_type,
            limit=limit
        )

    return result


@router.post("/locations/save")
async def save_location(
    user_id: str,
    location_name: str,
    location_type: str,
    address: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    reason: Optional[str] = None,
    tags: Optional[List[str]] = None,
    rating: Optional[float] = None,
    price_level: Optional[int] = None
):
    """
    收藏地点

    Args:
        user_id: 用户 ID
        location_name: 地点名称
        location_type: 地点类型
        address: 地址
        latitude: 纬度
        longitude: 经度
        reason: 收藏理由
        tags: 标签
        rating: 评分
        price_level: 价格等级
    """
    location_id = activity_recommendation_service.save_location(
        user_id=user_id,
        location_name=location_name,
        location_type=location_type,
        address=address,
        latitude=latitude,
        longitude=longitude,
        reason=reason,
        tags=tags,
        rating=rating,
        price_level=price_level
    )

    return {
        "location_id": location_id,
        "status": "saved"
    }


@router.get("/locations/{user_id}")
async def get_saved_locations(
    user_id: str,
    location_type: Optional[str] = None
):
    """
    获取收藏的地点

    Args:
        user_id: 用户 ID
        location_type: 地点类型过滤
    """
    locations = activity_recommendation_service.get_saved_locations(
        user_id=user_id,
        location_type=location_type
    )

    return {
        "locations": locations,
        "total": len(locations)
    }


@router.delete("/locations/{location_id}")
async def delete_saved_location(
    location_id: str,
    user_id: str
):
    """
    删除收藏的地点

    Args:
        location_id: 地点 ID
        user_id: 用户 ID
    """
    success = activity_recommendation_service.delete_saved_location(user_id, location_id)

    if success:
        return {"status": "deleted"}
    else:
        raise HTTPException(status_code=404, detail="Location not found")


@router.get("/locations/nearby/{user_id}")
async def get_nearby_locations(
    user_id: str,
    keyword: str = "咖啡厅",
    radius: int = 3000,
    limit: int = 10
):
    """
    搜索附近的地点（调用地图 API）

    Args:
        user_id: 用户 ID
        keyword: 搜索关键词
        radius: 搜索半径（米）
        limit: 返回数量
    """
    # 获取用户位置
    from db.repositories import UserRepository

    db = next(get_db())
    try:
        service = UserRepository(db)
        db_user = service.get_by_id(user_id)

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        from services.activity_recommendation_service import GeoService
        coords = GeoService._get_coordinates(db_user.location)

        if not coords:
            raise HTTPException(status_code=400, detail="Invalid user location")

        latitude, longitude = coords

        # 调用地图 API 搜索
        map_api = activity_recommendation_service.map_api
        locations = map_api.search_nearby(
            latitude=latitude,
            longitude=longitude,
            keyword=keyword,
            radius=radius,
            limit=limit
        )

        return {
            "locations": locations,
            "center": {"latitude": latitude, "longitude": longitude},
            "total": len(locations)
        }
    finally:
        db.close()
