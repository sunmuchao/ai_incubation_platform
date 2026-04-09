"""
账单分析 Skill

基于消费水平和地理轨迹的真实匹配
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger
import json


class BillAnalysisSkill:
    """
    账单分析 Skill - 基于"消费水平"的真实匹配

    核心能力:
    - 账单特征分析（非明细）
    - 消费层级识别
    - 消费习惯画像
    - 消费观兼容性分析

    AI Native 特性:
    - 自主分析用户消费模式
    - 主动推送消费观匹配建议
    - 自然语言查询消费画像
    """

    name = "bill_analysis"
    version = "1.0.0"
    description = """
    账单分析服务

    能力:
    - 账单特征分析（非明细，仅特征）
    - 消费层级识别（轻奢/性价比/高端等）
    - 消费习惯画像生成
    - 消费观兼容性分析
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "action": {
                    "type": "string",
                    "enum": ["analyze", "get_profile", "compare_compatibility"],
                    "description": "操作类型"
                },
                "target_user_id": {
                    "type": "string",
                    "description": "目标用户 ID（用于兼容性比较）"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["month", "quarter", "year"],
                    "default": "quarter"
                }
            },
            "required": ["user_id", "action"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "consumption_profile": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string"},
                        "frequency": {"type": "string"},
                        "preferred_categories": {"type": "array"},
                        "average_transaction": {"type": "string"}
                    }
                },
                "compatibility": {
                    "type": "object",
                    "properties": {
                        "consumption_match": {"type": "number"},
                        "lifestyle_match": {"type": "number"},
                        "aesthetic_match": {"type": "number"},
                        "overall_match": {"type": "number"}
                    }
                }
            }
        }

    async def execute(
        self,
        user_id: str,
        action: str,
        target_user_id: Optional[str] = None,
        time_range: Optional[str] = "quarter",
        **kwargs
    ) -> dict:
        """
        执行账单分析 Skill

        Args:
            user_id: 用户 ID
            action: 操作类型 (analyze/get_profile/compare_compatibility)
            target_user_id: 目标用户 ID（用于兼容性比较）
            time_range: 时间范围
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"BillAnalysisSkill: Executing for user={user_id}, action={action}")

        if action == "analyze":
            return await self._analyze_bills(user_id, time_range)
        elif action == "get_profile":
            return await self._get_consumption_profile(user_id)
        elif action == "compare_compatibility":
            if not target_user_id:
                return {"success": False, "error": "target_user_id required for compatibility comparison"}
            return await self._compare_consumption_compatibility(user_id, target_user_id)
        else:
            return {"success": False, "error": "Invalid action", "ai_message": "不支持的操作类型"}

    async def _analyze_bills(self, user_id: str, time_range: str) -> dict:
        """
        分析账单特征

        注意：仅分析特征，不读取明细，保护用户隐私
        """
        logger.info(f"BillAnalysisSkill: Analyzing bills for user={user_id}, range={time_range}")

        # Step 1: 获取用户授权的账单特征数据
        # 注：当前使用模拟数据，待对接外部账单 API 后替换
        bill_features = await self._fetch_bill_features(user_id, time_range)

        if not bill_features:
            # 开发环境返回模拟数据
            bill_features = self._generate_mock_bill_features(user_id)

        # Step 2: 分析消费层级
        consumption_level = self._analyze_consumption_level(bill_features)

        # Step 3: 分析消费习惯
        consumption_habits = self._analyze_consumption_habits(bill_features)

        # Step 4: 生成消费画像
        profile = {
            "user_id": user_id,
            "level": consumption_level["level"],
            "level_score": consumption_level["score"],
            "frequency": consumption_habits["frequency"],
            "preferred_categories": consumption_habits["categories"],
            "average_transaction": consumption_habits["avg_transaction"],
            "spending_pattern": consumption_habits["pattern"],
            "price_sensitivity": consumption_habits["price_sensitivity"]
        }

        # Step 5: 保存到数据库
        await self._save_consumption_profile(user_id, profile)

        # Step 6: 生成 AI 消息
        ai_message = self._generate_analysis_message(profile)

        return {
            "success": True,
            "ai_message": ai_message,
            "consumption_profile": profile,
            "bill_features": {
                "total_transactions": bill_features.get("total_transactions", 0),
                "avg_monthly_spending": bill_features.get("avg_monthly_spending", 0),
                "category_distribution": bill_features.get("category_distribution", {})
            }
        }

    async def _get_consumption_profile(self, user_id: str) -> dict:
        """获取用户消费画像"""
        # 注：当前从本地缓存获取，待对接数据库后替换
        profile = await self._load_consumption_profile(user_id)

        if not profile:
            # 如果还没有画像，先分析
            return await self._analyze_bills(user_id, "quarter")

        return {
            "success": True,
            "ai_message": f"已为你生成消费画像：{profile.get('level', '未知')}消费群体",
            "consumption_profile": profile
        }

    async def _compare_consumption_compatibility(self, user_id_1: str, user_id_2: str) -> dict:
        """比较两人消费观兼容性"""
        # 获取双方消费画像
        profile_1 = await self._load_consumption_profile(user_id_1)
        profile_2 = await self._load_consumption_profile(user_id_2)

        if not profile_1:
            profile_1 = (await self._analyze_bills(user_id_1, "quarter")).get("consumption_profile", {})
        if not profile_2:
            profile_2 = (await self._analyze_bills(user_id_2, "quarter")).get("consumption_profile", {})

        # 计算兼容性
        compatibility = self._calculate_consumption_compatibility(profile_1, profile_2)

        # 生成 AI 解读
        ai_interpretation = self._generate_compatibility_interpretation(compatibility)

        return {
            "success": True,
            "ai_message": ai_interpretation["message"],
            "compatibility": compatibility,
            "analysis": {
                "user_1_level": profile_1.get("level", "未知"),
                "user_2_level": profile_2.get("level", "未知"),
                "key_differences": ai_interpretation["differences"],
                "key_similarities": ai_interpretation["similarities"]
            }
        }

    async def _fetch_bill_features(self, user_id: str, time_range: str) -> Optional[dict]:
        """
        从外部 API 获取账单特征（非明细）

        隐私保护：
        - 仅获取聚合特征，不获取具体消费明细
        - 用户必须授权才能访问

        注：当前版本返回 None，使用模拟数据替代
        待对接外部账单 API 后实现真实数据获取
        """
        # 注：外部账单 API 待对接，当前使用模拟数据
        logger.info(f"BillAnalysisSkill: Bill features requested for user={user_id}, returning mock data")
        return None

    def _generate_mock_bill_features(self, user_id: str) -> dict:
        """生成模拟账单特征（开发环境）"""
        # 基于用户 ID 哈希生成一致的模拟数据
        hash_value = hash(user_id) % 100

        # 消费层级分布
        if hash_value < 20:
            level = "高端"
            avg_transaction = "500-1000 元"
            categories = ["高端餐饮", "奢侈品", "五星级酒店", "私人会所"]
        elif hash_value < 50:
            level = "轻奢"
            avg_transaction = "200-500 元"
            categories = ["精品咖啡", "设计师品牌", "艺术展览", "品质餐厅"]
        elif hash_value < 80:
            level = "性价比"
            avg_transaction = "100-200 元"
            categories = ["连锁餐饮", "快时尚", "电影院", "快餐"]
        else:
            level = "经济型"
            avg_transaction = "50-100 元"
            categories = ["食堂", "平价超市", "拼多多", "自助餐"]

        return {
            "total_transactions": 50 + (hash_value % 100),
            "avg_monthly_spending": 3000 + (hash_value % 5000),
            "category_distribution": {
                "餐饮": 30 + (hash_value % 20),
                "购物": 20 + (hash_value % 15),
                "娱乐": 15 + (hash_value % 10),
                "交通": 10 + (hash_value % 5),
                "其他": 25
            },
            "level": level,
            "avg_transaction": avg_transaction,
            "categories": categories
        }

    def _analyze_consumption_level(self, bill_features: dict) -> dict:
        """分析消费层级"""
        level = bill_features.get("level", "未知")

        level_scores = {
            "高端": 0.95,
            "轻奢": 0.75,
            "性价比": 0.50,
            "经济型": 0.30
        }

        return {
            "level": level,
            "score": level_scores.get(level, 0.5),
            "confidence": 0.85
        }

    def _analyze_consumption_habits(self, bill_features: dict) -> dict:
        """分析消费习惯"""
        categories = bill_features.get("categories", [])

        # 消费频率
        total_transactions = bill_features.get("total_transactions", 0)
        if total_transactions > 100:
            frequency = "高频"
        elif total_transactions > 50:
            frequency = "中频"
        else:
            frequency = "低频"

        # 平均客单价
        avg_transaction = bill_features.get("avg_transaction", "未知")

        # 消费模式
        pattern = self._infer_spending_pattern(categories)

        # 价格敏感度
        price_sensitivity = self._infer_price_sensitivity(bill_features)

        return {
            "frequency": frequency,
            "categories": categories,
            "avg_transaction": avg_transaction,
            "pattern": pattern,
            "price_sensitivity": price_sensitivity
        }

    def _infer_spending_pattern(self, categories: List[str]) -> str:
        """推断消费模式"""
        quality_keywords = ["精品", "设计师", "艺术", "品质", "高端"]
        practical_keywords = ["性价比", "平价", "连锁", "快餐"]

        quality_count = sum(1 for cat in categories if any(kw in cat for kw in quality_keywords))
        practical_count = sum(1 for cat in categories if any(kw in cat for kw in practical_keywords))

        if quality_count > practical_count:
            return "品质导向型"
        elif practical_count > quality_count:
            return "实用导向型"
        else:
            return "平衡型"

    def _infer_price_sensitivity(self, bill_features: dict) -> str:
        """推断价格敏感度"""
        # 基于消费分散度推断
        category_dist = bill_features.get("category_distribution", {})
        if len(category_dist) > 5:
            return "低敏感（多元化消费）"
        elif len(category_dist) > 3:
            return "中等敏感"
        else:
            return "高敏感（集中消费）"

    # 内存缓存（开发环境使用，生产环境应使用数据库）
    _profile_cache: Dict[str, dict] = {}

    async def _save_consumption_profile(self, user_id: str, profile: dict) -> None:
        """保存消费画像到缓存（生产环境应使用数据库）"""
        # 注：当前使用内存缓存，待对接数据库
        self._profile_cache[user_id] = {
            **profile,
            "updated_at": datetime.now().isoformat()
        }
        logger.info(f"BillAnalysisSkill: Profile saved for user={user_id}")

    async def _load_consumption_profile(self, user_id: str) -> Optional[dict]:
        """从缓存加载消费画像（生产环境应使用数据库）"""
        # 注：当前使用内存缓存，待对接数据库
        return self._profile_cache.get(user_id)

    def _calculate_consumption_compatibility(self, profile_1: dict, profile_2: dict) -> dict:
        """计算消费观兼容性"""
        # 消费层级匹配
        level_score = self._calculate_level_compatibility(
            profile_1.get("level_score", 0.5),
            profile_2.get("level_score", 0.5)
        )

        # 消费习惯匹配
        habit_score = self._calculate_habit_compatibility(
            profile_1.get("pattern", ""),
            profile_2.get("pattern", "")
        )

        # 审美匹配
        aesthetic_score = self._calculate_aesthetic_compatibility(
            profile_1.get("preferred_categories", []),
            profile_2.get("preferred_categories", [])
        )

        # 总体兼容性
        overall = (level_score * 0.4 + habit_score * 0.3 + aesthetic_score * 0.3)

        return {
            "consumption_match": round(level_score, 2),
            "lifestyle_match": round(habit_score, 2),
            "aesthetic_match": round(aesthetic_score, 2),
            "overall_match": round(overall, 2)
        }

    def _calculate_level_compatibility(self, score_1: float, score_2: float) -> float:
        """计算消费层级兼容性"""
        # 层级差异越小，兼容性越高
        diff = abs(score_1 - score_2)
        return max(1.0 - diff, 0.0)

    def _calculate_habit_compatibility(self, pattern_1: str, pattern_2: str) -> float:
        """计算消费习惯兼容性"""
        if pattern_1 == pattern_2:
            return 1.0
        elif "品质" in pattern_1 and "品质" in pattern_2:
            return 0.8
        elif "实用" in pattern_1 and "实用" in pattern_2:
            return 0.8
        else:
            return 0.5

    def _calculate_aesthetic_compatibility(self, categories_1: List[str], categories_2: List[str]) -> float:
        """计算审美兼容性"""
        if not categories_1 or not categories_2:
            return 0.5

        common = set(categories_1) & set(categories_2)
        union = set(categories_1) | set(categories_2)

        if not union:
            return 0.5

        jaccard = len(common) / len(union)
        return min(jaccard * 2, 1.0)  # 放大共同兴趣的权重

    def _generate_analysis_message(self, profile: dict) -> str:
        """生成分析结果消息"""
        level = profile.get("level", "未知")
        pattern = profile.get("pattern", "未知")
        frequency = profile.get("frequency", "未知")

        return (f"基于你的消费特征分析，你属于「{level}」消费群体。\n"
                f"消费模式：{pattern}\n"
                f"消费频率：{frequency}\n\n"
                f"AI 将基于此为你匹配消费观相近的人，减少「见光死」的概率~")

    def _generate_compatibility_interpretation(self, compatibility: dict) -> dict:
        """生成兼容性解读"""
        overall = compatibility.get("overall_match", 0.5)

        if overall >= 0.8:
            message = "你们的消费观非常匹配！在生活方式和审美品味上都有很好的契合度~"
        elif overall >= 0.6:
            message = "你们的消费观整体匹配，在一些方面可能有差异，但可以相互包容~"
        else:
            message = "你们的消费观有一定差异，建议提前沟通各自的消费习惯和期望~"

        differences = []
        similarities = []

        if compatibility.get("consumption_match", 0.5) >= 0.8:
            similarities.append("消费层级相近")
        else:
            differences.append("消费层级有差异")

        if compatibility.get("lifestyle_match", 0.5) >= 0.8:
            similarities.append("生活方式相似")
        else:
            differences.append("生活方式不同")

        return {
            "message": message,
            "differences": differences,
            "similarities": similarities
        }

    # 自主触发器

    async def autonomous_trigger(self, user_id: str, trigger_type: str, context: dict) -> dict:
        """
        自主触发账单分析

        Args:
            user_id: 用户 ID
            trigger_type: 触发类型
            context: 上下文数据

        Returns:
            触发结果
        """
        logger.info(f"BillAnalysisSkill: Autonomous trigger {trigger_type} for {user_id}")

        if trigger_type == "profile_update_reminder":
            # 定期提醒更新画像
            return await self._handle_profile_update_reminder(user_id, context)
        elif trigger_type == "new_match_compatibility":
            # 新匹配时自动分析消费兼容性
            return await self._handle_new_match_compatibility(user_id, context)
        else:
            return {"triggered": False, "reason": "unknown_trigger_type"}

    async def _handle_profile_update_reminder(self, user_id: str, context: dict) -> dict:
        """处理画像更新提醒"""
        last_analysis = context.get("last_analysis_date")

        # 如果超过 3 个月未分析，提醒更新
        if last_analysis:
            days_since = (datetime.now() - last_analysis).days
            if days_since > 90:
                return {
                    "triggered": True,
                    "should_push": True,
                    "push_message": "你的消费画像已超过 3 个月未更新，建议更新以获得更精准的匹配~"
                }

        return {"triggered": False, "reason": "profile_is_recent"}

    async def _handle_new_match_compatibility(self, user_id: str, context: dict) -> dict:
        """处理新匹配时的兼容性分析"""
        match_id = context.get("match_id")
        target_user_id = context.get("target_user_id")

        if not target_user_id:
            return {"triggered": False, "reason": "no_target_user"}

        # 自动分析消费兼容性
        result = await self._compare_consumption_compatibility(user_id, target_user_id)

        # 如果兼容性很高，可以推送
        if result.get("compatibility", {}).get("overall_match", 0) >= 0.8:
            return {
                "triggered": True,
                "should_push": True,
                "push_message": f"AI 分析发现你们消费观匹配度高达{result['compatibility']['overall_match'] * 100:.0f}%~",
                "compatibility": result.get("compatibility")
            }

        return {"triggered": False, "reason": "compatibility_not_high"}


# 全局 Skill 实例
_bill_analysis_skill_instance: Optional[BillAnalysisSkill] = None


def get_bill_analysis_skill() -> BillAnalysisSkill:
    """获取账单分析 Skill 单例实例"""
    global _bill_analysis_skill_instance
    if _bill_analysis_skill_instance is None:
        _bill_analysis_skill_instance = BillAnalysisSkill()
    return _bill_analysis_skill_instance
