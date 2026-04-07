"""
安全增强模块：API 密钥认证、速率限制、请求签名
"""
import hashlib
import hmac
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AuthMethod(str, Enum):
    """认证方式"""
    API_KEY = "api_key"
    REQUEST_SIGNATURE = "request_signature"
    JWT = "jwt"


class SecurityEvent(str, Enum):
    """安全事件类型"""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_SIGNATURE = "invalid_signature"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class SecurityAuditRecord:
    """安全审计记录"""

    def __init__(
        self,
        event_type: SecurityEvent,
        ip_address: str,
        endpoint: str,
        user_agent: Optional[str] = None,
        api_key_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.timestamp = datetime.utcnow()
        self.event_type = event_type
        self.ip_address = ip_address
        self.endpoint = endpoint
        self.user_agent = user_agent
        self.api_key_id = api_key_id
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "ip_address": self.ip_address,
            "endpoint": self.endpoint,
            "user_agent": self.user_agent,
            "api_key_id": self.api_key_id,
            "details": self.details
        }


class APIKeyManager:
    """API Key 管理器

    功能:
    - API Key 生成和验证
    - Key 权限管理
    - Key 过期时间管理
    """

    def __init__(self):
        self._api_keys: Dict[str, Dict[str, Any]] = {}
        self._key_by_hash: Dict[str, str] = {}  # hash -> key 映射

    def load_keys(self, keys_config: str) -> int:
        """从配置加载 API Keys

        Args:
            keys_config: 逗号分隔的 API Keys 配置
                格式：key1,key2,... 或 key1:admin,key2:readonly,...

        Returns:
            加载的 Key 数量
        """
        if not keys_config:
            return 0

        count = 0
        for item in keys_config.split(","):
            item = item.strip()
            if not item:
                continue

            if ":" in item:
                key, role = item.split(":", 1)
            else:
                key = item
                role = "admin"

            key_hash = self._hash_key(key)
            self._api_keys[key] = {
                "key": key,
                "role": role,
                "created_at": datetime.utcnow(),
                "last_used": None,
                "use_count": 0,
                "enabled": True
            }
            self._key_by_hash[key_hash] = key
            count += 1

        logger.info(f"Loaded {count} API keys")
        return count

    def add_key(
        self,
        key: str,
        role: str = "admin",
        expires_at: datetime = None,
        permissions: List[str] = None
    ) -> str:
        """添加 API Key

        Args:
            key: API Key 字符串
            role: 角色 (admin, readonly, metrics_only, etc.)
            expires_at: 过期时间
            permissions: 权限列表

        Returns:
            Key ID
        """
        key_hash = self._hash_key(key)
        self._api_keys[key] = {
            "key": key,
            "key_hash": key_hash,
            "role": role,
            "permissions": permissions or self._get_default_permissions(role),
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_used": None,
            "use_count": 0,
            "enabled": True
        }
        self._key_by_hash[key_hash] = key
        return key

    def _get_default_permissions(self, role: str) -> List[str]:
        """获取角色的默认权限"""
        if role == "admin":
            return ["read", "write", "delete", "admin"]
        elif role == "readonly":
            return ["read"]
        elif role == "metrics":
            return ["read:metrics", "write:metrics"]
        else:
            return ["read"]

    def validate_key(self, key: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """验证 API Key

        Args:
            key: API Key 字符串

        Returns:
            (是否有效，Key 信息，错误消息)
        """
        if key not in self._api_keys:
            return False, None, "Invalid API key"

        key_info = self._api_keys[key]

        if not key_info.get("enabled", True):
            return False, None, "API key is disabled"

        expires_at = key_info.get("expires_at")
        if expires_at and datetime.utcnow() > expires_at:
            return False, None, "API key has expired"

        # 更新使用统计
        key_info["last_used"] = datetime.utcnow()
        key_info["use_count"] = key_info.get("use_count", 0) + 1

        return True, key_info, None

    def validate_key_hash(self, key_hash: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """通过 hash 验证 API Key (用于从请求头中提取)"""
        if key_hash not in self._key_by_hash:
            return False, None, "Invalid API key"

        key = self._key_by_hash[key_hash]
        return self.validate_key(key)

    def _hash_key(self, key: str) -> str:
        """对 Key 进行哈希"""
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def generate_key(self, prefix: str = "ai_opt") -> str:
        """生成新的 API Key

        Args:
            prefix: Key 前缀

        Returns:
            生成的 API Key
        """
        import secrets
        random_part = secrets.token_urlsafe(24)
        return f"{prefix}_{random_part}"

    def get_key_stats(self) -> Dict[str, Any]:
        """获取 Key 使用统计"""
        total_keys = len(self._api_keys)
        enabled_keys = sum(1 for k in self._api_keys.values() if k.get("enabled", True))
        total_uses = sum(k.get("use_count", 0) for k in self._api_keys.values())

        return {
            "total_keys": total_keys,
            "enabled_keys": enabled_keys,
            "disabled_keys": total_keys - enabled_keys,
            "total_uses": total_uses
        }

    def revoke_key(self, key: str) -> bool:
        """撤销 API Key"""
        if key in self._api_keys:
            self._api_keys[key]["enabled"] = False
            del self._key_by_hash[self._hash_key(key)]
            logger.info(f"Revoked API key: {key[:8]}...")
            return True
        return False

    def list_keys(self) -> List[Dict[str, Any]]:
        """列出所有 Key (不返回完整的 key 值)"""
        return [
            {
                "key_prefix": k[:8] + "..." if len(k) > 8 else k,
                "role": v["role"],
                "created_at": v["created_at"].isoformat() if v.get("created_at") else None,
                "last_used": v["last_used"].isoformat() if v.get("last_used") else None,
                "use_count": v.get("use_count", 0),
                "enabled": v.get("enabled", True)
            }
            for k, v in self._api_keys.items()
        ]


class RateLimiter:
    """速率限制器

    实现滑动窗口算法进行速率限制
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """初始化速率限制器

        Args:
            max_requests: 窗口内最大请求数
            window_seconds: 窗口大小 (秒)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}  # key -> [timestamps]

    def is_allowed(self, key: str = "default") -> Tuple[bool, Dict[str, Any]]:
        """检查请求是否允许

        Args:
            key: 限制 key (可以是 IP、API key 等)

        Returns:
            (是否允许，限制信息)
        """
        now = time.time()
        window_start = now - self.window_seconds

        # 初始化或清理过期记录
        if key not in self._requests:
            self._requests[key] = []
        else:
            self._requests[key] = [t for t in self._requests[key] if t > window_start]

        # 检查是否超过限制
        current_count = len(self._requests[key])
        remaining = max(0, self.max_requests - current_count)
        reset_time = window_start + self.window_seconds

        info = {
            "limit": self.max_requests,
            "remaining": remaining,
            "reset_at": datetime.fromtimestamp(reset_time).isoformat(),
            "retry_after": max(0, reset_time - now) if remaining == 0 else 0
        }

        if current_count >= self.max_requests:
            return False, info

        # 记录请求
        self._requests[key].append(now)
        info["remaining"] = self.max_requests - len(self._requests[key])

        return True, info

    def get_stats(self, key: str = None) -> Dict[str, Any]:
        """获取速率限制统计"""
        if key:
            if key in self._requests:
                return {
                    "key": key,
                    "request_count": len(self._requests[key]),
                    "limit": self.max_requests,
                    "window_seconds": self.window_seconds
                }
            return {"key": key, "request_count": 0}

        return {
            "total_keys": len(self._requests),
            "limit": self.max_requests,
            "window_seconds": self.window_seconds
        }

    def reset(self, key: str = None):
        """重置速率限制"""
        if key:
            self._requests.pop(key, None)
        else:
            self._requests.clear()


class RequestSigner:
    """请求签名验证器

    使用 HMAC-SHA256 对请求进行签名验证
    """

    def __init__(self, secret: str):
        """初始化签名验证器

        Args:
            secret: 签名密钥
        """
        self.secret = secret.encode()

    def generate_signature(
        self,
        method: str,
        path: str,
        timestamp: str,
        body: str = ""
    ) -> str:
        """生成请求签名

        Args:
            method: HTTP 方法 (GET, POST, etc.)
            path: 请求路径
            timestamp: 时间戳字符串
            body: 请求体

        Returns:
            签名字符串 (hex)
        """
        # 构建签名字符串
        message = f"{method}\n{path}\n{timestamp}\n{body}"

        # 生成 HMAC-SHA256 签名
        signature = hmac.new(
            self.secret,
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def verify_signature(
        self,
        method: str,
        path: str,
        timestamp: str,
        signature: str,
        body: str = "",
        max_age_seconds: int = 300
    ) -> Tuple[bool, Optional[str]]:
        """验证请求签名

        Args:
            method: HTTP 方法
            path: 请求路径
            timestamp: 时间戳字符串
            signature: 签名
            body: 请求体
            max_age_seconds: 最大允许时间差 (秒)

        Returns:
            (是否有效，错误消息)
        """
        # 检查时间戳有效性
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.utcnow()
            age = abs((now - ts).total_seconds())

            if age > max_age_seconds:
                return False, f"Request timestamp too old (age: {age}s, max: {max_age_seconds}s)"

        except ValueError as e:
            return False, f"Invalid timestamp format: {e}"

        # 验证签名
        expected_signature = self.generate_signature(method, path, timestamp, body)

        if not hmac.compare_digest(signature, expected_signature):
            return False, "Invalid signature"

        return True, None


class SecurityAuditor:
    """安全审计器

    记录所有安全相关事件
    """

    def __init__(self, max_records: int = 10000):
        """初始化审计器

        Args:
            max_records: 最大保留记录数
        """
        self.max_records = max_records
        self._records: List[SecurityAuditRecord] = []

    def record_event(
        self,
        event_type: SecurityEvent,
        ip_address: str,
        endpoint: str,
        user_agent: Optional[str] = None,
        api_key_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录安全事件"""
        record = SecurityAuditRecord(
            event_type=event_type,
            ip_address=ip_address,
            endpoint=endpoint,
            user_agent=user_agent,
            api_key_id=api_key_id,
            details=details
        )
        self._records.append(record)

        # 清理旧记录
        if len(self._records) > self.max_records:
            self._records = self._records[-self.max_records:]

        logger.info(f"Security event: {event_type.value} from {ip_address} at {endpoint}")

    def get_events(
        self,
        event_type: SecurityEvent = None,
        ip_address: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """查询安全事件"""
        results = self._records

        if event_type:
            results = [r for r in results if r.event_type == event_type]
        if ip_address:
            results = [r for r in results if r.ip_address == ip_address]
        if start_time:
            results = [r for r in results if r.timestamp >= start_time]
        if end_time:
            results = [r for r in results if r.timestamp <= end_time]

        # 按时间倒序排序
        results = sorted(results, key=lambda r: r.timestamp, reverse=True)

        return [r.to_dict() for r in results[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        """获取审计统计"""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)

        return {
            "total_records": len(self._records),
            "max_records": self.max_records,
            "events_last_hour": sum(1 for r in self._records if r.timestamp > last_hour),
            "events_last_day": sum(1 for r in self._records if r.timestamp > last_day),
            "events_by_type": self._count_by_type()
        }

    def _count_by_type(self) -> Dict[str, int]:
        """按事件类型统计"""
        counts = {}
        for r in self._records:
            event_type = r.event_type.value
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts


# ==================== 全局实例 ====================

_api_key_manager: Optional[APIKeyManager] = None
_rate_limiter: Optional[RateLimiter] = None
_request_signer: Optional[RequestSigner] = None
_security_auditor: Optional[SecurityAuditor] = None


def get_api_key_manager() -> APIKeyManager:
    """获取 API Key 管理器实例"""
    global _api_key_manager
    if _api_key_manager is None:
        from core.config import config
        _api_key_manager = APIKeyManager()
        if config.api_keys:
            _api_key_manager.load_keys(config.api_keys)
    return _api_key_manager


def get_rate_limiter() -> RateLimiter:
    """获取速率限制器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        from core.config import config
        _rate_limiter = RateLimiter(
            max_requests=config.api_rate_limit_requests,
            window_seconds=60
        )
    return _rate_limiter


def get_request_signer() -> Optional[RequestSigner]:
    """获取请求签名器实例"""
    global _request_signer
    if _request_signer is None:
        from core.config import config
        if config.signing_secret:
            _request_signer = RequestSigner(config.signing_secret)
        else:
            _request_signer = None  # 未配置签名密钥
    return _request_signer


def get_security_auditor() -> SecurityAuditor:
    """获取安全审计器实例"""
    global _security_auditor
    if _security_auditor is None:
        _security_auditor = SecurityAuditor()
    return _security_auditor
