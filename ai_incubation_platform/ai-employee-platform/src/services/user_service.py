"""
用户管理服务
负责用户的 CRUD 操作和认证
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.db_models import UserDB, UserRoleEnum
from services.base_service import BaseService
from config.settings import settings

import bcrypt
import jwt


class UserService(BaseService):
    """用户服务"""

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = bcrypt.gensalt(settings.bcrypt_rounds)
        return bcrypt.hashpw(password.encode(), salt).decode()

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode(), hashed_password.encode())

    def _create_access_token(self, user: UserDB) -> str:
        """创建 JWT 令牌"""
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
        to_encode = {
            "sub": user.id,
            "tenant_id": user.tenant_id,
            "role": user.role.value,
            "exp": expire
        }
        return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: str = "hirer"
    ) -> Optional[UserDB]:
        """创建用户"""
        try:
            # 检查用户名是否已存在
            existing = self.db.query(UserDB).filter(UserDB.username == username).first()
            if existing:
                self.logger.warning(f"Username already exists: {username}")
                return None

            hashed_password = self._hash_password(password)
            user = UserDB(
                tenant_id=tenant_id,
                username=username,
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                role=UserRoleEnum(role)
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            self.logger.info(f"Created user: {user.id}, username: {username}")
            return user
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create user: {str(e)}")
            raise

    def get_user(self, user_id: str) -> Optional[UserDB]:
        """获取用户"""
        return self.db.query(UserDB).filter(UserDB.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[UserDB]:
        """通过用户名获取用户"""
        return self.db.query(UserDB).filter(UserDB.username == username).first()

    def authenticate_user(self, username: str, password: str) -> Optional[UserDB]:
        """验证用户凭证"""
        user = self.get_user_by_username(username)
        if not user or not self._verify_password(password, user.hashed_password):
            return None
        user.last_login_at = datetime.now()
        self.db.commit()
        return user

    def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户登录"""
        user = self.authenticate_user(username, password)
        if not user or not user.is_active:
            return None

        access_token = self._create_access_token(user)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_expire_hours * 3600,
            "user": user
        }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT 令牌"""
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            user_id: str = payload.get("sub")
            tenant_id: str = payload.get("tenant_id")
            role: str = payload.get("role")
            if user_id is None or tenant_id is None:
                return None
            return {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "role": role
            }
        except jwt.PyJWTError:
            return None

    def update_user_role(self, user_id: str, role: str) -> bool:
        """更新用户角色"""
        user = self.get_user(user_id)
        if not user:
            return False

        try:
            user.role = UserRoleEnum(role)
            user.updated_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Updated user {user_id} role to {role}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to update user role: {str(e)}")
            raise
