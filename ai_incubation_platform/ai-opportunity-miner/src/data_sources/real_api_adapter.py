"""
真实 API 数据适配器
支持多数据源接入和自动降级策略

P5 阶段已接入的真实数据源：
1. NewsAPI - 全球新闻数据（https://newsapi.org/）
2. OpenCorporates - 企业工商数据（https://opencorporates.com/）

降级策略:
1. 真实 API 可用 -> 使用真实数据
2. 真实 API 不可用 -> 使用缓存数据
3. 缓存数据过期 -> 使用模拟数据 + 提示
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    """数据源类型"""
    ENTERPRISE = "enterprise"  # 企业数据
    FINANCING = "financing"  # 融资事件
    PATENT = "patent"  # 专利数据
    NEWS = "news"  # 新闻数据
    SOCIAL = "social"  # 社交媒体


class DataSourceStatus(str, Enum):
    """数据源状态"""
    ACTIVE = "active"  # 活跃
    DEGRADED = "degraded"  # 降级（使用缓存）
    OFFLINE = "offline"  # 离线（使用模拟数据）


class DataSourceConfig:
    """数据源配置"""
    def __init__(
        self,
        name: str,
        api_key: Optional[str] = None,
        api_url: str = "",
        timeout: int = 30,
        retry_count: int = 3,
        rate_limit: int = 100,  # 每分钟请求数限制
        cache_ttl: int = 3600,  # 缓存过期时间（秒）
    ):
        self.name = name
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout
        self.retry_count = retry_count
        self.rate_limit = rate_limit
        self.cache_ttl = cache_ttl


class RealDataAdapter:
    """
    真实 API 数据适配器

    支持的数据源:
    - 天眼查/企查查：企业工商数据
    - IT 桔子/鲸准：融资事件数据
    - 国家知识产权局：专利数据
    - 新闻 API：实时新闻

    降级策略:
    1. 真实 API 可用 -> 使用真实数据
    2. 真实 API 不可用 -> 使用缓存数据
    3. 缓存数据过期 -> 使用模拟数据 + 提示
    """

    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 数据源配置
        self._configs: Dict[DataSourceType, DataSourceConfig] = {}
        # 数据源状态
        self._status: Dict[DataSourceType, DataSourceStatus] = {}
        # 缓存的数据
        self._cache: Dict[str, Any] = {}

        # 初始化默认配置
        self._init_default_configs()

    def _init_default_configs(self):
        """初始化默认数据源配置"""
        from config.settings import settings

        # 企业数据源配置（天眼查/企查查）
        self._configs[DataSourceType.ENTERPRISE] = DataSourceConfig(
            name="enterprise",
            api_key=settings.enterprise_api_key,
            api_url=settings.enterprise_api_url,
            cache_ttl=86400 * 7,  # 7 天缓存
        )

        # 融资事件数据源配置（IT 桔子/鲸准）
        self._configs[DataSourceType.FINANCING] = DataSourceConfig(
            name="financing",
            api_key=settings.financing_api_key,
            api_url=settings.financing_api_url,
            cache_ttl=86400,  # 1 天缓存
        )

        # 专利数据源配置
        self._configs[DataSourceType.PATENT] = DataSourceConfig(
            name="patent",
            api_key=settings.patent_api_key,
            api_url=settings.patent_api_url,
            cache_ttl=86400 * 30,  # 30 天缓存
        )

        # 新闻数据源配置
        self._configs[DataSourceType.NEWS] = DataSourceConfig(
            name="news",
            api_key=settings.news_api_key,
            api_url=settings.news_api_url,
            cache_ttl=3600,  # 1 小时缓存
        )

        # 初始化状态
        for data_type, config in self._configs.items():
            if config.api_key:
                self._status[data_type] = DataSourceStatus.ACTIVE
            else:
                self._status[data_type] = DataSourceStatus.OFFLINE

    def configure(
        self,
        data_type: DataSourceType,
        api_key: Optional[str] = None,
        api_url: str = "",
        **kwargs
    ):
        """配置数据源"""
        if data_type not in self._configs:
            self._configs[data_type] = DataSourceConfig(name=data_type.value)

        config = self._configs[data_type]
        if api_key:
            config.api_key = api_key
        if api_url:
            config.api_url = api_url

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # 更新状态
        if config.api_key:
            self._status[data_type] = DataSourceStatus.ACTIVE
        else:
            self._status[data_type] = DataSourceStatus.OFFLINE

        logger.info(f"Configured data source {data_type.value}: status={self._status[data_type].value}")

    def get_status(self, data_type: DataSourceType) -> DataSourceStatus:
        """获取数据源状态"""
        return self._status.get(data_type, DataSourceStatus.OFFLINE)

    def get_all_status(self) -> Dict[str, str]:
        """获取所有数据源状态"""
        return {t.value: s.value for t, s in self._status.items()}

    async def query_enterprise(
        self,
        keyword: str,
        limit: int = 20,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        查询企业信息

        降级策略:
        1. 尝试调用天眼查/企查查 API
        2. API 失败则使用缓存
        3. 缓存过期则生成模拟数据
        """
        cache_key = f"enterprise:{keyword}:{limit}"

        # 尝试从缓存获取
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.info(f"Cache hit for enterprise query: {keyword}")
                return cached

        # 检查数据源状态
        status = self.get_status(DataSourceType.ENTERPRISE)

        if status == DataSourceStatus.ACTIVE:
            try:
                # 调用真实 API
                result = await self._call_enterprise_api(keyword, limit)
                if result:
                    self._save_to_cache(cache_key, result)
                    return result
            except Exception as e:
                logger.warning(f"Enterprise API call failed: {e}")
                self._status[DataSourceType.ENTERPRISE] = DataSourceStatus.DEGRADED

        # 降级到模拟数据
        logger.info(f"Using mock data for enterprise query: {keyword}")
        mock_result = self._generate_mock_enterprise_data(keyword, limit)
        return mock_result

    async def _call_enterprise_api(
        self,
        keyword: str,
        limit: int
    ) -> Optional[List[Dict]]:
        """调用企业数据 API

        支持的 API:
        1. OpenCorporates (https://opencorporates.com/) - 免费全球企业数据
        2. 天眼查/企查查 - 需要商务合作获取 API

        OpenCorporates 免费计划：
        - API URL: https://api.opencorporates.com/v0.4/companies/search
        - 限制：需注明数据来源，非商业用途免费
        """
        config = self._configs.get(DataSourceType.ENTERPRISE)
        if not config or not config.api_key:
            return None

        # 判断是否使用 OpenCorporates
        if "opencorporates" in config.api_url.lower() or not config.api_url:
            return await self._call_opencorporates_api(keyword, limit, config)
        else:
            # 使用自定义 API（如天眼查/企查查）
            return await self._call_custom_enterprise_api(keyword, limit, config)

    async def _call_opencorporates_api(
        self,
        keyword: str,
        limit: int,
        config: DataSourceConfig
    ) -> Optional[List[Dict]]:
        """调用 OpenCorporates 企业数据 API"""
        base_url = "https://api.opencorporates.com/v0.4/companies/search"
        params = {
            "q": keyword,
            "per_page": min(limit, 50),  # OpenCorporates 最大限制 50
            "api_token": config.api_key
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    base_url,
                    params=params,
                    timeout=config.timeout
                )
                response.raise_for_status()
                data = response.json()

                results = []
                companies = data.get("results", {}).get("companies", [])
                for company in companies[:limit]:
                    company_data = company.get("company", {})
                    results.append({
                        "company_id": company_data.get("opencorporates_url", ""),
                        "name": company_data.get("name", ""),
                        "jurisdiction": company_data.get("jurisdiction_code", ""),
                        "created_date": company_data.get("incorporation_date", ""),
                        "status": company_data.get("current_status", ""),
                        "company_type": company_data.get("company_type", ""),
                        "address": company_data.get("registered_address_in_full", ""),
                        "source_type": "enterprise",
                        "source": "OpenCorporates",
                        "_mock": False
                    })
                logger.info(f"Successfully fetched {len(results)} companies from OpenCorporates")
                return results
        except httpx.TimeoutException:
            logger.warning(f"OpenCorporates request timed out")
            self._status[DataSourceType.ENTERPRISE] = DataSourceStatus.DEGRADED
            return None
        except httpx.HTTPError as e:
            logger.warning(f"OpenCorporates HTTP error: {e}")
            self._status[DataSourceType.ENTERPRISE] = DataSourceStatus.DEGRADED
            return None
        except Exception as e:
            logger.warning(f"OpenCorporates call failed: {e}")
            return None

    async def _call_custom_enterprise_api(
        self,
        keyword: str,
        limit: int,
        config: DataSourceConfig
    ) -> Optional[List[Dict]]:
        """调用自定义企业数据 API（如天眼查/企查查）"""
        headers = {
            "X-Api-Key": config.api_key,
            "Content-Type": "application/json"
        }
        params = {"keyword": keyword, "limit": limit}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    config.api_url,
                    params=params,
                    headers=headers,
                    timeout=config.timeout
                )
                response.raise_for_status()
                data = response.json()
                # 适配不同 API 的响应格式
                result = data.get("data", data.get("result", []))
                if isinstance(result, list):
                    logger.info(f"Successfully fetched {len(result)} companies from custom API")
                    return result
                return None
        except httpx.TimeoutException:
            logger.warning(f"Custom enterprise API request timed out")
            self._status[DataSourceType.ENTERPRISE] = DataSourceStatus.DEGRADED
            return None
        except httpx.HTTPError as e:
            logger.warning(f"Custom enterprise API HTTP error: {e}")
            self._status[DataSourceType.ENTERPRISE] = DataSourceStatus.DEGRADED
            return None
        except Exception as e:
            logger.warning(f"Custom enterprise API call failed: {e}")
            return None

    async def query_financing(
        self,
        company_name: str = None,
        industry: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 50,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        查询融资事件

        支持的数据源:
        - IT 桔子
        - 鲸准
        - 清科私募通
        """
        cache_key = f"financing:{company_name}:{industry}:{start_date}:{end_date}:{limit}"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached

        status = self.get_status(DataSourceType.FINANCING)

        if status == DataSourceStatus.ACTIVE:
            try:
                result = await self._call_financing_api(
                    company_name, industry, start_date, end_date, limit
                )
                if result:
                    self._save_to_cache(cache_key, result)
                    return result
            except Exception as e:
                logger.warning(f"Financing API call failed: {e}")
                self._status[DataSourceType.FINANCING] = DataSourceStatus.DEGRADED

        # 降级到模拟数据
        mock_result = self._generate_mock_financing_data(
            company_name, industry, start_date, end_date, limit
        )
        return mock_result

    async def _call_financing_api(
        self,
        company_name: str,
        industry: str,
        start_date: str,
        end_date: str,
        limit: int
    ) -> Optional[List[Dict]]:
        """调用融资事件 API"""
        config = self._configs.get(DataSourceType.FINANCING)
        if not config or not config.api_key:
            return None

        # TODO: 实现真实的 API 调用
        logger.debug(f"Would call financing API: {config.api_url}")
        return None

    async def query_patent(
        self,
        keyword: str,
        patent_type: str = None,
        limit: int = 20,
        use_cache: bool = True
    ) -> List[Dict]:
        """查询专利信息"""
        cache_key = f"patent:{keyword}:{patent_type}:{limit}"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached

        status = self.get_status(DataSourceType.PATENT)

        if status == DataSourceStatus.ACTIVE:
            try:
                result = await self._call_patent_api(keyword, patent_type, limit)
                if result:
                    self._save_to_cache(cache_key, result)
                    return result
            except Exception as e:
                logger.warning(f"Patent API call failed: {e}")
                self._status[DataSourceType.PATENT] = DataSourceStatus.DEGRADED

        mock_result = self._generate_mock_patent_data(keyword, patent_type, limit)
        return mock_result

    async def _call_patent_api(
        self,
        keyword: str,
        patent_type: str,
        limit: int
    ) -> Optional[List[Dict]]:
        """调用专利 API"""
        config = self._configs.get(DataSourceType.PATENT)
        if not config or not config.api_key:
            return None

        logger.debug(f"Would call patent API: {config.api_url}")
        return None

    async def query_news(
        self,
        keyword: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = 20,
        use_cache: bool = True
    ) -> List[Dict]:
        """查询新闻"""
        cache_key = f"news:{keyword}:{start_date}:{end_date}:{limit}"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached

        status = self.get_status(DataSourceType.NEWS)

        if status == DataSourceStatus.ACTIVE:
            try:
                result = await self._call_news_api(keyword, start_date, end_date, limit)
                if result:
                    self._save_to_cache(cache_key, result)
                    return result
            except Exception as e:
                logger.warning(f"News API call failed: {e}")
                self._status[DataSourceType.NEWS] = DataSourceStatus.DEGRADED

        mock_result = self._generate_mock_news_data(keyword, start_date, end_date, limit)
        return mock_result

    async def _call_news_api(
        self,
        keyword: str,
        start_date: str,
        end_date: str,
        limit: int
    ) -> Optional[List[Dict]]:
        """调用新闻 API（NewsAPI）

        API 文档：https://newsapi.org/docs/endpoints/everything
        免费计划：100 次/天，适合开发和测试
        """
        config = self._configs.get(DataSourceType.NEWS)
        if not config or not config.api_key:
            return None

        # 构建 NewsAPI 请求
        url = config.api_url or "https://newsapi.org/v2/everything"
        params = {
            "q": keyword,
            "language": "zh",
            "sortBy": "relevancy",
            "pageSize": min(limit, 100),  # NewsAPI 最大限制 100
            "apiKey": config.api_key
        }

        # 添加日期范围（如果提供）
        if start_date:
            params["from"] = start_date
        if end_date:
            params["to"] = end_date

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    timeout=config.timeout
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "ok":
                    articles = data.get("articles", [])
                    results = []
                    for article in articles[:limit]:
                        results.append({
                            "title": article.get("title", ""),
                            "content": article.get("description", ""),
                            "source": article.get("source", {}).get("name", ""),
                            "url": article.get("url", ""),
                            "publish_date": article.get("publishedAt", ""),
                            "source_type": "news",
                            "_mock": False
                        })
                    logger.info(f"Successfully fetched {len(results)} news articles from NewsAPI")
                    return results
                else:
                    logger.warning(f"NewsAPI returned error: {data.get('message', 'Unknown error')}")
                    return None
        except httpx.TimeoutException:
            logger.warning(f"NewsAPI request timed out")
            self._status[DataSourceType.NEWS] = DataSourceStatus.DEGRADED
            return None
        except httpx.HTTPError as e:
            logger.warning(f"NewsAPI HTTP error: {e}")
            self._status[DataSourceType.NEWS] = DataSourceStatus.DEGRADED
            return None
        except Exception as e:
            logger.warning(f"NewsAPI call failed: {e}")
            return None

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        cache_file = self.cache_dir / f"{self._safe_key(key)}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查缓存是否过期
            cached_at = data.get("_cached_at", 0)
            cache_ttl = data.get("_ttl", 3600)
            if datetime.now().timestamp() - cached_at > cache_ttl:
                logger.debug(f"Cache expired for key: {key}")
                return None

            return data.get("data")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return None

    def _save_to_cache(self, key: str, data: Any, ttl: int = None):
        """保存数据到缓存"""
        cache_file = self.cache_dir / f"{self._safe_key(key)}.json"

        # 获取 TTL
        for data_type, config in self._configs.items():
            if data_type.value in key:
                ttl = ttl or config.cache_ttl
                break
        ttl = ttl or 3600

        cache_data = {
            "data": data,
            "_cached_at": datetime.now().timestamp(),
            "_ttl": ttl
        }

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved cache for key: {key}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _safe_key(self, key: str) -> str:
        """生成安全的缓存文件名"""
        import hashlib
        return hashlib.md5(key.encode()).hexdigest()

    def clear_cache(self, data_type: DataSourceType = None):
        """清除缓存"""
        if data_type:
            # 清除特定数据源的缓存
            pattern = f"{data_type.value}:"
            for cache_file in self.cache_dir.glob("*.json"):
                with open(cache_file, 'r') as f:
                    try:
                        data = json.load(f)
                        if pattern in data.get("_key", ""):
                            cache_file.unlink()
                    except:
                        pass
        else:
            # 清除所有缓存
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
        logger.info("Cache cleared")

    # ========== 模拟数据生成方法 ==========

    def _generate_mock_enterprise_data(self, keyword: str, limit: int) -> List[Dict]:
        """生成模拟企业数据"""
        industry_prefixes = {
            "科技": ["智能", "未来", "创新", "数字", "云", "AI", "数据", "网络"],
            "医疗": ["健康", "生物", "医药", "诊疗", "医疗", "康复"],
            "金融": ["财富", "资本", "投资", "基金", "资管", "信托"],
            "制造": ["精密", "智能", "高端", "装备", "机械", "自动化"],
            "消费": ["优品", "生活", "时尚", "美食", "家居", "母婴"],
        }

        matched_industry = "科技"
        for industry in industry_prefixes:
            if industry in keyword:
                matched_industry = industry
                break

        prefixes = industry_prefixes.get(matched_industry, ["智能", "科技"])

        from datetime import datetime, timedelta
        base_date = datetime.now() - timedelta(days=365*3)

        results = []
        for i in range(limit):
            prefix = prefixes[i % len(prefixes)]
            company_name = f"{prefix}{keyword}科技有限公司"
            establish_years = (i % 10) + 1
            establish_date = base_date - timedelta(days=365*establish_years)
            registered_capital = (i % 20 + 1) * 100

            results.append({
                "company_id": f"ENT-{keyword}-{i:04d}",
                "name": company_name,
                "legal_representative": f"张{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[i%26]}",
                "registered_capital": f"{registered_capital}万人民币",
                "establish_date": establish_date.strftime("%Y-%m-%d"),
                "status": "存续",
                "industry": f"{keyword}相关",
                "address": f"{'北京市朝阳区' if i % 2 == 0 else '上海市浦东新区'}科技园{i}号",
                "source_type": "enterprise",
                "_mock": True,
                "_warning": "数据源未配置，使用模拟数据。请配置 ENTERPRISE_API_KEY 以使用真实数据。"
            })

        return results

    def _generate_mock_financing_data(
        self,
        company_name: str,
        industry: str,
        start_date: str,
        end_date: str,
        limit: int
    ) -> List[Dict]:
        """生成模拟融资事件数据"""
        companies = [
            "字节跳动", "小红书", "理想汽车", "小鹏汽车", "完美日记",
            "喜茶", "泡泡玛特", "得物", "货拉拉", "快狗打车"
        ]

        rounds = ["天使轮", "Pre-A", "A 轮", "B 轮", "C 轮", "D 轮", "战略投资"]
        investors = [
            ["红杉资本", "IDG 资本"],
            ["高瓴资本", "腾讯投资"],
            ["阿里巴巴战投", "字节跳动战投"],
            ["美团龙珠", "顺为资本"],
            ["源码资本", "经纬创投"],
        ]

        from datetime import datetime, timedelta
        base_date = datetime.now() - timedelta(days=365)

        results = []
        for i in range(limit):
            company = company_name or companies[i % len(companies)]
            round_name = rounds[i % len(rounds)]
            amount = (i % 10 + 1) * 1000  # 1000 万 -1 亿

            results.append({
                "company_name": company,
                "industry": industry or "科技",
                "round": round_name,
                "amount": f"{amount}万人民币",
                "investors": investors[i % len(investors)],
                "investment_date": (base_date + timedelta(days=i*30)).strftime("%Y-%m-%d"),
                "source_type": "financing",
                "_mock": True,
                "_warning": "数据源未配置，使用模拟数据。请配置 FINANCING_API_KEY 以使用真实数据。"
            })

        return results

    def _generate_mock_patent_data(
        self,
        keyword: str,
        patent_type: str,
        limit: int
    ) -> List[Dict]:
        """生成模拟专利数据"""
        types = ["发明专利", "实用新型", "外观设计"]
        statuses = ["授权", "实审", "申请"]

        results = []
        for i in range(limit):
            results.append({
                "patent_id": f"PAT-{keyword}-{i:04d}",
                "name": f"一种{keyword}相关的专利方法或系统{i}",
                "type": patent_type or types[i % len(types)],
                "status": statuses[i % len(statuses)],
                "applicant": f"{keyword}科技有限公司",
                "inventor": f"发明人{i}",
                "application_date": f"202{ i % 4}-0{i % 9 + 1}-01",
                "source_type": "patent",
                "_mock": True
            })

        return results

    def _generate_mock_news_data(
        self,
        keyword: str,
        start_date: str,
        end_date: str,
        limit: int
    ) -> List[Dict]:
        """生成模拟新闻数据"""
        sources = ["36 氪", "界面新闻", "财联社", "晚点 LatePost", "投资界"]

        from datetime import datetime, timedelta
        base_date = datetime.now() - timedelta(days=30)

        results = []
        for i in range(limit):
            results.append({
                "title": f"{keyword}领域重要新闻：行业最新动态和趋势分析{i}",
                "content": f"这里是关于{keyword}的新闻内容摘要。据报道，{keyword}行业最近出现了新的发展趋势...",
                "source": sources[i % len(sources)],
                "url": f"https://example.com/news/{i}",
                "publish_date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "source_type": "news",
                "_mock": True,
                "_warning": "数据源未配置，使用模拟数据。请配置 NEWS_API_KEY 以使用真实数据。"
            })

        return results


# 全局适配器实例
data_adapter = RealDataAdapter()
