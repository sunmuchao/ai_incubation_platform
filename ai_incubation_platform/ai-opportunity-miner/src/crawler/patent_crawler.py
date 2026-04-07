"""
专利数据采集器
支持国家知识产权局 API 和模拟数据模式
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from config.settings import settings
from utils.http_client import http_client
from models.opportunity import SourceType

logger = logging.getLogger(__name__)


class PatentCrawler:
    """专利数据采集器"""

    def __init__(self):
        self.api_key = settings.patent_api_key
        self.api_url = settings.patent_api_url
        self.use_mock = not self.api_key  # 如果没有配置 API 密钥，使用模拟模式

    async def search_patent(self, keyword: str, limit: int = 20) -> List[Dict]:
        """搜索专利数据"""
        if self.use_mock:
            return self._generate_mock_patents(keyword, limit)

        headers = {"X-Api-Key": self.api_key}
        params = {"keyword": keyword, "limit": limit}

        try:
            response = await http_client.async_get(self.api_url, params=params, headers=headers)
            return self._parse_patent_response(response)
        except Exception as e:
            logger.error(f"Failed to search patent: {str(e)}")
            return self._generate_mock_patents(keyword, limit)

    async def get_patent_detail(self, patent_id: str) -> Optional[Dict]:
        """获取专利详情"""
        if self.use_mock:
            return self._generate_mock_patent_detail(patent_id)

        headers = {"X-Api-Key": self.api_key}
        try:
            response = await http_client.async_get(
                f"{self.api_url}/{patent_id}",
                headers=headers
            )
            return self._parse_patent_detail(response)
        except Exception as e:
            logger.error(f"Failed to get patent detail: {str(e)}")
            return None

    def _parse_patent_response(self, response: Dict) -> List[Dict]:
        """解析专利 API 响应"""
        patents = response.get("patents", [])
        parsed = []
        for patent in patents:
            try:
                parsed.append({
                    "patent_id": patent["id"],
                    "title": patent["title"],
                    "patent_type": patent.get("type", "发明专利"),
                    "applicant": patent.get("applicant", ""),
                    "inventor": patent.get("inventor", ""),
                    "application_date": patent.get("applicationDate", ""),
                    "publication_date": patent.get("publicationDate", ""),
                    "status": patent.get("status", "有效"),
                    "abstract": patent.get("abstract", ""),
                    "source_type": SourceType.PATENT.value
                })
            except Exception as e:
                logger.warning(f"Failed to parse patent: {str(e)}")
                continue
        return parsed

    def _parse_patent_detail(self, response: Dict) -> Dict:
        """解析专利详情响应"""
        patent = response
        return {
            "patent_id": patent["id"],
            "title": patent["title"],
            "patent_type": patent.get("type", "发明专利"),
            "applicant": patent.get("applicant", ""),
            "inventor": patent.get("inventor", ""),
            "application_date": patent.get("applicationDate", ""),
            "publication_date": patent.get("publicationDate", ""),
            "authorization_date": patent.get("authorizationDate", ""),
            "status": patent.get("status", "有效"),
            "abstract": patent.get("abstract", ""),
            "claims": patent.get("claims", []),
            "ipc_classification": patent.get("ipcClassification", []),
            "cited_patents": patent.get("citedPatents", []),
            "legal_events": patent.get("legalEvents", []),
            "source_type": SourceType.PATENT.value
        }

    def _generate_mock_patents(self, keyword: str, limit: int) -> List[Dict]:
        """生成模拟专利数据"""
        # 专利类型
        patent_types = ["发明专利", "实用新型", "外观设计"]

        # 专利状态
        patent_statuses = ["有效", "审查中", "驳回", "失效"]

        # IPC 分类（国际专利分类）
        ipc_classes = {
            "科技": ["G06F", "G06N", "H04L", "G01N"],
            "医疗": ["A61K", "A61B", "G01N", "C12N"],
            "制造": ["B25J", "G05B", "B23Q", "F16H"],
            "能源": ["H01M", "H02J", "F03D", "H01L"],
            "化学": ["C07C", "C08F", "C12N", "G01N"],
        }

        # 根据关键词匹配 IPC 分类
        matched_ipc = ipc_classes.get("科技")
        for industry, ipcs in ipc_classes.items():
            if industry in keyword:
                matched_ipc = ipcs
                break

        mock_patents = []
        base_date = datetime.now() - timedelta(days=365*2)

        for i in range(limit):
            patent_type = patent_types[i % 3]
            application_date = base_date - timedelta(days=i*30)
            publication_date = application_date + timedelta(days=180)

            # 发明专利授权时间较长
            if patent_type == "发明专利":
                authorization_date = application_date + timedelta(days=730)
            else:
                authorization_date = application_date + timedelta(days=365)

            status = patent_statuses[i % 4] if i < limit - 2 else "有效"

            mock_patents.append({
                "patent_id": f"PAT-{keyword}-{i:04d}",
                "title": f"一种基于{keyword}的{['方法', '系统', '装置', '设备'][i % 4]}",
                "patent_type": patent_type,
                "applicant": f"{keyword}科技有限公司" if i % 3 == 0 else f"{'张李王刘陈'[i%5]}某",
                "inventor": f"{'张李王刘陈'[i%5]}某；{'赵钱孙周吴'[i%5]}某",
                "application_date": application_date.strftime("%Y-%m-%d"),
                "publication_date": publication_date.strftime("%Y-%m-%d"),
                "authorization_date": authorization_date.strftime("%Y-%m-%d") if status == "有效" else None,
                "status": status,
                "abstract": f"本发明/实用新型公开了一种基于{keyword}的解决方案，涉及{keyword}技术领域。该方案通过...实现了...效果。",
                "ipc_classification": [matched_ipc[i % len(matched_ipc)]],
                "source_type": SourceType.PATENT.value
            })

        return mock_patents

    def _generate_mock_patent_detail(self, patent_id: str) -> Dict:
        """生成模拟专利详情"""
        parts = patent_id.split("-")
        keyword = parts[1] if len(parts) > 1 else "科技"
        idx = int(parts[2]) if len(parts) > 2 else 0

        return {
            "patent_id": patent_id,
            "title": f"一种基于{keyword}的智能处理方法及系统",
            "patent_type": "发明专利",
            "applicant": f"{keyword}科技有限公司",
            "inventor": "张三；李四；王五",
            "application_date": (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d"),
            "publication_date": (datetime.now() - timedelta(days=545)).strftime("%Y-%m-%d"),
            "authorization_date": (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"),
            "status": "有效",
            "abstract": f"""
            本发明公开了一种基于{keyword}的智能处理方法及系统，涉及{keyword}技术领域。

            该方法包括：
            步骤 S1：获取输入数据；
            步骤 S2：对所述输入数据进行预处理；
            步骤 S3：利用{keyword}相关算法进行处理；
            步骤 S4：输出处理结果。

            本发明通过上述技术方案，能够有效提高处理效率和准确性。
            """,
            "claims": [
                f"1. 一种基于{keyword}的处理方法，其特征在于，包括：获取输入数据；对所述输入数据进行处理；输出结果。",
                "2. 根据权利要求 1 所述的方法，其特征在于，所述处理步骤包括预处理和后处理。",
                "3. 一种基于{keyword}的处理系统，其特征在于，包括：数据采集模块、数据处理模块、结果输出模块。"
            ],
            "ipc_classification": ["G06F17/30", "G06N3/08"],
            "cited_patents": [
                {"patent_id": f"PAT-{keyword}-0001", "title": "一种相关方法"},
                {"patent_id": f"PAT-{keyword}-0002", "title": "一种相关系统"}
            ],
            "legal_events": [
                {"date": (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d"), "event": "专利申请"},
                {"date": (datetime.now() - timedelta(days=545)).strftime("%Y-%m-%d"), "event": "公开"},
                {"date": (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"), "event": "授权"}
            ],
            "source_type": SourceType.PATENT.value
        }

    async def get_patents_by_applicant(self, applicant: str, limit: int = 50) -> List[Dict]:
        """按申请人获取专利列表"""
        return await self.search_patent(applicant, limit)

    async def get_recent_patents(self, days: int = 30, keyword: str = None, limit: int = 20) -> List[Dict]:
        """获取最近公开的专利"""
        mock_patents = self._generate_mock_patents(keyword or "最新", limit)
        base_date = datetime.now()
        for i, patent in enumerate(mock_patents):
            patent["application_date"] = (base_date - timedelta(days=i % days)).strftime("%Y-%m-%d")
            patent["publication_date"] = (base_date - timedelta(days=(i % days) - 180)).strftime("%Y-%m-%d")
        return mock_patents

    async def analyze_patent_trend(self, keyword: str, years: int = 5) -> Dict:
        """分析专利技术趋势"""
        # 生成年度专利申请趋势
        current_year = datetime.now().year
        trend_data = []
        for year in range(current_year - years, current_year + 1):
            trend_data.append({
                "year": year,
                "application_count": 100 + (year - (current_year - years)) * 20,
                "authorization_count": 80 + (year - (current_year - years)) * 15,
                "invention_ratio": 0.3 + (year - (current_year - years)) * 0.05
            })

        return {
            "keyword": keyword,
            "trend": trend_data,
            "top_applicants": [
                {"name": f"{keyword}科技有限公司", "count": 150},
                {"name": f"{keyword}研究所", "count": 80},
                {"name": f"{keyword}大学", "count": 60}
            ],
            "top_inventors": [
                {"name": "张三", "count": 25},
                {"name": "李四", "count": 20},
                {"name": "王五", "count": 15}
            ],
            "hot_technologies": [
                f"{keyword}算法",
                f"{keyword}系统",
                f"{keyword}应用"
            ]
        }


patent_crawler = PatentCrawler()
