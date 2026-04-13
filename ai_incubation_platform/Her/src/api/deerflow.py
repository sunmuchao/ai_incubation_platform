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
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import sys
import json

from utils.logger import logger

router = APIRouter(prefix="/api/deerflow", tags=["deerflow"])

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

    from deerflow.client import DeerFlowClient
    from deerflow.config.app_config import reload_app_config

    DEERFLOW_AVAILABLE = True

    # 初始化 DeerFlow 客户端
    config_path = os.path.join(HER_PROJECT_ROOT, "deerflow", "config.yaml")

    # 全局客户端缓存
    _deerflow_client_cache: Optional[DeerFlowClient] = None

    def get_deerflow_client() -> Optional[DeerFlowClient]:
        """获取 DeerFlow 客户端实例（带缓存）"""
        global _deerflow_client_cache

        if _deerflow_client_cache is not None:
            return _deerflow_client_cache

        if os.path.exists(config_path):
            reload_app_config(config_path)
            _deerflow_client_cache = DeerFlowClient(config_path=config_path)
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
    获取 Her 用户画像

    从 Her 的数据库获取用户基本信息和偏好

    🔧 [修复] 使用原生 SQL 查询，绕过 ORM schema 不一致问题
    """
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
            # 默认路径
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "matchmaker.db")

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

        return {
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


def sync_user_memory_to_deerflow(user_id: str) -> int:
    """
    同步用户画像到用户独立的 Memory 文件

    【用户隔离架构】

    每个用户有独立的 memory 文件，防止数据混用：
    - 路径：{base_dir}/users/{user_id}/memory.json
    - 只包含当前用户的基本信息和偏好
    - DeerFlow Agent 仍然使用全局 memory（对话历史等）

    目录结构：
        {base_dir}/
        ├── memory.json          ← DeerFlow 全局 memory（对话历史）
        └── users/
            └── {user_id}/
                └── memory.json  ← 用户独立 memory（基本信息 + 偏好）

    同步时机：
    - 用户发起对话时（/api/deerflow/chat）
    - 用户在 Her 中更新画像后

    Returns:
        同步的 facts 数量
    """
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

        # Step 3: 写入用户独立的 memory 文件
        user_memory_dir = os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", ".deer-flow", "users", user_id)
        user_memory_path = os.path.join(user_memory_dir, "memory.json")

        # 创建目录
        os.makedirs(user_memory_dir, exist_ok=True)

        # 构建用户 memory 数据结构
        user_memory_data = {
            "version": "1.0",
            "lastUpdated": datetime.now().isoformat(),
            "facts": facts,
        }

        # 原子写入
        temp_path = user_memory_path + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(user_memory_data, f, ensure_ascii=False, indent=2)
        os.rename(temp_path, user_memory_path)

        logger.info(f"[Memory同步] Her → 用户独立文件: {len(facts)} facts for user {user_id}")

        return len(facts)

    except Exception as e:
        logger.error(f"Failed to sync user memory: {e}")
        return 0


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


async def _handle_with_deerflow(request: ChatRequest) -> DeerFlowResponse:
    """使用 DeerFlow Agent 处理"""
    import time
    start_time = time.time()

    client = get_deerflow_client()
    if not client:
        logger.warning("DeerFlow client not available, fallback to Her service")
        return await _handle_with_her_service(request)

    try:
        # 如果有 user_id，同步用户画像到 Memory（首次对话时）
        # 注：不再每次请求都 reset_agent()，DeerFlowClient 已有 agent 缓存机制
        # 只有在 SOUL.md 或 Skills 配置更新后才需要手动 reset_agent()
        if request.user_id:
            sync_start = time.time()
            sync_user_memory_to_deerflow(request.user_id)
            logger.info(f"[DEERFLOW] Memory sync done in {time.time() - sync_start:.3f}s for user {request.user_id}")

        # 调用 DeerFlow（传入 user_id 以实现用户隔离）
        thread_id = request.thread_id or f"her-{request.user_id or 'anonymous'}-{os.urandom(4).hex()}"

        chat_start = time.time()
        response_text = client.chat(request.message, thread_id=thread_id, user_id=request.user_id)
        logger.info(f"[DEERFLOW] Agent chat done in {time.time() - chat_start:.3f}s for message: {request.message[:30]}...")

        # 解析响应，提取结构化数据
        tool_result = None
        generative_ui = None
        learning_result = None

        parse_start = time.time()
        try:
            if response_text.startswith("{") and response_text.endswith("}"):
                parsed = json.loads(response_text)
                if parsed.get("success") and parsed.get("data"):
                    tool_result = parsed
                    generative_ui = build_generative_ui_from_tool_result(parsed)
                    response_text = parsed.get("summary", response_text)

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

        except json.JSONDecodeError:
            pass
        logger.info(f"[DEERFLOW] Response parsing done in {time.time() - parse_start:.3f}s")

        logger.info(f"[DEERFLOW] COMPLETE in {time.time() - start_time:.3f}s for user {request.user_id}")
        return DeerFlowResponse(
            success=True,
            ai_message=response_text,
            deerflow_used=True,
            generative_ui=generative_ui,
            tool_result=tool_result,
            learning_result=learning_result.to_dict() if learning_result else None,
        )

    except Exception as e:
        logger.error(f"DeerFlow chat error: {e}, fallback to Her service")
        return await _handle_with_her_service(request)


async def _handle_with_her_service(request: ChatRequest) -> DeerFlowResponse:
    """
    降级处理：直接调用 ConversationMatchService

    当 DeerFlow 不可用时，使用 Her 的核心服务处理对话
    """
    logger.info(f"[Her降级处理] user_id={request.user_id}")

    try:
        from services.conversation_match_service import get_conversation_match_service

        service = get_conversation_match_service()

        # 调用 ConversationMatchService
        response = await service.process_message(
            user_id=request.user_id or "anonymous",
            message=request.message,
            conversation_history=None
        )

        # 构建 Generative UI
        generative_ui = response.generative_ui if response.generative_ui else None

        return DeerFlowResponse(
            success=True,
            ai_message=response.ai_message,
            deerflow_used=False,  # 标记未使用 DeerFlow
            generative_ui=generative_ui,
            tool_result={
                "intent_type": response.intent_type,
                "matches_count": len(response.matches),
                "has_bias_analysis": response.bias_analysis is not None,
            }
        )

    except Exception as e:
        logger.error(f"Her service error: {e}")
        return DeerFlowResponse(
            success=False,
            ai_message=f"处理出错：{str(e)}",
            deerflow_used=False
        )


def build_generative_ui_from_tool_result(tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据工具返回的结构化数据构建 Generative UI

    前端根据 component_type 渲染不同的卡片。

    维护规则：
    - 新增组件必须在 generative_ui_schema.py 中注册
    - 必填 props 必须校验
    - 前端对应的 generativeCard 值必须同步
    """
    from generative_ui_schema import get_frontend_card, validate_props, GENERATIVE_UI_SCHEMA

    data = tool_result.get("data", {})

    # 信息收集卡片 → ProfileQuestionCard（优先级最高，新用户流程）
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

    # 匹配结果 → MatchCardList
    if data.get("matches") or data.get("recommendations"):
        matches = data.get("matches") or data.get("recommendations")
        props = {
            "matches": matches,
            "total": data.get("total", len(matches))
        }
        return _build_ui_response("MatchCardList", props)

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

    # 默认 → SimpleResponse
    return _build_ui_response("SimpleResponse", {"content": tool_result.get("summary", "")})


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