"""
邮件加载器 - 支持 IMAP/POP3 协议和 Exchange 邮件接入
"""
import email
import imaplib
import poplib
from email import policy
from email.parser import BytesParser
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import UnstructuredDataConnector, UnstructuredConfig, DocumentChunk
try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class EmailLoader(UnstructuredDataConnector):
    """邮件加载器 - 支持 IMAP/POP3 协议"""

    def __init__(self, config: UnstructuredConfig):
        super().__init__(config)
        self._emails = []
        self._metadata = {}

        # 邮件服务器配置
        self.protocol = config.options.get("protocol", "imap")  # imap 或 pop3
        self.server = config.options.get("server", "")
        self.port = config.options.get("port", 993 if self.protocol == "imap" else 995)
        self.username = config.options.get("username", "")
        self.password = config.options.get("password", "")
        self.use_ssl = config.options.get("use_ssl", True)
        self.folder = config.options.get("folder", "INBOX")
        self.max_emails = config.options.get("max_emails", 50)

        # 连接对象
        self._mail_connection = None

    async def connect(self) -> None:
        """连接邮件服务器"""
        if not self.server:
            raise ValueError("Email server is required")
        if not self.username or not self.password:
            raise ValueError("Email username and password are required")

        try:
            if self.protocol == "imap":
                await self._connect_imap()
            else:
                await self._connect_pop3()

            self._connected = True
            logger.info("Email loader connected", extra={"server": self.server, "protocol": self.protocol})
        except Exception as e:
            logger.error("Failed to connect to email server", extra={"error": str(e)})
            raise ConnectionError(f"Failed to connect to email server: {str(e)}")

    async def disconnect(self) -> None:
        """断开邮件服务器连接"""
        if self._mail_connection:
            try:
                if self.protocol == "imap":
                    self._mail_connection.close()
                    self._mail_connection.logout()
                else:
                    self._mail_connection.quit()
            except Exception as e:
                logger.error("Error disconnecting from email server", extra={"error": str(e)})

        self._mail_connection = None
        self._emails = []
        self._metadata = {}
        self._content_cache = []
        self._connected = False
        logger.info("Email loader disconnected")

    async def load_content(self) -> List[DocumentChunk]:
        """加载邮件内容"""
        if not self._connected:
            await self.connect()

        emails_data = await self._fetch_emails()

        # 合并所有邮件内容
        all_texts = []
        for i, email_data in enumerate(emails_data):
            text = f"""Subject: {email_data.get('subject', '')}
From: {email_data.get('from', '')}
To: {email_data.get('to', '')}
Date: {email_data.get('date', '')}

{email_data.get('body', '')}
"""
            all_texts.append(text)

        full_text = "\n\n---\n\n".join(all_texts)

        # 分割成片段
        chunks = self._split_text(full_text)
        result = []
        for i, chunk in enumerate(chunks):
            result.append(self._create_chunk(
                content=chunk,
                index=i,
                metadata={"chunk_type": "email", "email_count": len(emails_data)}
            ))

        self._content_cache = result
        self._emails = emails_data
        self._metadata = {
            "protocol": self.protocol,
            "server": self.server,
            "folder": self.folder,
            "email_count": len(emails_data),
            "emails": emails_data[:10]  # 只保留前 10 封详细信息
        }

        logger.info("Emails loaded", extra={"count": len(emails_data)})
        return result

    async def get_schema(self) -> Dict[str, Any]:
        """获取邮件元数据"""
        return {
            "source_type": "email",
            "protocol": self.protocol,
            "server": self.server,
            "folder": self.folder,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "metadata": self._metadata,
            "total_chunks": len(self._content_cache)
        }

    async def _connect_imap(self) -> None:
        """连接 IMAP 服务器"""
        import aioimaplib

        self._mail_connection = aioimaplib.IMAP4(
            host=self.server,
            port=self.port
        )
        await self._mail_connection.wait_hello_from_server()

        if self.use_ssl:
            # 注意：aioimaplib 的 SSL 支持有限，可能需要使用同步版本
            pass

        await self._mail_connection.login(self.username, self.password)
        await self._mail_connection.select(self.folder)

    async def _connect_pop3(self) -> None:
        """连接 POP3 服务器"""
        # Python 标准库 poplib 是同步的，这里使用 asyncio 包装
        loop = asyncio.get_event_loop()

        def _connect():
            if self.use_ssl:
                conn = poplib.POP3_SSL(self.server, self.port)
            else:
                conn = poplib.POP3(self.server, self.port)
            conn.user(self.username)
            conn.pass_(self.password)
            return conn

        self._mail_connection = await loop.run_in_executor(None, _connect)

    async def _fetch_emails(self) -> List[Dict[str, Any]]:
        """获取邮件列表"""
        emails = []

        if self.protocol == "imap":
            emails = await self._fetch_imap_emails()
        else:
            emails = await self._fetch_pop3_emails()

        return emails

    async def _fetch_imap_emails(self) -> List[Dict[str, Any]]:
        """从 IMAP 服务器获取邮件"""
        import aioimaplib

        emails = []

        try:
            # 搜索所有邮件
            _, messages = await self._mail_connection.search("ALL")

            # 获取最新 N 封邮件
            message_ids = messages[1].decode().split()[-self.max_emails:]

            for msg_id in message_ids:
                try:
                    _, data = await self._mail_connection.fetch(msg_id, "RFC822")

                    # 解析邮件
                    raw_email = data[1]
                    msg = BytesParser(policy=policy.default).parsebytes(raw_email)

                    email_data = {
                        "subject": msg.get("Subject", ""),
                        "from": msg.get("From", ""),
                        "to": msg.get("To", ""),
                        "date": msg.get("Date", ""),
                        "body": self._extract_email_body(msg)
                    }
                    emails.append(email_data)
                except Exception as e:
                    logger.error("Failed to fetch email", extra={"msg_id": msg_id, "error": str(e)})
                    continue

        except Exception as e:
            logger.error("IMAP fetch error", extra={"error": str(e)})
            # IMAP 失败时尝试使用同步方式
            emails = await self._fetch_imap_sync()

        return emails

    async def _fetch_imap_sync(self) -> List[Dict[str, Any]]:
        """使用同步 IMAP 获取邮件（备选方案）"""
        emails = []
        loop = asyncio.get_event_loop()

        def _fetch():
            if self.use_ssl:
                mail = imaplib.IMAP4_SSL(self.server, self.port)
            else:
                mail = imaplib.IMAP4(self.server, self.port)

            mail.login(self.username, self.password)
            mail.select(self.folder)

            _, message_ids = mail.search(None, "ALL")
            ids = message_ids[0].split()[-self.max_emails:]

            result = []
            for msg_id in ids:
                try:
                    _, data = mail.fetch(msg_id, "(RFC822)")
                    raw_email = data[0][1]
                    msg = BytesParser(policy=policy.default).parsebytes(raw_email)

                    result.append({
                        "subject": msg.get("Subject", ""),
                        "from": msg.get("From", ""),
                        "to": msg.get("To", ""),
                        "date": msg.get("Date", ""),
                        "body": self._extract_email_body(msg)
                    })
                except Exception as e:
                    logger.error("Failed to fetch email", extra={"msg_id": msg_id, "error": str(e)})
                    continue

            mail.close()
            mail.logout()
            return result

        try:
            emails = await loop.run_in_executor(None, _fetch)
        except Exception as e:
            logger.error("Sync IMAP fetch error", extra={"error": str(e)})

        return emails

    async def _fetch_pop3_emails(self) -> List[Dict[str, Any]]:
        """从 POP3 服务器获取邮件"""
        emails = []
        loop = asyncio.get_event_loop()

        def _fetch():
            result = []
            num_messages = len(self._mail_connection.list()[1])

            for i in range(max(0, num_messages - self.max_emails), num_messages):
                try:
                    response, data, _ = self._mail_connection.retr(i + 1)
                    raw_email = b"\r\n".join(data).decode("utf-8")
                    msg = BytesParser(policy=policy.default).parsestr(raw_email)

                    result.append({
                        "subject": msg.get("Subject", ""),
                        "from": msg.get("From", ""),
                        "to": msg.get("To", ""),
                        "date": msg.get("Date", ""),
                        "body": self._extract_email_body(msg)
                    })
                except Exception as e:
                    logger.error("Failed to fetch POP3 email", extra={"index": i, "error": str(e)})
                    continue

            return result

        try:
            emails = await loop.run_in_executor(None, _fetch)
        except Exception as e:
            logger.error("POP3 fetch error", extra={"error": str(e)})

        return emails

    def _extract_email_body(self, msg) -> str:
        """从邮件中提取正文"""
        body_parts = []

        # 优先获取纯文本部分
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # 跳过附件
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    try:
                        body = part.get_content()
                        body_parts.append(body)
                    except Exception:
                        pass
        else:
            try:
                body = msg.get_content()
                body_parts.append(body)
            except Exception:
                pass

        return "\n".join(body_parts)

    @classmethod
    async def from_eml_file(cls, file_path: str, name: str = "email_file") -> "EmailLoader":
        """从 .eml 文件加载邮件"""
        config = UnstructuredConfig(
            name=name,
            source_type="email",
            source_path=file_path
        )
        loader = cls(config)

        # 解析单个 eml 文件
        loop = asyncio.get_event_loop()

        def _parse():
            with open(file_path, 'rb') as f:
                msg = BytesParser(policy=policy.default).parse(f)
            return {
                "subject": msg.get("Subject", ""),
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "date": msg.get("Date", ""),
                "body": loader._extract_email_body(msg)
            }

        email_data = await loop.run_in_executor(None, _parse)
        loader._emails = [email_data]
        loader._metadata = {"source_file": file_path, "email_count": 1}
        loader._connected = True

        return loader
