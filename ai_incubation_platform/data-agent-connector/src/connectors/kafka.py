"""
Apache Kafka 消息队列连接器
"""
import asyncio
import json
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from utils.logger import logger


class KafkaConnector(BaseConnector):
    """Apache Kafka 消息队列连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._consumer = None
        self._producer = None
        self._admin_client = None
        self._bootstrap_servers = []
        self._current_topic = None

    async def connect(self) -> None:
        """建立 Kafka 连接"""
        try:
            from kafka import KafkaConsumer, KafkaProducer, KafkaAdminClient
            parsed = self._parse_connection_string()

            self._bootstrap_servers = parsed.get('bootstrap_servers', ['localhost:9092'])

            # 创建消费者
            self._consumer = KafkaConsumer(
                bootstrap_servers=self._bootstrap_servers,
                auto_offset_reset=parsed.get('auto_offset_reset', 'earliest'),
                enable_auto_commit=parsed.get('enable_auto_commit', True),
                group_id=parsed.get('group_id', 'data-agent-connector-group'),
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
                consumer_timeout_ms=5000
            )

            # 创建生产者
            self._producer = KafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8') if not isinstance(x, bytes) else x,
                acks='all',
                retries=3
            )

            # 创建管理客户端
            self._admin_client = KafkaAdminClient(
                bootstrap_servers=self._bootstrap_servers,
                client_id='data-agent-connector-admin'
            )

            self._connected = True
            logger.info(f"Connected to Kafka: {self._bootstrap_servers}")
        except Exception as e:
            raise ConnectorError(f"Failed to connect to Kafka: {e}")

    async def disconnect(self) -> None:
        """断开 Kafka 连接"""
        if self._consumer:
            self._consumer.close()
        if self._producer:
            self._producer.flush()
            self._producer.close()
        if self._admin_client:
            self._admin_client.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        执行 Kafka 查询
        查询格式：
        - "CONSUME topic_name LIMIT n" - 消费消息
        - "PRODUCE topic_name MESSAGE data" - 生产消息
        - "LIST_TOPICS" - 列出所有主题
        - "DESCRIBE topic_name" - 描述主题
        """
        if not self._connected:
            raise ConnectorError("Not connected to Kafka")

        query_upper = query.upper().strip()

        try:
            # 列出主题
            if query_upper == "LIST_TOPICS":
                topics = self._admin_client.list_topics()
                return [{"topic": topic} for topic in topics]

            # 描述主题
            if query_upper.startswith("DESCRIBE "):
                topic_name = query.split(" ", 1)[1].strip()
                return await self._describe_topic(topic_name)

            # 消费消息
            if query_upper.startswith("CONSUME "):
                parts = query.split()
                topic_name = parts[1]
                limit = 100
                if "LIMIT" in query_upper:
                    limit_idx = parts.index("LIMIT") + 1
                    if limit_idx < len(parts):
                        limit = int(parts[limit_idx])
                return await self._consume_messages(topic_name, limit)

            # 生产消息
            if query_upper.startswith("PRODUCE "):
                topic_name = params.get('topic') or query.split(" ", 2)[1].strip()
                message = params.get('message', {})
                return await self._produce_message(topic_name, message)

            raise ConnectorError(f"Unknown Kafka query: {query}")

        except Exception as e:
            raise ConnectorError(f"Kafka query execution failed: {e}")

    async def _consume_messages(self, topic: str, limit: int = 100) -> List[Dict[str, Any]]:
        """消费消息"""
        messages = []

        # 订阅主题
        if self._current_topic != topic:
            self._consumer.subscribe([topic])
            self._current_topic = topic

        count = 0
        for message in self._consumer:
            if count >= limit:
                break
            messages.append({
                "topic": message.topic,
                "partition": message.partition,
                "offset": message.offset,
                "key": message.key.decode('utf-8') if message.key else None,
                "value": message.value,
                "timestamp": message.timestamp
            })
            count += 1

        return messages

    async def _produce_message(self, topic: str, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生产消息"""
        try:
            future = self._producer.send(topic, value=message)
            record_metadata = future.get(timeout=10)
            return [{
                "topic": record_metadata.topic,
                "partition": record_metadata.partition,
                "offset": record_metadata.offset,
                "timestamp": record_metadata.timestamp
            }]
        except Exception as e:
            raise ConnectorError(f"Failed to produce message: {e}")

    async def _describe_topic(self, topic: str) -> List[Dict[str, Any]]:
        """描述主题"""
        try:
            from kafka.admin import DescribeTopicsResult
            result = self._admin_client.describe_topics([topic])
            return [{
                "topic": topic,
                "partitions": len(result.get(topic, {}).get('partitions', [])),
                "description": result.get(topic, {})
            }]
        except Exception as e:
            return [{"error": str(e)}]

    async def get_schema(self) -> Dict[str, Any]:
        """获取 Kafka 主题结构（Schema）"""
        try:
            topics = self._admin_client.list_topics()
            schema = {}

            for topic in topics:
                # 消费一条消息来推断 schema
                self._consumer.subscribe([topic])
                messages = []
                for msg in self._consumer:
                    messages.append(msg)
                    if len(messages) >= 1:
                        break

                if messages:
                    sample_value = messages[0].value
                    schema[topic] = {
                        "type": "topic",
                        "sample_schema": self._infer_schema(sample_value) if sample_value else {}
                    }
                else:
                    schema[topic] = {"type": "topic", "sample_schema": {}}

            return {"topics": schema}
        except Exception as e:
            raise ConnectorError(f"Failed to get Kafka schema: {e}")

    def _infer_schema(self, data: Any, depth: int = 0) -> Dict[str, Any]:
        """推断数据结构"""
        if depth > 5:  # 防止过深
            return {"type": "max_depth_reached"}

        if isinstance(data, dict):
            schema = {"type": "object", "properties": {}}
            for key, value in data.items():
                schema["properties"][key] = self._infer_schema(value, depth + 1)
            return schema
        elif isinstance(data, list):
            if data:
                return {
                    "type": "array",
                    "items": self._infer_schema(data[0], depth + 1)
                }
            return {"type": "array", "items": {}}
        else:
            return {"type": type(data).__name__}

    def _parse_connection_string(self) -> Dict[str, Any]:
        """
        解析 Kafka 连接字符串
        格式：kafka://host1:port1,host2:port2/group_id?auto_offset_reset=earliest
        """
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        # 解析 bootstrap servers
        bootstrap_servers = []
        if parsed.netloc:
            # 支持多个 broker: host1:port1,host2:port2
            servers = parsed.netloc.split(',')
            for server in servers:
                if ':' not in server:
                    server = f"{server}:9092"
                bootstrap_servers.append(server)

        return {
            'bootstrap_servers': bootstrap_servers or ['localhost:9092'],
            'group_id': parsed.path.strip('/') or query_params.get('group_id', ['data-agent-connector-group'])[0],
            'auto_offset_reset': query_params.get('auto_offset_reset', ['earliest'])[0],
            'enable_auto_commit': query_params.get('enable_auto_commit', ['true'])[0].lower() == 'true'
        }


__all__ = ["KafkaConnector"]
