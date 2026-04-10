"""
第三方授权补充服务 - 渐进式智能收集架构

支持的第三方数据源：
1. 微信授权
   - 基础信息：昵称、头像、地区
   - 朋友圈分析：兴趣、性格、生活方式
   - 小程序使用：消费能力、兴趣偏好
2. 其他平台（预留）
   - 微博：公开内容分析
   - 豆瓣：观影/阅读记录
   - 知乎：关注话题
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json
import hashlib

from models.profile_vector_models import (
    UserVectorProfile,
    DimensionValue,
    ThirdPartyDataInference,
    DataSource,
    DIMENSION_DEFINITIONS,
)
from utils.logger import logger


class ThirdPartyProvider(str, Enum):
    """第三方平台"""
    WECHAT = "wechat"
    WEIBO = "weibo"
    DOUBAN = "douban"
    ZHIHU = "zhihu"


@dataclass
class WechatAuthData:
    """微信授权数据"""
    openid: str
    unionid: Optional[str] = None

    # 基础信息
    nickname: str = ""
    avatar_url: str = ""
    gender: int = 0  # 0-未知, 1-男, 2-女
    province: str = ""
    city: str = ""
    country: str = ""

    # 授权时间
    authorized_at: datetime = None

    def __post_init__(self):
        if self.authorized_at is None:
            self.authorized_at = datetime.now()


@dataclass
class WechatMomentsData:
    """微信朋友圈数据（已脱敏）"""
    # 帖子数量
    posts_count: int = 0

    # 帖子内容摘要（已脱敏）
    posts: List[Dict[str, Any]] = None

    # 兴趣标签（AI分析结果）
    interest_tags: List[str] = None

    # 情感倾向
    sentiment_summary: Dict[str, float] = None

    def __post_init__(self):
        if self.posts is None:
            self.posts = []
        if self.interest_tags is None:
            self.interest_tags = []
        if self.sentiment_summary is None:
            self.sentiment_summary = {}


class ThirdPartyAuthService:
    """
    第三方授权服务

    负责处理第三方平台的授权、数据获取、隐私保护
    """

    def __init__(self):
        # 授权配置
        self.auth_configs = {
            ThirdPartyProvider.WECHAT: {
                "app_id": "",  # 从环境变量读取
                "app_secret": "",  # 从环境变量读取
                "auth_url": "https://open.weixin.qq.com/connect/qrconnect",
                "token_url": "https://api.weixin.qq.com/sns/oauth2/access_token",
                "user_info_url": "https://api.weixin.qq.com/sns/userinfo",
            }
        }

        # 数据保留策略
        self.data_retention_days = {
            ThirdPartyProvider.WECHAT: 30,
            ThirdPartyProvider.WEIBO: 30,
            ThirdPartyProvider.DOUBAN: 30,
            ThirdPartyProvider.ZHIHU: 30,
        }

    async def process_wechat_auth(
        self,
        user_id: str,
        auth_code: str,
        existing_profile: Optional[UserVectorProfile] = None
    ) -> ThirdPartyDataInference:
        """
        处理微信授权

        Args:
            user_id: 用户ID
            auth_code: 微信授权码
            existing_profile: 已有画像

        Returns:
            推断结果
        """
        logger.info(f"ThirdPartyAuthService: Processing WeChat auth for user {user_id}")

        try:
            # 1. 获取 access_token
            access_token_data = await self._get_wechat_access_token(auth_code)

            # 2. 获取用户信息
            user_info = await self._get_wechat_user_info(
                access_token_data.get("access_token"),
                access_token_data.get("openid")
            )

            # 3. 构建授权数据
            wechat_data = WechatAuthData(
                openid=user_info.get("openid", ""),
                unionid=user_info.get("unionid"),
                nickname=user_info.get("nickname", ""),
                avatar_url=user_info.get("headimgurl", ""),
                gender=user_info.get("sex", 0),
                province=user_info.get("province", ""),
                city=user_info.get("city", ""),
                country=user_info.get("country", "")
            )

            # 4. 推断画像维度
            inference = await self._infer_from_wechat_data(
                user_id=user_id,
                wechat_data=wechat_data,
                existing_profile=existing_profile
            )

            return inference

        except Exception as e:
            logger.error(f"ThirdPartyAuthService: WeChat auth failed: {e}")
            return ThirdPartyDataInference(
                user_id=user_id,
                source=DataSource.WECHAT_BASIC,
                user_consent=False
            )

    async def _get_wechat_access_token(self, auth_code: str) -> Dict[str, Any]:
        """获取微信 access_token"""
        import os
        import httpx

        config = self.auth_configs[ThirdPartyProvider.WECHAT]
        app_id = os.getenv("WECHAT_APP_ID", config.get("app_id", ""))
        app_secret = os.getenv("WECHAT_APP_SECRET", config.get("app_secret", ""))

        url = f"{config['token_url']}?appid={app_id}&secret={app_secret}&code={auth_code}&grant_type=authorization_code"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

            if "errcode" in data:
                raise Exception(f"WeChat API error: {data.get('errmsg')}")

            return data

    async def _get_wechat_user_info(
        self,
        access_token: str,
        openid: str
    ) -> Dict[str, Any]:
        """获取微信用户信息"""
        import httpx

        config = self.auth_configs[ThirdPartyProvider.WECHAT]
        url = f"{config['user_info_url']}?access_token={access_token}&openid={openid}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

            if "errcode" in data:
                raise Exception(f"WeChat API error: {data.get('errmsg')}")

            return data

    async def _infer_from_wechat_data(
        self,
        user_id: str,
        wechat_data: WechatAuthData,
        existing_profile: Optional[UserVectorProfile] = None
    ) -> ThirdPartyDataInference:
        """
        从微信数据推断用户画像

        Args:
            user_id: 用户ID
            wechat_data: 微信授权数据
            existing_profile: 已有画像

        Returns:
            推断结果
        """
        dimension_inferences: Dict[int, DimensionValue] = {}
        inferred_profile: Dict[str, Any] = {}

        # 1. 昵称分析
        if wechat_data.nickname:
            nickname_inference = self._analyze_nickname(wechat_data.nickname)
            inferred_profile["nickname_analysis"] = nickname_inference

            # 推断性格倾向
            if "extraversion_hint" in nickname_inference:
                dimension_inferences[34] = DimensionValue(
                    value=nickname_inference["extraversion_hint"],
                    confidence=0.3,
                    source=DataSource.WECHAT_BASIC,
                    inferred_at=datetime.now(),
                    evidence="昵称分析推断"
                )

        # 2. 地区分析
        if wechat_data.city or wechat_data.province:
            location_inference = self._analyze_location(
                wechat_data.province,
                wechat_data.city
            )
            inferred_profile["location_analysis"] = location_inference

            # 推断城市层级
            if "city_tier" in location_inference:
                dimension_inferences[6] = DimensionValue(
                    value=location_inference["city_tier"],
                    confidence=0.9,
                    source=DataSource.WECHAT_BASIC,
                    inferred_at=datetime.now(),
                    evidence=f"城市: {wechat_data.city}"
                )

        # 3. 性别分析
        if wechat_data.gender:
            gender_value = 0.0 if wechat_data.gender == 1 else 1.0
            dimension_inferences[3] = DimensionValue(
                value=gender_value,
                confidence=0.95,
                source=DataSource.WECHAT_BASIC,
                inferred_at=datetime.now(),
                evidence="微信授权性别"
            )
            inferred_profile["gender"] = "male" if wechat_data.gender == 1 else "female"

        return ThirdPartyDataInference(
            user_id=user_id,
            source=DataSource.WECHAT_BASIC,
            inferred_profile=inferred_profile,
            dimension_inferences=dimension_inferences,
            data_summary=json.dumps({
                "nickname": wechat_data.nickname[:20] if wechat_data.nickname else "",
                "province": wechat_data.province,
                "city": wechat_data.city,
            }, ensure_ascii=False),
            user_consent=True
        )

    def _analyze_nickname(self, nickname: str) -> Dict[str, Any]:
        """
        分析昵称，推断性格倾向

        Args:
            nickname: 昵称

        Returns:
            分析结果
        """
        result = {}

        # 检查表情符号
        emoji_count = sum(1 for c in nickname if ord(c) > 0x1F000)
        if emoji_count > 0:
            result["extraversion_hint"] = 0.7  # 使用表情可能更外向
            result["emoji_usage"] = True

        # 检查特殊字符
        special_chars = ["♥", "♡", "❤", "☆", "★", "✨", "🌸", "🍀"]
        for char in special_chars:
            if char in nickname:
                result["style"] = "cute"
                result["extraversion_hint"] = 0.6
                break

        # 检查英文名
        english_chars = sum(1 for c in nickname if c.isalpha() and ord(c) < 128)
        if english_chars > len(nickname) * 0.5:
            result["style"] = "english"
            result["education_hint"] = True  # 可能受教育程度较高

        return result

    def _analyze_location(
        self,
        province: str,
        city: str
    ) -> Dict[str, Any]:
        """
        分析地区，推断城市层级

        Args:
            province: 省份
            city: 城市

        Returns:
            分析结果
        """
        result = {}

        # 城市层级定义
        tier1_cities = ["北京", "上海", "广州", "深圳"]
        tier2_cities = ["杭州", "南京", "苏州", "成都", "武汉", "西安", "重庆", "天津"]

        if any(c in city for c in tier1_cities):
            result["city_tier"] = 1.0
            result["tier"] = "一线"
        elif any(c in city for c in tier2_cities):
            result["city_tier"] = 0.7
            result["tier"] = "二线"
        else:
            result["city_tier"] = 0.5
            result["tier"] = "其他"

        result["province"] = province
        result["city"] = city

        return result

    async def process_wechat_moments(
        self,
        user_id: str,
        moments_data: WechatMomentsData,
        existing_profile: Optional[UserVectorProfile] = None
    ) -> ThirdPartyDataInference:
        """
        处理微信朋友圈数据

        Args:
            user_id: 用户ID
            moments_data: 朋友圈数据（已脱敏）
            existing_profile: 已有画像

        Returns:
            推断结果
        """
        logger.info(f"ThirdPartyAuthService: Processing WeChat moments for user {user_id}")

        dimension_inferences: Dict[int, DimensionValue] = {}
        inferred_profile: Dict[str, Any] = {}

        if moments_data.posts_count < 5:
            return ThirdPartyDataInference(
                user_id=user_id,
                source=DataSource.WECHAT_MOMENTS,
                inferred_profile={"status": "insufficient_data"},
                user_consent=True
            )

        # 1. 兴趣分析
        if moments_data.interest_tags:
            inferred_profile["interests"] = moments_data.interest_tags

            # 更新兴趣向量 [72-87]
            for i, tag in enumerate(moments_data.interest_tags[:16]):
                dimension_inferences[72 + i] = DimensionValue(
                    value=1.0,
                    confidence=0.6,
                    source=DataSource.WECHAT_MOMENTS,
                    inferred_at=datetime.now(),
                    evidence=f"朋友圈推断: {tag}"
                )

        # 2. 情感倾向分析
        if moments_data.sentiment_summary:
            inferred_profile["sentiment"] = moments_data.sentiment_summary

            # 推断性格
            positive_ratio = moments_data.sentiment_summary.get("positive", 0.5)
            dimension_inferences[42] = DimensionValue(  # 乐观程度
                value=positive_ratio,
                confidence=0.5,
                source=DataSource.WECHAT_MOMENTS,
                inferred_at=datetime.now(),
                evidence="朋友圈情感分析"
            )

        # 3. 社交活跃度
        if moments_data.posts_count > 100:
            dimension_inferences[40] = DimensionValue(  # 社交活跃度
                value=0.8,
                confidence=0.5,
                source=DataSource.WECHAT_MOMENTS,
                inferred_at=datetime.now(),
                evidence="朋友圈活跃度高"
            )

        return ThirdPartyDataInference(
            user_id=user_id,
            source=DataSource.WECHAT_MOMENTS,
            inferred_profile=inferred_profile,
            dimension_inferences=dimension_inferences,
            data_summary=json.dumps({
                "posts_count": moments_data.posts_count,
                "interest_tags": moments_data.interest_tags[:5],
            }, ensure_ascii=False),
            user_consent=True
        )

    async def request_moments_permission(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        请求朋友圈访问权限

        Args:
            user_id: 用户ID

        Returns:
            授权链接或状态
        """
        # 在实际实现中，这里会返回微信的授权链接
        # 由于微信朋友圈数据需要特殊权限，这里只是框架

        return {
            "status": "pending",
            "message": "朋友圈数据访问需要用户额外授权",
            "auth_url": None,  # 实际实现中返回授权链接
            "privacy_note": "您的朋友圈数据仅用于本地推断，不会上传原始内容"
        }

    def get_privacy_policy(self, provider: ThirdPartyProvider) -> Dict[str, Any]:
        """
        获取隐私政策

        Args:
            provider: 第三方平台

        Returns:
            隐私政策信息
        """
        return {
            "provider": provider.value,
            "data_retention_days": self.data_retention_days.get(provider, 30),
            "data_usage": [
                "仅用于用户画像推断",
                "原始数据不会被存储",
                "推断结果用户可查看和修改",
            ],
            "user_rights": [
                "查看推断结果",
                "删除推断数据",
                "撤回授权",
            ],
            "data_deletion": {
                "method": "用户可在设置中删除所有第三方数据",
                "retention_after_deletion": 0,  # 删除后不再保留
            }
        }


# 全局实例
_third_party_auth_service: Optional[ThirdPartyAuthService] = None


def get_third_party_auth_service() -> ThirdPartyAuthService:
    """获取第三方授权服务单例"""
    global _third_party_auth_service
    if _third_party_auth_service is None:
        _third_party_auth_service = ThirdPartyAuthService()
    return _third_party_auth_service