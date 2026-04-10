"""
P14 约会辅助服务

包含：
1. 穿搭推荐服务 - 天气感知穿搭建议
2. 场所策略服务 - 约会场所分析和建议
3. 话题锦囊服务 - 约会话题生成
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import random

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from db.models import UserDB
from models.p14_models import (
    DateOutfitRecommendationDB,
    DateVenueStrategyDB,
    DateTopicKitDB,
    SimulationScenarioType
)
from utils.logger import logger


class OutfitRecommendationService:
    """穿搭推荐服务"""

    # 天气到穿搭的映射
    WEATHER_OUTFIT_MAP = {
        "sunny": {
            "top": ["T 恤", "POLO 衫", "短袖衬衫"],
            "bottom": ["短裤", "休闲裤", "牛仔裤"],
            "shoes": ["运动鞋", "休闲鞋", "凉鞋"],
            "accessories": ["太阳镜", "帽子"]
        },
        "cloudy": {
            "top": ["长袖衬衫", "薄卫衣", "T 恤 + 外套"],
            "bottom": ["牛仔裤", "休闲裤", "卡其裤"],
            "shoes": ["运动鞋", "休闲鞋"],
            "accessories": ["手表", "薄围巾"]
        },
        "rainy": {
            "top": ["防水外套", "长袖衬衫"],
            "bottom": ["防水裤", "牛仔裤"],
            "shoes": ["防水鞋", "雨靴"],
            "accessories": ["雨伞", "防水包"]
        },
        "cold": {
            "top": ["毛衣", "厚外套", "羽绒服"],
            "bottom": ["厚裤子", "牛仔裤"],
            "shoes": ["靴子", "保暖鞋"],
            "accessories": ["围巾", "手套", "帽子"]
        }
    }

    # 场所到正式程度的映射
    VENUE_DRESS_CODE_MAP = {
        "restaurant": {
            "fine_dining": "formal",
            "casual_dining": "smart_casual",
            "fast_food": "casual"
        },
        "cafe": "casual",
        "park": "casual",
        "cinema": "smart_casual",
        "museum": "smart_casual",
        "concert": {
            "classical": "formal",
            "pop": "casual",
            "rock": "casual"
        }
    }

    # 温度范围到穿搭建议
    TEMPERATURE_RANGES = [
        (30, "炎热", "sunny"),
        (20, "温暖", "sunny"),
        (10, "凉爽", "cloudy"),
        (0, "寒冷", "cold"),
        (-10, "极寒", "cold")
    ]

    def get_weather_condition(self, temperature: float, weather_desc: str = "") -> str:
        """根据温度获取天气状况分类"""
        for threshold, label, condition in self.TEMPERATURE_RANGES:
            if temperature >= threshold:
                return condition
        return "cold"

    def generate_outfit_recommendation(
        self,
        user_id: str,
        venue: str,
        venue_type: str,
        weather_condition: str,
        temperature: float,
        date_date: datetime,
        db_session=None
    ) -> DateOutfitRecommendationDB:
        """
        生成穿搭推荐

        参数:
        - user_id: 用户 ID
        - venue: 场所名称
        - venue_type: 场所类型
        - weather_condition: 天气状况
        - temperature: 温度
        - date_date: 约会日期
        """
        # 获取基础天气穿搭
        base_outfit = self.WEATHER_OUTFIT_MAP.get(
            weather_condition,
            self.WEATHER_OUTFIT_MAP["cloudy"]
        )

        # 获取场所正式程度
        dress_code = self._get_dress_code(venue_type)

        # 根据正式程度调整穿搭
        outfit = self._adjust_outfit_for_dress_code(base_outfit, dress_code)

        # 生成穿搭理由
        reasoning = self._generate_outfit_reasoning(
            weather_condition, temperature, venue_type, dress_code
        )

        # 生成配色方案
        color_scheme = self._generate_color_scheme(dress_code, date_date)

        # 创建推荐记录
        recommendation_id = f"outfit_{user_id}_{datetime.utcnow().timestamp()}"
        recommendation = DateOutfitRecommendationDB(
            id=recommendation_id,
            user_id=user_id,
            venue=venue,
            venue_type=venue_type,
            weather_condition=weather_condition,
            temperature=temperature,
            date_date=date_date,
            outfit_recommendation=outfit,
            outfit_reasoning=reasoning,
            dress_code=dress_code,
            color_scheme=color_scheme
        )

        if db_session:
            db_session.add(recommendation)
            db_session.commit()
            db_session.refresh(recommendation)

        return recommendation

    def _get_dress_code(self, venue_type: str) -> str:
        """获取场所的正式程度"""
        if isinstance(self.VENUE_DRESS_CODE_MAP.get(venue_type), dict):
            # 需要更具体的子类型，默认返回 smart_casual
            return "smart_casual"
        return self.VENUE_DRESS_CODE_MAP.get(venue_type, "casual")

    def _adjust_outfit_for_dress_code(
        self,
        base_outfit: Dict,
        dress_code: str
    ) -> Dict:
        """根据正式程度调整穿搭"""
        outfit = base_outfit.copy()

        if dress_code == "formal":
            outfit["top"] = ["正装衬衫", "西装外套"]
            outfit["bottom"] = ["西裤", "正装裤"]
            outfit["shoes"] = ["皮鞋"]
            outfit["accessories"].extend(["领带", "皮带"])
        elif dress_code == "smart_casual":
            outfit["top"] = ["休闲衬衫", "POLO 衫", "薄毛衣"]
            outfit["bottom"] = ["卡其裤", "休闲裤", "深色牛仔裤"]
            outfit["shoes"] = ["休闲皮鞋", "干净的运动鞋"]

        return outfit

    def _generate_outfit_reasoning(
        self,
        weather_condition: str,
        temperature: float,
        venue_type: str,
        dress_code: str
    ) -> str:
        """生成穿搭理由"""
        reasons = []

        # 天气因素
        if weather_condition == "rainy":
            reasons.append("今天可能下雨，建议携带雨具和防水装备")
        elif weather_condition == "cold":
            reasons.append(f"气温较低 ({temperature}°C)，注意保暖")
        elif weather_condition == "sunny":
            reasons.append("天气晴朗，可以选择清爽透气的服装")

        # 场所因素
        if dress_code == "formal":
            reasons.append(f"{venue_type} 是正式场合，建议正装出席")
        elif dress_code == "smart_casual":
            reasons.append(f"{venue_type} 适合商务休闲风格")
        else:
            reasons.append(f"{venue_type} 可以穿着休闲舒适")

        return "。".join(reasons) + "。"

    def _generate_color_scheme(
        self,
        dress_code: str,
        date_date: datetime
    ) -> Dict:
        """生成配色方案"""
        # 根据季节调整
        month = date_date.month
        if month in [3, 4, 5]:  # 春季
            base_colors = ["浅蓝", "米白", "淡粉"]
        elif month in [6, 7, 8]:  # 夏季
            base_colors = ["白色", "天蓝", "浅灰"]
        elif month in [9, 10, 11]:  # 秋季
            base_colors = ["卡其", "深蓝", "棕色"]
        else:  # 冬季
            base_colors = ["黑色", "深灰", "藏蓝"]

        if dress_code == "formal":
            base_colors = ["黑色", "深蓝", "白色"]

        return {
            "primary": random.choice(base_colors),
            "secondary": random.choice(base_colors),
            "accent": random.choice(["红色", "黄色", "绿色"])
        }

    def get_recommendation(
        self,
        recommendation_id: str,
        db_session
    ) -> Optional[DateOutfitRecommendationDB]:
        """获取穿搭推荐记录"""
        return db_session.query(DateOutfitRecommendationDB).filter(
            DateOutfitRecommendationDB.id == recommendation_id
        ).first()

    def get_user_recommendations(
        self,
        user_id: str,
        db_session,
        limit: int = 10
    ) -> List[DateOutfitRecommendationDB]:
        """获取用户的穿搭推荐历史"""
        return db_session.query(DateOutfitRecommendationDB).filter(
            DateOutfitRecommendationDB.user_id == user_id
        ).order_by(DateOutfitRecommendationDB.created_at.desc()).limit(limit).all()


class VenueStrategyService:
    """场所策略服务"""

    # 预定义的场所策略库
    DEFAULT_VENUE_STRATEGIES = {
        "浪漫西餐厅": {
            "venue_type": "restaurant",
            "features": ["浪漫", "安静", "适合聊天"],
            "best_time_slots": ["19:00-21:00"],
            "recommended_activities": ["共进晚餐", "餐后散步"],
            "conversation_topics": ["美食体验", "旅行经历", "未来规划"],
            "tips": ["提前预订窗边位置", "注意用餐礼仪"],
            "suitable_stages": ["first_date", "anniversary"],
            "average_cost": 300.0,
            "reservation_info": {"required": True, "advance_days": 2}
        },
        "休闲咖啡厅": {
            "venue_type": "cafe",
            "features": ["轻松", "舒适", "适合深度交流"],
            "best_time_slots": ["14:00-17:00", "19:00-21:00"],
            "recommended_activities": ["喝咖啡", "玩桌游", "看书"],
            "conversation_topics": ["兴趣爱好", "工作经历", "生活趣事"],
            "tips": ["选择安静角落", "不要点太吵的音乐"],
            "suitable_stages": ["first_meet", "casual"],
            "average_cost": 80.0,
            "reservation_info": {"required": False}
        },
        "城市公园": {
            "venue_type": "park",
            "features": ["自然", "开放", "适合活动"],
            "best_time_slots": ["10:00-12:00", "15:00-17:00"],
            "recommended_activities": ["散步", "野餐", "放风筝"],
            "conversation_topics": ["户外活动", "健康生活", "童年回忆"],
            "tips": ["注意防晒", "带些零食和水"],
            "suitable_stages": ["casual", "active_date"],
            "average_cost": 50.0,
            "reservation_info": {"required": False}
        },
        "电影院": {
            "venue_type": "cinema",
            "features": ["娱乐", "共享体验"],
            "best_time_slots": ["14:00-16:00", "19:00-21:00"],
            "recommended_activities": ["看电影", "讨论剧情", "吃爆米花"],
            "conversation_topics": ["电影剧情", "演员表现", "类似电影推荐"],
            "tips": ["提前选座", "电影后安排讨论时间"],
            "suitable_stages": ["casual", "entertainment_date"],
            "average_cost": 150.0,
            "reservation_info": {"required": True, "advance_days": 1}
        }
    }

    def __init__(self):
        self._initialized = False

    def _ensure_initialized(self, db_session):
        """初始化默认场所策略"""
        if self._initialized:
            return

        for venue_name, strategy_data in self.DEFAULT_VENUE_STRATEGIES.items():
            existing = db_session.query(DateVenueStrategyDB).filter(
                DateVenueStrategyDB.venue_name == venue_name
            ).first()
            if not existing:
                strategy = DateVenueStrategyDB(
                    id=f"venue_{venue_name}_{datetime.utcnow().timestamp()}",
                    venue_name=venue_name,
                    **strategy_data
                )
                db_session.add(strategy)

        db_session.commit()
        self._initialized = True

    def get_venue_strategy(
        self,
        venue_name: str,
        db_session
    ) -> Optional[DateVenueStrategyDB]:
        """获取场所策略"""
        self._ensure_initialized(db_session)

        strategy = db_session.query(DateVenueStrategyDB).filter(
            DateVenueStrategyDB.venue_name == venue_name
        ).first()

        return strategy

    def search_venue_strategies(
        self,
        venue_type: Optional[str] = None,
        relationship_stage: Optional[str] = None,
        db_session=None
    ) -> List[DateVenueStrategyDB]:
        """搜索场所策略"""
        self._ensure_initialized(db_session)

        query = db_session.query(DateVenueStrategyDB)

        if venue_type:
            query = query.filter(DateVenueStrategyDB.venue_type == venue_type)

        strategies = query.all()

        # 过滤关系阶段
        if relationship_stage and strategies:
            filtered = []
            for s in strategies:
                if s.suitable_relationship_stages is None or \
                   relationship_stage in s.suitable_relationship_stages:
                    filtered.append(s)
            return filtered

        return strategies

    def create_venue_strategy(
        self,
        venue_name: str,
        venue_type: str,
        venue_features: List[str],
        conversation_topics: List[str],
        db_session=None
    ) -> DateVenueStrategyDB:
        """创建新的场所策略"""
        strategy_id = f"venue_{venue_name}_{datetime.utcnow().timestamp()}"
        strategy = DateVenueStrategyDB(
            id=strategy_id,
            venue_name=venue_name,
            venue_type=venue_type,
            venue_features=venue_features,
            conversation_topics=conversation_topics,
            best_time_slots=["19:00-21:00"],
            recommended_activities=[venue_type],
            suitable_relationship_stages=["casual"],
            average_cost=100.0,
            reservation_info={"required": False}
        )

        if db_session:
            db_session.add(strategy)
            db_session.commit()
            db_session.refresh(strategy)

        return strategy

    def get_venue_recommendations(
        self,
        relationship_stage: str,
        budget_range: Optional[tuple] = None,
        db_session=None
    ) -> List[Dict[str, Any]]:
        """根据关系阶段推荐场所"""
        self._ensure_initialized(db_session)

        strategies = self.search_venue_strategies(
            relationship_stage=relationship_stage,
            db_session=db_session
        )

        # 按成功率排序
        sorted_strategies = sorted(
            strategies,
            key=lambda s: s.success_rate,
            reverse=True
        )

        # 应用预算过滤
        if budget_range:
            min_budget, max_budget = budget_range
            sorted_strategies = [
                s for s in sorted_strategies
                if s.average_cost is None or min_budget <= s.average_cost <= max_budget
            ]

        return [
            {
                "venue_name": s.venue_name,
                "venue_type": s.venue_type,
                "features": s.venue_features,
                "average_cost": s.average_cost,
                "success_rate": s.success_rate,
                "tips": s.tips_and_warnings
            }
            for s in sorted_strategies
        ]


class TopicKitService:
    """话题锦囊服务"""

    # 默认话题库
    DEFAULT_TOPICS = {
        "opening": [
            "今天过得怎么样？",
            "这里环境还不错吧？你之前来过吗？",
            "最近有什么好看的电影/书推荐吗？",
            "周末一般都喜欢做什么？"
        ],
        "deep": [
            "你理想中的生活是什么样子的？",
            "有什么事情是你一直坚持在做的事情？",
            "如果能回到过去，你最想改变什么？",
            "你觉得最重要的是什么？家庭、事业还是其他？"
        ],
        "emergency": [
            "最近有什么新鲜事吗？",
            "你喜欢什么类型的音乐/电影？",
            "有去过哪些好玩的地方吗？",
            "最近有什么好吃的餐厅推荐吗？"
        ],
        "fun": [
            "如果你有超能力，你希望是什么？",
            "如果能和任何人共进晚餐，你会选择谁？",
            "你最奇怪的爱好是什么？",
            "做过最疯狂的事情是什么？"
        ]
    }

    def generate_topic_kit(
        self,
        user_id: str,
        common_interests: Optional[List[str]] = None,
        shared_experiences: Optional[List[Dict]] = None,
        db_session=None
    ) -> DateTopicKitDB:
        """
        生成话题锦囊

        参数:
        - user_id: 用户 ID
        - common_interests: 共同兴趣列表
        - shared_experiences: 共同经历列表
        """
        # 基于默认话题
        opening_topics = self.DEFAULT_TOPICS["opening"].copy()
        deep_topics = self.DEFAULT_TOPICS["deep"].copy()
        emergency_topics = self.DEFAULT_TOPICS["emergency"].copy()
        fun_topics = self.DEFAULT_TOPICS["fun"].copy()

        # 根据共同兴趣添加话题
        if common_interests:
            for interest in common_interests[:3]:  # 最多取 3 个
                opening_topics.append(f"你最喜欢{interest}的什么？")
                deep_topics.append(f"{interest}对你来说意味着什么？")

        # 根据共同经历添加话题
        if shared_experiences:
            for exp in shared_experiences[:2]:  # 最多取 2 个
                desc = exp.get("description", "这段经历")
                emergency_topics.append(f"还记得{desc}吗？那真的很有趣")

        # 创建话题锦囊
        kit_id = f"topic_kit_{user_id}_{datetime.utcnow().timestamp()}"
        kit = DateTopicKitDB(
            id=kit_id,
            user_id=user_id,
            kit_type="comprehensive",
            opening_topics=opening_topics,
            deep_topics=deep_topics,
            emergency_topics=emergency_topics,
            fun_topics=fun_topics,
            based_on_common_interests=common_interests or [],
            based_on_shared_experiences=shared_experiences or []
        )

        if db_session:
            db_session.add(kit)
            db_session.commit()
            db_session.refresh(kit)

        return kit

    def get_topic_kit(
        self,
        kit_id: str,
        db_session
    ) -> Optional[DateTopicKitDB]:
        """获取话题锦囊"""
        return db_session.query(DateTopicKitDB).filter(
            DateTopicKitDB.id == kit_id
        ).first()

    def get_user_topic_kits(
        self,
        user_id: str,
        db_session,
        limit: int = 10
    ) -> List[DateTopicKitDB]:
        """获取用户的话题锦囊历史"""
        return db_session.query(DateTopicKitDB).filter(
            DateTopicKitDB.user_id == user_id
        ).order_by(DateTopicKitDB.created_at.desc()).limit(limit).all()

    def get_topic_by_type(
        self,
        topic_type: str,
        count: int = 5
    ) -> List[str]:
        """根据类型获取话题"""
        topics = self.DEFAULT_TOPICS.get(topic_type, [])
        return random.sample(topics, min(count, len(topics)))


# 创建全局服务实例
outfit_recommendation_service = OutfitRecommendationService()
venue_strategy_service = VenueStrategyService()
topic_kit_service = TopicKitService()
