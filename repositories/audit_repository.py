"""Data access for the audit trail (FR-16). Append-only (enforced by triggers)."""
from typing import List, Optional

import config
from utils import escape_like, utc_now


class AuditRepository:
    def __init__(self, db):
        self.db = db

    def add(self, staff_user_id: Optional[int], action: str, entity_type: Optional[str] = None,
            entity_id=None, details: Optional[str] = None) -> None:
        self.db.conn.execute(
            """INSERT INTO audit_logs (staff_user_id, action, entity_type, entity_id, details, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (staff_user_id, action, entity_type, None if entity_id is None else str(entity_id),
             (details or "")[:500], utc_now()))

    def list(self, text: str = "", limit: int = config.SEARCH_LIMIT) -> List[dict]:
        sql = """SELECT l.id, l.created_at, COALESCE(u.username, '-') AS username, l.action,
                        COALESCE(l.entity_type, '') AS entity_type, COALESCE(l.entity_id, '') AS entity_id,
                        COALESCE(l.details, '') AS details
                 FROM audit_logs l LEFT JOIN staff_users u ON u.id = l.staff_user_id WHERE 1 = 1"""
        params: list = []
        text = (text or "").strip()
        if text:
            like = f"%{escape_like(text)}%"
            sql += (" AND (l.action LIKE ? ESCAPE '\\' OR l.details LIKE ? ESCAPE '\\'"
                    " OR u.username LIKE ? ESCAPE '\\' OR l.entity_type LIKE ? ESCAPE '\\')")
            params += [like] * 4
        sql += " ORDER BY l.id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.db.conn.execute(sql, params).fetchall()]
