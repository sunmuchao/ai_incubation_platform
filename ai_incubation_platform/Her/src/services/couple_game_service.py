"""
P10-004: 双人互动游戏服务

提供多种双人互动游戏，帮助用户在轻松的氛围中加深了解。
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import uuid
import random
from sqlalchemy.orm import Session
from utils.db_session_manager import db_session, db_session_readonly
from db.database import SessionLocal
from db.models import UserDB, MatchHistoryDB
from models.p10_models import (
    CoupleGameDB,
    CoupleGameRoundDB,
    GameResultInsightDB
)
from utils.logger import logger


# 游戏类型定义
GAME_TYPES = {
    "qna_mutual": {
        "label": "互相问答",
        "description": "轮流提问回答问题，了解彼此的内心世界",
        "min_rounds": 5,
        "default_rounds": 10,
        "question_pool": "mutual"
    },
    "values_quiz": {
        "label": "价值观测试",
        "description": "通过极端场景测试，了解双方的价值观是否契合",
        "min_rounds": 5,
        "default_rounds": 8,
        "question_pool": "values"
    },
    "preference_match": {
        "label": "偏好匹配",
        "description": "猜测对方的喜好，测试你们的默契程度",
        "min_rounds": 5,
        "default_rounds": 10,
        "question_pool": "preference"
    },
    "personality_quiz": {
        "label": "性格测试",
        "description": "通过情景选择题，了解双方的性格特点",
        "min_rounds": 8,
        "default_rounds": 12,
        "question_pool": "personality"
    },
    "trivia_couple": {
        "label": "情侣知识问答",
        "description": "测试你们对彼此的了解程度",
        "min_rounds": 5,
        "default_rounds": 10,
        "question_pool": "trivia"
    },
    "future_planning": {
        "label": "未来规划游戏",
        "description": "探讨对未来的期待和规划",
        "min_rounds": 5,
        "default_rounds": 8,
        "question_pool": "future"
    },
    "memory_lane": {
        "label": "回忆之旅",
        "description": "回顾你们相识以来的美好时刻",
        "min_rounds": 3,
        "default_rounds": 5,
        "question_pool": "memory"
    }
}


# 问题库
QUESTION_POOLS = {
    "mutual": [
        "你理想中的周末是怎样的？",
        "最近有什么让你特别开心的事情？",
        "如果用三个词形容自己，你会选哪三个？",
        "你有什么特别坚持的习惯或原则吗？",
        "你最喜欢的一部电影/书籍是什么？为什么？",
        "你有什么童年时期最难忘的回忆？",
        "你认为什么是真正的友谊？",
        "你最想和另一半一起完成的一件事是什么？",
        "你有什么不为人知的小爱好？",
        "你对'家'的定义是什么？",
        "你最感激的人是谁？为什么？",
        "你有什么一直想尝试但还没做过的事情？"
    ],
    "values": [
        "如果事业和爱情只能选一个，你会怎么选？",
        "你愿意为了伴侣搬到另一个城市生活吗？",
        "你认为金钱在感情中的重要性如何？",
        "你能接受异地恋吗？最长能接受多久？",
        "你认为婚姻中最重要的因素是什么？",
        "你希望婚后与父母同住吗？",
        "你对生育的看法是什么？",
        "你认为家务应该如何分配？",
        "你能接受伴侣有自己的异性好友吗？",
        "你认为信任在关系中有多重要？"
    ],
    "preference": [
        "我更喜欢哪种类型的电影？",
        "我最喜欢的季节是什么？",
        "我平时最喜欢做什么运动？",
        "我最不能接受的食物是什么？",
        "我更喜欢宅在家还是出门玩？",
        "我更喜欢早上还是晚上工作/学习？",
        "我更注重仪式感还是随性？",
        "我更喜欢计划好的行程还是说走就走？",
        "我更喜欢热闹的聚会还是安静的二人世界？",
        "我更喜欢收到礼物还是体验？"
    ],
    "personality": [
        "在聚会上，你通常是：A) 主动和陌生人聊天 B) 和熟人待在一起 C) 躲在角落玩手机",
        "遇到困难时，你更倾向于：A) 立即解决 B) 先冷静分析 C) 寻求他人帮助",
        "你做决定时更多依靠：A) 直觉 B) 逻辑分析 C) 他人建议",
        "你更喜歡：A) 按计划行事 B) 随性而为",
        "你觉得自己是：A) 早起鸟 B) 夜猫子 C) 看情况",
        "面对冲突，你会：A) 直接沟通 B) 冷静处理 C) 暂时回避",
        "你更喜欢：A) 听别人说 B) 自己说 C) 平衡交流",
        "你做事情的风格是：A) 追求完美 B) 完成就好 C) 看心情"
    ],
    "trivia": [
        "我的生日是哪一天？",
        "我最喜欢的颜色是什么？",
        "我有什么特别的爱好或技能？",
        "我最讨厌做什么事情？",
        "我最想去的地方是哪里？",
        "我最喜欢的食物是什么？",
        "我有什么害怕的东西吗？",
        "我最好的朋友是谁？",
        "我最近在看什么书/剧？",
        "我的口头禅是什么？"
    ],
    "future": [
        "你理想中的 5 年后的生活是怎样的？",
        "你对婚姻有什么期待？",
        "你希望未来的家是什么样子的？",
        "你有什么职业上的目标和规划？",
        "你希望能和伴侣一起培养什么共同爱好？",
        "你对财务规划有什么看法？",
        "你希望在关系中保持多少个人空间？",
        "你认为理想的沟通频率是怎样的？"
    ],
    "memory": [
        "还记得我们第一次聊天时聊了什么吗？",
        "你对我第一印象是什么？",
        "我们之间最让你印象深刻的瞬间是什么？",
        "你最想重温我们之间的哪个时刻？",
        "你觉得我们之间的关系是怎么发展的？"
    ]
}


class CoupleGameService:
    """双人互动游戏服务"""

    def __init__(self):
        pass

    def create_couple_game(
        self,
        user_id_1: str,
        user_id_2: str,
        game_type: str,
        game_config: Optional[Dict[str, Any]] = None,
        difficulty: str = "normal",
        db_session: Optional[Any] = None
    ) -> str:
        """
        创建双人互动游戏

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            game_type: 游戏类型
            game_config: 游戏配置
            difficulty: 难度等级
            db_session: 可选的数据库会话（用于测试）

        Returns:
            游戏 ID
        """
        if game_type not in GAME_TYPES:
            raise ValueError(f"Invalid game type: {game_type}")

        db = db_session if db_session else SessionLocal()
        should_close = db_session is None
        try:
            # 验证匹配关系
            match_record = db.query(MatchHistoryDB).filter(
                ((MatchHistoryDB.user_id_1 == user_id_1) & (MatchHistoryDB.user_id_2 == user_id_2)) |
                ((MatchHistoryDB.user_id_1 == user_id_2) & (MatchHistoryDB.user_id_2 == user_id_1))
            ).first()

            if not match_record:
                raise ValueError("Users are not matched")

            game_info = GAME_TYPES[game_type]
            total_rounds = game_config.get("total_rounds", game_info["default_rounds"]) if game_config else game_info["default_rounds"]
            total_rounds = max(game_info["min_rounds"], total_rounds)

            # 创建游戏
            game_id = str(uuid.uuid4())
            game = CoupleGameDB(
                id=game_id,
                user_id_1=user_id_1,
                user_id_2=user_id_2,
                game_type=game_type,
                status="pending",
                current_round=0,
                total_rounds=total_rounds,
                game_config=game_config or {},
                difficulty=difficulty
            )
            db.add(game)

            # 预先生成游戏问题
            self._generate_game_rounds(db, game_id, game_type, total_rounds, user_id_1, user_id_2)

            db.commit()
            db.refresh(game)

            logger.info(f"Created couple game: {game_id}, type={game_type}")
            return game_id

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating couple game: {e}")
            raise
        finally:
            if should_close:
                db.close()

    def _generate_game_rounds(
        self,
        db,
        game_id: str,
        game_type: str,
        total_rounds: int,
        user_id_1: str,
        user_id_2: str
    ):
        """预先生成游戏轮次"""
        game_info = GAME_TYPES.get(game_type, {})
        question_pool_name = game_info.get("question_pool", "mutual")
        question_pool = QUESTION_POOLS.get(question_pool_name, QUESTION_POOLS["mutual"])

        # 随机选择问题
        selected_questions = random.sample(question_pool, min(total_rounds, len(question_pool)))

        for i, question in enumerate(selected_questions):
            round_db = CoupleGameRoundDB(
                id=str(uuid.uuid4()),
                game_id=game_id,
                round_number=i + 1,
                question=question,
                question_type=question_pool_name
            )
            db.add(round_db)

    def get_game_details(self, game_id: str, db_session: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """获取游戏详情"""
        db = db_session if db_session else SessionLocal()
        should_close = db_session is None
        try:
            game = db.query(CoupleGameDB).filter(CoupleGameDB.id == game_id).first()
            if not game:
                return None

            # 获取轮次
            rounds = db.query(CoupleGameRoundDB).filter(
                CoupleGameRoundDB.game_id == game_id
            ).order_by(CoupleGameRoundDB.round_number).all()

            rounds_data = []
            for r in rounds:
                rounds_data.append({
                    "round_number": r.round_number,
                    "question": r.question,
                    "question_type": r.question_type,
                    "answer_user1": r.answer_user1,
                    "answer_user2": r.answer_user2,
                    "is_match": r.is_match,
                    "match_percentage": r.match_percentage,
                    "insight": r.insight
                })

            game_info = GAME_TYPES.get(game.game_type, {})

            return {
                "id": game.id,
                "user_id_1": game.user_id_1,
                "user_id_2": game.user_id_2,
                "game_type": game.game_type,
                "game_type_label": game_info.get("label", game.game_type),
                "game_description": game_info.get("description", ""),
                "status": game.status,
                "current_round": game.current_round,
                "total_rounds": game.total_rounds,
                "difficulty": game.difficulty,
                "result_user1": game.result_user1,
                "result_user2": game.result_user2,
                "compatibility_insight": game.compatibility_insight,
                "created_at": game.created_at.isoformat() if game.created_at else None,
                "started_at": game.started_at.isoformat() if game.started_at else None,
                "completed_at": game.completed_at.isoformat() if game.completed_at else None,
                "rounds": rounds_data
            }

        finally:
            if should_close:
                db.close()

    def start_game(self, game_id: str, user_id: str, db_session: Optional[Any] = None) -> bool:
        """开始游戏"""
        db = db_session if db_session else SessionLocal()
        should_close = db_session is None
        try:
            game = db.query(CoupleGameDB).filter(CoupleGameDB.id == game_id).first()
            if not game:
                return False

            # 验证用户
            if user_id not in [game.user_id_1, game.user_id_2]:
                return False

            # 只有当游戏状态为 pending 时才能开始
            if game.status != "pending":
                return False

            game.status = "in_progress"
            game.started_at = datetime.now()
            db.commit()

            logger.info(f"Started couple game: {game_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error starting game: {e}")
            return False
        finally:
            if should_close:
                db.close()

    def submit_game_round(
        self,
        game_id: str,
        round_number: int,
        answer: str,
        user_id: str,
        db_session: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        提交游戏轮次回答

        Returns:
            轮次结果（包含匹配情况）
        """
        db = db_session if db_session else SessionLocal()
        should_close = db_session is None
        try:
            game = db.query(CoupleGameDB).filter(CoupleGameDB.id == game_id).first()
            if not game:
                return None

            # 验证用户
            if user_id not in [game.user_id_1, game.user_id_2]:
                return None

            # 验证游戏状态
            if game.status != "in_progress":
                return None

            # 获取轮次
            round_db = db.query(CoupleGameRoundDB).filter(
                CoupleGameRoundDB.game_id == game_id,
                CoupleGameRoundDB.round_number == round_number
            ).first()

            if not round_db:
                return None

            # 根据用户设置答案
            if user_id == game.user_id_1:
                if round_db.answer_user1 is not None:
                    return None  # 已经回答过
                round_db.answer_user1 = answer
            else:
                if round_db.answer_user2 is not None:
                    return None  # 已经回答过
                round_db.answer_user2 = answer

            # 检查是否需要计算匹配度
            result = self._calculate_round_result(db, game, round_db)

            # 检查是否完成游戏
            if game.current_round >= game.total_rounds:
                self._complete_game(db, game)

            db.commit()

            return result

        except Exception as e:
            db.rollback()
            logger.error(f"Error submitting game round: {e}")
            return None
        finally:
            if should_close:
                db.close()

    def _calculate_round_result(
        self,
        db,
        game: CoupleGameDB,
        round_db: CoupleGameRoundDB
    ) -> Dict[str, Any]:
        """计算轮次结果"""
        result = {
            "round_number": round_db.round_number,
            "question": round_db.question,
            "answer_user1": round_db.answer_user1,
            "answer_user2": round_db.answer_user2,
            "is_match": False,
            "match_percentage": 0,
            "insight": None
        }

        # 根据游戏类型计算匹配度
        if game.game_type == "preference_match":
            # 偏好匹配：检查答案是否一致
            if round_db.answer_user1 and round_db.answer_user2:
                # 简单文本匹配（实际应该用 AI 语义匹配）
                is_match = round_db.answer_user1.strip() == round_db.answer_user2.strip()
                result["is_match"] = is_match
                result["match_percentage"] = 1.0 if is_match else 0.3  # 不完全匹配也给一些分数

        elif game.game_type == "trivia_couple":
            # 情侣问答：由提问者判断答案是否正确
            # 这里简化处理，假设回答正确
            result["is_match"] = True
            result["match_percentage"] = 1.0

        else:
            # 其他类型：AI 分析答案的契合度
            if round_db.answer_user1 and round_db.answer_user2:
                # 使用 AI 分析答案的价值观契合度
                analysis = self._analyze_answer_compatibility(
                    round_db.answer_user1,
                    round_db.answer_user2,
                    game.game_type
                )
                result["match_percentage"] = analysis["score"]
                result["insight"] = analysis["insight"]
                result["is_match"] = analysis["score"] >= 0.7

        # 更新数据库
        round_db.is_match = result["is_match"]
        round_db.match_percentage = result["match_percentage"]
        round_db.insight = result["insight"]

        # 更新游戏当前轮次
        game.current_round = max(game.current_round, round_db.round_number)

        return result

    def _analyze_answer_compatibility(
        self,
        answer1: str,
        answer2: str,
        game_type: str
    ) -> Dict[str, Any]:
        """AI 分析答案兼容性"""
        # 简化版本：基于关键词匹配
        # 实际应该调用 LLM 进行语义分析

        # 提取关键词
        words1 = set(answer1.lower())
        words2 = set(answer2.lower())

        # 计算 Jaccard 相似度
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        similarity = intersection / union if union > 0 else 0

        # 长度因子：答案长度相近可能表示沟通风格相似
        len_diff = abs(len(answer1) - len(answer2))
        length_factor = max(0, 1 - len_diff / 100)

        # 综合得分
        score = similarity * 0.6 + length_factor * 0.4

        # 生成简单洞察
        if score >= 0.8:
            insight = "你们的答案高度契合，显示出相似的思维方式和价值观"
        elif score >= 0.6:
            insight = "你们的答案有一定共性，但也存在一些差异，这是正常且健康的"
        elif score >= 0.4:
            insight = "你们的答案有所不同，可能需要更多沟通来理解彼此的想法"
        else:
            insight = "你们的答案差异较大，建议深入交流了解背后的原因"

        return {
            "score": round(score, 2),
            "insight": insight
        }

    def _complete_game(self, db, game: CoupleGameDB):
        """完成游戏并生成结果"""
        game.status = "completed"
        game.completed_at = datetime.now()

        # 获取所有轮次
        rounds = db.query(CoupleGameRoundDB).filter(
            CoupleGameRoundDB.game_id == game.id
        ).all()

        # 计算结果
        user1_score = 0
        user2_score = 0
        total_match = 0

        for r in rounds:
            if r.is_match:
                user1_score += 1
                user2_score += 1
            if r.match_percentage:
                total_match += r.match_percentage

        avg_match = total_match / len(rounds) if rounds else 0

        game.result_user1 = user1_score
        game.result_user2 = user2_score

        # 生成兼容性洞察
        compatibility_insight = self._generate_compatibility_insight(
            game.game_type,
            avg_match,
            rounds
        )
        game.compatibility_insight = compatibility_insight

        # 创建游戏结果洞察记录
        self._create_game_result_insight(
            db,
            game.id,
            game.user_id_1,
            game.user_id_2,
            game.game_type,
            avg_match,
            rounds
        )

    def _generate_compatibility_insight(
        self,
        game_type: str,
        avg_match: float,
        rounds: List[CoupleGameRoundDB]
    ) -> str:
        """生成兼容性洞察"""
        if avg_match >= 0.8:
            return f"恭喜！你们在{GAME_TYPES.get(game_type, {}).get('label', '游戏')}中展现了极高的默契度，这是一段美好关系的开始！"
        elif avg_match >= 0.6:
            return "你们之间有不错的默契，虽然有些地方还需要更多了解，但这正是探索彼此的乐趣所在。"
        elif avg_match >= 0.4:
            return "你们在某些方面有差异，这很正常。重要的是保持开放的沟通，理解彼此的独特之处。"
        else:
            return "你们的答案显示出较大的差异。差异不一定是坏事，关键是要学会欣赏和尊重彼此的不同。"

    def _create_game_result_insight(
        self,
        db,
        game_id: str,
        user_id_1: str,
        user_id_2: str,
        game_type: str,
        avg_match: float,
        rounds: List[CoupleGameRoundDB]
    ):
        """创建游戏结果洞察记录"""
        insight_id = str(uuid.uuid4())

        # 分析兼容性领域
        compatibility_areas = self._analyze_compatibility_areas(game_type, rounds)

        insight = GameResultInsightDB(
            id=insight_id,
            game_id=game_id,
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            insight_type="game_result",
            title=f"{GAME_TYPES.get(game_type, {}).get('label', '游戏')}结果分析",
            content=f"你们的整体默契度为{round(avg_match * 100)}%",
            compatibility_areas=json.dumps(compatibility_areas["compatibility"]),
            strength_areas=json.dumps(compatibility_areas["strengths"]),
            growth_areas=json.dumps(compatibility_areas["growth"]),
            suggestions=json.dumps(self._generate_suggestions(game_type, avg_match, rounds))
        )
        db.add(insight)

    def _analyze_compatibility_areas(
        self,
        game_type: str,
        rounds: List[CoupleGameRoundDB]
    ) -> Dict[str, List[str]]:
        """分析兼容性领域"""
        compatibility = []
        strengths = []
        growth = []

        # 统计高匹配和低匹配的轮次
        high_match_rounds = [r for r in rounds if r.match_percentage and r.match_percentage >= 0.7]
        low_match_rounds = [r for r in rounds if r.match_percentage and r.match_percentage < 0.5]

        if len(high_match_rounds) >= 3:
            strengths.append("在多个话题上展现出高度默契")
            compatibility.append("价值观契合")

        if len(low_match_rounds) > len(rounds) * 0.3:
            growth.append("需要更多沟通来理解彼此的想法")

        if not strengths:
            strengths.append("愿意一起参与互动游戏，这是良好的开始")

        if not growth:
            growth.append("继续保持开放的沟通")

        return {
            "compatibility": compatibility,
            "strengths": strengths,
            "growth": growth
        }

    def _generate_suggestions(
        self,
        game_type: str,
        avg_match: float,
        rounds: List[CoupleGameRoundDB]
    ) -> List[str]:
        """生成建议"""
        suggestions = []

        if avg_match >= 0.8:
            suggestions.append("尝试更深入的话题，进一步了解彼此")
            suggestions.append("可以规划一次特别的约会来庆祝你们的默契")
        elif avg_match >= 0.6:
            suggestions.append("继续保持良好的沟通习惯")
            suggestions.append("尝试分享更多个人故事和经历")
        else:
            suggestions.append("不要担心差异，试着理解彼此想法背后的原因")
            suggestions.append("可以多玩几种不同类型的游戏，全面了解彼此")

        return suggestions

    def get_user_games(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 10,
        db_session: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """获取用户参与的游戏列表"""
        db = db_session if db_session else SessionLocal()
        should_close = db_session is None
        try:
            query = db.query(CoupleGameDB).filter(
                (CoupleGameDB.user_id_1 == user_id) |
                (CoupleGameDB.user_id_2 == user_id)
            )

            if status:
                query = query.filter(CoupleGameDB.status == status)

            games = query.order_by(
                CoupleGameDB.created_at.desc()
            ).limit(limit).all()

            result = []
            for g in games:
                game_info = GAME_TYPES.get(g.game_type, {})
                result.append({
                    "id": g.id,
                    "game_type": g.game_type,
                    "game_type_label": game_info.get("label", g.game_type),
                    "status": g.status,
                    "current_round": g.current_round,
                    "total_rounds": g.total_rounds,
                    "result_user1": g.result_user1,
                    "result_user2": g.result_user2,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                    "completed_at": g.completed_at.isoformat() if g.completed_at else None
                })
            return result

        finally:
            if should_close:
                db.close()

    def get_game_insights(self, game_id: str) -> Optional[Dict[str, Any]]:
        """获取游戏结果洞察"""
        with db_session_readonly() as db:
            insight = db.query(GameResultInsightDB).filter(
                GameResultInsightDB.game_id == game_id
            ).first()

            if not insight:
                return None

            return {
                "id": insight.id,
                "game_id": insight.game_id,
                "insight_type": insight.insight_type,
                "title": insight.title,
                "content": insight.content,
                "compatibility_areas": json.loads(insight.compatibility_areas) if insight.compatibility_areas else [],
                "strength_areas": json.loads(insight.strength_areas) if insight.strength_areas else [],
                "growth_areas": json.loads(insight.growth_areas) if insight.growth_areas else [],
                "suggestions": json.loads(insight.suggestions) if insight.suggestions else [],
                "created_at": insight.created_at.isoformat() if insight.created_at else None
            }

    def complete_game(self, game_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """完成游戏并返回洞察"""
        with db_session() as db:
            game = db.query(CoupleGameDB).filter(CoupleGameDB.id == game_id).first()
            if not game:
                return None

            # 验证用户
            if user_id not in [game.user_id_1, game.user_id_2]:
                return None

            # 如果游戏未完成，强制完成
            if game.status != "completed":
                game.current_round = game.total_rounds
                self._complete_game(db, game)
                # auto-commits

            # 返回游戏详情和洞察
            # 注意：get_game_details 和 get_game_insights 会创建自己的会话
            game_details = self.get_game_details(game_id, db_session_param=db)
            insights = self.get_game_insights(game_id)

            return {
                "game": game_details,
                "insights": insights
            }


# 全局服务实例
couple_game_service = CoupleGameService()
