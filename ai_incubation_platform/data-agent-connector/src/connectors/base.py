"""
连接器基类 - v1.4 增强版
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
import time


@dataclass
class HealthStatus:
    """健康状态"""
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: float  # 延迟（毫秒）
    message: str  # 详细信息
    timestamp: str  # 时间戳
    connector_type: str  # 连接器类型
    connector_name: str  # 连接器名称


@dataclass
class ConnectorConfig:
    """连接器配置"""
    name: str
    # 从 API 或环境解析出的连接串。若为空，则可由 connection_manager 基于 datasource_name 拼装。
    connection_string: Optional[str] = None
    # 数据源名称，用于从环境变量/密钥管理器加载连接凭据并拼装连接串
    datasource_name: Optional[str] = None
    timeout: int = 30
    max_connections: int = 10


class ConnectorError(Exception):
    """连接器异常"""
    pass


class BaseConnector(ABC):
    """数据连接器基类"""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行查询"""
        pass

    @abstractmethod
    async def get_schema(self) -> Dict[str, Any]:
        """获取数据结构/模式"""
        pass

    async def health_check(self) -> HealthStatus:
        """
        健康检查（默认实现）
        子类应重写此方法以提供特定于数据源的健康检查逻辑
        """
        start_time = time.time()
        try:
            if not self._connected:
                await self.connect()

            # 执行简单的健康检查查询
            await self._do_health_check_query()

            latency_ms = (time.time() - start_time) * 1000

            return HealthStatus(
                status="healthy",
                latency_ms=round(latency_ms, 2),
                message="Connection OK",
                timestamp=datetime.utcnow().isoformat(),
                connector_type=self.__class__.__name__,
                connector_name=self.config.name
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                status="unhealthy",
                latency_ms=round(latency_ms, 2),
                message=str(e),
                timestamp=datetime.utcnow().isoformat(),
                connector_type=self.__class__.__name__,
                connector_name=self.config.name
            )

    async def _do_health_check_query(self) -> None:
        """
        执行健康检查查询（默认实现）
        子类应重写此方法以提供特定于数据源的检查查询
        """
        # 尝试执行一个简单的查询来验证连接
        try:
            await self.execute("SELECT 1")
        except Exception:
            # 如果 SELECT 1 失败，可能是非 SQL 数据源，子类应重写此方法
            pass

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


class ConnectorFactory:
    """连接器工厂"""
    _connectors: Dict[str, type] = {}
    _instances: Dict[str, BaseConnector] = {}  # 连接器实例注册中心

    @classmethod
    def register(cls, connector_type: str, connector_class: type):
        cls._connectors[connector_type] = connector_class

    @classmethod
    def create(cls, connector_type: str, config: ConnectorConfig) -> BaseConnector:
        if connector_type not in cls._connectors:
            raise ConnectorError(f"Unknown connector type: {connector_type}")
        connector = cls._connectors[connector_type](config)
        # 注册实例
        cls._instances[config.name] = connector
        return connector

    @classmethod
    def get_instance(cls, name: str) -> Optional[BaseConnector]:
        """获取已注册的连接器实例"""
        return cls._instances.get(name)

    @classmethod
    def list_types(cls) -> List[str]:
        """列出所有支持的连接器类型"""
        return list(cls._connectors.keys())

    @classmethod
    def list_instances(cls) -> List[str]:
        """列出所有已注册的连接器实例"""
        return list(cls._instances.keys())

    @classmethod
    async def health_check_all(cls) -> Dict[str, HealthStatus]:
        """批量健康检查所有已注册的连接器"""
        results = {}
        for name, instance in cls._instances.items():
            if instance.is_connected:
                results[name] = await instance.health_check()
        return results

    @classmethod
    def get_connector_info(cls) -> Dict[str, Any]:
        """获取所有连接器的元信息"""
        return {
            "supported_types": list(cls._connectors.keys()),
            "active_instances": list(cls._instances.keys()),
            "total_types": len(cls._connectors),
            "total_instances": len(cls._instances)
        }


# 注册内置连接器
def register_builtin_connectors():
    from connectors.database import MySQLConnector, PostgreSQLConnector
    from connectors.api_connector import RESTAPIConnector
    from connectors.mongodb import MongoDBConnector
    from connectors.redis import RedisConnector
    from connectors.sqlite import SQLiteConnector
    from connectors.elasticsearch import ElasticsearchConnector
    from connectors.snowflake import SnowflakeConnector
    from connectors.oracle import OracleConnector
    from connectors.sqlserver import SQLServerConnector
    from connectors.kafka import KafkaConnector
    from connectors.csv_file import CSVConnector
    from connectors.bigquery import BigQueryConnector
    from connectors.clickhouse import ClickHouseConnector
    from connectors.starrocks import StarRocksConnector
    from connectors.databricks import DatabricksConnector
    # v1.4 新增连接器
    from connectors.hive import HiveConnector
    from connectors.presto import PrestoConnector
    from connectors.neo4j import Neo4jConnector
    from connectors.s3 import S3Connector
    from connectors.graphql import GraphQLConnector

    ConnectorFactory.register("mysql", MySQLConnector)
    ConnectorFactory.register("postgresql", PostgreSQLConnector)
    ConnectorFactory.register("rest_api", RESTAPIConnector)
    ConnectorFactory.register("mongodb", MongoDBConnector)
    ConnectorFactory.register("redis", RedisConnector)
    ConnectorFactory.register("sqlite", SQLiteConnector)
    ConnectorFactory.register("elasticsearch", ElasticsearchConnector)
    ConnectorFactory.register("snowflake", SnowflakeConnector)
    ConnectorFactory.register("oracle", OracleConnector)
    ConnectorFactory.register("sqlserver", SQLServerConnector)
    ConnectorFactory.register("kafka", KafkaConnector)
    ConnectorFactory.register("csv", CSVConnector)
    ConnectorFactory.register("bigquery", BigQueryConnector)
    ConnectorFactory.register("clickhouse", ClickHouseConnector)
    ConnectorFactory.register("starrocks", StarRocksConnector)
    ConnectorFactory.register("doris", StarRocksConnector)
    ConnectorFactory.register("databricks", DatabricksConnector)
    # v1.4 新增连接器注册
    ConnectorFactory.register("hive", HiveConnector)
    ConnectorFactory.register("presto", PrestoConnector)
    ConnectorFactory.register("neo4j", Neo4jConnector)
    ConnectorFactory.register("s3", S3Connector)
    ConnectorFactory.register("graphql", GraphQLConnector)
