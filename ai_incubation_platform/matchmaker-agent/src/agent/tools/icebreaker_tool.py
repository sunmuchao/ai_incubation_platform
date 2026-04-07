"""
破冰问题生成工具

基于匹配双方的共同兴趣和画像特征，生成个性化的破冰对话建议。
参考 Tinder 的"GIF + 预设问题"机制，但采用 AI 生成更个性化的内容。
"""
from typing import Dict, Any, List
import random
from db.database import get_db
from db.repositories import UserRepository
from utils.logger import logger


class IcebreakerTool:
    """
    破冰问题生成工具

    功能：
    - 基于共同兴趣生成个性化问题
    - 提供多种风格选择（幽默、深度、轻松）
    - 支持文化敏感的对话建议
    - 避免敏感话题
    """

    name = "icebreaker_generator"
    description = "基于匹配双方特征生成个性化破冰对话建议"
    tags = ["icebreaker", "conversation", "engagement"]

    # 预设问题模板库，按类别分类
    QUESTION_TEMPLATES = {
        "interests": [
            "看到你也喜欢 {interest}，最近有什么推荐的 {interest_category} 吗？",
            "我也是 {interest} 爱好者！你最喜欢的是什么？",
            "发现我们有共同的兴趣：{interest}，你是怎么开始接触的？",
            "好奇你对 {interest} 有什么独到见解？",
        ],
        "travel": [
            "你的照片背景是在哪里拍的？看起来很美！",
            "最近一次让你印象深刻的旅行是去哪里？",
            "如果现在可以去任何地方旅行，你会选择哪里？",
            "你有什么私藏的旅行目的地推荐吗？",
        ],
        "food": [
            "你看起来很喜欢美食，最近有发现什么好吃的餐厅吗？",
            "如果能选择一种食物吃一辈子，你会选什么？",
            "你有什么拿手菜或者特别喜欢做的料理吗？",
            "甜党还是咸党？这个问题很重要 😄",
        ],
        "entertainment": [
            "最近有看什么好剧/电影推荐吗？我正愁剧荒呢",
            "你更喜欢电影院还是在家追剧？",
            "有什么电影/电视剧是你看了好几遍的？",
            "最近有听什么好歌吗？求推荐！",
        ],
        "lifestyle": [
            "周末你一般都喜欢做些什么？",
            "你是早起型还是夜猫子型？",
            "工作之余你最喜欢做的事情是什么？",
            "有什么一直坚持的习惯或者爱好吗？",
        ],
        "personality": [
            "朋友通常会用哪三个词来形容你？",
            "你觉得自己是内向还是外向？",
            "什么事情会让你特别有成就感？",
            "你理想中的完美一天是怎样的？",
        ],
        "humor": [
            "讲个冷笑话：为什么数学书很悲伤？因为它有太多问题 😅",
            "如果动物会说话，你觉得哪种动物最毒舌？",
            "你有什么奇怪但可爱的小习惯吗？",
            "如果用一种食物形容自己，你会是什么？",
        ],
        "deep": [
            "最近有什么事情让你觉得特别有收获？",
            "你对未来有什么期待或者规划吗？",
            "有什么事情是你一直想尝试但还没做的？",
            "你觉得什么品质在一段关系中最重要？",
        ],
    }

    # 兴趣分类映射
    INTEREST_CATEGORIES = {
        "阅读": "books",
        "旅行": "travel",
        "音乐": "entertainment",
        "电影": "entertainment",
        "健身": "lifestyle",
        "美食": "food",
        "摄影": "interests",
        "绘画": "interests",
        "游泳": "lifestyle",
        "跑步": "lifestyle",
        "瑜伽": "lifestyle",
        "游戏": "entertainment",
        "咖啡": "food",
        "品酒": "food",
        "烘焙": "food",
        "登山": "travel",
        "滑雪": "travel",
        "冲浪": "travel",
    }

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "发起对话的用户 ID"
                },
                "target_user_id": {
                    "type": "string",
                    "description": "目标用户 ID"
                },
                "style": {
                    "type": "string",
                    "description": "破冰问题风格",
                    "enum": ["casual", "humorous", "deep", "interest_based"],
                    "default": "casual"
                },
                "count": {
                    "type": "integer",
                    "description": "生成问题数量",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["user_id", "target_user_id"]
        }

    @staticmethod
    def handle(
        user_id: str,
        target_user_id: str,
        style: str = "casual",
        count: int = 3
    ) -> dict:
        """
        生成破冰问题

        Args:
            user_id: 发起对话的用户 ID
            target_user_id: 目标用户 ID
            style: 问题风格 (casual/humorous/deep/interest_based)
            count: 生成数量

        Returns:
            破冰问题列表和相关建议
        """
        logger.info(f"IcebreakerTool: Generating icebreakers for {user_id} -> {target_user_id}, style={style}, count={count}")

        try:
            db = next(get_db())
            user_repo = UserRepository(db)

            db_user = user_repo.get_by_id(user_id)
            db_target = user_repo.get_by_id(target_user_id)

            if not db_user or not db_target:
                return {"error": "User not found"}

            from api.users import _from_db
            user = _from_db(db_user)
            target = _from_db(db_target)

            # 获取共同兴趣
            common_interests = list(set(user.interests) & set(target.interests))
            logger.info(f"IcebreakerTool: Common interests: {common_interests}")

            # 生成破冰问题
            icebreakers = []

            # 1. 基于共同兴趣的问题（优先级最高）
            if common_interests and style in ["casual", "interest_based"]:
                for interest in common_interests[:3]:
                    category = IcebreakerTool.INTEREST_CATEGORIES.get(interest, "interests")
                    templates = IcebreakerTool.QUESTION_TEMPLATES.get(category, IcebreakerTool.QUESTION_TEMPLATES["interests"])
                    template = random.choice(templates)
                    question = template.format(
                        interest=interest,
                        interest_category=IcebreakerTool._get_category_name(category)
                    )
                    icebreakers.append({
                        "question": question,
                        "type": "interest_based",
                        "context": f"基于共同兴趣：{interest}",
                        "confidence": 0.9
                    })

            # 2. 基于风格的问题
            style_templates = IcebreakerTool._get_templates_for_style(style)
            while len(icebreakers) < count and style_templates:
                template = random.choice(style_templates)
                # 避免重复
                if template not in [ib["question"] for ib in icebreakers]:
                    icebreakers.append({
                        "question": template,
                        "type": style,
                        "context": f"{IcebreakerTool._get_style_name(style)}风格",
                        "confidence": 0.7
                    })

            # 3. 如果还不够，从通用问题中补充
            if len(icebreakers) < count:
                general_templates = (
                    IcebreakerTool.QUESTION_TEMPLATES["lifestyle"] +
                    IcebreakerTool.QUESTION_TEMPLATES["personality"]
                )
                while len(icebreakers) < count and general_templates:
                    template = random.choice(general_templates)
                    if template not in [ib["question"] for ib in icebreakers]:
                        icebreakers.append({
                            "question": template,
                            "type": "general",
                            "context": "通用破冰问题",
                            "confidence": 0.5
                        })

            # 截断到指定数量
            icebreakers = icebreakers[:count]

            # 生成对话建议
            tips = IcebreakerTool._generate_conversation_tips(user, target, common_interests)

            logger.info(f"IcebreakerTool: Generated {len(icebreakers)} icebreakers")

            return {
                "icebreakers": icebreakers,
                "conversation_tips": tips,
                "common_interests": common_interests,
                "style": style
            }

        except Exception as e:
            logger.error(f"IcebreakerTool: Failed to generate icebreakers: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_templates_for_style(style: str) -> List[str]:
        """根据风格获取模板"""
        style_mapping = {
            "casual": IcebreakerTool.QUESTION_TEMPLATES["lifestyle"],
            "humorous": IcebreakerTool.QUESTION_TEMPLATES["humor"],
            "deep": IcebreakerTool.QUESTION_TEMPLATES["deep"],
            "interest_based": []  # 特殊处理
        }
        return style_mapping.get(style, IcebreakerTool.QUESTION_TEMPLATES["lifestyle"])

    @staticmethod
    def _get_style_name(style: str) -> str:
        """获取风格中文名"""
        names = {
            "casual": "轻松",
            "humorous": "幽默",
            "deep": "深度",
            "interest_based": "兴趣"
        }
        return names.get(style, "轻松")

    @staticmethod
    def _get_category_name(category: str) -> str:
        """获取分类中文名"""
        names = {
            "books": "书籍/作品",
            "travel": "旅行地点",
            "entertainment": "娱乐作品",
            "food": "美食/料理",
            "lifestyle": "生活方式",
            "interests": "相关内容"
        }
        return names.get(category, "相关内容")

    @staticmethod
    def _generate_conversation_tips(user, target, common_interests: List[str]) -> List[str]:
        """生成对话建议"""
        tips = []

        # 基于共同兴趣的建议
        if common_interests:
            tips.append(f"可以从共同的兴趣 '{common_interests[0]}' 开始聊起")

        # 基于 bio 的建议
        if target.bio and len(target.bio) > 10:
            tips.append("对方的个人简介很有特点，可以询问相关内容")

        # 通用建议
        general_tips = [
            "保持真诚和好奇心，不要急于表现自己",
            "问开放式问题，鼓励对方分享更多",
            "注意对方的回应节奏，不要连续发问",
            "分享自己的相关经历，建立共鸣"
        ]
        tips.extend(random.sample(general_tips, 2))

        return tips
