"""
配置设置
"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Settings:
    """应用配置"""
    # 服务配置
    app_name: str = "AI Incubation Platform - Portal"
    app_version: str = "3.0.0"
    debug: bool = False

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # AI 配置
    deerflow_api_key: Optional[str] = None
    deerflow_base_url: str = "http://localhost:8080"

    # 子项目端点配置
    project_endpoints: dict = None

    # 置信度阈值
    auto_route_threshold: float = 0.8
    clarification_threshold: float = 0.5

    def __post_init__(self):
        if self.project_endpoints is None:
            self.project_endpoints = {}

        # 从环境变量加载配置
        self.deerflow_api_key = os.getenv("DEERFLOW_API_KEY", self.deerflow_api_key)
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.port = int(os.getenv("PORT", self.port))


# 全局配置实例
settings = Settings(
    app_name="AI Incubation Platform - Portal",
    app_version="3.0.0 AI Native",
)
