"""
API 文档门户

提供：
1. OpenAPI 规范导出
2. 开发者指南
3. API 使用示例
4. SDK 生成支持
"""
from fastapi import APIRouter, Response, HTTPException
from fastapi.openapi.utils import get_openapi
from typing import Dict, Any, List, Optional
import json
import yaml

router = APIRouter(prefix="/api/docs", tags=["API 文档门户"])


# 存储自定义 OpenAPI 规范
_custom_openapi: Optional[Dict[str, Any]] = None


def get_custom_openapi(app) -> Dict[str, Any]:
    """获取自定义 OpenAPI 规范"""
    global _custom_openapi

    if _custom_openapi is None:
        _custom_openapi = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # 添加自定义扩展
        _custom_openapi["info"]["x-api-version"] = "v1"
        _custom_openapi["info"]["x-support"] = {
            "email": "support@data-agent-connector.io",
            "docs": "https://docs.data-agent-connector.io"
        }

        # 添加安全方案
        _custom_openapi["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API 密钥认证"
            },
            "UserId": {
                "type": "apiKey",
                "in": "header",
                "name": "X-User-ID",
                "description": "用户 ID 标识"
            },
            "TenantCode": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Tenant-Code",
                "description": "租户编码标识"
            }
        }

    return _custom_openapi


@router.get("/openapi.json")
async def get_openapi_spec() -> Dict[str, Any]:
    """获取 OpenAPI JSON 规范"""
    from main import app
    return get_custom_openapi(app)


@router.get("/openapi.yaml")
async def get_openapi_yaml() -> str:
    """获取 OpenAPI YAML 规范"""
    from main import app
    spec = get_custom_openapi(app)
    return yaml.dump(spec, allow_unicode=True, default_flow_style=False)


@router.get("/openapi")
async def download_openapi_spec(format: str = "json") -> Response:
    """下载 OpenAPI 规范文件"""
    from main import app
    spec = get_custom_openapi(app)

    if format.lower() == "yaml":
        content = yaml.dump(spec, allow_unicode=True, default_flow_style=False)
        media_type = "application/x-yaml"
        filename = "openapi.yaml"
    else:
        content = json.dumps(spec, indent=2, ensure_ascii=False)
        media_type = "application/json"
        filename = "openapi.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/guide")
async def get_developer_guide() -> Dict[str, Any]:
    """获取开发者指南"""
    return {
        "title": "Data-Agent Connector API 开发者指南",
        "version": "1.0",
        "sections": [
            {
                "title": "快速开始",
                "content": {
                    "introduction": """
Data-Agent Connector 是一个 AI Native 的数据网关，让每个 Agent 和业务人员都能安全、自然、高效地访问任何数据源。

核心功能：
- 多数据源连接（MySQL、PostgreSQL、MongoDB、Redis 等）
- 自然语言查询（NL2SQL）
- 细粒度 RBAC 权限控制
- 多租户架构支持
- 查询审计与监控告警
                    """,
                    "base_url": "http://localhost:8009",
                    "authentication": """
所有 API 请求需要在 Header 中包含：
- X-API-Key: 您的 API 密钥
- X-User-ID: 用户 ID 标识
- X-Tenant-Code: 租户编码（多租户模式下必需）
                    """
                }
            },
            {
                "title": "认证与授权",
                "content": {
                    "api_key_auth": """
使用 API 密钥进行认证：

```bash
curl -H "X-API-Key: your-api-key" \\
     -H "X-User-ID: user123" \\
     http://localhost:8009/api/connectors
```
                    """,
                    "rbac": """
系统支持细粒度 RBAC 权限控制：
- 系统级权限：角色管理、用户管理
- 数据源级权限：访问特定数据源
- 表级权限：访问特定表
- 列级权限：字段脱敏

内置角色：
- admin: 系统管理员，拥有所有权限
- editor: 编辑者，拥有读写权限
- analyst: 分析师，拥有只读 + 分析权限
- viewer: 查看者，仅拥有查看权限
                    """
                }
            },
            {
                "title": "核心 API",
                "content": {
                    "connectors": """
### 连接器管理

- `GET /api/connectors` - 获取所有连接器
- `POST /api/connectors` - 创建连接器
- `GET /api/connectors/{name}` - 获取连接器详情
- `PUT /api/connectors/{name}` - 更新连接器
- `DELETE /api/connectors/{name}` - 删除连接器
- `GET /api/connectors/{name}/schema` - 获取 Schema
- `GET /api/connectors/{name}/tables` - 获取表列表
                    """,
                    "query": """
### 查询接口

- `POST /api/query` - 执行 SQL 查询
- `POST /api/ai/query` - 自然语言查询
- `GET /api/ai/schema` - 获取 Schema 缓存
- `POST /api/ai/suggest` - 获取查询建议
                    """,
                    "rbac": """
### 权限管理

- `GET /api/rbac/roles` - 获取所有角色
- `POST /api/rbac/roles` - 创建角色
- `POST /api/rbac/users/{user_id}/roles` - 分配角色
- `POST /api/rbac/check` - 检查权限
- `POST /api/rbac/mask` - 应用数据脱敏
                    """,
                    "tenant": """
### 多租户管理

- `GET /api/tenant` - 获取租户列表
- `POST /api/tenant` - 创建租户
- `GET /api/tenant/{code}` - 获取租户详情
- `POST /api/tenant/{code}/members` - 添加成员
- `POST /api/tenant/{code}/datasources` - 添加数据源
                    """,
                    "monitoring": """
### 监控告警

- `GET /api/monitoring/metrics` - 获取监控指标
- `GET /api/monitoring/dashboard` - 获取大盘数据
- `GET /api/monitoring/prometheus/metrics` - Prometheus 格式指标
- `POST /api/monitoring/alert-rules` - 创建告警规则
                    """
                }
            },
            {
                "title": "使用示例",
                "content": {
                    "python_example": """
### Python SDK 示例

```python
import requests

BASE_URL = "http://localhost:8009"
HEADERS = {
    "X-API-Key": "your-api-key",
    "X-User-ID": "user123"
}

# 创建连接器
connector = {
    "name": "my_mysql",
    "connector_type": "mysql",
    "config": {
        "host": "localhost",
        "port": 3306,
        "database": "test_db"
    }
}
response = requests.post(
    f"{BASE_URL}/api/connectors",
    headers=HEADERS,
    json=connector
)

# 执行查询
query = {"datasource": "my_mysql", "sql": "SELECT * FROM users LIMIT 10"}
response = requests.post(
    f"{BASE_URL}/api/query",
    headers=HEADERS,
    json=query
)
data = response.json()
print(data["results"])

# 自然语言查询
nl_query = {"datasource": "my_mysql", "question": "显示前 10 个用户"}
response = requests.post(
    f"{BASE_URL}/api/ai/query",
    headers=HEADERS,
    json=nl_query
)
print(response.json()["answer"])
```
                    """,
                    "curl_example": """
### cURL 示例

```bash
# 获取连接器列表
curl -H "X-API-Key: your-api-key" \\
     http://localhost:8009/api/connectors

# 执行 SQL 查询
curl -X POST -H "X-API-Key: your-api-key" \\
     -H "Content-Type: application/json" \\
     -d '{"datasource": "my_mysql", "sql": "SELECT * FROM users"}' \\
     http://localhost:8009/api/query

# 自然语言查询
curl -X POST -H "X-API-Key: your-api-key" \\
     -H "Content-Type: application/json" \\
     -d '{"datasource": "my_mysql", "question": "显示销售额前 10 的产品"}' \\
     http://localhost:8009/api/ai/query
```
                    """
                }
            },
            {
                "title": "错误处理",
                "content": {
                    "error_codes": """
### 错误码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（API 密钥无效） |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 429 | 请求限流 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
    "detail": "错误描述信息",
    "error_code": "ERROR_CODE",
    "timestamp": "2024-01-01T12:00:00Z"
}
```
                    """
                }
            },
            {
                "title": "最佳实践",
                "content": {
                    "security": """
### 安全建议

1. **API 密钥管理**
   - 不要在客户端代码中硬编码 API 密钥
   - 定期轮换 API 密钥
   - 使用环境变量或密钥管理服务存储密钥

2. **权限最小化**
   - 为用户分配最小必要权限
   - 定期审计权限分配
   - 对敏感数据应用脱敏

3. **查询安全**
   - 所有查询都会经过安全检查
   - 避免在查询中包含敏感信息
   - 使用参数化查询防止注入
                    """,
                    "performance": """
### 性能优化

1. **连接池使用**
   - 复用连接器而非频繁创建
   - 合理设置最大连接数
   - 监控连接池使用率

2. **查询优化**
   - 使用 LIMIT 限制返回行数
   - 避免 SELECT *
   - 为常用查询创建索引

3. **限流配置**
   - 根据业务需求调整限流参数
   - 监控限流触发情况
   - 设置合理的超时时间
                    """
                }
            }
        ]
    }


@router.get("/examples")
async def get_api_examples() -> Dict[str, Any]:
    """获取 API 使用示例"""
    return {
        "examples": [
            {
                "category": "连接器管理",
                "examples": [
                    {
                        "title": "创建 MySQL 连接器",
                        "method": "POST",
                        "endpoint": "/api/connectors",
                        "request": {
                            "name": "my_mysql",
                            "connector_type": "mysql",
                            "config": {
                                "host": "localhost",
                                "port": 3306,
                                "database": "test_db",
                                "user": "${DATASOURCE_USER}",
                                "password": "${DATASOURCE_PASSWORD}"
                            }
                        },
                        "response": {
                            "success": True,
                            "connector": {"name": "my_mysql", "status": "active"}
                        }
                    },
                    {
                        "title": "获取连接器 Schema",
                        "method": "GET",
                        "endpoint": "/api/connectors/my_mysql/schema",
                        "response": {
                            "tables": [
                                {"name": "users", "columns": [{"name": "id", "type": "int"}, {"name": "name", "type": "string"}]},
                                {"name": "orders", "columns": [{"name": "order_id", "type": "int"}, {"name": "amount", "type": "decimal"}]}
                            ]
                        }
                    }
                ]
            },
            {
                "category": "查询执行",
                "examples": [
                    {
                        "title": "执行 SQL 查询",
                        "method": "POST",
                        "endpoint": "/api/query",
                        "request": {
                            "datasource": "my_mysql",
                            "sql": "SELECT * FROM users WHERE status = 'active' LIMIT 10"
                        },
                        "response": {
                            "success": True,
                            "results": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}],
                            "row_count": 10,
                            "execution_time_ms": 45
                        }
                    },
                    {
                        "title": "自然语言查询",
                        "method": "POST",
                        "endpoint": "/api/ai/query",
                        "request": {
                            "datasource": "my_mysql",
                            "question": "显示上个月销售额前 10 的产品"
                        },
                        "response": {
                            "success": True,
                            "sql": "SELECT product_name, SUM(amount) as total FROM orders GROUP BY product_name ORDER BY total DESC LIMIT 10",
                            "results": [{"product_name": "Product A", "total": 10000}],
                            "explanation": "查询按产品分组并计算销售额总和"
                        }
                    }
                ]
            },
            {
                "category": "权限管理",
                "examples": [
                    {
                        "title": "创建自定义角色",
                        "method": "POST",
                        "endpoint": "/api/rbac/roles",
                        "request": {
                            "name": "data_analyst",
                            "description": "数据分析师角色",
                            "permissions": [
                                "datasource:*:select",
                                "system:view"
                            ]
                        }
                    },
                    {
                        "title": "给用户分配角色",
                        "method": "POST",
                        "endpoint": "/api/rbac/users/user123/roles",
                        "request": {
                            "role_name": "data_analyst"
                        }
                    }
                ]
            },
            {
                "category": "多租户",
                "examples": [
                    {
                        "title": "创建租户",
                        "method": "POST",
                        "endpoint": "/api/tenant",
                        "request": {
                            "tenant_code": "acme_corp",
                            "tenant_name": "ACME 公司",
                            "quota": {
                                "max_datasources": 10,
                                "max_users": 50,
                                "max_queries_per_day": 50000
                            }
                        }
                    },
                    {
                        "title": "添加租户数据源",
                        "method": "POST",
                        "endpoint": "/api/tenant/acme_corp/datasources",
                        "request": {
                            "datasource_name": "prod_mysql",
                            "connector_type": "mysql",
                            "is_public": True
                        }
                    }
                ]
            },
            {
                "category": "监控告警",
                "examples": [
                    {
                        "title": "获取 Prometheus 指标",
                        "method": "GET",
                        "endpoint": "/api/monitoring/prometheus/metrics",
                        "response": """# HELP query_total Data-Agent Connector metric
# TYPE query_total counter
query_total{datasource="mysql"} 1234
query_latency_ms_avg{datasource="mysql"} 45.6"""
                    },
                    {
                        "title": "创建告警规则",
                        "method": "POST",
                        "endpoint": "/api/monitoring/alert-rules",
                        "request": {
                            "name": "High Latency Alert",
                            "metric_name": "query_latency_ms_avg",
                            "operator": ">",
                            "threshold": 500,
                            "severity": "warning",
                            "notify_channels": ["dingtalk"]
                        }
                    }
                ]
            }
        ]
    }


@router.get("/sdk")
async def get_sdk_info() -> Dict[str, Any]:
    """获取 SDK 生成信息"""
    return {
        "openapi_generator": {
            "description": "使用 OpenAPI Generator 生成 SDK",
            "command": "openapi-generator generate -i http://localhost:8009/api/docs/openapi.json -g python -o ./sdk",
            "supported_languages": [
                "python",
                "javascript",
                "typescript",
                "java",
                "go",
                "ruby",
                "php",
                "csharp"
            ]
        },
        "official_sdks": [
            {
                "language": "Python",
                "repository": "https://github.com/data-agent-connector/python-sdk",
                "installation": "pip install data-agent-connector-sdk"
            }
        ]
    }


@router.get("/")
async def docs_index() -> Dict[str, Any]:
    """文档门户首页"""
    return {
        "title": "Data-Agent Connector API 文档门户",
        "version": "1.0.0",
        "links": {
            "openapi_json": "/api/docs/openapi.json",
            "openapi_yaml": "/api/docs/openapi.yaml",
            "developer_guide": "/api/docs/guide",
            "api_examples": "/api/docs/examples",
            "sdk_info": "/api/docs/sdk",
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        },
        "description": """
欢迎使用 Data-Agent Connector API 文档门户。

Data-Agent Connector 是一个 AI Native 的数据网关，提供：
- 多数据源连接与管理
- 自然语言查询（NL2SQL）
- 细粒度 RBAC 权限控制
- 多租户架构
- 实时监控与告警

通过本文档门户，您可以：
- 获取 OpenAPI 规范用于 SDK 生成
- 查看开发者指南和 API 使用示例
- 了解认证授权机制
- 学习最佳实践
        """
    }
