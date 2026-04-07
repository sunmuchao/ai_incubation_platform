"""
智能选品工作流

流程：
1. 理解用户需求
2. 搜索候选商品
3. 多维度比较分析
4. 生成推荐理由
5. 预测成团概率
6. 排序返回 Top-N
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AutoSelectProductWorkflow:
    """
    智能选品工作流

    基于用户需求和上下文，自主搜索、比较并推荐最优商品。
    """

    def __init__(self, db_session: Optional[Any] = None):
        self.db = db_session
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute(
        self,
        query: str,
        user_id: str,
        community_id: Optional[str] = None,
        category: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        执行智能选品工作流

        Args:
            query: 用户查询文本
            user_id: 用户 ID
            community_id: 社区 ID
            category: 商品类别
            keywords: 关键词列表
            limit: 返回数量限制

        Returns:
            Dict: 选品结果，包含推荐商品列表和推荐理由
        """
        trace_id = f"asp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.logger.info(f"[{trace_id}] 智能选品工作流开始执行")

        try:
            # Step 1: 深度理解用户需求
            user_intent = await self._step_understand_intent(query, user_id, trace_id)

            # Step 2: 搜索候选商品
            candidates = await self._step_search_products(user_intent, category, keywords, trace_id)

            # Step 3: 多维度比较分析
            compared = await self._step_compare_products(candidates, user_intent, trace_id)

            # Step 4: 生成推荐理由
            with_reasons = await self._step_generate_reasons(compared, user_intent, trace_id)

            # Step 5: 预测成团概率
            with_probability = await self._step_predict_probability(with_reasons, community_id, trace_id)

            # Step 6: 排序并返回 Top-N
            result = await self._step_rank_and_return(with_probability, limit, trace_id)

            self.logger.info(f"[{trace_id}] 智能选品工作流执行完成，返回 {len(result)} 个商品")

            return {
                "products": result,
                "query": query,
                "user_intent": user_intent,
                "total_candidates": len(candidates),
                "trace_id": trace_id
            }

        except Exception as e:
            self.logger.error(f"[{trace_id}] 工作流执行失败：{str(e)}")
            raise

    async def _step_understand_intent(self, query: str, user_id: str, trace_id: str) -> Dict[str, Any]:
        """Step 1: 深度理解用户需求"""
        self.logger.info(f"[{trace_id}] Step 1: 理解用户需求")

        # 用户意图分析
        intent = {
            "category": None,
            "price_sensitivity": "medium",  # low, medium, high
            "quality_preference": "balanced",  # budget, balanced, premium
            "urgency": "normal",  # low, normal, high
            "implicit_preferences": []
        }

        # 类别识别
        category_keywords = {
            "水果": ["水果", "苹果", "香蕉", "橙子", "草莓", "葡萄", "西瓜", "芒果", "樱桃", "榴莲"],
            "蔬菜": ["蔬菜", "青菜", "土豆", "番茄", "黄瓜", "萝卜", "白菜", "菠菜"],
            "肉类": ["肉类", "猪肉", "牛肉", "羊肉", "鸡肉", "鸭肉", "排骨"],
            "海鲜": ["海鲜", "鱼", "虾", "蟹", "贝类", "龙虾", "鲍鱼"],
            "乳品": ["牛奶", "酸奶", "奶酪", "乳品", "奶粉"],
            "零食": ["零食", "饼干", "坚果", "糖果", "薯片", "巧克力"],
            "粮油": ["大米", "面粉", "油", "粮油", "杂粮", "小米", "玉米"],
            "饮料": ["饮料", "果汁", "茶饮", "咖啡", "汽水"]
        }

        query_lower = query.lower()
        for category, keywords in category_keywords.items():
            if any(kw in query_lower for kw in keywords):
                intent["category"] = category
                intent["matched_keywords"] = [kw for kw in keywords if kw in query_lower]
                break

        # 价格敏感度分析
        if any(kw in query_lower for kw in ["便宜", "实惠", "低价", "划算", "省钱", "优惠"]):
            intent["price_sensitivity"] = "high"
            intent["quality_preference"] = "budget"
        elif any(kw in query_lower for kw in ["高档", "精品", "进口", "有机", "高端", "品质"]):
            intent["price_sensitivity"] = "low"
            intent["quality_preference"] = "premium"

        # 紧急程度分析
        if any(kw in query_lower for kw in ["急", "马上", "现在", "今天", "尽快"]):
            intent["urgency"] = "high"

        # 加载用户历史偏好（简化实现）
        intent["implicit_preferences"] = await self._load_user_preferences(user_id)

        self.logger.info(f"[{trace_id}] 用户意图：{intent}")
        return intent

    async def _load_user_preferences(self, user_id: str) -> List[str]:
        """加载用户历史偏好"""
        # 简化实现：返回模拟偏好
        return ["新鲜", "性价比高", "好评多"]

    async def _step_search_products(
        self,
        user_intent: Dict,
        category: Optional[str],
        keywords: Optional[List[str]],
        trace_id: str
    ) -> List[Dict[str, Any]]:
        """Step 2: 搜索候选商品"""
        self.logger.info(f"[{trace_id}] Step 2: 搜索候选商品")

        # 确定搜索类别
        search_category = category or user_intent.get("category", "精选")

        # 商品目录（简化实现，实际应从数据库或商品服务获取）
        product_catalog = self._get_product_catalog()

        # 获取候选商品
        candidates = product_catalog.get(search_category, product_catalog.get("精选", []))

        # 关键词过滤
        if keywords:
            filtered = []
            for p in candidates:
                if any(kw in p["name"] or kw in p.get("description", "") for kw in keywords):
                    filtered.append(p)
            if filtered:
                candidates = filtered

        # 价格过滤（基于用户偏好）
        price_pref = user_intent.get("price_sensitivity", "medium")
        if price_pref == "high":  # 价格敏感，只显示便宜商品
            candidates = [p for p in candidates if p["group_price"] <= 40]
        elif price_pref == "low":  # 品质优先，显示高端商品
            candidates = [p for p in candidates if p["group_price"] >= 50]

        self.logger.info(f"[{trace_id}] 找到 {len(candidates)} 个候选商品")
        return candidates

    def _get_product_catalog(self) -> Dict[str, List[Dict]]:
        """获取商品目录"""
        return {
            "水果": [
                {
                    "id": "p001",
                    "name": "有机草莓",
                    "description": "有机种植，新鲜采摘，当季热销",
                    "price": 49.9,
                    "group_price": 35.9,
                    "category": "水果",
                    "rating": 4.9,
                    "sales_count": 1580,
                    "stock": 200,
                    "origin": "辽宁丹东",
                    "shelf_life": "3 天",
                    "tags": ["有机", "新鲜", "当季"]
                },
                {
                    "id": "p002",
                    "name": "海南芒果",
                    "description": "热带水果，甜度高核小肉厚",
                    "price": 39.9,
                    "group_price": 29.9,
                    "category": "水果",
                    "rating": 4.7,
                    "sales_count": 2300,
                    "stock": 500,
                    "origin": "海南三亚",
                    "shelf_life": "5 天",
                    "tags": ["热带", "甜", "当季"]
                },
                {
                    "id": "p003",
                    "name": "进口蓝莓",
                    "description": "富含花青素，护眼健康，进口品质",
                    "price": 59.9,
                    "group_price": 45.9,
                    "category": "水果",
                    "rating": 4.8,
                    "sales_count": 980,
                    "stock": 150,
                    "origin": "智利",
                    "shelf_life": "7 天",
                    "tags": ["进口", "健康", "护眼"]
                },
                {
                    "id": "p004",
                    "name": "新疆葡萄",
                    "description": "无籽提子，香甜可口",
                    "price": 35.9,
                    "group_price": 25.9,
                    "category": "水果",
                    "rating": 4.6,
                    "sales_count": 1200,
                    "stock": 300,
                    "origin": "新疆",
                    "shelf_life": "5 天",
                    "tags": ["无籽", "甜", "当季"]
                }
            ],
            "蔬菜": [
                {
                    "id": "p010",
                    "name": "有机蔬菜礼盒",
                    "description": "多种时令蔬菜组合，有机认证",
                    "price": 59.9,
                    "group_price": 45.9,
                    "category": "蔬菜",
                    "rating": 4.8,
                    "sales_count": 850,
                    "stock": 100,
                    "origin": "本地农场",
                    "shelf_life": "3 天",
                    "tags": ["有机", "新鲜", "组合"]
                }
            ],
            "肉类": [
                {
                    "id": "p020",
                    "name": "精选牛肉礼盒",
                    "description": "进口草饲牛肉，多部位组合",
                    "price": 199.9,
                    "group_price": 169.9,
                    "category": "肉类",
                    "rating": 4.9,
                    "sales_count": 420,
                    "stock": 50,
                    "origin": "澳大利亚",
                    "shelf_life": "冷冻 30 天",
                    "tags": ["进口", "草饲", "高端"]
                }
            ],
            "海鲜": [
                {
                    "id": "p030",
                    "name": "鲜活大闸蟹",
                    "description": "阳澄湖大闸蟹，鲜活配送",
                    "price": 129.9,
                    "group_price": 99.9,
                    "category": "海鲜",
                    "rating": 4.8,
                    "sales_count": 680,
                    "stock": 200,
                    "origin": "阳澄湖",
                    "shelf_life": "鲜活 3 天",
                    "tags": ["鲜活", "名产", "当季"]
                }
            ],
            "乳品": [
                {
                    "id": "p040",
                    "name": "进口牛奶箱装",
                    "description": "欧盟进口，纯牛奶 24 盒整箱",
                    "price": 89.9,
                    "group_price": 69.9,
                    "category": "乳品",
                    "rating": 4.9,
                    "sales_count": 3200,
                    "stock": 500,
                    "origin": "德国",
                    "shelf_life": "12 个月",
                    "tags": ["进口", "纯牛奶", "整箱"]
                }
            ],
            "零食": [
                {
                    "id": "p050",
                    "name": "混合坚果礼盒",
                    "description": "多种坚果组合，营养健康",
                    "price": 79.9,
                    "group_price": 59.9,
                    "category": "零食",
                    "rating": 4.7,
                    "sales_count": 1500,
                    "stock": 300,
                    "origin": "国产",
                    "shelf_life": "180 天",
                    "tags": ["坚果", "健康", "礼盒"]
                }
            ],
            "粮油": [
                {
                    "id": "p060",
                    "name": "东北大米 10kg",
                    "description": "黑土地五常大米，香甜软糯",
                    "price": 69.9,
                    "group_price": 55.9,
                    "category": "粮油",
                    "rating": 4.9,
                    "sales_count": 5200,
                    "stock": 1000,
                    "origin": "黑龙江五常",
                    "shelf_life": "12 个月",
                    "tags": ["五常", "优质", "家庭装"]
                }
            ],
            "精选": [
                {"id": "p001", "name": "有机草莓", "price": 49.9, "group_price": 35.9, "rating": 4.9, "sales_count": 1580},
                {"id": "p040", "name": "进口牛奶箱装", "price": 89.9, "group_price": 69.9, "rating": 4.9, "sales_count": 3200},
                {"id": "p060", "name": "东北大米 10kg", "price": 69.9, "group_price": 55.9, "rating": 4.9, "sales_count": 5200},
                {"id": "p050", "name": "混合坚果礼盒", "price": 79.9, "group_price": 59.9, "rating": 4.7, "sales_count": 1500}
            ]
        }

    async def _step_compare_products(
        self,
        candidates: List[Dict],
        user_intent: Dict,
        trace_id: str
    ) -> List[Dict[str, Any]]:
        """Step 3: 多维度比较分析"""
        self.logger.info(f"[{trace_id}] Step 3: 多维度比较分析")

        compared = []
        for product in candidates:
            # 计算综合得分
            score = self._calculate_product_score(product, user_intent)

            compared.append({
                **product,
                "score": score,
                "dimensions": {
                    "price_score": self._score_price(product),
                    "quality_score": self._score_quality(product),
                    "popularity_score": self._score_popularity(product),
                    "freshness_score": self._score_freshness(product)
                }
            })

        # 按得分排序
        compared.sort(key=lambda x: x["score"], reverse=True)

        return compared

    def _calculate_product_score(self, product: Dict, user_intent: Dict) -> float:
        """计算商品综合得分"""
        price_score = self._score_price(product)
        quality_score = self._score_quality(product)
        popularity_score = self._score_popularity(product)
        freshness_score = self._score_freshness(product)

        # 根据用户偏好调整权重
        pref = user_intent.get("quality_preference", "balanced")
        if pref == "budget":
            weights = {"price": 0.4, "quality": 0.2, "popularity": 0.2, "freshness": 0.2}
        elif pref == "premium":
            weights = {"price": 0.1, "quality": 0.4, "popularity": 0.2, "freshness": 0.3}
        else:
            weights = {"price": 0.25, "quality": 0.3, "popularity": 0.25, "freshness": 0.2}

        score = (
            price_score * weights["price"] +
            quality_score * weights["quality"] +
            popularity_score * weights["popularity"] +
            freshness_score * weights["freshness"]
        )

        return round(score, 2)

    def _score_price(self, product: Dict) -> float:
        """价格得分（越低越便宜，得分越高）"""
        price = product.get("group_price", 100)
        # 0-30 元：10 分，30-60 元：7 分，60-100 元：5 分，100+：3 分
        if price <= 30:
            return 10.0
        elif price <= 60:
            return 10.0 - (price - 30) / 10.0
        elif price <= 100:
            return 7.0 - (price - 60) / 20.0
        else:
            return max(3.0, 5.0 - (price - 100) / 50.0)

    def _score_quality(self, product: Dict) -> float:
        """质量得分（基于评分和标签）"""
        rating = product.get("rating", 4.0)
        tags = product.get("tags", [])

        # 基础分（评分转换）
        base_score = rating * 2  # 5 分制转 10 分制

        # 质量标签加分
        quality_tags = ["有机", "进口", "精选", "高端", "品质"]
        bonus = sum(1 for tag in tags if tag in quality_tags)

        return min(10.0, base_score + bonus)

    def _score_popularity(self, product: Dict) -> float:
        """热度得分（基于销量）"""
        sales = product.get("sales_count", 0)
        # 销量得分：1000+ 为 10 分，线性插值
        return min(10.0, sales / 100.0)

    def _score_freshness(self, product: Dict) -> float:
        """新鲜度得分（基于保质期和类别）"""
        shelf_life = product.get("shelf_life", "")
        tags = product.get("tags", [])

        # 短保质期但标明"新鲜"的得分高
        if "新鲜" in tags or "当季" in tags:
            return 9.0
        elif "鲜活" in tags:
            return 10.0
        elif "冷冻" in shelf_life or "天" in shelf_life:
            return 7.0
        else:
            return 5.0

    async def _step_generate_reasons(
        self,
        compared: List[Dict],
        user_intent: Dict,
        trace_id: str
    ) -> List[Dict[str, Any]]:
        """Step 4: 生成推荐理由"""
        self.logger.info(f"[{trace_id}] Step 4: 生成推荐理由")

        for product in compared:
            reasons = []

            # 基于标签生成理由
            tags = product.get("tags", [])
            if "有机" in tags:
                reasons.append("有机种植，安全健康")
            if "进口" in tags:
                reasons.append("进口品质，值得信赖")
            if "当季" in tags:
                reasons.append("当季新鲜，口感最佳")
            if "新鲜" in tags:
                reasons.append("新鲜采摘/生产")

            # 基于评分生成理由
            if product.get("rating", 0) >= 4.8:
                reasons.append(f"高评分商品（{product.get('rating', 0)}⭐）")

            # 基于销量生成理由
            if product.get("sales_count", 0) >= 1000:
                reasons.append(f"热销 {product.get('sales_count', 0)}+ 件")

            # 基于价格生成理由
            original = product.get("price", 0)
            group = product.get("group_price", 0)
            if original > group:
                discount = ((original - group) / original) * 100
                reasons.append(f"成团优惠 {discount:.0f}%")

            # 基于用户偏好生成理由
            implicit_prefs = user_intent.get("implicit_preferences", [])
            if "性价比高" in implicit_prefs and product.get("score", 0) >= 8:
                reasons.append("符合您的性价比偏好")

            product["reasons"] = reasons
            product["reason"] = "；".join(reasons[:3]) if reasons else "综合推荐"

        return compared

    async def _step_predict_probability(
        self,
        with_reasons: List[Dict],
        community_id: Optional[str],
        trace_id: str
    ) -> List[Dict[str, Any]]:
        """Step 5: 预测成团概率"""
        self.logger.info(f"[{trace_id}] Step 5: 预测成团概率")

        for product in with_reasons:
            # 基于历史数据预测成团概率
            probability = self._calculate_group_probability(product, community_id)
            product["success_probability"] = probability

        return with_reasons

    def _calculate_group_probability(self, product: Dict, community_id: Optional[str]) -> float:
        """计算成团概率"""
        # 基础概率（基于商品热度）
        base_prob = 60.0

        # 销量加成
        sales = product.get("sales_count", 0)
        if sales >= 3000:
            base_prob += 25
        elif sales >= 1000:
            base_prob += 15
        elif sales >= 500:
            base_prob += 10

        # 评分加成
        rating = product.get("rating", 4.0)
        if rating >= 4.8:
            base_prob += 10
        elif rating >= 4.5:
            base_prob += 5

        # 价格加成（适中价格更容易成团）
        price = product.get("group_price", 50)
        if 25 <= price <= 60:
            base_prob += 5

        return min(98.0, base_prob)

    async def _step_rank_and_return(
        self,
        with_probability: List[Dict],
        limit: int,
        trace_id: str
    ) -> List[Dict[str, Any]]:
        """Step 6: 排序并返回 Top-N"""
        self.logger.info(f"[{trace_id}] Step 6: 排序并返回 Top-{limit}")

        # 按综合得分排序
        with_probability.sort(key=lambda x: x["score"], reverse=True)

        # 返回 Top-N
        result = with_probability[:limit]

        # 添加排序说明
        if result:
            result[0]["is_top_recommendation"] = True
            result[0]["recommendation_reason"] = "综合得分最高，最符合您的需求"

        return result


# 工作流工厂
def create_auto_select_product_workflow(db_session: Optional[Any] = None) -> AutoSelectProductWorkflow:
    """创建智能选品工作流实例"""
    return AutoSelectProductWorkflow(db_session=db_session)
