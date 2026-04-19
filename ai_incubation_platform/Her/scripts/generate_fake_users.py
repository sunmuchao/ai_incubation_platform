"""
生成逼真的虚假用户数据

功能：
1. 生成指定数量的虚假用户（包含完整的个人信息）
2. 模拟真实用户的行为特征（职业、爱好、性格、价值观）
3. 为每个用户生成自然的个人简介
4. 设置用户的择偶偏好

使用方法：
    cd Her
    python scripts/generate_fake_users.py --count 10000 --auto-confirm --batch-size 200
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from db.database import SessionLocal
from db.models import UserDB
from datetime import datetime
import json
import uuid
import random
from utils.logger import logger

# 预计算的密码哈希（所有用户密码均为 "123456"）；避免万级 bcrypt 计算
DEFAULT_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF.0KLzm"

# ==================== 数据池 ====================

# 中文姓氏（扩展版 - 150 个常见姓氏，覆盖绝大多数人口）
FIRST_NAMES = [
    # 前 100 大姓（覆盖约 85% 人口）
    "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴",
    "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗",
    "郑", "梁", "谢", "宋", "唐", "许", "邓", "韩", "冯", "曹",
    "彭", "曾", "萧", "田", "董", "袁", "潘", "蔡", "蒋", "余",
    "杜", "戴", "夏", "钟", "汪", "田", "任", "姜", "范", "方",
    "石", "姚", "谭", "廖", "邹", "熊", "金", "陆", "郝", "孔",
    "白", "崔", "康", "毛", "邱", "秦", "江", "尹", "黎", "易",
    "常", "武", "乔", "贺", "赖", "龚", "文", "庞", "樊", "兰",
    "殷", "施", "洪", "段", "汤", "巴", "岳", "祁", "牛", "叶",
    # 补充 50 个较常见姓氏
    "万", "章", "鲁", "葛", "俞", "柳", "鲍", "史", "岑", "雷",
    "钱", "孟", "尹", "阮", "闵", "倪", "严", "毕", "洪", "焦",
    "侯", "柳", "齐", "莫", "裴", "焦", "管", "童", "叶", "钱",
    "柳", "祁", "覃", "霍", "涂", "向", "顾", "阮", "梅", "凌",
    "邢", "虞", "相", "伊", "褚", "余", "仲", "柳", "童", "伯"
]

# 名字（两字 - 男性扩展版，150 个）
LAST_NAMES_MALE = [
    # 传统经典名（50 个）
    "伟", "强", "磊", "洋", "勇", "军", "杰", "俊", "涛", "明",
    "鹏", "辉", "斌", "飞", "健", "刚", "平", "东", "峰", "波",
    "毅", "智", "旭", "晨", "宇", "泽", "浩", "然", "轩", "博",
    "文", "航", "天", "硕", "瑞", "铭", "远", "恒", "嘉", "诚",
    "建", "志", "立", "永", "春", "亮", "光", "荣", "兴", "华",
    # 自然意象名（30 个）
    "林", "森", "柏", "松", "海", "江", "河", "山", "石", "泉",
    "炎", "烨", "焕", "灿", "烁", "风", "云", "雷", "电", "星",
    "辰", "阳", "昊", "晖", "曜", "曦", "昭", "昱", "暄", "晴",
    # 现代流行名（40 个）
    "成", "庆", "德", "树", "柯", "楠", "楷", "栋", "梁", "材",
    "贤", "良", "才", "达", "通", "顺", "畅", "朗", "清", "正",
    "威", "武", "雄", "豪", "英", "俊", "彦", "儒", "墨", "渊",
    "坤", "乾", "震", "巽", "坎", "离", "艮", "兑", "衡", "岳",
    # 品德修养名（30 个）
    "信", "义", "仁", "礼", "孝", "忠", "廉", "勤", "俭", "让",
    "谦", "慎", "笃", "厚", "淳", "朴", "实", "诚", "真", "挚",
    "善", "美", "圣", "哲", "智", "慧", "觉", "悟", "修", "省"
]

# 名字（两字 - 女性扩展版，150 个）
LAST_NAMES_FEMALE = [
    # 传统经典名（50 个）
    "娜", "丽", "秀", "敏", "静", "艳", "娟", "芳", "燕", "萍",
    "华", "梅", "霞", "玲", "桂", "芬", "英", "兰", "琴", "欣",
    "怡", "雪", "悦", "彤", "瑶", "佳", "颖", "梦", "思", "雨",
    "晓", "婉", "雅", "诗", "嘉", "慧", "琳", "晴", "月", "柔",
    "曼", "蕾", "薇", "荷", "莲", "菊", "桃", "竹", "凤", "鸾",
    # 自然意象名（30 个）
    "云", "霞", "虹", "霓", "雾", "露", "霜", "雪", "冰", "晶",
    "莹", "珠", "玉", "宝", "珍", "琪", "瑗", "瑛", "瑾", "璇",
    "璐", "璟", "茗", "蓉", "蓓", "绮", "绯", "缦", "倩", "姿",
    # 现代流行名（40 个）
    "萱", "嫣", "芷", "芸", "苑", "蕴", "融", "蓉", "莲", "菱",
    "菲", "芳", "蕊", "苗", "苗", "蔓", "蔚", "蓝", "青", "翠",
    "绿", "红", "紫", "丹", "朱", "彤", "橙", "黄", "白", "素",
    "彩", "绘", "画", "图", "影", "像", "照", "映", "晖", "曦",
    # 才艺修养名（30 个）
    "音", "韵", "律", "曲", "歌", "舞", "乐", "琴", "瑟", "筝",
    "笛", "萧", "笙", "管", "弦", "墨", "笔", "书", "画", "诗",
    "词", "赋", "章", "句", "文", "章", "艺", "术", "才", "慧"
]

# 职业列表（扩展版 - 100+ 种职业）
JOBS = [
    # 互联网/科技
    "软件工程师", "产品经理", "设计师", "数据分析师", "运维工程师",
    "前端工程师", "后端工程师", "全栈工程师", "移动端开发", "测试工程师",
    "算法工程师", "AI 工程师", "机器学习工程师", "架构师", "技术总监",
    # 医疗/健康
    "医生", "护士", "药师", "理疗师", "营养师",
    "牙医", "心理医生", "兽医", "医学研究员", "健康管理师",
    # 教育/科研
    "教师", "大学教授", "研究员", "培训机构讲师", "家教",
    "幼儿园老师", "体育教练", "音乐老师", "美术老师", "教育顾问",
    # 法律/金融
    "律师", "会计师", "金融分析师", "投资经理", "银行职员",
    "保险代理人", "税务顾问", "审计师", "风控专员", "证券经纪人",
    # 市场/销售
    "市场专员", "销售经理", "客户经理", "商务拓展", "品牌策划",
    "广告策划", "公关专员", "新媒体运营", "电商运营", "直播带货主播",
    # 行政/人力
    "人力资源", "行政助理", "前台接待", "秘书", "翻译",
    "采购专员", "物流专员", "仓库管理", "物业管理", "客服人员",
    # 媒体/创意
    "记者", "编辑", "作家", "摄影师", "设计师",
    "插画师", "动画师", "游戏策划", "音效师", "编剧",
    # 餐饮/服务
    "厨师", "咖啡师", "调酒师", "烘焙师", "营养师",
    "餐厅经理", "酒店管理", "导游", "空乘人员", "高铁乘务员",
    # 艺术/娱乐
    "创业者", "自由职业者", "艺术家", "音乐人", "演员",
    "歌手", "舞者", "模特", "主持人", "网红博主",
    # 传统行业
    "公务员", "事业单位员工", "国企员工", "外企员工", "创业者",
    "工程师", "技术员", "质检员", "生产主管", "供应链经理",
    # 新兴职业
    "自媒体人", "视频博主", "知识付费讲师", "社群运营", "增长黑客",
    "区块链工程师", "云计算工程师", "物联网工程师", "安全工程师", "数据科学家"
]

# 城市列表（扩展版 - 50 个城市）
CITIES = [
    # 一线城市
    "北京", "上海", "深圳", "广州",
    # 新一线城市
    "杭州", "南京", "成都", "武汉", "西安", "重庆", "苏州", "宁波",
    "厦门", "青岛", "大连", "长沙", "郑州", "济南", "合肥", "福州",
    # 二线城市
    "天津", "沈阳", "哈尔滨", "长春", "石家庄", "太原", "呼和浩特",
    "南昌", "南宁", "海口", "贵阳", "昆明", "拉萨", "乌鲁木齐",
    # 三线城市
    "无锡", "常州", "南通", "扬州", "徐州", "温州", "金华", "台州",
    "泉州", "漳州", "佛山", "东莞", "中山", "珠海", "惠州", "江门"
]

# 兴趣爱好池（扩展版 - 分类更细，项目更多）
INTERESTS_BY_CATEGORY = {
    "运动健身": ["健身", "跑步", "游泳", "篮球", "足球", "羽毛球", "网球", "瑜伽", "骑行", "登山", "滑雪", "潜水", "拳击", "跆拳道", "普拉提", "CrossFit", "马拉松", "铁人三项"],
    "艺术创作": ["绘画", "摄影", "音乐", "吉他", "钢琴", "书法", "舞蹈", "话剧", "展览", "手工艺", "陶艺", "插花", "剪纸", "篆刻", "油画", "水彩", "素描", "雕塑"],
    "娱乐休闲": ["电影", "电视剧", "动漫", "游戏", "K 歌", "追星", "桌游", "剧本杀", "密室逃脱", "听书", "播客", "综艺", "音乐会", "演唱会", "livehouse"],
    "美食生活": ["美食", "烹饪", "烘焙", "咖啡", "茶道", "花艺", "园艺", "宠物", "购物", "品酒", "调酒", "探店", "打卡网红店", "收集手办", "整理收纳"],
    "学习成长": ["阅读", "写作", "语言学习", "历史", "哲学", "心理学", "科技", "纪录片", "在线课程", "考证", "演讲", "辩论", "思维导图", "时间管理"],
    "旅行户外": ["旅行", "徒步", "露营", "自驾游", "背包客", "城市探索", "拍照打卡", "民宿体验", "海边度假", "山区避暑", "温泉养生", "极光观测", "沙漠徒步"],
    "社交活动": ["聚会", "志愿者", "社团活动", "行业交流", "交友", "派对", "读书会", "创业沙龙", "技术分享", "公益义工", "户外活动", "徒步组织"],
    "养生健康": ["冥想", "太极", "气功", "艾灸", "按摩", "针灸", "药膳", "养生", "减肥", "塑形", "戒糖", "轻断食", "有机食品", "保健品"],
    "科技数码": ["编程", "开源项目", "硬件 DIY", "装机", "手机评测", "智能家居", "3D 打印", "无人机", "机器人", "VR/AR", "区块链", "加密货币"]
}

# 所有兴趣扁平化（用于随机选择）
ALL_INTERESTS = [i for items in INTERESTS_BY_CATEGORY.values() for i in items]

# 性格描述模板（扩展版 - 更多维度，更细致）
PERSONALITY_DESCRIPTIONS = {
    "外向": [
        "性格开朗，喜欢结交新朋友",
        "社交达人，朋友眼中的开心果",
        "热情 active，享受人群中的感觉",
        "健谈，善于倾听也乐于分享",
        "自来熟，和谁都能聊得来",
        "喜欢组织活动，是朋友圈的核心人物"
    ],
    "内向": [
        "性格安静，享受独处的时光",
        "慢热型，熟悉后很健谈",
        "喜欢深度交流而非表面寒暄",
        "内敛温和，心思细腻",
        "更喜欢一对一的交流",
        "需要独处时间来恢复能量"
    ],
    "理性": [
        "逻辑清晰，做事有条理",
        "理性分析派，不轻易冲动",
        "注重实际，相信数据胜过感觉",
        "冷静客观，善于解决问题",
        "决策前会充分收集信息",
        "很少被情绪左右判断"
    ],
    "感性": [
        "感性浪漫，注重情感体验",
        "心思敏感，容易被小事打动",
        "直觉型，相信第一印象",
        "富有同情心，善解人意",
        "容易被艺术和美景触动",
        "重视情感连接和共鸣"
    ],
    "冒险": [
        "喜欢尝试新鲜事物",
        "说走就走的旅行说干就干",
        "生活需要刺激和变化",
        "不安于现状，追求挑战",
        "愿意跳出舒适区探索未知",
        "认为人生就是一场冒险"
    ],
    "稳定": [
        "追求稳定安逸的生活",
        "做事稳妥，不喜欢冒险",
        "按计划行事，不喜欢意外",
        "重视安全感和确定性",
        "喜欢熟悉的环境和节奏",
        "是朋友眼中靠谱的人"
    ],
    "独立": [
        "习惯自己解决问题",
        "享受独立自主的生活",
        "不依赖他人，自我驱动",
        "有自己的主见和判断",
        "喜欢独自完成任务",
        "经济和精神都追求独立"
    ],
    "合群": [
        "重视团队合作",
        "喜欢和大家在一起",
        "善于协调人际关系",
        "愿意为集体付出",
        "在团队中找到归属感",
        "喜欢共同参与活动"
    ]
}

# 价值观选项（扩展版 - 更多维度）
VALUES_OPTIONS = {
    "family": {"label": "家庭观念", "options": [
        "家庭第一，希望早点成家",
        "事业和家庭平衡最重要",
        "先事业后家庭，不着急",
        "享受单身，不急于进入关系",
        "丁克家庭也不错",
        "想要一个热闹的大家庭",
        "父母 opinions 很重要",
        "小家庭优先"
    ]},
    "career": {"label": "事业态度", "options": [
        "事业心强，追求职业成就",
        "工作生活平衡，不为工作牺牲生活",
        "随遇而安，做自己喜欢的事",
        "财务自由是目标",
        "稳定工作最重要",
        "创业实现人生价值",
        "斜杠青年，多重身份",
        "FIRE 运动践行者"
    ]},
    "lifestyle": {"label": "生活方式", "options": [
        "简约生活，断舍离",
        "品质生活，追求精致",
        "实用主义，不追求奢侈品",
        "享受当下，及时行乐",
        "极简主义者",
        "追求仪式感",
        "环保可持续生活",
        "数字游民生活方式"
    ]},
    "relationship": {"label": "感情观", "options": [
        "一生一世一双人",
        "感情需要经营和维护",
        "合适比喜欢更重要",
        "感情随缘，不强求",
        "相信命中注定的缘分",
        "主动出击争取幸福",
        "宁缺毋滥",
        "先做朋友再谈恋爱"
    ]},
    "money": {"label": "金钱观", "options": [
        "钱是赚出来的不是省出来的",
        "精打细算，理性消费",
        "该花就花不犹豫",
        "投资自己最重要",
        "为未来储蓄",
        "体验比物质重要",
        "财务独立是底线",
        "共同理财更靠谱"
    ]},
    "social": {"label": "社交态度", "options": [
        "朋友在精不在多",
        "广泛社交拓展人脉",
        "三两好友足矣",
        "社恐但不妨碍交流",
        "喜欢认识不同的人",
        "更注重线上社交",
        "圈层文化爱好者",
        "兴趣社群参与者"
    ]}
}

# 自我介绍模板（扩展版 - 更多样化）
BIO_TEMPLATES = [
    "{personality}。{hobby_desc}期待遇见一个{expect}的人。",
    "从事{job}工作，平时喜欢{hobbies}。{personality}。希望找到{expect}的 TA。",
    "朋友眼中的我{personality}。热爱{hobbies}，最近在{doing}。期待{expect}。",
    "{job}，坐标{city}。{personality}，喜欢{hobbies}。如果你也{match}，也许我们可以聊聊。",
    "用三个词形容自己：{adj1}、{adj2}、{adj3}。平时喜欢{hobbies}，期待认识新朋友。",
    "在{city}生活的{job}，{personality}。闲暇时{hobby_desc}，希望遇到{expect}的你。",
    "{adj1}又{adj2}的{job}，热爱{hobbies}。相信{expect}的人值得相遇。",
    "典型的{personality_type}，从事{job}工作。喜欢{hobbies}，期待与{expect}的你相识。",
    "在{city}打拼的{job}，{personality}。最近迷上{doing}，希望能遇见{expect}的 TA。",
    "朋友说我{personality}，其实我也{adj1}。喜欢{hobbies}，期待{expect}的缘分。"
]

# 择偶期望（扩展版）
EXPECTATIONS = [
    "真诚善良", "有趣幽默", "有上进心", "温柔体贴",
    "成熟稳重", "阳光开朗", "有共同话题", "三观相合",
    "热爱生活", "有责任感", "善解人意", "独立自信",
    "知性优雅", "活泼可爱", "踏实可靠", "包容大度",
    "有爱心", "孝顺父母", "有事业心", "懂浪漫"
]

# 形容词池（扩展版）
ADJECTIVES = [
    "真诚", "善良", "开朗", "幽默", "温柔", "体贴",
    "独立", "自信", "阳光", "稳重", "有趣", "随和",
    "细心", "乐观", "积极", "温暖", "理性", "感性",
    "知性", "优雅", "活泼", "可爱", "踏实", "可靠",
    "包容", "大度", "贴心", "周到", "聪明", "智慧",
    "勇敢", "坚强", "坚韧", "执着", "努力", "勤奋"
]

# 正在做的事情（扩展版）
DOING_OPTIONS = [
    "学习新技能", "准备考证", "规划下一次旅行",
    "尝试新的餐厅", "追一部好剧", "读一本好书",
    "学习一门新语言", "健身减肥", "学习烹饪",
    "准备换工作", "创业中", "学习投资理财",
    "学习乐器", "练习书法", "学习摄影",
    "写小说", "做自媒体", "学习编程"
]

# 匹配条件（扩展版）
MATCH_OPTIONS = [
    "也喜欢旅行", "是个吃货", "爱运动",
    "喜欢看电影", "热爱阅读", "对世界充满好奇",
    "也喜欢美食", "也是个铲屎官", "也喜欢音乐",
    "也喜欢健身", "也爱打游戏", "也喜欢拍照",
    "也喜欢探店", "也爱睡觉", "也喜欢购物",
    "也恐高", "也怕黑", "也是个夜猫子"
]

EDUCATION_OPTIONS = ["bachelor", "master", "college", "high_school", "phd"]
RELATIONSHIP_GOALS = ["serious", "dating", "marriage", "casual"]


def generate_username(index: int) -> str:
    """生成用户名"""
    return f"user_{index:04d}"


def generate_name(gender: str, used_names: set = None, max_attempts: int = 100) -> str:
    """生成中文姓名（支持唯一性检查）"""
    for _ in range(max_attempts):
        first = random.choice(FIRST_NAMES)
        if gender == "male":
            last = random.choice(LAST_NAMES_MALE)
        else:
            last = random.choice(LAST_NAMES_FEMALE)
        name = first + last
        if used_names is None or name not in used_names:
            return name
    # 如果尝试多次仍未找到唯一名字，添加随机数字后缀
    base_name = first + last
    suffix = random.randint(1, 999)
    return f"{base_name}{suffix}"


def generate_job() -> str:
    """生成职业"""
    return random.choice(JOBS)


def generate_city() -> str:
    """生成城市"""
    return random.choice(CITIES)


def generate_age(gender: str) -> int:
    """生成年龄（符合真实分布）"""
    if gender == "male":
        # 男性年龄分布：24-40 岁为主
        weights = [5, 10, 15, 20, 20, 15, 10, 5]
        age_base = list(range(24, 32))
        return random.choices(age_base, weights=weights)[0] + random.randint(0, 8)
    else:
        # 女性年龄分布：22-35 岁为主
        weights = [10, 15, 20, 20, 15, 10, 5, 5]
        age_base = list(range(22, 30))
        return random.choices(age_base, weights=weights)[0] + random.randint(0, 5)


def generate_interests(count: int = None) -> list:
    """生成兴趣爱好"""
    if count is None:
        count = random.randint(3, 8)

    # 从不同类别中选取，确保多样性
    categories = random.sample(list(INTERESTS_BY_CATEGORY.keys()), min(3, len(INTERESTS_BY_CATEGORY)))
    interests = []

    for category in categories:
        category_interests = INTERESTS_BY_CATEGORY[category]
        interests.extend(random.sample(category_interests, min(2, len(category_interests))))

    # 补充到指定数量
    while len(interests) < count:
        interest = random.choice(ALL_INTERESTS)
        if interest not in interests:
            interests.append(interest)

    return interests[:count]


def generate_personality() -> dict:
    """生成性格描述"""
    # 选择 2-3 个性格特征
    traits = random.sample(list(PERSONALITY_DESCRIPTIONS.keys()), random.randint(2, 3))
    descriptions = [random.choice(PERSONALITY_DESCRIPTIONS[trait]) for trait in traits]
    return {
        "traits": traits,
        "description": " ".join(descriptions)
    }


def generate_values() -> dict:
    """生成价值观（数值评分 0-1）"""
    values = {}
    for key in ["family", "career", "lifestyle", "relationship", "money", "social"]:
        # 生成 0-1 之间的随机浮点数，保留 2 位小数
        values[key] = round(random.uniform(0.0, 1.0), 2)
    return values


def generate_bio(job: str, city: str, interests: list, personality: dict) -> str:
    """生成个人简介"""
    template = random.choice(BIO_TEMPLATES)

    hobby_desc = random.choice([
        f"热爱{', '.join(interests[:3])}",
        f"闲暇时喜欢{', '.join(interests[:2])}",
        f"是个{interests[0]}爱好者",
        f"沉迷于{interests[0]}无法自拔",
        f"{interests[0]}资深玩家",
        f"对{interests[0]}有着独特的热爱"
    ])

    expect = random.choice(EXPECTATIONS)

    doing = random.choice(DOING_OPTIONS)

    match = random.choice(MATCH_OPTIONS)

    adj_sample = random.sample(ADJECTIVES, 3)

    # 生成性格类型标签
    personality_type = random.choice(["INTJ", "INFP", "ENFP", "ENTJ", "ISFJ", "ESFJ", "ISTP", "ESTP"])

    bio = template.format(
        personality=personality["description"],
        hobby_desc=hobby_desc,
        expect=expect,
        job=job,
        city=city,
        hobbies=", ".join(interests[:3]),
        doing=doing,
        match=match,
        adj1=adj_sample[0],
        adj2=adj_sample[1],
        adj3=adj_sample[2],
        personality_type=personality_type
    )

    return bio


def generate_preferred_age(my_age: int, gender: str) -> tuple:
    """生成择偶年龄偏好"""
    if gender == "male":
        # 男性通常偏好比自己小的
        min_age = max(18, my_age - random.randint(5, 10))
        max_age = my_age + random.randint(0, 3)
    else:
        # 女性通常偏好比自己大的
        min_age = max(18, my_age - random.randint(2, 5))
        max_age = min(60, my_age + random.randint(5, 15))

    return min_age, max_age


def generate_user(index: int, gender: str, used_names: set = None) -> dict:
    """生成单个用户数据"""
    name = generate_name(gender, used_names)
    if used_names is not None:
        used_names.add(name)
    age = generate_age(gender)
    job = generate_job()
    city = generate_city()
    interests = generate_interests()
    personality = generate_personality()
    values = generate_values()
    bio = generate_bio(job, city, interests, personality)
    pref_min, pref_max = generate_preferred_age(age, gender)

    # 全局唯一邮箱，避免与已有用户或重复跑脚本冲突
    email = f"bulk_{index:05d}_{uuid.uuid4().hex[:10]}@seed.her.local"

    rel_goal = random.choice(RELATIONSHIP_GOALS)
    self_profile = {
        "display_name": name,
        "city": city,
        "occupation": job,
        "interests": interests[:10],
        "personality_traits": personality["traits"],
        "personality_note": personality["description"][:800],
    }
    desire_profile = {
        "preferred_gender": "female" if gender == "male" else "male",
        "age_min": pref_min,
        "age_max": pref_max,
        "relationship_goal": rel_goal,
    }

    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "password_hash": DEFAULT_PASSWORD_HASH,
        "age": age,
        "gender": gender,
        "location": city,
        "bio": bio,
        "interests": json.dumps(interests, ensure_ascii=False),
        "values": json.dumps(values, ensure_ascii=False),
        "preferred_age_min": pref_min,
        "preferred_age_max": pref_max,
        "preferred_location": random.choice([None, city, random.choice(CITIES)]),
        "preferred_gender": "female" if gender == "male" else "male",
        "avatar_url": None,
        "is_active": True,
        "job": job,
        "occupation": job[:50],
        "education": random.choice(EDUCATION_OPTIONS),
        "relationship_goal": rel_goal,
        "accept_remote": random.choice(["yes", "no", "conditional"]),
        "personality": personality["description"][:2000],
        "self_profile_json": json.dumps(self_profile, ensure_ascii=False),
        "desire_profile_json": json.dumps(desire_profile, ensure_ascii=False),
        "profile_completeness": round(random.uniform(0.45, 0.92), 2),
        "profile_confidence": round(random.uniform(0.35, 0.85), 2),
    }


def generate_users(count: int = 50, male_ratio: float = 0.5):
    """生成多个用户（名字唯一性保证）"""
    users = []
    used_names: set = set()  # 跟踪已使用的名字，防止重复
    male_count = int(count * male_ratio)
    female_count = count - male_count

    logger.info(f"计划生成 {count} 个用户（男性：{male_count}, 女性：{female_count}）")

    # 生成男性用户
    for i in range(male_count):
        user = generate_user(i, "male", used_names)
        users.append(user)

    # 生成女性用户
    for i in range(male_count, count):
        user = generate_user(i, "female", used_names)
        users.append(user)

    logger.info(f"用户生成完成，共{len(users)}个用户，唯一名字数：{len(used_names)}")
    return users


def _user_row_to_userdb_kwargs(u: dict) -> dict:
    """将生成器 dict 转为 UserDB 构造参数（仅包含模型列）。"""
    job = u.get("occupation") or u.get("job") or ""
    occ = (job or "")[:50] if job else None
    return {
        "id": u["id"],
        "name": u["name"],
        "email": u["email"],
        "password_hash": u["password_hash"],
        "age": u["age"],
        "gender": u["gender"],
        "location": u.get("location"),
        "interests": u.get("interests", "[]"),
        "values": u.get("values", "{}"),
        "bio": u.get("bio", ""),
        "avatar_url": u.get("avatar_url"),
        "is_active": u.get("is_active", True),
        "preferred_age_min": u.get("preferred_age_min", 18),
        "preferred_age_max": u.get("preferred_age_max", 60),
        "preferred_location": u.get("preferred_location"),
        "preferred_gender": u.get("preferred_gender"),
        "sexual_orientation": u.get("sexual_orientation", "heterosexual"),
        "relationship_goal": u.get("relationship_goal"),
        "personality": u.get("personality"),
        "education": u.get("education"),
        "occupation": occ,
        "accept_remote": u.get("accept_remote"),
        "self_profile_json": u.get("self_profile_json", "{}"),
        "desire_profile_json": u.get("desire_profile_json", "{}"),
        "profile_completeness": u.get("profile_completeness", 0.0),
        "profile_confidence": u.get("profile_confidence", 0.3),
    }


def import_users(users: list, batch_size: int = 200):
    """分批 add_all + 单次 commit，适合万级导入（避免每条 Repository.create 单独 commit）。"""
    db = SessionLocal()
    created_count = 0
    error_count = 0

    print(f"\n开始导入用户，共{len(users)}个，批处理大小：{batch_size}")
    print("-" * 80)

    try:
        for batch_start in range(0, len(users), batch_size):
            batch_end = min(batch_start + batch_size, len(users))
            batch = users[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(users) + batch_size - 1) // batch_size

            objs = []
            for user_data in batch:
                try:
                    objs.append(UserDB(**_user_row_to_userdb_kwargs(user_data)))
                except Exception as e:
                    logger.warning(f"构造用户 {user_data.get('email')} 失败：{e}")
                    error_count += 1

            if objs:
                db.add_all(objs)
                db.commit()
                created_count += len(objs)

            progress = (batch_end / len(users)) * 100
            print(
                f"进度：{batch_num}/{total_batches} 批次 | {progress:.1f}% | "
                f"本批写入：{len(objs)} | 累计成功：{created_count} | 构造失败：{error_count}"
            )

        print("-" * 80)
        print(f"用户导入完成！新建：{created_count}个，构造失败：{error_count}个")

    except Exception as e:
        logger.error(f"导入用户失败：{e}")
        db.rollback()
        raise
    finally:
        db.close()


def print_user_summary(users: list):
    """打印用户摘要信息"""
    print("\n" + "=" * 80)
    print("生成的用户摘要")
    print("=" * 80)

    males = [u for u in users if u["gender"] == "male"]
    females = [u for u in users if u["gender"] == "female"]

    print(f"\n总用户数：{len(users)}")
    print(f"男性：{len(males)}, 女性：{len(females)}")

    if males:
        avg_age_male = sum(u["age"] for u in males) / len(males)
        print(f"男性平均年龄：{avg_age_male:.1f}")

    if females:
        avg_age_female = sum(u["age"] for u in females) / len(females)
        print(f"女性平均年龄：{avg_age_female:.1f}")

    # 城市分布
    cities = {}
    for u in users:
        cities[u["location"]] = cities.get(u["location"], 0) + 1

    print("\n城市分布 TOP 10：")
    for city, count in sorted(cities.items(), key=lambda x: -x[1])[:10]:
        print(f"  {city}: {count}人")

    # 热门兴趣
    all_interests = []
    for u in users:
        try:
            interests = json.loads(u["interests"])
            all_interests.extend(interests)
        except:
            pass

    interest_count = {}
    for i in all_interests:
        interest_count[i] = interest_count.get(i, 0) + 1

    print("\n热门兴趣 TOP 10：")
    for interest, count in sorted(interest_count.items(), key=lambda x: -x[1])[:10]:
        print(f"  {interest}: {count}人")

    # 职业分布
    jobs = {}
    for u in users:
        job = u.get("job", "未知")
        jobs[job] = jobs.get(job, 0) + 1

    print("\n热门职业 TOP 10：")
    for job, count in sorted(jobs.items(), key=lambda x: -x[1])[:10]:
        print(f"  {job}: {count}人")

    # 年龄分布
    ages = {}
    for u in users:
        age = u["age"]
        ages[age] = ages.get(age, 0) + 1

    print("\n年龄分布：")
    for age_range in [(20, 25), (26, 30), (31, 35), (36, 40), (41, 45), (46, 50)]:
        count = sum(ages.get(a, 0) for a in range(age_range[0], age_range[1] + 1))
        if count > 0:
            print(f"  {age_range[0]}-{age_range[1]}岁：{count}人")

    print("\n" + "=" * 80)
    print("用户账号信息（所有用户密码均为：123456）")
    print("=" * 80)
    print(f"{'用户名':<25} {'姓名':<8} {'性别':<6} {'年龄':<6} {'城市':<10} {'职业':<15}")
    print("-" * 80)

    # 显示前 30 个用户
    for i, user in enumerate(users[:30]):
        print(f"{user['email']:<25} {user['name']:<8} {user['gender']:<6} {user['age']:<6} {user['location']:<10} {user.get('job', 'N/A'):<15}")

    if len(users) > 30:
        print(f"... 还有 {len(users) - 30} 个用户")

    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="生成逼真的虚假用户数据")
    parser.add_argument("--count", type=int, default=10000, help="生成用户数量（默认：10000）")
    parser.add_argument("--male-ratio", type=float, default=0.5, help="男性比例（默认：0.5）")
    parser.add_argument("--batch-size", type=int, default=200, help="批处理大小（默认：200，万级建议 200）")
    parser.add_argument("--auto-confirm", action="store_true", help="自动确认导入，无需交互确认")
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("AI Matchmaker - 虚假用户数据生成器（万级用户版）")
    print("=" * 80)
    print(f"配置：生成{args.count}个用户 | 男性比例{args.male_ratio*100:.0f}% | 批处理大小{args.batch_size}")
    print("=" * 80)

    # 生成用户
    users = generate_users(args.count, args.male_ratio)

    # 打印摘要
    print_user_summary(users)

    # 确认导入
    if not args.auto_confirm:
        confirm = input(f"是否将 {len(users)} 个用户导入数据库？(y/n): ")
        if confirm.lower() != 'y':
            print("已取消导入")
            return

    # 导入数据库
    import_users(users, batch_size=args.batch_size)

    print("\n导入完成！所有用户密码均为：123456")
    print("你可以使用任意生成的账号登录测试匹配功能。\n")
    print("提示：可以使用以下命令快速测试：")
    first_email = users[0]["email"]
    print(f"  curl -X POST http://localhost:8002/api/auth/login \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -d '{{\"email\":\"{first_email}\",\"password\":\"123456\"}}'")
    print()


if __name__ == "__main__":
    main()
