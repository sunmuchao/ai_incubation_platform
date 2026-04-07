"""
统一配置管理

提供配置的加载、验证和访问功能
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='Settings')


class ConfigSource(Enum):
    """配置来源"""
    DEFAULT = "default"
    FILE = "file"
    ENV = "env"
    OVERRIDE = "override"


@dataclass
class Settings:
    """
    统一配置管理

    支持多种配置来源：
    - 默认值
    - 配置文件
    - 环境变量
    - 运行时覆盖
    """

    # 应用配置
    app_name: str = "agent-platform-core"
    app_version: str = "3.0.0"
    app_env: str = "development"  # development/staging/production

    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # DeerFlow 配置
    deerflow_api_key: Optional[str] = None
    deerflow_api_url: str = "https://api.deerflow.ai"
    deerflow_timeout: float = 30.0
    deerflow_max_retries: int = 3

    # 数据库配置
    database_url: Optional[str] = None
    database_pool_size: int = 10
    database_echo: bool = False

    # Redis 配置
    redis_url: Optional[str] = None
    redis_prefix: str = "agent:"

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "json"  # json/text
    log_file: Optional[str] = None

    # 审计配置
    audit_enabled: bool = True
    audit_retention_days: int = 30
    audit_storage_path: Optional[str] = None

    # 安全配置
    secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # 限流配置
    rate_limit_enabled: bool = True
    rate_limit_default: int = 100  # 请求/分钟

    # 功能开关
    features: Dict[str, bool] = field(default_factory=dict)

    # 自定义配置
    custom: Dict[str, Any] = field(default_factory=dict)

    # 配置来源追踪
    _config_sources: Dict[str, ConfigSource] = field(default_factory=dict, repr=False)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return getattr(self, key, default)

    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.OVERRIDE) -> None:
        """设置配置值"""
        if hasattr(self, key):
            setattr(self, key, value)
            self._config_sources[key] = source
        else:
            # 动态添加自定义配置
            self.custom[key] = value

    def get_source(self, key: str) -> ConfigSource:
        """获取配置来源"""
        return self._config_sources.get(key, ConfigSource.DEFAULT)

    def to_dict(self, include_source: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        if include_source:
            result["_sources"] = {
                k: v.value for k, v in self._config_sources.items()
            }
        return result

    def validate(self) -> List[str]:
        """
        验证配置

        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []

        # 验证端口
        if not (1 <= self.port <= 65535):
            errors.append(f"Invalid port: {self.port}")

        # 验证日志级别
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"Invalid log level: {self.log_level}")

        # 生产环境检查
        if self.app_env == "production":
            if self.debug:
                errors.append("Debug mode should be disabled in production")
            if not self.secret_key:
                errors.append("Secret key is required in production")

        return errors

    def is_production(self) -> bool:
        """是否生产环境"""
        return self.app_env == "production"

    def is_development(self) -> bool:
        """是否开发环境"""
        return self.app_env == "development"


class ConfigLoader:
    """
    配置加载器

    支持从多种来源加载配置
    """

    def __init__(self, settings_class: Type[Settings] = Settings):
        """
        初始化配置加载器

        Args:
            settings_class: Settings 类
        """
        self.settings_class = settings_class
        self._config_paths: List[str] = []

    def add_config_path(self, path: str) -> 'ConfigLoader':
        """添加配置文件路径"""
        self._config_paths.append(path)
        return self

    def load(
        self,
        env_prefix: str = "AGENT_",
        **overrides
    ) -> Settings:
        """
        加载配置

        Args:
            env_prefix: 环境变量前缀
            **overrides: 覆盖配置

        Returns:
            Settings: 配置对象
        """
        # 1. 创建默认配置
        settings = self.settings_class()
        settings._config_sources = {
            field: ConfigSource.DEFAULT
            for field in settings.__dataclass_fields__
        }

        # 2. 从文件加载
        for config_path in self._config_paths:
            file_config = self._load_from_file(config_path)
            if file_config:
                self._apply_config(settings, file_config, ConfigSource.FILE)
                logger.info(f"Loaded config from {config_path}")

        # 3. 从环境变量加载
        env_config = self._load_from_env(env_prefix)
        if env_config:
            self._apply_config(settings, env_config, ConfigSource.ENV)

        # 4. 应用覆盖配置
        if overrides:
            self._apply_config(settings, overrides, ConfigSource.OVERRIDE)

        return settings

    def _load_from_file(self, path: str) -> Optional[Dict[str, Any]]:
        """从文件加载配置"""
        config_path = Path(path)

        if not config_path.exists():
            logger.debug(f"Config file not found: {path}")
            return None

        try:
            if config_path.suffix in ('.yaml', '.yml'):
                import yaml
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            elif config_path.suffix == '.json':
                with open(config_path, 'r') as f:
                    return json.load(f)
            elif config_path.suffix in ('.ini', '.conf'):
                return self._load_ini(config_path)
            elif config_path.suffix == '.env':
                return self._load_env_file(config_path)
            else:
                # 尝试 JSON
                try:
                    with open(config_path, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    return self._load_ini(config_path)
        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
            return None

    def _load_from_env(self, prefix: str) -> Dict[str, Any]:
        """从环境变量加载配置"""
        config = {}

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # 转换环境变量名为配置键
                config_key = key[len(prefix):].lower()
                config[config_key] = self._parse_env_value(value)

        return config

    def _load_env_file(self, path: Path) -> Dict[str, Any]:
        """加载 .env 文件"""
        config = {}
        try:
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip().lower()
                    value = value.strip().strip('"\'')
                    config[key] = self._parse_env_value(value)
        except Exception as e:
            logger.error(f"Failed to load env file {path}: {e}")
        return config

    def _load_ini(self, path: Path) -> Dict[str, Any]:
        """加载 INI 文件"""
        import configparser
        config = {}
        parser = configparser.ConfigParser()
        parser.read(path)
        for section in parser.sections():
            for key, value in parser.items(section):
                config[f"{section}.{key}"] = self._parse_env_value(value)
        return config

    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值"""
        # 布尔值
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        if value.lower() in ('false', 'no', 'off', '0'):
            return False

        # 数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # JSON 数组/对象
        if value.startswith('[') or value.startswith('{'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        # 字符串（去除引号）
        return value.strip('"\'')

    def _apply_config(
        self,
        settings: Settings,
        config: Dict[str, Any],
        source: ConfigSource
    ) -> None:
        """应用配置到 Settings 对象"""
        for key, value in config.items():
            # 处理嵌套配置
            if '.' in key:
                section, field = key.split('.', 1)
                if hasattr(settings, section):
                    section_obj = getattr(settings, section)
                    if isinstance(section_obj, dict):
                        section_obj[field] = value
                continue

            # 直接配置
            if hasattr(settings, key):
                settings.set(key, value, source)
            else:
                settings.custom[key] = value
                settings._config_sources[key] = source

    def save(
        self,
        settings: Settings,
        path: str,
        format: str = "json",
        exclude_defaults: bool = False
    ) -> bool:
        """
        保存配置到文件

        Args:
            settings: 配置对象
            path: 文件路径
            format: 文件格式 (json/yaml)
            exclude_defaults: 是否排除默认值

        Returns:
            是否保存成功
        """
        config_dict = settings.to_dict()

        # 排除默认值
        if exclude_defaults:
            default_settings = self.settings_class()
            default_dict = default_settings.to_dict()
            config_dict = {
                k: v for k, v in config_dict.items()
                if k.startswith('_') or v != default_dict.get(k)
            }

        try:
            config_path = Path(path)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            if format == "json":
                with open(config_path, 'w') as f:
                    json.dump(config_dict, f, indent=2)
            elif format == "yaml":
                import yaml
                with open(config_path, 'w') as f:
                    yaml.safe_dump(config_dict, f, default_flow_style=False)
            else:
                logger.error(f"Unsupported format: {format}")
                return False

            logger.info(f"Saved config to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False


# 全局配置实例
_global_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置"""
    global _global_settings
    if _global_settings is None:
        _global_settings = ConfigLoader().load()
    return _global_settings


def set_settings(settings: Settings) -> None:
    """设置全局配置"""
    global _global_settings
    _global_settings = settings


def reload_settings(**overrides) -> Settings:
    """重新加载配置"""
    global _global_settings
    _global_settings = ConfigLoader().load(**overrides)
    return _global_settings
