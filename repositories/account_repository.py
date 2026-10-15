"""Data access for accounts. All SQL is parameterized."""
import secrets
from typing import List, Optional

import config
from models import Account
from utils import escape_like, utc_now

_SELECT = ("SELECT a.*, c.full_name AS customer_name, c.customer_number AS customer_number "
           "FROM accounts a JOIN customers c ON c.id = a.customer_id")


class AccountRepository:
    def __init__(self, db):
        self.db = db

    def generate_account_number(self) -> str:
        """Random 10-digit number that does not yet exist (the UNIQUE constraint is the final guard)."""
        while True:
            number = str(secrets.randbelow(9 * 10 ** 9) + 10 ** 9)
            if not self.get_by_number(number):
                return number

    def create(self, customer_id: int, account_type: str, currency: str) -> Account:
        cur = self.db.conn.execute(
            """INSERT INTO accounts (account_number, customer_id, account_type, balance_minor_units,
                                     currency, status, opened_at)
               VALUES (?, ?, ?, 0, ?, 'active', ?)""",
            (self.generate_account_number(), customer_id, account_type, currency, utc_now()))
        return self.get(cur.lastrowid)

    def get(self, account_id: int) -> Optional[Account]:
        row = self.db.conn.execute(_SELECT + " WHERE a.id = ?", (account_id,)).fetchone()
        return Account.from_row(row) if row else None

    def get_by_number(self, number: str) -> Optional[Account]:
        row = self.db.conn.execute(_SELECT + " WHERE a.account_number = ?", (number,)).fetchone()
        return Account.from_row(row) if row else None

    def list_for_customer(self, customer_id: int) -> List[Account]:
        rows = self.db.conn.execute(_SELECT + " WHERE a.customer_id = ? ORDER BY a.id", (customer_id,)).fetchall()
        return [Account.from_row(r) for r in rows]

    def search(self, term: str = "", status: Optional[str] = None, limit: int = config.SEARCH_LIMIT) -> List[Account]:
        sql = _SELECT + " WHERE 1 = 1"
        params: list = []
        term = (term or "").strip()
        if term:
            like = f"%{escape_like(term)}%"
            sql += (" AND (a.account_number LIKE ? ESCAPE '\\' OR c.full_name LIKE ? ESCAPE '\\'"
                    " OR c.customer_number LIKE ? ESCAPE '\\')")
            params += [like, like, like]
        if status:
            sql += " AND a.status = ?"
            params.append(status)
        sql += " ORDER BY a.id DESC LIMIT ?"
        params.append(limit)
        return [Account.from_row(r) for r in self.db.conn.execute(sql, params).fetchall()]

    def adjust_balance(self, account_id: int, delta_minor: int) -> None:
        """Relative update; the CHECK constraint refuses a negative balance."""
        self.db.conn.execute(
            "UPDATE accounts SET balance_minor_units = balance_minor_units + ? WHERE id = ?",
            (delta_minor, account_id))

    def set_status(self, account_id: int, status: str) -> None:
        closed_at = utc_now() if status == "closed" else None
        self.db.conn.execute("UPDATE accounts SET status = ?, closed_at = ? WHERE id = ?",
                             (status, closed_at, account_id))

    def ledger_rows(self):
        """Stored balance vs. balance recomputed from the transaction ledger (FR-12)."""
        return self.db.conn.execute(
            """SELECT a.id, a.account_number, a.balance_minor_units AS stored,
                      COALESCE((SELECT SUM(amount_minor_units) FROM transactions t
                                WHERE t.destination_account_id = a.id), 0)
                    - COALESCE((SELECT SUM(amount_minor_units) FROM transactions t
                                WHERE t.source_account_id = a.id), 0) AS ledger
               FROM accounts a ORDER BY a.id""").fetchall()
