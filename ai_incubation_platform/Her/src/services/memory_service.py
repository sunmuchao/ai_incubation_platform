"""
AI 记忆服务 - 基于 Mem0 的长期记忆系统

功能:
- 从对话中提取重要记忆
- 搜索相关记忆
- 记忆重要性衰减
- 多用户隔离

使用 Mem0 + Qdrant 本地模式存储
"""
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from utils.logger import logger

try:
    from mem0 import Memory
    from mem0.configs.base import MemoryConfig
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("Mem0 SDK not available, memory features will be disabled")


class MemoryService:
    """
    AI 记忆服务

    提供轻量级的长期记忆能力：
    1. 自动提取重要信息（事实、偏好、事件）
    2. 基于关键词和语义搜索记忆
    3. 记忆重要性自动衰减
    4. 支持多用户隔离
    """

    # 记忆分类
    CATEGORY_USER_INFO = "user_info"       # 用户信息（年龄、职业、所在地）
    CATEGORY_PREFERENCE = "preference"     # 偏好（喜欢什么、讨厌什么）
    CATEGORY_EVENT = "event"              # 事件（计划、发生的事）
    CATEGORY_RELATIONSHIP = "relationship" # 关系（与匹配对象的互动）
    CATEGORY_PERSONALITY = "personality"   # 性格特点

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化记忆服务

        Args:
            db_path: Qdrant 数据目录路径，默认使用 ./data/qdrant
        """
        if not MEM0_AVAILABLE:
            self.memory = None
            logger.warning("Memory service disabled: Mem0 not available")
            return

        if db_path is None:
            # 使用项目数据目录
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "qdrant")

        # 确保数据目录存在
        os.makedirs(db_path, exist_ok=True)

        # 配置 Mem0（使用 Qdrant 本地模式 + OpenAI 兼容 embedder）
        # 使用与 LLM 相同的 API 配置
        api_key = os.getenv("LLM_API_KEY", "")
        api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")

        config = MemoryConfig(
            vector_store={
                "provider": "qdrant",
                "config": {
                    "collection_name": "mem0_her",
                    "path": db_path,
                    "on_disk": True,  # 启用本地持久化
                }
            },
            embedder={
                "provider": "openai",
                "config": {
                    "api_key": api_key,
                    "openai_base_url": api_base,
                    "model": "text-embedding-v3"  # 阿里云兼容的 embedding 模型
                }
            },
        )

        self.memory = Memory(config=config)
        self.db_path = db_path
        logger.info(f"Memory service initialized with Qdrant: {db_path}")

    def add_memory(
        self,
        content: str,
        user_id: str,
        category: Optional[str] = None,
        importance: int = 3,
        metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        添加记忆

        Args:
            content: 记忆内容
            user_id: 用户 ID
            category: 记忆分类
            importance: 重要性 1-5（5 最重要）
            metadata: 额外元数据

        Returns:
            记忆 ID，如果失败返回 None
        """
        if not self.memory:
            return None

        try:
            # 构建记忆元数据
            mem_metadata = {
                "category": category or self.CATEGORY_USER_INFO,
                "importance": importance,
                "created_at": datetime.now().isoformat(),
                **(metadata or {})
            }

            # 添加记忆
            result = self.memory.add(
                content,
                user_id=user_id,
                metadata=mem_metadata
            )

            memory_id = result.get("id") if isinstance(result, dict) else None
            logger.info(f"Added memory: {memory_id} for user {user_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return None

    def search_memories(
        self,
        query: str,
        user_id: str,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict]:
        """
        搜索记忆

        Args:
            query: 搜索查询
            user_id: 用户 ID
            category: 记忆分类过滤
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        if not self.memory:
            return []

        try:
            # 构建过滤器
            filters = {}
            if category:
                filters["category"] = category

            # 搜索记忆
            results = self.memory.search(
                query,
                user_id=user_id,
                filters=filters if filters else None,
                limit=limit
            )

            # 格式化结果
            memories = []
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        memories.append({
                            "id": item.get("id"),
                            "content": item.get("content", ""),
                            "category": item.get("metadata", {}).get("category"),
                            "importance": item.get("metadata", {}).get("importance"),
                            "created_at": item.get("metadata", {}).get("created_at"),
                            "score": item.get("score", 0),  # 相关性分数
                        })
            elif isinstance(results, dict) and "results" in results:
                for item in results["results"]:
                    if isinstance(item, dict):
                        memories.append({
                            "id": item.get("id"),
                            "content": item.get("content", ""),
                            "category": item.get("metadata", {}).get("category"),
                            "importance": item.get("metadata", {}).get("importance"),
                            "created_at": item.get("metadata", {}).get("created_at"),
                            "score": item.get("score", 0),
                        })

            logger.info(f"Found {len(memories)} memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    def get_all_memories(
        self,
        user_id: str,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        获取用户所有记忆

        Args:
            user_id: 用户 ID
            category: 记忆分类过滤
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        if not self.memory:
            return []

        try:
            results = self.memory.get_all(
                user_id=user_id,
                limit=limit
            )

            memories = []
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        mem_category = item.get("metadata", {}).get("category")
                        if category and mem_category != category:
                            continue
                        memories.append({
                            "id": item.get("id"),
                            "content": item.get("content", ""),
                            "category": mem_category,
                            "importance": item.get("metadata", {}).get("importance"),
                            "created_at": item.get("metadata", {}).get("created_at"),
                        })
            elif isinstance(results, dict) and "results" in results:
                for item in results.get("results", []):
                    if isinstance(item, dict):
                        mem_category = item.get("metadata", {}).get("category")
                        if category and mem_category != category:
                            continue
                        memories.append({
                            "id": item.get("id"),
                            "content": item.get("content", ""),
                            "category": mem_category,
                            "importance": item.get("metadata", {}).get("importance"),
                            "created_at": item.get("metadata", {}).get("created_at"),
                        })

            return memories

        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")
            return []

    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """
        删除记忆

        Args:
            memory_id: 记忆 ID
            user_id: 用户 ID

        Returns:
            是否成功删除
        """
        if not self.memory:
            return False

        try:
            self.memory.delete(memory_id, user_id=user_id)
            logger.info(f"Deleted memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False

    def extract_memory_from_dialogue(
        self,
        dialogue: str,
        user_id: str,
    ) -> List[Dict]:
        """
        从对话中提取记忆

        Args:
            dialogue: 对话内容
            user_id: 用户 ID

        Returns:
            提取的记忆列表
        """
        if not self.memory:
            return []

        try:
            # 使用 LLM 提取重要信息
            from llm.client import call_llm

            prompt = f"""从以下对话中提取重要事实作为记忆（只提取客观事实，不要主观评论）：

{dialogue}

请返回 JSON 数组，每个元素包含：
- content: 记忆内容（一句话）
- category: 分类（user_info/preference/event/relationship/personality）
- importance: 重要性 1-5（5 最重要）

示例格式：
[
    {{"content": "用户有只猫叫咪咪", "category": "user_info", "importance": 4}},
    {{"content": "用户喜欢喝奶茶", "category": "preference", "importance": 3}}
]

如果没有值得记忆的内容，返回空数组 []。
"""

            response = call_llm(
                prompt=prompt,
                temperature=0.3,
                max_tokens=500,
            )

            # 解析 JSON
            import json
            try:
                extracted = json.loads(response.strip())
                if not isinstance(extracted, list):
                    extracted = []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse extracted memories: {response}")
                return []

            # 添加记忆
            added_memories = []
            for item in extracted:
                if isinstance(item, dict) and "content" in item:
                    memory_id = self.add_memory(
                        content=item["content"],
                        user_id=user_id,
                        category=item.get("category", self.CATEGORY_USER_INFO),
                        importance=item.get("importance", 3),
                    )
                    if memory_id:
                        added_memories.append({
                            "id": memory_id,
                            "content": item["content"],
                            "category": item.get("category"),
                            "importance": item.get("importance"),
                        })

            logger.info(f"Extracted {len(added_memories)} memories from dialogue")
            return added_memories

        except Exception as e:
            logger.error(f"Failed to extract memories: {e}")
            return []

    def get_contextual_memories(
        self,
        user_id: str,
        current_context: str,
        limit: int = 3,
    ) -> List[Dict]:
        """
        获取与当前上下文相关的记忆

        Args:
            user_id: 用户 ID
            current_context: 当前对话上下文
            limit: 返回数量限制

        Returns:
            相关记忆列表
        """
        # 使用当前上下文作为查询
        return self.search_memories(
            query=current_context,
            user_id=user_id,
            limit=limit
        )

    def get_user_profile(self, user_id: str) -> Dict[str, List[str]]:
        """
        获取用户画像（基于记忆）

        Args:
            user_id: 用户 ID

        Returns:
            用户画像字典
        """
        profile = {
            "user_info": [],
            "preferences": [],
            "personality": [],
            "recent_events": [],
        }

        # 获取各类记忆
        all_memories = self.get_all_memories(user_id, limit=100)

        for mem in all_memories:
            category = mem.get("category", "")
            content = mem.get("content", "")

            if category == self.CATEGORY_USER_INFO:
                profile["user_info"].append(content)
            elif category == self.CATEGORY_PREFERENCE:
                profile["preferences"].append(content)
            elif category == self.CATEGORY_PERSONALITY:
                profile["personality"].append(content)
            elif category == self.CATEGORY_EVENT:
                profile["recent_events"].append(content)

        return profile


# 全局单例
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> Optional[MemoryService]:
    """获取记忆服务单例"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
