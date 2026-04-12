"""
虚拟礼物服务

参考 Soul/探探的礼物系统：
- 多种礼物类型和价格层级
- 礼物发送和动画展示
- 礼物统计和收入管理
"""
from datetime import datetime
from typing import Optional, List, Tuple
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from models.gift import (
    Gift,
    GiftSendRequest,
    GiftSendResponse,
    GiftTransaction,
    GiftStoreResponse,
    UserGiftStats,
    GIFT_CONFIG,
    GiftType,
    GiftCategory,
    GiftTransactionDB,
    UserGiftStatsDB,
)
from db.repositories import UserRepository
from utils.logger import logger
from services.base_service import BaseService


class GiftService(BaseService):
    """虚拟礼物服务"""

    def __init__(self, db: Session):
        super().__init__(db)

    def get_gift_store(self) -> GiftStoreResponse:
        """获取礼物商店"""
        gifts = []
        popular_gifts = []
        new_gifts = []

        for gift_id, config in GIFT_CONFIG.items():
            gift = Gift(
                id=gift_id,
                name=config["name"],
                type=config["type"],
                category=config["category"],
                price=config["price"],
                icon=config["icon"],
                animation=config.get("animation"),
                description=config["description"],
                fullscreen=config.get("fullscreen", False),
                is_popular=gift_id in ["rose_single", "rose_bouquet", "coffee"],
                is_new=gift_id in ["love_balloon"],
            )
            gifts.append(gift)

            if gift.is_popular:
                popular_gifts.append(gift)
            if gift.is_new:
                new_gifts.append(gift)

        # 按价格排序
        gifts.sort(key=lambda x: x.price)
        popular_gifts.sort(key=lambda x: x.price)

        # 分类整理
        categories = [
            {"id": "love", "name": "爱情浪漫", "icon": "❤️"},
            {"id": "food", "name": "餐饮美食", "icon": "☕"},
            {"id": "birthday", "name": "生日庆祝", "icon": "🎂"},
            {"id": "festival", "name": "节日庆典", "icon": "🎆"},
            {"id": "funny", "name": "搞怪趣味", "icon": "😜"},
        ]

        return GiftStoreResponse(
            categories=categories,
            gifts=gifts,
            popular_gifts=popular_gifts,
            new_gifts=new_gifts,
        )

    def send_gift(
        self,
        sender_id: str,
        request: GiftSendRequest
    ) -> GiftSendResponse:
        """
        发送礼物

        Args:
            sender_id: 发送者 ID
            request: 发送请求

        Returns:
            GiftSendResponse: 发送结果
        """
        # 1. 获取礼物配置
        gift_config = GIFT_CONFIG.get(request.gift_id)
        if not gift_config:
            return GiftSendResponse(
                success=False,
                message="礼物不存在",
                gift_id=request.gift_id,
                gift_name="",
                total_price=0,
            )

        # 2. 检查目标用户
        user_repo = UserRepository(self.db)
        target_user = user_repo.get_by_id(request.target_user_id)
        if not target_user:
            return GiftSendResponse(
                success=False,
                message="目标用户不存在",
                gift_id=request.gift_id,
                gift_name=gift_config["name"],
                total_price=0,
            )

        # 3. 计算总金额
        total_price = gift_config["price"] * request.count

        # 4. 检查用户余额（如果有）
        # 余额检查暂未实现（集成支付系统后可检查用户虚拟货币余额）

        # 5. 创建交易记录
        transaction = GiftTransactionDB(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=request.target_user_id,
            gift_id=request.gift_id,
            gift_name=gift_config["name"],
            gift_icon=gift_config["icon"],
            gift_type=gift_config["type"].value,
            gift_category=gift_config["category"].value,
            count=request.count,
            price=gift_config["price"],
            total_amount=total_price,
            message=request.message,
        )
        self.db.add(transaction)

        # 6. 更新用户礼物统计
        self._update_user_stats(sender_id, request.target_user_id, request.gift_id, total_price)

        self.db.commit()

        logger.info(f"Gift sent: {sender_id} -> {request.target_user_id}, gift={request.gift_id}, count={request.count}")

        return GiftSendResponse(
            success=True,
            message=f"已发送 {gift_config['icon']} {gift_config['name']}",
            gift_id=request.gift_id,
            gift_name=gift_config["name"],
            total_price=total_price,
            transaction_id=transaction.id,
        )

    def _update_user_stats(
        self,
        sender_id: str,
        receiver_id: str,
        gift_id: str,
        amount: float
    ):
        """更新用户礼物统计"""
        # 更新发送者统计
        sender_stats = self.db.query(UserGiftStatsDB).filter(
            UserGiftStatsDB.user_id == sender_id
        ).first()

        if not sender_stats:
            sender_stats = UserGiftStatsDB(
                id=str(uuid.uuid4()),
                user_id=sender_id,
            )
            self.db.add(sender_stats)

        sender_stats.total_sent_count += 1
        sender_stats.total_sent_amount += amount

        # 更新发送最多的礼物
        if sender_stats.most_sent_gift_id == gift_id:
            sender_stats.most_sent_gift_count += 1
        elif sender_stats.most_sent_gift_count < 1:
            sender_stats.most_sent_gift_id = gift_id
            sender_stats.most_sent_gift_count = 1

        # 更新接收者统计
        receiver_stats = self.db.query(UserGiftStatsDB).filter(
            UserGiftStatsDB.user_id == receiver_id
        ).first()

        if not receiver_stats:
            receiver_stats = UserGiftStatsDB(
                id=str(uuid.uuid4()),
                user_id=receiver_id,
            )
            self.db.add(receiver_stats)

        receiver_stats.total_received_count += 1
        receiver_stats.total_received_amount += amount

        # 更新收到最多的礼物
        if receiver_stats.most_received_gift_id == gift_id:
            receiver_stats.most_received_gift_count += 1
        elif receiver_stats.most_received_gift_count < 1:
            receiver_stats.most_received_gift_id = gift_id
            receiver_stats.most_received_gift_count = 1

        # 更新 top sender/receiver
        if sender_stats.total_sent_amount > receiver_stats.top_sender_amount or not receiver_stats.top_sender_id:
            receiver_stats.top_sender_id = sender_id
            receiver_stats.top_sender_amount = sender_stats.total_sent_amount

        if receiver_stats.total_received_amount > sender_stats.top_receiver_amount or not sender_stats.top_receiver_id:
            sender_stats.top_receiver_id = receiver_id
            sender_stats.top_receiver_amount = receiver_stats.total_received_amount

    def get_user_received_gifts(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[GiftTransaction]:
        """获取用户收到的礼物"""
        transactions = self.db.query(GiftTransactionDB).filter(
            GiftTransactionDB.receiver_id == user_id
        ).order_by(GiftTransactionDB.sent_at.desc()).limit(limit).all()

        results = []
        for t in transactions:
            results.append(GiftTransaction(
                id=t.id,
                sender_id=t.sender_id,
                receiver_id=t.receiver_id,
                gift_id=t.gift_id,
                gift_name=t.gift_name,
                gift_icon=t.gift_icon,
                gift_type=GiftType(t.gift_type),
                count=t.count,
                price=t.price,
                total_amount=t.total_amount,
                message=t.message,
                sent_at=t.sent_at,
                is_seen=t.is_seen,
                seen_at=t.seen_at,
            ))

        return results

    def get_user_sent_gifts(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[GiftTransaction]:
        """获取用户发送的礼物"""
        transactions = self.db.query(GiftTransactionDB).filter(
            GiftTransactionDB.sender_id == user_id
        ).order_by(GiftTransactionDB.sent_at.desc()).limit(limit).all()

        results = []
        for t in transactions:
            results.append(GiftTransaction(
                id=t.id,
                sender_id=t.sender_id,
                receiver_id=t.receiver_id,
                gift_id=t.gift_id,
                gift_name=t.gift_name,
                gift_icon=t.gift_icon,
                gift_type=GiftType(t.gift_type),
                count=t.count,
                price=t.price,
                total_amount=t.total_amount,
                message=t.message,
                sent_at=t.sent_at,
                is_seen=t.is_seen,
                seen_at=t.seen_at,
            ))

        return results

    def get_user_stats(self, user_id: str) -> UserGiftStats:
        """获取用户礼物统计"""
        stats = self.db.query(UserGiftStatsDB).filter(
            UserGiftStatsDB.user_id == user_id
        ).first()

        if not stats:
            return UserGiftStats(
                user_id=user_id,
                total_received=0,
                total_received_amount=0,
                total_sent=0,
                total_sent_amount=0,
            )

        return UserGiftStats(
            user_id=user_id,
            total_received=stats.total_received_count,
            total_received_amount=stats.total_received_amount,
            total_sent=stats.total_sent_count,
            total_sent_amount=stats.total_sent_amount,
            most_received_gift=stats.most_received_gift_id,
            most_sent_gift=stats.most_sent_gift_id,
            top_sender=stats.top_sender_id,
            top_receiver=stats.top_receiver_id,
        )

    def mark_gift_seen(self, transaction_id: str) -> bool:
        """标记礼物已查看"""
        transaction = self.db.query(GiftTransactionDB).filter(
            GiftTransactionDB.id == transaction_id
        ).first()

        if not transaction:
            return False

        transaction.is_seen = True
        transaction.seen_at = datetime.now()
        self.db.commit()

        return True

    def get_unseen_gifts_count(self, user_id: str) -> int:
        """获取未查看礼物数量"""
        count = self.db.query(GiftTransactionDB).filter(
            GiftTransactionDB.receiver_id == user_id,
            GiftTransactionDB.is_seen == False
        ).count()

        return count

    def get_gift_by_id(self, gift_id: str) -> Optional[Gift]:
        """获取单个礼物信息"""
        config = GIFT_CONFIG.get(gift_id)
        if not config:
            return None

        return Gift(
            id=gift_id,
            name=config["name"],
            type=config["type"],
            category=config["category"],
            price=config["price"],
            icon=config["icon"],
            animation=config.get("animation"),
            description=config["description"],
            fullscreen=config.get("fullscreen", False),
        )


# 服务工厂函数
def get_gift_service(db: Session) -> GiftService:
    """获取礼物服务实例"""
    return GiftService(db)