"""
数据访问层 - Repositories
"""
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

from db.models import UserDB, MatchHistoryDB


class UserRepository:
    """用户数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_data: Dict[str, Any]) -> UserDB:
        """创建用户"""
        # 处理列表转 JSON 字符串
        interests = user_data.get("interests", [])
        if isinstance(interests, list):
            interests = json.dumps(interests)

        # values 既可能是 dict（价值观维度），也可能是 list（兼容旧结构）
        values = user_data.get("values", {})
        if isinstance(values, (list, dict)):
            values = json.dumps(values)

        db_user = UserDB(
            id=user_data["id"],
            name=user_data["name"],
            email=user_data["email"],
            password_hash=user_data.get("password_hash", ""),
            age=user_data["age"],
            gender=user_data["gender"],
            location=user_data["location"],
            interests=interests,
            values=values,
            bio=user_data.get("bio", ""),
            avatar_url=user_data.get("avatar_url"),
            preferred_age_min=user_data.get("preferred_age_min", 18),
            preferred_age_max=user_data.get("preferred_age_max", 60),
            preferred_location=user_data.get("preferred_location"),
            preferred_gender=user_data.get("preferred_gender")
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_by_id(self, user_id: str) -> Optional[UserDB]:
        """根据 ID 获取用户"""
        return self.db.query(UserDB).filter(UserDB.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[UserDB]:
        """根据邮箱获取用户"""
        return self.db.query(UserDB).filter(UserDB.email == email).first()

    def list_all(self, is_active: bool = True) -> List[UserDB]:
        """获取用户列表"""
        query = self.db.query(UserDB)
        if is_active:
            query = query.filter(UserDB.is_active == True)
        return query.all()

    def update(self, user_id: str, update_data: Dict[str, Any]) -> Optional[UserDB]:
        """更新用户"""
        user = self.get_by_id(user_id)
        if not user:
            return None

        for key, value in update_data.items():
            if key == "interests" or key == "values":
                if isinstance(value, list):
                    value = json.dumps(value)
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user_id: str) -> bool:
        """删除用户（软删除）"""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.db.commit()
            return True
        return False

    def search(self, filters: Dict[str, Any]) -> List[UserDB]:
        """搜索用户"""
        query = self.db.query(UserDB).filter(UserDB.is_active == True)

        if "gender" in filters and filters["gender"]:
            query = query.filter(UserDB.gender == filters["gender"])
        if "age_min" in filters:
            query = query.filter(UserDB.age >= filters["age_min"])
        if "age_max" in filters:
            query = query.filter(UserDB.age <= filters["age_max"])
        if "location" in filters and filters["location"]:
            query = query.filter(UserDB.location.ilike(f"%{filters['location']}%"))

        return query.all()


class MatchHistoryRepository:
    """匹配历史数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, match_data: Dict[str, Any]) -> MatchHistoryDB:
        """创建匹配记录"""
        db_match = MatchHistoryDB(
            id=match_data["id"],
            user_id_1=match_data["user_id_1"],
            user_id_2=match_data["user_id_2"],
            compatibility_score=match_data["compatibility_score"],
            status=match_data.get("status", "pending")
        )
        self.db.add(db_match)
        self.db.commit()
        self.db.refresh(db_match)
        return db_match

    def get_by_user(self, user_id: str) -> List[MatchHistoryDB]:
        """获取用户的匹配历史"""
        return self.db.query(MatchHistoryDB).filter(
            (MatchHistoryDB.user_id_1 == user_id) |
            (MatchHistoryDB.user_id_2 == user_id)
        ).all()

    def update_status(self, match_id: str, status: str) -> Optional[MatchHistoryDB]:
        """更新匹配状态"""
        match = self.db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()
        if match:
            match.status = status
            match.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(match)
        return match

    def get_mutual_matches(self, user_id_1: str, user_id_2: str) -> List[MatchHistoryDB]:
        """获取双方匹配记录"""
        return self.db.query(MatchHistoryDB).filter(
            ((MatchHistoryDB.user_id_1 == user_id_1) & (MatchHistoryDB.user_id_2 == user_id_2)) |
            ((MatchHistoryDB.user_id_1 == user_id_2) & (MatchHistoryDB.user_id_2 == user_id_1))
        ).all()
