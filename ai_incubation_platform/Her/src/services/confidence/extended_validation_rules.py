"""
交叉验证规则扩展模块

新增规则：
- 兴趣-浏览一致性验证
- 年龄-自报一致性验证（基于聊天风格）
- 照片-画像风格一致性验证
- 地理轨迹一致性验证
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json

from utils.logger import logger
from db.models import UserDB, BehaviorEventDB, PhotoDB, ChatMessageDB


# ============================================
# 规则四：兴趣-浏览一致性验证
# ============================================

# 兴趣与浏览类别的映射关系
INTEREST_BROWSE_MAPPING = {
    "旅行": ["travel", "outdoor", "photography", "风景", "旅游", "户外"],
    "摄影": ["photography", "camera", "风景", "艺术", "拍照"],
    "美食": ["food", "cooking", "餐厅", "咖啡", "做饭", "吃货"],
    "运动": ["sports", "fitness", "健身", "户外", "跑步", "游泳"],
    "阅读": ["books", "reading", "文学", "知识", "看书", "读书"],
    "音乐": ["music", "concert", "演唱会", "乐器", "唱歌", "钢琴"],
    "电影": ["movie", "film", "影视", "电影院", "观影"],
    "游戏": ["game", "gaming", "电竞", "玩游戏", "王者荣耀"],
    "宠物": ["pet", "cat", "dog", "猫", "狗", "养宠物"],
    "时尚": ["fashion", "shopping", "购物", "穿搭", "美妆"],
    "投资": ["invest", "finance", "理财", "股票", "基金"],
    "创业": ["startup", "business", "创业", "公司", "企业家"],
}

def validate_interest_browse_consistency(
    user: UserDB,
    db: Session,
    days: int = 30
) -> Dict[str, Any]:
    """
    验证用户声称的兴趣与实际浏览行为的一致性

    Args:
        user: 用户对象
        db: 数据库会话
        days: 分析最近多少天的行为

    Returns:
        {
            "valid": True/False,
            "severity": "low"/"medium"/"high",
            "match_rate": 0-1,
            "detail": "描述",
            "claimed_interests": [...],
            "matched_interests": [...],
            "sample_size": N
        }
    """
    # 获取用户声称的兴趣
    try:
        claimed_interests = json.loads(user.interests or "[]")
    except:
        claimed_interests = user.interests.split(",") if user.interests else []

    # 清理兴趣列表
    claimed_interests = [i.strip() for i in claimed_interests if i.strip()]

    if not claimed_interests:
        return {"valid": True, "match_rate": 1.0, "note": "未填写兴趣"}

    # 获取用户浏览行为统计
    browse_events = db.query(BehaviorEventDB).filter(
        BehaviorEventDB.user_id == user.id,
        BehaviorEventDB.event_type == "profile_view",
        BehaviorEventDB.created_at >= datetime.now() - timedelta(days=days)
    ).limit(100).all()

    if not browse_events:
        return {"valid": True, "match_rate": 0.5, "note": "浏览数据不足，暂不判断"}

    # 统计浏览目标的特征
    browse_tags = {}
    for event in browse_events:
        target_id = event.target_id
        if not target_id:
            continue

        # 获取被浏览用户的兴趣标签
        target_user = db.query(UserDB).filter(UserDB.id == target_id).first()
        if target_user and target_user.interests:
            try:
                target_interests = json.loads(target_user.interests or "[]")
            except:
                target_interests = []

            for interest in target_interests:
                browse_tags[interest.strip()] = browse_tags.get(interest.strip(), 0) + 1

    # 计算匹配率
    matched_interests = []
    for claimed in claimed_interests:
        # 获取该兴趣对应的浏览类别
        expected_tags = INTEREST_BROWSE_MAPPING.get(claimed, [claimed])

        # 检查是否浏览过相关内容
        for tag in expected_tags:
            if tag in browse_tags or any(t in browse_tags for t in [tag]):
                matched_interests.append(claimed)
                break

    match_rate = len(matched_interests) / len(claimed_interests) if claimed_interests else 0

    # 异常判断
    if match_rate < 0.2:  # 少于20%匹配
        return {
            "valid": False,
            "severity": "high",
            "match_rate": match_rate,
            "detail": f"声称{len(claimed_interests)}个兴趣，但只有{len(matched_interests)}个与浏览行为匹配（{match_rate*100:.0f}%）",
            "claimed_interests": claimed_interests,
            "matched_interests": matched_interests,
            "sample_size": len(browse_events),
        }

    if match_rate < 0.4:  # 少于40%匹配
        return {
            "valid": False,
            "severity": "medium",
            "match_rate": match_rate,
            "detail": f"兴趣与浏览行为部分不一致，匹配率仅{match_rate*100:.0f}%",
            "claimed_interests": claimed_interests,
            "matched_interests": matched_interests,
            "sample_size": len(browse_events),
        }

    return {
        "valid": True,
        "match_rate": match_rate,
        "detail": f"兴趣与浏览行为一致性良好（{match_rate*100:.0f}%）",
        "claimed_interests": claimed_interests,
        "matched_interests": matched_interests,
        "sample_size": len(browse_events),
    }


# ============================================
# 规则五：年龄-自报一致性验证（基于聊天风格）
# ============================================

# 年龄段语言特征
AGE_LANGUAGE_FEATURES = {
    "young": {  # 18-25岁
        "keywords": ["yyds", "绝绝子", "笑死", "破防", "宝藏", "神仙", "真的会谢", "家人们"],
        "emoji_rate": 0.3,  # 表情包使用率高
        "topics": ["毕业", "找工作", "考研", "大学", "宿舍", "室友"],
    },
    "young_adult": {  # 25-35岁
        "keywords": ["内卷", "躺平", "996", "加班", "跳槽", "晋升", "理财", "买房"],
        "emoji_rate": 0.15,
        "topics": ["工作", "同事", "领导", "项目", "客户", "房贷", "结婚"],
    },
    "middle": {  # 35-45岁
        "keywords": ["孩子", "教育", "学区房", "补习", "老公", "老婆", "健康", "养生"],
        "emoji_rate": 0.08,
        "topics": ["孩子", "家庭", "学校", "父母", "健康", "体检"],
    },
    "senior": {  # 45岁+
        "keywords": ["退休", "养生", "保健品", "子女", "孙辈", "老伙伴", "回忆"],
        "emoji_rate": 0.05,
        "topics": ["退休", "旅游", "子女", "健康", "老友"],
    },
}

AGE_BRACKET_RANGES = {
    "young": (18, 25),
    "young_adult": (25, 35),
    "middle": (35, 45),
    "senior": (45, 60),
}

def validate_age_self_declared_consistency(
    user: UserDB,
    db: Session,
    days: int = 30
) -> Dict[str, Any]:
    """
    验证用户声称年龄与聊天风格的一致性

    通过分析聊天内容中的语言特征推断年龄段，
    与用户填写的年龄对比

    Returns:
        {
            "valid": True/False,
            "severity": "low"/"medium"/"high",
            "inferred_bracket": "young"/"young_adult"/"middle"/"senior",
            "claimed_age": N,
            "match": True/False
        }
    """
    # 获取用户聊天记录样本
    messages = db.query(ChatMessageDB).filter(
        ChatMessageDB.sender_id == user.id,
        ChatMessageDB.message_type == "text",
        ChatMessageDB.created_at >= datetime.now() - timedelta(days=days)
    ).order_by(ChatMessageDB.created_at.desc()).limit(50).all()

    if len(messages) < 5:
        return {"valid": True, "note": "聊天数据不足，暂不判断"}

    # 合并聊天文本
    chat_text = " ".join([m.content for m in messages if m.content])
    chat_text_lower = chat_text.lower()

    # 分析语言特征推断年龄段
    bracket_scores = {}

    for bracket, features in AGE_LANGUAGE_FEATURES.items():
        score = 0

        # 关键词匹配
        for keyword in features.get("keywords", []):
            if keyword in chat_text_lower:
                score += 1

        # 话题匹配
        for topic in features.get("topics", []):
            if topic in chat_text_lower:
                score += 0.5

        bracket_scores[bracket] = score

    # 找出得分最高的年龄段
    if not bracket_scores or max(bracket_scores.values()) == 0:
        # 没有明显的年龄特征，暂不判断
        return {"valid": True, "note": "聊天内容无明显年龄特征"}

    inferred_bracket = max(bracket_scores, key=bracket_scores.get)
    expected_range = AGE_BRACKET_RANGES.get(inferred_bracket, (18, 60))

    # 对比声称年龄
    claimed_age = user.age
    min_age, max_age = expected_range

    # 允许误差范围（宽松判断）
    tolerance = 5  # 5年宽容度

    if claimed_age < min_age - tolerance or claimed_age > max_age + tolerance:
        severity = "medium"
        if abs(claimed_age - min_age) > 10 or abs(claimed_age - max_age) > 10:
            severity = "high"

        return {
            "valid": False,
            "severity": severity,
            "inferred_bracket": inferred_bracket,
            "inferred_range": expected_range,
            "claimed_age": claimed_age,
            "detail": f"聊天风格推断年龄段{inferred_bracket}({min_age}-{max_age}岁)，但声称{claimed_age}岁",
            "bracket_scores": bracket_scores,
        }

    return {
        "valid": True,
        "inferred_bracket": inferred_bracket,
        "claimed_age": claimed_age,
        "detail": f"聊天风格与声称年龄一致",
    }


# ============================================
# 规则六：照片-画像风格一致性验证
# ============================================

# 照片风格与性格的映射
PHOTO_PERSONALITY_MAPPING = {
    "professional": {  # 正式职业照风格
        "features": ["正装", "办公室", "商务", "证件照风格"],
        "expected_personality": ["serious", "professional", "introvert", "稳重"],
    },
    "active": {  # 活泼户外风格
        "features": ["户外", "运动", "旅行", "阳光", "活力"],
        "expected_personality": ["outgoing", "active", "开朗", "外向"],
    },
    "artistic": {  # 文艺风格
        "features": ["文艺", "艺术", "音乐", "阅读", "咖啡厅"],
        "expected_personality": ["introvert", "creative", "文静", "内敛"],
    },
    "casual": {  # 休闲日常风格
        "features": ["日常生活", "朋友聚会", "美食", "休闲"],
        "expected_personality": ["balanced", "outgoing", "随和"],
    },
}

def validate_photo_personality_consistency(
    user: UserDB,
    db: Session
) -> Dict[str, Any]:
    """
    验证用户照片风格与声称性格的一致性

    注意：完整实现需要AI图像分析，此处为简化版本

    Returns:
        {
            "valid": True/False,
            "severity": "low"/"medium",
            "photo_style": "...",
            "claimed_personality": "...",
            "detail": "..."
        }
    """
    # 获取用户照片
    photos = db.query(PhotoDB).filter(
        PhotoDB.user_id == user.id,
        PhotoDB.is_active == True
    ).order_by(PhotoDB.display_order).limit(5).all()

    if not photos:
        return {"valid": True, "note": "无照片数据"}

    # 获取用户声称的性格
    try:
        personality = json.loads(user.personality or "{}")
    except:
        personality = {}

    claimed_style = personality.get("social_style", "unknown")
    # social_style 可能值：outgoing, introvert, balanced

    if claimed_style == "unknown":
        return {"valid": True, "note": "未填写性格信息"}

    # 简化版：基于照片数量和审核状态推断
    # 完整版需要AI图像识别

    # 如果有多张照片且都是生活照 → 推断活泼
    # 如果照片都是正式风格 → 推断稳重

    photo_count = len(photos)
    approved_count = sum(1 for p in photos if p.moderation_status == "approved")

    # 简化判断：照片多且审核通过率高 → 可能是真实展示自己的
    if photo_count >= 3 and approved_count >= 2:
        inferred_style = "outgoing"  # 多照片展示 → 外向
    elif photo_count <= 1:
        inferred_style = "introvert"  # 少照片 → 内向
    else:
        inferred_style = "balanced"

    # 对比
    if claimed_style == "outgoing" and inferred_style == "introvert":
        return {
            "valid": False,
            "severity": "low",
            "photo_style": inferred_style,
            "claimed_style": claimed_style,
            "detail": "声称外向但照片展示较少，可能性格偏内向",
        }

    if claimed_style == "introvert" and inferred_style == "outgoing":
        return {
            "valid": False,
            "severity": "low",
            "photo_style": inferred_style,
            "claimed_style": claimed_style,
            "detail": "声称内向但照片展示丰富，可能性格偏外向",
        }

    return {
        "valid": True,
        "photo_style": inferred_style,
        "claimed_style": claimed_style,
        "detail": "照片展示风格与性格描述一致",
    }


# ============================================
# 规则七：地理轨迹一致性验证
# ============================================

def validate_location_trajectory_consistency(
    user: UserDB,
    db: Session,
    days: int = 30
) -> Dict[str, Any]:
    """
    验证用户声称位置与实际签到/活跃轨迹的一致性

    Returns:
        {
            "valid": True/False,
            "severity": "low"/"medium"/"high",
            "claimed_location": "...",
            "inferred_location": "...",
            "distance_km": N
        }
    """
    # 获取用户声称的位置
    claimed_location = user.location

    if not claimed_location:
        return {"valid": True, "note": "未填写位置信息"}

    # 获取用户活跃记录（通过浏览行为推断）
    # 如果用户浏览的都是同一城市的用户 → 推断在该城市

    browse_events = db.query(BehaviorEventDB).filter(
        BehaviorEventDB.user_id == user.id,
        BehaviorEventDB.event_type == "profile_view",
        BehaviorEventDB.created_at >= datetime.now() - timedelta(days=days)
    ).limit(50).all()

    if not browse_events:
        return {"valid": True, "note": "活跃数据不足"}

    # 统计被浏览用户的位置分布
    location_counts = {}
    for event in browse_events:
        if not event.target_id:
            continue

        target_user = db.query(UserDB).filter(UserDB.id == event.target_id).first()
        if target_user and target_user.location:
            loc = target_user.location
            location_counts[loc] = location_counts.get(loc, 0) + 1

    if not location_counts:
        return {"valid": True, "note": "无法推断位置"}

    # 找出最常浏览的城市
    inferred_location = max(location_counts, key=location_counts.get)

    # 对比位置（简化版：城市名匹配）
    # 完整版需要地理编码计算距离

    # 城市名匹配（去除省市后缀）
    claimed_city = extract_city_name(claimed_location)
    inferred_city = extract_city_name(inferred_location)

    if claimed_city == inferred_city:
        return {
            "valid": True,
            "claimed_location": claimed_location,
            "inferred_location": inferred_location,
            "detail": "位置信息与活跃轨迹一致",
        }

    # 同省份不同城市 → 低异常
    # 完全不同城市 → 中异常

    # 简化判断：不匹配则为异常
    return {
        "valid": False,
        "severity": "medium",
        "claimed_location": claimed_location,
        "inferred_location": inferred_location,
        "detail": f"声称在{claimed_location}，但活跃轨迹显示主要关注{inferred_location}的用户",
        "browse_distribution": location_counts,
    }


def extract_city_name(location: str) -> str:
    """从位置字符串中提取城市名"""
    if not location:
        return ""

    # 常见的省市后缀
    suffixes = ["省", "市", "区", "县", "自治区", "特别行政区"]

    result = location.strip()
    for suffix in suffixes:
        if result.endswith(suffix):
            result = result[:-len(suffix)]

    # 处理直辖市
    direct_cities = ["北京", "上海", "天津", "重庆"]
    for city in direct_cities:
        if result.startswith(city):
            return city

    return result


# ============================================
# 综合验证函数
# ============================================

def run_all_extended_validations(
    user: UserDB,
    db: Session
) -> Tuple[float, Dict[str, Any]]:
    """
    执行所有扩展验证规则

    Returns:
        (score, flags)
        score: 0-1，初始为1，发现异常扣分
        flags: 各规则的验证结果
    """
    score = 1.0
    flags = {}

    # 规则四：兴趣-浏览一致性
    result4 = validate_interest_browse_consistency(user, db)
    if not result4.get("valid"):
        severity = result4.get("severity", "medium")
        penalty = _severity_to_penalty(severity)
        score -= penalty
        flags["interest_browse_mismatch"] = result4

    # 规则五：年龄-自报一致性
    result5 = validate_age_self_declared_consistency(user, db)
    if not result5.get("valid"):
        severity = result5.get("severity", "medium")
        penalty = _severity_to_penalty(severity)
        score -= penalty
        flags["age_self_declared_mismatch"] = result5

    # 规则六：照片-画像一致性
    result6 = validate_photo_personality_consistency(user, db)
    if not result6.get("valid"):
        severity = result6.get("severity", "low")
        penalty = _severity_to_penalty(severity)
        score -= penalty
        flags["photo_personality_mismatch"] = result6

    # 规则七：地理轨迹一致性
    result7 = validate_location_trajectory_consistency(user, db)
    if not result7.get("valid"):
        severity = result7.get("severity", "medium")
        penalty = _severity_to_penalty(severity)
        score -= penalty
        flags["location_trajectory_mismatch"] = result7

    # 确保分数在合理范围
    score = max(0.0, min(1.0, score))

    return score, flags


def _severity_to_penalty(severity: str) -> float:
    """将异常严重等级转换为扣分"""
    penalties = {
        "low": 0.1,
        "medium": 0.25,
        "high": 0.4,
    }
    return penalties.get(severity, 0.2)