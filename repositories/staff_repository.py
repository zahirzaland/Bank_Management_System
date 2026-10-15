"""Data access for staff users. All SQL is parameterized."""
from typing import List, Optional

from models import StaffUser
from utils import utc_now


class StaffRepository:
    def __init__(self, db):
        self.db = db

    def count(self) -> int:
        return self.db.conn.execute("SELECT COUNT(*) FROM staff_users").fetchone()[0]

    def count_active_admins(self) -> int:
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM staff_users WHERE role = 'admin' AND is_active = 1").fetchone()[0]

    def create(self, username: str, password_hash: str, role: str) -> StaffUser:
        cur = self.db.conn.execute(
            "INSERT INTO staff_users (username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
            (username, password_hash, role, utc_now()))
        return self.get(cur.lastrowid)

    def get(self, user_id: int) -> Optional[StaffUser]:
        row = self.db.conn.execute("SELECT * FROM staff_users WHERE id = ?", (user_id,)).fetchone()
        return StaffUser.from_row(row) if row else None

    def get_by_username(self, username: str) -> Optional[StaffUser]:
        row = self.db.conn.execute("SELECT * FROM staff_users WHERE username = ?", (username,)).fetchone()
        return StaffUser.from_row(row) if row else None

    def list_all(self) -> List[StaffUser]:
        rows = self.db.conn.execute("SELECT * FROM staff_users ORDER BY username").fetchall()
        return [StaffUser.from_row(r) for r in rows]

    def set_role(self, user_id: int, role: str) -> None:
        self.db.conn.execute("UPDATE staff_users SET role = ? WHERE id = ?", (role, user_id))

    def set_active(self, user_id: int, active: bool) -> None:
        self.db.conn.execute("UPDATE staff_users SET is_active = ? WHERE id = ?", (1 if active else 0, user_id))

    def set_password_hash(self, user_id: int, password_hash: str) -> None:
        self.db.conn.execute("UPDATE staff_users SET password_hash = ? WHERE id = ?", (password_hash, user_id))

    def touch_login(self, user_id: int) -> None:
        self.db.conn.execute("UPDATE staff_users SET last_login_at = ? WHERE id = ?", (utc_now(), user_id))
