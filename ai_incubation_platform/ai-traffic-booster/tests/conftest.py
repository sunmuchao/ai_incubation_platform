"""
pytest 配置
"""
import pytest
import sys
from pathlib import Path

# 添加 src 到路径以便导入
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_content():
    """示例内容用于测试"""
    return """
    SEO 优化是网站优化的重要组成部分。通过合理的 SEO 优化策略，
    可以显著提升网站在搜索引擎中的排名，从而获得更多的有机流量。

    本文介绍了 SEO 优化的核心技术和实践方法，包括关键词研究、
    内容优化、技术 SEO 等方面。

    ### 关键词研究

    关键词研究是 SEO 优化的基础。选择合适的关键词可以帮助你的内容
    更好地匹配用户搜索意图。

    ### 内容优化

    优质的内容是 SEO 成功的核心。确保你的内容具有原创性、价值性和可读性。

    ### 技术 SEO

    技术 SEO 关注网站的基础设施优化，包括页面加载速度、移动适配、
    网站结构等方面。

    总之，SEO 优化是一个系统工程，需要持续关注和优化。
    """


@pytest.fixture
def sample_keywords():
    """示例关键词列表"""
    return ["SEO 优化", "关键词研究", "内容优化"]


@pytest.fixture
def sample_seo_request(sample_content, sample_keywords):
    """示例 SEO 分析请求"""
    from schemas.seo import SEOAnalysisRequest
    return SEOAnalysisRequest(
        content=sample_content,
        target_keywords=sample_keywords,
        title="SEO 优化完全指南",
        meta_description="本文介绍 SEO 优化的核心技术和实践方法"
    )


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    from unittest.mock import MagicMock
    return MagicMock()
