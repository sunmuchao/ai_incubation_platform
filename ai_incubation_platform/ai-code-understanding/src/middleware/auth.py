"""
API Key 认证中间件

提供基于 API Key 的身份验证机制，保护 API 端点免受未授权访问。
"""
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Set
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from functools import wraps
import json
from pathlib import Path


# API Key 在 Header 中的名称
API_KEY_HEADER_NAME = "X-API-Key"

# 默认 API Key 存储文件
API_KEYS_FILE = Path(__file__).parent.parent / "config" / "api_keys.json"


class APIKeyManager:
    """
    API Key 管理器

    负责 API Key 的创建、验证、撤销和持久化管理。
    支持多 Key 管理，每个 Key 可关联不同的权限和使用限制。
    """

    def __init__(self, keys_file: Optional[Path] = None):
        self.keys_file = keys_file or API_KEYS_FILE
        self._keys: Dict[str, Dict] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """从文件加载 API Keys"""
        if self.keys_file.exists():
            try:
                with open(self.keys_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._keys = data.get('api_keys', {})
            except (json.JSONDecodeError, IOError) as e:
                print(f"警告：加载 API Keys 文件失败：{e}")
                self._keys = {}
        else:
            # 首次运行时创建默认 Key
            self._create_default_key()
            self._save_keys()

    def _save_keys(self) -> None:
        """保存 API Keys 到文件"""
        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.keys_file, 'w', encoding='utf-8') as f:
            json.dump({'api_keys': self._keys}, f, indent=2, ensure_ascii=False)

    def _create_default_key(self) -> str:
        """创建默认 API Key"""
        default_key = "sk-ai-code-understanding-default-key-change-me"
        self._keys[default_key] = {
            'name': 'Default Key',
            'created_at': datetime.now().isoformat(),
            'expires_at': None,  # 永不过期
            'enabled': True,
            'permissions': ['read', 'write'],
            'usage_count': 0,
            'last_used_at': None
        }
        print(f"已创建默认 API Key: {default_key}")
        print("警告：请在生产环境中修改默认 API Key！")
        return default_key

    def create_key(
        self,
        name: str,
        permissions: Optional[Set[str]] = None,
        expires_in_days: Optional[int] = None
    ) -> str:
        """
        创建新的 API Key

        Args:
            name: Key 的名称/描述
            permissions: 权限集合，如 {'read', 'write'}
            expires_in_days: 过期天数，None 表示永不过期

        Returns:
            生成的 API Key 字符串
        """
        # 生成随机 Key
        random_bytes = secrets.token_bytes(32)
        api_key = f"sk-{random_bytes.hex()}"

        # 计算过期时间
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()

        # 存储 Key 信息
        self._keys[api_key] = {
            'name': name,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at,
            'enabled': True,
            'permissions': permissions or ['read', 'write'],
            'usage_count': 0,
            'last_used_at': None
        }

        self._save_keys()
        return api_key

    def validate_key(self, api_key: str) -> Optional[Dict]:
        """
        验证 API Key 是否有效

        Args:
            api_key: 待验证的 API Key

        Returns:
            Key 信息字典（如果有效），否则 None
        """
        if api_key not in self._keys:
            return None

        key_info = self._keys[api_key]

        # 检查是否启用
        if not key_info.get('enabled', True):
            return None

        # 检查是否过期
        expires_at = key_info.get('expires_at')
        if expires_at:
            try:
                if datetime.fromisoformat(expires_at) < datetime.now():
                    return None
            except ValueError:
                return None

        return key_info

    def update_usage(self, api_key: str) -> None:
        """更新 API Key 的使用记录"""
        if api_key in self._keys:
            self._keys[api_key]['usage_count'] = self._keys[api_key].get('usage_count', 0) + 1
            self._keys[api_key]['last_used_at'] = datetime.now().isoformat()
            self._save_keys()

    def revoke_key(self, api_key: str) -> bool:
        """
        撤销 API Key

        Args:
            api_key: 待撤销的 Key

        Returns:
            是否成功撤销
        """
        if api_key in self._keys:
            self._keys[api_key]['enabled'] = False
            self._save_keys()
            return True
        return False

    def delete_key(self, api_key: str) -> bool:
        """
        永久删除 API Key

        Args:
            api_key: 待删除的 Key

        Returns:
            是否成功删除
        """
        if api_key in self._keys:
            del self._keys[api_key]
            self._save_keys()
            return True
        return False

    def list_keys(self) -> Dict[str, Dict]:
        """
        列出所有 API Key（不包含完整 Key 值）

        Returns:
            Key 信息字典，Key 值被部分隐藏
        """
        result = {}
        for key, info in self._keys.items():
            # 隐藏 Key 的中间部分
            masked_key = f"{key[:8]}...{key[-8:]}" if len(key) > 16 else "***"
            result[masked_key] = {
                'name': info['name'],
                'created_at': info['created_at'],
                'expires_at': info.get('expires_at'),
                'enabled': info['enabled'],
                'permissions': info['permissions'],
                'usage_count': info.get('usage_count', 0),
                'last_used_at': info.get('last_used_at')
            }
        return result


# 创建全局管理器实例
api_key_manager = APIKeyManager()

# FastAPI 安全依赖
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    获取并验证 API Key

    用作 FastAPI 依赖注入，自动从 Header 中提取并验证 API Key

    Args:
        api_key: 从 Header 中提取的 API Key

    Returns:
        有效的 API Key

    Raises:
        HTTPException: 如果 Key 无效或缺失
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="缺少 API Key，请在请求头中提供 X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    key_info = api_key_manager.validate_key(api_key)
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail="无效的 API Key 或 Key 已过期/被撤销",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # 更新使用记录
    api_key_manager.update_usage(api_key)

    return api_key


async def verify_api_key_optional(request: Request) -> Optional[str]:
    """
    可选的 API Key 验证

    如果提供了 API Key 则验证，不提供也不报错
    用于区分匿名访问和认证访问的场景

    Args:
        request: FastAPI 请求对象

    Returns:
        有效的 API Key 或 None
    """
    api_key = request.headers.get(API_KEY_HEADER_NAME)
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info:
            api_key_manager.update_usage(api_key)
            return api_key
    return None


def require_auth(func):
    """
    要求认证的装饰器

    用于同步函数的简单认证装饰器
    """
    @wraps(func)
    async def wrapper(*args, request: Request, **kwargs):
        api_key = request.headers.get(API_KEY_HEADER_NAME)
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="缺少 API Key"
            )

        key_info = api_key_manager.validate_key(api_key)
        if not key_info:
            raise HTTPException(
                status_code=401,
                detail="无效的 API Key"
            )

        api_key_manager.update_usage(api_key)
        return await func(*args, **kwargs)

    return wrapper


# ============= 管理工具函数 =============

def generate_api_key(name: str = "Unnamed", expires_in_days: Optional[int] = None) -> str:
    """
    生成新的 API Key 的便捷函数

    Args:
        name: Key 名称
        expires_in_days: 过期天数

    Returns:
        生成的 API Key
    """
    return api_key_manager.create_key(name=name, expires_in_days=expires_in_days)


def revoke_api_key(api_key: str) -> bool:
    """撤销 API Key"""
    return api_key_manager.revoke_key(api_key)


def list_api_keys() -> Dict:
    """列出所有 API Key"""
    return api_key_manager.list_keys()


def check_api_key_health() -> Dict:
    """
    检查 API Key 健康状况

    Returns:
        包含统计信息的字典
    """
    keys = api_key_manager.list_keys()
    total = len(keys)
    enabled = sum(1 for k in keys.values() if k['enabled'])
    expired = sum(1 for k in keys.values() if k.get('expires_at') and
                  datetime.fromisoformat(k['expires_at']) < datetime.now())

    return {
        'total_keys': total,
        'enabled_keys': enabled,
        'disabled_keys': total - enabled,
        'expired_keys': expired,
        'keys': keys
    }
