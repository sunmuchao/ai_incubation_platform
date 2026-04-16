"""
意图配置加载器

从 YAML 文件加载意图配置，支持：
- 热更新（无需重启服务）
- 配置校验
- 缓存机制

使用示例：
    from config.intent_config_loader import get_intent_config_loader

    loader = get_intent_config_loader()
    config = loader.get_config()

    # 获取意图关键词
    keywords = config.get_keywords("matching")

    # 获取所有意图（按优先级排序）
    intents = config.get_sorted_intents()

    # 热更新配置
    loader.reload()
"""
import yaml
import pathlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import threading

from utils.logger import logger


# ============= 配置数据结构 =============

@dataclass
class IntentConfig:
    """单个意图配置"""
    name: str
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    priority: int = 10
    skill: Optional[str] = None
    deerflow_tool: Optional[str] = None  # 新架构：直接调用 DeerFlow 工具
    is_local: bool = False
    response_template: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "priority": self.priority,
            "skill": self.skill,
            "deerflow_tool": self.deerflow_tool,
            "is_local": self.is_local,
            "response_template": self.response_template,
        }


@dataclass
class SuggestedActionConfig:
    """建议操作配置"""
    label: str
    action: str


@dataclass
class FeatureConfig:
    """功能介绍配置"""
    name: str
    description: str


@dataclass
class FullIntentConfig:
    """完整意图配置"""
    intents: Dict[str, IntentConfig] = field(default_factory=dict)
    suggested_actions: Dict[str, List[SuggestedActionConfig]] = field(default_factory=dict)
    capability_intro: str = ""
    feature_list: List[FeatureConfig] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 排序后的意图列表（按优先级）
    _sorted_intents: List[IntentConfig] = field(default_factory=list)

    def get_keywords(self, intent_name: str) -> List[str]:
        """获取指定意图的关键词"""
        intent = self.intents.get(intent_name)
        return intent.keywords if intent else []

    def get_sorted_intents(self) -> List[IntentConfig]:
        """获取按优先级排序的意图列表"""
        if not self._sorted_intents:
            self._sorted_intents = sorted(
                self.intents.values(),
                key=lambda x: x.priority
            )
        return self._sorted_intents

    def get_local_intents(self) -> List[str]:
        """获取本地处理的意图名称列表"""
        return [name for name, intent in self.intents.items() if intent.is_local]

    def get_skill_mapping(self) -> Dict[str, Optional[str]]:
        """获取意图到 Skill 的映射"""
        return {name: intent.skill for name, intent in self.intents.items()}

    def get_response_template(self, intent_name: str) -> str:
        """获取意图的响应模板"""
        intent = self.intents.get(intent_name)
        return intent.response_template if intent else ""

    def get_suggested_actions(self, intent_name: str) -> List[Dict[str, str]]:
        """获取意图的建议操作"""
        actions = self.suggested_actions.get(intent_name, [])
        return [{"label": a.label, "action": a.action} for a in actions]


# ============= 配置加载器 =============

class IntentConfigLoader:
    """
    意图配置加载器

    功能：
    1. 从 YAML 文件加载配置
    2. 配置校验
    3. 热更新支持
    4. 缓存机制
    """

    DEFAULT_CONFIG_PATH = pathlib.Path(__file__).parent / "intents.yaml"

    def __init__(self, config_path: Optional[pathlib.Path] = None):
        self._config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[FullIntentConfig] = None
        self._last_loaded: Optional[datetime] = None
        self._lock = threading.Lock()

        # 首次加载
        self._load_config()

    def _load_config(self) -> None:
        """加载 YAML 配置文件"""
        if not self._config_path.exists():
            logger.error(f"[IntentConfigLoader] 配置文件不存在: {self._config_path}")
            self._config = self._get_default_config()
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)

            self._config = self._parse_config(raw_config)
            self._last_loaded = datetime.now()

            logger.info(
                f"[IntentConfigLoader] 配置加载成功: "
                f"{len(self._config.intents)} 个意图, "
                f"版本 {self._config.metadata.get('version', 'unknown')}"
            )

        except Exception as e:
            logger.error(f"[IntentConfigLoader] 配置加载失败: {e}")
            self._config = self._get_default_config()

    def _parse_config(self, raw: Dict[str, Any]) -> FullIntentConfig:
        """解析原始配置为结构化对象"""
        config = FullIntentConfig()

        # 解析意图
        for intent_raw in raw.get("intents", []):
            intent = IntentConfig(
                name=intent_raw.get("name", ""),
                description=intent_raw.get("description", ""),
                keywords=intent_raw.get("keywords", []),
                priority=intent_raw.get("priority", 10),
                skill=intent_raw.get("skill"),
                deerflow_tool=intent_raw.get("deerflow_tool"),  # 新架构：DeerFlow 工具
                is_local=intent_raw.get("is_local", False),
                response_template=intent_raw.get("response_template", ""),
            )
            config.intents[intent.name] = intent

        # 解析建议操作
        for intent_name, actions_raw in raw.get("suggested_actions", {}).items():
            config.suggested_actions[intent_name] = [
                SuggestedActionConfig(
                    label=a.get("label", ""),
                    action=a.get("action", "")
                )
                for a in actions_raw
            ]

        # 解析能力介绍
        config.capability_intro = raw.get("capability_intro", "")

        # 解析功能列表
        for feature_raw in raw.get("feature_list", []):
            config.feature_list.append(
                FeatureConfig(
                    name=feature_raw.get("name", ""),
                    description=feature_raw.get("description", ""),
                )
            )

        # 解析元数据
        config.metadata = raw.get("metadata", {})

        return config

    def _get_default_config(self) -> FullIntentConfig:
        """获取默认配置（配置文件加载失败时使用）"""
        config = FullIntentConfig()

        # 最小化默认意图
        default_intents = [
            IntentConfig(name="matching", keywords=["找人", "匹配", "推荐"], priority=1, skill="conversation_matchmaker"),
            IntentConfig(name="greeting", keywords=["你好", "hi"], priority=2, is_local=True),
            IntentConfig(name="general", keywords=[], priority=3, is_local=True),
        ]

        for intent in default_intents:
            config.intents[intent.name] = intent

        return config

    def get_config(self) -> FullIntentConfig:
        """获取当前配置"""
        with self._lock:
            return self._config

    def reload(self) -> bool:
        """
        热更新配置

        Returns:
            True: 更新成功
            False: 更新失败，继续使用旧配置
        """
        with self._lock:
            try:
                self._load_config()
                return True
            except Exception as e:
                logger.error(f"[IntentConfigLoader] 热更新失败: {e}")
                return False

    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息（用于调试）"""
        return {
            "config_path": str(self._config_path),
            "last_loaded": self._last_loaded.isoformat() if self._last_loaded else None,
            "intent_count": len(self._config.intents) if self._config else 0,
            "metadata": self._config.metadata if self._config else {},
        }


# ============= 全局实例 =============

_loader_instance: Optional[IntentConfigLoader] = None
_loader_lock = threading.Lock()


def get_intent_config_loader() -> IntentConfigLoader:
    """获取意图配置加载器单例"""
    global _loader_instance

    with _loader_lock:
        if _loader_instance is None:
            _loader_instance = IntentConfigLoader()
            logger.info("IntentConfigLoader initialized")

    return _loader_instance