"""
GraphQL API 连接器 - 异步
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError, HealthStatus


class GraphQLConnector(BaseConnector):
    """
    GraphQL API 连接器
    支持任意 GraphQL 端点的查询和变异操作
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._endpoint = None
        self._headers = {}
        self._schema_introspection = None

    async def connect(self) -> None:
        """建立 GraphQL 连接"""
        try:
            parsed = self._parse_connection_string()

            self._endpoint = parsed.get('endpoint', '')

            # 设置认证头
            if parsed.get('token'):
                self._headers['Authorization'] = f"Bearer {parsed.get('token')}"
            elif parsed.get('api_key'):
                self._headers['X-API-Key'] = parsed.get('api_key')

            # 设置内容类型
            self._headers['Content-Type'] = 'application/json'

            self._connected = True

        except Exception as e:
            raise ConnectorError(f"Failed to connect to GraphQL endpoint: {e}")

    async def disconnect(self) -> None:
        """断开 GraphQL 连接"""
        self._headers = {}
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        执行 GraphQL 查询
        支持语法：
        - 标准 GraphQL 查询："{ user(id: 1) { name email } }"
        - 带变量的查询：需要 params 提供 variables
        - Mutation: "mutation { createUser(name: \"Alice\") { id name } }"
        """
        if not self._connected:
            raise ConnectorError("Not connected to GraphQL endpoint")

        try:
            import aiohttp

            variables = params.get('variables', {}) if params else {}
            operation_name = params.get('operation_name') if params else None

            payload = {
                "query": query,
                "variables": variables,
            }

            if operation_name:
                payload["operationName"] = operation_name

            async with aiohttp.ClientSession(headers=self._headers) as session:
                async with session.post(self._endpoint, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ConnectorError(f"GraphQL request failed: {response.status} - {error_text}")

                    result = await response.json()

                    # 处理 GraphQL 错误
                    if "errors" in result:
                        errors = result["errors"]
                        error_msg = "; ".join([e.get("message", str(e)) for e in errors])
                        raise ConnectorError(f"GraphQL errors: {error_msg}")

                    # 提取数据
                    data = result.get("data", {})
                    return self._flatten_data(data)

        except Exception as e:
            raise ConnectorError(f"GraphQL query failed: {e}")

    def _flatten_data(self, data: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
        """将 GraphQL 响应数据扁平化为字典列表"""
        results = []

        if isinstance(data, dict):
            # 检查是否有列表字段
            lists_found = {k: v for k, v in data.items() if isinstance(v, list)}

            if lists_found:
                # 如果有列表，展开列表
                for key, value in lists_found.items():
                    for item in value:
                        if isinstance(item, dict):
                            row = {f"{prefix}{key}": item}
                            # 添加其他非列表字段
                            for k, v in data.items():
                                if k != key and not isinstance(v, list):
                                    row[f"{prefix}{k}"] = v
                            results.append(row)
                        else:
                            results.append({f"{prefix}{key}": item})
            else:
                # 没有列表，直接返回
                results.append({f"{prefix}{k}": v for k, v in data.items()})

        elif isinstance(data, list):
            for item in data:
                results.extend(self._flatten_data(item, prefix))

        else:
            results.append({f"{prefix}value": data})

        return results

    async def get_schema(self) -> Dict[str, Any]:
        """获取 GraphQL Schema（通过内省查询）"""
        if not self._connected:
            raise ConnectorError("Not connected to GraphQL endpoint")

        # 如果已经有内省结果，直接返回
        if self._schema_introspection:
            return self._schema_introspection

        try:
            # GraphQL 内省查询
            introspection_query = """
            query IntrospectionQuery {
                __schema {
                    queryType { name }
                    mutationType { name }
                    subscriptionType { name }
                    types {
                        ...FullType
                    }
                    directives {
                        name
                        description
                        locations
                        args {
                            ...InputValue
                        }
                    }
                }
            }

            fragment FullType on __Type {
                kind
                name
                description
                fields(includeDeprecated: true) {
                    name
                    description
                    args {
                        ...InputValue
                    }
                    type {
                        ...TypeRef
                    }
                    isDeprecated
                    deprecationReason
                }
                inputFields {
                    ...InputValue
                }
                interfaces {
                    ...TypeRef
                }
                enumValues(includeDeprecated: true) {
                    name
                    description
                    isDeprecated
                    deprecationReason
                }
                possibleTypes {
                    ...TypeRef
                }
            }

            fragment InputValue on __InputValue {
                name
                description
                type {
                    ...TypeRef
                }
                defaultValue
            }

            fragment TypeRef on __Type {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                    ofType {
                                        kind
                                        name
                                        ofType {
                                            kind
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """

            import aiohttp

            payload = {
                "query": introspection_query,
                "variables": {},
            }

            async with aiohttp.ClientSession(headers=self._headers) as session:
                async with session.post(self._endpoint, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ConnectorError(f"Introspection failed: {response.status} - {error_text}")

                    result = await response.json()

                    if "errors" in result:
                        errors = result["errors"]
                        error_msg = "; ".join([e.get("message", str(e)) for e in errors])
                        raise ConnectorError(f"Introspection errors: {error_msg}")

                    self._schema_introspection = {
                        "schema": result.get("data", {}),
                        "endpoint": self._endpoint,
                    }

                    return self._schema_introspection

        except Exception as e:
            raise ConnectorError(f"Failed to introspect schema: {e}")

    async def health_check(self) -> HealthStatus:
        """GraphQL 健康检查"""
        import time
        start_time = time.time()

        try:
            if not self._connected:
                await self.connect()

            # 执行简单的内省查询
            health_query = "{ __typename }"
            await self.execute(health_query)

            latency_ms = (time.time() - start_time) * 1000

            return HealthStatus(
                status="healthy",
                latency_ms=round(latency_ms, 2),
                message="GraphQL endpoint OK",
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="graphql",
                connector_name=self.config.name
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                status="unhealthy",
                latency_ms=round(latency_ms, 2),
                message=str(e),
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="graphql",
                connector_name=self.config.name
            )

    async def get_query_fields(self) -> List[Dict[str, Any]]:
        """获取所有查询字段"""
        schema = await self.get_schema()
        query_type = schema.get("schema", {}).get("__schema", {}).get("queryType", {})
        query_type_name = query_type.get("name", "Query")

        types = schema.get("schema", {}).get("__schema", {}).get("types", [])
        query_type_def = next((t for t in types if t.get("name") == query_type_name), None)

        if query_type_def:
            fields = query_type_def.get("fields", []) or []
            return [
                {
                    "name": f.get("name"),
                    "description": f.get("description"),
                    "args": [
                        {
                            "name": a.get("name"),
                            "type": self._type_to_string(a.get("type")),
                            "default": a.get("defaultValue"),
                        }
                        for a in f.get("args", [])
                    ],
                    "type": self._type_to_string(f.get("type")),
                }
                for f in fields
            ]

        return []

    async def get_mutation_fields(self) -> List[Dict[str, Any]]:
        """获取所有变异字段"""
        schema = await self.get_schema()
        mutation_type = schema.get("schema", {}).get("__schema", {}).get("mutationType", {})

        if not mutation_type or not mutation_type.get("name"):
            return []

        mutation_type_name = mutation_type.get("name", "Mutation")
        types = schema.get("schema", {}).get("__schema", {}).get("types", [])
        mutation_type_def = next((t for t in types if t.get("name") == mutation_type_name), None)

        if mutation_type_def:
            fields = mutation_type_def.get("fields", []) or []
            return [
                {
                    "name": f.get("name"),
                    "description": f.get("description"),
                    "args": [
                        {
                            "name": a.get("name"),
                            "type": self._type_to_string(a.get("type")),
                            "default": a.get("defaultValue"),
                        }
                        for a in f.get("args", [])
                    ],
                    "type": self._type_to_string(f.get("type")),
                }
                for f in fields
            ]

        return []

    def _type_to_string(self, type_ref: Optional[Dict[str, Any]]) -> str:
        """将 GraphQL 类型引用转换为字符串表示"""
        if not type_ref:
            return "Unknown"

        kind = type_ref.get("kind")
        name = type_ref.get("name")

        if name:
            return name
        elif kind == "LIST":
            inner = self._type_to_string(type_ref.get("ofType"))
            return f"[{inner}]"
        elif kind == "NON_NULL":
            inner = self._type_to_string(type_ref.get("ofType"))
            return f"{inner}!"
        else:
            return "Unknown"

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析连接字符串
        格式：graphql://endpoint?token=xxx 或 graphql://endpoint?api_key=xxx
        示例：
        - graphql://https://api.github.com/graphql?token=ghp_xxx
        - graphql://https://api.example.com/graphql?api_key=xxx
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        # 构建端点 URL
        endpoint = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            endpoint += f":{parsed.port}"
        if parsed.path:
            endpoint += parsed.path

        # 如果是 graphql:// 前缀，替换为 https://
        if endpoint.startswith("graphql://"):
            endpoint = endpoint.replace("graphql://", "https://")

        return {
            'endpoint': endpoint,
            'token': query_params.get('token', [''])[0],
            'api_key': query_params.get('api_key', [''])[0],
        }


# 导出
__all__ = ["GraphQLConnector"]
