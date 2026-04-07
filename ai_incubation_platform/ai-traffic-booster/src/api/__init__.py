"""
API 路由模块
"""
from .data_sources import router as data_sources_router
from .dashboard import router as dashboard_router

__all__ = ['data_sources_router', 'dashboard_router']
