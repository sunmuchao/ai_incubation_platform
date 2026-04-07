"""
MongoDB 连接器 - 异步
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError


class MongoDBConnector(BaseConnector):
    """MongoDB 数据库连接器（使用 motor 异步驱动）"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client = None
        self._db = None

    async def connect(self) -> None:
        """建立 MongoDB 连接"""
        try:
            import motor.motor_asyncio
            self._client = motor.motor_asyncio.AsyncIOMotorClient(
                self.config.connection_string,
                serverSelectionTimeoutMS=self.config.timeout * 1000
            )
            # 解析数据库名
            db_name = self._parse_database_name()
            self._db = self._client[db_name]

            # 测试连接
            await self._client.admin.command('ping')
            self._connected = True
        except Exception as e:
            raise ConnectorError(f"Failed to connect to MongoDB: {e}")

    async def disconnect(self) -> None:
        """断开 MongoDB 连接"""
        if self._client:
            self._client.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        执行 MongoDB 查询
        支持简化的查询语法:
        - "find collection_name {filter}" - 查询文档
        - "insert collection_name {doc}" - 插入文档
        - "update collection_name {filter} {update}" - 更新文档
        - "delete collection_name {filter}" - 删除文档
        - "aggregate collection_name {pipeline}" - 聚合查询
        """
        if not self._connected:
            raise ConnectorError("Not connected to database")

        try:
            import json
            parts = query.split(maxsplit=2)
            operation = parts[0].lower()
            collection_name = parts[1]
            collection = self._db[collection_name]

            if operation == "find":
                filter_doc = json.loads(parts[2]) if len(parts) > 2 else {}
                cursor = collection.find(filter_doc)
                return await cursor.to_list(length=None)

            elif operation == "insert":
                doc = json.loads(parts[2]) if len(parts) > 2 else {}
                result = await collection.insert_one(doc)
                return [{"_id": str(result.inserted_id), "status": "inserted"}]

            elif operation == "update":
                update_parts = query.split(maxsplit=3)
                filter_doc = json.loads(update_parts[2]) if len(update_parts) > 2 else {}
                update_doc = json.loads(update_parts[3]) if len(update_parts) > 3 else {}
                result = await collection.update_many(filter_doc, {"$set": update_doc})
                return [{"matched": result.matched_count, "modified": result.modified_count}]

            elif operation == "delete":
                filter_doc = json.loads(parts[2]) if len(parts) > 2 else {}
                result = await collection.delete_many(filter_doc)
                return [{"deleted_count": result.deleted_count}]

            elif operation == "aggregate":
                pipeline = json.loads(parts[2]) if len(parts) > 2 else []
                cursor = collection.aggregate(pipeline)
                return await cursor.to_list(length=None)

            else:
                raise ConnectorError(f"Unknown operation: {operation}")

        except json.JSONDecodeError as e:
            raise ConnectorError(f"Invalid JSON in query: {e}")
        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库结构（集合列表和示例文档）"""
        if not self._connected:
            raise ConnectorError("Not connected to database")

        collections = await self._db.list_collection_names()
        schema = {}

        for collection_name in collections:
            collection = self._db[collection_name]
            # 获取文档计数
            count = await collection.count_documents({})
            # 获取示例文档
            sample = await collection.find_one()

            schema[collection_name] = {
                "document_count": count,
                "sample_document": sample,
                "fields": list(sample.keys()) if sample else []
            }

        return {"collections": schema}

    def _parse_database_name(self) -> str:
        """从连接字符串解析数据库名"""
        from urllib.parse import urlparse
        parsed = urlparse(self.config.connection_string)
        path = parsed.path.lstrip('/')
        return path if path else "default"

    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """获取集合统计信息"""
        collection = self._db[collection_name]
        stats = await collection.command("collstats", collection_name)
        return stats

    async def create_index(self, collection_name: str, keys: List[str], unique: bool = False) -> str:
        """创建索引"""
        collection = self._db[collection_name]
        index_name = await collection.create_index(
            [(key, 1) for key in keys],
            unique=unique
        )
        return index_name

    async def drop_index(self, collection_name: str, index_name: str) -> None:
        """删除索引"""
        collection = self._db[collection_name]
        await collection.drop_index(index_name)


# 导出
__all__ = ["MongoDBConnector"]
