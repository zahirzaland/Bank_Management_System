"""Data access for the transaction ledger. All SQL is parameterized."""
import secrets
from typing import List, Optional

import config
from models import Transaction
from utils import escape_like, utc_now, utc_now_compact

_SELECT = """SELECT t.*, sa.account_number AS source_account_number,
                    da.account_number AS destination_account_number,
                    u.username AS created_by_username
             FROM transactions t
             LEFT JOIN accounts sa ON sa.id = t.source_account_id
             LEFT JOIN accounts da ON da.id = t.destination_account_id
             JOIN staff_users u ON u.id = t.created_by"""


class TransactionRepository:
    def __init__(self, db):
        self.db = db

    def _unique_ref(self) -> str:
        while True:
            ref = f"TXN-{utc_now_compact()}-{secrets.token_hex(3).upper()}"
            if not self.get_by_ref(ref):
                return ref

    def insert(self, transaction_type: str, amount: int, currency: str, source_id: Optional[int],
               destination_id: Optional[int], created_by: int, note: Optional[str],
               reversed_of_id: Optional[int] = None) -> Transaction:
        cur = self.db.conn.execute(
            """INSERT INTO transactions (transaction_ref, transaction_type, amount_minor_units, currency,
                                         source_account_id, destination_account_id, created_by, created_at,
                                         status, note, reversed_of_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)""",
            (self._unique_ref(), transaction_type, amount, currency, source_id, destination_id,
             created_by, utc_now(), note or None, reversed_of_id))
        return self.get(cur.lastrowid)

    def get(self, transaction_id: int) -> Optional[Transaction]:
        row = self.db.conn.execute(_SELECT + " WHERE t.id = ?", (transaction_id,)).fetchone()
        return Transaction.from_row(row) if row else None

    def get_by_ref(self, ref: str) -> Optional[Transaction]:
        row = self.db.conn.execute(_SELECT + " WHERE t.transaction_ref = ?", (ref,)).fetchone()
        return Transaction.from_row(row) if row else None

    def mark_reversed(self, transaction_id: int) -> None:
        self.db.conn.execute("UPDATE transactions SET status = 'reversed' WHERE id = ?", (transaction_id,))

    def search(self, account_number: str = "", transaction_type: str = "", start: Optional[str] = None,
               end: Optional[str] = None, ref_or_id: str = "", limit: int = config.SEARCH_LIMIT) -> List[Transaction]:
        """Filter by account, type, [start, end) timestamps, or transaction ID / reference."""
        sql = _SELECT + " WHERE 1 = 1"
        params: list = []
        if account_number:
            sql += " AND (sa.account_number = ? OR da.account_number = ?)"
            params += [account_number, account_number]
        if transaction_type:
            sql += " AND t.transaction_type = ?"
            params.append(transaction_type)
        if start:
            sql += " AND t.created_at >= ?"
            params.append(start)
        if end:
            sql += " AND t.created_at < ?"
            params.append(end)
        if ref_or_id:
            if ref_or_id.isdigit():  # a bare number is a transaction ID
                sql += " AND t.id = ?"
                params.append(int(ref_or_id))
            else:  # otherwise match (part of) the transaction reference
                sql += " AND t.transaction_ref LIKE ? ESCAPE '\\'"
                params.append(f"%{escape_like(ref_or_id)}%")
        sql += " ORDER BY t.id DESC LIMIT ?"
        params.append(limit)
        return [Transaction.from_row(r) for r in self.db.conn.execute(sql, params).fetchall()]
