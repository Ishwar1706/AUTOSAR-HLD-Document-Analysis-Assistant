"""
Audit log module.

SQLite-based log recording every query, extraction, comparison, and review
action. Supports the governance requirement that AI-generated content must
be traceable and reviewed.

Does NOT store API keys or sensitive credentials.
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict

import config

logger = logging.getLogger(__name__)


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection, creating the table if needed."""
    conn = sqlite3.connect(config.AUDIT_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            collection TEXT NOT NULL,
            action_type TEXT NOT NULL,
            details TEXT,
            document TEXT,
            model_used TEXT,
            status TEXT DEFAULT 'success',
            latency_ms INTEGER
        )
    """)
    return conn


def log_action(
    collection: str,
    action_type: str,
    details: str,
    model_used: str,
    document: str = "",
    status: str = "success",
    latency_ms: int = None,
):
    """
    Log an action to the audit database.

    action_type should be one of:
        document_ingestion, question_answering, entity_extraction,
        document_comparison, architecture_review, document_summary, export
    """
    try:
        conn = _get_conn()
        with conn:
            conn.execute(
                "INSERT INTO audit_log (timestamp, collection, action_type, details, document, model_used, status, latency_ms) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.utcnow().isoformat(),
                    collection,
                    action_type,
                    details[:2000] if details else "",  # Truncate long details
                    document,
                    model_used,
                    status,
                    latency_ms,
                ),
            )
        conn.close()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


def get_recent_logs(
    collection: Optional[str] = None,
    action_type: Optional[str] = None,
    limit: int = 100,
) -> List[tuple]:
    """
    Retrieve recent audit log entries with optional filters.
    """
    try:
        conn = _get_conn()
        query = "SELECT timestamp, collection, action_type, details, document, model_used, status FROM audit_log"
        conditions = []
        params = []

        if collection:
            conditions.append("collection = ?")
            params.append(collection)
        if action_type:
            conditions.append("action_type = ?")
            params.append(action_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        cur = conn.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to read audit log: {e}")
        return []


def get_log_stats(collection: Optional[str] = None) -> Dict:
    """Get summary statistics from the audit log."""
    try:
        conn = _get_conn()

        base_query = "FROM audit_log"
        params = []
        if collection:
            base_query += " WHERE collection = ?"
            params.append(collection)

        # Total count
        cur = conn.execute(f"SELECT COUNT(*) {base_query}", params)
        total = cur.fetchone()[0]

        # Count by action type
        cur = conn.execute(
            f"SELECT action_type, COUNT(*) {base_query} GROUP BY action_type",
            params,
        )
        by_action = dict(cur.fetchall())

        conn.close()
        return {"total": total, "by_action": by_action}
    except Exception as e:
        logger.error(f"Failed to get audit stats: {e}")
        return {"total": 0, "by_action": {}}


def get_action_types() -> List[str]:
    """Return list of distinct action types in the log."""
    try:
        conn = _get_conn()
        cur = conn.execute("SELECT DISTINCT action_type FROM audit_log ORDER BY action_type")
        types = [row[0] for row in cur.fetchall()]
        conn.close()
        return types
    except Exception:
        return []
