"""
配置文件
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """应用配置"""

    # 服务配置
    service_host: str = "0.0.0.0"
    service_port: int = 8006
    debug: bool = True

    # ============= P5 真实数据源配置 =============

    # 新闻 API 配置（P5 已实现 - NewsAPI）
    news_api_key: Optional[str] = None
    news_api_url: str = "https://newsapi.org/v2/everything"

    # 企业数据 API 配置（P5 已实现 - OpenCorporates）
    # 默认使用 OpenCorporates API
    enterprise_api_key: Optional[str] = None
    enterprise_api_url: str = "https://api.opencorporates.com/v0.4/companies/search"

    # ============= 可选数据源配置 =============

    # 行业报告 API 配置
    industry_report_api_url: str = "https://api.example.com/reports"
    industry_report_api_key: Optional[str] = None

    # 融资事件 API 配置（P5 预留 - IT 桔子/鲸准）
    financing_api_key: Optional[str] = None
    financing_api_url: str = "https://api.itjuzi.com/api/v1/companies"

    # 专利数据 API 配置（P5 预留 - 国家知识产权局）
    patent_api_key: Optional[str] = None
    patent_api_url: str = "https://api.cnipa.gov.cn/patent/search"

    # 社交媒体 API 配置（P5 预留）
    weibo_api_key: Optional[str] = None
    weibo_api_url: str = "https://api.weibo.com/2/search/statuses"
    twitter_api_key: Optional[str] = None
    twitter_api_url: str = "https://api.twitter.com/2/tweets/search/recent"

    # ============= 其他配置 =============

    # LLM 配置（可选，使用 OpenAI/文心一言/通义千问等）
    llm_api_key: Optional[str] = None
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"
    llm_model: str = "gpt-3.5-turbo"

    # 数据存储配置
    data_dir: str = "./data"
    export_dir: str = "./exports"

    # 数据库配置（可选，默认使用 SQLite）
    database_url: Optional[str] = None

    # DeerFlow 配置（可选）
    deerflow_gateway_url: str = "http://localhost:2026"
    deerflow_config_path: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略未定义的字段

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.export_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "cache"), exist_ok=True)

settings = Settings()
