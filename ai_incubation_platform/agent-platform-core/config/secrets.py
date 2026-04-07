"""
密钥管理

提供安全的密钥存储和访问功能
"""

import os
import base64
import hashlib
import logging
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import time
from enum import Enum

logger = logging.getLogger(__name__)


class SecretType(Enum):
    """密钥类型"""
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    ENCRYPTION_KEY = "encryption_key"
    DATABASE_URL = "database_url"
    CUSTOM = "custom"


class SecretStoreType(Enum):
    """密钥存储类型"""
    MEMORY = "memory"
    FILE = "file"
    ENV = "env"
    VAULT = "vault"  # HashiCorp Vault
    AWS_SECRETS = "aws_secrets"
    AZURE_KEY_VAULT = "azure_key_vault"
    GCP_SECRET_MANAGER = "gcp_secret_manager"


@dataclass
class SecretEntry:
    """密钥条目"""
    name: str
    value: str
    secret_type: SecretType = SecretType.CUSTOM
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def masked_value(self) -> str:
        """脱敏后的值"""
        if len(self.value) <= 4:
            return "*" * len(self.value)
        return self.value[:2] + "*" * (len(self.value) - 4) + self.value[-2:]

    def to_dict(self, include_value: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "name": self.name,
            "secret_type": self.secret_type.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "is_expired": self.is_expired,
            "metadata": self.metadata,
            "tags": self.tags
        }
        if include_value:
            result["value"] = self.value
        else:
            result["masked_value"] = self.masked_value
        return result


class SecretsManager:
    """
    密钥管理器

    功能:
    - 安全存储密钥
    - 支持多种存储后端
    - 自动过期管理
    - 访问审计
    """

    def __init__(
        self,
        store_type: SecretStoreType = SecretStoreType.MEMORY,
        encryption_key: Optional[str] = None,
        store_path: Optional[str] = None,
        store_config: Optional[Dict] = None
    ):
        """
        初始化密钥管理器

        Args:
            store_type: 存储类型
            encryption_key: 加密密钥（用于文件加密）
            store_path: 存储路径（文件存储时使用）
            store_config: 存储配置（云服务时使用）
        """
        self.store_type = store_type
        self.encryption_key = encryption_key
        self.store_path = store_path
        self.store_config = store_config or {}

        # 内存存储
        self._secrets: Dict[str, SecretEntry] = {}
        self._access_log: List[Dict[str, Any]] = []

        # 加载现有密钥
        if store_type == SecretStoreType.FILE and store_path:
            self._load_from_file()
        elif store_type == SecretStoreType.ENV:
            self._load_from_env()

        logger.info(f"SecretsManager initialized (type={store_type.value})")

    def set(
        self,
        name: str,
        value: str,
        secret_type: SecretType = SecretType.CUSTOM,
        expires_in: Optional[int] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> SecretEntry:
        """
        设置密钥

        Args:
            name: 密钥名称
            value: 密钥值
            secret_type: 密钥类型
            expires_in: 过期时间（秒）
            metadata: 元数据
            tags: 标签

        Returns:
            SecretEntry: 密钥条目
        """
        now = time.time()
        entry = SecretEntry(
            name=name,
            value=self._encrypt(value),
            secret_type=secret_type,
            created_at=now,
            updated_at=now,
            expires_at=now + expires_in if expires_in else None,
            metadata=metadata or {},
            tags=tags or []
        )

        self._secrets[name] = entry
        logger.info(f"Set secret: {name} (type={secret_type.value})")

        # 文件存储时保存
        if self.store_type == SecretStoreType.FILE and self.store_path:
            self._save_to_file()

        return entry

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取密钥

        Args:
            name: 密钥名称
            default: 默认值

        Returns:
            密钥值，不存在或已过期时返回 None/default
        """
        entry = self._secrets.get(name)

        if entry is None:
            logger.warning(f"Secret not found: {name}")
            return default

        if entry.is_expired:
            logger.warning(f"Secret expired: {name}")
            del self._secrets[name]
            return default

        # 记录访问
        self._log_access(name, "get")

        return self._decrypt(entry.value)

    def get_entry(self, name: str) -> Optional[SecretEntry]:
        """获取密钥条目（不包含值）"""
        entry = self._secrets.get(name)
        if entry and not entry.is_expired:
            return entry
        return None

    def delete(self, name: str) -> bool:
        """删除密钥"""
        if name in self._secrets:
            del self._secrets[name]
            logger.info(f"Deleted secret: {name}")

            # 文件存储时保存
            if self.store_type == SecretStoreType.FILE and self.store_path:
                self._save_to_file()

            return True
        return False

    def list_secrets(
        self,
        secret_type: Optional[SecretType] = None,
        tags: Optional[List[str]] = None,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        列出密钥

        Args:
            secret_type: 密钥类型过滤
            tags: 标签过滤
            include_expired: 是否包含已过期的

        Returns:
            密钥信息列表（不包含值）
        """
        results = []

        for entry in self._secrets.values():
            # 过滤过期
            if not include_expired and entry.is_expired:
                continue

            # 过滤类型
            if secret_type and entry.secret_type != secret_type:
                continue

            # 过滤标签
            if tags and not any(tag in entry.tags for tag in tags):
                continue

            results.append(entry.to_dict())

        return results

    def rotate(
        self,
        name: str,
        new_value: str,
        keep_old_version: bool = False
    ) -> SecretEntry:
        """
        轮换密钥

        Args:
            name: 密钥名称
            new_value: 新值
            keep_old_version: 是否保留旧版本

        Returns:
            SecretEntry: 新的密钥条目
        """
        old_entry = self._secrets.get(name)
        if not old_entry:
            raise ValueError(f"Secret not found: {name}")

        # 创建新条目
        now = time.time()
        new_entry = SecretEntry(
            name=name,
            value=self._encrypt(new_value),
            secret_type=old_entry.secret_type,
            created_at=now,
            updated_at=now,
            expires_at=old_entry.expires_at,
            metadata=old_entry.metadata,
            tags=old_entry.tags
        )

        # 保留旧版本
        if keep_old_version:
            old_name = f"{name}_old_{int(now)}"
            old_entry.name = old_name
            old_entry.metadata["rotated_from"] = name
            old_entry.metadata["rotation_time"] = now
            self._secrets[old_name] = old_entry

        self._secrets[name] = new_entry
        logger.info(f"Rotated secret: {name}")

        # 文件存储时保存
        if self.store_type == SecretStoreType.FILE and self.store_path:
            self._save_to_file()

        return new_entry

    def _encrypt(self, value: str) -> str:
        """加密值"""
        if not self.encryption_key:
            return value

        # 简单 XOR 加密（生产环境应使用更安全的算法）
        key = hashlib.sha256(self.encryption_key.encode()).digest()
        value_bytes = value.encode('utf-8')
        encrypted = bytes(a ^ b for a, b in zip(value_bytes, key * (len(value_bytes) // len(key) + 1)))
        return base64.b64encode(encrypted).decode('utf-8')

    def _decrypt(self, encrypted_value: str) -> str:
        """解密值"""
        if not self.encryption_key:
            return encrypted_value

        try:
            encrypted_bytes = base64.b64decode(encrypted_value)
            key = hashlib.sha256(self.encryption_key.encode()).digest()
            decrypted = bytes(a ^ b for a, b in zip(encrypted_bytes, key * (len(encrypted_bytes) // len(key) + 1)))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt: {e}")
            raise

    def _load_from_file(self) -> None:
        """从文件加载"""
        path = Path(self.store_path)
        if not path.exists():
            return

        try:
            with open(path, 'r') as f:
                data = json.load(f)

            for name, entry_data in data.items():
                entry = SecretEntry(
                    name=entry_data.get("name", name),
                    value=entry_data.get("value", ""),
                    secret_type=SecretType(entry_data.get("secret_type", "custom")),
                    created_at=entry_data.get("created_at", time.time()),
                    updated_at=entry_data.get("updated_at", time.time()),
                    expires_at=entry_data.get("expires_at"),
                    metadata=entry_data.get("metadata", {}),
                    tags=entry_data.get("tags", [])
                )
                self._secrets[name] = entry

            logger.info(f"Loaded {len(self._secrets)} secrets from {self.store_path}")
        except Exception as e:
            logger.error(f"Failed to load secrets from file: {e}")

    def _save_to_file(self) -> None:
        """保存到文件"""
        try:
            path = Path(self.store_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                name: entry.to_dict(include_value=True)
                for name, entry in self._secrets.items()
            }

            with open(path, 'w') as f:
                json.dump(data, f, indent=2)

            # 设置文件权限
            os.chmod(path, 0o600)

            logger.info(f"Saved {len(self._secrets)} secrets to {self.store_path}")
        except Exception as e:
            logger.error(f"Failed to save secrets to file: {e}")

    def _load_from_env(self) -> None:
        """从环境变量加载"""
        prefix = "SECRET_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                name = key[len(prefix):].lower()
                self.set(name, value, secret_type=SecretType.CUSTOM)

    def _log_access(self, name: str, action: str) -> None:
        """记录访问日志"""
        self._access_log.append({
            "name": name,
            "action": action,
            "timestamp": time.time()
        })

        # 限制日志大小
        if len(self._access_log) > 1000:
            self._access_log = self._access_log[-1000:]

    def get_access_log(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取访问日志"""
        if name:
            return [log for log in self._access_log if log["name"] == name]
        return self._access_log

    def export(self, include_values: bool = False) -> str:
        """
        导出密钥

        Args:
            include_values: 是否包含值（谨慎使用）

        Returns:
            JSON 字符串
        """
        data = {
            name: entry.to_dict(include_value=include_values)
            for name, entry in self._secrets.items()
        }
        return json.dumps(data, indent=2)

    def import_secrets(self, data: Dict[str, Any]) -> int:
        """
        导入密钥

        Args:
            data: 密钥数据

        Returns:
            导入数量
        """
        count = 0
        for name, entry_data in data.items():
            try:
                self.set(
                    name=entry_data.get("name", name),
                    value=entry_data.get("value", ""),
                    secret_type=SecretType(entry_data.get("secret_type", "custom")),
                    expires_in=None,  # 从 expires_at 计算
                    metadata=entry_data.get("metadata", {}),
                    tags=entry_data.get("tags", [])
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to import secret {name}: {e}")
        return count

    def cleanup_expired(self) -> int:
        """清理过期密钥"""
        expired = [
            name for name, entry in self._secrets.items()
            if entry.is_expired
        ]
        for name in expired:
            del self._secrets[name]
        logger.info(f"Cleaned up {len(expired)} expired secrets")
        return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        now = time.time()
        by_type = {}
        expired_count = 0
        expiring_soon_count = 0

        for entry in self._secrets.values():
            # 按类型统计
            type_key = entry.secret_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            # 过期统计
            if entry.is_expired:
                expired_count += 1
            elif entry.expires_at and (entry.expires_at - now) < 86400 * 7:
                # 7 天内过期
                expiring_soon_count += 1

        return {
            "total_count": len(self._secrets),
            "expired_count": expired_count,
            "expiring_soon_count": expiring_soon_count,
            "by_type": by_type
        }


# 全局默认实例
_default_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """获取默认密钥管理器"""
    global _default_secrets_manager
    if _default_secrets_manager is None:
        # 从环境变量获取配置
        store_type = os.environ.get("SECRETS_STORE_TYPE", "memory")
        store_type_map = {
            "memory": SecretStoreType.MEMORY,
            "file": SecretStoreType.FILE,
            "env": SecretStoreType.ENV
        }
        _default_secrets_manager = SecretsManager(
            store_type=store_type_map.get(store_type, SecretStoreType.MEMORY),
            encryption_key=os.environ.get("SECRETS_ENCRYPTION_KEY"),
            store_path=os.environ.get("SECRETS_STORE_PATH")
        )
    return _default_secrets_manager


def set_secrets_manager(manager: SecretsManager) -> None:
    """设置默认密钥管理器"""
    global _default_secrets_manager
    _default_secrets_manager = manager
