"""
规则引擎（常规模式）

继承 MatchEngine 基类，封装现有的 matcher.py 匹配算法。
定位：主力产品，免费，服务大多数用户。

核心特点：
- 匹配精准：176维向量 + 心理学规则
- 双向奔赴：计算双向选择概率，不只推单向
- 市场平衡：考虑市场竞争力，避免无效匹配
- 快速响应：<100ms，无等待
- 免费使用：核心功能免费
"""

import time
from typing import Optional, List, Dict, Any
from datetime import datetime

from matching.engine_base import (
    MatchEngine,
    MatchRequest,
    MatchResult,
    MatchCandidate,
    EngineMetrics,
    EngineType,
)
from matching.matcher import MatchmakerAlgorithm, get_matchmaker
from utils.logger import logger


class RuleMatchEngine(MatchEngine):
    """
    规则匹配引擎（常规模式）

    封装现有 MatchmakerAlgorithm，提供标准化接口。
    """

    engine_type = EngineType.RULE

    def __init__(self):
        """初始化规则引擎"""
        self._matchmaker = get_matchmaker()
        self.metrics = EngineMetrics(engine_type=EngineType.RULE)
        logger.info("RuleMatchEngine initialized")

    async def match(self, request: MatchRequest) -> MatchResult:
        """
        执行规则匹配

        Args:
            request: 匹配请求

        Returns:
            MatchResult: 匹配结果
        """
        start_time = time.time()

        # 验证请求
        validation_error = self.validate_request(request)
        if validation_error:
            return MatchResult(
                success=False,
                error=validation_error,
                error_code="INVALID_REQUEST",
                engine_type=EngineType.RULE,
            )

        # 预处理
        request = self.pre_process(request)

        try:
            # 调用底层匹配算法
            matches = self._matchmaker.find_matches(
                user_id=request.user_id,
                limit=request.limit
            )

            # 转换为标准候选格式
            candidates = []
            for match in matches:
                candidate = self._convert_match_to_candidate(
                    match,
                    request.user_id
                )
                candidates.append(candidate)

            # 构建结果
            latency_ms = (time.time() - start_time) * 1000
            result = MatchResult(
                success=True,
                candidates=candidates,
                total_count=len(candidates),
                engine_type=EngineType.RULE,
                latency_ms=latency_ms,
                timestamp=datetime.now(),
            )

            # 后处理
            result = self.post_process(result)

            # 记录指标
            self.metrics.record_request(
                success=True,
                latency_ms=latency_ms,
                candidates_count=len(candidates)
            )

            logger.debug(
                f"RuleMatchEngine: matched {len(candidates)} candidates "
                f"for user {request.user_id} in {latency_ms:.2f}ms"
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"RuleMatchEngine error: {e}")

            self.metrics.record_request(success=False, latency_ms=latency_ms)

            return MatchResult(
                success=False,
                error=str(e),
                error_code="ENGINE_ERROR",
                engine_type=EngineType.RULE,
                latency_ms=latency_ms,
            )

    def _convert_match_to_candidate(
        self,
        match: Dict[str, Any],
        user_id: str
    ) -> MatchCandidate:
        """
        将底层匹配结果转换为标准候选格式

        Args:
            match: 底层匹配结果
            user_id: 请求用户ID

        Returns:
            MatchCandidate: 标准候选格式
        """
        # 从匹配器获取候选用户详细信息
        candidate_user = self._matchmaker._users.get(match['user_id'], {})

        # 构建候选对象
        candidate = MatchCandidate(
            user_id=match['user_id'],
            name=candidate_user.get('name', 'TA'),
            score=match['score'],
            breakdown=match['breakdown'],
            age=candidate_user.get('age'),
            location=candidate_user.get('location'),
            gender=candidate_user.get('gender'),
            interests=candidate_user.get('interests', []),
            bio=candidate_user.get('bio'),
        )

        # 生成推荐理由（AI驱动）
        if candidate_user:
            reasoning = self._matchmaker.generate_match_reasoning(
                user=self._matchmaker._users.get(user_id, {}),
                candidate=candidate_user,
                score=match['score'],
                breakdown=match['breakdown']
            )
            candidate.reasoning = reasoning

        return candidate

    def get_metrics(self) -> EngineMetrics:
        """获取引擎指标"""
        return self.metrics

    def reset_metrics(self) -> None:
        """重置指标"""
        self.metrics = EngineMetrics(engine_type=EngineType.RULE)
        logger.info("RuleMatchEngine metrics reset")

    def register_user(self, user: Dict[str, Any]) -> None:
        """
        注册用户到匹配池

        Args:
            user: 用户数据
        """
        self._matchmaker.register_user(user)
        logger.debug(f"RuleMatchEngine: registered user {user.get('id')}")

    def unregister_user(self, user_id: str) -> None:
        """
        从匹配池注销用户

        Args:
            user_id: 用户ID
        """
        self._matchmaker.unregister_user(user_id)
        logger.debug(f"RuleMatchEngine: unregistered user {user_id}")

    def get_registered_users(self) -> Dict[str, Dict]:
        """
        获取所有已注册用户

        Returns:
            用户字典
        """
        return self._matchmaker._users


# 全局引擎实例
_rule_engine_instance: Optional[RuleMatchEngine] = None


def get_rule_engine() -> RuleMatchEngine:
    """
    获取规则引擎实例

    Returns:
        RuleMatchEngine: 全局规则引擎实例
    """
    global _rule_engine_instance
    if _rule_engine_instance is None:
        _rule_engine_instance = RuleMatchEngine()
    return _rule_engine_instance