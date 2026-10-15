"""Data access for customers. All SQL is parameterized."""
from typing import List, Optional

import config
from models import Customer
from utils import escape_like, utc_now


class CustomerRepository:
    def __init__(self, db):
        self.db = db

    def next_customer_number(self) -> str:
        n = self.db.conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM customers").fetchone()[0]
        return f"CUST-{n:02d}"

    def create(self, full_name: str, phone: str, email: Optional[str], address: Optional[str]) -> Customer:
        now = utc_now()
        cur = self.db.conn.execute(
            """INSERT INTO customers (customer_number, full_name, phone, email, address, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
            (self.next_customer_number(), full_name, phone, email, address, now, now))
        return self.get(cur.lastrowid)

    def get(self, customer_id: int) -> Optional[Customer]:
        row = self.db.conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return Customer.from_row(row) if row else None

    def get_by_number(self, number: str) -> Optional[Customer]:
        row = self.db.conn.execute("SELECT * FROM customers WHERE customer_number = ?", (number,)).fetchone()
        return Customer.from_row(row) if row else None

    def find_duplicate(self, full_name: str, phone: str, exclude_id: Optional[int] = None) -> Optional[Customer]:
        row = self.db.conn.execute(
            "SELECT * FROM customers WHERE lower(full_name) = lower(?) AND phone = ? AND id <> ?",
            (full_name, phone, exclude_id or -1)).fetchone()
        return Customer.from_row(row) if row else None

    def search(self, term: str = "", status: Optional[str] = None, limit: int = config.SEARCH_LIMIT) -> List[Customer]:
        """Match customer ID/number, name or any of the customer's account numbers."""
        sql = ("SELECT DISTINCT c.* FROM customers c "
               "LEFT JOIN accounts a ON a.customer_id = c.id WHERE 1 = 1")
        params: list = []
        term = (term or "").strip()
        if term:
            like = f"%{escape_like(term)}%"
            sql += (" AND (c.customer_number LIKE ? ESCAPE '\\' OR c.full_name LIKE ? ESCAPE '\\'"
                    " OR a.account_number LIKE ? ESCAPE '\\')")
            params += [like, like, like]
        if status:
            sql += " AND c.status = ?"
            params.append(status)
        sql += " ORDER BY c.full_name, c.id LIMIT ?"
        params.append(limit)
        return [Customer.from_row(r) for r in self.db.conn.execute(sql, params).fetchall()]

    def update(self, customer_id: int, full_name: str, phone: str, email: Optional[str], address: Optional[str]) -> None:
        self.db.conn.execute(
            "UPDATE customers SET full_name = ?, phone = ?, email = ?, address = ?, updated_at = ? WHERE id = ?",
            (full_name, phone, email, address, utc_now(), customer_id))

    def set_status(self, customer_id: int, status: str) -> None:
        self.db.conn.execute("UPDATE customers SET status = ?, updated_at = ? WHERE id = ?",
                             (status, utc_now(), customer_id))

    def count_open_accounts(self, customer_id: int) -> int:
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM accounts WHERE customer_id = ? AND status <> 'closed'",
            (customer_id,)).fetchone()[0]

    def set_kyc(self, customer_id: int, status: str, notes: Optional[str], verified_at: Optional[str]) -> None:
        self.db.conn.execute(
            "UPDATE customers SET kyc_status = ?, kyc_notes = ?, kyc_verified_at = ?, updated_at = ? WHERE id = ?",
            (status, notes, verified_at, utc_now(), customer_id))
