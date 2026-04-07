"""
企业数据采集器
支持企查查/天眼查 API 和模拟数据模式
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from config.settings import settings
from utils.http_client import http_client
from models.opportunity import SourceType

logger = logging.getLogger(__name__)


class EnterpriseCrawler:
    """企业数据采集器"""

    def __init__(self):
        self.api_key = settings.enterprise_api_key
        self.api_url = settings.enterprise_api_url
        self.use_mock = not self.api_key  # 如果没有配置 API 密钥，使用模拟模式

    async def search_company(self, keyword: str, limit: int = 20) -> List[Dict]:
        """搜索企业信息"""
        if self.use_mock:
            return self._generate_mock_companies(keyword, limit)

        headers = {"X-Api-Key": self.api_key}
        params = {"keyword": keyword, "limit": limit}

        try:
            response = await http_client.async_get(self.api_url, params=params, headers=headers)
            return self._parse_company_response(response)
        except Exception as e:
            logger.error(f"Failed to search company: {str(e)}")
            return self._generate_mock_companies(keyword, limit)

    async def get_company_detail(self, company_id: str) -> Optional[Dict]:
        """获取企业详情"""
        if self.use_mock:
            return self._generate_mock_company_detail(company_id)

        headers = {"X-Api-Key": self.api_key}
        try:
            response = await http_client.async_get(
                f"{self.api_url}/{company_id}",
                headers=headers
            )
            return self._parse_company_detail(response)
        except Exception as e:
            logger.error(f"Failed to get company detail: {str(e)}")
            return None

    def _parse_company_response(self, response: Dict) -> List[Dict]:
        """解析企业 API 响应"""
        companies = response.get("companies", [])
        parsed = []
        for company in companies:
            try:
                parsed.append({
                    "company_id": company["id"],
                    "name": company["name"],
                    "legal_representative": company.get("legalRepresentative", ""),
                    "registered_capital": company.get("registeredCapital", ""),
                    "establish_date": company.get("establishDate", ""),
                    "status": company.get("status", "存续"),
                    "industry": company.get("industry", ""),
                    "address": company.get("address", ""),
                    "source_type": SourceType.ENTERPRISE.value
                })
            except Exception as e:
                logger.warning(f"Failed to parse company: {str(e)}")
                continue
        return parsed

    def _parse_company_detail(self, response: Dict) -> Dict:
        """解析企业详情响应"""
        company = response
        return {
            "company_id": company["id"],
            "name": company["name"],
            "legal_representative": company.get("legalRepresentative", ""),
            "registered_capital": company.get("registeredCapital", ""),
            "establish_date": company.get("establishDate", ""),
            "status": company.get("status", "存续"),
            "industry": company.get("industry", ""),
            "address": company.get("address", ""),
            "business_scope": company.get("businessScope", ""),
            "shareholders": company.get("shareholders", []),
            "investments": company.get("investments", []),
            "patents": company.get("patents", []),
            "trademarks": company.get("trademarks", []),
            "financing_history": company.get("financingHistory", []),
            "source_type": SourceType.ENTERPRISE.value
        }

    def _generate_mock_companies(self, keyword: str, limit: int) -> List[Dict]:
        """生成模拟企业数据"""
        # 模拟不同行业的企业名称前缀
        industry_prefixes = {
            "科技": ["智能", "未来", "创新", "数字", "云", "AI", "数据", "网络"],
            "医疗": ["健康", "生物", "医药", "诊疗", "医疗", "康复", "护理"],
            "金融": ["财富", "资本", "投资", "基金", "资管", "信托", "保险"],
            "制造": ["精密", "智能", "高端", "装备", "机械", "自动化", "机器人"],
            "消费": ["优品", "生活", "时尚", "美食", "家居", "母婴", "美妆"],
            "能源": ["绿色", "新能", "太阳能", "风能", "储能", "电池", "环保"]
        }

        # 根据关键词匹配行业
        matched_industry = "科技"
        for industry in industry_prefixes:
            if industry in keyword or keyword in industry:
                matched_industry = industry
                break

        prefixes = industry_prefixes.get(matched_industry, industry_prefixes["科技"])

        mock_companies = []
        base_date = datetime.now() - timedelta(days=365*3)

        for i in range(limit):
            prefix = prefixes[i % len(prefixes)]
            company_name = f"{prefix}{keyword}科技有限公司"
            establish_years = (i % 10) + 1
            establish_date = base_date - timedelta(days=365*establish_years)
            registered_capital = (i % 20 + 1) * 100  # 100-2000 万

            mock_companies.append({
                "company_id": f"ENT-{keyword}-{i:04d}",
                "name": company_name,
                "legal_representative": f"张{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[i%26]}{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[(i*2)%26]}",
                "registered_capital": f"{registered_capital}万人民币",
                "establish_date": establish_date.strftime("%Y-%m-%d"),
                "status": "存续" if i % 10 != 0 else "注销",
                "industry": f"{keyword}相关",
                "address": f"{'北京市朝阳区' if i % 2 == 0 else '上海市浦东新区'}{'科技园' if i % 3 == 0 else '商务区'}{i}号",
                "source_type": SourceType.ENTERPRISE.value
            })

        return mock_companies

    def _generate_mock_company_detail(self, company_id: str) -> Dict:
        """生成模拟企业详情"""
        # 从 company_id 中提取关键词
        parts = company_id.split("-")
        keyword = parts[1] if len(parts) > 1 else "科技"

        return {
            "company_id": company_id,
            "name": f"{keyword}科技有限公司",
            "legal_representative": "张三",
            "registered_capital": "1000 万人民币",
            "establish_date": (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d"),
            "status": "存续",
            "industry": f"{keyword}行业",
            "address": "北京市朝阳区科技园 1 号",
            "business_scope": f"从事{keyword}领域内的技术开发、技术咨询、技术服务；软件开发；产品销售等",
            "shareholders": [
                {"name": "张三", "ratio": "60%", "type": "自然人"},
                {"name": "李四", "ratio": "30%", "type": "自然人"},
                {"name": "某创投基金", "ratio": "10%", "type": "机构"}
            ],
            "investments": [
                {"company": f"{keyword}子公司 A", "ratio": "100%", "amount": "500 万"},
                {"company": f"{keyword}子公司 B", "ratio": "51%", "amount": "300 万"}
            ] if int(company_id.split("-")[-1]) % 3 == 0 else [],
            "patents": [
                {"name": f"一种{keyword}相关方法", "type": "发明专利", "status": "授权"},
                {"name": f"一种{keyword}系统", "type": "实用新型", "status": "授权"}
            ] if int(company_id.split("-")[-1]) % 2 == 0 else [],
            "trademarks": [
                {"name": f"{keyword}商标", "type": "文字商标", "status": "注册"}
            ],
            "financing_history": [
                {"round": "天使轮", "amount": "500 万", "investors": ["某天使基金"], "date": "2022-01-15"},
                {"round": "A 轮", "amount": "2000 万", "investors": ["某 VC"], "date": "2023-06-20"}
            ] if int(company_id.split("-")[-1]) % 3 == 0 else [],
            "source_type": SourceType.ENTERPRISE.value
        }

    async def get_companies_by_industry(self, industry: str, limit: int = 50) -> List[Dict]:
        """按行业获取企业列表"""
        return await self.search_company(industry, limit)

    async def get_recent_registered_companies(self, days: int = 30, limit: int = 20) -> List[Dict]:
        """获取最近注册的企业"""
        # 这是一个示例方法，实际实现需要 API 支持
        mock_recent = self._generate_mock_companies("新注册", limit)
        for company in mock_recent:
            company["establish_date"] = (datetime.now() - timedelta(days=i % days)).strftime("%Y-%m-%d")
        return mock_recent


enterprise_crawler = EnterpriseCrawler()
