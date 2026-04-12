"""
关系压力测试服务

模拟不同场景测试关系韧性：
- 价值观冲突场景
- 生活习惯差异场景
- 经济观念差异场景
- 家庭关系场景
- 沟通方式差异场景

帮助用户了解关系的潜在问题和解决方向
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from utils.logger import logger
from services.base_service import BaseService


class RelationshipStressTestService(BaseService):
    """关系压力测试服务"""

    # 测试场景类型
    SCENARIO_TYPES = [
        {
            "type": "value_conflict",
            "name": "价值观冲突",
            "description": "模拟价值观差异引发的情况",
            "scenarios": [
                "一方重视事业，一方重视家庭",
                "消费观念差异（节俭 vs 品质）",
                "社交观念差异（内向 vs 外向）"
            ]
        },
        {
            "type": "lifestyle_difference",
            "name": "生活习惯差异",
            "description": "模拟生活习惯不同引发的情况",
            "scenarios": [
                "作息时间差异（早睡 vs 睡晚）",
                "家务分工观念差异",
                "个人空间需求差异"
            ]
        },
        {
            "type": "economic_disagreement",
            "name": "经济观念差异",
            "description": "模拟金钱观念不同引发的情况",
            "scenarios": [
                "收入分配分歧",
                "消费优先级差异",
                "储蓄观念差异"
            ]
        },
        {
            "type": "family_relation",
            "name": "家庭关系",
            "description": "模拟家庭因素引发的情况",
            "scenarios": [
                "父母期望冲突",
                "家庭责任分担",
                "节假日安排分歧"
            ]
        },
        {
            "type": "communication_style",
            "name": "沟通方式差异",
            "description": "模拟沟通方式不同引发的情况",
            "scenarios": [
                "表达方式差异（直接 vs 含蓄）",
                "情绪处理方式差异",
                "决策方式差异（独立 vs 协商）"
            ]
        }
    ]

    def __init__(self, db: Session):
        super().__init__(db)
        self.db = db

    async def create_stress_test(
        self,
        user_id: str,
        partner_id: str,
        scenario_type: str,
        relationship_stage: str = "dating"  # dating/committed/married
    ) -> Dict[str, Any]:
        """
        创建压力测试

        生成测试场景和问题

        Args:
            user_id: 用户 ID
            partner_id: 对方 ID
            scenario_type: 场景类型
            relationship_stage: 关系阶段

        Returns:
            测试详情
        """
        from models.relationship_stress_test import StressTestDB
        from services.llm_service import get_llm_service

        # 获取用户资料
        from db.models import UserDB
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        partner = self.db.query(UserDB).filter(UserDB.id == partner_id).first()

        if not user or not partner:
            return {"success": False, "message": "用户不存在"}

        test_id = str(uuid.uuid4())

        # 选择具体场景
        scenario_config = self._get_scenario_config(scenario_type)
        if not scenario_config:
            return {"success": False, "message": "场景类型无效"}

        # AI 生成测试问题
        llm_service = get_llm_service()

        prompt = f"""请为以下关系生成压力测试问题：

用户 A：
- 年龄：{user.age}
- 性别：{user.gender}
- 简介：{user.bio}
- 兴趣：{user.interests}

用户 B：
- 年龄：{partner.age}
- 性别：{partner.gender}
- 简介：{partner.bio}
- 兴趣：{partner.interests}

关系阶段：{relationship_stage}
测试场景类型：{scenario_config['name']}
可能情况：{scenario_config['scenarios']}

请生成 5 个测试问题，每个问题：
1. 描述一个具体的场景
2. 给出 3-4 个选择选项（代表不同的处理方式）
3. 说明每个选项的潜在后果
4. 标记问题的难度（1-5）

回复格式：
[
  {
    "question_id": "q1",
    "scenario_description": "场景描述",
    "options": [
      {"id": "a", "content": "选项内容", "consequence": "潜在后果"},
      {"id": "b", "content": "选项内容", "consequence": "潜在后果"},
      ...
    ],
    "difficulty": 3,
    "key_insight": "这个问题的关键洞察"
  },
  ...
]"""

        try:
            result = await llm_service.generate(prompt)
            import json
            questions = json.loads(result)

            # 创建测试记录
            test_record = StressTestDB(
                id=test_id,
                user_id=user_id,
                partner_id=partner_id,
                scenario_type=scenario_type,
                relationship_stage=relationship_stage,
                questions=questions,
                status="pending",
                created_at=datetime.now()
            )
            self.db.add(test_record)
            self.db.commit()

            logger.info(f"Stress test created: {test_id}")

            return {
                "success": True,
                "test_id": test_id,
                "scenario_type": scenario_type,
                "scenario_name": scenario_config['name'],
                "questions": questions,
                "total_questions": len(questions)
            }
        except Exception as e:
            logger.error(f"Failed to create stress test: {e}")
            return {"success": False, "message": str(e)}

    def _get_scenario_config(self, scenario_type: str) -> Optional[Dict]:
        """获取场景配置"""
        for scenario in self.SCENARIO_TYPES:
            if scenario["type"] == scenario_type:
                return scenario
        return None

    async def submit_test_answer(
        self,
        test_id: str,
        question_id: str,
        selected_option: str,
        open_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        提交测试答案

        Args:
            test_id: 测试 ID
            question_id: 问题 ID
            selected_option: 选择选项
            open_response: 开放式回答（可选）

        Returns:
            分析结果
        """
        from models.relationship_stress_test import StressTestAnswerDB, StressTestDB
        from services.llm_service import get_llm_service

        # 获取测试
        test = self.db.query(StressTestDB).filter(StressTestDB.id == test_id).first()
        if not test:
            return {"success": False, "message": "测试不存在"}

        # 获取问题详情
        questions = test.questions
        question = None
        for q in questions:
            if q.get("question_id") == question_id:
                question = q
                break

        if not question:
            return {"success": False, "message": "问题不存在"}

        # AI 分析答案
        llm_service = get_llm_service()

        prompt = f"""请分析这个压力测试答案：

场景描述：{question.get('scenario_description')}
问题难度：{question.get('difficulty')}
选择选项：{selected_option}
选项详情：{question.get('options', [])}
开放式回答：{open_response or '无'}

请分析：
1. 这个选择代表的关系态度
2. 可能的沟通建议
3. 潜在的风险点
4. 关系韧性评分（0-100）
5. 改进建议

回复格式：
{
  "attitude_analysis": "态度分析",
  "communication_advice": "沟通建议",
  "risk_points": ["风险点列表"],
  "resilience_score": 75,
  "improvement_suggestions": ["改进建议"],
  "key_takeaway": "关键启示"
}"""

        try:
            result = await llm_service.generate(prompt)
            import json
            analysis = json.loads(result)

            # 保存答案
            answer_id = str(uuid.uuid4())
            answer_record = StressTestAnswerDB(
                id=answer_id,
                test_id=test_id,
                question_id=question_id,
                selected_option=selected_option,
                open_response=open_response,
                analysis_result=analysis,
                created_at=datetime.now()
            )
            self.db.add(answer_record)
            self.db.commit()

            return {
                "success": True,
                "answer_id": answer_id,
                "analysis": analysis
            }
        except Exception as e:
            logger.error(f"Failed to analyze answer: {e}")
            return {"success": False, "message": str(e)}

    async def get_test_summary(self, test_id: str) -> Dict[str, Any]:
        """
        获取测试总结

        分析所有答案，给出关系韧性评估

        Args:
            test_id: 测试 ID

        Returns:
            总结报告
        """
        from models.relationship_stress_test import StressTestDB, StressTestAnswerDB

        test = self.db.query(StressTestDB).filter(StressTestDB.id == test_id).first()
        if not test:
            return {"success": False, "message": "测试不存在"}

        # 获取所有答案
        answers = self.db.query(StressTestAnswerDB).filter(
            StressTestAnswerDB.test_id == test_id
        ).all()

        # 计算总分
        total_score = 0
        for answer in answers:
            analysis = answer.analysis_result
            if analysis:
                total_score += analysis.get("resilience_score", 0)

        average_score = total_score / len(answers) if answers else 0

        # 生成总结报告
        summary = {
            "test_id": test_id,
            "scenario_type": test.scenario_type,
            "total_questions": len(test.questions),
            "answered_questions": len(answers),
            "average_resilience_score": average_score,
            "overall_risk_level": self._get_risk_level(average_score),
            "key_findings": [],
            "recommendations": []
        }

        # 收集关键发现
        for answer in answers:
            analysis = answer.analysis_result
            if analysis:
                summary["key_findings"].extend(analysis.get("risk_points", []))
                summary["recommendations"].extend(analysis.get("improvement_suggestions", []))

        return summary

    def _get_risk_level(self, score: float) -> str:
        """根据分数判断风险等级"""
        if score >= 80:
            return "低风险 - 关系韧性良好"
        elif score >= 60:
            return "中等风险 - 需要关注沟通"
        elif score >= 40:
            return "较高风险 - 建议深入讨论"
        else:
            return "高风险 - 需要认真对待"

    def get_available_scenarios(self) -> List[Dict[str, Any]]:
        """获取可用的测试场景"""
        return self.SCENARIO_TYPES


# 服务工厂函数
def get_relationship_stress_test_service(db: Session) -> RelationshipStressTestService:
    """获取关系压力测试服务实例"""
    return RelationshipStressTestService(db)