"""
Neo4j 图数据库连接器 - 异步
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError, HealthStatus


class Neo4jConnector(BaseConnector):
    """Neo4j 图数据库连接器（使用 neo4j 异步驱动）"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._driver = None
        self._session = None

    async def connect(self) -> None:
        """建立 Neo4j 连接"""
        try:
            from neo4j import AsyncGraphDatabase

            parsed = self._parse_connection_string()

            uri = f"bolt://{parsed.get('host', 'localhost')}:{parsed.get('port', 7687)}"

            self._driver = AsyncGraphDatabase.driver(
                uri,
                auth=(parsed.get('user', 'neo4j'), parsed.get('password', 'password')),
            )

            # 验证连接
            await self._driver.verify_connectivity()
            self._connected = True

        except Exception as e:
            raise ConnectorError(f"Failed to connect to Neo4j: {e}")

    async def disconnect(self) -> None:
        """断开 Neo4j 连接"""
        if self._session:
            await self._session.close()
        if self._driver:
            await self._driver.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        执行 Cypher 查询
        支持查询语法：
        - "MATCH (n) RETURN n LIMIT 10" - 查询节点
        - "MATCH (n)-[r]-(m) RETURN n, r, m" - 查询关系
        - "CREATE (n:Person {name: 'Alice'})" - 创建节点
        - "MATCH (n) WHERE n.name = 'Alice' DELETE n" - 删除节点
        """
        if not self._connected:
            raise ConnectorError("Not connected to Neo4j")

        try:
            async with self._driver.session() as session:
                result = await session.run(query, params or {})
                records = await result.data()

                # 转换记录为字典列表
                return [dict(record) for record in records]

        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取 Neo4j 图结构（节点标签、关系类型、属性）"""
        if not self._connected:
            raise ConnectorError("Not connected to Neo4j")

        try:
            async with self._driver.session() as session:
                schema = {
                    "labels": [],
                    "relationship_types": [],
                    "property_keys": [],
                }

                # 获取所有节点标签
                result = await session.run("CALL db.labels()")
                labels = await result.data()
                schema["labels"] = [record["label"] for record in labels]

                # 获取所有关系类型
                result = await session.run("CALL db.relationshipTypes()")
                rel_types = await result.data()
                schema["relationship_types"] = [record["relationshipType"] for record in rel_types]

                # 获取所有属性键
                result = await session.run("CALL db.propertyKeys()")
                prop_keys = await result.data()
                schema["property_keys"] = [record["propertyKey"] for record in prop_keys]

                # 获取每个标签的示例和属性
                schema["label_details"] = {}
                for label in schema["labels"]:
                    # 获取示例节点
                    result = await session.run(
                        f"MATCH (n:`{label}`) RETURN n LIMIT 5"
                    )
                    nodes = await result.data()

                    # 提取属性
                    properties = set()
                    for node in nodes:
                        for key in node["n"].keys():
                            properties.add(key)

                    schema["label_details"][label] = {
                        "properties": list(properties),
                        "sample_count": len(nodes),
                    }

                # 获取关系详情
                schema["relationship_details"] = {}
                for rel_type in schema["relationship_types"]:
                    result = await session.run(
                        f"MATCH ()-[r:`{rel_type}`]->() RETURN type(r) as type, properties(r) as props LIMIT 5"
                    )
                    rels = await result.data()

                    properties = set()
                    for rel in rels:
                        for key in rel["props"].keys():
                            properties.add(key)

                    schema["relationship_details"][rel_type] = {
                        "properties": list(properties),
                    }

                return {"graph": schema}

        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    async def health_check(self) -> HealthStatus:
        """Neo4j 健康检查"""
        import time
        start_time = time.time()

        try:
            if not self._connected:
                await self.connect()

            # 执行简单的查询
            await self.execute("RETURN 1")

            latency_ms = (time.time() - start_time) * 1000

            return HealthStatus(
                status="healthy",
                latency_ms=round(latency_ms, 2),
                message="Neo4j connection OK",
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="neo4j",
                connector_name=self.config.name
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                status="unhealthy",
                latency_ms=round(latency_ms, 2),
                message=str(e),
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="neo4j",
                connector_name=self.config.name
            )

    async def get_node_count(self, label: Optional[str] = None) -> int:
        """获取节点数量"""
        if label:
            result = await self.execute(f"MATCH (n:`{label}`) RETURN count(n) as count")
        else:
            result = await self.execute("MATCH (n) RETURN count(n) as count")
        return result[0]["count"] if result else 0

    async def get_relationship_count(self, rel_type: Optional[str] = None) -> int:
        """获取关系数量"""
        if rel_type:
            result = await self.execute(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count")
        else:
            result = await self.execute("MATCH ()-[r]->() RETURN count(r) as count")
        return result[0]["count"] if result else 0

    async def get_indexes(self) -> List[Dict[str, Any]]:
        """获取索引信息"""
        if not self._connected:
            raise ConnectorError("Not connected to Neo4j")

        try:
            async with self._driver.session() as session:
                result = await session.run("SHOW INDEXES")
                indexes = await result.data()
                return [dict(idx) for idx in indexes]
        except Exception as e:
            raise ConnectorError(f"Failed to get indexes: {e}")

    async def create_index(
        self,
        label: str,
        properties: List[str],
        index_type: str = "BTREE"
    ) -> Dict[str, Any]:
        """创建索引"""
        props_str = ", ".join([f"n.`{p}`" for p in properties])
        index_name = f"index_{label}_{'_'.join(properties)}"

        query = f"CREATE INDEX {index_name} FOR (n:`{label}`) ON ({props_str})"
        await self.execute(query)

        return {
            "name": index_name,
            "label": label,
            "properties": properties,
            "type": index_type,
        }

    async def create_constraint(
        self,
        label: str,
        property: str,
        constraint_type: str = "UNIQUE"
    ) -> Dict[str, Any]:
        """创建约束"""
        constraint_name = f"constraint_{label}_{property}"

        if constraint_type == "UNIQUE":
            query = f"CREATE CONSTRAINT {constraint_name} FOR (n:`{label}`) REQUIRE n.`{property}` IS UNIQUE"
        else:
            query = f"CREATE CONSTRAINT {constraint_name} FOR (n:`{label}`) REQUIRE n.`{property}` IS NOT NULL"

        await self.execute(query)

        return {
            "name": constraint_name,
            "label": label,
            "property": property,
            "type": constraint_type,
        }

    async def explain_query(self, query: str) -> Dict[str, Any]:
        """获取查询执行计划"""
        result = await self.execute(f"EXPLAIN {query}")
        return {"plan": "Query planned (Neo4j does not return detailed plan via Cypher)"}

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析连接字符串
        格式：neo4j://user:password@host:port
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 7687,
            'user': parsed.username or query_params.get('user', ['neo4j'])[0],
            'password': parsed.password or query_params.get('password', ['password'])[0],
        }


# 导出
__all__ = ["Neo4jConnector"]
