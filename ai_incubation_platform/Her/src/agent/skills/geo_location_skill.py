"""
地理数据 Skill

基于地理轨迹的真实匹配和约会地点推荐
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger
from config import settings
import math


class GeoLocationSkill(BaseSkill):
    """
    地理数据 Skill - 基于"地理轨迹"的真实匹配

    核心能力:
    - 地理轨迹分析
    - 常驻商圈画像
    - 生活质感评估
    - 地理中点计算
    - 约会地点推荐

    AI Native 特性:
    - 自主分析用户活动范围
    - 主动推送附近匹配
    - 情境感知约会地点推荐
    """

    name = "geo_location"
    version = "1.0.0"
    description = """
    地理数据服务

    能力:
    - 地理轨迹分析（常驻地点、活动范围）
    - 常驻商圈画像（偏好商圈类型）
    - 生活质感评估
    - 地理中点计算
    - 约会地点推荐
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
                    "enum": [
                        "analyze_trajectory",
                        "get_profile",
                        "calculate_midpoint",
                        "recommend_dates",
                        "compare_compatibility"
                    ],
                    "description": "操作类型"
                },
                "target_user_id": {
                    "type": "string",
                    "description": "目标用户 ID（用于兼容性比较或中点计算）"
                },
                "date_type": {
                    "type": "string",
                    "enum": ["casual", "romantic", "cultural", "outdoor"],
                    "description": "约会类型（用于地点推荐）"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["week", "month", "quarter"],
                    "default": "month"
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
                "geo_profile": {
                    "type": "object",
                    "properties": {
                        "home_district": {"type": "string"},
                        "work_district": {"type": "string"},
                        "frequent_areas": {"type": "array"},
                        "lifestyle_tags": {"type": "array"}
                    }
                },
                "midpoint": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "distance_to_user_1": {"type": "number"},
                        "distance_to_user_2": {"type": "number"}
                    }
                },
                "date_recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "address": {"type": "string"},
                            "distance_from_midpoint": {"type": "number"},
                            "price_range": {"type": "string"},
                            "match_score": {"type": "number"}
                        }
                    }
                },
                "compatibility": {
                    "type": "object",
                    "properties": {
                        "geo_match": {"type": "number"},
                        "lifestyle_match": {"type": "number"},
                        "activity_range_overlap": {"type": "number"}
                    }
                }
            }
        }

    async def execute(
        self,
        user_id: str,
        action: str,
        target_user_id: Optional[str] = None,
        date_type: Optional[str] = None,
        time_range: Optional[str] = "month",
        **kwargs
    ) -> dict:
        """
        执行地理数据 Skill

        Args:
            user_id: 用户 ID
            action: 操作类型
            target_user_id: 目标用户 ID
            date_type: 约会类型
            time_range: 时间范围
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"GeoLocationSkill: Executing for user={user_id}, action={action}")

        if action == "analyze_trajectory":
            return await self._analyze_trajectory(user_id, time_range)
        elif action == "get_profile":
            return await self._get_geo_profile(user_id)
        elif action == "calculate_midpoint":
            if not target_user_id:
                return {"success": False, "error": "target_user_id required"}
            return await self._calculate_midpoint(user_id, target_user_id)
        elif action == "recommend_dates":
            if not target_user_id:
                return {"success": False, "error": "target_user_id required for date recommendations"}
            return await self._recommend_dates(user_id, target_user_id, date_type)
        elif action == "compare_compatibility":
            if not target_user_id:
                return {"success": False, "error": "target_user_id required"}
            return await self._compare_geo_compatibility(user_id, target_user_id)
        else:
            return {"success": False, "error": "Invalid action", "ai_message": "不支持的操作类型"}

    async def _analyze_trajectory(self, user_id: str, time_range: str) -> dict:
        """
        分析用户地理轨迹

        基于授权的位置数据，分析用户常驻地点和活动范围

        降级方案：
        - 有外部 API 时：调用真实地理数据服务
        - 无 API 时：使用模拟数据（基于用户 ID 哈希生成一致结果）
        """
        logger.info(f"GeoLocationSkill: Analyzing trajectory for user={user_id}, range={time_range}")

        # Step 1: 获取用户授权的位置数据
        # 检查是否配置了高德地图 API
        if settings.amap_enabled and settings.amap_api_key:
            try:
                location_data = await self._fetch_location_data_from_amap(user_id, time_range)
            except Exception as e:
                logger.warning(f"AMap location fetch failed: {e}, using fallback")
                location_data = None
        else:
            location_data = None

        if not location_data:
            # 降级方案：使用模拟数据
            logger.debug("Using mock location data as fallback")
            location_data = self._generate_mock_location_data(user_id)

        # Step 2: 识别常驻地点（家/公司）
        home_work = self._identify_home_work(location_data)

        # Step 3: 识别常去商圈
        frequent_areas = self._identify_frequent_areas(location_data)

        # Step 4: 生成生活质感标签
        lifestyle_tags = self._generate_lifestyle_tags(frequent_areas)

        # Step 5: 构建地理画像
        profile = {
            "user_id": user_id,
            "home_district": home_work.get("home", "未知"),
            "work_district": home_work.get("work", "未知"),
            "frequent_areas": frequent_areas,
            "lifestyle_tags": lifestyle_tags,
            "activity_radius": self._calculate_activity_radius(location_data, home_work),
            "preferred_distance": self._infer_preferred_distance(lifestyle_tags)
        }

        # Step 6: 保存画像
        await self._save_geo_profile(user_id, profile)

        # Step 7: 生成 AI 消息
        ai_message = self._generate_analysis_message(profile)

        return {
            "success": True,
            "ai_message": ai_message,
            "geo_profile": profile,
            "location_summary": {
                "total_locations": location_data.get("total_locations", 0),
                "unique_areas": len(frequent_areas),
                "coverage_area_km2": location_data.get("coverage_area", 0)
            }
        }

    async def _get_geo_profile(self, user_id: str) -> dict:
        """获取用户地理画像"""
        profile = await self._load_geo_profile(user_id)

        if not profile:
            return await self._analyze_trajectory(user_id, "month")

        return {
            "success": True,
            "ai_message": f"你的常居区域：{profile.get('home_district', '未知')}，工作区域：{profile.get('work_district', '未知')}",
            "geo_profile": profile
        }

    async def _calculate_midpoint(self, user_id_1: str, user_id_2: str) -> dict:
        """计算两人地理中点"""
        profile_1 = await self._load_geo_profile(user_id_1)
        profile_2 = await self._load_geo_profile(user_id_2)

        if not profile_1:
            profile_1 = (await self._analyze_trajectory(user_id_1, "month")).get("geo_profile")
        if not profile_2:
            profile_2 = (await self._analyze_trajectory(user_id_2, "month")).get("geo_profile")

        # 计算中点
        midpoint = self._find_optimal_midpoint(profile_1, profile_2)

        # 计算各自到中点的距离
        distance_1 = self._calculate_distance(
            profile_1.get("home_district", ""),
            midpoint["location"]
        )
        distance_2 = self._calculate_distance(
            profile_2.get("home_district", ""),
            midpoint["location"]
        )

        ai_message = (f"为你们找到的见面中点是「{midpoint['location']}」。\n"
                     f"距离你约{distance_1:.1f}公里，距离 TA 约{distance_2:.1f}公里。\n"
                     f"这个区域交通便利，适合约会~")

        return {
            "success": True,
            "ai_message": ai_message,
            "midpoint": {
                "location": midpoint["location"],
                "area_type": midpoint["area_type"],
                "distance_to_user_1": round(distance_1, 1),
                "distance_to_user_2": round(distance_2, 1),
                "transportation": midpoint.get("transportation", "地铁可达")
            }
        }

    async def _recommend_dates(self, user_id_1: str, user_id_2: str, date_type: str = None) -> dict:
        """
        推荐约会地点

        基于双方位置、喜好和约会类型推荐
        """
        date_type = date_type or "casual"

        # 获取双方画像
        profile_1 = await self._load_geo_profile(user_id_1) or \
                    (await self._analyze_trajectory(user_id_1, "month")).get("geo_profile")
        profile_2 = await self._load_geo_profile(user_id_2) or \
                    (await self._analyze_trajectory(user_id_2, "month")).get("geo_profile")

        # 计算中点
        midpoint = self._find_optimal_midpoint(profile_1, profile_2)

        # 推荐地点
        recommendations = self._find_date_spots(midpoint, date_type, profile_1, profile_2)

        # 生成 AI 消息
        ai_message = self._generate_recommendation_message(recommendations, date_type)

        return {
            "success": True,
            "ai_message": ai_message,
            "midpoint": midpoint["location"],
            "date_recommendations": recommendations,
            "date_type": date_type
        }

    async def _compare_geo_compatibility(self, user_id_1: str, user_id_2: str) -> dict:
        """比较两人地理位置兼容性"""
        profile_1 = await self._load_geo_profile(user_id_1)
        profile_2 = await self._load_geo_profile(user_id_2)

        if not profile_1 or not profile_2:
            return {"success": False, "error": "Profile not found"}

        # 计算兼容性
        compatibility = self._calculate_geo_compatibility(profile_1, profile_2)

        # 生成 AI 解读
        ai_interpretation = self._generate_compatibility_interpretation(compatibility, profile_1, profile_2)

        return {
            "success": True,
            "ai_message": ai_interpretation["message"],
            "compatibility": compatibility,
            "analysis": {
                "user_1_areas": profile_1.get("lifestyle_tags", []),
                "user_2_areas": profile_2.get("lifestyle_tags", []),
                "common_areas": ai_interpretation["common_areas"],
                "distance_analysis": ai_interpretation["distance"]
            }
        }

    async def _fetch_location_data(self, user_id: str, time_range: str) -> Optional[dict]:
        """
        从外部 API 获取位置数据

        隐私保护：
        - 用户必须授权
        - 仅用于匹配目的
        - 定期清理历史数据

        使用高德地图 API 进行地理编码和位置服务
        """
        from db.database import SessionLocal
        from db.models import UserDB
        from integration.amap_client import get_amap_client

        db = SessionLocal()
        try:
            # 获取用户位置信息
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return None

            # 获取用户位置（实际使用时从用户表获取经纬度）
            user_location = getattr(user, "location", None)

            amap = get_amap_client()

            # 如果用户有地址信息，进行地理编码
            if user_location and isinstance(user_location, str):
                geo_result = await amap.geocode(user_location)
                if geo_result:
                    return {
                        "total_locations": 1,
                        "coverage_area": 50,
                        "user_location": user_location,
                        "coordinates": geo_result.get("location"),
                        "formatted_address": geo_result.get("formatted_address"),
                        "city": geo_result.get("city")
                    }

            # 如果没有位置信息，返回 None 使用模拟数据
            logger.info(f"GeoLocationSkill: User {user_id} location not available")
            return None

        except Exception as e:
            logger.error(f"GeoLocationSkill: Error fetching location data: {e}")
            return None
        finally:
            db.close()

    async def _fetch_location_data_from_amap(self, user_id: str, time_range: str) -> dict:
        """
        从高德地图 API 获取用户位置数据

        TODO: 实现真实的高德地图 API 调用
        目前返回 None 以使用降级方案
        """
        logger.info(f"GeoLocationSkill: Fetching location data from AMap for user={user_id}")

        # 未来实现：
        # 1. 调用高德地图轨迹 API 获取用户历史位置
        # 2. 解析 API 响应，提取位置点列表
        # 3. 返回标准化的位置数据结构

        # 临时实现：返回 None 以使用模拟数据降级方案
        # 实际使用时需要：
        # - 申请高德地图轨迹服务 API Key
        # - 实现 OAuth 用户授权获取位置权限
        # - 调用高德轨迹 API 获取数据
        logger.warning("AMap location API not implemented yet, will use mock data as fallback")
        return None

    def _generate_mock_location_data(self, user_id: str) -> dict:
        """生成模拟位置数据（开发环境）"""
        hash_value = hash(user_id) % 100

        # 模拟商圈
        areas = [
            {"name": "朝阳区三里屯", "type": "商圈", "visit_count": 25 + (hash_value % 20)},
            {"name": "海淀区中关村", "type": "办公区", "visit_count": 40 + (hash_value % 10)},
            {"name": "东城区王府井", "type": "商圈", "visit_count": 15 + (hash_value % 15)},
            {"name": "798 艺术区", "type": "文化区", "visit_count": 8 + (hash_value % 10)},
            {"name": "朝阳区 CBD", "type": "办公区", "visit_count": 30 + (hash_value % 20)}
        ]

        return {
            "total_locations": 100 + (hash_value % 200),
            "coverage_area": 50 + (hash_value % 100),
            "frequent_areas": areas[:3 + (hash_value % 3)],
            "home_area": areas[hash_value % 2]["name"] if hash_value < 50 else "朝阳区",
            "work_area": areas[1]["name"] if hash_value < 50 else "海淀区"
        }

    def _identify_home_work(self, location_data: dict) -> dict:
        """识别家庭和工作地点"""
        frequent_areas = location_data.get("frequent_areas", [])

        # 基于访问模式识别
        home = location_data.get("home_area", "未知")
        work = location_data.get("work_area", "未知")

        # 如果没有预设，基于类型推断
        if home == "未知":
            for area in frequent_areas:
                if "居住" in area.get("type", "") or "住宅" in area.get("name", ""):
                    home = area["name"]
                    break

        if work == "未知":
            for area in frequent_areas:
                if "办公" in area.get("type", "") or "商务" in area.get("name", ""):
                    work = area["name"]
                    break

        return {"home": home, "work": work}

    def _identify_frequent_areas(self, location_data: dict) -> List[dict]:
        """识别常去区域"""
        return location_data.get("frequent_areas", [])[:5]

    def _generate_lifestyle_tags(self, frequent_areas: List[dict]) -> List[str]:
        """生成生活质感标签"""
        tags = []

        area_keywords = {
            "商圈": ["时尚", "购物达人"],
            "文化区": ["文艺", "艺术爱好者"],
            "办公区": ["职场精英", "工作狂"],
            "公园": ["户外爱好者", "健康生活"],
            "餐饮": ["美食家", "吃货"],
            "住宅": ["居家型", "生活规律"]
        }

        for area in frequent_areas:
            area_type = area.get("type", "")
            if area_type in area_keywords:
                tags.extend(area_keywords[area_type])

        # 去重
        return list(set(tags))[:5]

    def _calculate_activity_radius(self, location_data: dict, home_work: dict) -> float:
        """计算活动半径"""
        # 基于覆盖面积估算
        coverage_area = location_data.get("coverage_area", 50)
        # 假设圆形区域，计算半径
        return math.sqrt(coverage_area / math.pi)

    def _infer_preferred_distance(self, lifestyle_tags: List[str]) -> str:
        """推断偏好距离"""
        if "户外爱好者" in lifestyle_tags or "健康生活" in lifestyle_tags:
            return "较远（接受跨区域约会）"
        elif "居家型" in lifestyle_tags or "生活规律" in lifestyle_tags:
            return "较近（偏好附近约会）"
        else:
            return "适中"

    def _find_optimal_midpoint(self, profile_1: dict, profile_2: dict) -> dict:
        """找到最优中点"""
        # 简化版本：基于区域名称找中点
        home_1 = profile_1.get("home_district", "")
        home_2 = profile_2.get("home_district", "")

        # 注：当前使用简化映射表，待对接真实地理编码 API
        # 生产环境应使用高德/百度地图 API 的地理编码服务计算精确中点
        if home_1 == home_2:
            return {
                "location": home_1,
                "area_type": "同区域",
                "transportation": "步行/短途"
            }

        # 基于常见区域对中点
        midpoint_map = {
            ("朝阳区", "海淀区"): {"location": "西城区金融街", "area_type": "商圈", "transportation": "地铁 4 号线"},
            ("朝阳区", "东城区"): {"location": "朝阳门", "area_type": "商圈", "transportation": "地铁 2 号线"},
            ("朝阳区", "丰台区"): {"location": "国贸 CBD", "area_type": "商圈", "transportation": "地铁 10 号线"},
            ("海淀区", "东城区"): {"location": "平安里", "area_type": "商圈", "transportation": "地铁 4 号线"},
        }

        key = (home_1, home_2) if home_1 < home_2 else (home_2, home_1)
        return midpoint_map.get(key, {
            "location": "市中心",
            "area_type": "商圈",
            "transportation": "地铁可达"
        })

    def _calculate_distance(self, location_1: str, location_2: str) -> float:
        """计算两个位置之间的距离（公里）"""
        # 注：当前使用简化映射表估算，待对接真实地理编码 API
        # 生产环境应使用高德/百度地图 API 的距离计算服务
        if location_1 == location_2:
            return 0.0

        # 简化估算
        distance_map = {
            ("朝阳区", "海淀区"): 15.0,
            ("朝阳区", "东城区"): 8.0,
            ("朝阳区", "丰台区"): 12.0,
            ("海淀区", "东城区"): 12.0,
            ("海淀区", "丰台区"): 18.0,
            ("东城区", "丰台区"): 10.0,
        }

        key = (location_1, location_2) if location_1 < location_2 else (location_2, location_1)
        return distance_map.get(key, 10.0)

    def _find_date_spots(self, midpoint: dict, date_type: str, profile_1: dict, profile_2: dict) -> List[dict]:
        """寻找约会地点"""
        location = midpoint.get("location", "市中心")

        # 基于约会类型的地点数据库
        date_spots = {
            "casual": [
                {"name": "星巴克臻选", "type": "咖啡厅", "price_range": "50-100 元/人", "match_score": 0.9},
                {"name": "Costa Coffee", "type": "咖啡厅", "price_range": "40-80 元/人", "match_score": 0.85},
                {"name": "漫咖啡", "type": "咖啡厅", "price_range": "60-120 元/人", "match_score": 0.8}
            ],
            "romantic": [
                {"name": "TRB  Hutong", "type": "法式餐厅", "price_range": "500-800 元/人", "match_score": 0.95},
                {"name": "京兆尹", "type": "素食餐厅", "price_range": "400-600 元/人", "match_score": 0.9},
                {"name": "Temple Restaurant Beijing", "type": "创意菜", "price_range": "600-1000 元/人", "match_score": 0.85}
            ],
            "cultural": [
                {"name": "UCCA 尤伦斯当代艺术中心", "type": "艺术展", "price_range": "80-150 元/人", "match_score": 0.95},
                {"name": "中国美术馆", "type": "美术馆", "price_range": "免费 -50 元/人", "match_score": 0.9},
                {"name": "保利剧院", "type": "剧院", "price_range": "200-800 元/人", "match_score": 0.85}
            ],
            "outdoor": [
                {"name": "朝阳公园", "type": "公园", "price_range": "免费", "match_score": 0.9},
                {"name": "奥林匹克森林公园", "type": "公园", "price_range": "免费", "match_score": 0.9},
                {"name": "颐和园", "type": "园林", "price_range": "60 元/人", "match_score": 0.85}
            ]
        }

        spots = date_spots.get(date_type, date_spots["casual"])

        # 添加位置信息
        for spot in spots:
            spot["address"] = f"{location}区域"
            spot["distance_from_midpoint"] = 0.5  # 假设都在中点附近

        return spots

    def _generate_recommendation_message(self, recommendations: List[dict], date_type: str) -> str:
        """生成推荐消息"""
        type_names = {
            "casual": "休闲约会",
            "romantic": "浪漫约会",
            "cultural": "文化之旅",
            "outdoor": "户外漫步"
        }

        message = f"为你们的{type_names.get(date_type, '约会')}推荐了{len(recommendations)}个地点：\n\n"

        for i, spot in enumerate(recommendations[:3], 1):
            message += f"{i}. {spot['name']}（{spot['type']}）\n"
            message += f"   预算：{spot['price_range']} | 匹配度：{spot['match_score'] * 100:.0f}%\n\n"

        message += "选择一个你们都感兴趣的地点，开始美好的约会吧~"

        return message

    def _calculate_geo_compatibility(self, profile_1: dict, profile_2: dict) -> dict:
        """计算地理位置兼容性"""
        # 同区域加分
        same_district = profile_1.get("home_district") == profile_2.get("home_district")

        # 活动范围重叠
        areas_1 = set(a["name"] for a in profile_1.get("frequent_areas", []))
        areas_2 = set(a["name"] for a in profile_2.get("frequent_areas", []))
        overlap = len(areas_1 & areas_2) / max(len(areas_1 | areas_2), 1)

        # 生活方式标签匹配
        tags_1 = set(profile_1.get("lifestyle_tags", []))
        tags_2 = set(profile_2.get("lifestyle_tags", []))
        tag_match = len(tags_1 & tags_2) / max(len(tags_1 | tags_2), 1)

        return {
            "geo_match": 0.9 if same_district else 0.6,
            "lifestyle_match": round(tag_match, 2),
            "activity_range_overlap": round(overlap, 2)
        }

    def _generate_compatibility_interpretation(self, compatibility: dict, profile_1: dict, profile_2: dict) -> dict:
        """生成兼容性解读"""
        geo_match = compatibility.get("geo_match", 0.5)

        if geo_match >= 0.9:
            message = "你们住在同一区域，约会非常方便，可以多安排线下见面~"
        elif geo_match >= 0.6:
            message = "你们距离适中，交通便利的情况下见面很容易~"
        else:
            message = "你们距离较远，建议提前规划好交通，选择中点位置见面~"

        # 共同区域
        areas_1 = [a["name"] for a in profile_1.get("frequent_areas", [])]
        areas_2 = [a["name"] for a in profile_2.get("frequent_areas", [])]
        common = list(set(areas_1) & set(areas_2))

        return {
            "message": message,
            "common_areas": common if common else ["暂无共同常去区域"],
            "distance": {
                "user_1_home": profile_1.get("home_district", "未知"),
                "user_2_home": profile_2.get("home_district", "未知")
            }
        }

    # 内存缓存（开发环境使用，生产环境应使用数据库）
    _geo_profile_cache: Dict[str, dict] = {}

    async def _save_geo_profile(self, user_id: str, profile: dict) -> None:
        """保存地理画像到缓存（生产环境应使用数据库）"""
        # 注：当前使用内存缓存，待对接数据库
        self._geo_profile_cache[user_id] = {
            **profile,
            "updated_at": datetime.now().isoformat()
        }
        logger.info(f"GeoLocationSkill: Profile saved for user={user_id}")

    async def _load_geo_profile(self, user_id: str) -> Optional[dict]:
        """从缓存加载地理画像（生产环境应使用数据库）"""
        # 注：当前使用内存缓存，待对接数据库
        return self._geo_profile_cache.get(user_id)

    def _generate_analysis_message(self, profile: dict) -> str:
        """生成分析结果消息"""
        home = profile.get("home_district", "未知")
        work = profile.get("work_district", "未知")
        tags = profile.get("lifestyle_tags", [])

        message = f"你的常居区域：{home}\n"
        message += f"工作区域：{work}\n"
        if tags:
            message += f"生活标签：{', '.join(tags)}\n"
        message += "\nAI 将基于你的活动范围，为你推荐合适的约会地点~"

        return message

    # 自主触发器

    async def autonomous_trigger(self, user_id: str, trigger_type: str, context: dict) -> dict:
        """
        自主触发地理数据分析

        Args:
            user_id: 用户 ID
            trigger_type: 触发类型
            context: 上下文数据

        Returns:
            触发结果
        """
        logger.info(f"GeoLocationSkill: Autonomous trigger {trigger_type} for {user_id}")

        if trigger_type == "nearby_match_alert":
            return await self._handle_nearby_match(user_id, context)
        elif trigger_type == "weekend_date_suggestion":
            return await self._handle_weekend_suggestion(user_id, context)
        else:
            return {"triggered": False, "reason": "unknown_trigger_type"}

    async def _handle_nearby_match(self, user_id: str, context: dict) -> dict:
        """处理附近匹配提醒"""
        # 检测是否有新的高质量匹配在附近
        nearby_matches = context.get("nearby_matches", [])

        if nearby_matches:
            match = nearby_matches[0]
            distance = match.get("distance", 0)

            if distance < 5:  # 5 公里内
                return {
                    "triggered": True,
                    "should_push": True,
                    "push_message": f"发现一位优质匹配在附近（约{distance}公里），约会很方便哦~"
                }

        return {"triggered": False, "reason": "no_nearby_match"}

    async def _handle_weekend_suggestion(self, user_id: str, context: dict) -> dict:
        """处理周末约会建议"""
        match_id = context.get("match_id")
        target_user_id = context.get("target_user_id")

        if match_id and target_user_id:
            # 推荐周末约会地点
            result = await self._recommend_dates(user_id, target_user_id, "casual")

            return {
                "triggered": True,
                "should_push": True,
                "push_message": "周末快到了，为你们推荐了几个不错的约会地点~",
                "recommendations": result.get("date_recommendations", [])
            }

        return {"triggered": False, "reason": "no_match"}


# 全局 Skill 实例
_geo_location_skill_instance: Optional[GeoLocationSkill] = None


def get_geo_location_skill() -> GeoLocationSkill:
    """获取地理数据 Skill 单例实例"""
    global _geo_location_skill_instance
    if _geo_location_skill_instance is None:
        _geo_location_skill_instance = GeoLocationSkill()
    return _geo_location_skill_instance
