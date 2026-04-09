"""
P10-002: 约会建议引擎服务

基于用户兴趣、位置和关系阶段，智能推荐约会地点和活动。
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import uuid
import math

from db.database import SessionLocal
from db.models import UserDB, MatchHistoryDB
from models.p10_models import DateSuggestionDB, DateVenueDB
from utils.logger import logger


# 约会类型定义
DATE_TYPES = {
    "coffee": {"label": "咖啡约会", "duration": 60, "price_range": (30, 100), "suitable_stages": ["chatting", "exchanged_contact"]},
    "meal": {"label": "用餐约会", "duration": 90, "price_range": (100, 500), "suitable_stages": ["exchanged_contact", "first_date"]},
    "movie": {"label": "电影约会", "duration": 120, "price_range": (80, 200), "suitable_stages": ["first_date", "dating"]},
    "outdoor": {"label": "户外活动", "duration": 180, "price_range": (0, 300), "suitable_stages": ["chatting", "first_date", "dating"]},
    "culture": {"label": "文化艺术", "duration": 120, "price_range": (50, 300), "suitable_stages": ["chatting", "dating"]},
    "sports": {"label": "运动健身", "duration": 90, "price_range": (0, 200), "suitable_stages": ["chatting", "dating"]},
    "entertainment": {"label": "娱乐活动", "duration": 120, "price_range": (100, 500), "suitable_stages": ["first_date", "dating"]},
    "creative": {"label": "创意体验", "duration": 150, "price_range": (100, 400), "suitable_stages": ["first_date", "dating"]},
}


class DateSuggestionService:
    """约会建议服务"""

    def __init__(self):
        pass

    def generate_date_suggestion(
        self,
        user_id: str,
        target_user_id: Optional[str] = None,
        date_type: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
        db_session: Optional[Any] = None
    ) -> str:
        """
        生成约会建议

        Args:
            user_id: 用户 ID
            target_user_id: 约会对象 ID（可选）
            date_type: 约会类型
            preferences: 偏好设置
            db_session: 可选的数据库会话（用于测试）

        Returns:
            建议 ID
        """
        db = db_session if db_session else SessionLocal()
        should_close = db_session is None
        try:
            # 获取用户信息
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")

            # 获取约会对象信息（如果有）
            target_user = None
            match_record = None
            if target_user_id:
                target_user = db.query(UserDB).filter(UserDB.id == target_user_id).first()
                # 获取匹配记录
                match_record = db.query(MatchHistoryDB).filter(
                    ((MatchHistoryDB.user_id_1 == user_id) & (MatchHistoryDB.user_id_2 == target_user_id)) |
                    ((MatchHistoryDB.user_id_1 == target_user_id) & (MatchHistoryDB.user_id_2 == user_id))
                ).first()

            # 确定关系阶段
            relationship_stage = match_record.relationship_stage if match_record else "chatting"

            # 推荐合适的约会类型
            if not date_type:
                date_type = self._suggest_date_type(relationship_stage, user, target_user)

            # 查找合适的地点
            venue = self._find_suitable_venue(db, user, target_user, date_type, preferences)

            if not venue:
                # 如果没有找到合适的地点，生成一个通用建议
                venue = self._generate_generic_venue(user, date_type)

            # 计算匹配置信度
            match_score = self._calculate_match_score(user, target_user, venue, date_type)

            # 生成推荐理由
            recommendation_reason = self._generate_recommendation_reason(
                user, target_user, venue, date_type, relationship_stage
            )

            # 创建约会建议
            suggestion_id = str(uuid.uuid4())
            estimated_cost = DATE_TYPES.get(date_type, {}).get("price_range", (100, 200))
            estimated_duration = DATE_TYPES.get(date_type, {}).get("duration", 60)

            suggestion = DateSuggestionDB(
                id=suggestion_id,
                user_id=user_id,
                target_user_id=target_user_id,
                date_type=date_type,
                venue_name=venue["name"],
                venue_type=venue.get("type", date_type),
                address=venue.get("address", ""),
                latitude=venue.get("latitude"),
                longitude=venue.get("longitude"),
                recommendation_reason=recommendation_reason,
                estimated_cost=estimated_cost[1],  # 使用较高估值
                estimated_duration=estimated_duration,
                best_time_suggestion=self._suggest_best_time(date_type),
                compatibility_analysis=json.dumps({
                    "interests_match": self._get_interests_match(user, target_user),
                    "stage_appropriate": date_type in [t for t, info in DATE_TYPES.items() if relationship_stage in info.get("suitable_stages", [])]
                }),
                match_score=match_score,
                status="pending"
            )
            db.add(suggestion)
            db.commit()
            db.refresh(suggestion)

            logger.info(f"Generated date suggestion: {suggestion_id} for {user_id}")
            return suggestion_id

        except Exception as e:
            db.rollback()
            logger.error(f"Error generating date suggestion: {e}")
            raise
        finally:
            if should_close:
                db.close()

    def _suggest_date_type(
        self,
        relationship_stage: str,
        user: UserDB,
        target_user: Optional[UserDB]
    ) -> str:
        """根据关系阶段推荐约会类型"""
        # 根据关系阶段推荐
        if relationship_stage in ["chatting", "exchanged_contact"]:
            # 早期阶段：轻松、低压力的约会
            if target_user:
                common_interests = self._get_common_interests(user, target_user)
                if "咖啡" in common_interests or "聊天" in common_interests:
                    return "coffee"
                if "美食" in common_interests:
                    return "meal"
            return "coffee"  # 默认咖啡约会

        elif relationship_stage in ["first_date", "dating"]:
            # 已有约会经验：可以尝试更有深度的活动
            return "meal"  # 默认用餐约会

        return "coffee"

    def _find_suitable_venue(
        self,
        db,
        user: UserDB,
        target_user: Optional[UserDB],
        date_type: str,
        preferences: Optional[Dict[str, Any]]
    ) -> Optional[Dict]:
        """查找合适的约会地点"""
        # 优先从数据库中查找
        # 提取城市名
        city = user.location.split(" ")[0] if " " in user.location else user.location

        query = db.query(DateVenueDB).filter(
            DateVenueDB.city == city,
            DateVenueDB.venue_type == date_type,
            DateVenueDB.is_popular == True
        ).order_by(DateVenueDB.rating.desc()).limit(5).all()

        if query:
            venue = query[0]
            return {
                "name": venue.venue_name,
                "type": venue.venue_type,
                "address": venue.address,
                "latitude": venue.latitude,
                "longitude": venue.longitude,
                "rating": venue.rating,
                "price_level": venue.price_level
            }

        return None

    def _generate_generic_venue(self, user: UserDB, date_type: str) -> Dict:
        """生成通用约会地点"""
        location = user.location if user.location else "城市中心"

        venue_templates = {
            "coffee": {"name": f"{location}特色咖啡馆", "type": "咖啡", "address": f"{location}市中心"},
            "meal": {"name": f"{location}精品餐厅", "type": "餐饮", "address": f"{location}美食街"},
            "movie": {"name": f"{location}IMAX 影城", "type": "电影", "address": f"{location}商业中心"},
            "outdoor": {"name": f"{location}中央公园", "type": "户外", "address": f"{location}市中心"},
            "culture": {"name": f"{location}艺术博物馆", "type": "文化", "address": f"{location}文化区"},
            "sports": {"name": f"{location}运动中心", "type": "运动", "address": f"{location}体育区"},
            "entertainment": {"name": f"{location}游乐场", "type": "娱乐", "address": f"{location}娱乐区"},
            "creative": {"name": f"{location}创意工坊", "type": "创意", "address": f"{location}艺术区"},
        }

        template = venue_templates.get(date_type, venue_templates["coffee"])
        return {
            "name": template["name"],
            "type": template["type"],
            "address": template["address"],
            "latitude": None,
            "longitude": None
        }

    def _calculate_match_score(
        self,
        user: UserDB,
        target_user: Optional[UserDB],
        venue: Dict,
        date_type: str
    ) -> float:
        """计算匹配置信度"""
        score = 0.5  # 基础分

        # 兴趣匹配加成
        if target_user:
            common_interests = self._get_common_interests(user, target_user)
            if common_interests:
                score += min(len(common_interests) * 0.1, 0.3)

        # 地点评分加成
        if venue.get("rating", 0) >= 4.5:
            score += 0.1
        elif venue.get("rating", 0) >= 4.0:
            score += 0.05

        return min(score, 1.0)

    def _generate_recommendation_reason(
        self,
        user: UserDB,
        target_user: Optional[UserDB],
        venue: Dict,
        date_type: str,
        relationship_stage: str
    ) -> str:
        """生成推荐理由"""
        reasons = []

        # 基于关系阶段
        stage_reasons = {
            "chatting": "这是一个轻松的初次见面选择，可以让你们在舒适的环境中相互了解",
            "exchanged_contact": "交换联系方式后，一次面对面的约会能让你们的关系更进一步",
            "first_date": "为你们的第一次正式约会精心挑选的场所",
            "dating": "为你们的感情增添新的体验"
        }
        reasons.append(stage_reasons.get(relationship_stage, ""))

        # 基于兴趣匹配
        if target_user:
            common_interests = self._get_common_interests(user, target_user)
            if common_interests:
                reasons.append(f"你们有{len(common_interests)}个共同兴趣")

        # 基于地点特色
        if venue.get("rating", 0) >= 4.5:
            reasons.append("高分热门地点，值得一试")

        return "。".join([r for r in reasons if r])

    def _suggest_best_time(self, date_type: str) -> str:
        """建议最佳时间"""
        time_suggestions = {
            "coffee": "下午 2-4 点，阳光正好",
            "meal": "晚上 6-8 点，享受晚餐时光",
            "movie": "下午或晚上，根据排片选择",
            "outdoor": "上午 9-11 点或下午 3-5 点，避开正午",
            "culture": "下午 2-5 点，有充足时间欣赏",
            "sports": "早上或傍晚，天气凉爽",
            "entertainment": "晚上 7 点后，夜生活开始",
            "creative": "下午 2-5 点，创意最活跃的时间"
        }
        return time_suggestions.get(date_type, "根据双方时间安排")

    def _get_common_interests(self, user1: UserDB, user2: UserDB) -> List[str]:
        """获取共同兴趣"""
        interests1 = set(json.loads(user1.interests) if user1.interests else [])
        interests2 = set(json.loads(user2.interests) if user2.interests else [])
        return list(interests1 & interests2)

    def _get_interests_match(self, user1: UserDB, user2: Optional[UserDB]) -> Dict:
        """获取兴趣匹配详情"""
        if not user2:
            return {"common": [], "match_rate": 0}

        interests1 = set(json.loads(user1.interests) if user1.interests else [])
        interests2 = set(json.loads(user2.interests) if user2.interests else [])
        common = list(interests1 & interests2)

        union = interests1 | interests2
        match_rate = len(common) / len(union) if union else 0

        return {
            "common": common,
            "match_rate": round(match_rate, 2),
            "user1_unique": list(interests1 - interests2)[:5],
            "user2_unique": list(interests2 - interests1)[:5]
        }

    def get_user_date_suggestions(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 10,
        db_session: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """获取用户的约会建议列表"""
        db = db_session if db_session else SessionLocal()
        should_close = db_session is None
        try:
            query = db.query(DateSuggestionDB).filter(
                DateSuggestionDB.user_id == user_id
            )

            if status:
                query = query.filter(DateSuggestionDB.status == status)

            suggestions = query.order_by(
                DateSuggestionDB.created_at.desc()
            ).limit(limit).all()

            result = []
            for s in suggestions:
                result.append({
                    "id": s.id,
                    "user_id": s.user_id,
                    "target_user_id": s.target_user_id,
                    "date_type": s.date_type,
                    "date_type_label": DATE_TYPES.get(s.date_type, {}).get("label", s.date_type),
                    "venue_name": s.venue_name,
                    "venue_type": s.venue_type,
                    "address": s.address,
                    "recommendation_reason": s.recommendation_reason,
                    "estimated_cost": s.estimated_cost,
                    "estimated_duration": s.estimated_duration,
                    "best_time_suggestion": s.best_time_suggestion,
                    "match_score": s.match_score,
                    "status": s.status,
                    "suggested_at": s.suggested_at.isoformat() if s.suggested_at else None,
                    "responded_at": s.responded_at.isoformat() if s.responded_at else None,
                    "user_rating": s.user_rating,
                    "user_feedback": s.user_feedback
                })
            return result

        finally:
            if should_close:
                db.close()

    def respond_to_date_suggestion(
        self,
        suggestion_id: str,
        action: str,
        feedback: Optional[str] = None,
        counter_suggestion: Optional[str] = None,
        db_session: Optional[Any] = None
    ) -> bool:
        """响应用户对约会建议的回应"""
        db = db_session if db_session else SessionLocal()
        should_close = db_session is None
        try:
            suggestion = db.query(DateSuggestionDB).filter(
                DateSuggestionDB.id == suggestion_id
            ).first()

            if not suggestion:
                return False

            # 更新状态
            if action == "accept":
                suggestion.status = "accepted"
            elif action == "reject":
                suggestion.status = "rejected"
            elif action == "counter":
                suggestion.status = "countered"
                # 可以创建反向建议
            else:
                suggestion.status = action

            suggestion.responded_at = datetime.now()
            if feedback:
                suggestion.user_feedback = feedback

            db.commit()
            logger.info(f"Date suggestion {suggestion_id} responded with action: {action}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error responding to date suggestion: {e}")
            return False
        finally:
            if should_close:
                db.close()

    def get_date_venues(
        self,
        city: str,
        venue_type: Optional[str] = None,
        price_level: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取约会地点推荐"""
        db = SessionLocal()
        try:
            query = db.query(DateVenueDB).filter(
                DateVenueDB.city == city,
                DateVenueDB.is_active == True if hasattr(DateVenueDB, 'is_active') else True
            )

            if venue_type:
                query = query.filter(DateVenueDB.venue_type == venue_type)

            if price_level:
                query = query.filter(DateVenueDB.price_level == price_level)

            venues = query.order_by(
                DateVenueDB.rating.desc(),
                DateVenueDB.is_popular.desc()
            ).limit(limit).all()

            result = []
            for v in venues:
                result.append({
                    "id": v.id,
                    "venue_name": v.venue_name,
                    "venue_type": v.venue_type,
                    "category": v.category,
                    "address": v.address,
                    "city": v.city,
                    "district": v.district,
                    "latitude": v.latitude,
                    "longitude": v.longitude,
                    "rating": v.rating,
                    "review_count": v.review_count,
                    "price_level": v.price_level,
                    "tags": json.loads(v.tags) if v.tags else [],
                    "suitable_for": json.loads(v.suitable_for) if v.suitable_for else [],
                    "is_popular": v.is_popular
                })
            return result

        except Exception as e:
            logger.error(f"Error getting date venues: {e}")
            raise
        finally:
            db.close()

    def add_date_venue(
        self,
        venue_name: str,
        venue_type: str,
        address: str,
        city: str,
        latitude: float,
        longitude: float,
        category: Optional[str] = None,
        district: Optional[str] = None,
        rating: float = 0.0,
        price_level: int = 2,
        tags: Optional[List[str]] = None,
        suitable_for: Optional[List[str]] = None,
        source: str = "manual"
    ) -> str:
        """添加约会地点"""
        db = SessionLocal()
        try:
            venue_id = str(uuid.uuid4())
            venue = DateVenueDB(
                id=venue_id,
                venue_name=venue_name,
                venue_type=venue_type,
                category=category or venue_type,
                address=address,
                city=city,
                district=district,
                latitude=latitude,
                longitude=longitude,
                rating=rating,
                price_level=price_level,
                tags=json.dumps(tags) if tags else "",
                suitable_for=json.dumps(suitable_for) if suitable_for else "",
                source=source
            )
            db.add(venue)
            db.commit()
            db.refresh(venue)

            logger.info(f"Added date venue: {venue_id} - {venue_name}")
            return venue_id

        except Exception as e:
            db.rollback()
            logger.error(f"Error adding date venue: {e}")
            raise
        finally:
            db.close()


# 全局服务实例
date_suggestion_service = DateSuggestionService()
