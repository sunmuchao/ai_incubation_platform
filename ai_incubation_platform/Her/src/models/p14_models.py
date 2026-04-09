"""
P14 实战演习数据库模型

核心理念：约会教练与保镖
消除见面焦虑，确保每一次见面得体，专业分工协作。

包含以下模块：
1. 约会模拟沙盒 - AI 分身创建、场景模拟、实时反馈
2. 全能约会辅助 - 天气感知穿搭、场所策略、话题锦囊
3. 多代理协作 - 红娘 Agent、教练 Agent、保安 Agent
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum
from sqlalchemy.orm import relationship
import enum

from db.database import Base


# ==================== 约会模拟沙盒模块 ====================

class SimulationScenarioType(str, enum.Enum):
    """约会场景类型"""
    RESTAURANT = "restaurant"  # 餐厅
    CAFE = "cafe"  # 咖啡厅
    PARK = "park"  # 公园
    CINEMA = "cinema"  # 电影院
    MUSEUM = "museum"  # 博物馆
    CONCERT = "concert"  # 音乐会
    SPORTS = "sports"  # 运动活动
    HOME_COOKING = "home_cooking"  # 在家做饭


class AvatarPersonalityType(str, enum.Enum):
    """AI 分身性格类型"""
    OUTGOING = "outgoing"  # 外向
    INTROVERTED = "introverted"  # 内向
    HUMOROUS = "humorous"  # 幽默
    SERIOUS = "serious"  # 严肃
    GENTLE = "gentle"  # 温柔
    INDEPENDENT = "independent"  # 独立


class AIDateAvatarDB(Base):
    """AI 约会分身"""
    __tablename__ = "ai_date_avatars"

    id = Column(String, primary_key=True)

    # 用户 ID（分身所属用户）
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 分身名称
    avatar_name = Column(String, nullable=False)

    # 分身性格
    personality = Column(String, default=AvatarPersonalityType.OUTGOING.value)

    # 外貌描述
    appearance_description = Column(Text)

    # 性格特征
    personality_traits = Column(JSON)  # ["健谈", "害羞", "幽默"]

    # 兴趣爱好
    interests = Column(JSON)  # ["旅行", "美食", "电影"]

    # 对话风格
    conversation_style = Column(String)  # casual, formal, playful

    # 禁忌话题
    off_limit_topics = Column(JSON)  # ["政治", "前任"]

    # 约会偏好
    date_preferences = Column(JSON)  # 喜欢的约会类型

    # 基于的用户照片 ID（可选）
    based_on_photo_ids = Column(JSON)

    # 激活状态
    is_active = Column(Boolean, default=True)

    # 使用次数
    usage_count = Column(Integer, default=0)

    # 平均评分
    avg_rating = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DateSimulationDB(Base):
    """约会模拟记录"""
    __tablename__ = "date_simulations"

    id = Column(String, primary_key=True)

    # 用户 ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # AI 分身 ID
    avatar_id = Column(String, ForeignKey("ai_date_avatars.id"), nullable=False)

    # 约会场景
    scenario = Column(String, nullable=False)

    # 场景描述
    scenario_description = Column(Text)

    # 模拟目标
    simulation_goal = Column(String)  # "练习开场白", "学习倾听"

    # 对话历史
    conversation_history = Column(JSON)  # [{role, content, timestamp}]

    # 模拟时长（秒）
    duration_seconds = Column(Integer, default=0)

    # 消息数量
    message_count = Column(Integer, default=0)

    # 模拟状态
    status = Column(String, default="completed")  # ongoing, completed, abandoned

    # 用户自评
    self_rating = Column(Integer)  # 1-10

    # 完成状态
    is_completed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class SimulationFeedbackDB(Base):
    """模拟反馈评估"""
    __tablename__ = "simulation_feedbacks"

    id = Column(String, primary_key=True)

    # 关联的模拟 ID
    simulation_id = Column(String, ForeignKey("date_simulations.id"), nullable=False)

    # 总体评分
    overall_score = Column(Integer, nullable=False)  # 1-10

    # 各维度评分
    conversation_score = Column(Integer)  # 对话流畅度
    empathy_score = Column(Integer)  # 共情能力
    humor_score = Column(Integer)  # 幽默感
    confidence_score = Column(Integer)  # 自信心
    listening_score = Column(Integer)  # 倾听能力

    # AI 评语
    ai_comments = Column(Text)

    # 亮点
    highlights = Column(JSON)  # ["开场白自然", "善于提问"]

    # 改进建议
    improvement_suggestions = Column(JSON)  # ["多倾听对方", "避免打断"]

    # 推荐练习
    recommended_practices = Column(JSON)  # ["练习开放式问题", "学习积极回应"]

    # 关键对话片段
    key_moments = Column(JSON)  # 重要对话片段及分析

    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 全能约会辅助模块 ====================

class DateOutfitRecommendationDB(Base):
    """约会穿搭推荐记录"""
    __tablename__ = "date_outfit_recommendations"

    id = Column(String, primary_key=True)

    # 用户 ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 约会 ID（可选）
    date_id = Column(String)  # 关联约会记录

    # 约会日期
    date_date = Column(DateTime, nullable=False)

    # 约会场所
    venue = Column(String)

    # 场所类型
    venue_type = Column(String)  # restaurant, cafe, outdoor

    # 天气状况
    weather_condition = Column(String)  # sunny, rainy, cloudy

    # 温度（摄氏度）
    temperature = Column(Float)

    # 推荐的穿搭
    outfit_recommendation = Column(JSON, nullable=False)
    # {
    #     "top": "白色休闲衬衫",
    #     "bottom": "深蓝色牛仔裤",
    #     "shoes": "棕色皮鞋",
    #     "accessories": ["简约手表", "皮带"]
    # }

    # 穿搭理由
    outfit_reasoning = Column(Text)

    # 正式程度
    dress_code = Column(String)  # casual, smart_casual, formal

    # 配色方案
    color_scheme = Column(JSON)

    # 用户反馈
    user_feedback = Column(String)  # adopted, modified, rejected
    user_satisfaction = Column(Integer)  # 1-5

    created_at = Column(DateTime, default=datetime.utcnow)


class DateVenueStrategyDB(Base):
    """约会场所策略记录"""
    __tablename__ = "date_venue_strategies"

    id = Column(String, primary_key=True)

    # 场所名称
    venue_name = Column(String, nullable=False)

    # 场所类型
    venue_type = Column(String, nullable=False)

    # 场所地址
    venue_address = Column(String)

    # 场所特点
    venue_features = Column(JSON)  # ["安静", "浪漫", "适合聊天"]

    # 最佳时间段
    best_time_slots = Column(JSON)  # ["19:00-21:00"]

    # 推荐活动
    recommended_activities = Column(JSON)  # ["共进晚餐", "散步"]

    # 谈话话题建议
    conversation_topics = Column(JSON)

    # 注意事项
    tips_and_warnings = Column(JSON)  # ["需要提前预订", "禁止拍照"]

    # 适合的关系阶段
    suitable_relationship_stages = Column(JSON)  # ["first_date", "casual"]

    # 平均消费
    average_cost = Column(Float)

    # 预订信息
    reservation_info = Column(JSON)  # {"required": true, "phone": "..."}

    # 使用次数
    usage_count = Column(Integer, default=0)

    # 成功率（约会后继续发展的比例）
    success_rate = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DateTopicKitDB(Base):
    """约会话题锦囊记录"""
    __tablename__ = "date_topic_kits"

    id = Column(String, primary_key=True)

    # 用户 ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 约会 ID（可选）
    date_id = Column(String)

    # 锦囊类型
    kit_type = Column(String, nullable=False)  # opening, emergency, deep, fun

    # 开场话题
    opening_topics = Column(JSON)  # 用于开场的轻松话题

    # 深入话题
    deep_topics = Column(JSON)  # 用于深入了解的话题

    # 应急话题
    emergency_topics = Column(JSON)  # 冷场时使用

    # 趣味话题
    fun_topics = Column(JSON)  # 活跃气氛

    # 基于的共同兴趣
    based_on_common_interests = Column(JSON)

    # 基于的共同经历
    based_on_shared_experiences = Column(JSON)

    # 用户反馈
    used_topics = Column(JSON)  # 实际使用的话题
    effective_topics = Column(JSON)  # 效果好的话题

    # 约会后评分
    post_date_rating = Column(Integer)  # 1-5

    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 多代理协作模块 ====================

class AgentType(str, enum.Enum):
    """Agent 类型"""
    MATCHMAKER = "matchmaker"  # 红娘 Agent
    COACH = "coach"  # 教练 Agent
    GUARDIAN = "guardian"  # 保安 Agent


class AgentCollaborationRecordDB(Base):
    """Agent 协作记录"""
    __tablename__ = "agent_collaboration_records"

    id = Column(String, primary_key=True)

    # 用户 ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 主导 Agent 类型
    lead_agent = Column(String, nullable=False)

    # 参与 Agent 类型
    participating_agents = Column(JSON)  # ["matchmaker", "coach"]

    # 协作场景
    collaboration_scenario = Column(String, nullable=False)
    # "pre_date_prep", "during_date_safety", "post_date_analysis"

    # 各 Agent 的贡献
    agent_contributions = Column(JSON)
    # {
    #     "matchmaker": "提供了匹配背景信息",
    #     "coach": "给出了约会建议",
    #     "guardian": "进行了安全评估"
    # }

    # 协作输出
    collaboration_output = Column(Text)

    # 用户反馈
    user_satisfaction = Column(Integer)  # 1-5

    # 协作效果评估
    effectiveness_score = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)


class MatchmakerAgentSessionDB(Base):
    """红娘 Agent 会话记录"""
    __tablename__ = "matchmaker_agent_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 会话类型
    session_type = Column(String)  # match_analysis, date_planning, relationship_advice

    # 会话内容
    session_content = Column(JSON)

    # 会话输出
    session_output = Column(JSON)

    # 建议的行动
    recommended_actions = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


class CoachAgentSessionDB(Base):
    """教练 Agent 会话记录"""
    __tablename__ = "coach_agent_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 会话类型
    session_type = Column(String)  # date_prep, communication_training, confidence_building

    # 训练内容
    training_content = Column(JSON)

    # 训练结果
    training_results = Column(JSON)

    # 进步评估
    progress_assessment = Column(Text)

    # 下一步建议
    next_steps = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


class GuardianAgentSessionDB(Base):
    """保安 Agent 会话记录"""
    __tablename__ = "guardian_agent_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 会话类型
    session_type = Column(String)  # safety_check, risk_assessment, emergency_response

    # 安全评估结果
    safety_assessment = Column(JSON)

    # 风险等级
    risk_level = Column(String)  # low, medium, high

    # 安全建议
    safety_recommendations = Column(JSON)

    # 紧急联系人
    emergency_contact = Column(JSON)

    # 位置共享状态
    location_sharing_enabled = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
