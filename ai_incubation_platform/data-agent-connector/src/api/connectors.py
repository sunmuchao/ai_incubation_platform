"""
连接器 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connectors.base import ConnectorConfig, ConnectorFactory
from core.connection_manager import connection_manager
from .deps import verify_api_key, get_user_role
from utils.logger import logger

router = APIRouter(prefix="/api/connectors", tags=["connectors"], dependencies=[Depends(verify_api_key)])


@router.get("/types")
async def list_connector_types():
    """获取支持的连接器类型"""
    try:
        return {"types": ConnectorFactory.list_types()}
    except Exception as e:
        logger.error("Failed to list connector types", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{connector_id}/connect")
async def connect_connector(
    connector_id: str,
    config: ConnectorConfig,
    role: str = Depends(get_user_role)
):
    """创建并连接数据源"""
    try:
        await connection_manager.create_connector(
            connector_type=connector_id,
            config=config,
            role=role
        )
        return {"message": f"Connected to {config.name}", "status": "connected"}
    except Exception as e:
        logger.error(
            "Failed to connect connector",
            extra={
                "connector_id": connector_id,
                "connector_name": config.name,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{connector_id}/disconnect")
async def disconnect_connector(connector_id: str, name: str):
    """断开数据源连接"""
    try:
        success = await connection_manager.remove_connector(name)
        if not success:
            raise HTTPException(status_code=404, detail="Connector not found")
        return {"message": f"Disconnected from {name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disconnect connector", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/active")
async def list_active_connectors():
    """获取活跃连接器列表"""
    try:
        active = await connection_manager.list_connectors()
        return {"active": active}
    except Exception as e:
        logger.error("Failed to list active connectors", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{name}/schema")
async def get_connector_schema(name: str):
    """获取数据源结构"""
    try:
        connector = await connection_manager.get_connector(name)
        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        schema = await connector.get_schema()
        return schema
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get connector schema", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")
