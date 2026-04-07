"""
v1.9 生态建设 - 应用市场框架、开发者门户、数据合作伙伴计划
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import secrets

router = APIRouter(prefix="/api/v1.9", tags=["v1.9 生态建设"])

# ==================== 数据模型 ====================

class AppMarketApp(BaseModel):
    """应用市场应用"""
    name: str
    description: str
    category: str  # analytics/data/export/automation
    developer_name: str
    developer_email: str
    website_url: Optional[str] = None
    icon_url: Optional[str] = None
    pricing_model: str  # free/freemium/paid
    price: Optional[float] = None
    supported_regions: List[str] = Field(default=["CN"])

class AppMarketAppResponse(AppMarketApp):
    """应用市场应用响应"""
    app_id: str
    status: str  # pending/approved/rejected
    installs: int
    rating: float
    created_at: str
    updated_at: str

class ConnectorApp(BaseModel):
    """连接器应用"""
    name: str
    description: str
    data_source_type: str  # api/database/file
    connection_config: Dict[str, Any]
    auth_type: str  # none/api_key/oauth/basic

class ConnectorAppResponse(ConnectorApp):
    """连接器应用响应"""
    connector_id: str
    status: str  # pending/active/suspended
    installs: int
    created_at: str

class DeveloperProfile(BaseModel):
    """开发者档案"""
    display_name: str
    bio: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    github_url: Optional[str] = None
    skills: List[str] = Field(default=[])

class DeveloperProfileResponse(DeveloperProfile):
    """开发者档案响应"""
    developer_id: str
    email: str
    total_apps: int
    total_installs: int
    total_revenue: float
    rating: float
    joined_at: str

class DataPartnerApplication(BaseModel):
    """数据合作伙伴申请"""
    company_name: str
    contact_name: str
    contact_email: str
    data_type: str  # enterprise/patent/news/financial
    data_description: str
    sample_data_url: Optional[str] = None
    api_documentation_url: Optional[str] = None

class DataPartnerResponse(BaseModel):
    """数据合作伙伴响应"""
    partner_id: str
    company_name: str
    data_type: str
    status: str  # pending/approved/rejected
    partnership_level: str  # basic/premium/enterprise
    created_at: str

class DocumentationSection(BaseModel):
    """文档章节"""
    title: str
    content: str
    order: int
    parent_section: Optional[str] = None

class DocumentationResponse(BaseModel):
    """文档响应"""
    section_id: str
    title: str
    content: str
    order: int
    children: List['DocumentationResponse'] = []
    updated_at: str

# ==================== 模拟数据存储 ====================

_app_market: Dict[str, Dict[str, Any]] = {}
_connectors: Dict[str, Dict[str, Any]] = {}
_developer_profiles: Dict[str, Dict[str, Any]] = {}
_data_partners: Dict[str, Dict[str, Any]] = {}
_documentation: Dict[str, Dict[str, Any]] = {}

# 初始化一些示例数据
def _init_sample_data():
    """初始化示例数据"""
    if not _app_market:
        # 添加示例应用
        sample_apps = [
            {
                "app_id": "app-001",
                "name": "高级数据分析",
                "description": "提供深度数据分析和可视化能力",
                "category": "analytics",
                "developer_name": "数据科技",
                "developer_email": "dev@datatech.com",
                "pricing_model": "freemium",
                "price": 99.0,
                "status": "approved",
                "installs": 1250,
                "rating": 4.8,
                "created_at": "2026-01-15T00:00:00",
                "updated_at": "2026-04-01T00:00:00",
            },
            {
                "app_id": "app-002",
                "name": "自动报告生成器",
                "description": "自动生成精美的商业报告",
                "category": "export",
                "developer_name": "报告大师",
                "developer_email": "hello@reportmaster.com",
                "pricing_model": "paid",
                "price": 199.0,
                "status": "approved",
                "installs": 856,
                "rating": 4.6,
                "created_at": "2026-02-01T00:00:00",
                "updated_at": "2026-03-28T00:00:00",
            },
            {
                "app_id": "app-003",
                "name": "竞品监控助手",
                "description": "实时监控竞品动态并发送预警",
                "category": "automation",
                "developer_name": "监控科技",
                "developer_email": "contact@monitor.com",
                "pricing_model": "free",
                "status": "approved",
                "installs": 3200,
                "rating": 4.5,
                "created_at": "2026-01-20T00:00:00",
                "updated_at": "2026-04-03T00:00:00",
            },
        ]
        for app in sample_apps:
            _app_market[app["app_id"]] = app

    if not _connectors:
        # 添加示例连接器
        sample_connectors = [
            {
                "connector_id": "conn-001",
                "name": "天眼查数据连接器",
                "description": "连接天眼查企业数据 API",
                "data_source_type": "api",
                "connection_config": {
                    "base_url": "https://api.tianyancha.com",
                    "auth_type": "api_key",
                },
                "auth_type": "api_key",
                "status": "active",
                "installs": 580,
                "created_at": "2026-01-10T00:00:00",
            },
            {
                "connector_id": "conn-002",
                "name": "MySQL 数据连接器",
                "description": "连接 MySQL 数据库",
                "data_source_type": "database",
                "connection_config": {
                    "driver": "mysql",
                    "auth_type": "basic",
                },
                "auth_type": "basic",
                "status": "active",
                "installs": 1200,
                "created_at": "2026-01-05T00:00:00",
            },
        ]
        for conn in sample_connectors:
            _connectors[conn["connector_id"]] = conn

    if not _documentation:
        # 初始化文档
        _documentation["doc-001"] = {
            "section_id": "doc-001",
            "title": "快速开始",
            "content": "欢迎使用 AI 商机挖掘平台...",
            "order": 1,
            "children": [],
            "updated_at": "2026-04-01T00:00:00",
        }
        _documentation["doc-002"] = {
            "section_id": "doc-002",
            "title": "API 参考",
            "content": "本平台提供 RESTful API...",
            "order": 2,
            "children": [],
            "updated_at": "2026-04-01T00:00:00",
        }

# ==================== 应用市场 ====================

@router.post("/market/apps", response_model=AppMarketAppResponse, summary="提交应用到市场")
async def submit_app_to_market(app: AppMarketApp, x_developer_id: Optional[str] = Header(None)):
    """
    提交应用到应用市场

    应用类别：
    - analytics: 数据分析类
    - data: 数据增强类
    - export: 报告导出类
    - automation: 自动化类
    """
    _init_sample_data()
    app_id = f"app-{secrets.token_hex(8)}"
    now = datetime.now().isoformat()

    app_data = {
        "app_id": app_id,
        **app.model_dump(),
        "status": "pending",
        "installs": 0,
        "rating": 0.0,
        "created_at": now,
        "updated_at": now,
        "developer_id": x_developer_id or "dev-default",
    }

    _app_market[app_id] = app_data
    return AppMarketAppResponse(**app_data)

@router.get("/market/apps", response_model=List[AppMarketAppResponse], summary="获取应用市场列表")
async def list_market_apps(
    category: Optional[str] = None,
    pricing_model: Optional[str] = None,
    limit: int = 20,
):
    """获取应用市场中的应用列表"""
    _init_sample_data()

    apps = list(_app_market.values())

    # 筛选
    if category:
        apps = [a for a in apps if a["category"] == category]
    if pricing_model:
        apps = [a for a in apps if a["pricing_model"] == pricing_model]

    # 只返回 approved 的应用
    apps = [a for a in apps if a["status"] == "approved"]

    # 按评分排序
    apps = sorted(apps, key=lambda x: x["rating"], reverse=True)

    return [AppMarketAppResponse(**a) for a in apps[:limit]]

@router.get("/market/apps/{app_id}", response_model=AppMarketAppResponse, summary="获取应用详情")
async def get_market_app(app_id: str):
    """获取应用市场的单个应用详情"""
    _init_sample_data()
    if app_id not in _app_market:
        raise HTTPException(status_code=404, detail="App not found")

    return AppMarketAppResponse(**_app_market[app_id])

@router.post("/market/apps/{app_id}/install", summary="安装应用")
async def install_app(app_id: str, x_user_id: Optional[str] = Header(None)):
    """安装应用市场中的应用"""
    _init_sample_data()
    if app_id not in _app_market:
        raise HTTPException(status_code=404, detail="App not found")

    _app_market[app_id]["installs"] += 1

    return {
        "app_id": app_id,
        "status": "installed",
        "message": "应用安装成功",
    }

# ==================== 连接器市场 ====================

@router.post("/connectors", response_model=ConnectorAppResponse, summary="创建连接器")
async def create_connector(connector: ConnectorApp):
    """创建数据连接器"""
    _init_sample_data()
    connector_id = f"conn-{secrets.token_hex(8)}"
    now = datetime.now().isoformat()

    connector_data = {
        "connector_id": connector_id,
        **connector.model_dump(),
        "status": "pending",
        "installs": 0,
        "created_at": now,
    }

    _connectors[connector_id] = connector_data
    return ConnectorAppResponse(**connector_data)

@router.get("/connectors", response_model=List[ConnectorAppResponse], summary="获取连接器列表")
async def list_connectors(data_source_type: Optional[str] = None):
    """获取连接器列表"""
    _init_sample_data()
    connectors = list(_connectors.values())

    if data_source_type:
        connectors = [c for c in connectors if c["data_source_type"] == data_source_type]

    # 只返回 active 的连接器
    connectors = [c for c in connectors if c["status"] == "active"]

    return [ConnectorAppResponse(**c) for c in connectors]

@router.post("/connectors/{connector_id}/install", summary="安装连接器")
async def install_connector(connector_id: str):
    """安装连接器"""
    _init_sample_data()
    if connector_id not in _connectors:
        raise HTTPException(status_code=404, detail="Connector not found")

    _connectors[connector_id]["installs"] += 1

    return {
        "connector_id": connector_id,
        "status": "installed",
        "message": "连接器安装成功",
    }

# ==================== 开发者门户 ====================

@router.post("/developer/profile", response_model=DeveloperProfileResponse, summary="创建开发者档案")
async def create_developer_profile(profile: DeveloperProfile, x_email: str = Header(...)):
    """创建或更新开发者档案"""
    _init_sample_data()
    developer_id = f"dev-{secrets.token_hex(8)}"
    now = datetime.now().isoformat()

    profile_data = {
        "developer_id": developer_id,
        **profile.model_dump(),
        "email": x_email,
        "total_apps": 0,
        "total_installs": 0,
        "total_revenue": 0.0,
        "rating": 0.0,
        "joined_at": now,
    }

    _developer_profiles[developer_id] = profile_data
    return DeveloperProfileResponse(**profile_data)

@router.get("/developer/profile/{developer_id}", response_model=DeveloperProfileResponse, summary="获取开发者档案")
async def get_developer_profile(developer_id: str):
    """获取开发者档案"""
    _init_sample_data()
    if developer_id not in _developer_profiles:
        raise HTTPException(status_code=404, detail="Developer not found")

    return DeveloperProfileResponse(**_developer_profiles[developer_id])

@router.get("/developer/stats", summary="获取开发者统计")
async def get_developer_stats(x_developer_id: Optional[str] = Header(None)):
    """获取开发者统计数据"""
    _init_sample_data()
    if x_developer_id and x_developer_id in _developer_profiles:
        profile = _developer_profiles[x_developer_id]
        return {
            "developer_id": x_developer_id,
            "total_apps": profile["total_apps"],
            "total_installs": profile["total_installs"],
            "total_revenue": profile["total_revenue"],
            "rating": profile["rating"],
        }

    # 返回平台总体统计
    total_apps = len(_app_market)
    total_installs = sum(a["installs"] for a in _app_market.values())
    return {
        "platform_stats": {
            "total_developers": len(_developer_profiles),
            "total_apps": total_apps,
            "total_installs": total_installs,
            "total_connectors": len(_connectors),
        },
    }

# ==================== 数据合作伙伴计划 ====================

@router.post("/data-partners/apply", response_model=DataPartnerResponse, summary="申请成为数据合作伙伴")
async def apply_data_partner(application: DataPartnerApplication):
    """
    申请成为数据合作伙伴

    数据类型：
    - enterprise: 企业工商数据
    - patent: 专利数据
    - news: 新闻舆情数据
    - financial: 财务数据
    """
    partner_id = f"partner-{secrets.token_hex(8)}"
    now = datetime.now().isoformat()

    partner_data = {
        "partner_id": partner_id,
        "company_name": application.company_name,
        "contact_name": application.contact_name,
        "contact_email": application.contact_email,
        "data_type": application.data_type,
        "data_description": application.data_description,
        "status": "pending",
        "partnership_level": "basic",
        "created_at": now,
    }

    _data_partners[partner_id] = partner_data
    return DataPartnerResponse(**partner_data)

@router.get("/data-partners", response_model=List[DataPartnerResponse], summary="获取数据合作伙伴列表")
async def list_data_partners(data_type: Optional[str] = None):
    """获取已批准的数据合作伙伴列表"""
    partners = [p for p in _data_partners.values() if p["status"] == "approved"]

    if data_type:
        partners = [p for p in partners if p["data_type"] == data_type]

    return [DataPartnerResponse(**p) for p in partners]

# ==================== 开发者文档 ====================

@router.get("/docs", response_model=List[DocumentationResponse], summary="获取文档目录")
async def get_documentation_index():
    """获取开发者文档目录"""
    _init_sample_data()
    return [DocumentationResponse(**d) for d in _documentation.values()]

@router.get("/docs/{section_id}", response_model=DocumentationResponse, summary="获取文档章节")
async def get_documentation_section(section_id: str):
    """获取指定文档章节的内容"""
    _init_sample_data()
    if section_id not in _documentation:
        raise HTTPException(status_code=404, detail="Section not found")

    return DocumentationResponse(**_documentation[section_id])

# ==================== SDK 下载 ====================

@router.get("/sdks", summary="获取 SDK 列表")
async def list_sdks():
    """获取可用 SDK 列表"""
    sdks = [
        {
            "name": "Python SDK",
            "version": "1.0.0",
            "download_url": "https://github.com/ai-opportunity-miner/sdk-python",
            "description": "官方 Python SDK",
        },
        {
            "name": "JavaScript SDK",
            "version": "1.0.0-beta",
            "download_url": "https://github.com/ai-opportunity-miner/sdk-js",
            "description": "社区贡献的 JavaScript SDK",
        },
        {
            "name": "Java SDK",
            "version": "0.9.0",
            "download_url": "https://github.com/ai-opportunity-miner/sdk-java",
            "description": "官方 Java SDK (Beta)",
        },
    ]
    return sdks
