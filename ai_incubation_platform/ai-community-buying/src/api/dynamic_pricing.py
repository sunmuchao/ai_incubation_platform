"""
P1 动态定价引擎 - API 路由

提供以下 API：
1. 动态价格管理：/api/dynamic-pricing/*
2. 定价策略管理：/api/pricing-strategies/*
3. 价格弹性测试：/api/price-tests/*
4. 竞品价格追踪：/api/competitor-prices/*
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from config.database import get_db
from services.dynamic_pricing_service import DynamicPricingService
from models.pricing_entities import (
    DynamicPriceEntity, PriceHistoryEntity, PricingStrategyEntity,
    PriceElasticityTestEntity, CompetitorPriceEntity
)
from models.dynamic_pricing import (
    PricingStrategyType, PriceAdjustmentReason, PriceStatus,
    DynamicPriceCreate, DynamicPriceUpdate, PriceAdjustmentRequest,
    PricingStrategyCreate, PriceElasticityTestCreate
)
from core.exceptions import AppException

router = APIRouter(prefix="/api/dynamic-pricing", tags=["P1 动态定价引擎"])


# ==================== 动态价格管理 API ====================

@router.post("/prices", summary="创建/更新动态价格配置")
def create_or_update_price(
    request: DynamicPriceCreate,
    db: Session = Depends(get_db)
):
    """创建或更新商品的动态价格配置"""
    service = DynamicPricingService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    data = {
        "product_id": request.product_id,
        "community_id": request.community_id,
        "base_price": request.base_price,
        "min_price": request.min_price,
        "max_price": request.max_price,
        "strategy_type": request.strategy_type,
        "strategy_config": request.strategy_config
    }

    entity, success = service.create_dynamic_price(data)

    if not success or not entity:
        raise AppException(
            code="PRICE_CONFIG_CREATE_FAILED",
            message="创建动态价格配置失败"
        )

    return {
        "success": True,
        "message": "动态价格配置创建成功",
        "data": {
            "id": entity.id,
            "product_id": entity.product_id,
            "community_id": entity.community_id,
            "base_price": entity.base_price,
            "current_price": entity.current_price,
            "min_price": entity.min_price,
            "max_price": entity.max_price,
            "strategy_type": entity.strategy_type.value
        }
    }


@router.get("/prices/{price_id}", summary="获取动态价格详情")
def get_price(price_id: str, db: Session = Depends(get_db)):
    """获取动态价格配置详情"""
    service = DynamicPricingService(db)
    entity = service.get_dynamic_price(price_id)

    if not entity:
        raise AppException(
            code="PRICE_NOT_FOUND",
            message="动态价格配置不存在",
            status=404
        )

    return {
        "success": True,
        "data": {
            "id": entity.id,
            "product_id": entity.product_id,
            "community_id": entity.community_id,
            "base_price": entity.base_price,
            "current_price": entity.current_price,
            "min_price": entity.min_price,
            "max_price": entity.max_price,
            "adjustment_amount": entity.adjustment_amount,
            "adjustment_percentage": entity.adjustment_percentage,
            "adjustment_reason": entity.adjustment_reason.value if entity.adjustment_reason else None,
            "strategy_type": entity.strategy_type.value,
            "strategy_config": entity.strategy_config,
            "status": entity.status.value,
            "effective_from": entity.effective_from.isoformat() if entity.effective_from else None,
            "effective_to": entity.effective_to.isoformat() if entity.effective_to else None
        }
    }


@router.get("/prices/product/{product_id}/community/{community_id}", summary="获取商品在指定社区的价格")
def get_product_price(product_id: str, community_id: str, db: Session = Depends(get_db)):
    """获取商品在指定社区的动态价格"""
    service = DynamicPricingService(db)
    entity = service.get_price_for_product(product_id, community_id)

    if not entity:
        # 返回静态价格
        from models.entities import ProductEntity
        product = db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if product:
            return {
                "success": True,
                "data": {
                    "product_id": product_id,
                    "community_id": community_id,
                    "base_price": product.price,
                    "current_price": product.price,
                    "is_dynamic": False
                }
            }
        raise AppException(
            code="PRODUCT_NOT_FOUND",
            message="商品不存在",
            status=404
        )

    return {
        "success": True,
        "data": {
            "id": entity.id,
            "product_id": entity.product_id,
            "community_id": entity.community_id,
            "base_price": entity.base_price,
            "current_price": entity.current_price,
            "min_price": entity.min_price,
            "max_price": entity.max_price,
            "is_dynamic": True
        }
    }


@router.put("/prices/{price_id}", summary="更新动态价格")
def update_price(
    price_id: str,
    request: DynamicPriceUpdate,
    db: Session = Depends(get_db)
):
    """更新动态价格配置"""
    service = DynamicPricingService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    data = {
        "current_price": request.current_price,
        "adjustment_amount": request.adjustment_amount,
        "adjustment_reason": request.adjustment_reason,
        "strategy_config": request.strategy_config,
        "status": request.status,
        "effective_to": request.effective_to
    }

    entity, success = service.update_dynamic_price(price_id, {k: v for k, v in data.items() if v is not None})

    if not success or not entity:
        raise AppException(
            code="PRICE_UPDATE_FAILED",
            message="更新动态价格失败"
        )

    return {
        "success": True,
        "message": "动态价格更新成功",
        "data": {
            "id": entity.id,
            "current_price": entity.current_price
        }
    }


@router.post("/prices/{price_id}/adjust", summary="手动调价")
def adjust_price(
    price_id: str,
    request: PriceAdjustmentRequest,
    db: Session = Depends(get_db)
):
    """手动调整价格"""
    service = DynamicPricingService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    entity = service.get_dynamic_price(price_id)
    if not entity:
        raise AppException(
            code="PRICE_NOT_FOUND",
            message="动态价格配置不存在",
            status=404
        )

    # 计算调整金额
    if request.adjustment_type == "percentage":
        adjustment_amount = entity.base_price * request.adjustment_value
    else:
        adjustment_amount = request.adjustment_value

    # 应用调整
    new_price = entity.base_price + adjustment_amount
    new_price = max(entity.min_price, min(entity.max_price, new_price))

    data = {
        "current_price": new_price,
        "adjustment_amount": adjustment_amount,
        "adjustment_percentage": adjustment_amount / entity.base_price if entity.base_price > 0 else 0,
        "adjustment_reason": request.reason,
        "effective_to": request.effective_to
    }

    entity, success = service.update_dynamic_price(price_id, data)

    if not success:
        raise AppException(
            code="PRICE_ADJUST_FAILED",
            message="价格调整失败"
        )

    return {
        "success": True,
        "message": "价格调整成功",
        "data": {
            "old_price": entity.base_price,
            "new_price": new_price,
            "adjustment": adjustment_amount,
            "reason": request.reason.value
        }
    }


@router.get("/prices", summary="获取价格列表")
def list_prices(
    product_id: Optional[str] = Query(None, description="商品 ID"),
    community_id: Optional[str] = Query(None, description="社区 ID"),
    status: Optional[str] = Query(None, description="价格状态"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取动态价格列表"""
    service = DynamicPricingService(db)

    status_enum = None
    if status:
        try:
            status_enum = PriceStatus(status)
        except ValueError:
            pass

    entities = service.list_prices(
        product_id=product_id,
        community_id=community_id,
        status=status_enum,
        limit=limit
    )

    return {
        "success": True,
        "data": [
            {
                "id": e.id,
                "product_id": e.product_id,
                "community_id": e.community_id,
                "base_price": e.base_price,
                "current_price": e.current_price,
                "strategy_type": e.strategy_type.value,
                "status": e.status.value
            }
            for e in entities
        ]
    }


@router.get("/prices/{product_id}/history", summary="获取价格历史")
def get_price_history(
    product_id: str,
    community_id: Optional[str] = Query(None, description="社区 ID"),
    hours: int = Query(24, ge=1, le=720, description="查询小时数"),
    db: Session = Depends(get_db)
):
    """获取价格调整历史"""
    service = DynamicPricingService(db)
    histories = service.get_price_history(product_id, community_id, hours)

    return {
        "success": True,
        "data": [
            {
                "id": h.id,
                "old_price": h.old_price,
                "new_price": h.new_price,
                "adjustment_amount": h.adjustment_amount,
                "adjustment_reason": h.adjustment_reason.value if h.adjustment_reason else None,
                "trigger_source": h.trigger_source,
                "created_at": h.created_at.isoformat()
            }
            for h in histories
        ]
    }


# ==================== 动态价格计算 API ====================

@router.get("/calculate/{product_id}/{community_id}", summary="计算动态价格")
def calculate_dynamic_price(
    product_id: str,
    community_id: str,
    group_probability: Optional[float] = Query(None, ge=0, le=1, description="成团概率"),
    demand_level: Optional[float] = Query(None, ge=0, le=1, description="需求水平"),
    competitor_price: Optional[float] = Query(None, gt=0, description="竞品价格"),
    db: Session = Depends(get_db)
):
    """
    计算商品的动态价格

    可选参数：
    - group_probability: 成团概率 (0-1)
    - demand_level: 需求水平 (0-1)
    - competitor_price: 竞品价格
    """
    service = DynamicPricingService(db)

    context = {}
    if group_probability is not None:
        context["group_probability"] = group_probability
    if demand_level is not None:
        context["demand_level"] = demand_level
    if competitor_price is not None:
        context["competitor_price"] = competitor_price

    result = service.calculate_dynamic_price(product_id, community_id, context)

    return {
        "success": True,
        "data": result
    }


# ==================== 定价策略管理 API ====================

@router.post("/strategies", summary="创建定价策略")
def create_strategy(
    request: PricingStrategyCreate,
    db: Session = Depends(get_db)
):
    """创建新的定价策略"""
    service = DynamicPricingService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    data = {
        "name": request.name,
        "strategy_type": request.strategy_type,
        "description": request.description,
        "is_active": request.is_active,
        "priority": request.priority,
        "config": request.config
    }

    entity, success = service.create_strategy(data)

    if not success:
        raise AppException(
            code="STRATEGY_CREATE_FAILED",
            message="创建定价策略失败"
        )

    return {
        "success": True,
        "message": "定价策略创建成功",
        "data": {
            "id": entity.id,
            "name": entity.name,
            "strategy_type": entity.strategy_type.value,
            "priority": entity.priority
        }
    }


@router.get("/strategies", summary="获取定价策略列表")
def list_strategies(
    active_only: bool = Query(True, description="是否仅获取激活策略"),
    db: Session = Depends(get_db)
):
    """获取定价策略列表"""
    service = DynamicPricingService(db)
    strategies = service.list_strategies(is_active=active_only)

    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "strategy_type": s.strategy_type.value,
                "description": s.description,
                "priority": s.priority,
                "config": json.loads(s.config) if s.config else {}
            }
            for s in strategies
        ]
    }


# ==================== 价格弹性测试 API ====================

@router.post("/tests", summary="创建价格弹性测试")
def create_elasticity_test(
    request: PriceElasticityTestCreate,
    db: Session = Depends(get_db)
):
    """创建价格弹性 A/B 测试"""
    service = DynamicPricingService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    data = {
        "product_id": request.product_id,
        "community_id": request.community_id,
        "test_name": request.test_name,
        "control_price": request.control_price,
        "variant_prices": request.variant_prices,
        "traffic_allocation": request.traffic_allocation,
        "target_metric": request.target_metric
    }

    entity, success = service.create_elasticity_test(data)

    if not success:
        raise AppException(
            code="TEST_CREATE_FAILED",
            message="创建价格弹性测试失败"
        )

    return {
        "success": True,
        "message": "价格弹性测试创建成功",
        "data": {
            "id": entity.id,
            "test_name": entity.test_name,
            "control_price": entity.control_price,
            "variant_prices": entity.variant_prices,
            "status": entity.status
        }
    }


@router.post("/tests/{test_id}/start", summary="启动价格弹性测试")
def start_test(test_id: str, db: Session = Depends(get_db)):
    """启动价格弹性测试"""
    service = DynamicPricingService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    success, message = service.start_elasticity_test(test_id)

    if not success:
        raise AppException(
            code="TEST_START_FAILED",
            message=message
        )

    return {
        "success": True,
        "message": message
    }


@router.post("/tests/{test_id}/complete", summary="完成价格弹性测试")
def complete_test(
    test_id: str,
    control_metrics: Dict[str, Any] = Body(..., description="对照组指标"),
    variant_metrics: Dict[str, Any] = Body(..., description="实验组指标"),
    db: Session = Depends(get_db)
):
    """完成价格弹性测试并计算弹性系数"""
    service = DynamicPricingService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    success, elasticity = service.complete_elasticity_test(test_id, control_metrics, variant_metrics)

    if not success:
        raise AppException(
            code="TEST_COMPLETE_FAILED",
            message="完成测试失败"
        )

    return {
        "success": True,
        "message": "测试完成",
        "data": {
            "elasticity_coefficient": elasticity,
            "interpretation": "弹性充足" if abs(elasticity) > 1 else "弹性不足"
        }
    }


@router.get("/tests/{test_id}", summary="获取弹性测试详情")
def get_test(test_id: str, db: Session = Depends(get_db)):
    """获取价格弹性测试详情"""
    service = DynamicPricingService(db)
    entity = service.get_elasticity_test(test_id)

    if not entity:
        raise AppException(
            code="TEST_NOT_FOUND",
            message="测试不存在",
            status=404
        )

    return {
        "success": True,
        "data": {
            "id": entity.id,
            "test_name": entity.test_name,
            "control_price": entity.control_price,
            "status": entity.status,
            "elasticity_coefficient": entity.elasticity_coefficient,
            "start_time": entity.start_time.isoformat() if entity.start_time else None,
            "end_time": entity.end_time.isoformat() if entity.end_time else None
        }
    }


# ==================== 竞品价格 API ====================

@router.post("/competitor-prices", summary="更新竞品价格")
def update_competitor_price(
    product_id: str = Query(..., description="商品 ID"),
    competitor_name: str = Query(..., description="竞品平台名称"),
    competitor_price: float = Query(..., gt=0, description="竞品价格"),
    competitor_product_id: Optional[str] = Query(None, description="竞品商品 ID"),
    competitor_stock_status: str = Query("in_stock", description="库存状态"),
    db: Session = Depends(get_db)
):
    """更新或添加竞品价格信息"""
    service = DynamicPricingService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    data = {
        "product_id": product_id,
        "competitor_name": competitor_name,
        "competitor_price": competitor_price,
        "competitor_product_id": competitor_product_id,
        "competitor_stock_status": competitor_stock_status
    }

    entity, success = service.update_competitor_price(data)

    if not success:
        raise AppException(
            code="COMPETITOR_PRICE_UPDATE_FAILED",
            message="更新竞品价格失败"
        )

    return {
        "success": True,
        "message": "竞品价格更新成功",
        "data": {
            "id": entity.id,
            "competitor_name": entity.competitor_name,
            "competitor_price": entity.competitor_price
        }
    }


@router.get("/competitor-prices/{product_id}", summary="获取竞品价格列表")
def get_competitor_prices(product_id: str, db: Session = Depends(get_db)):
    """获取商品的竞品价格列表"""
    service = DynamicPricingService(db)
    prices = service.get_competitor_prices(product_id)

    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "competitor_name": p.competitor_name,
                "competitor_price": p.competitor_price,
                "competitor_stock_status": p.competitor_stock_status,
                "crawled_at": p.crawled_at.isoformat()
            }
            for p in prices
        ]
    }


# ==================== 统计报表 API ====================

@router.get("/stats", summary="获取价格统计")
def get_price_stats(
    product_id: Optional[str] = Query(None, description="商品 ID"),
    days: int = Query(7, ge=1, le=30, description="统计天数"),
    db: Session = Depends(get_db)
):
    """获取价格调整统计"""
    service = DynamicPricingService(db)
    stats = service.get_price_stats(product_id, days)

    return {
        "success": True,
        "data": stats
    }


# 需要导入 json 用于策略解析
import json
from models.entities import ProductEntity
