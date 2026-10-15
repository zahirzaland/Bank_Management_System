"""Data access for loan applications and balances."""
from typing import List, Optional

from models.loan import Loan


_SELECT = (
    "SELECT l.*, c.full_name AS customer_name, a.account_number AS account_number "
    "FROM loans l JOIN customers c ON c.id = l.customer_id "
    "JOIN accounts a ON a.id = l.account_id"
)


class LoanRepository:
    def __init__(self, db):
        self.db = db

    def create(self, ref, customer_id, account_id, principal, rate_bps, term_months, amount_due, notes, actor_id, applied_at):
        cur = self.db.conn.execute(
            """INSERT INTO loans
               (loan_ref, customer_id, account_id, principal_minor_units, rate_basis_points, term_months,
                amount_due_minor, status, notes, created_by, applied_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (ref, customer_id, account_id, principal, rate_bps, term_months, amount_due, notes, actor_id, applied_at))
        return self.get(cur.lastrowid)

    def get(self, loan_id: int) -> Optional[Loan]:
        row = self.db.conn.execute(_SELECT + " WHERE l.id = ?", (loan_id,)).fetchone()
        return Loan.from_row(row) if row else None

    def list_all(self) -> List[Loan]:
        rows = self.db.conn.execute(_SELECT + " ORDER BY l.id DESC").fetchall()
        return [Loan.from_row(row) for row in rows]

    def set_decision(self, loan_id: int, status: str, actor_id: int) -> None:
        self.db.conn.execute(
            "UPDATE loans SET status = ?, approved_by = ? WHERE id = ?",
            (status, actor_id, loan_id))

    def mark_disbursed(self, loan_id: int, disbursed_at: str) -> None:
        self.db.conn.execute(
            "UPDATE loans SET status = 'active', disbursed_at = ? WHERE id = ?",
            (disbursed_at, loan_id))

    def add_payment(self, loan_id: int, amount: int) -> None:
        self.db.conn.execute(
            "UPDATE loans SET paid_minor_units = paid_minor_units + ?, "
            "status = CASE WHEN paid_minor_units + ? = amount_due_minor THEN 'paid' ELSE status END "
            "WHERE id = ?",
            (amount, amount, loan_id))
