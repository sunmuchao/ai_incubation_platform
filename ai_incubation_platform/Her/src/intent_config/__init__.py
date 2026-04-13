"""
意图路由配置模块

包含意图配置加载器，支持 YAML 配置热更新。

导入方式：
- IntentConfigLoader: from intent_config.intent_config_loader import IntentConfigLoader
- get_intent_config_loader: from intent_config.intent_config_loader import get_intent_config_loader
"""

from intent_config.intent_config_loader import IntentConfigLoader, get_intent_config_loader

__all__ = ["IntentConfigLoader", "get_intent_config_loader"]