"""
对话理解工具 - 自然语言意图识别和槽位填充

将用户自然语言转换为结构化意图，供 Agent 决策使用。
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from tools.base import BaseTool, ToolMetadata, ToolResponse

logger = logging.getLogger(__name__)


class IntentRecognitionTool(BaseTool):
    """意图识别工具"""

    def __init__(self, db_session: Optional[Any] = None):
        super().__init__()
        self.db = db_session
        # 意图分类体系
        self.intent_categories = {
            "create_group": {
                "keywords": ["发起", "创建", "开团", "团购", "拼团", "组织"],
                "description": "创建新的团购活动"
            },
            "find_product": {
                "keywords": ["找", "买", "要", "想", "需要", "推荐", "看看", "浏览"],
                "description": "查找或推荐商品"
            },
            "check_status": {
                "keywords": ["进度", "状态", "怎么样", "如何", "查看", "查询", "我的"],
                "description": "查询团购状态或订单信息"
            },
            "join_group": {
                "keywords": ["参加", "加入", "参团", "拼一个", "我要买"],
                "description": "加入已有团购"
            },
            "cancel_group": {
                "keywords": ["取消", "退款", "退团", "不买了"],
                "description": "取消团购或订单"
            },
            "general_chat": {
                "keywords": ["你好", "谢谢", "再见", "在吗", "help", "帮助"],
                "description": "通用对话"
            }
        }

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="intent_recognition",
            description="识别用户自然语言中的意图，支持团购相关场景",
            version="1.0.0",
            tags=["nlp", "intent", "ai", "conversation"],
            author="ai-community-buying"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "用户输入的文本"
                },
                "user_id": {
                    "type": "string",
                    "description": "用户 ID（用于个性化识别）"
                },
                "context": {
                    "type": "object",
                    "description": "对话上下文",
                    "properties": {
                        "last_intent": {
                            "type": "string",
                            "description": "上一轮识别的意图"
                        },
                        "slot_values": {
                            "type": "object",
                            "description": "已填充的槽位值"
                        }
                    }
                }
            },
            "required": ["text"]
        }

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """执行意图识别"""
        request_id = context.get("request_id") if context else None

        try:
            text = params.get("text", "")
            user_id = params.get("user_id")
            dialog_context = params.get("context", {})

            # 意图识别
            intent = self._recognize_intent(text, dialog_context)

            # 槽位提取
            slots = self._extract_slots(text, intent)

            # 置信度计算
            confidence = self._calculate_confidence(intent, text, slots)

            result = {
                "intent": intent,
                "slots": slots,
                "confidence": confidence,
                "text": text,
                "user_id": user_id
            }

            self.logger.info(f"[{request_id}] 意图识别结果：{intent} (置信度：{confidence})")

            return ToolResponse.ok(data=result, request_id=request_id)

        except Exception as e:
            self.logger.error(f"[{request_id}] 意图识别失败：{str(e)}")
            return ToolResponse.fail(error=str(e), request_id=request_id)

    def _recognize_intent(self, text: str, context: Dict) -> str:
        """识别用户意图"""
        text_lower = text.lower()

        # 关键词匹配
        intent_scores = {}
        for intent, config in self.intent_categories.items():
            score = sum(1 for kw in config["keywords"] if kw in text_lower)
            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return "general_chat"

        # 返回得分最高的意图
        return max(intent_scores.keys(), key=lambda x: intent_scores[x])

    def _extract_slots(self, text: str, intent: str) -> Dict[str, Any]:
        """提取槽位信息"""
        slots = {}

        # 商品类别槽位
        category_map = {
            "水果": ["水果", "苹果", "香蕉", "橙子", "草莓", "葡萄", "西瓜", "芒果", "樱桃"],
            "蔬菜": ["蔬菜", "青菜", "土豆", "番茄", "黄瓜", "萝卜", "白菜"],
            "肉类": ["肉类", "猪肉", "牛肉", "羊肉", "鸡肉", "排骨"],
            "海鲜": ["海鲜", "鱼", "虾", "蟹", "贝类"],
            "乳品": ["牛奶", "酸奶", "奶酪", "奶粉"],
            "零食": ["零食", "饼干", "坚果", "糖果", "薯片"],
            "粮油": ["大米", "面粉", "油", "杂粮"]
        }

        for category, keywords in category_map.items():
            if any(kw in text for kw in keywords):
                slots["category"] = category
                slots["matched_keywords"] = [kw for kw in keywords if kw in text]
                break

        # 价格槽位
        import re
        price_patterns = [
            (r"(\d+(?:\.\d+)?)?元", "price"),
            (r"(\d+(?:\.\d+)?)?块", "price"),
            (r"(\d+(?:\.\d+)?)?块钱", "price"),
            (r"便宜 | 实惠 | 低价 | 划算", "price_preference_low"),
            (r"高档 | 精品 | 进口 | 高端 | 品质", "price_preference_high")
        ]

        for pattern, slot_name in price_patterns:
            if re.search(pattern, text):
                if slot_name == "price":
                    match = re.search(pattern, text)
                    if match:
                        slots["price"] = float(match.group(1)) if match.group(1) else None
                else:
                    slots["price_preference"] = slot_name.replace("price_preference_", "")

        # 数量槽位
        quantity_patterns = [
            (r"(\d+) 个", "count"),
            (r"(\d+) 斤", "weight"),
            (r"(\d+) 箱", "box"),
            (r"多一些 | 多一点", "quantity_more"),
            (r"少一些 | 少一点", "quantity_less")
        ]

        for pattern, slot_name in quantity_patterns:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                if match and slot_name == "count":
                    slots["quantity"] = int(match.group(1))
                else:
                    slots["quantity_preference"] = slot_name.replace("quantity_", "")

        # 时间槽位
        if any(kw in text for kw in ["今天", "今日", "马上", "现在", "尽快"]):
            slots["urgency"] = "high"
        elif any(kw in text for kw in ["明天", "后天", "过几天"]):
            slots["urgency"] = "low"

        return slots

    def _calculate_confidence(self, intent: str, text: str, slots: Dict) -> float:
        """计算置信度"""
        base_confidence = 0.5

        # 意图关键词匹配度
        if intent in self.intent_categories:
            keywords = self.intent_categories[intent]["keywords"]
            match_count = sum(1 for kw in keywords if kw in text.lower())
            base_confidence += min(0.3, match_count * 0.1)

        # 槽位填充度
        if slots:
            base_confidence += min(0.2, len(slots) * 0.05)

        # 文本长度因素（太短可能信息不足）
        if len(text) < 5:
            base_confidence -= 0.1
        elif len(text) > 50:
            base_confidence += 0.05

        return min(0.98, max(0.1, base_confidence))


class EntityExtractionTool(BaseTool):
    """实体抽取工具"""

    def __init__(self, db_session: Optional[Any] = None):
        super().__init__()
        self.db = db_session

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="entity_extraction",
            description="从文本中抽取团购相关的命名实体",
            version="1.0.0",
            tags=["nlp", "ner", "ai", "extraction"],
            author="ai-community-buying"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "待抽取的文本"
                }
            },
            "required": ["text"]
        }

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """执行实体抽取"""
        request_id = context.get("request_id") if context else None

        try:
            text = params.get("text", "")
            entities = self._extract_entities(text)

            return ToolResponse.ok(data={"entities": entities}, request_id=request_id)

        except Exception as e:
            self.logger.error(f"[{request_id}] 实体抽取失败：{str(e)}")
            return ToolResponse.fail(error=str(e), request_id=request_id)

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """抽取实体"""
        entities = []

        # 商品实体
        product_keywords = ["草莓", "芒果", "蓝莓", "苹果", "香蕉", "牛奶", "牛肉", "大米"]
        for kw in product_keywords:
            if kw in text:
                entities.append({
                    "type": "PRODUCT",
                    "text": kw,
                    "start": text.find(kw),
                    "end": text.find(kw) + len(kw)
                })

        # 价格实体
        import re
        for match in re.finditer(r'¥?(\d+(?:\.\d+)?)\s*(?:元 | 块)?', text):
            entities.append({
                "type": "PRICE",
                "text": match.group(),
                "value": float(match.group(1)),
                "start": match.start(),
                "end": match.end()
            })

        # 数量实体
        for match in re.finditer(r'(\d+)\s*(?:个 | 斤 | 箱 | 份 | 盒)', text):
            entities.append({
                "type": "QUANTITY",
                "text": match.group(),
                "value": int(match.group(1)),
                "unit": match.group(2),
                "start": match.start(),
                "end": match.end()
            })

        return entities


class ResponseGenerationTool(BaseTool):
    """响应生成工具 - 基于意图和槽位生成自然语言回复"""

    def __init__(self, db_session: Optional[Any] = None):
        super().__init__()
        self.db = db_session

        # 回复模板
        self.response_templates = {
            "create_group": [
                "好的！我来帮您发起【{product}】的团购，成团价{price}元，预计很快就能成团！",
                "没问题！{product}团购已为您安排上，{price}元的超值价格，快来邀请邻居们一起参团吧！",
                "收到！正在为您创建{product}团购，让我来帮您配置最优的成团方案~"
            ],
            "find_product": [
                "我为您找到了几款不错的{category}，都是性价比超高的选择！",
                "想了解{category}啊，我来帮您推荐几款社区最受欢迎的~",
                "{category}我熟啊！根据大家的购买记录，这几款最值得推荐！"
            ],
            "check_status": [
                "让我帮您查一下团购进度~",
                "正在查询您的团购状态，请稍候...",
                "好的，我来帮您看看目前的成团情况"
            ],
            "general_chat": [
                "您好！我是您的 AI 团购助手，有什么可以帮您的吗？",
                "在呢！想买点什么？我可以帮您推荐或发起团购~",
                "您好呀！今天社区有不少热门团购，要我给您介绍一下吗？"
            ]
        }

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="response_generation",
            description="基于意图和上下文生成自然语言回复",
            version="1.0.0",
            tags=["nlp", "generation", "ai", "conversation"],
            author="ai-community-buying"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "用户意图类型"
                },
                "slots": {
                    "type": "object",
                    "description": "槽位信息"
                },
                "context": {
                    "type": "object",
                    "description": "对话上下文"
                },
                "style": {
                    "type": "string",
                    "description": "回复风格",
                    "enum": ["friendly", "professional", "casual"],
                    "default": "friendly"
                }
            },
            "required": ["intent"]
        }

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """执行响应生成"""
        request_id = context.get("request_id") if context else None

        try:
            intent = params.get("intent", "general_chat")
            slots = params.get("slots", {})
            style = params.get("style", "friendly")

            # 生成回复
            response = self._generate_response(intent, slots, style)

            # 生成建议操作
            suggestions = self._generate_suggestions(intent, slots)

            result = {
                "response": response,
                "suggestions": suggestions,
                "intent": intent,
                "style": style
            }

            return ToolResponse.ok(data=result, request_id=request_id)

        except Exception as e:
            self.logger.error(f"[{request_id}] 响应生成失败：{str(e)}")
            return ToolResponse.fail(error=str(e), request_id=request_id)

    def _generate_response(self, intent: str, slots: Dict, style: str) -> str:
        """生成回复文本"""
        templates = self.response_templates.get(intent, self.response_templates["general_chat"])

        # 选择一个模板
        import random
        template = random.choice(templates)

        # 填充槽位
        product = slots.get("product", "精选商品")
        price = slots.get("price", "优惠")
        category = slots.get("category", "精选")

        try:
            response = template.format(product=product, price=price, category=category)
        except KeyError:
            response = template

        return response

    def _generate_suggestions(self, intent: str, slots: Dict) -> List[str]:
        """生成建议操作"""
        suggestion_map = {
            "create_group": ["查看团购详情", "邀请邻居参团", "分享给好友"],
            "find_product": ["查看商品详情", "发起团购", "再看看其他"],
            "check_status": ["邀请邻居加速", "查看配送信息", "联系客服"],
            "general_chat": ["我想买水果", "帮我找个牛奶团购", "发起一个零食团购"]
        }

        return suggestion_map.get(intent, suggestion_map["general_chat"])


# 工具注册工厂
def init_conversation_tools(db_session: Optional[Any] = None) -> List[BaseTool]:
    """初始化对话理解工具"""
    return [
        IntentRecognitionTool(db_session),
        EntityExtractionTool(db_session),
        ResponseGenerationTool(db_session)
    ]
