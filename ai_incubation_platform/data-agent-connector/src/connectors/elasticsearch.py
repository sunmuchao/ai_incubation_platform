"""
Elasticsearch 连接器 - 异步
"""
from typing import Any, Dict, List, Optional
import json
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError


class ElasticsearchConnector(BaseConnector):
    """Elasticsearch 数据库连接器（使用 elasticsearch 异步客户端）"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client = None

    async def connect(self) -> None:
        """建立 Elasticsearch 连接"""
        try:
            from elasticsearch import AsyncElasticsearch
            self._client = AsyncElasticsearch(
                self.config.connection_string,
                request_timeout=self.config.timeout
            )
            # 测试连接
            await self._client.info()
            self._connected = True
        except Exception as e:
            raise ConnectorError(f"Failed to connect to Elasticsearch: {e}")

    async def disconnect(self) -> None:
        """断开 Elasticsearch 连接"""
        if self._client:
            await self._client.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        执行 Elasticsearch 查询
        支持简化的查询语法:
        - "search index_name {query}" - 搜索文档
        - "get index_name doc_id" - 获取文档
        - "index index_name {doc}" - 索引文档
        - "update index_name doc_id {doc}" - 更新文档
        - "delete index_name doc_id" - 删除文档
        - "count index_name {query}" - 统计文档数量
        """
        if not self._connected:
            raise ConnectorError("Not connected to Elasticsearch")

        try:
            parts = query.split(maxsplit=2)
            operation = parts[0].lower()
            index_name = parts[1]

            if operation == "search":
                query_body = json.loads(parts[2]) if len(parts) > 2 else {"query": {"match_all": {}}}
                response = await self._client.search(index=index_name, **query_body)
                hits = response["hits"]["hits"]
                return [
                    {
                        "_id": hit["_id"],
                        "_score": hit["_score"],
                        **hit["_source"]
                    }
                    for hit in hits
                ]

            elif operation == "get":
                doc_id = parts[2] if len(parts) > 2 else ""
                if not doc_id:
                    raise ConnectorError("Document ID is required for GET operation")
                response = await self._client.get(index=index_name, id=doc_id)
                return [{
                    "_id": response["_id"],
                    **response["_source"]
                }]

            elif operation == "index":
                doc = json.loads(parts[2]) if len(parts) > 2 else {}
                response = await self._client.index(index=index_name, document=doc)
                return [{
                    "_id": response["_id"],
                    "result": response["result"],
                    "_version": response["_version"]
                }]

            elif operation == "update":
                update_parts = query.split(maxsplit=3)
                doc_id = update_parts[2] if len(update_parts) > 2 else ""
                doc = json.loads(update_parts[3]) if len(update_parts) > 3 else {}
                if not doc_id:
                    raise ConnectorError("Document ID is required for UPDATE operation")
                response = await self._client.update(
                    index=index_name,
                    id=doc_id,
                    doc=doc
                )
                return [{
                    "_id": response["_id"],
                    "result": response["result"],
                    "_version": response["_version"]
                }]

            elif operation == "delete":
                doc_id = parts[2] if len(parts) > 2 else ""
                if not doc_id:
                    raise ConnectorError("Document ID is required for DELETE operation")
                response = await self._client.delete(index=index_name, id=doc_id)
                return [{
                    "_id": response["_id"],
                    "result": response["result"],
                    "_version": response["_version"]
                }]

            elif operation == "count":
                query_body = json.loads(parts[2]) if len(parts) > 2 else {"query": {"match_all": {}}}
                response = await self._client.count(index=index_name, **query_body)
                return [{"count": response["count"]}]

            else:
                raise ConnectorError(f"Unknown operation: {operation}")

        except json.JSONDecodeError as e:
            raise ConnectorError(f"Invalid JSON in query: {e}")
        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取索引结构"""
        if not self._connected:
            raise ConnectorError("Not connected to Elasticsearch")

        try:
            # 获取所有索引
            indices = await self._client.indices.get(index="*")
            schema = {}

            for index_name, index_info in indices.items():
                if index_name.startswith('.'):  # 跳过系统索引
                    continue

                mappings = index_info["mappings"]
                settings = index_info["settings"]

                # 获取文档数量
                count = await self._client.count(index=index_name)

                schema[index_name] = {
                    "mapping": mappings,
                    "settings": {
                        "number_of_shards": settings["index"]["number_of_shards"],
                        "number_of_replicas": settings["index"]["number_of_replicas"],
                        "creation_date": settings["index"]["creation_date"]
                    },
                    "document_count": count["count"]
                }

            return {"indices": schema}
        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    async def create_index(self, index_name: str, mappings: Dict[str, Any] = None, settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建索引"""
        response = await self._client.indices.create(
            index=index_name,
            mappings=mappings,
            settings=settings
        )
        return {"acknowledged": response["acknowledged"], "index": index_name}

    async def delete_index(self, index_name: str) -> Dict[str, Any]:
        """删除索引"""
        response = await self._client.indices.delete(index=index_name)
        return {"acknowledged": response["acknowledged"]}

    async def bulk_insert(self, index_name: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量插入文档"""
        from elasticsearch.helpers import async_bulk
        actions = [
            {
                "_index": index_name,
                "_source": doc
            }
            for doc in documents
        ]
        success, failed = await async_bulk(self._client, actions)
        return {"success": success, "failed": failed}


# 导出
__all__ = ["ElasticsearchConnector"]
