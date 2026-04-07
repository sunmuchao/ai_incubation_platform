#!/usr/bin/env python3
"""
Nginx日志导入示例脚本
用于将Nginx日志导入到AI流量曝光平台
"""
import re
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import requests
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Nginx日志格式正则表达式
# 对应文档中定义的ai_traffic_json格式
NGINX_JSON_PATTERN = re.compile(r'\{.*\}')

# Nginx默认日志格式解析（非JSON格式）
NGINX_DEFAULT_PATTERN = re.compile(
    r'(?P<remote_addr>\S+) '
    r'(?P<remote_user>\S+) '
    r'(?P<remote_user>\S+) '
    r'\[(?P<timestamp>[^\]]+)\] '
    r'"(?P<request_method>\S+) '
    r'(?P<request_uri>\S+) '
    r'(?P<server_protocol>\S+)" '
    r'(?P<status>\d+) '
    r'(?P<body_bytes_sent>\d+) '
    r'"(?P<http_referer>[^"]*)" '
    r'"(?P<http_user_agent>[^"]*)"'
)

# 流量来源映射
SOURCE_MAPPING = {
    'google': 'organic_search',
    'baidu': 'organic_search',
    'bing': 'organic_search',
    'sogou': 'organic_search',
    '360': 'organic_search',
    'facebook': 'social',
    'facebook.com': 'social',
    'twitter.com': 'social',
    'weibo.com': 'social',
    'weixin': 'social',
    'qq.com': 'social',
    'linkedin.com': 'social',
    'youtube.com': 'social',
    'instagram.com': 'social',
    'tiktok.com': 'social',
    'xiaohongshu.com': 'social',
    'zhihu.com': 'social',
    'douban.com': 'social',
    'email': 'email',
    'mail': 'email',
    'cpc': 'paid_search',
    'ppc': 'paid_search',
    'ad': 'paid_search',
    'banner': 'display',
    'affiliate': 'affiliate'
}

class NginxLogParser:
    """Nginx日志解析器"""

    def __init__(self, log_format: str = 'json'):
        self.log_format = log_format

    def parse_line(self, line: str) -> Optional[Dict]:
        """解析单行日志"""
        line = line.strip()
        if not line:
            return None

        try:
            if self.log_format == 'json':
                # 解析JSON格式日志
                match = NGINX_JSON_PATTERN.search(line)
                if not match:
                    return None
                log_data = json.loads(match.group())
                return self._standardize_json_log(log_data)
            else:
                # 解析默认格式日志
                match = NGINX_DEFAULT_PATTERN.match(line)
                if not match:
                    return None
                log_data = match.groupdict()
                return self._standardize_default_log(log_data)

        except Exception as e:
            logger.debug(f"解析日志失败: {e}, line: {line[:100]}...")
            return None

    def _standardize_json_log(self, log_data: Dict) -> Dict:
        """标准化JSON格式日志"""
        # 解析时间戳
        timestamp = log_data.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                date_str = dt.date().isoformat()
            except:
                date_str = datetime.now().date().isoformat()
        else:
            date_str = datetime.now().date().isoformat()

        # 解析URL和路径
        request_uri = log_data.get('request_uri', '')
        path = request_uri.split('?')[0] if '?' in request_uri else request_uri

        # 识别流量来源
        source, medium, campaign, keyword = self._extract_utm_parameters(log_data)
        if not source:
            source = self._detect_source_from_referrer(log_data.get('http_referer', ''))

        # 标准化数据
        return {
            "date": date_str,
            "timestamp": timestamp,
            "url": request_uri,
            "domain": log_data.get('host', ''),
            "path": path,
            "status_code": int(log_data.get('status', 0)),
            "user_agent": log_data.get('http_user_agent', ''),
            "ip_address": log_data.get('remote_addr', ''),
            "referrer": log_data.get('http_referer', ''),
            "source": source,
            "medium": medium,
            "campaign": campaign,
            "keyword": keyword,
            "session_id": log_data.get('session_id', ''),
            "user_id": log_data.get('user_id', ''),
            "page_load_time": float(log_data.get('request_time', 0)),
            "is_bounce": False,  # 需要根据会话分析判断
            "is_conversion": False,  # 需要根据转化目标判断
            "conversion_value": 0.0
        }

    def _standardize_default_log(self, log_data: Dict) -> Dict:
        """标准化默认格式日志"""
        # 解析时间戳
        timestamp_str = log_data.get('timestamp', '')
        date_str = datetime.now().date().isoformat()
        if timestamp_str:
            try:
                dt = datetime.strptime(timestamp_str, "%d/%b/%Y:%H:%M:%S %z")
                date_str = dt.date().isoformat()
            except:
                pass

        # 解析URL和路径
        request_uri = log_data.get('request_uri', '')
        path = request_uri.split('?')[0] if '?' in request_uri else request_uri

        # 识别流量来源
        source = self._detect_source_from_referrer(log_data.get('http_referer', ''))

        return {
            "date": date_str,
            "timestamp": timestamp_str,
            "url": request_uri,
            "domain": "",
            "path": path,
            "status_code": int(log_data.get('status', 0)),
            "user_agent": log_data.get('http_user_agent', ''),
            "ip_address": log_data.get('remote_addr', ''),
            "referrer": log_data.get('http_referer', ''),
            "source": source,
            "medium": "",
            "campaign": "",
            "keyword": "",
            "session_id": "",
            "user_id": "",
            "page_load_time": 0.0,
            "is_bounce": False,
            "is_conversion": False,
            "conversion_value": 0.0
        }

    def _extract_utm_parameters(self, log_data: Dict) -> tuple:
        """从URL中提取UTM参数"""
        request_uri = log_data.get('request_uri', '')
        source = log_data.get('utm_source', '')
        medium = log_data.get('utm_medium', '')
        campaign = log_data.get('utm_campaign', '')
        keyword = log_data.get('utm_term', '')

        # 如果日志中没有，尝试从URL解析
        if not source and '?' in request_uri:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(request_uri)
            query_params = parse_qs(parsed.query)
            source = query_params.get('utm_source', [''])[0]
            medium = query_params.get('utm_medium', [''])[0]
            campaign = query_params.get('utm_campaign', [''])[0]
            keyword = query_params.get('utm_term', [''])[0]

        return source, medium, campaign, keyword

    def _detect_source_from_referrer(self, referrer: str) -> str:
        """从Referrer识别流量来源

        :param referrer: 来源URL
        :return: 标准化的来源类型
        """
        if not referrer or referrer == '-':
            return 'direct'

        referrer_lower = referrer.lower()

        for keyword, source_type in SOURCE_MAPPING.items():
            if keyword in referrer_lower:
                return source_type

        # 检查是否是自身域名
        # 这里可以配置自己的域名列表来识别内部跳转
        # if any(domain in referrer_lower for domain in ['your-domain.com']):
        #     return 'internal'

        return 'referral'

    def parse_log_file(self, file_path: str) -> List[Dict]:
        """解析整个日志文件"""
        logs = []
        path = Path(file_path)

        if not path.exists():
            logger.error(f"日志文件不存在: {file_path}")
            return logs

        logger.info(f"开始解析日志文件: {file_path}")

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                try:
                    log_data = self.parse_line(line)
                    if log_data:
                        logs.append(log_data)

                    if i % 10000 == 0:
                        logger.info(f"已解析 {i} 行, 有效数据 {len(logs)} 条")

                except Exception as e:
                    logger.warning(f"解析第 {i} 行失败: {e}")
                    continue

        logger.info(f"解析完成, 共 {i} 行, 有效数据 {len(logs)} 条")
        return logs


class TrafficDataImporter:
    """流量数据导入器"""

    def __init__(self, api_url: str, api_key: str = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def import_data(self, data: List[Dict], batch_size: int = 1000) -> tuple:
        """
        批量导入数据

        :param data: 标准化的日志数据列表
        :param batch_size: 批量导入批次大小
        :return: (成功数量, 失败数量)
        """
        total = len(data)
        success = 0
        failed = 0

        logger.info(f"开始导入 {total} 条数据")

        for i in range(0, total, batch_size):
            batch = data[i:i + batch_size]
            try:
                response = self.session.post(
                    f"{self.api_url}/api/analytics/traffic/import",
                    json={"data": batch},
                    timeout=30
                )

                if response.status_code == 200:
                    batch_success = len(batch)
                    success += batch_success
                    logger.info(f"批次 {i//batch_size + 1} 导入成功: {batch_success} 条")
                else:
                    failed += len(batch)
                    logger.error(f"批次 {i//batch_size + 1} 导入失败: {response.status_code} - {response.text}")

            except Exception as e:
                failed += len(batch)
                logger.error(f"批次 {i//batch_size + 1} 导入异常: {e}")

        logger.info(f"导入完成: 成功 {success} 条, 失败 {failed} 条")
        return success, failed


def main():
    parser = argparse.ArgumentParser(description='Nginx日志导入工具')
    parser.add_argument('log_file', help='Nginx日志文件路径')
    parser.add_argument('--api-url', default='http://localhost:8008', help='AI流量曝光平台API地址')
    parser.add_argument('--api-key', help='API密钥（可选）')
    parser.add_argument('--log-format', default='json', choices=['json', 'default'], help='日志格式')
    parser.add_argument('--batch-size', type=int, default=1000, help='批量导入大小')
    parser.add_argument('--dry-run', action='store_true', help='仅解析不导入')

    args = parser.parse_args()

    # 解析日志
    parser = NginxLogParser(log_format=args.log_format)
    logs = parser.parse_log_file(args.log_file)

    if not logs:
        logger.warning("没有有效日志数据")
        return

    # 测试输出
    logger.info("解析后的第一条数据示例:")
    logger.info(json.dumps(logs[0], indent=2, ensure_ascii=False))

    if args.dry_run:
        logger.info("Dry run模式，不执行导入")
        return

    # 导入数据
    importer = TrafficDataImporter(api_url=args.api_url, api_key=args.api_key)
    success, failed = importer.import_data(logs, batch_size=args.batch_size)

    logger.info(f"最终结果: 成功 {success} 条, 失败 {failed} 条")


if __name__ == "__main__":
    main()
