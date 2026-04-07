"""
意图识别工具 - 识别用户意图属于哪个子项目领域
"""
import logging
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)


# 子项目能力映射表
SUB_PROJECTS = {
    "ai-hires-human": {
        "keywords": ["任务", "招聘", "雇佣", "工人", "雇主", "零工", "兼职", "crowd", "human", "hire", "task"],
        "description": "AI 雇佣真人平台 - 发布任务、招聘真人完成 AI 无法完成的工作",
        "capabilities": ["任务发布", "工人匹配", "任务验收", "支付托管", "信誉管理"],
    },
    "ai-employee-platform": {
        "keywords": ["员工", "雇主", "匹配", "入职", "培训", "绩效", "employee", "talent", "matching"],
        "description": "AI 员工平台 - AI 与人类员工协作的企业级人才市场",
        "capabilities": ["人才匹配", "员工管理", "培训发展", "绩效评估"],
    },
    "human-ai-community": {
        "keywords": ["社区", "讨论", "帖子", "频道", "成员", "治理", "reputation", "community", "forum"],
        "description": "人类-AI 社区 - 去中心化社区治理和成员互动平台",
        "capabilities": ["内容发布", "社区治理", "成员匹配", "信誉系统", "经济激励"],
    },
    "ai-community-buying": {
        "keywords": ["团购", "拼团", "砍价", "商品", "供应链", "拼单", "groupbuy", "buying", "shopping"],
        "description": "AI 社区团购平台 - AI 辅助选品和团购管理的电商平台",
        "capabilities": ["商品选择", "团购管理", "供应链优化", "需求预测", "动态定价"],
    },
    "ai-opportunity-miner": {
        "keywords": ["商机", "机会", "挖掘", "发现", "市场", "opportunity", "miner", "discover"],
        "description": "AI 商机挖掘 - 发现市场机会和创业灵感",
        "capabilities": ["市场分析", "机会发现", "竞争分析", "趋势预测"],
    },
    "ai-runtime-optimizer": {
        "keywords": ["优化", "性能", "运行时", "runtime", "optimizer", "performance"],
        "description": "AI 运行时优化器 - 优化 AI 应用的执行性能",
        "capabilities": ["性能分析", "资源优化", "执行计划优化"],
    },
    "ai-traffic-booster": {
        "keywords": ["流量", "推广", "引流", "traffic", "booster", "marketing"],
        "description": "AI 流量加速器 - AI 驱动的流量获取和推广工具",
        "capabilities": ["流量分析", "推广策略", "渠道优化"],
    },
    "ai-code-understanding": {
        "keywords": ["代码", "理解", "分析", "code", "understanding", "analysis"],
        "description": "AI 代码理解 - 代码分析和理解工具",
        "capabilities": ["代码分析", "架构理解", "依赖分析"],
    },
    "data-agent-connector": {
        "keywords": ["数据", "连接器", "ETL", "data", "connector", "integration"],
        "description": "数据-Agent 连接器 - 连接数据源和 AI Agent",
        "capabilities": ["数据集成", "Agent 数据访问", "ETL 流程"],
    },
    "matchmaker-agent": {
        "keywords": ["匹配", "撮合", "matchmaker", "matching"],
        "description": "智能匹配 Agent - 通用匹配和撮合服务",
        "capabilities": ["双向匹配", "推荐算法", "匹配优化"],
    },
    "loganalyzer-agent": {
        "keywords": ["日志", "分析", "log", "analyzer", "monitoring"],
        "description": "日志分析 Agent - 自动分析系统日志和错误",
        "capabilities": ["日志分析", "异常检测", "根因分析"],
    },
    "platform-portal": {
        "keywords": ["门户", "入口", "导航", "portal", "entry", "navigation"],
        "description": "平台门户 - 统一入口和跨项目编排",
        "capabilities": ["意图识别", "路由分发", "跨项目工作流"],
    },
}

# 意图分类模型提示词模板
INTENT_ANALYSIS_PROMPT = """
请分析用户的自然语言输入，识别其意图属于哪个 AI 孵化平台子项目。

可用子项目列表：
{projects_info}

用户输入：{user_input}

请返回 JSON 格式的分析结果：
{{
    "project": "匹配的子项目名称",
    "confidence": 0.0-1.0 之间的置信度分数，
    "reasoning": "匹配理由",
    "detected_capabilities": ["用户可能需要的能力列表"],
    "alternative_projects": [
        {{"project": "备选项目 1", "confidence": 0.x}},
        {{"project": "备选项目 2", "confidence": 0.x}}
    ]
}}
"""


class IntentRecognizer:
    """意图识别器"""

    def __init__(self):
        self._projects_info = self._build_projects_info()

    def _build_projects_info(self) -> str:
        """构建项目信息字符串"""
        lines = []
        for name, info in SUB_PROJECTS.items():
            lines.append(f"- {name}: {info['description']}")
            lines.append(f"  能力：{', '.join(info['capabilities'])}")
        return "\n".join(lines)

    def recognize(self, user_input: str) -> Dict[str, Any]:
        """
        识别用户意图

        Args:
            user_input: 用户自然语言输入

        Returns:
            意图识别结果
        """
        logger.info(f"Recognizing intent for: {user_input[:100]}...")

        # 尝试使用 LLM 进行意图识别
        result = self._llm_recognize(user_input)

        # 如果 LLM 不可用，降级到关键词匹配
        if result is None:
            result = self._keyword_recognize(user_input)

        return result

    def _llm_recognize(self, user_input: str) -> Optional[Dict[str, Any]]:
        """使用 LLM 进行意图识别（需要外部 AI 服务）"""
        # 这是占位实现，实际应调用 DeerFlow 或其他 AI 服务
        # 这里返回 None 触发降级
        return None

    def _keyword_recognize(self, user_input: str) -> Dict[str, Any]:
        """关键词匹配的降级实现"""
        input_lower = user_input.lower()
        matches = []

        for project_name, project_info in SUB_PROJECTS.items():
            score = 0
            matched_keywords = []

            for keyword in project_info["keywords"]:
                if keyword.lower() in input_lower:
                    score += 1
                    matched_keywords.append(keyword)

            if score > 0:
                matches.append({
                    "project": project_name,
                    "score": score,
                    "matched_keywords": matched_keywords,
                    "description": project_info["description"],
                    "capabilities": project_info["capabilities"],
                })

        # 按得分排序
        matches.sort(key=lambda x: x["score"], reverse=True)

        if not matches:
            # 默认返回门户项目
            return {
                "project": "platform-portal",
                "confidence": 0.5,
                "reasoning": "未检测到明确的子项目意图，默认路由到门户",
                "detected_capabilities": ["意图识别", "路由分发"],
                "alternative_projects": [],
            }

        best_match = matches[0]
        total_keywords = len(SUB_PROJECTS[best_match["project"]]["keywords"])
        confidence = min(1.0, best_match["score"] / max(3, total_keywords) * 2)

        return {
            "project": best_match["project"],
            "confidence": confidence,
            "reasoning": f"匹配关键词：{', '.join(best_match['matched_keywords'])}",
            "detected_capabilities": [
                cap for cap in best_match["capabilities"]
                if any(kw in input_lower for kw in SUB_PROJECTS[best_match["project"]]["keywords"])
            ],
            "alternative_projects": [
                {"project": m["project"], "confidence": min(1.0, m["score"] / best_match["score"] * confidence * 0.8)}
                for m in matches[1:4]  # 最多 3 个备选
            ],
            "all_matches": matches,
        }


# 全局意图识别器实例
_recognizer = IntentRecognizer()


async def identify_intent(user_input: str) -> Dict[str, Any]:
    """
    识别用户意图属于哪个子项目

    Args:
        user_input: 用户自然语言输入

    Returns:
        意图识别结果，包含：
        - project: 匹配的子项目名称
        - confidence: 置信度分数
        - reasoning: 匹配理由
        - detected_capabilities: 检测到的能力需求
        - alternative_projects: 备选项目列表
    """
    logger.info(f"Identifying intent: {user_input[:100]}...")

    result = _recognizer.recognize(user_input)

    logger.info(f"Intent identified: {result.get('project')} (confidence: {result.get('confidence', 0):.2f})")

    return result


# 注册工具
from .registry import register_tool

register_tool(
    name="identify_intent",
    description="识别用户意图属于哪个子项目领域",
    input_schema={
        "type": "object",
        "properties": {
            "user_input": {
                "type": "string",
                "description": "用户自然语言输入",
            },
        },
        "required": ["user_input"],
    },
    handler=identify_intent,
)
