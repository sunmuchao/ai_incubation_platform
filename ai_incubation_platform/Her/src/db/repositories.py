"""
数据访问层 - Repositories
"""
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

from db.models import UserDB, MatchHistoryDB, ChatMessageDB, ChatConversationDB
from db.repositories_types import UserCreateData, UserUpdateData, MatchCreateData, MessageCreateData


class UserRepository:
    """用户数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_data: UserCreateData) -> UserDB:
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
            username=user_data.get("username"),  # 用户名（登录标识）
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
            preferred_gender=user_data.get("preferred_gender"),
            sexual_orientation=user_data.get("sexual_orientation", "heterosexual"),
            # 🔧 [新增] 支持注册时设置偏好字段
            accept_remote=user_data.get("accept_remote"),
            relationship_goal=user_data.get("relationship_goal"),
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_by_id(self, user_id: str) -> Optional[UserDB]:
        """根据 ID 获取用户"""
        return self.db.query(UserDB).filter(UserDB.id == user_id).first()

    def get_by_ids(self, user_ids: List[str]) -> Dict[str, UserDB]:
        """
        批量获取用户（优化 N+1 查询）

        Args:
            user_ids: 用户 ID 列表

        Returns:
            用户 ID -> UserDB 的映射字典
        """
        if not user_ids:
            return {}

        # 单次批量查询
        users = self.db.query(UserDB).filter(UserDB.id.in_(user_ids)).all()

        # 构建 ID -> User 映射
        return {user.id: user for user in users}

    def get_by_email(self, email: str) -> Optional[UserDB]:
        """根据邮箱获取用户"""
        return self.db.query(UserDB).filter(UserDB.email == email).first()

    def get_by_email_batch(self, emails: List[str]) -> Dict[str, UserDB]:
        """批量获取用户（按邮箱）"""
        if not emails:
            return {}
        users = self.db.query(UserDB).filter(UserDB.email.in_(emails)).all()
        return {user.email: user for user in users}

    def get_by_username(self, username: str) -> Optional[UserDB]:
        """根据用户名（username）获取用户"""
        return self.db.query(UserDB).filter(UserDB.username == username).first()

    def get_by_phone(self, phone: str) -> Optional[UserDB]:
        """根据手机号获取用户"""
        return self.db.query(UserDB).filter(UserDB.phone == phone).first()

    def update_phone_verification_code(
        self,
        user_id: str,
        verification_code: str,
        expires_at: datetime
    ) -> bool:
        """更新用户手机验证码"""
        user = self.get_by_id(user_id)
        if not user:
            return False

        user.phone_verification_code = verification_code
        user.phone_verification_expires_at = expires_at
        self.db.commit()
        return True

    def verify_phone(self, user_id: str, verification_code: str) -> bool:
        """验证手机号验证码"""
        user = self.get_by_id(user_id)
        if not user:
            return False

        from datetime import datetime
        # 检查验证码是否匹配且未过期
        if (user.phone_verification_code == verification_code and
            user.phone_verification_expires_at and
            user.phone_verification_expires_at > datetime.now()):
            user.phone_verified = True
            user.phone_verification_code = None
            user.phone_verification_expires_at = None
            self.db.commit()
            return True
        return False

    def list_all(self, is_active: bool = True) -> List[UserDB]:
        """获取用户列表"""
        query = self.db.query(UserDB)
        if is_active:
            query = query.filter(UserDB.is_active == True)
        return query.all()

    def update(self, user_id: str, update_data: UserUpdateData) -> Optional[UserDB]:
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
        """
        搜索用户

        注：filters 使用 Dict[str, Any] 因为搜索条件动态多变
        常用过滤条件：gender, age_min, age_max, location
        """
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

    def create(self, match_data: MatchCreateData) -> MatchHistoryDB:
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


# ============= 聊天 Repository =============

class ChatConversationRepository:
    """聊天会话数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id_1: str, user_id_2: str) -> ChatConversationDB:
        """获取或创建聊天会话"""
        # 尝试获取现有会话
        conversation = self.db.query(ChatConversationDB).filter(
            ((ChatConversationDB.user_id_1 == user_id_1) & (ChatConversationDB.user_id_2 == user_id_2)) |
            ((ChatConversationDB.user_id_1 == user_id_2) & (ChatConversationDB.user_id_2 == user_id_1))
        ).first()

        if conversation:
            return conversation

        # 创建新会话
        conversation = ChatConversationDB(
            id=f"conv-{datetime.now().timestamp()}",
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            status="active"
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversations(self, user_id: str) -> List[ChatConversationDB]:
        """获取用户的所有聊天会话"""
        return self.db.query(ChatConversationDB).filter(
            (ChatConversationDB.user_id_1 == user_id) | (ChatConversationDB.user_id_2 == user_id)
        ).order_by(ChatConversationDB.last_message_at.desc()).all()

    def update_last_message(self, conversation_id: str, message_preview: str) -> ChatConversationDB:
        """更新会话的最后一条消息"""
        conversation = self.db.query(ChatConversationDB).filter(
            ChatConversationDB.id == conversation_id
        ).first()
        if conversation:
            conversation.last_message_preview = message_preview
            conversation.last_message_at = datetime.now()
            self.db.commit()
            self.db.refresh(conversation)
        return conversation

    def increment_unread(self, conversation_id: str, user_id: str) -> None:
        """增加未读消息数"""
        conversation = self.db.query(ChatConversationDB).filter(
            ChatConversationDB.id == conversation_id
        ).first()
        if conversation:
            if conversation.user_id_1 == user_id:
                conversation.unread_count_user2 += 1
            else:
                conversation.unread_count_user1 += 1
            self.db.commit()

    def clear_unread(self, conversation_id: str, user_id: str) -> None:
        """清除未读消息数"""
        conversation = self.db.query(ChatConversationDB).filter(
            ChatConversationDB.id == conversation_id
        ).first()
        if conversation:
            if conversation.user_id_1 == user_id:
                conversation.unread_count_user1 = 0
            else:
                conversation.unread_count_user2 = 0
            self.db.commit()


class ChatMessageRepository:
    """聊天消息数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, message_data: MessageCreateData) -> ChatMessageDB:
        """创建消息"""
        message = ChatMessageDB(
            id=message_data.get("id", f"msg-{datetime.now().timestamp()}"),
            conversation_id=message_data["conversation_id"],
            sender_id=message_data["sender_id"],
            receiver_id=message_data["receiver_id"],
            message_type=message_data.get("message_type", "text"),
            content=message_data["content"]
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_by_conversation(self, conversation_id: str, limit: int = 50, offset: int = 0) -> List[ChatMessageDB]:
        """获取会话的消息历史"""
        return self.db.query(ChatMessageDB).filter(
            ChatMessageDB.conversation_id == conversation_id
        ).order_by(ChatMessageDB.created_at.asc()).offset(offset).limit(limit).all()

    def get_latest_messages(self, conversation_id: str, limit: int = 20) -> List[ChatMessageDB]:
        """获取最新的消息"""
        return self.db.query(ChatMessageDB).filter(
            ChatMessageDB.conversation_id == conversation_id
        ).order_by(ChatMessageDB.created_at.desc()).limit(limit).all()

    def mark_as_read(self, message_ids: List[str]) -> int:
        """标记消息为已读"""
        updated = self.db.query(ChatMessageDB).filter(
            ChatMessageDB.id.in_(message_ids)
        ).update({
            ChatMessageDB.is_read: True,
            ChatMessageDB.read_at: datetime.now(),
            ChatMessageDB.status: "read"
        }, synchronize_session=False)
        self.db.commit()
        return updated

    def count_unread(self, conversation_id: str, user_id: str) -> int:
        """统计未读消息数"""
        return self.db.query(ChatMessageDB).filter(
            ChatMessageDB.conversation_id == conversation_id,
            ChatMessageDB.receiver_id == user_id,
            ChatMessageDB.is_read == False
        ).count()
