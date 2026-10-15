"""Illustrative fixed-rate loan applications, approval, disbursement and repayment."""
import secrets

import config
from exceptions import AccountStateError, NotFoundError, ValidationError
from utils import utc_now
from validation import clean_text
from .permissions import require


class LoanService:
    def __init__(self, db, loans, banking, customers, accounts, audit):
        self.db, self.loans = db, loans
        self.banking, self.customers, self.accounts, self.audit = banking, customers, accounts, audit

    def list_loans(self, actor):
        require(actor, "manage_loans")
        return self.loans.list_all()

    def apply(self, actor, customer_id: int, account_id: int, principal: int,
              rate_basis_points: int, term_months: int, notes: str = ""):
        require(actor, "manage_loans")
        if not isinstance(principal, int) or isinstance(principal, bool) or not 0 < principal <= config.MAX_AMOUNT_MINOR:
            raise ValidationError("Loan principal must be a positive valid amount.")
        if not isinstance(rate_basis_points, int) or isinstance(rate_basis_points, bool) \
                or not 0 <= rate_basis_points <= config.MAX_LOAN_RATE_BPS:
            raise ValidationError(f"Annual interest rate must be between 0% and {config.MAX_LOAN_RATE_BPS / 100:.2f}%.")
        if not isinstance(term_months, int) or isinstance(term_months, bool) \
                or not 1 <= term_months <= config.MAX_LOAN_TERM_MONTHS:
            raise ValidationError(f"Term must be between 1 and {config.MAX_LOAN_TERM_MONTHS} months.")
        notes = clean_text(notes, "Loan notes", max_len=300)
        interest = (principal * rate_basis_points * term_months + 60_000) // 120_000
        amount_due = principal + interest
        if amount_due > config.MAX_AMOUNT_MINOR:
            raise ValidationError("Total loan repayment exceeds the supported amount.")

        with self.db.transaction():
            customer = self.customers.get(customer_id)
            account = self.accounts.get(account_id)
            if not customer or not account:
                raise NotFoundError("Select an existing customer and account.")
            if not customer.is_active or account.status != "active" or account.customer_id != customer_id:
                raise AccountStateError("Choose an active account belonging to the selected customer.")
            if customer.kyc_status != "verified":
                raise AccountStateError("The customer's KYC must be verified before applying for a loan.")
            loan = self.loans.create(
                f"LN-{secrets.token_hex(5).upper()}", customer_id, account_id, principal,
                rate_basis_points, term_months, amount_due, notes, actor.id, utc_now())
            self.audit.add(actor.id, "loan_applied", "loan", loan.id, loan.loan_ref)
            return loan

    def decide(self, actor, loan_id: int, approved: bool):
        require(actor, "approve_loans")
        if not isinstance(approved, bool):
            raise ValidationError("Loan decision is invalid.")
        with self.db.transaction():
            loan = self.loans.get(loan_id)
            if not loan:
                raise NotFoundError("Loan application not found.")
            if loan.status != "pending":
                raise ValidationError("Only pending loan applications can be decided.")
            status = "approved" if approved else "rejected"
            self.loans.set_decision(loan_id, status, actor.id)
            self.audit.add(actor.id, f"loan_{status}", "loan", loan_id, loan.loan_ref)
            return self.loans.get(loan_id)

    def disburse(self, actor, loan_id: int):
        require(actor, "transact")
        with self.db.transaction():
            loan = self.loans.get(loan_id)
            if not loan:
                raise NotFoundError("Loan application not found.")
            if loan.status != "approved":
                raise ValidationError("Only approved loans can be disbursed.")
            customer = self.customers.get(loan.customer_id)
            if not customer or customer.kyc_status != "verified":
                raise AccountStateError("The customer's KYC must remain verified to disburse a loan.")
            self.banking.deposit(
                actor, loan.account_id, loan.principal, f"Loan {loan.loan_ref} disbursement")
            self.loans.mark_disbursed(loan_id, utc_now())
            self.audit.add(actor.id, "loan_disbursed", "loan", loan_id, loan.loan_ref)
            return self.loans.get(loan_id)

    def repay(self, actor, loan_id: int, amount: int):
        require(actor, "transact")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise ValidationError("Repayment must be a positive amount.")
        with self.db.transaction():
            loan = self.loans.get(loan_id)
            if not loan:
                raise NotFoundError("Loan application not found.")
            if loan.status != "active":
                raise ValidationError("Only active loans can be repaid.")
            if amount > loan.outstanding:
                raise ValidationError("Repayment cannot exceed the outstanding loan balance.")
            self.banking.withdraw(actor, loan.account_id, amount, f"Loan {loan.loan_ref} repayment")
            self.loans.add_payment(loan_id, amount)
            self.audit.add(actor.id, "loan_repayment", "loan", loan_id,
                           f"{loan.loan_ref}: {amount} minor units")
            return self.loans.get(loan_id)
