"""Idempotent monthly interest crediting for Savings and Fixed Deposit accounts."""
import re
from datetime import datetime, timezone

import config
from exceptions import AccountStateError, DuplicateError, NotFoundError, ValidationError
from utils import utc_now
from .permissions import require

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class InterestService:
    def __init__(self, db, banking, accounts, audit):
        self.db, self.banking, self.accounts, self.audit = db, banking, accounts, audit

    def _account_and_rate(self, account_id: int, period: str):
        if not isinstance(period, str) or not _PERIOD_RE.fullmatch(period):
            raise ValidationError("Interest period must use YYYY-MM format.")
        if period != datetime.now(timezone.utc).strftime("%Y-%m"):
            raise ValidationError("Interest can only be applied for the current UTC month.")
        account = self.accounts.get(account_id)
        if not account:
            raise NotFoundError("Account not found.")
        if account.account_type not in config.INTEREST_RATES_BPS:
            raise AccountStateError("Interest is available only for Savings and Fixed Deposit accounts.")
        if account.status != "active":
            raise AccountStateError("Interest can only be applied to active accounts.")
        rate = config.INTEREST_RATES_BPS[account.account_type]
        amount = (account.balance * rate + 60_000) // 120_000
        if amount <= 0:
            raise ValidationError("The balance is too small to produce an interest credit.")
        return account, rate, amount

    def preview(self, actor, account_id: int, period: str):
        require(actor, "manage_interest")
        account, rate, amount = self._account_and_rate(account_id, period)
        existing = self.db.conn.execute(
            "SELECT rate_basis_points, amount_minor_units FROM interest_applications "
            "WHERE account_id = ? AND period = ?",
            (account_id, period)).fetchone()
        if existing:
            rate = existing["rate_basis_points"]
            amount = existing["amount_minor_units"]
        return {"account": account, "period": period, "rate_basis_points": rate,
                "amount": amount, "already_applied": existing is not None}

    def apply(self, actor, account_id: int, period: str):
        require(actor, "manage_interest")
        with self.db.transaction():
            account, rate, amount = self._account_and_rate(account_id, period)
            if self.db.conn.execute(
                    "SELECT 1 FROM interest_applications WHERE account_id = ? AND period = ?",
                    (account_id, period)).fetchone():
                raise DuplicateError("Interest has already been applied to this account for that month.")
            tx = self.banking.deposit(
                actor, account_id, amount, f"Monthly interest credit for {period}")
            self.db.conn.execute(
                """INSERT INTO interest_applications
                   (account_id, period, rate_basis_points, amount_minor_units, transaction_id, applied_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (account_id, period, rate, amount, tx.id, utc_now()))
            self.audit.add(actor.id, "interest_applied", "account", account_id,
                           f"{period}: {amount} minor units at {rate} bps")
            return amount

    def history(self, actor, account_id: int):
        require(actor, "manage_interest")
        if not self.accounts.get(account_id):
            raise NotFoundError("Account not found.")
        return self.db.conn.execute(
            """SELECT period, rate_basis_points, amount_minor_units, applied_at
               FROM interest_applications WHERE account_id = ? ORDER BY period DESC""",
            (account_id,)).fetchall()
