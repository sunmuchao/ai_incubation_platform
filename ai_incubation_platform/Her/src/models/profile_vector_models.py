"""
用户画像向量模型 - 渐进式智能收集架构

核心设计：
1. 144维向量存储（对应 VECTOR_MATCH_SYSTEM_DESIGN.md）
2. 画像完整度跟踪
3. 推断来源追溯
4. 置信度管理
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class DimensionCategory(str, Enum):
    """维度分类"""
    DEMOGRAPHICS = "demographics"  # 人口统计学 [0-15]
    VALUES = "values"  # 价值观 [16-31]
    PERSONALITY = "personality"  # 大五人格 [32-47]
    ATTACHMENT = "attachment"  # 依恋类型 [48-63]
    GROWTH = "growth"  # 成长意愿 [64-71]
    INTERESTS = "interests"  # 兴趣爱好 [72-87]
    LIFESTYLE = "lifestyle"  # 生活方式 [88-103]
    BEHAVIOR = "behavior"  # 行为模式 [104-119]
    COMMUNICATION = "communication"  # 沟通风格 [120-135]
    IMPLICIT = "implicit"  # 隐性特征 [136-143]


class DataSource(str, Enum):
    """数据来源"""
    # 直接收集
    REGISTRATION = "registration"  # 注册填写
    QUESTIONNAIRE = "questionnaire"  # 问卷回答
    GAME_TEST = "game_test"  # 游戏化测试
    CONVERSATION = "conversation"  # 对话收集

    # 第三方授权
    WECHAT_BASIC = "wechat_basic"  # 微信基础信息
    WECHAT_MOMENTS = "wechat_moments"  # 微信朋友圈分析
    WECHAT_MINIAPP = "wechat_miniapp"  # 微信小程序使用

    # AI 推断
    CHAT_INFERENCE = "chat_inference"  # 聊天内容推断
    BEHAVIOR_INFERENCE = "behavior_inference"  # 行为推断
    SWIPE_INFERENCE = "swipe_inference"  # 滑动行为推断
    INTERACTION_INFERENCE = "interaction_inference"  # 互动行为推断

    # 关系阶段收集
    CONFLICT_OBSERVATION = "conflict_observation"  # 冲突观察
    RELATIONSHIP_PROGRESS = "relationship_progress"  # 关系进展


class DimensionDefinition(BaseModel):
    """维度定义"""
    index: int  # 向量索引
    name: str  # 维度名称
    category: DimensionCategory  # 所属分类
    description: str  # 描述
    importance: str = "medium"  # high, medium, low
    collect_priority: int = 0  # 收集优先级（越大越优先）
    inferrable: bool = True  # 是否可推断
    inference_sources: List[DataSource] = []  # 可推断来源
    min_confidence: float = 0.5  # 最小置信度阈值


# 维度定义表（144维）
DIMENSION_DEFINITIONS: Dict[int, DimensionDefinition] = {
    # 人口统计学维度 [0-15]
    **{i: DimensionDefinition(
        index=i,
        name=["年龄", "年龄偏好下限", "年龄偏好上限", "性别编码", "性取向编码", "性别偏好编码",
              "城市层级", "是否接受异地", "经度", "纬度", "教育程度", "身高", "收入区间",
              "职业类型", "是否有房", "是否有车"][i],
        category=DimensionCategory.DEMOGRAPHICS,
        description="人口统计学基础信息",
        importance="high" if i in [0, 3, 6] else "medium",
        collect_priority=10 if i in [0, 3, 6] else 5,
        inferrable=i in [6, 7, 8, 9],  # 地理相关可推断
        inference_sources=[DataSource.REGISTRATION, DataSource.WECHAT_BASIC]
    ) for i in range(16)},

    # 价值观维度 [16-31]
    **{16 + i: DimensionDefinition(
        index=16 + i,
        name=["家庭重要程度", "是否想要孩子", "孩子数量偏好", "与父母同住意愿", "家务分配观念",
              "传统观念程度", "事业重要程度", "工作生活平衡偏好", "职业稳定性偏好", "创业意愿",
              "职业发展优先级", "消费观念", "理财意识", "风险偏好", "储蓄习惯", "消费决策风格"][i],
        category=DimensionCategory.VALUES,
        description="价值观相关维度",
        importance="high" if i in [1, 11] else "medium",  # 生育意愿、金钱观是高重要性
        collect_priority=9 if i in [1, 11] else 4,
        inferrable=True,
        inference_sources=[DataSource.CONVERSATION, DataSource.CHAT_INFERENCE,
                          DataSource.WECHAT_MOMENTS, DataSource.GAME_TEST]
    ) for i in range(16)},

    # 大五人格维度 [32-47]
    **{32 + i: DimensionDefinition(
        index=32 + i,
        name=["新事物接受程度", "好奇心强度", "创造力", "审美敏感度",
              "计划性", "自律程度", "可靠性", "目标导向",
              "社交活跃度", "精力水平", "乐观程度", "自信程度",
              "信任程度", "合作意愿", "情绪稳定性", "抗压能力"][i],
        category=DimensionCategory.PERSONALITY,
        description="大五人格相关维度",
        importance="high",
        collect_priority=8,
        inferrable=True,
        inference_sources=[DataSource.GAME_TEST, DataSource.CHAT_INFERENCE,
                          DataSource.BEHAVIOR_INFERENCE]
    ) for i in range(16)},

    # 依恋类型维度 [48-63]
    **{48 + i: DimensionDefinition(
        index=48 + i,
        name=["安全型得分", "焦虑型得分", "回避型得分", "恐惧型得分",
              "亲密需求程度", "独立需求程度", "安全感需求", "承诺意愿",
              "冲突情绪反应", "冲突沟通倾向", "被拒绝反应", "伴侣忙碌反应",
              "长期分离状态", "争吵后恢复速度", "负面情绪容忍度", "依恋类型置信度"][i],
        category=DimensionCategory.ATTACHMENT,
        description="依恋类型相关维度",
        importance="high",
        collect_priority=8,
        inferrable=True,
        inference_sources=[DataSource.GAME_TEST, DataSource.INTERACTION_INFERENCE,
                          DataSource.CONFLICT_OBSERVATION]
    ) for i in range(16)},

    # 成长意愿维度 [64-71]
    **{64 + i: DimensionDefinition(
        index=64 + i,
        name=["自我改变意愿", "接纳差异意愿", "学习意愿", "反思能力",
              "妥协意愿", "持续成长意识", "危机应对信心", "成长轨迹一致性"][i],
        category=DimensionCategory.GROWTH,
        description="成长意愿相关维度",
        importance="high",
        collect_priority=7,
        inferrable=True,
        inference_sources=[DataSource.INTERACTION_INFERENCE, DataSource.RELATIONSHIP_PROGRESS]
    ) for i in range(8)},

    # 兴趣爱好维度 [72-87]
    **{72 + i: DimensionDefinition(
        index=72 + i,
        name=f"兴趣嵌入向量_{i}",
        category=DimensionCategory.INTERESTS,
        description="兴趣爱好嵌入向量",
        importance="medium",
        collect_priority=6,
        inferrable=True,
        inference_sources=[DataSource.REGISTRATION, DataSource.WECHAT_MOMENTS,
                          DataSource.SWIPE_INFERENCE]
    ) for i in range(16)},

    # 生活方式维度 [88-103]
    **{88 + i: DimensionDefinition(
        index=88 + i,
        name=["作息类型", "运动频率", "社交频率", "独处需求", "娱乐偏好",
              "饮食偏好", "旅行频率", "周末活动偏好", "生活节奏", "压力应对方式",
              "决策风格", "冲突处理方式", "沟通偏好", "表达风格", "情感表达方式", "承诺态度"][i] if i < 16 else f"生活方式_{i}",
        category=DimensionCategory.LIFESTYLE,
        description="生活方式相关维度",
        importance="medium",
        collect_priority=5,
        inferrable=True,
        inference_sources=[DataSource.CHAT_INFERENCE, DataSource.BEHAVIOR_INFERENCE]
    ) for i in range(16)},

    # 行为模式维度 [104-119]
    **{104 + i: DimensionDefinition(
        index=104 + i,
        name=f"行为模式_{i}",
        category=DimensionCategory.BEHAVIOR,
        description="行为模式相关维度（从滑动/互动行为学习）",
        importance="medium",
        collect_priority=4,
        inferrable=True,
        inference_sources=[DataSource.SWIPE_INFERENCE, DataSource.BEHAVIOR_INFERENCE]
    ) for i in range(16)},

    # 沟通风格维度 [120-135]
    **{120 + i: DimensionDefinition(
        index=120 + i,
        name=["语言正式度_1", "语言正式度_2", "语言正式度_3", "语言正式度_4",
              "幽默程度_1", "幽默程度_2", "幽默程度_3", "幽默程度_4",
              "话题偏好_1", "话题偏好_2", "话题偏好_3", "话题偏好_4",
              "冲突沟通方式", "冷战倾向度", "冲突修复意愿", "冲突修复能力"][i] if i < 16 else f"沟通风格_{i}",
        category=DimensionCategory.COMMUNICATION,
        description="沟通风格相关维度",
        importance="high" if i >= 12 else "medium",  # 冲突相关是高重要性
        collect_priority=7 if i >= 12 else 4,
        inferrable=True,
        inference_sources=[DataSource.CHAT_INFERENCE, DataSource.INTERACTION_INFERENCE]
    ) for i in range(16)},

    # 隐性特征维度 [136-143]
    **{136 + i: DimensionDefinition(
        index=136 + i,
        name=["声明行为差异度", "实际偏好性格", "实际偏好生活方式", "实际偏好沟通风格",
              "潜意识需求", "社会期许偏差修正", "隐性特征置信度", "隐性特征推荐权重"][i],
        category=DimensionCategory.IMPLICIT,
        description="隐性特征相关维度（从行为-声明差异推断）",
        importance="low",  # 初次匹配时权重较低
        collect_priority=2,
        inferrable=True,
        inference_sources=[DataSource.SWIPE_INFERENCE, DataSource.BEHAVIOR_INFERENCE]
    ) for i in range(8)},
}


class DimensionValue(BaseModel):
    """维度值（包含置信度和来源）"""
    value: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: DataSource = DataSource.REGISTRATION
    inferred_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    evidence: Optional[str] = None  # 推断证据（如对话片段）


class CategoryCompleteness(BaseModel):
    """分类完整度"""
    category: DimensionCategory
    total_dimensions: int
    filled_dimensions: int
    avg_confidence: float
    missing_dimensions: List[int]

    @property
    def completeness_ratio(self) -> float:
        """完整度比例"""
        return self.filled_dimensions / self.total_dimensions if self.total_dimensions > 0 else 0.0


class ProfileCompleteness(BaseModel):
    """画像完整度"""
    total_dimensions: int = 144
    filled_dimensions: int = 0
    weighted_completeness: float = 0.0  # 按重要性加权
    categories: Dict[DimensionCategory, CategoryCompleteness] = {}

    # 关键维度检查
    critical_dimensions_filled: bool = False  # 一票否决维度是否填写
    critical_dimensions: List[str] = []  # 未填写的关键维度

    # 推荐策略
    recommended_strategy: str = "cold_start"  # cold_start, basic, vector, precise
    strategy_reason: str = ""

    @property
    def completeness_ratio(self) -> float:
        """完整度比例"""
        return self.filled_dimensions / self.total_dimensions if self.total_dimensions > 0 else 0.0

    def determine_strategy(self) -> str:
        """根据完整度确定匹配策略"""
        if self.completeness_ratio < 0.2:
            return "cold_start"
        elif self.completeness_ratio < 0.5:
            return "basic"
        elif self.completeness_ratio < 0.8:
            return "vector"
        else:
            return "precise"


class UserVectorProfile(BaseModel):
    """用户向量画像"""
    user_id: str

    # 144维向量（带置信度）
    dimensions: Dict[int, DimensionValue] = {}

    # 向量数组（用于相似度计算）
    vector: List[float] = Field(default_factory=lambda: [0.0] * 144)

    # 完整度
    completeness: ProfileCompleteness = Field(default_factory=ProfileCompleteness)

    # 元数据
    version: str = "v1.0"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 数据来源统计
    source_stats: Dict[DataSource, int] = {}

    def set_dimension(
        self,
        index: int,
        value: float,
        confidence: float = 1.0,
        source: DataSource = DataSource.REGISTRATION,
        evidence: Optional[str] = None
    ):
        """设置维度值"""
        if 0 <= index < 144:
            self.dimensions[index] = DimensionValue(
                value=value,
                confidence=confidence,
                source=source,
                inferred_at=datetime.now() if source != DataSource.REGISTRATION else None,
                updated_at=datetime.now(),
                evidence=evidence
            )
            self.vector[index] = value
            self.updated_at = datetime.now()

    def get_dimension(self, index: int) -> Optional[DimensionValue]:
        """获取维度值"""
        return self.dimensions.get(index)

    def calculate_completeness(self) -> ProfileCompleteness:
        """计算画像完整度"""
        categories: Dict[DimensionCategory, CategoryCompleteness] = {}
        total_filled = 0
        weighted_sum = 0.0

        # 重要性权重
        importance_weights = {"high": 1.0, "medium": 0.5, "low": 0.2}
        total_weight = 0.0

        for category in DimensionCategory:
            category_indices = [
                i for i, d in DIMENSION_DEFINITIONS.items()
                if d.category == category
            ]

            filled = sum(1 for i in category_indices if i in self.dimensions)
            total_filled += filled

            avg_conf = 0.0
            if filled > 0:
                avg_conf = sum(
                    self.dimensions[i].confidence
                    for i in category_indices
                    if i in self.dimensions
                ) / filled

            missing = [i for i in category_indices if i not in self.dimensions]

            categories[category] = CategoryCompleteness(
                category=category,
                total_dimensions=len(category_indices),
                filled_dimensions=filled,
                avg_confidence=avg_conf,
                missing_dimensions=missing
            )

            # 加权完整度
            for i in category_indices:
                weight = importance_weights.get(DIMENSION_DEFINITIONS[i].importance, 0.5)
                total_weight += weight
                if i in self.dimensions:
                    weighted_sum += weight * self.dimensions[i].confidence

        # 检查关键维度
        critical_dims = [17, 27]  # 生育意愿、金钱观
        critical_filled = [i for i in critical_dims if i in self.dimensions]
        critical_missing = [DIMENSION_DEFINITIONS[i].name for i in critical_dims if i not in self.dimensions]

        completeness = ProfileCompleteness(
            total_dimensions=144,
            filled_dimensions=total_filled,
            weighted_completeness=weighted_sum / total_weight if total_weight > 0 else 0.0,
            categories=categories,
            critical_dimensions_filled=len(critical_filled) == len(critical_dims),
            critical_dimensions=critical_missing
        )

        completeness.recommended_strategy = completeness.determine_strategy()

        self.completeness = completeness
        return completeness


class ProfileInferenceResult(BaseModel):
    """画像推断结果"""
    user_id: str

    # 推断的维度
    inferred_dimensions: Dict[int, DimensionValue] = {}

    # 推断来源
    inference_source: DataSource
    inference_method: str  # 具体方法名

    # 推断依据
    evidence: Optional[str] = None  # 原始数据摘要
    sample_size: int = 0  # 样本数量（如消息条数）

    # 置信度
    overall_confidence: float = 0.0

    # 时间
    inferred_at: datetime = Field(default_factory=datetime.now)

    # LLM 相关
    llm_model: Optional[str] = None
    llm_tokens_used: int = 0


class ThirdPartyDataInference(BaseModel):
    """第三方数据推断结果"""
    user_id: str
    source: DataSource

    # 推断结果
    inferred_profile: Dict[str, Any] = {}

    # 各维度推断
    dimension_inferences: Dict[int, DimensionValue] = {}

    # 原始数据摘要（脱敏）
    data_summary: Optional[str] = None

    # 隐私保护
    data_retention_days: int = 30  # 数据保留天数
    user_consent: bool = False  # 用户是否授权

    # 时间
    inferred_at: datetime = Field(default_factory=datetime.now)


class GameTestResult(BaseModel):
    """游戏化测试结果"""
    user_id: str
    test_type: str  # personality, attachment, values

    # 测试答案
    answers: List[Dict[str, Any]] = []

    # 推断的维度
    inferred_dimensions: Dict[int, DimensionValue] = {}

    # 测试报告
    test_report: Optional[str] = None

    # 时间
    completed_at: datetime = Field(default_factory=datetime.now)

    # 奖励
    reward_given: bool = False
    reward_type: Optional[str] = None  # unlock_precise_match, badge, etc.