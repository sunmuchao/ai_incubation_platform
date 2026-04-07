"""
配置管理
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import os
from enum import Enum


class LLMProvider(str, Enum):
    MOCK = "mock"
    OPENAI = "openai"
    CLAUDE = "claude"


class AppConfig(BaseModel):
    """应用配置"""
    # 服务配置
    host: str = Field(default="0.0.0.0", description="服务监听地址")
    port: int = Field(default=int(os.getenv("PORT", 8010)), description="服务监听端口")
    debug: bool = Field(default=False, description="是否开启调试模式")

    # 策略引擎配置
    enable_builtin_strategies: bool = Field(default=True, description="是否启用内置策略")
    custom_strategies_dir: Optional[str] = Field(default=None, description="自定义策略目录")

    # LLM 配置
    llm_enabled: bool = Field(default=False, description="是否启用 LLM 增强")
    llm_provider: LLMProvider = Field(default=LLMProvider.MOCK, description="LLM 提供商")
    llm_api_key: Optional[str] = Field(default=None, description="LLM API 密钥")
    llm_model: str = Field(default="claude-sonnet-4-20250514", description="LLM 模型名称")

    # 存储配置
    storage_type: str = Field(default="memory", description="存储类型：memory/redis/hybrid")
    storage_max_records: int = Field(default=100, description="每个服务最多保留的记录数")
    redis_url: Optional[str] = Field(default="redis://localhost:6379/0", description="Redis 连接 URL")

    # 时序数据库配置 (InfluxDB)
    enable_timeseries_db: bool = Field(default=False, description="是否启用时序数据库 (InfluxDB)")
    influxdb_url: Optional[str] = Field(default="http://localhost:8086", description="InfluxDB URL")
    influxdb_token: Optional[str] = Field(default="my-token", description="InfluxDB API token (v2)")
    influxdb_org: Optional[str] = Field(default="my-org", description="InfluxDB 组织名 (v2)")
    influxdb_bucket: Optional[str] = Field(default="ai-optimizer", description="InfluxDB bucket 名")
    influxdb_retention_policy: Optional[str] = Field(default="30d", description="InfluxDB 数据保留策略")
    influxdb_use_v1: bool = Field(default=False, description="是否使用 InfluxDB v1 协议")
    influxdb_v1_username: Optional[str] = Field(default="admin", description="InfluxDB v1 用户名")
    influxdb_v1_password: Optional[str] = Field(default="password", description="InfluxDB v1 密码")
    timeseries_redis_ttl_seconds: int = Field(default=3600, description="时序数据在 Redis 中的 TTL(秒)")

    # 安全配置
    auto_merge_allowed: bool = Field(default=False, description="是否允许自动合并代码变更")
    require_human_review: bool = Field(default=True, description="代码变更是否需要人工评审")
    require_ci_check: bool = Field(default=True, description="代码变更是否需要 CI 检查")

    # 安全增强配置
    enable_audit_logging: bool = Field(default=True, description="是否启用审计日志")
    enable_api_rate_limiting: bool = Field(default=False, description="是否启用 API 速率限制")
    api_rate_limit_requests: int = Field(default=100, description="API 速率限制 (请求数/分钟)")
    enable_api_key_auth: bool = Field(default=False, description="是否启用 API Key 认证")
    api_keys: Optional[str] = Field(default=None, description="API Keys 列表 (逗号分隔)")
    enable_cors: bool = Field(default=True, description="是否启用 CORS")
    cors_origins: Optional[str] = Field(default="*", description="CORS 允许的源 (逗号分隔)")
    enable_request_signing: bool = Field(default=False, description="是否启用请求签名验证")
    signing_secret: Optional[str] = Field(default=None, description="请求签名密钥")

    # 生产模式配置
    production_insight_mode: bool = Field(default=False, description="是否启用生产洞察只读模式：仅允许查询，不允许修改策略与配置")
    allow_data_modification: bool = Field(default=True, description="是否允许修改数据：关闭后仅允许查询分析，不允许上报新数据")
    enable_integration_adapters: bool = Field(default=True, description="是否启用外部集成适配器：CI、安全扫描等")

    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("AI_OPTIMIZER_HOST", "0.0.0.0"),
            port=int(os.getenv("AI_OPTIMIZER_PORT", "8012")),
            debug=os.getenv("AI_OPTIMIZER_DEBUG", "false").lower() == "true",
            enable_builtin_strategies=os.getenv("AI_OPTIMIZER_BUILTIN_STRATEGIES", "true").lower() == "true",
            custom_strategies_dir=os.getenv("AI_OPTIMIZER_STRATEGIES_DIR"),
            llm_enabled=os.getenv("AI_OPTIMIZER_LLM_ENABLED", "false").lower() == "true",
            llm_provider=LLMProvider(os.getenv("AI_OPTIMIZER_LLM_PROVIDER", "mock")),
            llm_api_key=os.getenv("AI_OPTIMIZER_LLM_API_KEY"),
            llm_model=os.getenv("AI_OPTIMIZER_LLM_MODEL", "claude-sonnet-4-20250514"),
            storage_type=os.getenv("AI_OPTIMIZER_STORAGE", "memory"),
            storage_max_records=int(os.getenv("AI_OPTIMIZER_STORAGE_MAX_RECORDS", "100")),
            redis_url=os.getenv("AI_OPTIMIZER_REDIS_URL", "redis://localhost:6379/0"),
            # InfluxDB 配置
            enable_timeseries_db=os.getenv("AI_OPTIMIZER_ENABLE_TIMESERIES_DB", "false").lower() == "true",
            influxdb_url=os.getenv("AI_OPTIMIZER_INFLUXDB_URL", "http://localhost:8086"),
            influxdb_token=os.getenv("AI_OPTIMIZER_INFLUXDB_TOKEN", "my-token"),
            influxdb_org=os.getenv("AI_OPTIMIZER_INFLUXDB_ORG", "my-org"),
            influxdb_bucket=os.getenv("AI_OPTIMIZER_INFLUXDB_BUCKET", "ai-optimizer"),
            influxdb_retention_policy=os.getenv("AI_OPTIMIZER_INFLUXDB_RETENTION", "30d"),
            influxdb_use_v1=os.getenv("AI_OPTIMIZER_INFLUXDB_USE_V1", "false").lower() == "true",
            influxdb_v1_username=os.getenv("AI_OPTIMIZER_INFLUXDB_V1_USERNAME", "admin"),
            influxdb_v1_password=os.getenv("AI_OPTIMIZER_INFLUXDB_V1_PASSWORD", "password"),
            timeseries_redis_ttl_seconds=int(os.getenv("AI_OPTIMIZER_TIMESERIES_REDIS_TTL", "3600")),
            # 安全配置
            auto_merge_allowed=os.getenv("AI_OPTIMIZER_AUTO_MERGE", "false").lower() == "true",
            require_human_review=os.getenv("AI_OPTIMIZER_REQUIRE_REVIEW", "true").lower() == "true",
            require_ci_check=os.getenv("AI_OPTIMIZER_REQUIRE_CI", "true").lower() == "true",
            enable_audit_logging=os.getenv("AI_OPTIMIZER_ENABLE_AUDIT", "true").lower() == "true",
            enable_api_rate_limiting=os.getenv("AI_OPTIMIZER_ENABLE_RATE_LIMIT", "false").lower() == "true",
            api_rate_limit_requests=int(os.getenv("AI_OPTIMIZER_RATE_LIMIT", "100")),
            enable_api_key_auth=os.getenv("AI_OPTIMIZER_ENABLE_API_KEY_AUTH", "false").lower() == "true",
            api_keys=os.getenv("AI_OPTIMIZER_API_KEYS"),
            enable_cors=os.getenv("AI_OPTIMIZER_ENABLE_CORS", "true").lower() == "true",
            cors_origins=os.getenv("AI_OPTIMIZER_CORS_ORIGINS", "*"),
            enable_request_signing=os.getenv("AI_OPTIMIZER_ENABLE_REQUEST_SIGNING", "false").lower() == "true",
            signing_secret=os.getenv("AI_OPTIMIZER_SIGNING_SECRET"),
            # 生产模式配置
            production_insight_mode=os.getenv("AI_OPTIMIZER_PRODUCTION_INSIGHT", "false").lower() == "true",
            allow_data_modification=os.getenv("AI_OPTIMIZER_ALLOW_DATA_MODIFICATION", "true").lower() == "true",
            enable_integration_adapters=os.getenv("AI_OPTIMIZER_ENABLE_INTEGRATIONS", "true").lower() == "true",
        )


# 全局配置实例
config = AppConfig.from_env()
