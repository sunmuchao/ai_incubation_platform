"""
AI 查询助手数据库仓储层

提供查询历史、收藏、报告、模板的持久化操作
"""
import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from models.query_assistant import (
    QueryHistory, QueryFavorite, SavedReport, QueryTemplate,
    QueryIntent, QueryStatus, QueryEntities, TimeRange, Filter, Comparison,
    DEFAULT_QUERY_TEMPLATES
)

logger = logging.getLogger(__name__)


class QueryAssistantRepository:
    """AI 查询助手数据仓储"""

    def __init__(self, db_path: str = "ai_traffic_booster.db"):
        self.db_path = db_path
        self._init_tables()
        self._init_templates()

    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_tables(self):
        """初始化数据表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 查询历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    query_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    query_text TEXT NOT NULL,
                    query_intent TEXT NOT NULL,
                    query_entities JSON,
                    sql_generated TEXT,
                    result_summary JSON,
                    ai_interpretation TEXT,
                    execution_time_ms INTEGER,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 查询历史索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_history_session
                ON query_history(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_history_user
                ON query_history(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_history_created
                ON query_history(created_at)
            """)

            # 收藏表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_favorites (
                    favorite_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    query_id TEXT REFERENCES query_history(query_id),
                    query_text TEXT NOT NULL,
                    custom_name TEXT,
                    category TEXT,
                    tags JSON,
                    is_public BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_favorites_user
                ON query_favorites(user_id)
            """)

            # 保存的报告表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_reports (
                    report_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    report_title TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    report_content JSON,
                    query_ids JSON,
                    is_scheduled BOOLEAN DEFAULT FALSE,
                    schedule_config JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_saved_reports_user
                ON saved_reports(user_id)
            """)

            # 查询模板表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_templates (
                    template_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    template_name TEXT NOT NULL,
                    template_text TEXT NOT NULL,
                    template_intent TEXT NOT NULL,
                    example_entities JSON,
                    usage_count INTEGER DEFAULT 0,
                    is_recommended BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            logger.info("Query assistant tables initialized")

    def _init_templates(self):
        """初始化默认查询模板"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 检查是否已有模板
            cursor.execute("SELECT COUNT(*) FROM query_templates")
            count = cursor.fetchone()[0]

            if count == 0:
                # 插入默认模板
                for template_data in DEFAULT_QUERY_TEMPLATES:
                    template = QueryTemplate(
                        template_id=f"tpl_{len(template_data['template_name'])}_{hash(template_data['template_text']) % 10000:04d}",
                        category=template_data["category"],
                        template_name=template_data["template_name"],
                        template_text=template_data["template_text"],
                        template_intent=QueryIntent(template_data["template_intent"]),
                        example_entities=template_data["example_entities"]
                    )

                    cursor.execute("""
                        INSERT INTO query_templates
                        (template_id, category, template_name, template_text, template_intent, example_entities)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        template.template_id,
                        template.category,
                        template.template_name,
                        template.template_text,
                        template.template_intent.value,
                        json.dumps(template.example_entities)
                    ))

                logger.info(f"Initialized {len(DEFAULT_QUERY_TEMPLATES)} default query templates")

    # ========== QueryHistory 操作 ==========

    def save_query(self, query: QueryHistory) -> bool:
        """保存查询历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO query_history
                    (query_id, session_id, user_id, query_text, query_intent, query_entities,
                     sql_generated, result_summary, ai_interpretation, execution_time_ms,
                     status, error_message, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    query.query_id,
                    query.session_id,
                    query.user_id,
                    query.query_text,
                    query.query_intent.value,
                    json.dumps(query.query_entities.to_dict()),
                    query.sql_generated,
                    json.dumps(query.result_summary),
                    query.ai_interpretation,
                    query.execution_time_ms,
                    query.status.value,
                    query.error_message,
                    query.created_at.isoformat()
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save query: {e}")
                return False

    def get_query(self, query_id: str) -> Optional[QueryHistory]:
        """获取单个查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM query_history WHERE query_id = ?
            """, (query_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return self._row_to_query(row)

    def get_queries_by_session(self, session_id: str, limit: int = 50) -> List[QueryHistory]:
        """按会话获取查询历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM query_history
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (session_id, limit))

            return [self._row_to_query(row) for row in cursor.fetchall()]

    def get_queries_by_user(self, user_id: str, limit: int = 100) -> List[QueryHistory]:
        """按用户获取查询历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM query_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))

            return [self._row_to_query(row) for row in cursor.fetchall()]

    def get_recent_queries(self, limit: int = 100) -> List[QueryHistory]:
        """获取最近的查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM query_history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            return [self._row_to_query(row) for row in cursor.fetchall()]

    def update_query_status(self, query_id: str, status: QueryStatus,
                           error_message: Optional[str] = None) -> bool:
        """更新查询状态"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE query_history
                SET status = ?, error_message = ?
                WHERE query_id = ?
            """, (status.value, error_message, query_id))

            return cursor.rowcount > 0

    def update_query_result(self, query_id: str, result_summary: Dict[str, Any],
                           ai_interpretation: Optional[str] = None,
                           execution_time_ms: int = 0) -> bool:
        """更新查询结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE query_history
                SET result_summary = ?, ai_interpretation = ?,
                    execution_time_ms = ?, status = ?
                WHERE query_id = ?
            """, (
                json.dumps(result_summary),
                ai_interpretation,
                execution_time_ms,
                QueryStatus.COMPLETED.value,
                query_id
            ))

            return cursor.rowcount > 0

    def _row_to_query(self, row: sqlite3.Row) -> QueryHistory:
        """将数据库行转换为 QueryHistory 对象"""
        return QueryHistory(
            query_id=row["query_id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            query_text=row["query_text"],
            query_intent=QueryIntent(row["query_intent"]),
            query_entities=QueryEntities.from_dict(json.loads(row["query_entities"] or "{}")),
            sql_generated=row["sql_generated"],
            result_summary=json.loads(row["result_summary"] or "{}"),
            ai_interpretation=row["ai_interpretation"],
            execution_time_ms=row["execution_time_ms"] or 0,
            status=QueryStatus(row["status"]),
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
        )

    # ========== QueryFavorite 操作 ==========

    def save_favorite(self, favorite: QueryFavorite) -> bool:
        """保存收藏"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO query_favorites
                (favorite_id, user_id, query_id, query_text, custom_name, category, tags, is_public, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                favorite.favorite_id,
                favorite.user_id,
                favorite.query_id,
                favorite.query_text,
                favorite.custom_name,
                favorite.category,
                json.dumps(favorite.tags),
                favorite.is_public,
                favorite.created_at.isoformat()
            ))

            return True

    def get_favorites_by_user(self, user_id: str) -> List[QueryFavorite]:
        """获取用户的收藏"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM query_favorites
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))

            return [self._row_to_favorite(row) for row in cursor.fetchall()]

    def delete_favorite(self, favorite_id: str, user_id: str) -> bool:
        """删除收藏"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM query_favorites
                WHERE favorite_id = ? AND user_id = ?
            """, (favorite_id, user_id))

            return cursor.rowcount > 0

    def _row_to_favorite(self, row: sqlite3.Row) -> QueryFavorite:
        """将数据库行转换为 QueryFavorite 对象"""
        return QueryFavorite(
            favorite_id=row["favorite_id"],
            user_id=row["user_id"],
            query_id=row["query_id"],
            query_text=row["query_text"],
            custom_name=row["custom_name"],
            category=row["category"],
            tags=json.loads(row["tags"] or "[]"),
            is_public=bool(row["is_public"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
        )

    # ========== SavedReport 操作 ==========

    def save_report(self, report: SavedReport) -> bool:
        """保存报告"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO saved_reports
                (report_id, user_id, report_title, report_type, report_content,
                 query_ids, is_scheduled, schedule_config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.report_id,
                report.user_id,
                report.report_title,
                report.report_type,
                json.dumps(report.report_content),
                json.dumps(report.query_ids),
                report.is_scheduled,
                json.dumps(report.schedule_config) if report.schedule_config else None,
                report.created_at.isoformat(),
                report.updated_at.isoformat()
            ))

            return True

    def get_reports_by_user(self, user_id: str) -> List[SavedReport]:
        """获取用户的报告"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM saved_reports
                WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,))

            return [self._row_to_report(row) for row in cursor.fetchall()]

    def get_report(self, report_id: str) -> Optional[SavedReport]:
        """获取单个报告"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM saved_reports WHERE report_id = ?
            """, (report_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return self._row_to_report(row)

    def delete_report(self, report_id: str, user_id: str) -> bool:
        """删除报告"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM saved_reports
                WHERE report_id = ? AND user_id = ?
            """, (report_id, user_id))

            return cursor.rowcount > 0

    def _row_to_report(self, row: sqlite3.Row) -> SavedReport:
        """将数据库行转换为 SavedReport 对象"""
        return SavedReport(
            report_id=row["report_id"],
            user_id=row["user_id"],
            report_title=row["report_title"],
            report_type=row["report_type"],
            report_content=json.loads(row["report_content"]),
            query_ids=json.loads(row["query_ids"] or "[]"),
            is_scheduled=bool(row["is_scheduled"]),
            schedule_config=json.loads(row["schedule_config"]) if row["schedule_config"] else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
        )

    # ========== QueryTemplate 操作 ==========

    def get_templates(self, category: Optional[str] = None,
                     recommended_only: bool = True) -> List[QueryTemplate]:
        """获取查询模板"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if category and recommended_only:
                cursor.execute("""
                    SELECT * FROM query_templates
                    WHERE category = ? AND is_recommended = TRUE
                    ORDER BY usage_count DESC
                """, (category,))
            elif category:
                cursor.execute("""
                    SELECT * FROM query_templates
                    WHERE category = ?
                    ORDER BY usage_count DESC
                """, (category,))
            elif recommended_only:
                cursor.execute("""
                    SELECT * FROM query_templates
                    WHERE is_recommended = TRUE
                    ORDER BY usage_count DESC
                """)
            else:
                cursor.execute("""
                    SELECT * FROM query_templates
                    ORDER BY usage_count DESC
                """)

            return [self._row_to_template(row) for row in cursor.fetchall()]

    def get_template(self, template_id: str) -> Optional[QueryTemplate]:
        """获取单个模板"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM query_templates WHERE template_id = ?
            """, (template_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return self._row_to_template(row)

    def increment_template_usage(self, template_id: str) -> bool:
        """增加模板使用次数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE query_templates
                SET usage_count = usage_count + 1
                WHERE template_id = ?
            """, (template_id,))

            return cursor.rowcount > 0

    def _row_to_template(self, row: sqlite3.Row) -> QueryTemplate:
        """将数据库行转换为 QueryTemplate 对象"""
        return QueryTemplate(
            template_id=row["template_id"],
            category=row["category"],
            template_name=row["template_name"],
            template_text=row["template_text"],
            template_intent=QueryIntent(row["template_intent"]),
            example_entities=json.loads(row["example_entities"] or "{}"),
            usage_count=row["usage_count"] or 0,
            is_recommended=bool(row["is_recommended"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
        )

    # ========== 统计操作 ==========

    def get_query_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取查询统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if user_id:
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_queries,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_queries,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_queries,
                        AVG(execution_time_ms) as avg_execution_time
                    FROM query_history
                    WHERE user_id = ?
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_queries,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_queries,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_queries,
                        AVG(execution_time_ms) as avg_execution_time
                    FROM query_history
                """)

            row = cursor.fetchone()
            return {
                "total_queries": row["total_queries"] or 0,
                "completed_queries": row["completed_queries"] or 0,
                "failed_queries": row["failed_queries"] or 0,
                "avg_execution_time_ms": round(row["avg_execution_time_ms"] or 0, 2)
            }

    def get_intent_distribution(self, days: int = 7) -> Dict[str, int]:
        """获取查询意图分布"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT query_intent, COUNT(*) as count
                FROM query_history
                WHERE created_at >= datetime('now', ?)
                GROUP BY query_intent
                ORDER BY count DESC
            """, (f"-{days} days",))

            return {row["query_intent"]: row["count"] for row in cursor.fetchall()}


# 全局仓储实例
query_repository = QueryAssistantRepository()
