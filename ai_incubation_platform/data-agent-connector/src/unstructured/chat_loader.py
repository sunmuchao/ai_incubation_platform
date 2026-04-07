"""
聊天记录加载器 - 支持微信、钉钉、Slack 等聊天记录导入解析
"""
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .base import UnstructuredDataConnector, UnstructuredConfig, DocumentChunk
try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ChatLoader(UnstructuredDataConnector):
    """聊天记录加载器 - 支持微信、钉钉、Slack 等"""

    def __init__(self, config: UnstructuredConfig):
        super().__init__(config)
        self._messages = []
        self._metadata = {}

        # 聊天平台类型
        self.platform = config.options.get("platform", "generic")  # wechat, dingtalk, slack, generic
        self.date_format = config.options.get("date_format", "%Y-%m-%d %H:%M:%S")

    async def connect(self) -> None:
        """验证文件是否存在"""
        if self.config.source_path:
            if not os.path.exists(self.config.source_path):
                raise FileNotFoundError(f"Chat file not found: {self.config.source_path}")
        self._connected = True
        logger.info("Chat loader connected", extra={"source": self.config.source_path, "platform": self.platform})

    async def disconnect(self) -> None:
        """断开连接，清理缓存"""
        self._messages = []
        self._metadata = {}
        self._content_cache = []
        self._connected = False
        logger.info("Chat loader disconnected")

    async def load_content(self) -> List[DocumentChunk]:
        """加载聊天记录"""
        if not self._connected:
            await self.connect()

        source_path = self.config.source_path
        if not source_path:
            raise ValueError("source_path is required for chat loading")

        # 根据平台类型解析聊天记录
        if self.platform == "wechat":
            messages, metadata = await self._load_wechat(source_path)
        elif self.platform == "dingtalk":
            messages, metadata = await self._load_dingtalk(source_path)
        elif self.platform == "slack":
            messages, metadata = await self._load_slack(source_path)
        else:
            messages, metadata = await self._load_generic(source_path)

        self._messages = messages
        self._metadata = metadata

        # 格式化为文本
        text = self._format_messages(messages)

        # 分割成片段
        chunks = self._split_text(text)
        result = []
        for i, chunk in enumerate(chunks):
            result.append(self._create_chunk(
                content=chunk,
                index=i,
                metadata={**metadata, "chunk_type": "chat", "platform": self.platform}
            ))

        self._content_cache = result
        logger.info("Chat history loaded", extra={"path": source_path, "messages": len(messages), "chunks": len(result)})
        return result

    async def get_schema(self) -> Dict[str, Any]:
        """获取聊天记录元数据"""
        return {
            "source_type": "chat",
            "source_path": self.config.source_path,
            "platform": self.platform,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "metadata": self._metadata,
            "total_chunks": len(self._content_cache),
            "message_count": len(self._messages)
        }

    async def _load_wechat(self, path: str) -> tuple:
        """加载微信聊天记录"""
        messages = []

        ext = Path(path).suffix.lower()

        if ext == '.json':
            # JSON 格式
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list):
                for msg in data:
                    messages.append({
                        "sender": msg.get("sender", msg.get("username", "")),
                        "content": msg.get("content", msg.get("text", "")),
                        "timestamp": msg.get("timestamp", msg.get("time", "")),
                        "type": msg.get("type", "text")
                    })
            elif isinstance(data, dict) and "messages" in data:
                for msg in data["messages"]:
                    messages.append({
                        "sender": msg.get("sender", msg.get("username", "")),
                        "content": msg.get("content", msg.get("text", "")),
                        "timestamp": msg.get("timestamp", msg.get("time", "")),
                        "type": msg.get("type", "text")
                    })

        elif ext == '.txt':
            # 文本格式 (假设格式为：YYYY-MM-DD HH:MM:SS - Sender: Message)
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # 尝试解析标准格式
                    if ' - ' in line and ':' in line:
                        try:
                            datetime_part, rest = line.split(' - ', 1)
                            if ':' in rest:
                                sender, content = rest.split(':', 1)
                                messages.append({
                                    "sender": sender.strip(),
                                    "content": content.strip(),
                                    "timestamp": datetime_part.strip(),
                                    "type": "text"
                                })
                        except ValueError:
                            # 解析失败，当作普通消息
                            messages.append({
                                "sender": "unknown",
                                "content": line,
                                "timestamp": "",
                                "type": "text"
                            })
                    else:
                        messages.append({
                            "sender": "unknown",
                            "content": line,
                            "timestamp": "",
                            "type": "text"
                        })

        return messages, {
            "platform": "wechat",
            "file_type": ext,
            "message_count": len(messages),
            "participants": list(set(msg["sender"] for msg in messages if msg["sender"]))
        }

    async def _load_dingtalk(self, path: str) -> tuple:
        """加载钉钉聊天记录"""
        messages = []

        ext = Path(path).suffix.lower()

        if ext == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 钉钉导出格式
            if isinstance(data, list):
                for msg in data:
                    messages.append({
                        "sender": msg.get("senderNick", msg.get("sender", "")),
                        "content": msg.get("text", msg.get("content", "")),
                        "timestamp": self._format_timestamp(msg.get("sendTime", msg.get("timestamp", ""))),
                        "type": msg.get("msgType", "text")
                    })
            elif isinstance(data, dict) and "messages" in data:
                for msg in data["messages"]:
                    messages.append({
                        "sender": msg.get("senderNick", msg.get("sender", "")),
                        "content": msg.get("text", msg.get("content", "")),
                        "timestamp": self._format_timestamp(msg.get("sendTime", msg.get("timestamp", ""))),
                        "type": msg.get("msgType", "text")
                    })

        return messages, {
            "platform": "dingtalk",
            "file_type": ext,
            "message_count": len(messages),
            "participants": list(set(msg["sender"] for msg in messages if msg["sender"]))
        }

    async def _load_slack(self, path: str) -> tuple:
        """加载 Slack 聊天记录"""
        messages = []

        ext = Path(path).suffix.lower()

        if ext == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Slack 导出格式
            if isinstance(data, list):
                for msg in data:
                    messages.append({
                        "sender": msg.get("user", msg.get("username", "")),
                        "content": self._parse_slack_text(msg.get("text", "")),
                        "timestamp": self._format_timestamp(msg.get("ts", msg.get("timestamp", ""))),
                        "type": "text",
                        "thread_ts": msg.get("thread_ts"),
                        "reactions": msg.get("reactions", [])
                    })

        return messages, {
            "platform": "slack",
            "file_type": ext,
            "message_count": len(messages),
            "participants": list(set(msg["sender"] for msg in messages if msg["sender"]))
        }

    async def _load_generic(self, path: str) -> tuple:
        """加载通用格式的聊天记录"""
        messages = []

        ext = Path(path).suffix.lower()

        if ext == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list):
                for msg in data:
                    messages.append({
                        "sender": msg.get("sender", msg.get("from", msg.get("user", ""))),
                        "content": msg.get("content", msg.get("text", msg.get("message", ""))),
                        "timestamp": msg.get("timestamp", msg.get("time", msg.get("date", ""))),
                        "type": msg.get("type", "text")
                    })
            elif isinstance(data, dict):
                if "messages" in data:
                    for msg in data["messages"]:
                        messages.append({
                            "sender": msg.get("sender", msg.get("from", "")),
                            "content": msg.get("content", msg.get("text", "")),
                            "timestamp": msg.get("timestamp", msg.get("time", "")),
                            "type": msg.get("type", "text")
                        })
                elif "chat" in data:
                    for msg in data["chat"]:
                        messages.append({
                            "sender": msg.get("sender", msg.get("from", "")),
                            "content": msg.get("content", msg.get("text", "")),
                            "timestamp": msg.get("timestamp", msg.get("time", "")),
                            "type": msg.get("type", "text")
                        })

        elif ext == '.csv':
            import csv
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    messages.append({
                        "sender": row.get("sender", row.get("from", row.get("user", ""))),
                        "content": row.get("content", row.get("text", row.get("message", ""))),
                        "timestamp": row.get("timestamp", row.get("time", row.get("date", ""))),
                        "type": row.get("type", "text")
                    })

        return messages, {
            "platform": "generic",
            "file_type": ext,
            "message_count": len(messages),
            "participants": list(set(msg["sender"] for msg in messages if msg["sender"]))
        }

    def _format_messages(self, messages: List[Dict]) -> str:
        """格式化消息为文本"""
        lines = []
        for msg in messages:
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            if timestamp:
                lines.append(f"[{timestamp}] {sender}: {content}")
            else:
                lines.append(f"{sender}: {content}")

        return "\n".join(lines)

    def _format_timestamp(self, ts: str) -> str:
        """格式化时间戳"""
        if not ts:
            return ""

        # 尝试解析常见格式
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S",
        ]

        # 如果是 Unix 时间戳
        try:
            unix_ts = float(ts)
            dt = datetime.fromtimestamp(unix_ts)
            return dt.strftime(self.date_format)
        except (ValueError, TypeError):
            pass

        # 尝试各种格式
        for fmt in formats:
            try:
                dt = datetime.strptime(ts, fmt)
                return dt.strftime(self.date_format)
            except ValueError:
                continue

        return ts

    def _parse_slack_text(self, text: str) -> str:
        """解析 Slack 文本格式（移除特殊标记）"""
        import re

        # 移除用户标记 <@U123456> -> @username
        text = re.sub(r'<@(\w+)>', r'@\1', text)

        # 移除频道标记
        text = re.sub(r'<#(\w+)\|?([^>]*)>', r'#\2', text)

        # 移除链接标记
        text = re.sub(r'<([^>|]+)\|([^>]+)>', r'\2 (\1)', text)

        return text

    @classmethod
    async def from_messages(cls, messages: List[Dict], name: str = "chat", platform: str = "generic") -> "ChatLoader":
        """从消息列表创建加载器"""
        config = UnstructuredConfig(
            name=name,
            source_type="chat",
            options={"platform": platform}
        )
        loader = cls(config)
        loader._messages = messages
        loader._metadata = {
            "platform": platform,
            "message_count": len(messages),
            "participants": list(set(msg.get("sender", "") for msg in messages if msg.get("sender")))
        }
        loader._connected = True
        return loader
