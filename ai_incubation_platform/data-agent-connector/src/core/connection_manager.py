"""
统一连接管理器
管理所有数据源连接的生命周期，提供全局统一的连接访问
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
from connectors.base import BaseConnector, ConnectorFactory, ConnectorConfig
from config.settings import settings, get_datasource_credentials
from utils.logger import logger
from connectors.base import ConnectorError


class ConnectionManager:
    """全局连接管理器"""

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._connection_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_connector(self, name: str) -> Optional[BaseConnector]:
        """获取连接器实例"""
        async with self._lock:
            connector = self._connectors.get(name)
            if connector:
                # 更新访问时间
                if name in self._connection_metadata:
                    self._connection_metadata[name]["last_accessed"] = datetime.utcnow()
            return connector

    async def create_connector(
        self,
        connector_type: str,
        config: ConnectorConfig,
        created_by: str = "system",
        role: str = "read_only"
    ) -> BaseConnector:
        """创建并连接数据源"""
        async with self._lock:
            if config.name in self._connectors:
                # 已存在的连接，先断开
                await self._disconnect_connector(config.name)

            # 若未显式提供连接串，则从 datasource_name 的环境变量/密钥管理中解析
            if not config.connection_string:
                datasource_name = config.datasource_name or config.name
                credentials = get_datasource_credentials(datasource_name)
                if not credentials:
                    raise ConnectorError(
                        f"Missing credentials for datasource '{datasource_name}'. "
                        f"Set env vars like {settings.credential.env_prefix}{datasource_name.upper()}_*"
                    )
                config.connection_string = self._build_connection_string(connector_type, credentials)

            # 创建连接器实例
            connector = ConnectorFactory.create(connector_type, config)

            try:
                # 建立连接
                await connector.connect()

                # 存储连接器和元数据
                self._connectors[config.name] = connector
                self._connection_metadata[config.name] = {
                    "connector_type": connector_type,
                    "created_at": datetime.utcnow(),
                    "last_accessed": datetime.utcnow(),
                    "created_by": created_by,
                    "role": role,
                    "query_count": 0
                }

                logger.info(
                    "Connector created",
                    extra={
                        "connector_name": config.name,
                        "connector_type": connector_type,
                        "created_by": created_by,
                        "role": role
                    }
                )

                return connector

            except Exception as e:
                logger.error(
                    "Failed to create connector",
                    extra={
                        "connector_name": config.name,
                        "connector_type": connector_type,
                        "error": str(e)
                    }
                )
                raise

    async def remove_connector(self, name: str) -> bool:
        """移除并断开连接器"""
        async with self._lock:
            return await self._disconnect_connector(name)

    async def _disconnect_connector(self, name: str) -> bool:
        """内部方法：断开连接器（需要在锁内调用）"""
        if name not in self._connectors:
            return False

        try:
            await self._connectors[name].disconnect()
        except Exception as e:
            logger.warning(
                "Error disconnecting connector",
                extra={"connector_name": name, "error": str(e)}
            )

        del self._connectors[name]
        if name in self._connection_metadata:
            del self._connection_metadata[name]

        logger.info("Connector removed", extra={"connector_name": name})
        return True

    async def list_connectors(self) -> List[Dict[str, Any]]:
        """列出所有活跃连接器"""
        async with self._lock:
            result = []
            for name, connector in self._connectors.items():
                metadata = self._connection_metadata.get(name, {})
                result.append({
                    "name": name,
                    "type": type(connector).__name__,
                    "connector_type": metadata.get("connector_type"),
                    "is_connected": connector.is_connected,
                    "created_at": metadata.get("created_at"),
                    "last_accessed": metadata.get("last_accessed"),
                    "created_by": metadata.get("created_by"),
                    "role": metadata.get("role"),
                    "query_count": metadata.get("query_count", 0)
                })
            return result

    async def increment_query_count(self, name: str) -> None:
        """增加查询计数"""
        async with self._lock:
            if name in self._connection_metadata:
                self._connection_metadata[name]["query_count"] += 1

    async def cleanup_idle_connections(self) -> int:
        """清理空闲超时的连接"""
        async with self._lock:
            idle_timeout = timedelta(seconds=settings.connector.idle_timeout)
            now = datetime.utcnow()
            removed_count = 0

            for name in list(self._connectors.keys()):
                metadata = self._connection_metadata.get(name, {})
                last_accessed = metadata.get("last_accessed")
                if last_accessed and (now - last_accessed) > idle_timeout:
                    await self._disconnect_connector(name)
                    removed_count += 1

            if removed_count > 0:
                logger.info(
                    "Cleaned up idle connections",
                    extra={"removed_count": removed_count}
                )

            return removed_count

    async def shutdown(self) -> None:
        """关闭所有连接"""
        async with self._lock:
            for name in list(self._connectors.keys()):
                await self._disconnect_connector(name)
            logger.info("All connections closed during shutdown")

    def _build_connection_string(self, connector_type: str, credentials: Dict[str, Any]) -> str:
        """
        从凭据字段拼装连接串。
        优先使用 credentials['connection_string']，便于兼容任意 DSN/URI。
        """
        conn_str = credentials.get("connection_string") or credentials.get("dsn") or credentials.get("uri")
        if conn_str:
            return str(conn_str)

        # SQL 系连接串：mysql / postgresql
        if connector_type in {"mysql", "postgresql"}:
            host = credentials.get("host")
            port = credentials.get("port")
            user = credentials.get("user") or credentials.get("username")
            password = credentials.get("password")
            database = credentials.get("database") or credentials.get("db")
            if not host or not user or not database:
                raise ConnectorError(
                    f"Insufficient credentials for {connector_type}. Need host/user/database (and optional port/password)."
                )
            port = int(port) if port else (3306 if connector_type == "mysql" else 5432)
            scheme = connector_type
            password_part = f":{password}" if password is not None else ""
            return f"{scheme}://{user}{password_part}@{host}:{port}/{database}"

        # SQLite：sqlite:///{path}
        if connector_type == "sqlite":
            path = credentials.get("path") or credentials.get("file") or credentials.get("database") or credentials.get("db")
            if not path:
                raise ConnectorError("Insufficient credentials for sqlite. Need path.")
            return f"sqlite:///{path}"

        # Elasticsearch
        if connector_type == "elasticsearch":
            host = credentials.get("host")
            port = credentials.get("port")
            scheme = credentials.get("scheme") or "http"
            if not host:
                raise ConnectorError("Insufficient credentials for elasticsearch. Need host or connection_string.")
            if port:
                return f"{scheme}://{host}:{int(port)}"
            return f"{scheme}://{host}"

        # MongoDB
        if connector_type == "mongodb":
            host = credentials.get("host")
            port = credentials.get("port") or 27017
            user = credentials.get("user") or credentials.get("username")
            password = credentials.get("password")
            database = credentials.get("database") or credentials.get("db")
            if not host:
                raise ConnectorError("Insufficient credentials for mongodb. Need host or connection_string.")
            auth_part = ""
            if user:
                password_part = f":{password}" if password else ""
                auth_part = f"{user}{password_part}@"
            db_part = f"/{database}" if database else ""
            return f"mongodb://{auth_part}{host}:{int(port)}{db_part}"

        # Redis：redis://[:password]@host:port
        if connector_type == "redis":
            host = credentials.get("host")
            port = credentials.get("port") or 6379
            password = credentials.get("password")
            if not host:
                raise ConnectorError("Insufficient credentials for redis. Need host or connection_string.")
            if password:
                return f"redis://:{password}@{host}:{int(port)}"
            return f"redis://{host}:{int(port)}"

        # REST API：需要 base_url
        if connector_type == "rest_api":
            host = credentials.get("host")
            port = credentials.get("port")
            scheme = credentials.get("scheme") or "http"
            if host:
                if port:
                    return f"{scheme}://{host}:{int(port)}"
                return f"{scheme}://{host}"
            raise ConnectorError("Insufficient credentials for rest_api. Need base URL fields or connection_string.")

        raise ConnectorError(f"Unsupported connector_type for env-based connection string building: {connector_type}")


# 全局连接管理器实例
connection_manager = ConnectionManager()
