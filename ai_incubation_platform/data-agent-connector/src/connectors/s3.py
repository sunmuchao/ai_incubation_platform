"""
Amazon S3 / 对象存储连接器 - 异步
"""
import asyncio
import os
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError, HealthStatus


class S3Connector(BaseConnector):
    """
    Amazon S3 兼容对象存储连接器
    支持：AWS S3, MinIO, 阿里云 OSS, 腾讯云 COS 等
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client = None
        self._endpoint = None

    async def connect(self) -> None:
        """建立 S3 连接"""
        try:
            import aiobotocore.session

            parsed = self._parse_connection_string()

            session = aiobotocore.session.get_session()

            self._client = session.create_client(
                's3',
                aws_access_key_id=parsed.get('access_key', ''),
                aws_secret_access_key=parsed.get('secret_key', ''),
                endpoint_url=parsed.get('endpoint', None),
                region_name=parsed.get('region', 'us-east-1'),
            )

            self._endpoint = parsed.get('endpoint', 'https://s3.amazonaws.com')
            self._connected = True

        except Exception as e:
            raise ConnectorError(f"Failed to connect to S3: {e}")

    async def disconnect(self) -> None:
        """断开 S3 连接"""
        if self._client:
            await self._client.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        执行 S3 操作
        支持语法：
        - "LIST buckets" - 列出所有桶
        - "LIST objects FROM bucket_name" - 列出桶中对象
        - "GET object FROM bucket_name/key" - 获取对象
        - "PUT object TO bucket_name/key" - 上传对象（需在 params 中提供数据）
        - "DELETE object FROM bucket_name/key" - 删除对象
        """
        if not self._connected:
            raise ConnectorError("Not connected to S3")

        import re

        try:
            # 解析命令
            query_upper = query.upper().strip()

            if query_upper.startswith("LIST BUCKETS"):
                return await self._list_buckets()

            elif query_upper.startswith("LIST OBJECTS"):
                match = re.search(r'FROM\s+(\S+)', query, re.IGNORECASE)
                if match:
                    bucket = match.group(1)
                    prefix = params.get('prefix', '') if params else ''
                    return await self._list_objects(bucket, prefix)
                else:
                    raise ConnectorError("Missing bucket name in LIST OBJECTS")

            elif query_upper.startswith("GET OBJECT"):
                match = re.search(r'FROM\s+(\S+)', query, re.IGNORECASE)
                if match:
                    path = match.group(1)
                    bucket, key = self._parse_path(path)
                    return await self._get_object(bucket, key)
                else:
                    raise ConnectorError("Missing path in GET OBJECT")

            elif query_upper.startswith("PUT OBJECT"):
                match = re.search(r'TO\s+(\S+)', query, re.IGNORECASE)
                if match:
                    path = match.group(1)
                    bucket, key = self._parse_path(path)
                    data = params.get('data', b'') if params else b''
                    content_type = params.get('content_type', 'application/octet-stream')
                    return await self._put_object(bucket, key, data, content_type)
                else:
                    raise ConnectorError("Missing path in PUT OBJECT")

            elif query_upper.startswith("DELETE OBJECT"):
                match = re.search(r'FROM\s+(\S+)', query, re.IGNORECASE)
                if match:
                    path = match.group(1)
                    bucket, key = self._parse_path(path)
                    return await self._delete_object(bucket, key)
                else:
                    raise ConnectorError("Missing path in DELETE OBJECT")

            else:
                raise ConnectorError(f"Unknown S3 operation: {query}")

        except Exception as e:
            raise ConnectorError(f"S3 operation failed: {e}")

    async def _list_buckets(self) -> List[Dict[str, Any]]:
        """列出所有桶"""
        async with self._client as client:
            response = await client.list_buckets()
            return [
                {
                    "name": bucket["Name"],
                    "creation_date": str(bucket.get("CreationDate", "")),
                }
                for bucket in response.get("Buckets", [])
            ]

    async def _list_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        """列出桶中的对象"""
        async with self._client as client:
            paginator = client.get_paginator('list_objects_v2')
            objects = []

            async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    objects.append({
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": str(obj.get("LastModified", "")),
                        "etag": obj.get("ETag", ""),
                    })

            return objects

    async def _get_object(self, bucket: str, key: str) -> List[Dict[str, Any]]:
        """获取对象内容"""
        async with self._client as client:
            response = await client.get_object(Bucket=bucket, Key=key)
            body = await response["Body"].read()

            return [
                {
                    "bucket": bucket,
                    "key": key,
                    "content": body.decode('utf-8', errors='replace'),
                    "content_type": response.get("ContentType", "unknown"),
                    "size": response.get("ContentLength", 0),
                    "metadata": response.get("Metadata", {}),
                }
            ]

    async def _put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> List[Dict[str, Any]]:
        """上传对象"""
        async with self._client as client:
            response = await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

            return [
                {
                    "bucket": bucket,
                    "key": key,
                    "etag": response.get("ETag", ""),
                    "status": "uploaded",
                }
            ]

    async def _delete_object(self, bucket: str, key: str) -> List[Dict[str, Any]]:
        """删除对象"""
        async with self._client as client:
            await client.delete_object(Bucket=bucket, Key=key)

            return [
                {
                    "bucket": bucket,
                    "key": key,
                    "status": "deleted",
                }
            ]

    async def get_schema(self) -> Dict[str, Any]:
        """获取 S3 存储结构（桶列表和对象概览）"""
        if not self._connected:
            raise ConnectorError("Not connected to S3")

        buckets = await self._list_buckets()
        schema = {"buckets": []}

        for bucket in buckets:
            bucket_info = {
                "name": bucket["name"],
                "creation_date": bucket["creation_date"],
                "object_count": 0,
                "total_size": 0,
            }

            try:
                objects = await self._list_objects(bucket["name"])
                bucket_info["object_count"] = len(objects)
                bucket_info["total_size"] = sum(obj["size"] for obj in objects)
            except Exception:
                pass

            schema["buckets"].append(bucket_info)

        return schema

    async def health_check(self) -> HealthStatus:
        """S3 健康检查"""
        import time
        start_time = time.time()

        try:
            if not self._connected:
                await self.connect()

            # 尝试列出桶
            await self._list_buckets()

            latency_ms = (time.time() - start_time) * 1000

            return HealthStatus(
                status="healthy",
                latency_ms=round(latency_ms, 2),
                message="S3 connection OK",
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="s3",
                connector_name=self.config.name
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                status="unhealthy",
                latency_ms=round(latency_ms, 2),
                message=str(e),
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="s3",
                connector_name=self.config.name
            )

    async def get_bucket_stats(self, bucket: str) -> Dict[str, Any]:
        """获取桶统计信息"""
        objects = await self._list_objects(bucket)

        total_size = sum(obj["size"] for obj in objects)
        file_types = {}
        for obj in objects:
            ext = os.path.splitext(obj["key"])[1] or "no_extension"
            file_types[ext] = file_types.get(ext, 0) + 1

        return {
            "bucket": bucket,
            "object_count": len(objects),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types,
        }

    def _parse_path(self, path: str) -> tuple:
        """解析 S3 路径为 bucket 和 key"""
        parts = path.split("/", 1)
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析连接字符串
        格式：s3://access_key:secret_key@endpoint?region=us-east-1
        或：s3://access_key:secret_key@s3.amazonaws.com
        或：s3://access_key:secret_key@minio.local:9000
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        endpoint = None
        if parsed.hostname and parsed.hostname not in ['s3.amazonaws.com', '']:
            endpoint = f"{parsed.scheme}://{parsed.hostname}"
            if parsed.port:
                endpoint += f":{parsed.port}"

        return {
            'access_key': parsed.username or query_params.get('access_key', [''])[0],
            'secret_key': parsed.password or query_params.get('secret_key', [''])[0],
            'endpoint': endpoint or query_params.get('endpoint', [None])[0],
            'region': query_params.get('region', ['us-east-1'])[0],
        }


# 导出
__all__ = ["S3Connector"]
