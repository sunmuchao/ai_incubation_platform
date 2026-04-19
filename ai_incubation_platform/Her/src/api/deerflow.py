"""
DeerFlow API Routes - Her 项目 DeerFlow 集成接口

提供前端调用 DeerFlow Agent 的 HTTP 接口。

路由：
- POST /api/deerflow/chat: 发送消息
- POST /api/deerflow/stream: 流式发送消息
- GET /api/deerflow/status: 获取 DeerFlow 状态
- POST /api/deerflow/memory/sync: 同步用户画像到 Memory

设计原则（AI Native）：
- DeerFlow 是 Agent 运行时，负责意图识别、工具编排、状态管理
- Her 只提供业务 Tools（匹配、关系分析、约会策划等）
- Memory 系统打通：用户画像注入 DeerFlow，Agent 知道用户背景

性能优化（延迟问题修复）：
- Memory 同步缓存：避免每次请求重复同步
- 用户画像缓存：减少数据库查询次数

🔧 [方案C] 意图预分类层（反模式，仅用于弱模型如 GLM-5）：
- 当使用弱模型时，Agent 无法自主决策工具调用
- 预分类层在调用 Agent 之前识别意图，强制指定工具
- 这是违反 Agent Native 原则的临时解决方案
- 通过 ENABLE_INTENT_ROUTER 开关控制启用/禁用
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import os
import sys
import json
import time
import asyncio  # 🔧 [修复] 添加 asyncio 导入，用于超时保护
import hashlib
import re
import uuid
from unittest.mock import MagicMock  # 🔧 [修复] 导入 MagicMock 用于类型检测

from utils.logger import logger


def _safe_json_serialize(obj: Any) -> str:
    """
    🔧 [修复] 安全的 JSON 序列化，处理 MagicMock 等不可序列化对象

    问题：测试环境中 MagicMock 对象无法被 json.dumps 序列化
    修复：检测 MagicMock 对象并转换为字符串表示
    """
    def _convert_mock(obj):
        # 检测 MagicMock 或 Mock 对象
        if isinstance(obj, (MagicMock, type(None).__class__)):  # MagicMock 检测
            # 检查是否是 MagicMock 的实例（更精确的检测）
            if hasattr(obj, '_mock_name') or 'MagicMock' in str(type(obj)):
                return str(obj) if obj._mock_name else f"<MagicMock:{type(obj).__name__}>"
        if isinstance(obj, dict):
            return {k: _convert_mock(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_convert_mock(item) for item in obj]
        return obj

    try:
        converted = _convert_mock(obj)
        return json.dumps(converted, sort_keys=True, ensure_ascii=False)
    except TypeError as e:
        logger.warning(f"[JSON序列化] 无法序列化对象: {e}, 使用空字典代替")
        return json.dumps({}, sort_keys=True)

router = APIRouter(prefix="/api/deerflow", tags=["deerflow"])

# 🔧 [性能优化] Memory 同步缓存
# 避免每次请求都重复同步用户画像
_memory_sync_cache: Dict[str, Dict[str, Any]] = {}  # user_id -> {last_sync_time, profile_hash}
MEMORY_SYNC_CACHE_TTL = 300  # 缓存有效期：5分钟

# 🔧 [性能优化] 用户画像缓存
# 减少数据库查询次数
_user_profile_cache: Dict[str, Dict[str, Any]] = {}  # user_id -> {profile, last_fetch_time}
USER_PROFILE_CACHE_TTL = 60  # 缓存有效期：1分钟

# DeerFlow 集成
try:
    # 设置 Her 项目根目录
    HER_PROJECT_ROOT = os.environ.get(
        "HER_PROJECT_ROOT",
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )

    # 添加 DeerFlow 到 Python 路径
    deerflow_path = os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", "packages", "harness")

    if deerflow_path not in sys.path:
        sys.path.insert(0, deerflow_path)

    from deerflow.client import DeerFlowClient, StreamEvent
    from deerflow.config.app_config import reload_app_config
    # 🔧 [新增] 导入 checkpointer，用于对话历史持久化
    from deerflow.agents.checkpointer.provider import get_checkpointer

    DEERFLOW_AVAILABLE = True

    # 初始化 DeerFlow 客户端
    config_path = os.path.join(HER_PROJECT_ROOT, "deerflow", "config.yaml")

    # 全局客户端缓存
    _deerflow_client_cache: Optional[DeerFlowClient] = None

    def get_deerflow_client() -> Optional[DeerFlowClient]:
        """获取 DeerFlow 客户端实例（带缓存 + checkpointer）"""
        global _deerflow_client_cache

        if _deerflow_client_cache is not None:
            return _deerflow_client_cache

        if os.path.exists(config_path):
            # 🔧 [关键修复] 先加载 DeerFlow 的 .env 文件，确保环境变量可用
            deerflow_env_path = os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", ".env")
            if os.path.exists(deerflow_env_path):
                # 读取 .env 文件并设置环境变量
                try:
                    with open(deerflow_env_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                if key and not os.environ.get(key):
                                    os.environ[key] = value
                                    logger.info(f"[DeerFlow] 加载环境变量: {key}={value[:10]}...")
                except Exception as e:
                    logger.warning(f"[DeerFlow] 加载 .env 文件失败: {e}")

            reload_app_config(config_path)

            # 🔧 [关键修复] 获取 checkpointer，让对话历史能持久化
            # 这样用户的回答才能被记住，不会重复问同样的问题
            checkpointer = get_checkpointer()
            logger.info(f"[DeerFlow] Checkpointer 已启用: {type(checkpointer).__name__}")

            # 🔧 [诊断] 检查 SOUL.md 是否存在
            from deerflow.config.paths import Paths
            paths = Paths()
            soul_path = paths.base_dir / "SOUL.md"
            logger.info(f"[DeerFlow] SOUL.md 路径: {soul_path}")
            logger.info(f"[DeerFlow] SOUL.md 存在: {soul_path.exists()}")
            if soul_path.exists():
                soul_content = soul_path.read_text(encoding="utf-8")
                # 检查是否包含 "GENERATIVE_UI" 禁止规则
                has_prohibition = "不需要" in soul_content or "禁止输出" in soul_content or "GENERATIVE_UI" in soul_content
                logger.info(f"[DeerFlow] SOUL.md 内容前500字: {soul_content[:500]}")
                logger.info(f"[DeerFlow] SOUL.md 包含 GENERATIVE_UI 禁止规则: {has_prohibition}")

            _deerflow_client_cache = DeerFlowClient(
                config_path=config_path,
                checkpointer=checkpointer  # 🔧 [关键] 传入 checkpointer
            )
            logger.info(f"[DeerFlow] DeerFlowClient 已创建，agent_name: {_deerflow_client_cache._agent_name}")
            return _deerflow_client_cache
        return None

    def reset_deerflow_client():
        """重置 DeerFlow 客户端缓存（在 Memory 更新后调用）"""
        global _deerflow_client_cache
        _deerflow_client_cache = None
        logger.info("DeerFlow client cache reset")

except ImportError as e:
    logger.warning(f"DeerFlow not available: {e}")
    DEERFLOW_AVAILABLE = False
    DeerFlowClient = None
    get_deerflow_client = lambda: None
    reset_deerflow_client = lambda: None


# ==================== Request/Response Models ====================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    thread_id: Optional[str] = None
    user_id: Optional[str] = None


class StreamRequest(BaseModel):
    """流式聊天请求"""
    message: str
    thread_id: str
    user_id: Optional[str] = None


class DeerFlowResponse(BaseModel):
    """DeerFlow 响应"""
    success: bool
    ai_message: str
    intent: Optional[Dict[str, Any]] = None
    generative_ui: Optional[Dict[str, Any]] = None
    suggested_actions: Optional[list] = None
    deerflow_used: Optional[bool] = None
    tool_result: Optional[Dict[str, Any]] = None  # 工具返回的结构化数据
    learning_result: Optional[Dict[str, Any]] = None  # DeerFlow 学习结果（可选回传）


class DeerFlowStatusResponse(BaseModel):
    """DeerFlow 状态响应"""
    available: bool
    path: str
    config_path: str
    config_exists: bool
    memory_enabled: bool


class MemorySyncRequest(BaseModel):
    """Memory 同步请求"""
    user_id: str


class LearningConfirmRequest(BaseModel):
    """学习结果确认请求"""
    user_id: str
    insights: List[Dict[str, Any]]  # 用户确认的洞察列表


class LearningConfirmResponse(BaseModel):
    """学习结果确认响应"""
    success: bool
    applied_count: int
    applied_dimensions: List[str]
    message: str


class MemorySyncResponse(BaseModel):
    """Memory 同步响应"""
    success: bool
    facts_count: int
    message: str


# ==================== Helper Functions ====================

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    获取 Her 用户画像（带缓存优化）

    从 Her 的数据库获取用户基本信息和偏好

    🔧 [性能优化] 添加内存缓存，避免每次请求都查询数据库
    """
    global _user_profile_cache

    # 🔧 [性能优化] 检查缓存
    cache_entry = _user_profile_cache.get(user_id)
    if cache_entry:
        elapsed = time.time() - cache_entry.get("last_fetch_time", 0)
        if elapsed < USER_PROFILE_CACHE_TTL:
            logger.debug(f"[缓存命中] 用户画像缓存有效，跳过数据库查询: {user_id}")
            return cache_entry.get("profile", {})

    try:
        import sqlite3
        from config import settings

        # 获取数据库路径
        db_url = settings.database_url
        if db_url.startswith("sqlite:///"):
            # 相对路径：从 Her 项目根目录解析
            db_name = db_url.replace("sqlite:///", "")
            # 🔧 [修复] database_url 是相对路径，实际数据库在 Her 根目录（而不是 Her/src）
            # 从 api/deerflow.py 的位置向上两级找到 Her 根目录
            her_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Her/
            db_path = os.path.join(her_root, db_name)
        else:
            # 默认路径：使用项目根目录下的 matchmaker_agent.db
            her_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Her/
            db_path = os.path.join(her_root, "matchmaker_agent.db")

        logger.debug(f"Database path: {db_path}")

        # 使用原生 SQL 查询（只查询实际存在的列）
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 查询用户基本信息（只查询数据库实际存在的列）
        cursor.execute("""
            SELECT id, name, age, gender, location, relationship_goal, interests, bio,
                   occupation, education, accept_remote, preferred_age_min, preferred_age_max,
                   preferred_location, deal_breakers
            FROM users WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {}

        # 解析 interests
        interests = []
        if row[6]:  # interests 列
            try:
                interests = json.loads(row[6])
            except json.JSONDecodeError:
                interests = row[6].split(",") if row[6] else []

        profile = {
            "id": row[0],
            "name": row[1],
            "age": row[2],
            "gender": row[3],
            "location": row[4],
            "relationship_goal": row[5],
            "interests": interests,
            "bio": row[7] or "",
            "occupation": row[8] or "",
            "education": row[9] or "",  # 学历
            # ===== 注册后填写的关键偏好 =====
            "accept_remote": row[10],  # 是否接受异地
            "preferred_age_min": row[11],
            "preferred_age_max": row[12],
            "preferred_location": row[13],
            "deal_breakers": row[14],  # 一票否决项
        }

        # 🔧 [性能优化] 保存到缓存
        _user_profile_cache[user_id] = {
            "profile": profile,
            "last_fetch_time": time.time()
        }
        logger.debug(f"[缓存更新] 用户画像已缓存: {user_id}")

        return profile

    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        return {}


def build_memory_facts(user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    根据用户画像构建 DeerFlow Memory Facts

    DeerFlow Memory Facts 格式：
    {
        "id": "fact-id",
        "content": "fact content",
        "category": "preference/knowledge/context/behavior/goal",
        "confidence": 0.9,
        "createdAt": "timestamp",
        "source": "user_profile"
    }
    """
    facts = []

    if not user_profile:
        return facts

    user_id = user_profile.get("id", "anonymous")

    # 🔑 关键：首先添加 user_id fact，用于 DeerFlow 工具提取当前用户 ID
    # ID 格式必须是 "user-id-{actual_user_id}"，以便 her_tools 的 get_current_user_id() 提取
    facts.append({
        "id": f"user-id-{user_id}",
        "content": f"用户ID：{user_id}",
        "category": "context",
        "confidence": 1.0,
        "source": "user_profile"
    })

    # 基本信息 - context 类别
    if user_profile.get("name"):
        facts.append({
            "id": f"user-name-{user_id}",
            "content": f"用户姓名：{user_profile['name']}",
            "category": "context",
            "confidence": 1.0,
            "source": "user_profile"
        })

    if user_profile.get("age"):
        facts.append({
            "id": f"user-age-{user_id}",
            "content": f"用户年龄：{user_profile['age']}岁",
            "category": "context",
            "confidence": 1.0,
            "source": "user_profile"
        })

    if user_profile.get("gender"):
        gender_text = "男" if user_profile["gender"] == "male" else "女"
        facts.append({
            "id": f"user-gender-{user_id}",
            "content": f"用户性别：{gender_text}",
            "category": "context",
            "confidence": 1.0,
            "source": "user_profile"
        })

    if user_profile.get("location"):
        facts.append({
            "id": f"user-location-{user_id}",
            "content": f"用户所在地：{user_profile['location']}",
            "category": "context",
            "confidence": 1.0,
            "source": "user_profile"
        })

    if user_profile.get("occupation"):
        facts.append({
            "id": f"user-occupation-{user_profile['id']}",
            "content": f"用户职业：{user_profile['occupation']}",
            "category": "context",
            "confidence": 0.9,
            "source": "user_profile"
        })

    # 学历 - context 类别
    if user_profile.get("education"):
        education_mapping = {
            "high_school": "高中",
            "college": "大专",
            "bachelor": "本科",
            "master": "硕士",
            "phd": "博士",
        }
        edu_text = education_mapping.get(user_profile["education"], user_profile["education"])
        facts.append({
            "id": f"user-education-{user_profile['id']}",
            "content": f"用户学历：{edu_text}",
            "category": "context",
            "confidence": 0.9,
            "source": "user_profile"
        })

    # 关系目标 - goal 类别
    if user_profile.get("relationship_goal"):
        goal_mapping = {
            "serious": "认真恋爱",
            "marriage": "奔着结婚",
            "dating": "轻松交友",
            "casual": "随便聊聊",
        }
        goal_text = goal_mapping.get(user_profile["relationship_goal"], user_profile["relationship_goal"])
        facts.append({
            "id": f"user-goal-{user_profile['id']}",
            "content": f"用户的关系目标：{goal_text}",
            "category": "goal",
            "confidence": 1.0,
            "source": "user_profile"
        })

    # 兴趣爱好 - preference 类别
    interests = user_profile.get("interests", [])
    if interests:
        interests_text = ", ".join(interests[:5])  #最多5个
        facts.append({
            "id": f"user-interests-{user_profile['id']}",
            "content": f"用户的兴趣爱好：{interests_text}",
            "category": "preference",
            "confidence": 0.9,
            "source": "user_profile"
        })

    # 个人简介 - context 类别（如果有）
    bio = user_profile.get("bio", "")
    if bio and len(bio) > 10:
        facts.append({
            "id": f"user-bio-{user_profile['id']}",
            "content": f"用户简介：{bio[:100]}...",  # 截断避免过长
            "category": "context",
            "confidence": 0.8,
            "source": "user_profile"
        })

    # ===== 注册后填写的关键偏好（重要！）=====
    # 异地接受度 - preference 类别
    # 🔧 [修复] 支持前端发送的值格式（yes/no/conditional）和数据库存储的中文格式
    accept_remote = user_profile.get("accept_remote")
    if accept_remote:
        remote_mapping = {
            # 前端发送的值格式
            "yes": "接受异地恋",
            "no": "不接受异地，只找同城",
            "conditional": "视情况而定，有缘分可以接受",
            # 数据库存储的中文格式（兼容）
            "同城优先": "同城优先，但也接受异地",
            "接受异地": "接受异地恋",
            "只找同城": "只找同城，不接受异地",
        }
        remote_text = remote_mapping.get(accept_remote, accept_remote)
        facts.append({
            "id": f"user-accept-remote-{user_profile['id']}",
            "content": f"用户对异地恋的态度：{remote_text}",
            "category": "preference",
            "confidence": 1.0,
            "source": "user_profile"
        })

    # 偏好年龄范围 - preference 类别
    age_min = user_profile.get("preferred_age_min")
    age_max = user_profile.get("preferred_age_max")
    if age_min and age_max:
        facts.append({
            "id": f"user-age-range-{user_profile['id']}",
            "content": f"用户偏好的对象年龄范围：{age_min}-{age_max}岁",
            "category": "preference",
            "confidence": 0.9,
            "source": "user_profile"
        })

    # 偏好地点 - preference 类别
    preferred_location = user_profile.get("preferred_location")
    if preferred_location:
        facts.append({
            "id": f"user-pref-location-{user_profile['id']}",
            "content": f"用户偏好的对象所在地：{preferred_location}",
            "category": "preference",
            "confidence": 0.9,
            "source": "user_profile"
        })

    # 一票否决项 - preference 类别（deal breakers）
    deal_breakers = user_profile.get("deal_breakers")
    if deal_breakers and len(deal_breakers) > 5:
        facts.append({
            "id": f"user-deal-breakers-{user_profile['id']}",
            "content": f"用户的一票否决项（绝对不接受）：{deal_breakers[:100]}",
            "category": "preference",
            "confidence": 0.95,
            "source": "user_profile"
        })

    return facts


def sync_user_memory_to_deerflow(user_id: str, force: bool = False) -> int:
    """
    同步用户画像到用户独立的 Memory 文件（带缓存优化）

    【用户隔离架构】

    每个用户有独立的 memory 文件，防止数据混用：
    - 路径：{base_dir}/users/{user_id}/memory.json
    - 只包含当前用户的基本信息和偏好
    - DeerFlow Agent 仍然使用全局 memory（对话历史等）

    🔧 [性能优化] 添加缓存机制：
    - 检查缓存是否有效（5分钟内已同步且画像未变化）
    - 如果有效，跳过同步，减少数据库查询和文件写入
    - force 参数可强制同步（用户画像更新后调用）

    目录结构：
        {base_dir}/
        ├── memory.json          ← DeerFlow 全局 memory（对话历史）
        └── users/
            └── {user_id}/
                └── memory.json  ← 用户独立 memory（基本信息 + 偏好）

    同步时机：
    - 用户发起对话时（/api/deerflow/chat）- 有缓存检查
    - 用户在 Her 中更新画像后 - 强制同步

    Returns:
        同步的 facts 数量（如果缓存命中返回缓存的数量）
    """
    global _memory_sync_cache

    # 🔧 [性能优化] 检查缓存是否有效
    if not force:
        cache_entry = _memory_sync_cache.get(user_id)
        if cache_entry:
            elapsed = time.time() - cache_entry.get("last_sync_time", 0)
            if elapsed < MEMORY_SYNC_CACHE_TTL:
                # 缓存有效，检查画像是否变化
                # 🔧 [修复] 使用安全的 JSON 序列化，避免 MagicMock 对象无法序列化
                current_hash = hashlib.md5(_safe_json_serialize(get_user_profile(user_id)).encode()).hexdigest()
                if current_hash == cache_entry.get("profile_hash"):
                    logger.info(f"[缓存命中] Memory 同步缓存有效，跳过同步: {user_id}")
                    return cache_entry.get("facts_count", 0)

    try:
        # Step 1: 从 Her 数据库获取用户画像（真相来源）
        user_profile = get_user_profile(user_id)
        if not user_profile:
            logger.warning(f"User profile not found for {user_id}")
            return 0

        # Step 2: 构建 Memory Facts
        facts = build_memory_facts(user_profile)
        if not facts:
            logger.warning(f"No facts to sync for {user_id}")
            return 0

        # 🔧 [性能优化] 计算画像 hash 用于缓存比较
        # 🔧 [修复] 使用安全的 JSON 序列化，避免 MagicMock 对象无法序列化
        profile_hash = hashlib.md5(_safe_json_serialize(user_profile).encode()).hexdigest()

        # Step 3: 写入用户独立的 memory 文件
        user_memory_dir = os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", ".deer-flow", "users", user_id)
        user_memory_path = os.path.join(user_memory_dir, "memory.json")

        # 创建目录
        os.makedirs(user_memory_dir, exist_ok=True)

        # 🔧 [修复] 构建符合 DeerFlow 标准格式的 memory 数据结构
        # DeerFlow 期望的格式包含 user、history、facts 三个部分
        user_memory_data = {
            "version": "1.0",
            "lastUpdated": datetime.now().isoformat(),
            # DeerFlow 标准格式：user 部分（上下文摘要）
            "user": {
                "workContext": {"summary": "", "updatedAt": ""},
                "personalContext": {"summary": "", "updatedAt": ""},
                "topOfMind": {"summary": "", "updatedAt": ""},
            },
            # DeerFlow 标准格式：history 部分（对话历史摘要）
            "history": {
                "recentMonths": {"summary": "", "updatedAt": ""},
                "earlierContext": {"summary": "", "updatedAt": ""},
                "longTermBackground": {"summary": "", "updatedAt": ""},
            },
            # DeerFlow 标准格式：facts 部分（离散事实）
            "facts": facts,
        }

        # 原子写入
        temp_path = user_memory_path + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(user_memory_data, f, ensure_ascii=False, indent=2)
        os.rename(temp_path, user_memory_path)

        # 🔧 [性能优化] 保存同步缓存信息
        _memory_sync_cache[user_id] = {
            "last_sync_time": time.time(),
            "profile_hash": profile_hash,
            "facts_count": len(facts)
        }

        logger.info(f"[Memory同步] Her → 用户独立文件: {len(facts)} facts for user {user_id}")

        return len(facts)

    except Exception as e:
        logger.error(f"Failed to sync user memory: {e}")
        return 0


def invalidate_user_cache(user_id: str) -> None:
    """
    清除用户缓存（当用户画像更新后调用）

    当用户在 Her 中更新了个人信息或偏好后，需要调用此函数：
    1. 清除用户画像缓存
    2. 清除 Memory 同步缓存
    3. 强制重新同步到 DeerFlow

    Args:
        user_id: 用户 ID
    """
    global _user_profile_cache, _memory_sync_cache

    # 清除用户画像缓存
    if user_id in _user_profile_cache:
        del _user_profile_cache[user_id]
        logger.info(f"[缓存清除] 用户画像缓存已清除: {user_id}")

    # 清除 Memory 同步缓存
    if user_id in _memory_sync_cache:
        del _memory_sync_cache[user_id]
        logger.info(f"[缓存清除] Memory 同步缓存已清除: {user_id}")

    # 强制重新同步
    sync_user_memory_to_deerflow(user_id, force=True)


async def _async_sync_user_memory(user_id: str) -> None:
    """
    🔧 [P1性能优化] 异步同步用户画像到 DeerFlow Memory

    在后台线程中执行同步，不阻塞主请求。
    使用 asyncio.to_thread 将同步函数包装为异步。

    Args:
        user_id: 用户 ID
    """
    try:
        # 使用 asyncio.to_thread 在后台线程执行同步函数
        await asyncio.to_thread(sync_user_memory_to_deerflow, user_id)
        logger.info(f"[DEERFLOW_ASYNC] Memory sync 完成 for user {user_id}")
    except Exception as e:
        logger.warning(f"[DEERFLOW_ASYNC] Memory sync 失败 for user {user_id}: {e}")


# ==================== Routes ====================

@router.post("/memory/sync", response_model=MemorySyncResponse)
async def sync_memory(request: MemorySyncRequest):
    """
    同步用户画像到 DeerFlow Memory

    将用户的年龄、性别、所在地、兴趣爱好、关系目标等信息
    注入到 DeerFlow 的记忆系统，让 Agent 了解用户背景。

    Args:
        request: MemorySyncRequest

    Returns:
        MemorySyncResponse
    """
    logger.info(f"DeerFlow Memory sync request for user {request.user_id}")

    if not DEERFLOW_AVAILABLE:
        return MemorySyncResponse(
            success=False,
            facts_count=0,
            message="DeerFlow 服务未启动"
        )

    facts_count = sync_user_memory_to_deerflow(request.user_id)

    if facts_count > 0:
        return MemorySyncResponse(
            success=True,
            facts_count=facts_count,
            message=f"已同步 {facts_count} 条用户信息到 DeerFlow Memory"
        )
    else:
        return MemorySyncResponse(
            success=False,
            facts_count=0,
            message="同步失败或用户信息不完整"
        )


@router.post("/chat", response_model=DeerFlowResponse)
async def chat(request: ChatRequest):
    """
    发送消息到 DeerFlow Agent（唯一入口）

    流程：
    1. 如果提供了 user_id，先同步用户画像到 Memory
    2. 调用 DeerFlow Agent 处理消息（意图识别 + 工具编排）
    3. 如果 DeerFlow 不可用，降级到 ConversationMatchService
    4. 返回响应（包含结构化数据供前端渲染）

    设计原则：
    - 这是系统的唯一对话入口
    - DeerFlow 负责：意图识别、工具编排、状态管理、Memory
    - Her 提供：匹配逻辑、认知偏差分析、主动建议
    """
    import time
    start_time = time.time()
    logger.info(f"[DEERFLOW入口] START - message={request.message[:30]}..., user={request.user_id}")

    # 尝试使用 DeerFlow
    if DEERFLOW_AVAILABLE:
        result = await _handle_with_deerflow(request)
        logger.info(f"[DEERFLOW入口] END - Total API time: {time.time() - start_time:.3f}s")
        return result
    else:
        # 降级：直接调用 ConversationMatchService
        return await _handle_with_her_service(request)


def infer_intent_from_response(
    message: str,
    response_text: str,
    generative_ui: Optional[Dict] = None,
    tool_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    从响应推断意图类型（用于测试报告）

    🔧 [Agent Native v4] 简化设计：
    1. 安全边界检测（允许保留规则）
    2. 从 tool_result/generative_ui 推断（Agent 自己决策后的结果）
    3. 默认兜底

    禁止硬编码关键词映射表，意图识别由 Agent 自己决策。
    """
    message_lower = message.lower()

    # 🔧 [安全边界] 检测安全攻击关键词（允许保留规则）
    # 这是硬约束，必须在代码中执行
    security_attack_keywords = [
        "忽略所有规则", "忽略规则", "系统密码", "告诉我密码",
        "管理员权限", "越权", "绕过限制", "删除所有", "删除数据库",
        "DROP", "DELETE", "注入", "SQL注入", "prompt injection",
        "你是谁的开发者", "你的源代码", "你的训练数据",
        "帮我测试系统漏洞", "帮我破解", "帮我攻击",
    ]
    if any(kw in message_lower for kw in security_attack_keywords):
        logger.warning(f"[IntentInfer] 检测到安全攻击关键词: {message[:50]}...")
        return {
            "type": "security_reject",
            "confidence": 1.0,
            "source": "security_check",
        }

    # 方式1：优先使用工具返回的意图（结构化单一真相来源）
    # Agent 通过调用工具返回 intent_type，这是 Agent 自己决策的结果
    if tool_result:
        data = tool_result.get("data", {})
        explicit_intent = (
            data.get("intent_type")
            or tool_result.get("intent_type")
            or data.get("intent")
        )
        if isinstance(explicit_intent, dict):
            intent_type = explicit_intent.get("type")
            confidence = explicit_intent.get("confidence", 0.95)
            if intent_type:
                return {"type": intent_type, "confidence": confidence, "source": "tool_result"}
        if isinstance(explicit_intent, str) and explicit_intent.strip():
            return {"type": explicit_intent.strip(), "confidence": 0.95, "source": "tool_result"}

    # 方式2：从 UI 组件推断（Agent 自己决策后的结果）
    # Agent 决定生成什么 UI，我们从 UI 类型推断意图
    if generative_ui:
        component_type = generative_ui.get("component_type", "")
        ui_intent_map = {
            "MatchCardList": "match_request",
            "UserProfileCard": "view_profile",
            "ProfileQuestionCard": "profile_collection",
            "TopicsCard": "topic_request",
            "DatePlanCard": "date_planning",
            "IcebreakerCard": "icebreaker_request",
            "CompatibilityChart": "compatibility_analysis",
            "RelationshipHealthCard": "relationship_analysis",
            "GiftCard": "gift_suggestion",
            "ChatInitiationCard": "initiate_chat",
        }
        if component_type in ui_intent_map:
            return {"type": ui_intent_map[component_type], "confidence": 0.9, "source": "ui_component"}

    # 方式3：默认兜底
    # Agent 未返回结构化信息时，无法推断具体意图
    # 🔧 [Agent Native] 移除关键词映射表，不再硬编码"当 X 时返回 Y"
    return {"type": "conversation", "confidence": 0.5, "source": "default"}


def _normalize_generative_ui(generative_ui: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    🔧 [Agent Native] 简化设计：不再修改数据。

    原设计（违反 Agent Native）：
    - 硬编码修改 props.total = len(matches)

    新设计：
    - 直接返回原值，不做修改
    - 工具应该返回正确的数据
    """
    return generative_ui


def _locations_match_for_filter(preferred: str, loc: str) -> bool:
    if not (preferred or "").strip() or not (loc or "").strip():
        return False
    pref = preferred.strip()
    l = loc.strip()
    return pref == l or pref in l or l in pref


def _coerce_interests_to_str_list(val: Any) -> List[str]:
    """将 interests 规范为 List[str]（与 her_tools.helpers 行为对齐的 API 层兜底）。"""
    if val is None:
        return []
    if isinstance(val, list):
        merged = "".join(str(x) for x in val if x is not None).strip()
        if merged.startswith("["):
            try:
                parsed = json.loads(merged.replace(" ", ""))
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()][:20]
            except json.JSONDecodeError:
                pass
        out: List[str] = []
        for x in val:
            if isinstance(x, str):
                s = x.strip()
                if s and s != "[]":
                    out.append(s)
        return out[:20]
    text = str(val).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [p.strip() for p in text.split(",") if p.strip() and p.strip() != "[]"][:20]


def _sanitize_interests_in_match_card_props(props: Dict[str, Any]) -> None:
    matches = props.get("matches")
    if not isinstance(matches, list):
        return
    for m in matches:
        if isinstance(m, dict):
            m["interests"] = _coerce_interests_to_str_list(m.get("interests"))


def _finalize_match_generative_ui(
    generative_ui: Optional[Dict[str, Any]],
    tool_result: Optional[Dict[str, Any]],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    🔧 [Agent Native] 简化设计：只做数据合并，不做业务判断。

    原设计（违反 Agent Native）：
    - 硬编码"只找同城"检查逻辑
    - 强制清空列表
    - 代码计算 matched_count/total

    新设计：
    - 只合并工具返回的 filter_applied、query_request_id
    - 字段规范化（interests）
    - 不做业务判断（由 Agent 在 Prompt 层面处理）
    """
    if not generative_ui or generative_ui.get("component_type") != "MatchCardList":
        return "", generative_ui

    props = generative_ui.get("props")
    if not isinstance(props, dict):
        return "", generative_ui

    # 合并工具返回的元数据（filter_applied、query_request_id）
    data = (tool_result or {}).get("data") or {}
    if isinstance(data.get("filter_applied"), dict):
        prev = props.get("filter_applied") if isinstance(props.get("filter_applied"), dict) else {}
        props["filter_applied"] = {**prev, **data["filter_applied"]}
    if data.get("query_request_id"):
        props.setdefault("query_request_id", data["query_request_id"])
    props.setdefault("query_request_id", str(uuid.uuid4()))

    # 字段规范化（interests）
    _sanitize_interests_in_match_card_props(props)

    return "", generative_ui


def _align_ai_message_with_structured_result(
    ai_message: str,
    generative_ui: Optional[Dict[str, Any]],
) -> str:
    """
    🔧 [Agent Native] 简化设计：不再强制替换 Agent 输出。

    原设计（违反 Agent Native）：
    - 硬编码模板 "为你找到 X 位候选人"
    - 强制替换 Agent 的输出

    新设计：
    - 只做最小一致性检查和警告
    - Agent 通过 Prompt 学习正确的输出格式
    - 不干预 Agent 的自然语言表达
    """
    # 只在数据明显不一致时记录警告，不强制替换
    if generative_ui and generative_ui.get("component_type") == "MatchCardList":
        props = generative_ui.get("props", {})
        if isinstance(props, dict):
            # 兼容多种字段名
            matches = props.get("matches") or props.get("candidates") or []
            if isinstance(matches, list) and len(matches) > 0:
                # 检查 Agent 输出是否与数据一致
                stated_counts = [int(item) for item in re.findall(r"(\d+)\s*位", ai_message or "")]
                actual_count = len(matches)
                if stated_counts and any(count != actual_count for count in stated_counts):
                    # 只记录警告，不强制替换（Agent Native 原则）
                    logger.warning(
                        f"[DEERFLOW] Agent 输出人数({stated_counts})与数据({actual_count})不一致，"
                        f"应在 Prompt 层面修复而非代码强制替换"
                    )

    # 直接返回 Agent 的原始输出，不做任何修改
    return ai_message


def _looks_like_placeholder_response(ai_message: str) -> bool:
    """检测工具占位文案，避免"查询成功，返回N行数据"直接暴露给用户。"""
    text = (ai_message or "").strip()
    if not text:
        return False
    placeholder_patterns = [
        r"^查询成功，返回\s*\d+\s*行数据$",
        r"^对比\s+.+\s+和\s+.+\s+的画像$",
        r"^分析\s+.+\s+和\s+.+\s+的关系$",
    ]
    return any(re.match(pattern, text) for pattern in placeholder_patterns)


def _render_structured_result_message(
    ai_message: str,
    tool_result: Optional[Dict[str, Any]],
    generative_ui: Optional[Dict[str, Any]],
) -> str:
    """
    🔧 [Agent Native] 简化设计：只处理真正的占位文案，不做硬编码模板输出。

    原设计（违反 Agent Native）：
    - 硬编码 relaxation_suggestions 输出模板
    - 硬编码 comparison_factors 输出模板
    - 硬编码 match_info 输出模板

    新设计：
    - 只检测并处理真正的占位文案（内部状态暴露）
    - 其他情况直接返回 Agent 原始输出
    - Agent 通过 Prompt 学习正确的输出格式
    """
    # 检测是否是占位文案（内部状态暴露，如"查询成功，返回N行数据")
    if not _looks_like_placeholder_response(ai_message):
        # 不是占位文案，直接返回 Agent 原始输出
        return ai_message

    # 是占位文案，尝试从 tool_result 提取基本信息
    if not isinstance(tool_result, dict):
        return ai_message

    data = tool_result.get("data", {})
    if not isinstance(data, dict):
        return ai_message

    # 处理占位文案：提取基本信息，不做硬编码格式化
    rows = data.get("rows")
    if isinstance(rows, list):
        row_count = len(rows)
        if row_count == 0:
            return "查询完成，当前没有符合条件的数据。"
        return f"查询完成，共 {row_count} 条数据。"

    # 无法处理，返回原消息（让 Agent 自己决定）
    return ai_message


def _build_observability_trace(
    request: ChatRequest,
    intent: Dict[str, Any],
    generative_ui: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """构建用于定位问题的最小可观测证据链。"""
    trace: Dict[str, Any] = {
        "thread_id": request.thread_id,
        "user_id": request.user_id,
        "message_preview": (request.message or "")[:80],
        "intent_type": intent.get("type"),
        "intent_source": intent.get("source"),
        "intent_confidence": intent.get("confidence"),
        "ui_component_type": None,
        "ui_matches_count": None,
        "query_request_id": None,
        "query_integrity": None,
    }
    if generative_ui:
        trace["ui_component_type"] = generative_ui.get("component_type")
        props = generative_ui.get("props", {})
        if isinstance(props, dict) and isinstance(props.get("matches"), list):
            trace["ui_matches_count"] = len(props.get("matches"))
        if isinstance(props, dict):
            trace["query_request_id"] = props.get("query_request_id")
            trace["query_integrity"] = props.get("query_integrity")
    return trace


def _trim_tool_result_candidates(
    tool_result: Optional[Dict[str, Any]],
    generative_ui: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    🔧 [数据精简] 当 generative_ui 已包含 Agent 精选的候选人时，
    移除 tool_result 中的完整候选池，只保留最小元数据。

    问题：candidate_005 同时出现在 generative_ui.props.matches（3个精选）
         和 tool_result.data.candidates（30个完整列表），造成数据冗余。

    解决：
    - 如果 generative_ui 是 MatchCardList/UserProfileCard（Agent 已筛选）
    - 则 tool_result 只保留 query_request_id 和 component_type
    - 不保留完整 candidates 列表、candidates_count 等中间状态
    - Agent Native 原则：中间状态不暴露给前端，由 Agent 在文字中说明

    Args:
        tool_result: 工具返回的原始数据
        generative_ui: Agent 决定展示的 UI

    Returns:
        精简后的 tool_result（只保留 query_request_id 和 component_type）
    """
    if not tool_result:
        return tool_result

    # 检查 generative_ui 是否已包含候选人展示
    if not generative_ui:
        return tool_result

    component_type = generative_ui.get("component_type", "")

    # 匹配类 UI：Agent 已筛选，不需要完整候选池
    match_ui_types = ["MatchCardList", "UserProfileCard", "ChatInitiationCard"]
    if component_type not in match_ui_types:
        return tool_result

    # 开始精简
    data = tool_result.get("data", {})
    if not isinstance(data, dict):
        return tool_result

    # 检查是否有完整候选池
    candidates = data.get("candidates", [])
    if not candidates:
        return tool_result

    # 精简：只保留最小元数据（query_request_id + component_type）
    # 不保留 candidates_count（Agent Native：中间状态不暴露）
    trimmed_data = {
        "query_request_id": data.get("query_request_id"),
        "component_type": data.get("component_type"),
    }

    # 移除 None 值的字段
    trimmed_data = {k: v for k, v in trimmed_data.items() if v is not None}

    # 构建精简后的 tool_result
    trimmed_tool_result = {
        "success": tool_result.get("success"),
        "error": tool_result.get("error", ""),
        "data": trimmed_data,
    }

    logger.info(
        f"[数据精简] tool_result 原有 {len(candidates)} 个候选人，"
        f"generative_ui 已包含 Agent 精选，移除完整列表只保留 query_request_id"
    )

    return trimmed_tool_result


def _enrich_tool_result_with_observability(
    tool_result: Optional[Dict[str, Any]],
    trace: Dict[str, Any],
) -> Dict[str, Any]:
    """把关键可观测信息挂到 tool_result，方便测试与排障统一读取。"""
    base: Dict[str, Any] = dict(tool_result) if isinstance(tool_result, dict) else {}
    base["observability"] = trace
    return base


async def _handle_with_deerflow(request: ChatRequest) -> DeerFlowResponse:
    """使用 DeerFlow Agent 处理"""
    start_time = time.time()

    # 🔧 [调试] 记录请求详情
    logger.info(f"[DEERFLOW_TRACE] ===== 开始处理请求 =====")
    logger.info(f"[DEERFLOW_TRACE] request.message={request.message[:100]}...")
    logger.info(f"[DEERFLOW_TRACE] request.user_id={request.user_id}")
    logger.info(f"[DEERFLOW_TRACE] request.thread_id={request.thread_id}")

    # 🔧 [安全] 先检测安全攻击，直接返回友好拒绝，不调用 DeerFlow
    security_intent = infer_intent_from_response(request.message, "", None)
    if security_intent.get("type") == "security_reject":
        logger.warning(f"[DEERFLOW_TRACE] 检测到安全攻击，返回友好拒绝: {request.message[:50]}...")
        return DeerFlowResponse(
            success=True,
            ai_message="我是一个红娘助手，只能帮你找对象、聊聊天哦~ 有什么情感问题需要帮忙的吗？",
            intent={"type": "security_reject", "confidence": 1.0, "source": "security_check"},
            deerflow_used=False,
        )

    client = get_deerflow_client()
    if not client:
        logger.warning("[DEERFLOW_TRACE] DeerFlow client not available, fallback to Her service")
        return await _handle_with_her_service(request)

    # 🔧 [调试] 记录 client 创建成功
    logger.info(f"[DEERFLOW_TRACE] DeerFlow client 创建成功，准备调用 chat")

    try:
        # 如果有 user_id，异步同步用户画像到 Memory（不阻塞主请求）
        # 🔧 [P1性能优化] Memory 同步异步化
        # 原逻辑：同步执行，阻塞主请求 1-2 秒
        # 新逻辑：后台异步执行，主请求立即继续
        if request.user_id:
            # 使用 asyncio.create_task 在后台执行同步
            # 不等待结果，主请求立即继续处理
            asyncio.create_task(_async_sync_user_memory(request.user_id))
            logger.info(f"[DEERFLOW] Memory sync 已异步提交 for user {request.user_id}")

        # 调用 DeerFlow（传入 user_id 以实现用户隔离）
        thread_id = request.thread_id or f"her-{request.user_id or 'anonymous'}-{os.urandom(4).hex()}"

        # 🔧 [调试] 记录调用参数
        logger.info(f"[DEERFLOW_TRACE] thread_id={thread_id}")
        logger.info(f"[DEERFLOW_TRACE] 准备调用 client.chat()")

        chat_start = time.time()

        # 🔧 [关键修复] 使用 stream 方法获取工具调用的原始结果
        # DeerFlow client.chat() 只返回文本，不返回工具 JSON
        # 使用 stream 可以获取 ToolMessage，其中包含工具返回的 JSON
        MAX_TIMEOUT = 45.0  # 🔧 [修复] 减少超时时间，45秒足够处理大多数请求
        response_text = ""
        tool_results_list = []  # 收集所有工具调用结果

        try:
            logger.info(f"[DEERFLOW_TRACE] 开始 stream 调用，超时={MAX_TIMEOUT}s")
            logger.info(f"[DEERFLOW_TRACE] 用户消息: {request.message[:150]}...")

            # 使用 asyncio.wait_for 包装整个 stream 处理
            async def process_stream():
                nonlocal response_text, tool_results_list
                # stream 是同步生成器，需要在线程中运行
                stream_gen = client.stream(request.message, thread_id=thread_id, user_id=request.user_id)

                for event in stream_gen:
                    if event.type == "messages-tuple":
                        data = event.data
                        # AI 文本回复
                        if data.get("type") == "ai" and data.get("content"):
                            response_text += data["content"]
                        # 工具返回结果（ToolMessage）
                        elif data.get("type") == "tool" and data.get("content"):
                            # 尝试解析工具返回的 JSON
                            try:
                                tool_json = json.loads(data["content"])
                                if tool_json.get("success") and tool_json.get("data"):
                                    tool_results_list.append(tool_json)
                                    logger.info(f"[DEERFLOW_TRACE] 提取工具结果: {tool_json.get('data', {}).get('component_type', 'unknown')}")
                            except json.JSONDecodeError:
                                pass
                    elif event.type == "end":
                        break

            await asyncio.wait_for(process_stream(), timeout=MAX_TIMEOUT)
            logger.info(f"[DEERFLOW_TRACE] stream 处理完成")

        except asyncio.TimeoutError:
            logger.warning(f"[DEERFLOW_TRACE] ⏱️ Timeout after {MAX_TIMEOUT}s for message: {request.message[:50]}...")
            # 🔧 [安全兜底] 返回友好提示，不暴露系统内部状态
            intent = infer_intent_from_response(request.message, "", None, None)
            logger.info(f"[DEERFLOW_TRACE] 返回 timeout_fallback 响应")
            return DeerFlowResponse(
                success=True,
                ai_message="抱歉，系统响应稍慢，请稍后再试。如需帮助，可以直接描述您的需求。",
                intent={"type": "timeout_fallback", "confidence": 0.5},
                deerflow_used=True,
            )
        except Exception as chat_error:
            # 🔧 [调试] 记录 chat 调用异常详情
            logger.error(f"[DEERFLOW_TRACE] ❌ client.chat 调用异常: {type(chat_error).__name__}: {chat_error}")
            logger.error(f"[DEERFLOW_TRACE] 异常堆栈:", exc_info=True)
            # 🔧 [安全兜底] 返回友好错误提示，不暴露异常详情
            return DeerFlowResponse(
                success=True,
                ai_message="抱歉，处理时遇到问题。请稍后再试，或换个方式描述您的需求。",
                intent={"type": "error_fallback", "confidence": 0.5},
                deerflow_used=True,
            )

        logger.info(f"[DEERFLOW] Agent chat done in {time.time() - chat_start:.3f}s for message: {request.message[:30]}...")

        # 解析响应，提取结构化数据
        tool_result = None
        generative_ui = None
        learning_result = None

        parse_start = time.time()
        # 🔧 [关键] 在 try 块开始时初始化 parsed
        parsed = None
        try:
            # 🔧 [Agent Native 优先级调整 v3]
            # 优先级：Agent 输出的 GENERATIVE_UI 标签 > tool_result 数据
            # Agent 是决策大脑，应优先使用 Agent 自己决定的展示方式

            # ===== Step 1: 先尝试解析 Agent 输出的 GENERATIVE_UI 标签 =====
            # 这是最优先的，因为 Agent 自主决定了展示什么
            if response_text and "[GENERATIVE_UI]" in response_text:
                all_ui_cards = []
                # 🔧 [修复] 只解析一种标签格式，避免重复解析导致 duplicates
                # 原代码遍历 ["GENERATIVE_UI", "GENERATIVE_UI"]（相同字符串），导致重复解析
                open_tag = "[GENERATIVE_UI]"
                close_tag = "[/GENERATIVE_UI]"
                search_start = 0
                while open_tag in response_text[search_start:]:
                    tag_pos = response_text.find(open_tag, search_start)
                    if tag_pos == -1:
                        break
                    ui_start = tag_pos + len(open_tag)
                    ui_end = response_text.find(close_tag, ui_start)
                    if ui_end > ui_start:
                        ui_json_str = response_text[ui_start:ui_end].strip()
                        try:
                            ui_parsed = json.loads(ui_json_str)
                            if ui_parsed.get("component_type") and ui_parsed.get("props"):
                                all_ui_cards.append(ui_parsed)
                                logger.info(f"[DEERFLOW] 从 GENERATIVE_UI 提取卡片: {ui_parsed.get('component_type')}")
                        except json.JSONDecodeError as e:
                            logger.warning(f"[DEERFLOW] GENERATIVE_UI JSON 解析失败: {e}")
                        search_start = ui_end + len(close_tag)
                    else:
                        break

                # 处理提取到的卡片
                if all_ui_cards:
                    user_profile_cards = [c for c in all_ui_cards if c.get("component_type") == "UserProfileCard"]
                    if len(user_profile_cards) > 1:
                        # 多个用户卡片 → 构建匹配列表
                        generative_ui = {
                            "component_type": "MatchCardList",
                            "props": {
                                "matches": [c["props"] for c in user_profile_cards],
                                "total": len(user_profile_cards)
                            }
                        }
                        logger.info(f"[DEERFLOW] 合并 {len(user_profile_cards)} 个 UserProfileCard 为 MatchCardList")
                    elif len(all_ui_cards) == 1:
                        generative_ui = all_ui_cards[0]
                    else:
                        generative_ui = all_ui_cards[0] if all_ui_cards else None

                    # 从 response_text 中移除所有 GENERATIVE_UI 标签
                    # 🔧 [修复] 只移除一种标签格式
                    open_tag = "[GENERATIVE_UI]"
                    close_tag = "[/GENERATIVE_UI]"
                    while open_tag in response_text and close_tag in response_text:
                        start = response_text.find(open_tag)
                        end = response_text.find(close_tag, start + len(open_tag))
                        if end > start:
                            response_text = response_text[:start] + response_text[end + len(close_tag):]
                        else:
                            break
                    response_text = re.sub(r'\n\s*\n\s*\n', '\n\n', response_text.strip())
                    logger.info(f"[DEERFLOW] Agent 自主输出的 GENERATIVE_UI 已解析: {generative_ui.get('component_type') if generative_ui else 'None'}")

            # ===== Step 2: 获取 tool_result（供参考，但不用于构建 UI）=====
            if tool_results_list:
                valid_tool_results = [
                    item for item in tool_results_list if item.get("success") and item.get("data")
                ]
                if valid_tool_results:
                    tool_result = valid_tool_results[-1]
                    # 🔧 [Agent Native] 只有 Agent 没输出 GENERATIVE_UI 时才从 tool_result 构建
                    if not generative_ui:
                        ui = build_generative_ui_from_tool_result(tool_result)
                        if ui and ui.get("component_type") != "SimpleResponse":
                            generative_ui = ui
                            logger.info(f"[DEERFLOW] 从工具结果构建 generative_ui（降级）: {ui.get('component_type')}")
                    data = tool_result.get("data", {})
                    output_hint = tool_result.get("output_hint", "")
                    if output_hint:
                        response_text = output_hint
                        logger.info(f"[DEERFLOW] 使用 output_hint 作为回复: {output_hint[:50]}...")
                    else:
                        response_text = data.get("summary", tool_result.get("summary", response_text))

            # 如果没有从 stream 获取工具结果，尝试从文本中提取
            if not generative_ui and response_text:
                # parsed 已在外层初始化

                # 方式 1：直接 JSON（完整响应是 JSON）
                if response_text and response_text.strip().startswith("{") and response_text.strip().endswith("}"):
                    try:
                        parsed = json.loads(response_text.strip())
                    except json.JSONDecodeError:
                        pass

                # 方式 2：从 Markdown 代码块中提取 JSON
                if not parsed and response_text and "```json" in response_text:
                    try:
                        json_start = response_text.find("```json") + 7
                        json_end = response_text.find("```", json_start)
                        if json_end > json_start:
                            json_str = response_text[json_start:json_end].strip()
                            parsed = json.loads(json_str)
                            logger.info(f"[DEERFLOW] 从 Markdown 代码块提取 JSON 成功")
                    except json.JSONDecodeError:
                        pass

            # 方式 3：从文本中查找第一个完整的 JSON 对象
            if not parsed and "{" in response_text:
                try:
                    json_start = response_text.find("{")
                    # 找到匹配的闭合括号
                    brace_count = 0
                    json_end = json_start
                    for i, char in enumerate(response_text[json_start:], json_start):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    if json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        parsed = json.loads(json_str)
                        logger.info(f"[DEERFLOW] 从文本中提取 JSON 成功")
                except json.JSONDecodeError:
                    pass

            # 如果成功解析 JSON（ToolResult），构建 Generative UI
            if parsed and parsed.get("success") and parsed.get("data"):
                tool_result = parsed
                # 🔧 [修复] 如果已经从 GENERATIVE_UI 文本提取，不要覆盖
                if not generative_ui:
                    generative_ui = build_generative_ui_from_tool_result(parsed)
                # 🔧 [根治] 优先使用 output_hint，而非 summary/instruction
                data = parsed.get("data", {})
                output_hint = parsed.get("output_hint", "")
                if output_hint:
                    response_text = output_hint
                    logger.info(f"[DEERFLOW] 从 parsed 使用 output_hint: {output_hint[:50]}...")
                else:
                    # 兼容旧工具，使用 summary
                    response_text = data.get("summary", parsed.get("summary", response_text))

                # 提取学习结果（如果 DeerFlow 有学习洞察）
                data = parsed.get("data", {})
                if data.get("learned_insights"):
                    from services.learning_result_handler import get_learning_result_handler
                    handler = get_learning_result_handler()
                    learning_result = handler.parse_learning_result(parsed)

                    # 如果有高置信度洞察，添加确认卡片
                    if learning_result and learning_result.has_high_confidence_insight:
                        learning_ui = handler.build_learning_confirmation_ui(learning_result)
                        # 作为附加 UI 返回（不覆盖主 UI）
                        if generative_ui:
                            generative_ui["learning_confirmation"] = learning_ui
                        else:
                            generative_ui = learning_ui

            # 🔧 [新增] 如果没有解析到 JSON，但意图明确需要 UI，尝试构建基本 UI
            elif not parsed:
                # 根据意图推断结果，尝试构建对应的 UI
                intent_type = infer_intent_from_response(request.message, response_text, None, tool_result).get("type")

                # 意图需要 UI 但响应是纯文本 → 射击提示
                if intent_type in ["match_request", "topic_request", "icebreaker_request", "date_planning", "compatibility_analysis"]:
                    logger.warning(f"[DEERFLOW] 意图 {intent_type} 需要 UI，但 DeerFlow 返回纯文本，无法渲染")

        except json.JSONDecodeError:
            pass
        logger.info(f"[DEERFLOW] Response parsing done in {time.time() - parse_start:.3f}s")

        # 🔧 [修复] 推断意图类型（测试框架需要）
        generative_ui = _normalize_generative_ui(generative_ui)
        integrity_notice, generative_ui = _finalize_match_generative_ui(generative_ui, tool_result)

        # 🔧 [Agent Native] 意图从 Agent 响应推断，不使用预分类层
        intent = infer_intent_from_response(request.message, response_text, generative_ui, tool_result)
        logger.info(f"[DEERFLOW] Intent inferred from response: {intent['type']} (confidence={intent['confidence']})")

        # 🔧 [P0修复] Fallback：当意图识别失败但存在聊天相关数据时，强制构建 ChatInitiationCard
        # 根因：Agent 可能直接输出文本而非调用工具，导致 tool_result 缺失 component_type
        # 但 tool_data 中有 target_user_id 和 target_user_name，应该渲染聊天发起卡片
        if not generative_ui and tool_result:
            tool_data = tool_result.get("data", {})
            # 检查是否有聊天发起相关字段
            has_chat_fields = (
                tool_data.get("target_user_id") or
                tool_result.get("target_user_id") or
                tool_data.get("target_user_name") or
                tool_result.get("target_user_name")
            )
            if has_chat_fields:
                # 从 message 关键词进一步确认是发起聊天意图
                chat_keywords = ["发起聊天", "联系他", "开始对话", "帮我发起", "聊一聊", "和他聊"]
                if any(kw in request.message for kw in chat_keywords):
                    logger.info(f"[DEERFLOW] Fallback: 强制构建 ChatInitiationCard（意图识别失败但有聊天数据）")
                    generative_ui = _build_chat_initiation_fallback(tool_result, tool_data)
                    intent = {"type": "initiate_chat", "confidence": 0.85, "source": "fallback"}

        response_text = _render_structured_result_message(response_text, tool_result, generative_ui)
        response_text = _align_ai_message_with_structured_result(response_text, generative_ui)
        if integrity_notice:
            response_text = f"{integrity_notice}\n\n{(response_text or '').lstrip()}"
        observability_trace = _build_observability_trace(request, intent, generative_ui)
        # 🔧 [数据精简] 当 generative_ui 已包含 Agent 精选的候选人时，移除 tool_result 中的完整候选池
        tool_result = _trim_tool_result_candidates(tool_result, generative_ui)
        tool_result = _enrich_tool_result_with_observability(tool_result, observability_trace)
        logger.info(f"[DEERFLOW_TRACE] Final trace: {json.dumps(observability_trace, ensure_ascii=False)}")
        logger.info(f"[DEERFLOW] COMPLETE in {time.time() - start_time:.3f}s for user {request.user_id}")
        return DeerFlowResponse(
            success=True,
            ai_message=response_text,
            intent=intent,  # 🔧 [修复] 添加意图字段
            deerflow_used=True,
            generative_ui=generative_ui,
            tool_result=tool_result,
            learning_result=learning_result.to_dict() if learning_result else None,
        )

    except Exception as e:
        # 🔧 [调试] 记录完整的异常详情
        logger.error(f"[DEERFLOW_TRACE] ❌ DeerFlow chat 异常: {type(e).__name__}: {e}")
        logger.error(f"[DEERFLOW_TRACE] 异常堆栈:", exc_info=True)
        logger.info(f"[DEERFLOW_TRACE] 降级到 Her service 处理")
        return await _handle_with_her_service(request)


async def _handle_with_her_service(request: ChatRequest) -> DeerFlowResponse:
    """
    降级处理：直接调用 ConversationMatchService

    当 DeerFlow 不可用时，使用 Her 的核心服务处理对话
    """
    # 🔧 [调试] 记录降级处理详情
    logger.info(f"[HER_SERVICE_TRACE] ===== 开始 Her Service 降级处理 =====")
    logger.info(f"[HER_SERVICE_TRACE] user_id={request.user_id}")
    logger.info(f"[HER_SERVICE_TRACE] message={request.message[:100]}...")

    try:
        from services.conversation_match_service import get_conversation_match_service

        service = get_conversation_match_service()
        logger.info(f"[HER_SERVICE_TRACE] ConversationMatchService 获取成功")

        # 调用 ConversationMatchService
        her_start = time.time()
        response = await service.process_message(
            user_id=request.user_id or "anonymous",
            message=request.message,
            conversation_history=None
        )
        logger.info(f"[HER_SERVICE_TRACE] process_message 完成，耗时={time.time() - her_start:.3f}s")

        # 🔧 [调试] 记录 Her service 返回的响应
        logger.info(f"[HER_SERVICE_TRACE] response.ai_message={response.ai_message[:200] if response.ai_message else 'EMPTY'}...")
        logger.info(f"[HER_SERVICE_TRACE] response.intent_type={response.intent_type}")
        logger.info(f"[HER_SERVICE_TRACE] matches_count={len(response.matches)}")

        # 构建 Generative UI
        generative_ui = response.generative_ui if response.generative_ui else None
        generative_ui = _normalize_generative_ui(generative_ui)
        _, generative_ui = _finalize_match_generative_ui(generative_ui, None)

        # 🔧 [修复] 添加意图字段
        intent = {"type": response.intent_type, "confidence": 0.8, "source": "her_service"}

        # 🔧 [调试] 记录最终返回结果
        logger.info(f"[HER_SERVICE_TRACE] 最终返回: success=True, deerflow_used=False")
        logger.info(f"[HER_SERVICE_TRACE] intent={intent}")
        logger.info(f"[HER_SERVICE_TRACE] ===== Her Service 降级处理完成 =====")

        observability_trace = _build_observability_trace(request, intent, generative_ui)
        logger.info(f"[HER_SERVICE_TRACE] Final trace: {json.dumps(observability_trace, ensure_ascii=False)}")

        return DeerFlowResponse(
            success=True,
            ai_message=response.ai_message,
            intent=intent,  # 🔧 [修复] 添加意图字段
            deerflow_used=False,  # 标记未使用 DeerFlow
            generative_ui=generative_ui,
            tool_result={
                "intent_type": response.intent_type,
                "matches_count": len(response.matches),
                "has_bias_analysis": response.bias_analysis is not None,
                "observability": observability_trace,
            },
        )

    except Exception as e:
        # 🔧 [调试] 记录 Her service 异常详情
        logger.error(f"[HER_SERVICE_TRACE] ❌ Her service 异常: {type(e).__name__}: {e}")
        logger.error(f"[HER_SERVICE_TRACE] 异常堆栈:", exc_info=True)
        logger.info(f"[HER_SERVICE_TRACE] 返回友好错误响应")

        # 🔧 [安全兜底] 不暴露异常详情，返回友好提示
        return DeerFlowResponse(
            success=True,  # 返回 success=True，前端显示友好消息
            ai_message="抱歉，系统暂时繁忙。请稍后再试，或换个方式描述您的需求。",
            intent={"type": "error_fallback", "confidence": 0.5},
            deerflow_used=False
        )


def build_generative_ui_from_tool_result(tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据 Agent 返回的结构化数据构建 Generative UI

    【Agent Native 设计原则】
    工具只返回原始数据，Agent 自己决定如何展示（通过 GENERATIVE_UI 标签）。

    此函数职责：
    1. 如果工具已指定 component_type → 直接使用（工具明确要求的 UI）
    2. 其他情况 → 返回 None，让 Agent 自己决定

    🔧 [Agent Native 修复 v2]
    移除以下自动构建逻辑（违反 Agent Native 原则）：
    - candidates/matches/recommendations → MatchCardList（Agent 应自己筛选并输出）
    - users → MatchCardList（Agent 应自己决定展示方式）

    Agent 会：
    1. 收到工具返回的原始候选池数据
    2. 根据 user_preferences 自主筛选 1-3 位
    3. 输出 [GENERATIVE_UI] 标签展示选中的候选人

    维护规则：
    - 新增组件必须在 generative_ui_schema.py 中注册
    - 必填 props 必须校验
    - 前端对应的 generativeCard 值必须同步
    """
    from generative_ui_schema import get_frontend_card, validate_props, GENERATIVE_UI_SCHEMA

    data = tool_result.get("data", {})

    # ===== Agent Native：优先使用工具指定的 component_type =====
    if data.get("component_type"):
        # 工具已明确要求特定 UI 类型，直接使用
        component_type = data.get("component_type")
        # props 应该从 data 中提取，不要包含 component_type
        props = {k: v for k, v in data.items() if k != "component_type"}

        logger.info(f"[GenerativeUI] 工具指定的 UI: {component_type}, props keys: {list(props.keys())}")
        return _build_ui_response(component_type, props)

    # ===== Agent Native：以下情况不自动构建 UI，让 Agent 自己决定 =====

    # 🔧 [移除] candidates/matches/recommendations 不自动构建 MatchCardList
    # Agent 应自己筛选并输出 GENERATIVE_UI 标签

    # 🔧 [移除] users 不自动构建 MatchCardList
    # Agent 应自己决定如何展示搜索结果

    # ===== 仅保留必要的降级判断（非匹配类 UI）=====

    # 信息收集卡片 → ProfileQuestionCard（新用户流程，必须有 UI）
    if data.get("question_card") or data.get("need_collection"):
        question_card = data.get("question_card", {})
        props = {
            "question": question_card.get("question", "请告诉我更多信息"),
            "subtitle": question_card.get("subtitle", ""),
            "question_type": question_card.get("question_type", "single_choice"),
            "options": question_card.get("options", []),
            "dimension": question_card.get("dimension", ""),
            "depth": question_card.get("depth", 0),
            "need_follow_up": data.get("need_follow_up", False),
        }
        return _build_ui_response("ProfileQuestionCard", props)

    # 用户详情卡片 → UserProfileCard（严格基于 selected_user 或带明确ID的 user_profile）
    # 说明：
    # - selected_user 是"目标用户"单一真相来源，应优先使用
    # - target_profile 是 her_get_icebreaker 等工具返回的目标用户信息（需要有 user_id）
    # - user_profile 在不同工具中语义不一致（可能是当前用户），没有 user_id/id 时禁止渲染详情卡
    selected_user = data.get("selected_user")
    target_profile = data.get("target_profile")
    user_profile = data.get("user_profile")
    user_data = None
    if isinstance(selected_user, dict) and (selected_user.get("user_id") or selected_user.get("id")):
        user_data = selected_user
    elif isinstance(target_profile, dict) and (target_profile.get("user_id") or target_profile.get("id")):
        # 🔧 [修复] target_profile 也需要有 user_id 才能渲染详情卡
        user_data = target_profile
    elif isinstance(user_profile, dict) and (user_profile.get("user_id") or user_profile.get("id")):
        user_data = user_profile

    if user_data:
        user_id = user_data.get("user_id") or user_data.get("id")
        props = {
            "user_id": user_id,
            "name": user_data.get("name", "TA"),
            "age": user_data.get("age", 0),
            "location": user_data.get("location", ""),
            "confidence_icon": user_data.get("confidence_icon", "✓"),
            "confidence_level": user_data.get("confidence_level", "medium"),
            "confidence_score": user_data.get("confidence_score", 40),
            "occupation": user_data.get("occupation", ""),
            "interests": user_data.get("interests", []),
            "bio": user_data.get("bio", ""),
            "relationship_goal": user_data.get("relationship_goal", ""),
            "actions": [
                {"label": "开始对话", "action": "start_chat", "target_user_id": user_id},
                {"label": "查看详情", "action": "view_profile", "target_user_id": user_id},
            ]
        }
        return _build_ui_response("UserProfileCard", props)

    # 🔧 [新增] 发起聊天卡片 → ChatInitiationCard
    # 当有 target_user_id 和 target_user_name，但不是 UserProfileCard 时
    if data.get("target_user_id") and data.get("target_user_name") and not user_data:
        props = {
            "target_user_id": data.get("target_user_id"),
            "target_user_name": data.get("target_user_name"),
            "target_user_avatar": data.get("target_user_avatar", ""),
            "target_user_location": data.get("target_user_location", ""),
            "target_user_age": data.get("target_user_age", 0),
            "target_user_interests": data.get("target_user_interests", []),
            "context": data.get("context", ""),
            "compatibility_score": data.get("compatibility_score", 0),
            "_schema": data.get("_schema", {}),
        }
        return _build_ui_response("ChatInitiationCard", props)

    # 兼容性分析 → CompatibilityChart
    if data.get("overall_score") and data.get("dimensions"):
        props = {
            "overall_score": data.get("overall_score"),
            "dimensions": data.get("dimensions"),
            "conflicts": data.get("conflicts", []),
            "strengths": data.get("strengths", [])
        }
        return _build_ui_response("CompatibilityChart", props)

    # 约会方案 → DatePlanCard
    if data.get("plans"):
        props = {
            "plans": data.get("plans"),
            "best_pick": data.get("best_pick"),
            "tips": data.get("tips", [])
        }
        return _build_ui_response("DatePlanCard", props)

    # 破冰建议 → IcebreakerCard
    if data.get("icebreakers"):
        props = {
            "icebreakers": data.get("icebreakers"),
            "best_pick": data.get("best_pick"),
            "tips": data.get("tips", [])
        }
        return _build_ui_response("IcebreakerCard", props)

    # 话题推荐 → TopicsCard
    if data.get("topics"):
        props = {
            "topics": data.get("topics"),
            "total": data.get("total")
        }
        return _build_ui_response("TopicsCard", props)

    # 关系健康度 → RelationshipHealthCard
    if data.get("health_score"):
        props = {
            "health_score": data.get("health_score"),
            "strengths": data.get("strengths", []),
            "issues": data.get("issues", []),
            "suggestions": data.get("suggestions", [])
        }
        return _build_ui_response("RelationshipHealthCard", props)

    # 默认 → SimpleResponse（纯文本，无卡片）
    return _build_ui_response("SimpleResponse", {"content": tool_result.get("summary", "")})


def _build_chat_initiation_fallback(
    tool_result: Optional[Dict[str, Any]],
    tool_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    🔧 [P0修复] Fallback 构建 ChatInitiationCard

    当 Agent 直接输出文本而非调用工具时，tool_result 可能缺少 component_type，
    但 tool_data 中有 target_user_id 和 target_user_name。
    此函数强制构建 ChatInitiationCard，确保聊天发起功能落地。

    Args:
        tool_result: 完整的 tool_result
        tool_data: tool_result.data 部分

    Returns:
        ChatInitiationCard 结构
    """
    data = tool_data or tool_result or {}

    # 提取字段（支持多层位置）
    target_user_id = (
        data.get("target_user_id") or
        tool_result.get("target_user_id") if tool_result else None
    )
    target_user_name = (
        data.get("target_user_name") or
        tool_result.get("target_user_name") if tool_result else None or
        "TA"
    )

    props = {
        "target_user_id": target_user_id,
        "target_user_name": target_user_name,
        "target_user_avatar": data.get("target_user_avatar", ""),
        "target_user_location": data.get("target_user_location", ""),
        "target_user_age": data.get("target_user_age", 0),
        "target_user_interests": data.get("target_user_interests", []),
        "context": data.get("context", ""),
        "compatibility_score": data.get("compatibility_score", 0),
        "_schema": {
            "backend_type": "ChatInitiationCard",
            "frontend_card": "chat_initiation",
            "description": "发起聊天确认卡片（Fallback 构建）"
        },
    }

    logger.info(f"[GenerativeUI] Fallback 构建 ChatInitiationCard: target={target_user_name}")
    return _build_ui_response("ChatInitiationCard", props)


def _build_ui_response(component_type: str, props: Dict[str, Any]) -> Dict[str, Any]:
    """
    构建 UI 响应（带校验）

    Args:
        component_type: 组件类型
        props: 组件 props

    Returns:
        Generative UI 响应
    """
    from generative_ui_schema import validate_props, GENERATIVE_UI_SCHEMA

    # 校验必填 props
    is_valid, missing = validate_props(component_type, props)
    if not is_valid:
        logger.warning(f"[GenerativeUI] component_type={component_type} 缺少必填 props: {missing}")

    # 添加 schema 信息（方便前端调试）
    schema = GENERATIVE_UI_SCHEMA.get(component_type, {})
    props["_schema"] = {
        "backend_type": component_type,
        "frontend_card": schema.get("frontend_card"),
        "description": schema.get("description"),
    }

    return {
        "component_type": component_type,
        "props": props,
    }


@router.post("/stream")
async def stream(request: StreamRequest):
    """
    流式发送消息到 DeerFlow Agent

    Args:
        request: StreamRequest

    Returns:
        StreamingResponse (SSE format)
    """
    from fastapi.responses import StreamingResponse
    import json

    logger.info(f"DeerFlow API: stream request, thread_id={request.thread_id}")

    if not DEERFLOW_AVAILABLE:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'end', 'data': {'error': 'DeerFlow not available'}})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    client = get_deerflow_client()
    if not client:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'end', 'data': {'error': 'DeerFlow client not initialized'}})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # 同步用户画像
    if request.user_id:
        sync_user_memory_to_deerflow(request.user_id)

    async def generate_stream():
        try:
            for event in client.stream(request.message, thread_id=request.thread_id, user_id=request.user_id):
                yield f"data: {json.dumps({'type': event.type, 'data': event.data})}\n\n"
        except Exception as e:
            logger.error(f"DeerFlow stream error: {e}")
            yield f"data: {json.dumps({'type': 'end', 'data': {'error': str(e)}})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@router.post("/learning/confirm", response_model=LearningConfirmResponse)
async def confirm_learning(request: LearningConfirmRequest):
    """
    确认并应用 DeerFlow 学习结果

    当用户在对话中确认"将这些信息添加到画像"时调用。

    Args:
        request: LearningConfirmRequest

    Returns:
        LearningConfirmResponse
    """
    logger.info(f"[DeerFlow学习确认] 用户 {request.user_id} 确认了 {len(request.insights)} 个洞察")

    try:
        from services.learning_result_handler import get_learning_result_handler

        handler = get_learning_result_handler()
        result = await handler.apply_learning_result(request.user_id, request.insights)

        return LearningConfirmResponse(
            success=result.get("success", True),
            applied_count=result.get("applied_count", 0),
            applied_dimensions=result.get("applied_dimensions", []),
            message=result.get("message", "画像已更新"),
        )

    except Exception as e:
        logger.error(f"[DeerFlow学习确认] 处理失败: {e}")
        return LearningConfirmResponse(
            success=False,
            applied_count=0,
            applied_dimensions=[],
            message=f"更新失败：{str(e)}",
        )


@router.get("/status", response_model=DeerFlowStatusResponse)
async def get_status():
    """
    获取 DeerFlow 状态

    Returns:
        DeerFlowStatusResponse
    """
    memory_path = os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", ".deer-flow", "memory.json")
    memory_enabled = os.path.exists(memory_path)

    return DeerFlowStatusResponse(
        available=DEERFLOW_AVAILABLE,
        path=os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", "packages", "harness"),
        config_path=os.path.join(HER_PROJECT_ROOT, "deerflow", "config.yaml"),
        config_exists=os.path.exists(os.path.join(HER_PROJECT_ROOT, "deerflow", "config.yaml")),
        memory_enabled=memory_enabled
    )


@router.post("/reset")
async def reset_client():
    """
    重置 DeerFlow 客户端

    当 config.yaml 更新后（如新增工具），需要调用此接口让 DeerFlow 重新加载配置。

    Returns:
        {"success": true, "message": "DeerFlow 客户端已重置"}
    """
    logger.info("[DeerFlow] 收到重置请求，将重新加载配置和工具")
    reset_deerflow_client()

    # 同时重置 checkpointer（如果需要）
    try:
        from deerflow.agents.checkpointer.provider import reset_checkpointer
        reset_checkpointer()
        logger.info("[DeerFlow] Checkpointer 已重置")
    except Exception as e:
        logger.warning(f"[DeerFlow] Checkpointer 重置失败: {e}")

    return {"success": True, "message": "DeerFlow 客户端已重置，配置和工具已重新加载"}