"""
P15 虚实结合服务层

核心理念：全自动关系管家
包含：
1. 自主约会策划服务
2. 情感纪念册服务
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import math
import random

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from db.models import UserDB, ConversationDB, ChatMessageDB
from models.p15_models import (
    AutonomousDatePlanDB,
    DateReservationDB,
    RelationshipAlbumDB,
    SweetMomentDB,
    CoupleFootprintDB,
    GeneratedMediaDB
)
from utils.logger import logger


class AutonomousDatePlanningService:
    """自主约会策划服务"""

    def __init__(self):
        # 预定义的场所数据库
        self.venue_database = self._initialize_venue_database()

    def _initialize_venue_database(self) -> List[Dict]:
        """初始化场所数据库"""
        return [
            {"id": "v1", "name": "浪漫意大利餐厅", "category": "restaurant", "avg_cost": 300, "rating": 4.8},
            {"id": "v2", "name": "星巴克咖啡厅", "category": "cafe", "avg_cost": 50, "rating": 4.2},
            {"id": "v3", "name": "中央公园", "category": "park", "avg_cost": 0, "rating": 4.7},
            {"id": "v4", "name": "IMAX 影城", "category": "cinema", "avg_cost": 100, "rating": 4.5},
        ]

    def calculate_geographic_midpoint(
        self,
        user_a_location: tuple,
        user_b_location: tuple
    ) -> Dict[str, Any]:
        """
        计算地理中点

        参数:
        - user_a_location: (latitude, longitude)
        - user_b_location: (latitude, longitude)
        """
        lat_a, lon_a = user_a_location
        lat_b, lon_b = user_b_location

        # 简单中点计算
        mid_lat = (lat_a + lat_b) / 2
        mid_lon = (lon_a + lon_b) / 2

        # 计算距离（Haversine 公式简化版）
        distance = self._calculate_distance(user_a_location, user_b_location)

        return {
            "latitude": mid_lat,
            "longitude": mid_lon,
            "distance_km": distance,
            "estimated_travel_time": self._estimate_travel_time(distance)
        }

    def _calculate_distance(self, loc1: tuple, loc2: tuple) -> float:
        """计算两点间距离（公里）"""
        lat1, lon1 = loc1
        lat2, lon2 = loc2

        # 简化计算
        lat_diff = abs(lat2 - lat1) * 111  # 1 度纬度约 111km
        lon_diff = abs(lon2 - lon1) * 85  # 1 度经度约 85km（中纬度）

        return math.sqrt(lat_diff ** 2 + lon_diff ** 2)

    def _estimate_travel_time(self, distance_km: float) -> str:
        """估算行程时间"""
        if distance_km < 5:
            return "15-30 分钟"
        elif distance_km < 15:
            return "30-60 分钟"
        else:
            return "1 小时以上"

    def find_venues_near_midpoint(
        self,
        midpoint: Dict[str, Any],
        category: Optional[str] = None,
        budget_range: Optional[tuple] = None,
        limit: int = 5
    ) -> List[Dict]:
        """查找中点附近的场所"""
        # 简单实现：返回预定义场所
        venues = self.venue_database

        if category:
            venues = [v for v in venues if v["category"] == category]

        if budget_range:
            min_b, max_b = budget_range
            venues = [v for v in venues if min_b <= v["avg_cost"] <= max_b]

        # 按评分排序
        venues = sorted(venues, key=lambda v: v["rating"], reverse=True)

        return venues[:limit]

    def create_date_plan(
        self,
        user_a_id: str,
        user_b_id: str,
        user_a_location: tuple,
        user_b_location: tuple,
        preferences: Dict[str, Any],
        db_session=None
    ) -> AutonomousDatePlanDB:
        """
        创建约会计划

        参数:
        - user_a_id, user_b_id: 用户 ID
        - user_a_location, user_b_location: 用户位置
        - preferences: 偏好设置（类别、预算等）
        """
        # 计算地理中点
        midpoint = self.calculate_geographic_midpoint(
            user_a_location, user_b_location
        )

        # 查找场所
        venues = self.find_venues_near_midpoint(
            midpoint,
            category=preferences.get("category"),
            budget_range=preferences.get("budget_range")
        )

        if not venues:
            raise ValueError("未找到合适的场所")

        best_venue = venues[0]

        # 生成计划
        plan_id = f"plan_{user_a_id}_{user_b_id}_{datetime.utcnow().timestamp()}"
        plan = AutonomousDatePlanDB(
            id=plan_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            plan_name=f"在{best_venue['name']}的约会",
            midpoint_latitude=midpoint["latitude"],
            midpoint_longitude=midpoint["longitude"],
            midpoint_address=f"中点位置（距离双方约{midpoint['distance_km']:.1f}公里）",
            venue_id=best_venue["id"],
            venue_name=best_venue["name"],
            venue_category=best_venue["category"],
            preference_match_score=0.9,
            budget_match_score=0.8,
            estimated_budget=best_venue["avg_cost"] * 2,
            ai_recommendation_reason=self._generate_recommendation_reason(
                best_venue, midpoint
            ),
            status="draft"
        )

        if db_session:
            db_session.add(plan)
            db_session.commit()
            db_session.refresh(plan)

        return plan

    def _generate_recommendation_reason(
        self,
        venue: Dict,
        midpoint: Dict
    ) -> str:
        """生成推荐理由"""
        return (
            f"推荐{venue['name']}因为：\n"
            f"1. 位于双方位置的地理中点，交通便利\n"
            f"2. 评分{venue['rating']}分，口碑良好\n"
            f"3. 人均消费{venue['avg_cost']}元，符合预算\n"
            f"4. 距离约{midpoint['distance_km']:.1f}公里，{midpoint['estimated_travel_time']}可达"
        )

    def confirm_plan(
        self,
        plan_id: str,
        user_id: str,
        db_session
    ) -> bool:
        """用户确认计划"""
        plan = db_session.query(AutonomousDatePlanDB).filter(
            AutonomousDatePlanDB.id == plan_id
        ).first()

        if not plan:
            return False

        if plan.user_a_id == user_id:
            plan.user_a_confirmation = True
        elif plan.user_b_id == user_id:
            plan.user_b_confirmation = True

        # 双方都确认则更新状态
        if plan.user_a_confirmation and plan.user_b_confirmation:
            plan.status = "confirmed"

        db_session.commit()
        return True


class RelationshipAlbumService:
    """情感纪念册服务"""

    def create_album(
        self,
        user_a_id: str,
        user_b_id: str,
        title: str,
        album_type: str = "moment",
        db_session=None
    ) -> RelationshipAlbumDB:
        """创建纪念册"""
        album_id = f"album_{user_a_id}_{user_b_id}_{datetime.utcnow().timestamp()}"
        album = RelationshipAlbumDB(
            id=album_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            title=title,
            album_type=album_type,
            content_item_ids=[]
        )

        if db_session:
            db_session.add(album)
            db_session.commit()
            db_session.refresh(album)

        return album

    def add_moment_to_album(
        self,
        album_id: str,
        content: str,
        source_type: str,
        user_a_id: str,
        user_b_id: str,
        db_session=None
    ) -> SweetMomentDB:
        """添加甜蜜瞬间到纪念册"""
        moment_id = f"moment_{album_id}_{datetime.utcnow().timestamp()}"
        moment = SweetMomentDB(
            id=moment_id,
            album_id=album_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            source_type=source_type,
            content=content,
            sentiment_score=random.uniform(0.7, 1.0),
            moment_date=datetime.utcnow()
        )

        if db_session:
            db_session.add(moment)

            # 更新纪念册
            album = db_session.query(RelationshipAlbumDB).filter(
                RelationshipAlbumDB.id == album_id
            ).first()
            if album:
                if album.content_item_ids is None:
                    album.content_item_ids = []
                album.content_item_ids.append(moment_id)
                album.total_moments += 1
                db_session.commit()

        return moment

    def extract_sweet_moments_from_chat(
        self,
        conversation_id: str,
        user_a_id: str,
        user_b_id: str,
        db_session
    ) -> List[SweetMomentDB]:
        """从对话中提取甜蜜瞬间"""
        messages = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.conversation_id == conversation_id
        ).order_by(ChatMessageDB.created_at.desc()).limit(100).all()

        # 甜蜜关键词
        sweet_keywords = ["喜欢", "爱", "开心", "幸福", "谢谢", "感动", "温暖"]

        moments = []
        for msg in messages:
            # 检查是否包含甜蜜关键词
            if any(kw in msg.content for kw in sweet_keywords):
                moment = self.add_moment_to_album(
                    album_id=None,  # 需要单独创建
                    content=msg.content,
                    source_type="chat_message",
                    user_a_id=user_a_id,
                    user_b_id=user_b_id,
                    db_session=db_session
                )
                moments.append(moment)

        return moments

    def generate_album_summary(
        self,
        album_id: str,
        db_session
    ) -> str:
        """生成纪念册 AI 总结"""
        album = db_session.query(RelationshipAlbumDB).filter(
            RelationshipAlbumDB.id == album_id
        ).first()

        if not album:
            return ""

        # 获取所有瞬间
        moments = db_session.query(SweetMomentDB).filter(
            SweetMomentDB.album_id == album_id
        ).all()

        if not moments:
            return "暂无内容"

        # 生成简单总结
        summary = (
            f"这本纪念册记录了{len(moments)}个甜蜜瞬间。\n"
            f"从{moments[-1].moment_date.strftime('%Y-%m-%d')}到"
            f"{moments[0].moment_date.strftime('%Y-%m-%d')}，\n"
            f"你们一起度过了许多美好时光。"
        )

        album.ai_summary = summary
        db_session.commit()

        return summary


# 创建全局服务实例
autonomous_date_service = AutonomousDatePlanningService()
relationship_album_service = RelationshipAlbumService()
