"""爬虫模块"""
from crawler.news_crawler import news_crawler
from crawler.report_crawler import report_crawler
from crawler.enterprise_crawler import enterprise_crawler
from crawler.patent_crawler import patent_crawler
from crawler.social_media_crawler import social_media_crawler

__all__ = [
    'news_crawler',
    'report_crawler',
    'enterprise_crawler',
    'patent_crawler',
    'social_media_crawler'
]
