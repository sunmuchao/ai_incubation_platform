"""
P19 AI 助手增强 - 服务层
版本：v19.0.0
主题：AI 助手增强 (智能工作助手、日程管理、会议摘要、工作简报)
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from models.p19_assistant_models import (
    AssistantProfile, TaskRecommendation, WorkSuggestion, SmartSchedule,
    ScheduleConflict, Meeting, MeetingSummary, MeetingActionItem,
    WorkReport, ReportTemplate, ReportGeneration,
    TaskPriority, TaskStatus, RecommendationType, MeetingType,
    MeetingStatus, ReportType, ReportStatus, ScheduleConflictType,
    get_assistant_db
)


# ==================== 工作助手服务 ====================

class WorkAssistantService:
    """工作助手服务"""

    def __init__(self, db: Optional[Any] = None):
        self.db = db or get_assistant_db()

    def create_assistant(self, user_id: int, assistant_type: str,
                         name: str = "工作助手", description: str = None,
                         preferences: Dict[str, Any] = None) -> AssistantProfile:
        """创建 AI 助手"""
        assistant = AssistantProfile(
            user_id=user_id,
            assistant_type=assistant_type,
            name=name,
            description=description,
            preferences=preferences or {}
        )
        return self.db.create_assistant(assistant)

    def get_user_assistants(self, user_id: int) -> List[AssistantProfile]:
        """获取用户的助手列表"""
        return self.db.get_user_assistants(user_id)

    def create_task_recommendation(self, user_id: int, recommendation_type: str,
                                    title: str, task_id: int = None,
                                    employee_id: int = None,
                                    description: str = None,
                                    reason: str = None,
                                    confidence_score: float = 0.0,
                                    metadata: Dict[str, Any] = None) -> TaskRecommendation:
        """创建任务推荐"""
        recommendation = TaskRecommendation(
            user_id=user_id,
            recommendation_type=recommendation_type,
            task_id=task_id,
            employee_id=employee_id,
            title=title,
            description=description,
            reason=reason,
            confidence_score=confidence_score,
            metadata=metadata or {}
        )
        return self.db.create_recommendation(recommendation)

    def get_recommendations(self, user_id: int, limit: int = 50) -> List[TaskRecommendation]:
        """获取用户推荐"""
        return self.db.get_recommendations(user_id, limit)

    def accept_recommendation(self, recommendation_id: int) -> bool:
        """接受推荐"""
        return self.db.accept_recommendation(recommendation_id)

    def generate_task_priority_recommendations(self, user_id: int,
                                                tasks: List[Dict[str, Any]]) -> List[TaskRecommendation]:
        """生成任务优先级推荐"""
        recommendations = []

        # 按优先级和截止时间排序
        priority_order = {
            TaskPriority.CRITICAL.value: 0,
            TaskPriority.HIGH.value: 1,
            TaskPriority.MEDIUM.value: 2,
            TaskPriority.LOW.value: 3
        }

        sorted_tasks = sorted(tasks, key=lambda t: (
            priority_order.get(t.get('priority', 'medium'), 2),
            t.get('due_date', '9999-12-31')
        ))

        # 为高优先级任务生成推荐
        for i, task in enumerate(sorted_tasks[:10]):
            reason = f"该任务优先级为{task.get('priority', 'medium')}"
            if task.get('due_date'):
                due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                days_left = (due_date - datetime.now()).days
                if days_left <= 1:
                    reason = f"任务即将到期，剩余{days_left}天"

            recommendation = TaskRecommendation(
                user_id=user_id,
                recommendation_type=RecommendationType.TASK_PRIORITY.value,
                task_id=task.get('id'),
                title=f"优先处理：{task.get('title', '未命名任务')}",
                description=task.get('description'),
                reason=reason,
                confidence_score=0.9 - (i * 0.05),
                metadata={'task_data': task, 'sort_order': i}
            )
            recommendations.append(self.db.create_recommendation(recommendation))

        return recommendations

    def generate_ai_employee_recommendations(self, user_id: int,
                                              task_description: str,
                                              budget: float = None) -> List[TaskRecommendation]:
        """基于任务推荐 AI 员工"""
        # 这里简化实现，实际应该对接匹配服务
        recommendations = []

        # 模拟推荐逻辑
        recommendation = TaskRecommendation(
            user_id=user_id,
            recommendation_type=RecommendationType.AI_EMPLOYEE.value,
            title=f"推荐 AI 员工处理：{task_description[:50]}",
            description=f"基于任务描述'{task_description}'推荐合适的 AI 员工",
            reason="该 AI 员工在类似任务上表现优异",
            confidence_score=0.85,
            metadata={'task_description': task_description, 'budget': budget}
        )
        recommendations.append(self.db.create_recommendation(recommendation))

        return recommendations

    def create_work_suggestion(self, user_id: int, suggestion_type: str,
                                title: str, description: str = None,
                                expected_impact: str = None,
                                effort_level: str = "medium",
                                priority: str = "medium",
                                metadata: Dict[str, Any] = None) -> WorkSuggestion:
        """创建工作建议"""
        suggestion = WorkSuggestion(
            user_id=user_id,
            suggestion_type=suggestion_type,
            title=title,
            description=description,
            expected_impact=expected_impact,
            effort_level=effort_level,
            priority=priority,
            metadata=metadata or {}
        )
        # 需要使用 WorkSuggestion 的 CRUD 方法，这里简化处理
        return suggestion


# ==================== 智能日程服务 ====================

class SmartScheduleService:
    """智能日程服务"""

    def __init__(self, db: Optional[Any] = None):
        self.db = db or get_assistant_db()

    def create_schedule(self, user_id: int, title: str, start_time: str,
                        end_time: str, description: str = None,
                        location: str = None, attendees: List[int] = None,
                        is_recurring: bool = False,
                        recurrence_pattern: str = None,
                        recurrence_end: str = None,
                        priority: str = "medium",
                        timezone: str = "UTC") -> SmartSchedule:
        """创建日程"""
        schedule = SmartSchedule(
            user_id=user_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            attendees=attendees or [],
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern,
            recurrence_end=recurrence_end,
            priority=priority,
            timezone=timezone
        )
        return self.db.create_schedule(schedule)

    def get_schedule(self, schedule_id: int) -> Optional[SmartSchedule]:
        """获取日程"""
        return self.db.get_schedule(schedule_id)

    def get_user_schedules(self, user_id: int, start_date: str = None,
                           end_date: str = None) -> List[SmartSchedule]:
        """获取用户日程"""
        return self.db.get_user_schedules(user_id, start_date, end_date)

    def update_schedule(self, schedule: SmartSchedule) -> SmartSchedule:
        """更新日程"""
        return self.db.update_schedule(schedule)

    def delete_schedule(self, schedule_id: int) -> bool:
        """删除日程"""
        return self.db.delete_schedule(schedule_id)

    def detect_conflicts(self, user_id: int, schedule: SmartSchedule) -> List[ScheduleConflict]:
        """检测日程冲突"""
        conflicts = []
        user_schedules = self.db.get_user_schedules(user_id)

        for existing in user_schedules:
            if existing.id == schedule.id:
                continue

            # 检查时间重叠
            if self._is_time_overlap(schedule, existing):
                conflict = ScheduleConflict(
                    user_id=user_id,
                    conflict_type=ScheduleConflictType.TIME_OVERLAP.value,
                    schedule_id_1=schedule.id or 0,
                    schedule_id_2=existing.id or 0,
                    description=f"日程'{schedule.title}'与'{existing.title}'时间冲突",
                    severity=self._calculate_conflict_severity(schedule, existing)
                )
                conflicts.append(conflict)

        return conflicts

    def _is_time_overlap(self, s1: SmartSchedule, s2: SmartSchedule) -> bool:
        """检查两个日程是否时间重叠"""
        start1 = datetime.fromisoformat(s1.start_time.replace('Z', '+00:00'))
        end1 = datetime.fromisoformat(s1.end_time.replace('Z', '+00:00'))
        start2 = datetime.fromisoformat(s2.start_time.replace('Z', '+00:00'))
        end2 = datetime.fromisoformat(s2.end_time.replace('Z', '+00:00'))

        return start1 < end2 and start2 < end1

    def _calculate_conflict_severity(self, s1: SmartSchedule,
                                      s2: SmartSchedule) -> str:
        """计算冲突严重程度"""
        priority_order = {
            TaskPriority.CRITICAL.value: 3,
            TaskPriority.HIGH.value: 2,
            TaskPriority.MEDIUM.value: 1,
            TaskPriority.LOW.value: 0
        }

        p1 = priority_order.get(s1.priority, 1)
        p2 = priority_order.get(s2.priority, 1)

        if p1 >= 2 and p2 >= 2:
            return "high"
        elif p1 >= 1 or p2 >= 1:
            return "medium"
        return "low"

    def suggest_alternative_times(self, user_id: int, schedule: SmartSchedule,
                                   duration_minutes: int = 60) -> List[Dict[str, str]]:
        """建议替代时间"""
        alternatives = []
        user_schedules = self.db.get_user_schedules(user_id)

        # 获取原始日程的日期
        original_date = datetime.fromisoformat(schedule.start_time.replace('Z', '+00:00')).date()

        # 检查当天和前后两天的时间段
        for day_offset in range(-1, 3):
            check_date = original_date + timedelta(days=day_offset)

            # 检查工作时间的每个小时段 (9:00 - 18:00)
            for hour in range(9, 18):
                slot_start = datetime(check_date.year, check_date.month,
                                      check_date.day, hour, 0)
                slot_end = slot_start + timedelta(minutes=duration_minutes)

                # 检查该时段是否与现有日程冲突
                has_conflict = False
                for existing in user_schedules:
                    existing_start = datetime.fromisoformat(existing.start_time.replace('Z', '+00:00'))
                    existing_end = datetime.fromisoformat(existing.end_time.replace('Z', '+00:00'))

                    if slot_start < existing_end and slot_end > existing_start:
                        has_conflict = True
                        break

                if not has_conflict:
                    alternatives.append({
                        'start_time': slot_start.isoformat(),
                        'end_time': slot_end.isoformat(),
                        'confidence': 0.9 - (abs(day_offset) * 0.1)
                    })

                if len(alternatives) >= 5:
                    break

            if len(alternatives) >= 5:
                break

        return alternatives


# ==================== 会议摘要服务 ====================

class MeetingSummaryService:
    """会议摘要服务"""

    def __init__(self, db: Optional[Any] = None):
        self.db = db or get_assistant_db()

    def create_meeting(self, title: str, meeting_type: str, organizer_id: int,
                       start_time: str, end_time: str,
                       description: str = None, location: str = None,
                       attendees: List[int] = None,
                       agenda: str = None) -> Meeting:
        """创建会议"""
        meeting = Meeting(
            title=title,
            description=description,
            meeting_type=meeting_type,
            organizer_id=organizer_id,
            start_time=start_time,
            end_time=end_time,
            location=location,
            attendees=attendees or [],
            agenda=agenda
        )
        return self.db.create_meeting(meeting)

    def get_meeting(self, meeting_id: int) -> Optional[Meeting]:
        """获取会议"""
        return self.db.get_meeting(meeting_id)

    def get_user_meetings(self, user_id: int, status: str = None) -> List[Meeting]:
        """获取用户会议"""
        return self.db.get_user_meetings(user_id, status)

    def update_meeting(self, meeting: Meeting) -> Meeting:
        """更新会议"""
        return self.db.update_meeting(meeting)

    def delete_meeting(self, meeting_id: int) -> bool:
        """删除会议"""
        return self.db.delete_meeting(meeting_id)

    def generate_summary(self, meeting_id: int, transcript: str = None,
                         notes: str = None) -> MeetingSummary:
        """生成会议摘要"""
        meeting = self.db.get_meeting(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        # 简化实现：生成基础摘要
        content = transcript or notes or meeting.description or ""

        # 提取关键决策和行动项 (简化逻辑)
        key_decisions = []
        action_items = []

        # 简单关键词匹配
        if "决定" in content or "decided" in content.lower():
            key_decisions.append("会议做出了重要决定")
        if "需要" in content or "需要" in content or "action" in content.lower():
            action_items.append({"title": "待办事项", "assignee": None})

        summary = MeetingSummary(
            meeting_id=meeting_id,
            summary_text=f"会议'{meeting.title}'于{meeting.start_time}召开。{content[:200]}...",
            key_decisions=key_decisions,
            action_items=action_items,
            generated_by="ai",
            quality_score=0.8 if len(key_decisions) > 0 or len(action_items) > 0 else 0.5
        )

        # 保存摘要
        conn = self.db._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO p19_meeting_summaries
            (meeting_id, summary_text, key_decisions, action_items, follow_up_items, generated_by, quality_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            summary.meeting_id,
            summary.summary_text,
            json.dumps(summary.key_decisions),
            json.dumps(summary.action_items),
            json.dumps(summary.follow_up_items),
            summary.generated_by,
            summary.quality_score,
            summary.created_at
        ))
        summary.id = cursor.lastrowid
        conn.commit()
        conn.close()

        return summary

    def create_action_item(self, meeting_id: int, title: str,
                           assignee_id: int = None,
                           due_date: str = None,
                           priority: str = "medium",
                           description: str = None) -> MeetingActionItem:
        """创建行动项"""
        action_item = MeetingActionItem(
            meeting_id=meeting_id,
            title=title,
            description=description,
            assignee_id=assignee_id,
            due_date=due_date,
            priority=priority
        )

        conn = self.db._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO p19_meeting_action_items
            (meeting_id, title, description, assignee_id, due_date, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            action_item.meeting_id,
            action_item.title,
            action_item.description,
            action_item.assignee_id,
            action_item.due_date,
            action_item.priority,
            action_item.status,
            action_item.created_at,
            action_item.updated_at
        ))
        action_item.id = cursor.lastrowid
        conn.commit()
        conn.close()

        return action_item

    def complete_action_item(self, action_item_id: int,
                             completion_notes: str = None) -> bool:
        """完成行动项"""
        conn = self.db._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE p19_meeting_action_items
            SET status = 'completed', completion_notes = ?, completed_at = ?, updated_at = ?
            WHERE id = ?
        """, (
            completion_notes,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            action_item_id
        ))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def get_meeting_action_items(self, meeting_id: int) -> List[MeetingActionItem]:
        """获取会议行动项"""
        conn = self.db._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM p19_meeting_action_items
            WHERE meeting_id = ?
            ORDER BY created_at
        """, (meeting_id,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_action_item(row) for row in rows]

    def _row_to_action_item(self, row) -> MeetingActionItem:
        """将数据库行转换为 MeetingActionItem 对象"""
        return MeetingActionItem(
            id=row['id'],
            meeting_id=row['meeting_id'],
            summary_id=row['summary_id'],
            title=row['title'],
            description=row['description'],
            assignee_id=row['assignee_id'],
            due_date=row['due_date'],
            priority=row['priority'],
            status=row['status'],
            completion_notes=row['completion_notes'],
            completed_at=row['completed_at'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


# ==================== 自动报告服务 ====================

class AutoReportService:
    """自动报告服务"""

    def __init__(self, db: Optional[Any] = None):
        self.db = db or get_assistant_db()

    def create_report(self, user_id: int, report_type: str,
                      period_start: str, period_end: str,
                      title: str = None,
                      content: str = None,
                      tasks_completed: List[int] = None,
                      time_spent_hours: float = 0.0,
                      achievements: List[str] = None,
                      blockers: List[str] = None,
                      next_steps: List[str] = None) -> WorkReport:
        """创建工作报告"""
        report = WorkReport(
            user_id=user_id,
            report_type=report_type,
            title=title,
            period_start=period_start,
            period_end=period_end,
            content=content,
            tasks_completed=tasks_completed or [],
            time_spent_hours=time_spent_hours,
            achievements=achievements or [],
            blockers=blockers or [],
            next_steps=next_steps or []
        )
        return self.db.create_report(report)

    def get_report(self, report_id: int) -> Optional[WorkReport]:
        """获取报告"""
        return self.db.get_report(report_id)

    def get_user_reports(self, user_id: int, report_type: str = None,
                         limit: int = 50) -> List[WorkReport]:
        """获取用户报告"""
        return self.db.get_user_reports(user_id, report_type, limit)

    def update_report(self, report: WorkReport) -> WorkReport:
        """更新报告"""
        return self.db.update_report(report)

    def delete_report(self, report_id: int) -> bool:
        """删除报告"""
        return self.db.delete_report(report_id)

    def create_template(self, user_id: int, name: str, report_type: str,
                        template_content: str, description: str = None,
                        sections: List[str] = None,
                        is_default: bool = False) -> ReportTemplate:
        """创建报告模板"""
        template = ReportTemplate(
            user_id=user_id,
            name=name,
            description=description,
            report_type=report_type,
            template_content=template_content,
            sections=sections or [],
            is_default=is_default
        )
        return self.db.create_template(template)

    def get_user_templates(self, user_id: int) -> List[ReportTemplate]:
        """获取用户模板"""
        return self.db.get_user_templates(user_id)

    def generate_auto_report(self, user_id: int, report_type: str,
                             period_start: str, period_end: str,
                             template_id: int = None) -> WorkReport:
        """自动生成报告"""
        # 获取模板
        template = None
        if template_id:
            template = self.db.get_template(template_id)

        # 生成报告内容 (简化实现)
        title = f"{self._get_report_type_name(report_type)} ({period_start} - {period_end})"

        content = self._generate_report_content(user_id, period_start, period_end, template)

        report = WorkReport(
            user_id=user_id,
            report_type=report_type,
            title=title,
            period_start=period_start,
            period_end=period_end,
            content=content,
            status=ReportStatus.COMPLETED.value,
            generated_at=datetime.now().isoformat()
        )

        return self.db.create_report(report)

    def _get_report_type_name(self, report_type: str) -> str:
        """获取报告类型名称"""
        type_names = {
            ReportType.DAILY.value: "日报",
            ReportType.WEEKLY.value: "周报",
            ReportType.MONTHLY.value: "月报",
            ReportType.PROJECT.value: "项目报告",
            ReportType.CUSTOM.value: "自定义报告"
        }
        return type_names.get(report_type, "报告")

    def _generate_report_content(self, user_id: int, period_start: str,
                                  period_end: str,
                                  template: ReportTemplate = None) -> str:
        """生成报告内容"""
        # 简化实现：生成基础报告内容
        content = []

        if template:
            content.append(f"使用模板：{template.name}\n")
            content.append(template.template_content)
        else:
            content.append(f"报告周期：{period_start} 至 {period_end}\n\n")
            content.append("## 工作内容\n")
            content.append("- 完成多项工作任务\n")
            content.append("\n## 成果\n")
            content.append("- 达成预期目标\n")
            content.append("\n## 问题与建议\n")
            content.append("- 持续改进中\n")

        return "\n".join(content)


# ==================== 统一外观服务 ====================

class AssistantService:
    """AI 助手统一外观服务"""

    def __init__(self, db: Optional[Any] = None):
        self.db = db or get_assistant_db()
        self.work_assistant = WorkAssistantService(self.db)
        self.smart_schedule = SmartScheduleService(self.db)
        self.meeting_summary = MeetingSummaryService(self.db)
        self.auto_report = AutoReportService(self.db)

    def get_dashboard(self, user_id: int) -> Dict[str, Any]:
        """获取助手仪表盘"""
        # 获取今日日程
        today = datetime.now().date().isoformat()
        schedules = self.smart_schedule.get_user_schedules(user_id, today, today)

        # 获取待办行动项
        # (简化实现)

        # 获取最新报告
        reports = self.auto_report.get_user_reports(user_id, limit=5)

        # 获取推荐
        recommendations = self.work_assistant.get_recommendations(user_id, limit=10)

        return {
            'user_id': user_id,
            'today_schedules': [s.to_dict() for s in schedules],
            'pending_action_items': [],
            'recent_reports': [r.to_dict() for r in reports],
            'recommendations': [r.to_dict() for r in recommendations[:5]],
            'stats': {
                'total_schedules': len(schedules),
                'total_reports': len(reports),
                'pending_recommendations': len([r for r in recommendations if r.is_accepted is None])
            }
        }
