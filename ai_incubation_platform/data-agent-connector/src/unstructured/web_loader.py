"""
网页加载器 - 支持静态和动态网页内容抓取
"""
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from .base import UnstructuredDataConnector, UnstructuredConfig, DocumentChunk

try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class WebLoader(UnstructuredDataConnector):
    """网页加载器 - 支持静态和动态网页内容抓取"""

    def __init__(self, config: UnstructuredConfig):
        super().__init__(config)
        self._page_content = ""
        self._metadata = {}
        self._max_depth = config.options.get("max_depth", 0)  # 最大爬取深度
        self._allowed_domains = config.options.get("allowed_domains", [])  # 允许域名

    async def connect(self) -> None:
        """验证 URL 是否有效"""
        if self.config.source_url:
            parsed = urlparse(self.config.source_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL: {self.config.source_url}")
        self._connected = True
        logger.info("Web loader connected", extra={"url": self.config.source_url})

    async def disconnect(self) -> None:
        """断开连接，清理缓存"""
        self._page_content = ""
        self._metadata = {}
        self._content_cache = []
        self._connected = False
        logger.info("Web loader disconnected")

    async def load_content(self) -> List[DocumentChunk]:
        """加载网页内容"""
        if not self._connected:
            await self.connect()

        source_url = self.config.source_url
        if not source_url:
            raise ValueError("source_url is required for web loading")

        text, metadata = await self._fetch_page(source_url)

        self._page_content = text
        self._metadata = metadata

        # 分割成片段
        chunks = self._split_text(text)
        result = []
        for i, chunk in enumerate(chunks):
            result.append(self._create_chunk(
                content=chunk,
                index=i,
                metadata={**metadata, "chunk_type": "web", "url": source_url}
            ))

        self._content_cache = result
        logger.info("Web page loaded", extra={"url": source_url, "chunks": len(result)})
        return result

    async def get_schema(self) -> Dict[str, Any]:
        """获取网页元数据"""
        return {
            "source_type": "web",
            "source_url": self.config.source_url,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "metadata": self._metadata,
            "total_chunks": len(self._content_cache)
        }

    async def _fetch_page(self, url: str) -> tuple:
        """抓取网页内容"""
        # 首先尝试使用 Playwright（支持动态网页）
        try:
            return await self._playwright_fetch(url)
        except ImportError:
            # 备选：使用 aiohttp + BeautifulSoup（仅支持静态）
            try:
                return await self._static_fetch(url)
            except ImportError:
                raise ImportError(
                    "Playwright or beautifulsoup4 is required for web scraping. "
                    "Install with: pip install playwright beautifulsoup4 aiohttp"
                )

    async def _playwright_fetch(self, url: str) -> tuple:
        """使用 Playwright 抓取网页（支持动态内容）"""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # 访问页面
                response = await page.goto(url, timeout=self.config.timeout * 1000)

                # 等待页面加载完成
                await page.wait_for_load_state("networkidle", timeout=self.config.timeout * 1000)

                # 获取页面内容
                title = await page.title()
                html = await page.content()
                text = await page.evaluate("document.body.innerText")

                # 获取所有链接
                links = await page.evaluate("""
                    () => {
                        return Array.from(document.querySelectorAll('a'))
                            .map(a => ({
                                text: a.innerText.trim(),
                                href: a.href
                            }))
                            .filter(l => l.text && l.href)
                            .slice(0, 20);
                    }
                """)

                metadata = {
                    "file_type": "web",
                    "url": url,
                    "title": title,
                    "status_code": response.status,
                    "content_type": response.headers.get("content-type", ""),
                    "link_count": len(links),
                    "links": links,
                    "fetch_method": "playwright"
                }

                return text, metadata

            finally:
                await browser.close()

    async def _static_fetch(self, url: str) -> tuple:
        """使用 aiohttp + BeautifulSoup 抓取网页（仅静态）"""
        import aiohttp
        from bs4 import BeautifulSoup

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=self.config.timeout) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch {url}: Status {response.status}")

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # 移除脚本和样式
                for script in soup(["script", "style", "nav", "footer"]):
                    script.decompose()

                # 获取标题
                title = soup.title.string if soup.title else ""

                # 获取正文内容
                text_parts = []
                for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "article", "main", "section"]):
                    if element.get_text(strip=True):
                        text_parts.append(element.get_text(strip=True))

                text = "\n\n".join(text_parts)

                # 获取链接
                links = []
                for a in soup.find_all("a", href=True)[:20]:
                    links.append({
                        "text": a.get_text(strip=True),
                        "href": a["href"]
                    })

                metadata = {
                    "file_type": "web",
                    "url": url,
                    "title": title,
                    "status_code": response.status,
                    "content_type": response.headers.get("content-type", ""),
                    "link_count": len(links),
                    "links": links,
                    "fetch_method": "static"
                }

                return text, metadata

    @classmethod
    async def scrape_url(cls, url: str, timeout: int = 30) -> Dict[str, Any]:
        """静态方法：快速抓取网页"""
        config = UnstructuredConfig(
            name="temp_scrape",
            source_type="web",
            source_url=url,
            timeout=timeout
        )
        loader = cls(config)
        await loader.connect()
        chunks = await loader.load_content()
        await loader.disconnect()

        return {
            "text": "\n".join(chunk.content for chunk in chunks),
            "metadata": loader._metadata,
            "chunks": [chunk.to_dict() for chunk in chunks]
        }

    async def crawl(self, start_url: str, max_pages: int = 10) -> List[Dict[str, Any]]:
        """爬取多个页面"""
        visited = set()
        to_visit = [start_url]
        results = []

        while to_visit and len(results) < max_pages:
            url = to_visit.pop(0)

            if url in visited:
                continue

            # 检查域名
            parsed = urlparse(url)
            if self._allowed_domains and parsed.netloc not in self._allowed_domains:
                continue

            visited.add(url)

            try:
                config = UnstructuredConfig(
                    name=f"crawl_{len(results)}",
                    source_type="web",
                    source_url=url,
                    timeout=self.config.timeout
                )
                loader = WebLoader(config)
                await loader.connect()
                chunks = await loader.load_content()

                results.append({
                    "url": url,
                    "text": "\n".join(chunk.content for chunk in chunks),
                    "metadata": loader._metadata
                })

                await loader.disconnect()

                # 添加新链接
                for link in loader._metadata.get("links", []):
                    if link["href"] and link["href"].startswith("http"):
                        if link["href"] not in visited:
                            to_visit.append(link["href"])

            except Exception as e:
                logger.error("Failed to crawl page", extra={"url": url, "error": str(e)})
                continue

        return results
