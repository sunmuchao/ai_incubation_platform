"""
监控告警 API 接口

提供监控指标查询、告警规则管理、告警记录查询等接口
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from services.monitoring_service import monitoring_service
from services.retry_service import retry_service
from config.database import db_manager
from models.monitoring import AlertRuleModel, AlertModel, SystemHealthModel
from utils.logger import logger

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# ============ 请求/响应模型 ============

class AlertRuleCreate(BaseModel):
    """创建告警规则请求"""
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    metric_name: str = Field(..., description="指标名称")
    operator: str = Field(..., description="操作符 (>, <, >=, <=, ==, !=)")
    threshold: float = Field(..., description="阈值")
    duration_seconds: int = Field(0, description="持续时间（秒）")
    severity: str = Field("warning", description="告警级别")
    notify_channels: List[str] = Field(default_factory=list, description="通知渠道")
    notify_receivers: List[str] = Field(default_factory=list, description="通知接收人")


class AlertRuleUpdate(BaseModel):
    """更新告警规则请求"""
    name: Optional[str] = Field(None, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    metric_name: Optional[str] = Field(None, description="指标名称")
    operator: Optional[str] = Field(None, description="操作符")
    threshold: Optional[float] = Field(None, description="阈值")
    duration_seconds: Optional[int] = Field(None, description="持续时间")
    severity: Optional[str] = Field(None, description="告警级别")
    notify_channels: Optional[List[str]] = Field(None, description="通知渠道")
    notify_receivers: Optional[List[str]] = Field(None, description="通知接收人")
    enabled: Optional[bool] = Field(None, description="是否启用")
    silenced: Optional[bool] = Field(None, description="是否静默")


# ============ 监控指标接口 ============

@router.get("/metrics")
async def get_metrics(
    name: Optional[str] = Query(None, description="指标名称"),
    hours: int = Query(1, description="查询时长（小时）"),
    limit: int = Query(100, description="返回数量限制")
) -> Dict[str, Any]:
    """获取监控指标数据"""
    try:
        metrics = await monitoring_service.metrics_collector.get_metrics(name=name, hours=hours)
        return {
            "success": True,
            "metrics": metrics[:limit],
            "count": len(metrics)
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/latest/{metric_name}")
async def get_latest_metric(metric_name: str) -> Dict[str, Any]:
    """获取最新指标值"""
    try:
        metric = await monitoring_service.metrics_collector.get_latest_metrics(metric_name)
        return {
            "success": True,
            "metric": metric
        }
    except Exception as e:
        logger.error(f"Failed to get latest metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prometheus/metrics")
async def get_prometheus_metrics() -> str:
    """获取 Prometheus 格式的指标"""
    try:
        return await monitoring_service.prometheus_exporter.generate_prometheus_metrics()
    except Exception as e:
        logger.error(f"Failed to generate prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    """获取监控大盘数据"""
    try:
        dashboard = await monitoring_service.get_metrics_dashboard()
        return {
            "success": True,
            "data": dashboard
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 告警规则接口 ============

@router.post("/alert-rules")
async def create_alert_rule(rule: AlertRuleCreate) -> Dict[str, Any]:
    """创建告警规则"""
    async with db_manager.get_async_session() as session:
        try:
            # 检查规则名称是否已存在
            result = await session.execute(
                AlertRuleModel.name == rule.name
            )
            # 简化检查逻辑
            from sqlalchemy import select
            result = await session.execute(
                select(AlertRuleModel).where(AlertRuleModel.name == rule.name)
            )
            if result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="规则名称已存在")

            alert_rule = AlertRuleModel(
                name=rule.name,
                description=rule.description,
                metric_name=rule.metric_name,
                operator=rule.operator,
                threshold=rule.threshold,
                duration_seconds=rule.duration_seconds,
                severity=rule.severity,
                notify_channels=rule.notify_channels,
                notify_receivers=rule.notify_receivers
            )
            session.add(alert_rule)
            await session.flush()

            return {
                "success": True,
                "message": "告警规则创建成功",
                "rule": alert_rule.to_dict()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create alert rule: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/alert-rules")
async def list_alert_rules(
    enabled: Optional[bool] = Query(None, description="是否启用"),
    limit: int = Query(50, description="返回数量限制")
) -> Dict[str, Any]:
    """获取告警规则列表"""
    from sqlalchemy import select
    async with db_manager.get_async_session() as session:
        try:
            query = select(AlertRuleModel)
            if enabled is not None:
                query = query.where(AlertRuleModel.enabled == enabled)
            query = query.limit(limit)

            result = await session.execute(query)
            rules = result.scalars().all()

            return {
                "success": True,
                "rules": [r.to_dict() for r in rules],
                "count": len(rules)
            }
        except Exception as e:
            logger.error(f"Failed to list alert rules: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/alert-rules/{rule_id}")
async def get_alert_rule(rule_id: str) -> Dict[str, Any]:
    """获取告警规则详情"""
    from sqlalchemy import select
    async with db_manager.get_async_session() as session:
        try:
            result = await session.execute(
                select(AlertRuleModel).where(AlertRuleModel.id == rule_id)
            )
            rule = result.scalar_one_or_none()

            if not rule:
                raise HTTPException(status_code=404, detail="规则不存在")

            return {
                "success": True,
                "rule": rule.to_dict()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get alert rule: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.put("/alert-rules/{rule_id}")
async def update_alert_rule(rule_id: str, rule_update: AlertRuleUpdate) -> Dict[str, Any]:
    """更新告警规则"""
    from sqlalchemy import select, update
    async with db_manager.get_async_session() as session:
        try:
            # 获取现有规则
            result = await session.execute(
                select(AlertRuleModel).where(AlertRuleModel.id == rule_id)
            )
            rule = result.scalar_one_or_none()

            if not rule:
                raise HTTPException(status_code=404, detail="规则不存在")

            # 更新字段
            update_data = rule_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(rule, field, value)

            await session.flush()

            return {
                "success": True,
                "message": "告警规则更新成功",
                "rule": rule.to_dict()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update alert rule: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(rule_id: str) -> Dict[str, Any]:
    """删除告警规则"""
    from sqlalchemy import select, delete
    async with db_manager.get_async_session() as session:
        try:
            result = await session.execute(
                delete(AlertRuleModel).where(AlertRuleModel.id == rule_id)
            )

            if result.rowcount > 0:
                return {
                    "success": True,
                    "message": "告警规则删除成功"
                }
            else:
                raise HTTPException(status_code=404, detail="规则不存在")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete alert rule: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/alert-rules/{rule_id}/silence")
async def silence_alert_rule(
    rule_id: str,
    duration_minutes: int = Query(60, description="静默时长（分钟）")
) -> Dict[str, Any]:
    """静默告警规则"""
    from sqlalchemy import select
    async with db_manager.get_async_session() as session:
        try:
            from datetime import timedelta
            result = await session.execute(
                select(AlertRuleModel).where(AlertRuleModel.id == rule_id)
            )
            rule = result.scalar_one_or_none()

            if not rule:
                raise HTTPException(status_code=404, detail="规则不存在")

            rule.silenced = True
            rule.silenced_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
            await session.flush()

            return {
                "success": True,
                "message": f"告警规则已静默 {duration_minutes} 分钟",
                "rule": rule.to_dict()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to silence alert rule: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============ 告警记录接口 ============

@router.get("/alerts")
async def list_alerts(
    status: Optional[str] = Query(None, description="告警状态 (firing, resolved, acknowledged)"),
    severity: Optional[str] = Query(None, description="告警级别"),
    rule_id: Optional[str] = Query(None, description="规则 ID"),
    hours: int = Query(24, description="查询时长（小时）"),
    limit: int = Query(100, description="返回数量限制")
) -> Dict[str, Any]:
    """获取告警记录列表"""
    from sqlalchemy import select, and_
    async with db_manager.get_async_session() as session:
        try:
            from datetime import timedelta
            query = select(AlertModel).where(
                AlertModel.fired_at >= datetime.utcnow() - timedelta(hours=hours)
            )

            if status:
                query = query.where(AlertModel.status == status)
            if severity:
                query = query.where(AlertModel.severity == severity)
            if rule_id:
                query = query.where(AlertModel.rule_id == rule_id)

            query = query.limit(limit)
            result = await session.execute(query)
            alerts = result.scalars().all()

            return {
                "success": True,
                "alerts": [a.to_dict() for a in alerts],
                "count": len(alerts)
            }
        except Exception as e:
            logger.error(f"Failed to list alerts: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str) -> Dict[str, Any]:
    """获取告警详情"""
    from sqlalchemy import select
    async with db_manager.get_async_session() as session:
        try:
            result = await session.execute(
                select(AlertModel).where(AlertModel.id == alert_id)
            )
            alert = result.scalar_one_or_none()

            if not alert:
                raise HTTPException(status_code=404, detail="告警不存在")

            return {
                "success": True,
                "alert": alert.to_dict()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get alert: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user_id: str) -> Dict[str, Any]:
    """确认告警"""
    from sqlalchemy import select
    async with db_manager.get_async_session() as session:
        try:
            result = await session.execute(
                select(AlertModel).where(AlertModel.id == alert_id)
            )
            alert = result.scalar_one_or_none()

            if not alert:
                raise HTTPException(status_code=404, detail="告警不存在")

            alert.status = "acknowledged"
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = user_id
            await session.flush()

            return {
                "success": True,
                "message": "告警已确认",
                "alert": alert.to_dict()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============ 系统健康接口 ============

@router.get("/health")
async def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态"""
    from sqlalchemy import select, desc
    async with db_manager.get_async_session() as session:
        try:
            result = await session.execute(
                select(SystemHealthModel).order_by(desc(SystemHealthModel.timestamp)).limit(1)
            )
            health = result.scalar_one_or_none()

            if health:
                return {
                    "success": True,
                    "health": health.to_dict()
                }
            else:
                return {
                    "success": True,
                    "health": None,
                    "message": "暂无健康数据"
                }
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============ 重试服务接口 ============

@router.get("/retry/stats")
async def get_retry_stats(func_name: Optional[str] = Query(None, description="函数名称")) -> Dict[str, Any]:
    """获取重试统计信息"""
    try:
        stats = retry_service.get_stats(func_name)
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get retry stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry/stats/reset")
async def reset_retry_stats(func_name: Optional[str] = Query(None, description="函数名称")) -> Dict[str, Any]:
    """重置重试统计"""
    try:
        retry_service.reset_stats(func_name)
        return {
            "success": True,
            "message": f"统计已重置：{func_name or 'all'}"
        }
    except Exception as e:
        logger.error(f"Failed to reset retry stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retry/dead-letter")
async def get_dead_letter_entries(
    limit: int = Query(100, description="返回数量限制"),
    error_type: Optional[str] = Query(None, description="错误类型"),
    hours: int = Query(24, description="查询时长（小时）")
) -> Dict[str, Any]:
    """获取死信队列条目"""
    try:
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(hours=hours)
        entries = retry_service.dead_letter_queue.get_entries(
            limit=limit,
            error_type=error_type,
            since=since
        )
        return {
            "success": True,
            "entries": entries,
            "count": len(entries),
            "total_count": retry_service.dead_letter_queue.count()
        }
    except Exception as e:
        logger.error(f"Failed to get dead letter entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/retry/dead-letter/{entry_id}")
async def delete_dead_letter_entry(entry_id: int) -> Dict[str, Any]:
    """删除死信队列条目"""
    try:
        if retry_service.dead_letter_queue.delete(entry_id):
            return {
                "success": True,
                "message": "条目已删除"
            }
        else:
            raise HTTPException(status_code=404, detail="条目不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dead letter entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry/dead-letter/clear")
async def clear_dead_letter_queue(
    older_than_hours: Optional[int] = Query(None, description="清理早于此时长的条目")
) -> Dict[str, Any]:
    """清理死信队列"""
    try:
        from datetime import datetime, timedelta
        older_than = None
        if older_than_hours:
            older_than = datetime.utcnow() - timedelta(hours=older_than_hours)

        deleted = retry_service.dead_letter_queue.clear(older_than=older_than)
        return {
            "success": True,
            "message": f"已清理 {deleted} 条条目"
        }
    except Exception as e:
        logger.error(f"Failed to clear dead letter queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))
