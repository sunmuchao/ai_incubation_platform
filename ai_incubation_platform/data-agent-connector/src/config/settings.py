"""
配置管理模块
从环境变量和配置文件加载配置，支持密钥管理集成
"""
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import Dict, Optional, List
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class SecuritySettings(BaseSettings):
    """安全配置"""
    api_key: Optional[str] = Field(None, description="API 访问密钥")
    allow_roles: List[str] = Field(["read_only", "read_write"], description="允许的角色列表")
    default_role: str = Field("read_only", description="默认角色")
    dangerous_operations: List[str] = Field(
        ["DROP", "ALTER", "TRUNCATE", "DELETE", "UPDATE", "INSERT", "CREATE", "REPLACE"],
        description="危险操作关键字"
    )
    allow_write_operations: List[str] = Field(
        ["INSERT", "UPDATE", "DELETE"],
        description="写权限允许的操作"
    )
    max_query_rows: int = Field(10000, description="单次查询最大返回行数")
    query_timeout: int = Field(30, description="查询超时时间（秒）")


class RateLimitSettings(BaseSettings):
    """限流配置"""
    enabled: bool = Field(True, description="是否启用限流")
    max_requests_per_minute: int = Field(60, description="每分钟最大请求数")
    max_concurrent_queries: int = Field(10, description="最大并发查询数")
    burst_limit: int = Field(20, description="突发请求限制")


class AuditSettings(BaseSettings):
    """审计配置"""
    enabled: bool = Field(True, description="是否启用审计日志")
    log_all_queries: bool = Field(True, description="是否记录所有查询")
    log_sensitive_data: bool = Field(False, description="是否记录敏感数据")
    retention_days: int = Field(90, description="审计日志保留天数")


class ConnectorSettings(BaseSettings):
    """连接器配置"""
    default_max_connections: int = Field(10, description="默认最大连接数")
    connection_timeout: int = Field(10, description="连接超时时间（秒）")
    idle_timeout: int = Field(300, description="连接空闲超时时间（秒）")
    allow_custom_connectors: bool = Field(False, description="是否允许自定义连接器")


class CredentialSettings(BaseSettings):
    """凭据管理配置"""
    use_env_credentials: bool = Field(True, description="是否从环境变量读取凭据")
    env_prefix: str = Field("DATASOURCE_", description="环境变量前缀")
    secret_manager_type: Optional[str] = Field(None, description="密钥管理器类型 (aws, hashicorp, none)")
    secret_manager_url: Optional[str] = Field(None, description="密钥管理器地址")


class LineageSettings(BaseSettings):
    """血缘持久化配置"""
    enabled: bool = Field(True, description="是否启用血缘持久化")
    db_type: str = Field("sqlite", description="数据库类型 (sqlite, postgresql)")
    db_path: str = Field("./data/lineage.db", description="SQLite 数据库路径")
    db_host: str = Field("localhost", description="PostgreSQL 主机")
    db_port: int = Field(5432, description="PostgreSQL 端口")
    db_name: str = Field("lineage_db", description="数据库名称")
    db_user: str = Field("postgres", description="数据库用户")
    db_password: str = Field("postgres", description="数据库密码")
    pool_size: int = Field(10, description="连接池大小")
    max_overflow: int = Field(20, description="最大溢出连接数")
    retention_days: int = Field(90, description="血缘历史保留天数")
    snapshot_interval_hours: int = Field(24, description="快照间隔小时数")


class RetrySettings(BaseSettings):
    """重试配置"""
    enabled: bool = Field(True, description="是否启用自动重试")
    max_retries: int = Field(3, description="最大重试次数")
    base_delay: float = Field(1.0, description="基础延迟（秒）")
    max_delay: float = Field(30.0, description="最大延迟（秒）")
    strategy: str = Field("exponential_jitter", description="重试策略：fixed, linear, exponential, exponential_jitter")
    retryable_errors: List[str] = Field(
        default_factory=lambda: ["connection", "timeout", "temporarily", "retry", "lock", "busy", "deadlock"],
        description="可重试的错误关键字"
    )


class AISettings(BaseSettings):
    """AI 功能配置"""
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API 密钥")
    anthropic_model: str = Field("claude-sonnet-4-20250514", description="Anthropic 模型名称")
    nl2sql_use_llm: bool = Field(True, description="NL2SQL 是否使用 LLM（否则使用规则匹配）")
    enable_intent_recognition: bool = Field(True, description="是否启用查询意图识别")
    enable_result_explanation: bool = Field(True, description="是否启用结果解释")
    enable_query_optimization: bool = Field(True, description="是否启用查询优化建议")
    schema_auto_evolution: bool = Field(True, description="是否启用 Schema 自动演进")
    schema_auto_apply: bool = Field(False, description="是否自动应用非破坏性 Schema 变更")


class AppSettings(BaseSettings):
    """应用全局配置"""
    host: str = Field("0.0.0.0", description="服务监听地址")
    port: int = Field(8009, description="服务监听端口")
    environment: str = Field("development", description="运行环境 (development, staging, production)")
    debug: bool = Field(False, description="是否启用调试模式")

    # 子配置
    security: SecuritySettings = SecuritySettings()
    rate_limit: RateLimitSettings = RateLimitSettings()
    audit: AuditSettings = AuditSettings()
    connector: ConnectorSettings = ConnectorSettings()
    credential: CredentialSettings = CredentialSettings()
    lineage: LineageSettings = LineageSettings()
    ai: AISettings = AISettings()
    retry: RetrySettings = RetrySettings()

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


# 全局配置实例
settings = AppSettings()


def get_datasource_credentials(datasource_name: str) -> Optional[Dict[str, str]]:
    """
    从环境变量获取数据源凭据
    环境变量格式：DATASOURCE_{NAME}_{KEY}
    例如：DATASOURCE_MYSQL_PROD_HOST=localhost
    """
    if not settings.credential.use_env_credentials:
        return None

    prefix = f"{settings.credential.env_prefix}{datasource_name.upper()}_"
    credentials = {}

    for key, value in os.environ.items():
        if key.startswith(prefix):
            credential_key = key[len(prefix):].lower()
            credentials[credential_key] = value

    return credentials if credentials else None
