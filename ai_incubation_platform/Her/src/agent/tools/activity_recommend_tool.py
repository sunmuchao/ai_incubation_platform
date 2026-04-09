"""
活动推荐工具

基于用户共同兴趣推荐适合的活动。
"""
from typing import Dict, List, Optional, Any
from utils.logger import logger


class ActivityRecommendTool:
    """
    活动推荐工具

    功能：
    - 基于共同兴趣推荐活动
    - 生成活动建议列表
    - 支持地点和时间过滤
    """

    name = "activity_recommend"
    description = "基于用户共同兴趣推荐适合的活动"
    tags = ["activity", "recommend", "date"]

    # 兴趣到活动的映射
    INTEREST_TO_ACTIVITY = {
        "阅读": ["书店约会", "读书分享会", "图书馆", "签售会"],
        "旅行": ["城市探索", "周边游", "景点打卡", "美食之旅"],
        "音乐": ["音乐会", "Livehouse", "KTV", "音乐展览"],
        "电影": ["电影院", "电影节", "私人影院", "电影主题展"],
        "健身": ["健身房", "攀岩馆", "瑜伽课", "户外跑步"],
        "美食": ["美食探店", "DIY 料理", "美食节", "品酒会"],
        "摄影": ["摄影展", "外拍活动", "摄影工作室", "景点拍照"],
        "艺术": ["美术馆", "艺术展览", "手作工坊", "艺术市集"],
        "运动": ["羽毛球", "游泳", "骑行", "徒步"],
        "游戏": ["电玩城", "桌游吧", "密室逃脱", "剧本杀"],
        "宠物": ["宠物咖啡厅", "宠物公园", "宠物展览", "动物救助站"],
        "咖啡": ["精品咖啡馆", "手冲体验", "咖啡师体验课", "咖啡展"],
    }

    # 活动难度级别
    ACTIVITY_DIFFICULTY = {
        "咖啡厅": "easy",
        "餐厅": "easy",
        "书店": "easy",
        "公园散步": "easy",
        "电影院": "easy",
        "展览": "medium",
        "音乐会": "medium",
        "DIY 料理": "medium",
        "运动": "medium",
        "徒步": "medium",
        "密室逃脱": "hard",
        "剧本杀": "hard",
    }

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "用户兴趣列表"
                },
                "target_interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "匹配对象兴趣列表"
                },
                "location": {
                    "type": "string",
                    "description": "所在城市/地区"
                },
                "difficulty": {
                    "type": "string",
                    "description": "活动难度偏好",
                    "enum": ["easy", "medium", "hard", "any"]
                }
            },
            "required": ["user_interests", "target_interests"]
        }

    @staticmethod
    def handle(
        user_interests: List[str],
        target_interests: List[str],
        location: Optional[str] = None,
        difficulty: Optional[str] = "any"
    ) -> dict:
        """
        处理活动推荐请求

        Args:
            user_interests: 用户兴趣列表
            target_interests: 匹配对象兴趣列表
            location: 所在城市/地区
            difficulty: 活动难度偏好

        Returns:
            活动推荐列表
        """
        logger.info(f"ActivityRecommendTool: Generating recommendations")

        # 找出共同兴趣
        common_interests = set(user_interests) & set(target_interests)

        # 为每个共同兴趣生成活动推荐
        recommendations = []

        for interest in common_interests:
            activities = ActivityRecommendTool.INTEREST_TO_ACTIVITY.get(interest, [])
            for activity in activities[:2]:  # 每个兴趣取前 2 个活动
                rec = {
                    "activity": activity,
                    "based_on_interest": interest,
                    "difficulty": ActivityRecommendTool.ACTIVITY_DIFFICULTY.get(
                        activity.split()[0], "medium"
                    ),
                    "description": ActivityRecommendTool._get_activity_description(activity)
                }
                recommendations.append(rec)

        # 如果没有共同兴趣，推荐通用活动
        if not recommendations:
            recommendations = [
                {"activity": "咖啡厅闲聊", "based_on_interest": "通用", "difficulty": "easy",
                 "description": "轻松的氛围，适合初次见面"},
                {"activity": "公园散步", "based_on_interest": "通用", "difficulty": "easy",
                 "description": "自然环境，边散步边聊天"},
                {"activity": "美食探店", "based_on_interest": "通用", "difficulty": "medium",
                 "description": "一起探索新餐厅，分享美食体验"},
            ]

        # 按难度过滤
        if difficulty and difficulty != "any":
            recommendations = [r for r in recommendations if r["difficulty"] == difficulty]

        # 按难度排序（先易后难）
        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        recommendations.sort(key=lambda x: difficulty_order.get(x["difficulty"], 1))

        logger.info(f"ActivityRecommendTool: Generated {len(recommendations)} recommendations")

        return {
            "recommendations": recommendations[:5],  # 最多返回 5 个
            "common_interests": list(common_interests),
            "total": len(recommendations)
        }

    @staticmethod
    def _get_activity_description(activity: str) -> str:
        """获取活动描述"""
        descriptions = {
            "书店约会": "在安静的书店里一起选书、看书，分享阅读心得",
            "读书分享会": "参加读书活动，与志同道合的人交流",
            "咖啡厅闲聊": "在舒适的咖啡馆里放松聊天，互相了解",
            "美食探店": "探索城市里的特色餐厅，分享美食体验",
            "公园散步": "在自然环境中散步，享受轻松惬意的时光",
            "电影院": "一起观看最新电影，结束后交流观后感",
            "音乐会": "欣赏现场音乐表演，感受艺术的魅力",
            "DIY 料理": "一起动手制作美食，增进互动和默契",
            "展览": "参观艺术展览，分享对艺术的理解和感受",
            "健身房": "一起运动健身，保持健康的生活方式",
            "攀岩馆": "挑战自我，互相鼓励完成攀岩路线",
            "密室逃脱": "团队协作解谜，考验默契和智力",
            "剧本杀": "沉浸式角色扮演体验，锻炼推理能力",
        }
        return descriptions.get(activity, "一起度过愉快的时光")
