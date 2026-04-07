"""
主动邀请工作流

流程：
1. 分析团购特征
2. 识别潜在参团者
3. 计算参团概率
4. 生成个性化邀请
5. 发送邀请并追踪
6. 更新成团预测
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AutoInviteWorkflow:
    """
    主动邀请工作流

    基于团购特征和用户画像，智能识别并邀请潜在参团者。
    """

    def __init__(self, db_session: Optional[Any] = None):
        self.db = db_session
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute(
        self,
        group_id: str,
        product_id: str,
        product_name: str,
        community_id: Optional[str] = None,
        target_count: int = 10,
        creator_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行主动邀请工作流

        Args:
            group_id: 团购 ID
            product_id: 商品 ID
            product_name: 商品名称
            community_id: 社区 ID
            target_count: 目标邀请人数
            creator_id: 创建者 ID

        Returns:
            Dict: 邀请结果，包含邀请统计和成团概率变化
        """
        trace_id = f"ai_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.logger.info(f"[{trace_id}] 主动邀请工作流开始执行")

        try:
            # Step 1: 分析团购特征
            group_profile = await self._step_analyze_group(
                group_id, product_id, product_name, trace_id
            )

            # Step 2: 识别潜在参团者
            candidates = await self._step_identify_candidates(
                group_profile, community_id, target_count, trace_id
            )

            # Step 3: 计算参团概率
            scored_candidates = await self._step_calculate_join_probability(
                candidates, group_profile, trace_id
            )

            # Step 4: 选择最优邀请集合
            selected = await self._step_select_invitees(
                scored_candidates, target_count, trace_id
            )

            # Step 5: 生成个性化邀请内容
            invitations = await self._step_generate_invitations(
                selected, group_profile, creator_id, trace_id
            )

            # Step 6: 发送邀请
            send_result = await self._step_send_invitations(invitations, trace_id)

            # Step 7: 更新成团概率预测
            probability_update = await self._step_update_probability(
                send_result, group_profile, trace_id
            )

            self.logger.info(f"[{trace_id}] 主动邀请工作流执行完成")

            return {
                "invited_count": send_result.get("invited_count", 0),
                "expected_joins": send_result.get("expected_joins", 0),
                "probability_before": probability_update.get("before", 0),
                "probability_after": probability_update.get("after", 0),
                "probability_increase": probability_update.get("increase", 0),
                "top_candidates": [
                    {"user_id": c["user_id"], "name": c["name"], "probability": c["join_probability"]}
                    for c in scored_candidates[:5]
                ],
                "trace_id": trace_id
            }

        except Exception as e:
            self.logger.error(f"[{trace_id}] 工作流执行失败：{str(e)}")
            raise

    async def _step_analyze_group(
        self,
        group_id: str,
        product_id: str,
        product_name: str,
        trace_id: str
    ) -> Dict[str, Any]:
        """Step 1: 分析团购特征"""
        self.logger.info(f"[{trace_id}] Step 1: 分析团购特征")

        # 商品类别推断
        category_keywords = {
            "水果": ["草莓", "芒果", "蓝莓", "葡萄", "苹果", "香蕉", "西瓜"],
            "蔬菜": ["蔬菜", "青菜", "番茄", "黄瓜"],
            "肉类": ["牛肉", "猪肉", "羊肉", "鸡肉"],
            "海鲜": ["蟹", "虾", "鱼", "海鲜"],
            "乳品": ["牛奶", "酸奶", "奶酪"],
            "零食": ["坚果", "饼干", "零食"],
            "粮油": ["大米", "面粉", "油"]
        }

        category = "其他"
        for cat, keywords in category_keywords.items():
            if any(kw in product_name for kw in keywords):
                category = cat
                break

        # 价格区间分析
        price_level = "medium"  # 简化处理

        # 团购特征
        profile = {
            "group_id": group_id,
            "product_id": product_id,
            "product_name": product_name,
            "category": category,
            "price_level": price_level,
            "appeal_factors": self._get_appeal_factors(category)
        }

        self.logger.info(f"[{trace_id}] 团购特征：{profile}")
        return profile

    def _get_appeal_factors(self, category: str) -> List[str]:
        """获取商品吸引力因素"""
        factors_map = {
            "水果": ["新鲜", "健康", "当季", "维生素"],
            "蔬菜": ["健康", "有机", "新鲜", "低卡"],
            "肉类": ["高蛋白", "营养", "美味"],
            "海鲜": ["高蛋白", "新鲜", "营养", "稀缺"],
            "乳品": ["营养", "健康", "日常必备"],
            "零食": ["美味", "休闲", "分享"],
            "粮油": ["刚需", "家庭必备", "实惠"]
        }
        return factors_map.get(category, ["实惠", "精选"])

    async def _step_identify_candidates(
        self,
        group_profile: Dict,
        community_id: Optional[str],
        target_count: int,
        trace_id: str
    ) -> List[Dict[str, Any]]:
        """Step 2: 识别潜在参团者"""
        self.logger.info(f"[{trace_id}] Step 2: 识别潜在参团者")

        # 简化实现：返回模拟候选用户
        # 实际实现应从数据库查询用户画像和行为历史

        candidates = self._get_simulated_candidates(group_profile, target_count)

        self.logger.info(f"[{trace_id}] 找到 {len(candidates)} 个候选用户")
        return candidates

    def _get_simulated_candidates(self, group_profile: Dict, target_count: int) -> List[Dict]:
        """获取模拟候选用户"""
        # 基于商品类别生成有偏好的候选用户
        category = group_profile.get("category", "其他")

        # 用户画像模板
        user_profiles = [
            {"name": "王阿姨", "偏好": ["水果", "蔬菜", "生鲜"], "活跃度": "high", "历史参团": 25},
            {"name": "小李", "偏好": ["零食", "饮料", "水果"], "活跃度": "medium", "历史参团": 12},
            {"name": "张姐", "偏好": ["肉类", "海鲜", "粮油"], "活跃度": "high", "历史参团": 30},
            {"name": "小陈", "偏好": ["乳品", "早餐", "水果"], "活跃度": "medium", "历史参团": 8},
            {"name": "老刘", "偏好": ["粮油", "肉类", "蔬菜"], "活跃度": "low", "历史参团": 5},
            {"name": "小美", "偏好": ["水果", "零食", "海鲜"], "活跃度": "high", "历史参团": 18},
            {"name": "大伟", "偏好": ["肉类", "饮料", "零食"], "活跃度": "medium", "历史参团": 10},
            {"name": "芳芳", "偏好": ["蔬菜", "水果", "乳品"], "活跃度": "medium", "历史参团": 15},
            {"name": "赵哥", "偏好": ["海鲜", "肉类", "粮油"], "活跃度": "high", "历史参团": 22},
            {"name": "小周", "偏好": ["零食", "水果", "饮料"], "活跃度": "low", "历史参团": 3},
            {"name": "吴姐", "偏好": ["蔬菜", "粮油", "肉类"], "活跃度": "medium", "历史参团": 14},
            {"name": "郑哥", "偏好": ["水果", "海鲜", "饮料"], "活跃度": "high", "历史参团": 20}
        ]

        # 根据类别筛选和排序
        def match_score(profile):
            score = 0
            if category in profile["偏好"]:
                score += 3
            if profile["活跃度"] == "high":
                score += 2
            elif profile["活跃度"] == "medium":
                score += 1
            score += profile["历史参团"] / 10
            return score

        sorted_profiles = sorted(user_profiles, key=match_score, reverse=True)

        # 生成候选列表
        candidates = []
        for i, profile in enumerate(sorted_profiles[:target_count * 2]):
            candidates.append({
                "user_id": f"u{i+1:03d}",
                "name": profile["name"],
                "preferences": profile["偏好"],
                "activity_level": profile["活跃度"],
                "history_join_count": profile["历史参团"],
                "match_score": match_score(profile)
            })

        return candidates

    async def _step_calculate_join_probability(
        self,
        candidates: List[Dict],
        group_profile: Dict,
        trace_id: str
    ) -> List[Dict[str, Any]]:
        """Step 3: 计算参团概率"""
        self.logger.info(f"[{trace_id}] Step 3: 计算参团概率")

        scored = []
        for candidate in candidates:
            probability = self._calculate_join_probability(candidate, group_profile)
            scored.append({
                **candidate,
                "join_probability": probability,
                "probability_factors": self._get_probability_factors(candidate, group_profile)
            })

        # 按概率排序
        scored.sort(key=lambda x: x["join_probability"], reverse=True)

        return scored

    def _calculate_join_probability(self, candidate: Dict, group_profile: Dict) -> float:
        """计算单个用户的参团概率"""
        base_prob = 30.0  # 基础概率

        category = group_profile.get("category", "其他")

        # 类别匹配加成
        if category in candidate.get("preferences", []):
            base_prob += 35
        else:
            # 相关类别也有部分加成
            related = self._get_related_categories(category)
            if any(r in candidate.get("preferences", []) for r in related):
                base_prob += 15

        # 活跃度加成
        activity = candidate.get("activity_level", "low")
        if activity == "high":
            base_prob += 20
        elif activity == "medium":
            base_prob += 10

        # 历史参团数加成
        history = candidate.get("history_join_count", 0)
        if history >= 20:
            base_prob += 15
        elif history >= 10:
            base_prob += 10
        elif history >= 5:
            base_prob += 5

        # 匹配分数加成
        match_score = candidate.get("match_score", 0)
        base_prob += match_score * 2

        return min(95.0, base_prob)

    def _get_related_categories(self, category: str) -> List[str]:
        """获取相关类别"""
        related_map = {
            "水果": ["零食", "乳品"],
            "蔬菜": ["粮油", "肉类"],
            "肉类": ["蔬菜", "粮油", "海鲜"],
            "海鲜": ["肉类", "蔬菜"],
            "乳品": ["早餐", "零食", "水果"],
            "零食": ["水果", "饮料"],
            "粮油": ["蔬菜", "肉类"]
        }
        return related_map.get(category, [])

    def _get_probability_factors(self, candidate: Dict, group_profile: Dict) -> List[str]:
        """获取影响概率的因素"""
        factors = []

        category = group_profile.get("category", "其他")

        if category in candidate.get("preferences", []):
            factors.append(f"偏好匹配：喜欢{category}")

        if candidate.get("activity_level") == "high":
            factors.append("活跃用户")

        history = candidate.get("history_join_count", 0)
        if history >= 20:
            factors.append(f"参团达人（{history}次）")
        elif history >= 10:
            factors.append(f"经常参团（{history}次）")

        return factors

    async def _step_select_invitees(
        self,
        scored_candidates: List[Dict],
        target_count: int,
        trace_id: str
    ) -> List[Dict[str, Any]]:
        """Step 4: 选择最优邀请集合"""
        self.logger.info(f"[{trace_id}] Step 4: 选择最优邀请集合")

        # 选择概率最高的用户
        selected = scored_candidates[:target_count]

        # 计算预期参团人数
        expected_joins = sum(c["join_probability"] / 100 for c in selected)

        self.logger.info(f"[{trace_id}] 选择 {len(selected)} 人，预期 {expected_joins:.1f} 人参团")

        for c in selected:
            c["selected"] = True
            c["expected_contribution"] = c["join_probability"] / 100

        return selected

    async def _step_generate_invitations(
        self,
        selected: List[Dict],
        group_profile: Dict,
        creator_id: Optional[str],
        trace_id: str
    ) -> List[Dict[str, Any]]:
        """Step 5: 生成个性化邀请内容"""
        self.logger.info(f"[{trace_id}] Step 5: 生成个性化邀请内容")

        invitations = []
        for candidate in selected:
            invitation = self._generate_personalized_invitation(
                candidate, group_profile, creator_id
            )
            invitations.append({
                **candidate,
                "invitation_content": invitation
            })

        return invitations

    def _generate_personalized_invitation(
        self,
        candidate: Dict,
        group_profile: Dict,
        creator_id: Optional[str]
    ) -> str:
        """生成个性化邀请内容"""
        product_name = group_profile.get("product_name", "精选商品")
        category = group_profile.get("category", "精选")
        name = candidate.get("name", "邻居")

        # 基于用户偏好生成个性化文案
        if category in candidate.get("preferences", []):
            template = (
                f"【团购邀请】{name}您好！发现一款您可能喜欢的{category}——{product_name}，"
                f"成团超优惠！邻居们已经参加了，快来看看吧！"
            )
        elif candidate.get("activity_level") == "high":
            template = (
                f"【团购邀请】{name}您好！社区新开了一个{product_name}团购，"
                f"您可是我们的团购达人，快来带带节奏！"
            )
        else:
            template = (
                f"【团购邀请】{name}您好！社区热门团购{product_name}正在成团中，"
                f"价格超值，不要错过哦！"
            )

        return template

    async def _step_send_invitations(
        self,
        invitations: List[Dict],
        trace_id: str
    ) -> Dict[str, Any]:
        """Step 6: 发送邀请"""
        self.logger.info(f"[{trace_id}] Step 6: 发送邀请")

        # 模拟发送
        invited_count = len(invitations)
        expected_joins = sum(i.get("expected_contribution", 0) for i in invitations)

        # 记录发送结果
        for inv in invitations:
            inv["sent"] = True
            inv["sent_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.logger.info(f"[{trace_id}] 发送 {invited_count} 封邀请，预期 {expected_joins:.1f} 人参团")

        return {
            "invited_count": invited_count,
            "expected_joins": round(expected_joins, 1),
            "invitations": invitations
        }

    async def _step_update_probability(
        self,
        send_result: Dict,
        group_profile: Dict,
        trace_id: str
    ) -> Dict[str, Any]:
        """Step 7: 更新成团概率预测"""
        self.logger.info(f"[{trace_id}] Step 7: 更新成团概率预测")

        # 简化实现
        before_prob = 50.0  # 邀请前基础概率
        expected_joins = send_result.get("expected_joins", 0)

        # 邀请后概率提升
        increase = min(30.0, expected_joins * 5)  # 最多提升 30%
        after_prob = min(95.0, before_prob + increase)

        self.logger.info(f"[{trace_id}] 成团概率：{before_prob}% -> {after_prob}% (+{increase}%)")

        return {
            "before": round(before_prob, 1),
            "after": round(after_prob, 1),
            "increase": round(increase, 1)
        }


# 工作流工厂
def create_auto_invite_workflow(db_session: Optional[Any] = None) -> AutoInviteWorkflow:
    """创建主动邀请工作流实例"""
    return AutoInviteWorkflow(db_session=db_session)
