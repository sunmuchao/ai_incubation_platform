"""
团购智能体 - GroupBuyAgent

基于 DeerFlow 2.0 的团购领域 Agent，实现自主选品、主动邀请、智能成团等功能。
"""
import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from agents.deerflow_client import DeerFlowClient, WorkflowResult

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent 状态"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentContext:
    """Agent 执行上下文"""
    user_id: str
    session_id: str
    request_id: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    user_profile: Optional[Dict[str, Any]] = None
    community_id: Optional[str] = None


@dataclass
class AgentResponse:
    """Agent 响应"""
    success: bool
    message: str
    action: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.0

    @classmethod
    def reply(cls, message: str, suggestions: List[str] = None, data: Dict = None, confidence: float = 0.0) -> "AgentResponse":
        return cls(
            success=True,
            message=message,
            data=data,
            suggestions=suggestions or [],
            confidence=confidence
        )

    @classmethod
    def error(cls, message: str) -> "AgentResponse":
        return cls(success=False, message=message, confidence=0.0)


class GroupBuyAgent:
    """
    团购智能体

    核心能力：
    1. 需求理解 - 理解用户自然语言需求
    2. 自主选品 - 主动搜索并推荐商品
    3. 主动邀请 - 分析并邀请潜在参团者
    4. 成团预测 - 预测成团概率并优化策略
    5. 履约调度 - 智能安排配送
    """

    def __init__(self, client: DeerFlowClient, db_session: Optional[Any] = None):
        self.client = client
        self.db = db_session
        self.state = AgentState.IDLE
        self.context: Optional[AgentContext] = None
        self.logger = logging.getLogger(self.__class__.__name__)

        # 注册本地工作流和工具（用于降级模式）
        self._register_local_workflows()
        self._register_local_tools()

    def _register_local_workflows(self) -> None:
        """注册本地工作流"""
        self.client.register_local_workflow("auto_create_group", self._local_auto_create_group)
        self.client.register_local_workflow("auto_select_product", self._local_auto_select_product)
        self.client.register_local_workflow("auto_invite", self._local_auto_invite)

    def _register_local_tools(self) -> None:
        """注册本地工具"""
        self.client.register_local_tool("search_products", self._local_search_products)
        self.client.register_local_tool("create_group_buy", self._local_create_group_buy)
        self.client.register_local_tool("invite_members", self._local_invite_members)
        self.client.register_local_tool("predict_group_success", self._local_predict_group_success)

    async def chat(self, user_input: str, context: AgentContext) -> AgentResponse:
        """
        对话式交互入口

        Args:
            user_input: 用户输入
            context: 对话上下文

        Returns:
            AgentResponse: Agent 响应
        """
        self.context = context
        self.state = AgentState.THINKING

        try:
            # 1. 理解用户意图
            intent = await self._understand_intent(user_input)
            self.logger.info(f"意图识别结果：{intent}")

            # 2. 根据意图选择执行策略
            if intent["type"] == "create_group":
                return await self._handle_create_group(intent, user_input)
            elif intent["type"] == "find_product":
                return await self._handle_find_product(intent, user_input)
            elif intent["type"] == "check_status":
                return await self._handle_check_status(intent)
            elif intent["type"] == "general_query":
                return await self._handle_general_query(intent, user_input)
            else:
                return AgentResponse.reply(
                    message="我还没太理解您的需求，您可以试着问我：\n- 帮我找个水果团购\n- 我想买牛奶\n- 我的团购进度怎么样了",
                    suggestions=[
                        "帮我找个水果团购",
                        "我想买牛奶",
                        "查看我的团购进度",
                        "有什么好吃的推荐"
                    ],
                    confidence=0.5
                )

        except Exception as e:
            self.logger.error(f"对话处理异常：{str(e)}")
            return AgentResponse.error(f"处理您的请求时出现了问题，请稍后重试")

        finally:
            self.state = AgentState.IDLE

    async def _understand_intent(self, user_input: str) -> Dict[str, Any]:
        """理解用户意图"""
        # 简单的关键词匹配（实际应使用 LLM）
        user_input_lower = user_input.lower()

        # 创建团购相关
        if any(kw in user_input_lower for kw in ["发起", "创建", "开团", "团购"]):
            return {
                "type": "create_group",
                "keywords": self._extract_keywords(user_input)
            }

        # 查找商品相关
        if any(kw in user_input_lower for kw in ["找", "买", "要", "想", "需要", "推荐"]):
            return {
                "type": "find_product",
                "keywords": self._extract_keywords(user_input),
                "category": self._extract_category(user_input)
            }

        # 查询状态相关
        if any(kw in user_input_lower for kw in ["进度", "状态", "怎么样", "如何", "查看"]):
            return {
                "type": "check_status",
                "keywords": self._extract_keywords(user_input)
            }

        # 通用查询
        return {
            "type": "general_query",
            "keywords": self._extract_keywords(user_input)
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的中文分词（实际应使用更好的分词工具）
        keywords = []
        category_words = ["水果", "蔬菜", "肉类", "海鲜", "牛奶", "鸡蛋", "零食", "饮料", "粮油", "调味", "生鲜", "食品"]
        for word in category_words:
            if word in text:
                keywords.append(word)
        return keywords

    def _extract_category(self, text: str) -> Optional[str]:
        """提取商品类别"""
        category_map = {
            "水果": "fruit",
            "蔬菜": "vegetable",
            "肉类": "meat",
            "海鲜": "seafood",
            "牛奶": "dairy",
            "鸡蛋": "egg",
            "零食": "snack",
            "饮料": "beverage",
            "粮油": "grain",
            "生鲜": "fresh"
        }
        for cn, en in category_map.items():
            if cn in text:
                return en
        return None

    async def _handle_create_group(self, intent: Dict, user_input: str) -> AgentResponse:
        """处理创建团购请求"""
        self.state = AgentState.EXECUTING

        # 调用工作流自主创建团购
        result = await self.client.run_workflow(
            "auto_create_group",
            user_input=user_input,
            user_id=self.context.user_id,
            community_id=self.context.community_id
        )

        if result.success:
            group_data = result.data.get("group", {})
            return AgentResponse.reply(
                message=f"好的！我已经为您发起了【{group_data.get('product_name', '精选商品')}】的团购！\n\n"
                        f"成团价：¥{group_data.get('group_price', 0)}\n"
                        f"目标人数：{group_data.get('min_participants', 10)}人\n"
                        f"截止时间：{group_data.get('deadline', '今晚 24:00')}\n\n"
                        f"我已经自动邀请了 {result.data.get('invited_count', 0)} 位可能感兴趣的邻居，"
                        f"预计成团概率为 {result.data.get('success_probability', 80)}%！",
                suggestions=[
                    "查看团购详情",
                    "分享给更多邻居",
                    "再发起一个团购"
                ],
                data=group_data,
                confidence=0.9
            )
        else:
            return AgentResponse.error(f"创建团购失败：{result.error or '请稍后重试'}")

    async def _handle_find_product(self, intent: Dict, user_input: str) -> AgentResponse:
        """处理查找商品请求"""
        self.state = AgentState.EXECUTING

        # 调用工作流智能选品
        result = await self.client.run_workflow(
            "auto_select_product",
            query=user_input,
            category=intent.get("category"),
            keywords=intent.get("keywords", []),
            user_id=self.context.user_id,
            community_id=self.context.community_id
        )

        if result.success:
            products = result.data.get("products", [])
            if not products:
                return AgentResponse.reply(
                    message="抱歉，暂时没有找到符合您需求的商品。您可以试试搜索其他关键词~",
                    suggestions=[
                        "看看热门商品",
                        "查看今日特价",
                        "浏览全部商品"
                    ],
                    confidence=0.6
                )

            # 构建商品推荐消息
            message = f"我为您找到了 {len(products)} 款商品：\n\n"
            for i, p in enumerate(products[:3], 1):
                message += f"{i}. {p.get('name', '未知商品')}\n"
                message += f"   价格：¥{p.get('price', 0)} | 成团价：¥{p.get('group_price', 0)}\n"
                message += f"   推荐理由：{p.get('reason', '精选商品')}\n"
                message += f"   成团概率：{p.get('success_probability', 70)}%\n\n"

            message += "您想发起哪个商品的团购？或者我可以为您详细介绍某一款~"

            return AgentResponse.reply(
                message=message,
                suggestions=[
                    f"发起【{products[0].get('name', '商品')}】团购",
                    "详细介绍第一款",
                    "再看看其他商品"
                ],
                data={"products": products},
                confidence=0.85
            )
        else:
            return AgentResponse.error(f"查找商品失败：{result.error or '请稍后重试'}")

    async def _handle_check_status(self, intent: Dict) -> AgentResponse:
        """处理状态查询请求"""
        self.state = AgentState.EXECUTING

        # TODO: 查询用户参与的团购状态
        groups = await self._get_user_groups()

        if not groups:
            return AgentResponse.reply(
                message="您目前没有参与任何进行中的团购。\n\n"
                        "我可以帮您：\n"
                        "- 浏览正在进行的热门团购\n"
                        "- 根据您的需求发起新团购",
                suggestions=[
                    "看看热门团购",
                    "我想买水果",
                    "发起新团购"
                ],
                confidence=0.7
            )

        message = "您参与的团购：\n\n"
        for g in groups[:3]:
            progress = g.get("current_participants", 0) / max(g.get("min_participants", 1), 1) * 100
            message += f"【{g.get('product_name', '商品')}】\n"
            message += f"进度：{g.get('current_participants', 0)}/{g.get('min_participants', 1)}人 ({progress:.0f}%)\n"
            message += f"状态：{g.get('status', '进行中')}\n"
            message += f"预计成团时间：{g.get('estimated_complete_time', '未知')}\n\n"

        return AgentResponse.reply(
            message=message,
            suggestions=["邀请邻居参团", "查看团购详情"],
            data={"groups": groups},
            confidence=0.9
        )

    async def _handle_general_query(self, intent: Dict, user_input: str) -> AgentResponse:
        """处理通用查询"""
        # 根据上下文提供智能回复
        return AgentResponse.reply(
            message="我理解您可能想了解商品信息或发起团购。\n\n"
                    "您可以这样问我：\n"
                    "- '我想买点新鲜的水果'\n"
                    "- '帮我找个牛奶团购'\n"
                    "- '发起一个零食团购'",
            suggestions=[
                "我想买点水果",
                "帮我找个牛奶团购",
                "发起一个零食团购"
            ],
            confidence=0.5
        )

    async def _get_user_groups(self) -> List[Dict]:
        """获取用户参与的团购"""
        # TODO: 从数据库查询
        if self.db:
            # 实际查询逻辑
            pass

        # 返回模拟数据
        return [
            {
                "product_name": "有机草莓",
                "current_participants": 15,
                "min_participants": 20,
                "status": "进行中",
                "estimated_complete_time": "今晚 20:00"
            }
        ]

    # ==================== 本地工作流实现（降级模式）====================

    async def _local_auto_create_group(self, **kwargs) -> Dict[str, Any]:
        """本地自动创建团购工作流"""
        # 模拟创建团购流程
        return {
            "group": {
                "product_name": "精选水果礼盒",
                "group_price": 59.9,
                "min_participants": 10,
                "deadline": "2026-04-07 00:00:00"
            },
            "invited_count": 8,
            "success_probability": 85
        }

    async def _local_auto_select_product(self, **kwargs) -> Dict[str, Any]:
        """本地自动选品工作流"""
        # 模拟选品流程
        return {
            "products": [
                {
                    "name": "海南芒果",
                    "price": 39.9,
                    "group_price": 29.9,
                    "reason": "当季热带水果，甜度高核小",
                    "success_probability": 88
                },
                {
                    "name": "有机草莓",
                    "price": 49.9,
                    "group_price": 35.9,
                    "reason": "有机种植，新鲜采摘",
                    "success_probability": 75
                },
                {
                    "name": "进口蓝莓",
                    "price": 59.9,
                    "group_price": 45.9,
                    "reason": "富含花青素，护眼健康",
                    "success_probability": 82
                }
            ]
        }

    async def _local_auto_invite(self, **kwargs) -> Dict[str, Any]:
        """本地自动邀请工作流"""
        return {
            "invited_count": 10,
            "expected_join_count": 7,
            "success_probability_increase": 25
        }

    # ==================== 本地工具实现（降级模式）====================

    def _local_search_products(self, **kwargs) -> Dict[str, Any]:
        """本地商品搜索工具"""
        return {"products": [], "total": 0}

    def _local_create_group_buy(self, **kwargs) -> Dict[str, Any]:
        """本地创建团购工具"""
        return {"group_id": "mock_group_001", "status": "created"}

    def _local_invite_members(self, **kwargs) -> Dict[str, Any]:
        """本地邀请成员工具"""
        return {"invited_count": 5, "success": True}

    def _local_predict_group_success(self, **kwargs) -> Dict[str, Any]:
        """本地成团预测工具"""
        return {"probability": 0.75, "confidence": "medium"}


# Agent 工厂
def create_groupbuy_agent(db_session: Optional[Any] = None) -> GroupBuyAgent:
    """创建团购 Agent 实例"""
    client = DeerFlowClient()
    return GroupBuyAgent(client=client, db_session=db_session)
